package com.alldownload.android

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.pm.ServiceInfo
import android.app.ActivityManager
import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.os.PowerManager
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import android.util.Log
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import java.io.File

/**
 * Independent Android downloader with sequential persistent tasks.
 * Private workspaces and yt-dlp --continue enable best-effort pause/resume.
 * MediaExporter still limits every public output to All-Download categories.
 */
class DownloadService : Service() {
    data class UiState(val busy: Boolean, val progress: Int, val message: String)

    companion object {
        const val ACTION_START = "com.alldownload.android.START"
        const val ACTION_ADD_QUEUE = "com.alldownload.android.ADD_QUEUE"
        const val ACTION_RUN_QUEUE = "com.alldownload.android.RUN_QUEUE"
        const val ACTION_PAUSE = "com.alldownload.android.PAUSE"
        const val ACTION_CANCEL = "com.alldownload.android.CANCEL"
        const val ACTION_SHUTDOWN = "com.alldownload.android.SHUTDOWN"
        const val EXTRA_URL = "url"
        const val EXTRA_MODE = "mode"
        const val EXTRA_QUALITY = "quality"
        private const val CHANNEL = "downloads"
        private const val APP_CHANNEL = "application"
        private const val NOTIFICATION_ID = 101
        private const val APP_NOTIFICATION_ID = 102
        private const val PROCESS_ID = "all-download-android"

        // A notification while the UI is visible does NOT need an idle foreground
        // service. This avoids keeping CPU and battery awake just to show "Quitter".
        fun showOpenNotification(context: Context) {
            if (state.busy) return
            if (Build.VERSION.SDK_INT >= 33 &&
                context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=
                    PackageManager.PERMISSION_GRANTED) return
            val manager = context.getSystemService(NotificationManager::class.java)
            if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(
                NotificationChannel(APP_CHANNEL, "Application All-Download",
                    NotificationManager.IMPORTANCE_LOW))
            val open = PendingIntent.getActivity(context, 10,
                Intent(context, MainActivity::class.java),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val quit = PendingIntent.getService(context, 11,
                Intent(context, DownloadService::class.java).setAction(ACTION_SHUTDOWN),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val builder = if (Build.VERSION.SDK_INT >= 26)
                Notification.Builder(context, APP_CHANNEL) else Notification.Builder(context)
            manager.notify(APP_NOTIFICATION_ID, builder
                .setSmallIcon(android.R.drawable.stat_sys_download_done)
                .setContentTitle("All-Download ouverte")
                .setContentText("Fermer l’application depuis cette notification")
                .setContentIntent(open)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setPriority(Notification.PRIORITY_LOW)
                .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Fermer", quit)
                .build())
        }

        fun hideOpenNotification(context: Context) {
            context.getSystemService(NotificationManager::class.java)
                .cancel(APP_NOTIFICATION_ID)
        }

        @Volatile var state = UiState(false, 0, "Prêt.")
            private set
    }

    @Volatile private var cancelled = false
    @Volatile private var paused = false
    @Volatile private var active = false
    @Volatile private var timedOut = false
    private var lastNotification = 0L
    private var lastQueueSave = 0L
    private var lastStatusUpdate = 0L
    private var lastNotifiedPercent = -1
    private var lastSavedPercent = -1
    private var engineReady = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        DownloadQueue.recoverInterrupted(this)
        // Never block the UI/main service thread while deleting old media scratch.
        // A low-priority sweep at most once per day keeps I/O and battery bounded.
        val prefs = getSharedPreferences("android_scratch_maintenance", MODE_PRIVATE)
        val now = System.currentTimeMillis()
        if (now - prefs.getLong("last_sweep_ms", 0L) > 24L * 60 * 60 * 1000) {
            prefs.edit().putLong("last_sweep_ms", now).apply()
            Thread({
                try {
                    DownloadQueue.cleanupOrphanWorkspaces(applicationContext)
                } catch (error: Exception) {
                    Log.w("AllDownloadVideo", "Nettoyage différé impossible", error)
                }
            }, "all-download-scratch-maintenance").apply {
                priority = Thread.MIN_PRIORITY
                isDaemon = true
            }.start()
        }
        if (Build.VERSION.SDK_INT >= 26) {
            getSystemService(NotificationManager::class.java).createNotificationChannel(
                NotificationChannel(CHANNEL, "Téléchargements All-Download",
                    NotificationManager.IMPORTANCE_LOW))
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_SHUTDOWN -> {
                // Explicit shutdown ends this transfer and closes only our own task.
                // Pending downloads stay persisted and can be started next launch.
                if (active) {
                    cancelled = true
                    paused = false
                    state = state.copy(message = "Fermeture et arrêt du téléchargement…")
                    YoutubeDL.getInstance().destroyProcessById(PROCESS_ID)
                } else {
                    state = UiState(false, 0, "Application fermée.")
                    stopSelfResult(startId)
                }
                hideOpenNotification(this)
                if (!active) getSystemService(NotificationManager::class.java)
                    .cancel(NOTIFICATION_ID)
                val tasks = (getSystemService(ACTIVITY_SERVICE) as ActivityManager).appTasks
                tasks.forEach { task ->
                    try { task.finishAndRemoveTask() }
                    catch (error: RuntimeException) {
                        Log.w("AllDownloadVideo", "Fermeture de la tâche refusée", error)
                    }
                }
            }
            ACTION_CANCEL -> {
                if (active) {
                    cancelled = true
                    state = state.copy(message = "Annulation en cours…")
                    YoutubeDL.getInstance().destroyProcessById(PROCESS_ID)
                } else stopSelfResult(startId)
            }
            ACTION_PAUSE -> {
                if (active) {
                    paused = true
                    state = state.copy(message = "Pause demandée…")
                    YoutubeDL.getInstance().destroyProcessById(PROCESS_ID)
                } else stopSelfResult(startId)
            }
            ACTION_ADD_QUEUE, ACTION_START -> {
                val url = intent.getStringExtra(EXTRA_URL).orEmpty()
                val mode = intent.getIntExtra(EXTRA_MODE, 0).coerceIn(0, 6)
                val quality = intent.getIntExtra(EXTRA_QUALITY, 3).coerceIn(0, 4)
                if (url.isBlank()) {
                    if (!active) {
                        state = UiState(false, 0, "Lien manquant.")
                        stopSelfResult(startId)
                    }
                    return START_NOT_STICKY
                }
                try {
                    DownloadQueue.enqueue(this, url, mode, quality)
                } catch (error: Exception) {
                    if (!active) {
                        state = UiState(false, 0, "File d’attente : " + error.localizedMessage)
                        stopSelfResult(startId)
                    }
                    return START_NOT_STICKY
                }
                if (intent.action == ACTION_ADD_QUEUE) {
                    if (!active) {
                        state = UiState(false, 0, "Ajouté à la file d’attente.")
                        stopSelfResult(startId)
                    }
                } else if (!active) startWorker(startId)
            }
            ACTION_RUN_QUEUE -> {
                DownloadQueue.resumePaused(this)
                if (!active) startWorker(startId)
            }
        }
        return START_NOT_STICKY
    }

    private fun startWorker(startId: Int) {
        if (active) return
        if (DownloadQueue.next(this) == null) {
            state = UiState(false, 0, "La file d’attente est vide.")
            stopSelfResult(startId)
            return
        }
        active = true
        paused = false
        cancelled = false
        timedOut = false
        lastNotification = 0L
        lastQueueSave = 0L
        lastStatusUpdate = 0L
        lastNotifiedPercent = -1
        lastSavedPercent = -1
        state = UiState(true, 0, "Initialisation du moteur Android…")
        hideOpenNotification(this)
        startForeground(NOTIFICATION_ID, notification("File d’attente en préparation", 0))
        Thread({ processQueue() }, "all-download-worker").start()
    }

    private fun processQueue() {
        var lastResult = "File d’attente terminée."
        try {
            while (!paused && !cancelled) {
                val task = DownloadQueue.next(this) ?: break
                DownloadQueue.update(this, task.id, DownloadQueue.RUNNING, task.progress,
                    "Téléchargement en cours…")
                lastResult = downloadTask(task)
                if (paused || cancelled) break
            }
            state = UiState(false, if (paused || cancelled) 0 else 100,
                when {
                    paused -> if (timedOut) "Limite Android atteinte. Ouvrez All-Download puis reprenez." else "File mise en pause. Reprise possible."
                    cancelled -> "Téléchargement annulé. File conservée."
                    else -> lastResult
                })
        } catch (error: Exception) {
            Log.e("AllDownloadVideo", "Erreur inattendue de la file Android", error)
            state = UiState(false, 0, "Erreur de la file : " + errorSummary(error))
        } finally {
            active = false
            // All service commands are received on Android's main thread. Finalize there
            // as well: a new download may have started while this callback was queued.
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                if (active) return@post
                val showFinished = DownloadOptions.get(this)
                    .getBoolean("notify_finished", true)
                val manager = getSystemService(NotificationManager::class.java)
                if (!cancelled && !timedOut && showFinished) {
                    // Also publish the final error if the worker failed unexpectedly.
                    manager.notify(NOTIFICATION_ID,
                        notification(state.message, state.progress, false))
                }
                stopForeground(if (cancelled || timedOut || !showFinished)
                    STOP_FOREGROUND_REMOVE else STOP_FOREGROUND_DETACH)
                if (cancelled || timedOut || !showFinished) manager.cancel(NOTIFICATION_ID)
                // stopSelfResult(oldStartId) leaves this service resident after a later
                // pause/cancel/add command increments startId. All work is finished now.
                stopSelf()
            }
        }
    }

