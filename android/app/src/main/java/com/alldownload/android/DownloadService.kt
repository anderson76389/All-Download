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
import java.util.UUID

/**
 * Le moteur Android est indépendant du moteur Windows : aucun EXE, WebView2 ou CLI Windows.
 * Télécharge en espace privé, puis exporte vers le dossier public avec MediaStore.
 */
class DownloadService : Service() {
    data class UiState(val busy: Boolean, val progress: Int, val message: String)
    companion object {
        const val ACTION_START = "com.alldownload.android.START"
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
    @Volatile private var active = false
    private var lastNotification = 0L

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        if (Build.VERSION.SDK_INT >= 26) {
            getSystemService(NotificationManager::class.java).createNotificationChannel(
                NotificationChannel(CHANNEL, "Téléchargements All-Download", NotificationManager.IMPORTANCE_LOW)
            )
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_CANCEL -> {
                cancelled = true
                state = state.copy(message = "Annulation en cours…")
                YoutubeDL.getInstance().destroyProcessById(PROCESS_ID)
            }
            ACTION_START -> {
                if (active) return START_NOT_STICKY
                val url = intent.getStringExtra(EXTRA_URL).orEmpty()
                val mode = intent.getIntExtra(EXTRA_MODE, 0).coerceIn(0, 6)
                val quality = intent.getIntExtra(EXTRA_QUALITY, 0).coerceIn(0, 4)
                if (url.isBlank()) {
                    state = UiState(false, 0, "Lien manquant.")
                    stopSelfResult(startId)
                    return START_NOT_STICKY
                }
                active = true
                cancelled = false
                state = UiState(true, 0, "Initialisation du moteur Android…")
                startForeground(NOTIFICATION_ID, notification("Téléchargement en préparation", 0))
                Thread({ download(url, mode, quality, startId) }, "all-download-worker").start()
            }
        }
        return START_NOT_STICKY
    }

    private fun download(url: String, mode: Int, quality: Int, startId: Int) {
        val parent = getExternalFilesDir(null) ?: filesDir
        val work = File(parent, "All-Download/Donnees/temporaires/${UUID.randomUUID()}")
        var exported = 0
        try {
            check(!cancelled) { "Téléchargement annulé." }
            check(work.mkdirs() && work.isDirectory) { "Impossible de créer l'espace temporaire." }
            YoutubeDL.getInstance().init(applicationContext)
            FFmpeg.getInstance().init(applicationContext)
            maybeRefreshSocialEngine(url)
            check(!cancelled) { "Téléchargement annulé." }

            val request = buildRequest(url, mode, quality, work)
            state = UiState(true, 0, "Téléchargement en cours…")
            YoutubeDL.getInstance().execute(request, PROCESS_ID, false) { progress, eta, _ ->
                if (!cancelled) {
                    val percent = progress.toInt().coerceIn(0, 100)
                    state = UiState(true, percent, "Téléchargement : $percent % • reste ${eta.coerceAtLeast(0)} s")
                    val now = SystemClock.elapsedRealtime()
                    if (now - lastNotification > 1400) {
                        lastNotification = now
                        getSystemService(NotificationManager::class.java)
                            .notify(NOTIFICATION_ID, notification("Téléchargement : $percent %", percent))
                    }
                }
            }

            check(!cancelled) { "Téléchargement annulé." }
            val category = DownloadRules.categoryFor(url, mode)
            val files = work.walkTopDown().filter { it.isFile && !it.name.endsWith(".part") &&
                !it.name.endsWith(".ytdl") }.toList()
            check(files.isNotEmpty()) { "Aucun fichier final créé par le moteur." }
            for ((index, file) in files.withIndex()) {
                check(!cancelled) { "Téléchargement annulé." }
                state = UiState(true, 100, "Enregistrement : ${index + 1}/${files.size}")
                MediaExporter.export(this, file, category) { cancelled }
                exported++
            }
            state = UiState(false, 100, "$exported fichier(s) dans Téléchargements/All-Download/$category")
            work.deleteRecursively()
            getSystemService(NotificationManager::class.java)
                .notify(NOTIFICATION_ID, notification("Téléchargement terminé ($exported fichier(s))", 100, false))
        } catch (e: Exception) {
            if (!cancelled) Log.e("AllDownloadVideo", "Échec du téléchargement $url", e)
            val msg = if (cancelled) "Téléchargement annulé." else {
                "Échec : ${errorSummary(e)}"
            }
            state = UiState(false, 0, msg)
            if (cancelled) {
                work.deleteRecursively()
                getSystemService(NotificationManager::class.java).cancel(NOTIFICATION_ID)
            } else {
                getSystemService(NotificationManager::class.java)
                    .notify(NOTIFICATION_ID, notification("Téléchargement échoué", 0, false))
            }
            // En cas d'échec d'export, conserver les fichiers privés non exportés pour éviter leur perte.
        } finally {
            active = false
            // Garde le message de fin dans les notifications, sans service permanent.
            stopForeground(if (cancelled) STOP_FOREGROUND_REMOVE else STOP_FOREGROUND_DETACH)
            stopSelfResult(startId)
        }
    }

