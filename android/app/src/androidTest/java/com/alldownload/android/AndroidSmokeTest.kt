package com.alldownload.android

import android.Manifest
import android.content.Intent
import android.graphics.Color
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.widget.EditText
import android.widget.Spinner
import android.widget.TextView
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.ByteArrayInputStream
import java.io.File
import java.io.IOException
import java.util.UUID

/** Vérifie l'installation, le démarrage, l'interface et le stockage public sur un Android réel/émulé. */
@RunWith(AndroidJUnit4::class)
class AndroidSmokeTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext

    @Test fun appLaunchesAndShowsReadableModes() {
        val intent = Intent(context, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        val activity = instrumentation.startActivitySync(intent) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val mode = activity.findViewById<Spinner>(R.id.modeSpinner)
            val quality = activity.findViewById<Spinner>(R.id.qualitySpinner)
            assertEquals(7, mode.count)
            assertEquals(5, quality.count)
            assertEquals(0, quality.selectedItemPosition)
            assertEquals("Vidéo", mode.selectedItem.toString())
            // Évite le bug texte noir sur fond sombre de la première bêta.
            val selected = mode.selectedView as TextView
            assertTrue("Texte des modes illisible en thème sombre",
                Color.luminance(selected.currentTextColor) > 0.5)
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun sharedUrlIsPastedAutomatically() {
        val intent = Intent(context, MainActivity::class.java).apply {
            action = Intent.ACTION_SEND
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, "Découvrez cette vidéo https://youtu.be/test123456")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        }
        val activity = instrumentation.startActivitySync(intent) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            assertEquals("https://youtu.be/test123456",
                activity.findViewById<EditText>(R.id.urlInput).text.toString())
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun exportsFileToCorrectAllDownloadFolderWithoutRewritingBytes() {
        grantLegacyStorage()
        assertLegacyFolderWritable()
        val fileName = "all-download-smoke-${UUID.randomUUID()}.mp4"
        val payload = ByteArray(128 * 1024) { (it % 239).toByte() }
        val source = File(context.cacheDir, fileName)
        source.writeBytes(payload)
        try {
            MediaExporter.export(context, source, "TWITCH") { false }
            if (Build.VERSION.SDK_INT >= 29) {
                val file = findMediaStore(fileName)
                assertNotNull("Fichier absent de Downloads/All-Download/TWITCH", file)
                val (uri, relPath) = file!!
                try {
                    assertEquals("Download/All-Download/TWITCH/", relPath)
                    val copied = context.contentResolver.openInputStream(uri)!!.use { it.readBytes() }
                    assertArrayEquals(payload, copied)
                } finally {
                    context.contentResolver.delete(uri, null, null)
                }
            } else {
                @Suppress("DEPRECATION")
                val destination = File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS), "All-Download/TWITCH/$fileName")
                try {
                    assertTrue(destination.isFile)
                    assertArrayEquals(payload, destination.readBytes())
                } finally {
                    destination.delete()
                }
            }
        } finally {
            source.delete()
        }
    }

    @Test fun cancelledExportDoesNotLeavePartialPublicFile() {
        grantLegacyStorage()
        assertLegacyFolderWritable()
        val fileName = "all-download-cancel-${UUID.randomUUID()}.mp4"
        val source = File(context.cacheDir, fileName)
        source.writeBytes(ByteArray(512 * 1024) { 67 })
        var checks = 0
        try {
            try {
                MediaExporter.export(context, source, "VIDÉOS") { ++checks >= 4 }
                fail("La copie devait être interrompue.")
            } catch (expected: IOException) {
                assertTrue(expected.message.orEmpty().contains("Annulation"))
            }
            if (Build.VERSION.SDK_INT >= 29) {
                val orphan = findMediaStore(fileName)
                if (orphan != null) context.contentResolver.delete(orphan.first, null, null)
                assertNull("Fichier partiel publié malgré l'annulation", orphan)
            } else {
                @Suppress("DEPRECATION")
                val orphan = File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS), "All-Download/VIDÉOS/$fileName")
                assertFalse("Fichier partiel conservé malgré l'annulation", orphan.exists())
                orphan.delete()
            }
        } finally {
            source.delete()
        }
    }

    @Test fun cookieFileIsPrivateValidatedAndCanBeDeleted() {
        CookieStore.delete(context)
        val source = "# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tTRUE\t1999999999\tsession\tCI-dummy-cookie\n"
        try {
            CookieStore.importFromStream(context,
                ByteArrayInputStream(source.toByteArray(Charsets.UTF_8)))
            val cookies = CookieStore.existing(context)
            assertNotNull("Cookies absents de l'espace privé.", cookies)
            assertTrue(cookies!!.canonicalPath.startsWith(context.filesDir.canonicalPath + "/"))
            assertEquals(source, cookies.readText())
            try {
                CookieStore.importFromStream(context,
                    ByteArrayInputStream("garbage cookie value".toByteArray()))
                fail("Un fichier non Netscape devait être rejeté.")
            } catch (expected: IOException) {
                assertTrue(expected.message.orEmpty().contains("Netscape"))
            }
            assertEquals("L'ancien cookie ne doit pas être écrasé en cas d'erreur.",
                source, CookieStore.file(context).readText())
            assertTrue(CookieStore.delete(context))
            assertNull("Cookies présents après suppression.", CookieStore.existing(context))
        } finally {
            CookieStore.delete(context)
        }
    }

    private fun assertLegacyFolderWritable() {
        if (Build.VERSION.SDK_INT > 28) return
        @Suppress("DEPRECATION")
        val root = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
        val permission = context.checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE)
        val message = "Android ${Build.VERSION.SDK_INT}: permission=$permission, " +
            "state=${Environment.getExternalStorageState()}, root=${root.absolutePath}, " +
            "exists=${root.exists()}, writable=${root.canWrite()}, parent=${root.parentFile?.canWrite()}"
        assertTrue(message, root.isDirectory || root.mkdirs())
        val probe = File(root, ".alldownload-test-${UUID.randomUUID()}")
        assertTrue(message + ", testFileCreate=false", probe.createNewFile())
        probe.delete()
    }

    private fun grantLegacyStorage() {
        if (Build.VERSION.SDK_INT in 23..28 &&
            context.checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) !=
                android.content.pm.PackageManager.PERMISSION_GRANTED) {
            instrumentation.uiAutomation.grantRuntimePermission(context.packageName,
                Manifest.permission.WRITE_EXTERNAL_STORAGE)
        }
    }

    private fun findMediaStore(displayName: String): Pair<android.net.Uri, String>? {
        if (Build.VERSION.SDK_INT < 29) return null
        val columns = arrayOf(
            MediaStore.MediaColumns._ID,
            MediaStore.MediaColumns.RELATIVE_PATH
        )
        context.contentResolver.query(
            MediaStore.Downloads.EXTERNAL_CONTENT_URI, columns,
            "${MediaStore.MediaColumns.DISPLAY_NAME}=?",
            arrayOf(displayName), null
        )?.use { cursor ->
            if (!cursor.moveToFirst()) return null
            val uri = android.content.ContentUris.withAppendedId(
                MediaStore.Downloads.EXTERNAL_CONTENT_URI, cursor.getLong(0)
            )
            return uri to cursor.getString(1)
        }
        return null
    }
}