    private fun downloadTask(task: DownloadQueue.Task): String {
        val root = getExternalFilesDir(null) ?: filesDir
        val work = File(root, "All-Download/Donnees/temporaires/" + task.id)
        var exported = 0
        var exportRoot = work
        try {
            check(!paused && !cancelled) { "Interrompu." }
            if (!work.isDirectory && !work.mkdirs())
                throw IllegalStateException("Impossible de créer le dossier temporaire privé.")
            if (!engineReady) {
                YoutubeDL.getInstance().init(applicationContext)
                FFmpeg.getInstance().init(applicationContext)
                engineReady = true
            }
            maybeRefreshSocialEngine(task.url)
            check(!paused && !cancelled) { "Interrompu." }

            val request = buildRequest(task.url, task.mode, task.quality, work)
            lastSavedPercent = -1
            lastNotifiedPercent = -1
            lastQueueSave = 0L
            lastNotification = 0L
            state = UiState(true, task.progress, "Téléchargement en cours…")
            fun transfer(mediaRequest: YoutubeDLRequest) {
              YoutubeDL.getInstance().execute(mediaRequest, PROCESS_ID, false) { progress, eta, _ ->
                if (!paused && !cancelled) {
                    val percent = progress.toInt().coerceIn(0, 100)
                    val now = SystemClock.elapsedRealtime()
                    val message = "Téléchargement : $percent % • reste " +
                        eta.coerceAtLeast(0) + " s"
                    // Limit allocations and activity redraws while keeping progress visible.
                    if (percent != state.progress || now - lastStatusUpdate >= 2500L) {
                        state = UiState(true, percent, message)
                        lastStatusUpdate = now
                    }
                    // Atomic queue persistence at most every 3.5s, plus completion.
                    if (percent > lastSavedPercent && (
                            now - lastQueueSave >= 3500L || percent >= 100)) {
                        lastQueueSave = now
                        lastSavedPercent = percent
                        DownloadQueue.update(this, task.id, progress = percent,
                            message = message)
                    }
                    // Avoid high-frequency notification IPC and repeated wakeups.
                    if (percent != lastNotifiedPercent && (
                            now - lastNotification >= 5000L || percent >= 100)) {
                        lastNotification = now
                        lastNotifiedPercent = percent
                        getSystemService(NotificationManager::class.java).notify(
                            NOTIFICATION_ID, notification(message, percent))
                    }
                }
            }
            }
            try {
                transfer(request)
            } catch (initial: Exception) {
                if (paused || cancelled || !DownloadRules.isTwitchVod(task.url)) throw initial
                state = UiState(true, 0, "Vérification du flux Twitch public…")
                val manifest = TwitchHls.resolve(task.url, task.quality) { paused || cancelled }
                val fallbackWork = File(work, "twitch-source").apply {
                    check(isDirectory || mkdirs()) { "Dossier Twitch temporaire inaccessible." }
                }
                val fallback = buildRequest(task.url, task.mode, task.quality, fallbackWork, manifest)
                val id = java.net.URI(task.url).path.trimEnd('/').substringAfterLast('/')
                fallback.addOption("--output", File(fallbackWork, "Twitch_$id.%(ext)s").absolutePath)
                transfer(fallback)
                exportRoot = fallbackWork
            }
            check(!paused && !cancelled) { "Interrompu." }
            val category = DownloadRules.categoryFor(task.url, task.mode)
            val files = exportRoot.walkTopDown().filter { it.isFile &&
                !it.name.endsWith(".part") && !it.name.endsWith(".ytdl") }.toList()
            check(files.isNotEmpty()) { "Aucun fichier final créé par le moteur." }
            for ((index, file) in files.withIndex()) {
                check(!paused && !cancelled) { "Interrompu." }
                state = UiState(true, 100, "Enregistrement : " + (index + 1) + "/" + files.size)
                MediaExporter.export(this, file, category) { paused || cancelled }
                exported++
            }
            val success = "$exported fichier(s) dans Téléchargements/All-Download/$category"
            DownloadQueue.update(this, task.id, DownloadQueue.DONE, 100, success)
            work.deleteRecursively()
            return success
        } catch (error: Exception) {
            return when {
                paused -> {
                    DownloadQueue.update(this, task.id, DownloadQueue.PAUSED,
                        message = if (timedOut) "Limite Android 15 : reprise depuis la file." else "En pause : reprendre pour continuer.")
                    "Téléchargement en pause."
                }
                cancelled -> {
                    DownloadQueue.update(this, task.id, DownloadQueue.CANCELLED,
                        message = "Annulé par l’utilisateur.")
                    work.deleteRecursively()
                    "Téléchargement annulé."
                }
                else -> {
                    Log.e("AllDownloadVideo", "Échec du téléchargement " + task.url, error)
                    val message = "Échec : " + errorSummary(error)
                    DownloadQueue.update(this, task.id, DownloadQueue.ERROR, message = message)
                    message
                }
            }
        }
    }

