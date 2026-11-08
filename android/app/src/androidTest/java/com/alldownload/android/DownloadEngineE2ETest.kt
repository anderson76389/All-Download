package com.alldownload.android

import android.content.ContentUris
import android.content.Intent
import android.os.Build
import android.os.Environment
import android.os.SystemClock
import android.provider.MediaStore
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.sin

/**
 * Téléchargement bout en bout : un petit WAV est servi localement par HTTP.
 * yt-dlp le télécharge, FFmpeg le convertit en MP3, puis l'app publie le fichier.
 * Aucun site tiers, compte ou contenu protégé requis.
 */
@RunWith(AndroidJUnit4::class)
class DownloadEngineE2ETest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun downloadsConvertsAndExportsLocalAudio() {
        if (Build.VERSION.SDK_INT in 23..28) {
            InstrumentationRegistry.getInstrumentation().uiAutomation.grantRuntimePermission(
                context.packageName, android.Manifest.permission.WRITE_EXTERNAL_STORAGE
            )
        }
        val activity = InstrumentationRegistry.getInstrumentation().startActivitySync(
            Intent(context, MainActivity::class.java).addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            )
        ) as MainActivity
        val name = "all-download-ci-${UUID.randomUUID()}"
        val bytes = wavSamples()
        val listening = AtomicBoolean(true)
        val server = ServerSocket(0, 8, InetAddress.getByName("127.0.0.1"))
        server.soTimeout = 800
        val worker = Thread {
            while (listening.get()) {
                try {
                    server.accept().use { socket -> handle(socket, name, bytes) }
                } catch (_: SocketTimeoutException) {
                    // Continue tant que le test télécharge.
                } catch (_: Exception) {
                    if (!listening.get()) break
                }
            }
        }
        worker.isDaemon = true
        worker.start()

        try {
            val service = Intent(context, DownloadService::class.java).apply {
                action = DownloadService.ACTION_START
                putExtra(DownloadService.EXTRA_URL,
                    "http://127.0.0.1:${server.localPort}/$name.wav")
                putExtra(DownloadService.EXTRA_MODE, 1) // AUDIO MP3
                putExtra(DownloadService.EXTRA_QUALITY, 0)
            }
            if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(service)
            else context.startService(service)
            val until = SystemClock.elapsedRealtime() + 150_000
            var started = false
            while (SystemClock.elapsedRealtime() < until) {
                val state = DownloadService.state
                if (state.busy) started = true
                if (started && !state.busy) break
                SystemClock.sleep(350)
            }
            assertTrue("Le service de téléchargement n'a pas démarré.", started)
            val last = DownloadService.state
            assertFalse("Service non terminé après 150 secondes : ${last.message}", last.busy)
            assertTrue("Erreur yt-dlp/FFmpeg/export : ${last.message}",
                last.message.contains("fichier(s)"))
            if (Build.VERSION.SDK_INT >= 29) {
                val uri = findOutput(name)
                assertNotNull("MP3 introuvable dans Téléchargements/All-Download/AUDIOS", uri)
                try {
                    val length = context.contentResolver.openInputStream(uri!!)!!.use { it.readBytes().size }
                    assertTrue("MP3 vide ou corrompu", length > 1000)
                } finally {
                    if (uri != null) context.contentResolver.delete(uri, null, null)
                }
            } else {
                @Suppress("DEPRECATION")
                val dir = File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS), "All-Download/AUDIOS")
                val mp3 = dir.listFiles()?.firstOrNull { it.name.startsWith(name) && it.name.endsWith(".mp3") }
                assertNotNull("MP3 absent du dossier public", mp3)
                assertTrue("MP3 vide", mp3!!.length() > 1000)
                mp3.delete()
            }
        } finally {
            InstrumentationRegistry.getInstrumentation().runOnMainSync { activity.finish() }
            listening.set(false)
            server.close()
            worker.join(2500)
            if (DownloadService.state.busy) {
                context.startService(Intent(context, DownloadService::class.java)
                    .setAction(DownloadService.ACTION_CANCEL))
            }
        }
    }

    private fun findOutput(prefix: String): android.net.Uri? {
        val projection = arrayOf(MediaStore.MediaColumns._ID, MediaStore.MediaColumns.DISPLAY_NAME)
        context.contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI,
            projection, "${MediaStore.MediaColumns.DISPLAY_NAME} LIKE ?",
            arrayOf("$prefix%.mp3"), null)?.use { c ->
            if (c.moveToFirst()) return ContentUris.withAppendedId(
                MediaStore.Downloads.EXTERNAL_CONTENT_URI, c.getLong(0))
        }
        return null
    }

    private fun handle(socket: Socket, name: String, payload: ByteArray) {
        socket.soTimeout = 8000
        val reader = BufferedReader(InputStreamReader(socket.getInputStream(), Charsets.ISO_8859_1))
        val first = reader.readLine() ?: return
        while (true) {
            val line = reader.readLine() ?: break
            if (line.isEmpty()) break
        }
        val headers = (
            "HTTP/1.1 200 OK\r\n" +
            "Content-Type: audio/wav\r\n" +
            "Content-Disposition: attachment; filename=\"$name.wav\"\r\n" +
            "Content-Length: ${payload.size}\r\n" +
            "Connection: close\r\n\r\n"
        ).toByteArray(Charsets.ISO_8859_1)
        val out = socket.getOutputStream()
        out.write(headers)
        if (!first.startsWith("HEAD ")) out.write(payload)
        out.flush()
    }

    private fun wavSamples(): ByteArray {
        val sampleRate = 8000
        val samples = 8000
        val bodySize = samples * 2
        val w = ByteBuffer.allocate(44 + bodySize).order(ByteOrder.LITTLE_ENDIAN)
        w.put("RIFF".toByteArray(Charsets.US_ASCII))
        w.putInt(36 + bodySize)
        w.put("WAVE".toByteArray(Charsets.US_ASCII))
        w.put("fmt ".toByteArray(Charsets.US_ASCII))
        w.putInt(16)
        w.putShort(1) // PCM
        w.putShort(1) // mono
        w.putInt(sampleRate)
        w.putInt(sampleRate * 2)
        w.putShort(2)
        w.putShort(16)
        w.put("data".toByteArray(Charsets.US_ASCII))
        w.putInt(bodySize)
        for (i in 0 until samples) {
            w.putShort((sin(i * 440.0 * 2.0 * Math.PI / sampleRate) * 8000).toInt().toShort())
        }
        return w.array()
    }
}
