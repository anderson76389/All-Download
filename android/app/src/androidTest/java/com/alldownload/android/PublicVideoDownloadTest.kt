package com.alldownload.android

import android.content.ContentUris
import android.content.Intent
import android.media.MediaMetadataRetriever
import android.os.Build
import android.os.Environment
import android.os.SystemClock
import android.provider.MediaStore
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

/**
 * VÉRIFICATIONS RÉSEAU FACULTATIVES (workflow dédié, non bloquant pour l'APK).
 * Ces tests dépendent d'hôtes publics tiers qui peuvent supprimer, protéger
 * ou bloquer des médias / adresses IP GitHub Actions à n'importe quel moment.
 *
 * Aucune vidéo n'est conservée après le test. Flux courts, téléchargés seulement
 * pour vérifier le moteur et la conteneurisation audio/vidéo.
 */
@RunWith(AndroidJUnit4::class)
class PublicVideoDownloadTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun externalMp4DownloadsAndExportsPlayably() {
        // Démonstration CC0 officielle de MDN.
        val url = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"
        downloadUsingAppAndVerify(url, "AUTRES", "video/mp4")
    }

    @Test fun externalWebmDownloadsAndExportsPlayably() {
        val url = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.webm"
        downloadUsingAppAndVerify(url, "AUTRES", "video/webm")
    }

    @Test fun youtubeCanDownloadShortVideoSection() {
        // Vidéo de test créée pour l'extracteur yt-dlp (l'original BaW_jenozKc a été retiré).
        downloadShortExtractedVideo("YouTube",
            "https://www.youtube.com/watch?v=DTi8wZ1a1TA",
            "bestvideo[height<=720]+bestaudio/best[height<=720]")
    }

    @Test fun twitchClipCanDownloadShortVideoSection() {
        downloadShortExtractedVideo("Twitch clip",
            "https://www.twitch.tv/aminematue/clip/ResoluteYummyDaikonBibleThump-2TAOvt5En3sdDMZm",
            "best[height<=720]/best")
    }

    @Test fun twitchVodNativeSectionCanDownload() {
        // VOD utilisée dans la documentation de la version Windows, peut expirer.
        val url = "https://www.twitch.tv/videos/2919531847"
        downloadShortExtractedVideo("Twitch VOD", url, DownloadRules.videoFormat(url, 0))
    }

    private fun downloadShortExtractedVideo(label: String, url: String, format: String) {
        val work = File(context.cacheDir, "public-video-test-${UUID.randomUUID()}").apply { mkdirs() }
        try {
            YoutubeDL.getInstance().init(context.applicationContext)
            FFmpeg.getInstance().init(context.applicationContext)
            val request = YoutubeDLRequest(url)
            request.addOption("--no-playlist")
            request.addOption("--no-mtime")
            request.addOption("--no-overwrites")
            request.addOption("--socket-timeout", "15")
            request.addOption("--retries", "1")
            request.addOption("--fragment-retries", "1")
            request.addOption("--download-sections", "*0-5")
            request.addOption("--force-keyframes-at-cuts")
            request.addOption("--format", format)
            request.addOption("--merge-output-format", "mp4")
            request.addOption("--output", File(work, "%(title).80B [%(id)s].%(ext)s").absolutePath)
            try {
                YoutubeDL.getInstance().execute(request, "network-test-${UUID.randomUUID()}", false, null)
            } catch (e: Exception) {
                fail("$label : téléchargement d'un extrait réel impossible : ${e.message}")
            }
            val media = work.walkTopDown().filter { it.isFile && it.extension.lowercase() in setOf("mp4", "webm", "mkv") }.toList()
            assertTrue("$label : pas de fichier vidéo produit.", media.isNotEmpty())
            assertTrue("$label : vidéo vide.", media.any { it.length() > 2048 })
            for (file in media) verifyPlayableVideo(label, file)
        } finally {
            work.deleteRecursively()
        }
    }

    private fun downloadUsingAppAndVerify(url: String, category: String, expectedMime: String) {
        val activity = InstrumentationRegistry.getInstrumentation().startActivitySync(
            Intent(context, MainActivity::class.java).addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            )
        ) as MainActivity
        val stamp = SystemClock.elapsedRealtime()
        try {
            val service = Intent(context, DownloadService::class.java).apply {
                action = DownloadService.ACTION_START
                putExtra(DownloadService.EXTRA_URL, url)
                putExtra(DownloadService.EXTRA_MODE, 0)
                putExtra(DownloadService.EXTRA_QUALITY, 0)
            }
            if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(service)
            else context.startService(service)
            val deadline = SystemClock.elapsedRealtime() + 120_000
            var started = false
            while (SystemClock.elapsedRealtime() < deadline) {
                val st = DownloadService.state
                if (st.busy) started = true
                if (started && !st.busy) break
                SystemClock.sleep(350)
            }
            assertTrue("$url : service non démarré.", started)
            val state = DownloadService.state
            assertFalse("$url : service bloqué. ${state.message}", state.busy)
            assertTrue("$url : erreur de téléchargement : ${state.message}",
                state.message.contains("fichier(s)"))
            if (Build.VERSION.SDK_INT >= 29) {
                val ids = mutableListOf<android.net.Uri>()
                context.contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                    arrayOf(MediaStore.MediaColumns._ID, MediaStore.MediaColumns.MIME_TYPE,
                        MediaStore.MediaColumns.DATE_ADDED, MediaStore.MediaColumns.RELATIVE_PATH),
                    "${MediaStore.MediaColumns.RELATIVE_PATH}=?",
                    arrayOf("${Environment.DIRECTORY_DOWNLOADS}/All-Download/$category/"), null
                )?.use { cursor ->
                    val nowSeconds = System.currentTimeMillis() / 1000
                    while (cursor.moveToNext()) {
                        // Tests exécutés sur un émulateur neuf, aucune donnée utilisateur.
                        val ageSeconds = nowSeconds - cursor.getLong(2)
                        if (ageSeconds in 0..300) {
                            val uri = ContentUris.withAppendedId(
                                MediaStore.Downloads.EXTERNAL_CONTENT_URI, cursor.getLong(0))
                            val mime = cursor.getString(1)
                            if (mime == expectedMime) ids.add(uri)
                        }
                    }
                }
                assertTrue("$url : aucun média exporté dans All-Download/$category", ids.isNotEmpty())
                for (uri in ids) {
                    try {
                        val probeFile = File(context.cacheDir, "probe-${UUID.randomUUID()}")
                        context.contentResolver.openInputStream(uri)!!.use { input ->
                            probeFile.outputStream().use { input.copyTo(it) }
                        }
                        try { verifyPlayableVideo(url, probeFile) }
                        finally { probeFile.delete() }
                    } finally {
                        context.contentResolver.delete(uri, null, null)
                    }
                }
            } else {
                fail("Ce workflow externe ne couvre que Android 10+.")
            }
        } finally {
            InstrumentationRegistry.getInstrumentation().runOnMainSync { activity.finish() }
            if (DownloadService.state.busy) {
                context.startService(Intent(context, DownloadService::class.java)
                    .setAction(DownloadService.ACTION_CANCEL))
            }
        }
    }

    private fun verifyPlayableVideo(label: String, file: File) {
        assertTrue("$label : taille trop faible : ${file.length()}", file.length() > 2048)
        val meta = MediaMetadataRetriever()
        try {
            meta.setDataSource(file.absolutePath)
            val width = meta.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)
                ?.toIntOrNull() ?: 0
            val height = meta.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)
                ?.toIntOrNull() ?: 0
            assertTrue("$label : vidéo illisible sur Android (dimensions $width x $height)", width > 0 && height > 0)
        } finally {
            meta.release()
        }
    }
}