    private fun maybeRefreshSocialEngine(url: String) {
        // YouTube needs a recent yt-dlp extractor for JS challenges / 403 fixes.
        // Keep Twitch untouched and never refresh automatically on mobile data.
        if (!DownloadRules.needsFreshExtractor(url)) return
        // Don't spend mobile data or battery on optional yt-dlp engine updates.
        val power = getSystemService(POWER_SERVICE) as PowerManager
        if (power.isPowerSaveMode) return
        val network = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
        if (network.isActiveNetworkMetered) return
        if (!getSharedPreferences("app_settings_v1", MODE_PRIVATE)
                .getBoolean("auto_update", true)) return
        val prefs = getSharedPreferences("yt_dlp_updates", MODE_PRIVATE)
        val now = System.currentTimeMillis()
        val success = prefs.getLong("last_success_ms", 0L)
        val attempt = prefs.getLong("last_attempt_ms", 0L)
        if (success > 0 && now - success in 0 until 7L * 24 * 3600 * 1000) return
        if (attempt > 0 && now - attempt in 0 until 12L * 3600 * 1000) return
        prefs.edit().putLong("last_attempt_ms", now).apply()
        state = UiState(true, 0, "Actualisation de yt-dlp…")
        try {
            val result = YoutubeDL.getInstance().updateYoutubeDL(applicationContext)
            prefs.edit().putLong("last_success_ms", System.currentTimeMillis()).apply()
            Log.i("AllDownloadVideo", "yt-dlp : $result")
        } catch (error: Exception) {
            Log.w("AllDownloadVideo", "Version intégrée conservée.", error)
        }
    }

