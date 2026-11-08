package com.alldownload.android

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
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
        const val EXTRA_URL = "url"
        const val EXTRA_MODE = "mode"
        const val EXTRA_QUALITY = "quality"
        private const val CHANNEL = "downloads"
        private const val NOTIFICATION_ID = 101
        private const val PROCESS_ID = "all-download-android"

        @Volatile var state = UiState(false, 0, "Prêt.")
            private set
    }

    @Volatile private var cancelled = false
    @Volatile private var paused = false
    @Volatile private var active = false
    private var lastNotification = 0L
    private var lastQueueSave = 0L

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        DownloadQueue.recoverInterrupted(this)
        if (Build.VERSION.SDK_INT >= 26) {
            getSystemService(NotificationManager::class.java).createNotificationChannel(
                NotificationChannel(CHANNEL, "Téléchargements All-Download",
                    NotificationManager.IMPORTANCE_LOW))
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_CANCEL -> {
                if (active) {
                    cancelled = true
                    state = state.copy(message = "Annulation en cours…")
                    YoutubeDL.getInstance().destroyProcessById(PROCESS_ID)
                }
            }
            ACTION_PAUSE -> {
                if (active) {
                    paused = true
                    state = state.copy(message = "Pause demandée…")
                    YoutubeDL.getInstance().destroyProcessById(PROCESS_ID)
                }
            }
            ACTION_ADD_QUEUE, ACTION_START -> {
                val url = intent.getStringExtra(EXTRA_URL).orEmpty()
                val mode = intent.getIntExtra(EXTRA_MODE, 0).coerceIn(0, 6)
                val quality = intent.getIntExtra(EXTRA_QUALITY, 0).coerceIn(0, 4)
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
        lastNotification = 0L
        state = UiState(true, 0, "Initialisation du moteur Android…")
        startForeground(NOTIFICATION_ID, notification("File d’attente en préparation", 0))
        Thread({ processQueue(startId) }, "all-download-worker").start()
    }

    private fun processQueue(startId: Int) {
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
                    paused -> "File mise en pause. Reprise possible."
                    cancelled -> "Téléchargement annulé. File conservée."
                    else -> lastResult
                })
            getSystemService(NotificationManager::class.java).notify(
                NOTIFICATION_ID, notification(state.message, state.progress, false))
        } catch (error: Exception) {
            Log.e("AllDownloadVideo", "Erreur inattendue de la file Android", error)
            state = UiState(false, 0, "Erreur de la file : " + errorSummary(error))
        } finally {
            active = false
            stopForeground(if (cancelled) STOP_FOREGROUND_REMOVE else STOP_FOREGROUND_DETACH)
            stopSelfResult(startId)
        }
    }

    private fun downloadTask(task: DownloadQueue.Task): String {
        val root = getExternalFilesDir(null) ?: filesDir
        val work = File(root, "All-Download/Donnees/temporaires/" + task.id)
        var exported = 0
        try {
            check(!paused && !cancelled) { "Interrompu." }
            if (!work.isDirectory && !work.mkdirs())
                throw IllegalStateException("Impossible de créer le dossier temporaire privé.")
            YoutubeDL.getInstance().init(applicationContext)
            FFmpeg.getInstance().init(applicationContext)
            maybeRefreshSocialEngine(task.url)
            check(!paused && !cancelled) { "Interrompu." }

            val request = buildRequest(task.url, task.mode, task.quality, work)
            state = UiState(true, task.progress, "Téléchargement en cours…")
            YoutubeDL.getInstance().execute(request, PROCESS_ID, false) { progress, eta, _ ->
                if (!paused && !cancelled) {
                    val percent = progress.toInt().coerceIn(0, 100)
                    val message = "Téléchargement : $percent % • reste " + eta.coerceAtLeast(0) + " s"
                    state = UiState(true, percent, message)
                    val now = SystemClock.elapsedRealtime()
                    if (now - lastQueueSave > 950) {
                        lastQueueSave = now
                        DownloadQueue.update(this, task.id, progress = percent, message = message)
                    }
                    if (now - lastNotification > 1400) {
                        lastNotification = now
                        getSystemService(NotificationManager::class.java).notify(
                            NOTIFICATION_ID, notification(message, percent))
                    }
                }
            }
            check(!paused && !cancelled) { "Interrompu." }
            val category = DownloadRules.categoryFor(task.url, task.mode)
            val files = work.walkTopDown().filter { it.isFile &&
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
                        message = "En pause : reprendre pour continuer.")
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
        if (!DownloadRules.isSocialVideoHost(url)) return
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

    private fun buildRequest(url: String, mode: Int, quality: Int, work: File): YoutubeDLRequest {
        val request = YoutubeDLRequest(url)
        request.addOption("--no-mtime")
        request.addOption("--newline")
        request.addOption("--continue")
        request.addOption("--no-overwrites")
        request.addOption("--output", File(work, "%(title).150B [%(id)s].%(ext)s").absolutePath)
        CookieStore.existing(this)?.let { request.addOption("--cookies", it.absolutePath) }
        if (mode != 5 && mode != 6) request.addOption("--no-playlist")
        else request.addOption("--yes-playlist")
        when (mode) {
            1, 2, 3 -> {
                request.addOption("--extract-audio")
                request.addOption("--audio-format", when (mode) { 1 -> "mp3"; 2 -> "m4a"; else -> "flac" })
                request.addOption("--audio-quality", "0")
            }
            4 -> request.addOption("--recode-video", "gif")
            else -> {
                request.addOption("--format", DownloadRules.videoFormat(url, quality))
                request.addOption("--merge-output-format", "mp4")
            }
        }
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
        }
        return builder.build()
    }

    override fun onDestroy() {
        if (active) {
            paused = true
            YoutubeDL.getInstance().destroyProcessById(PROCESS_ID)
        }
        super.onDestroy()
    }
}
