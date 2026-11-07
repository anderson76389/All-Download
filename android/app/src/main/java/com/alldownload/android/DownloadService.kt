package com.alldownload.android

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
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
            val category = categoryFor(url, mode)
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
            val msg = if (cancelled) "Téléchargement annulé." else {
                "Échec : ${(e.localizedMessage ?: e.javaClass.simpleName).take(180)}"
            }
            state = UiState(false, 0, msg)
            if (cancelled) work.deleteRecursively()
            // En cas d'échec d'export, conserver les fichiers privés non exportés pour éviter leur perte.
        } finally {
            active = false
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelfResult(startId)
        }
    }

    private fun buildRequest(url: String, mode: Int, quality: Int, work: File): YoutubeDLRequest {
        val request = YoutubeDLRequest(url)
        request.addOption("--no-mtime")
        request.addOption("--newline")
        request.addOption("--no-overwrites")
        request.addOption("--output", File(work, "%(title).150B [%(id)s].%(ext)s").absolutePath)

        if (mode != 5 && mode != 6) request.addOption("--no-playlist")
        else request.addOption("--yes-playlist")

        val isTwitch = twitchVod(url) && mode == 0
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
                val format = if (isTwitch) when (quality) {
                    1 -> "bestvideo[height=720]+bestaudio/best[height=720]"
                    2 -> "bestvideo[height=480]+bestaudio/best[height=480]"
                    else -> "bestvideo[height=1080]+bestaudio/best[height=1080]/bestvideo[height=720]+bestaudio/best[height=720]"
                } else when (quality) {
                    1 -> "bestvideo[height<=720]+bestaudio/best[height<=720]"
                    2 -> "bestvideo[height<=480]+bestaudio/best[height<=480]"
                    3 -> "bestvideo+bestaudio/best"
                    4 -> "bestvideo[height<=2160]+bestaudio/best[height<=2160]"
                    else -> "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
                }
                request.addOption("--format", format)
                request.addOption("--merge-output-format", "mp4")
            }
        }
        return request
    }

    private fun twitchVod(url: String): Boolean {
        val uri = Uri.parse(url)
        val host = uri.host?.lowercase().orEmpty()
        return host in setOf("twitch.tv", "www.twitch.tv", "m.twitch.tv") &&
            Regex("^/videos/[0-9]{5,20}/?$").matches(uri.path.orEmpty())
    }

    private fun categoryFor(url: String, mode: Int): String {
        if (mode == 5) return "PLAYLIST"
        if (mode == 6) return "CHAÎNES"
        if (mode in 1..3) return "AUDIOS"
        if (mode == 4) return "GIFS"
        if (twitchVod(url)) return "TWITCH"
        val host = Uri.parse(url).host?.lowercase().orEmpty()
        return if (host == "youtu.be" || host == "youtube.com" ||
            host.endsWith(".youtube.com")) "VIDÉOS" else "AUTRES"
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