    private fun errorSummary(error: Throwable): String {
        val lines = (error.localizedMessage ?: error.javaClass.simpleName)
            .lines().map { it.trim() }.filter { it.isNotBlank() }
        return (lines.lastOrNull { it.startsWith("ERROR:", ignoreCase = true) }
            ?: lines.lastOrNull { !it.startsWith("WARNING:", ignoreCase = true) }
            ?: lines.lastOrNull()
            ?: error.javaClass.simpleName).take(280)
    }

    private fun buildRequest(url: String, mode: Int, quality: Int, work: File,
                             mediaUrl: String = url): YoutubeDLRequest {
        val request = YoutubeDLRequest(mediaUrl)
        // YouTube may advertise media URLs that return 403. Probe candidates
        // before selection while retaining the requested quality and container.
        if (DownloadRules.isYoutubeHost(url)) request.addOption("--check-formats")
        request.addOption("--no-mtime")
        request.addOption("--newline")
        request.addOption("--progress-delta", 1)
        request.addOption("--continue")
        // Retry transient network failures without changing source quality choices.
        request.addOption("--socket-timeout", 20)
        request.addOption("--retries", 5)
        request.addOption("--fragment-retries", 5)
        request.addOption("--no-overwrites")
        request.addOption("--output", File(work, "%(title).150B [%(id)s].%(ext)s").absolutePath)
        CookieStore.existing(this)?.let { request.addOption("--cookies", it.absolutePath) }
        if (mode != 5 && mode != 6) request.addOption("--no-playlist")
        else request.addOption("--yes-playlist")
        when (mode) {
            1, 2, 3 -> {
                request.addOption("--extract-audio")
                request.addOption("--audio-format", when (mode) { 1 -> "mp3"; 2 -> "m4a"; else -> "flac" })
                val target = DownloadOptions.get(this).getString("audio_quality", "0")
                val qualitySetting = if (mode == 1 && target in
                    setOf("0", "128K", "192K", "256K", "320K")) target ?: "0"
                    else "0"
                request.addOption("--audio-quality", qualitySetting)
            }
            4 -> request.addOption("--recode-video", "gif")
            else -> {
                request.addOption("--format", DownloadRules.videoFormat(url, quality))
                val container = if (DownloadOptions.get(this)
                        .getString("video_format", "MP4") == "MKV") "mkv" else "mp4"
                request.addOption("--merge-output-format", container)
                if (DownloadOptions.get(this).getBoolean("remux_video", false))
                    request.addOption("--remux-video", container)
            }
        }
        DownloadOptions.apply(this, request, url, mode)
        return request
    }