    /**
     * Les avertissements d'une version yt-dlp ancienne précèdent parfois l'erreur
     * réelle, qui doit être visible à l'écran au lieu d'être tronquée.
     */
    /**
     * Les extracteurs sociaux évoluent fréquemment. Vérifie la dernière version
     * officielle de yt-dlp au premier téléchargement social, puis au plus une
     * fois par semaine. Si GitHub est inaccessible, le moteur embarqué reste
     * utilisable : aucune dépendance obligatoire ni serveur intermédiaire.
     *
     * Le moteur Twitch historique n'est pas modifié.
     */
    private fun maybeRefreshSocialEngine(url: String) {
        if (!DownloadRules.isSocialVideoHost(url)) return
        val prefs = getSharedPreferences("yt_dlp_updates", MODE_PRIVATE)
        val now = System.currentTimeMillis()
        val previous = prefs.getLong("last_attempt_ms", 0L)
        val oneWeekMs = 7L * 24 * 60 * 60 * 1000
        if (previous > 0 && now - previous in 0 until oneWeekMs) return
        prefs.edit().putLong("last_attempt_ms", now).apply()
        state = UiState(true, 0, "Actualisation du moteur yt-dlp…")
        try {
            val result = YoutubeDL.getInstance().updateYoutubeDL(applicationContext)
            Log.i("AllDownloadVideo", "yt-dlp : $result")
        } catch (e: Exception) {
            Log.w("AllDownloadVideo",
                "Mise à jour yt-dlp indisponible, conservation du moteur embarqué.", e)
        }
    }

    private fun errorSummary(error: Throwable): String {
        val lines = (error.localizedMessage ?: error.javaClass.simpleName)
            .lines().map { it.trim() }.filter { it.isNotBlank() }
        val meaningful = lines.lastOrNull { it.startsWith("ERROR:", ignoreCase = true) }
            ?: lines.lastOrNull { !it.startsWith("WARNING:", ignoreCase = true) }
            ?: lines.lastOrNull()
            ?: error.javaClass.simpleName
        return meaningful.take(280)
    }

    private fun buildRequest(url: String, mode: Int, quality: Int, work: File): YoutubeDLRequest {
        val request = YoutubeDLRequest(url)
        request.addOption("--no-mtime")
        request.addOption("--newline")
        request.addOption("--no-overwrites")
        request.addOption("--output", File(work, "%(title).150B [%(id)s].%(ext)s").absolutePath)

        if (mode != 5 && mode != 6) request.addOption("--no-playlist")
        else request.addOption("--yes-playlist")

        when (mode) {
            1, 2, 3 -> {
                request.addOption("--extract-audio")
                request.addOption("--audio-format", when (mode) { 1 -> "mp3"; 2 -> "m4a"; else -> "flac" })
                request.addOption("--audio-quality", "0")
            }
            4 -> {
                request.addOption("--recode-video", "gif")
            }
            else -> {
                val format = DownloadRules.videoFormat(url, quality)
                request.addOption("--format", format)
                request.addOption("--merge-output-format", "mp4")
            }
        }
        return request
    }

    private fun notification(message: String, progress: Int, ongoing: Boolean = true): Notification {
        val managerIntent = Intent(this, MainActivity::class.java)
        val contentIntent = PendingIntent.getActivity(
            this, 0, managerIntent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val builder = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, CHANNEL)
                      else Notification.Builder(this)
        builder.setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle("All-Download")
            .setContentText(message)
            .setContentIntent(contentIntent)
            .setOnlyAlertOnce(true)
            .setOngoing(ongoing)
            .setProgress(100, progress, progress == 0 && ongoing)
        if (ongoing) {
            val cancelIntent = Intent(this, DownloadService::class.java).setAction(ACTION_CANCEL)
            val pending = PendingIntent.getService(
                this, 1, cancelIntent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            builder.addAction(android.R.drawable.ic_menu_close_clear_cancel, "Annuler", pending)
        }
        return builder.build()
    }

    override fun onDestroy() {
        if (active) {
            cancelled = true
            YoutubeDL.getInstance().destroyProcessById(PROCESS_ID)
        }
        super.onDestroy()
    }
}