    private fun notification(message: String, progress: Int,
                             ongoing: Boolean = true): Notification {
        val openIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val builder = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, CHANNEL)
                      else Notification.Builder(this)
        builder.setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle("All-Download")
            .setContentText(message)
            .setContentIntent(openIntent)
            .setOnlyAlertOnce(true)
            .setOngoing(ongoing)
            .setProgress(100, progress, progress == 0 && ongoing)
        if (ongoing) {
            val pause = PendingIntent.getService(this, 1,
                Intent(this, DownloadService::class.java).setAction(ACTION_PAUSE),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val cancel = PendingIntent.getService(this, 2,
                Intent(this, DownloadService::class.java).setAction(ACTION_CANCEL),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            builder.addAction(android.R.drawable.ic_media_pause, "Pause", pause)
            builder.addAction(android.R.drawable.ic_menu_close_clear_cancel, "Annuler", cancel)
            val quit = PendingIntent.getService(this, 3,
                Intent(this, DownloadService::class.java).setAction(ACTION_SHUTDOWN),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            builder.addAction(android.R.drawable.ic_menu_close_clear_cancel, "Fermer", quit)
        }
        return builder.build()
    }

    /** Android 15 enforces a six-hour rolling dataSync foreground-service limit. */
    override fun onTimeout(startId: Int, fgsType: Int) {
        if (fgsType and ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC != 0) {
            timedOut = true
            paused = true
            state = UiState(false, state.progress,
                "Durée maximale Android atteinte. Ouvrez All-Download pour reprendre.")
            try {
                DownloadQueue.pauseRunning(this,
                    "Limite Android 15 atteinte : reprise possible depuis la file.")
            } catch (error: Exception) {
                Log.e("AllDownloadVideo", "Sauvegarde du transfert expiré impossible", error)
            }
            // Stop in the system's grace period. onDestroy interrupts yt-dlp.
            stopSelf()
        } else {
            super.onTimeout(startId, fgsType)
        }
    }

    override fun onDestroy() {
        if (active) {
            paused = true
            YoutubeDL.getInstance().destroyProcessById(PROCESS_ID)
        }
        super.onDestroy()
    }
}
