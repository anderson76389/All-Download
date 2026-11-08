package com.alldownload.android

import android.Manifest
import android.content.Intent
import android.graphics.Color
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.view.View
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
            assertNull("Les paramètres avancés ne doivent pas être construits au démarrage.",
                activity.findViewById<View>(R.id.settingsTabs))
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
            assertTrue(cookies!!.canonicalPath.startsWith(context.noBackupFilesDir.canonicalPath + "/"))
            assertEquals(source, cookies.readText())
            val replaced = source.replace("CI-dummy-cookie", "CI-replaced-cookie")
            CookieStore.importFromStream(context,
                ByteArrayInputStream(replaced.toByteArray(Charsets.UTF_8)))
            assertEquals("L'import d'une nouvelle session doit remplacer l'ancienne.",
                replaced, CookieStore.file(context).readText())
            try {
                CookieStore.importFromStream(context,
                    ByteArrayInputStream("garbage cookie value".toByteArray()))
                fail("Un fichier non Netscape devait être rejeté.")
            } catch (expected: IOException) {
                assertTrue(expected.message.orEmpty().contains("Netscape"))
            }
            assertEquals("L'ancien cookie ne doit pas être écrasé en cas d'erreur.",
                replaced, CookieStore.file(context).readText())
            assertTrue(CookieStore.delete(context))
            assertNull("Cookies présents après suppression.", CookieStore.existing(context))
        } finally {
            CookieStore.delete(context)
        }
    }


    @Test fun windowsInspiredResponsiveShellKeepsWorkingControls() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val options = activity.findViewById<LinearLayout>(R.id.downloadOptions)
            val footer = activity.findViewById<LinearLayout>(R.id.statusFooterCard)
            val home = activity.findViewById<LinearLayout>(R.id.homePage)
            val nav = activity.findViewById<LinearLayout>(R.id.navigation)
            val mode = activity.findViewById<Spinner>(R.id.modeSpinner)
            assertNotNull("Barre d'options de Windows absente", options)
            assertNotNull("Barre d'état/progression absente", footer)
            assertNotNull(activity.findViewById<Button>(R.id.queueButton))
            assertNotNull(activity.findViewById<Button>(R.id.startButton))
            assertNotNull(activity.findViewById<Button>(R.id.cancelButton))
            val wide = activity.resources.configuration.screenWidthDp >= 720
            if (wide) {
                assertSame("La barre d'état doit rester dans la page sur tablette",
                    home, footer.parent)
                assertEquals(LinearLayout.HORIZONTAL, options.orientation)
                assertEquals(LinearLayout.VERTICAL, nav.orientation)
            } else {
                val navBar = nav.parent as View
                assertSame("Navigation et statut doivent être épinglés au même écran",
                    footer.parent, navBar.parent)
                assertNotSame("La barre d'état ne doit pas scroller sur téléphone",
                    home, footer.parent)
                assertEquals(LinearLayout.HORIZONTAL, nav.orientation)
                assertTrue("Le contenu doit rester affiché au-dessus de la navigation",
                    activity.findViewById<View>(R.id.scroll).parent === footer.parent)
            }
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.quickAudioButton).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(1, mode.selectedItemPosition)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.quickPlaylistButton).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(5, mode.selectedItemPosition)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navQueue).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(View.VISIBLE, activity.findViewById<View>(R.id.queuePage).visibility)
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun originalBrandAndFourNativeTabsAreFunctional() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            assertEquals("All-Download",
                context.packageManager.getApplicationLabel(context.applicationInfo).toString())
            assertNotNull("Icône Android absente.",
                context.packageManager.getApplicationIcon(context.packageName))
            assertNotNull("Logo Windows absent de l'interface Android.",
                activity.findViewById<ImageView>(R.id.brandLogo).drawable)
            assertEquals("ALL-DOWNLOAD",
                activity.findViewById<TextView>(R.id.brandTitle).text.toString())
            assertNotNull(activity.findViewById<LinearLayout>(R.id.homeQueuePreview))
            assertNotNull(activity.findViewById<Button>(R.id.pasteUrlButton))
            assertNotNull(activity.findViewById<Button>(R.id.quickGifButton))
            assertNotNull(activity.findViewById<Button>(R.id.quickPlaylistButton))
            assertNotNull(activity.findViewById<Button>(R.id.quickTwitchButton))
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navQueue).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(View.VISIBLE, activity.findViewById<View>(R.id.queuePage).visibility)
            assertEquals(View.GONE, activity.findViewById<View>(R.id.homePage).visibility)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navFiles).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(View.VISIBLE, activity.findViewById<View>(R.id.filesPage).visibility)
            val files = activity.findViewById<LinearLayout>(R.id.filesList)
            val deadline = android.os.SystemClock.uptimeMillis() + 7000
            while (files.childCount < 7 &&
                android.os.SystemClock.uptimeMillis() < deadline) {
                android.os.SystemClock.sleep(100)
                instrumentation.waitForIdleSync()
            }
            assertTrue("Les sept catégories de fichiers doivent être visibles.",
                files.childCount >= 7)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navSettings).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(View.VISIBLE,
                activity.findViewById<View>(R.id.settingsPage).visibility)
            assertEquals(3, activity.findViewById<Spinner>(R.id.themeSpinner).count)
            val wide = activity.resources.configuration.screenWidthDp >= 720
            val navOrientation = activity.findViewById<LinearLayout>(R.id.navigation).orientation
            assertEquals("La navigation doit devenir une barre latérale sur tablette.",
                if (wide) LinearLayout.VERTICAL else LinearLayout.HORIZONTAL,
                navOrientation)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navHome).performClick()
                activity.findViewById<Button>(R.id.quickAudioButton).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(1, activity.findViewById<Spinner>(R.id.modeSpinner)
                .selectedItemPosition)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.quickVideoButton).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(0, activity.findViewById<Spinner>(R.id.modeSpinner)
                .selectedItemPosition)
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun queueCleanupNeverDeletesRunningTasks() {
        val base = "https://example.org/alldownload-queue-" + UUID.randomUUID()
        val waiting = DownloadQueue.enqueue(context, "$base-waiting.mp4", 0, 0)
        val failed = DownloadQueue.enqueue(context, "$base-failed.mp4", 0, 0)
        val running = DownloadQueue.enqueue(context, "$base-running.mp4", 0, 0)
        try {
            DownloadQueue.update(context, failed.id, DownloadQueue.ERROR)
            DownloadQueue.update(context, running.id, DownloadQueue.RUNNING)
            assertEquals(1, DownloadQueue.clearStatuses(context, setOf(DownloadQueue.ERROR)))
            assertEquals(1, DownloadQueue.clearStatuses(context, setOf(DownloadQueue.WAITING)))
            assertEquals(0, DownloadQueue.clearStatuses(context, setOf(DownloadQueue.RUNNING)))
            assertTrue(DownloadQueue.snapshot(context).any { it.id == running.id })
        } finally {
            DownloadQueue.update(context, running.id, DownloadQueue.ERROR)
            listOf(waiting, failed, running).forEach { DownloadQueue.remove(context, it.id) }
        }
    }

    @Test fun queueSurvivesStorageReloadAndPauseResumeStates() {
        val uniqueUrl = "https://example.com/all-download-test-" +
            UUID.randomUUID().toString() + ".mp4"
        val task = DownloadQueue.enqueue(context, uniqueUrl, 0, 0)
        try {
            val existing = DownloadQueue.snapshot(context).find { it.id == task.id }
            assertNotNull("Tâche absente de la file persistante.", existing)
            assertEquals(DownloadQueue.WAITING, existing!!.status)
            assertTrue("La file n'a pas été sauvée sur stockage privé.",
                context.getSharedPreferences("all_download_queue_v1",
                    android.content.Context.MODE_PRIVATE)
                    .getString("tasks", "").orEmpty().contains(task.id))
            DownloadQueue.update(context, task.id, DownloadQueue.PAUSED, 37,
                "Pause utilisateur")
            val paused = DownloadQueue.snapshot(context).find { it.id == task.id }
            assertEquals(DownloadQueue.PAUSED, paused?.status)
            assertEquals(37, paused?.progress)
            DownloadQueue.resumePaused(context)
            assertEquals(DownloadQueue.WAITING,
                DownloadQueue.snapshot(context).find { it.id == task.id }?.status)
            DownloadQueue.update(context, task.id, DownloadQueue.RUNNING)
            DownloadQueue.recoverInterrupted(context)
            assertEquals("Une tâche interrompue doit être relançable.",
                DownloadQueue.WAITING,
                DownloadQueue.snapshot(context).find { it.id == task.id }?.status)
            DownloadQueue.update(context, task.id, DownloadQueue.ERROR)
            DownloadQueue.retry(context, task.id)
            assertEquals(DownloadQueue.WAITING,
                DownloadQueue.snapshot(context).find { it.id == task.id }?.status)
        } finally {
            DownloadQueue.update(context, task.id, DownloadQueue.ERROR)
            DownloadQueue.remove(context, task.id)
        }
        assertTrue(DownloadQueue.snapshot(context).none { it.id == task.id })
    }

    @Test fun androidReleaseChecksDoNotConfuseWindowsAndCompareVersionsProperly() {
        assertTrue(AndroidUpdates.compareVersions("0.10.0-beta", "0.9.99-beta") > 0)
        assertTrue(AndroidUpdates.compareVersions("0.3.1-beta", "0.3.0-beta") > 0)
        assertEquals(0, AndroidUpdates.compareVersions("0.3.0-beta", "0.3.0-beta"))
        assertTrue(AndroidUpdates.compareVersions("0.2.9-beta", "0.3.0-beta") < 0)
        val releases = org.json.JSONArray()
        releases.put(org.json.JSONObject().apply {
            put("tag_name", "build-999")
            put("html_url", "https://github.com/anderson76389/All-Download/releases/tag/build-999")
            put("assets", org.json.JSONArray().put(org.json.JSONObject().apply {
                put("name", "All-Download-Portable-Windows.zip")
                put("size", 45000000)
            }))
        })
        fun androidRelease(version: String, draft: Boolean = false) =
            org.json.JSONObject().apply {
                val tag = "android-v" + version
                put("tag_name", tag)
                put("draft", draft)
                put("name", "All-Download Android " + version)
                put("html_url", "https://github.com/anderson76389/All-Download/releases/tag/" + tag)
                put("body", "Nouveaux réglages Android")
                put("assets", org.json.JSONArray().put(org.json.JSONObject().apply {
                    put("name", "All-Download-Android-" + version + ".apk")
                    put("browser_download_url",
                        "https://github.com/anderson76389/All-Download/releases/download/" +
                            tag + "/All-Download-Android-" + version + ".apk")
                    put("size", 203000000)
                }))
            }
        releases.put(androidRelease("0.2.0-beta"))
        releases.put(androidRelease("0.3.1-beta"))
        releases.put(androidRelease("0.8.0-beta", draft = true))
        val newer = AndroidUpdates.findNewer(releases.toString(), "0.3.0-beta")
        assertNotNull("Nouvelle Release Android non détectée.", newer)
        assertEquals("0.3.1-beta", newer!!.version)
        assertTrue(newer.apkUrl.endsWith("All-Download-Android-0.3.1-beta.apk"))
        assertNull("Pas de mise à jour à version identique.",
            AndroidUpdates.findNewer(releases.toString(), "0.3.1-beta"))
    }

    @Test fun privateUpdateApkProviderAndChecksumRulesWorkWithoutBrowser() {
        val name = "All-Download-Android-0.5.0-beta.apk"
        val digest = "f".repeat(64)
        assertEquals(digest, AndroidApkInstaller.readChecksum("$digest  $name\n", name))
        assertNull(AndroidApkInstaller.readChecksum("$digest  other.apk", name))
        assertNull(AndroidApkInstaller.readChecksum("bad  $name", name))
        assertTrue(AndroidApkInstaller.isTrustedDownloadHost("github.com"))
        assertTrue(AndroidApkInstaller.isTrustedDownloadHost("release-assets.githubusercontent.com"))
        assertFalse(AndroidApkInstaller.isTrustedDownloadHost("github.com.example.org"))
        assertFalse(AndroidApkInstaller.isTrustedDownloadHost("attacker.com"))
        val dir = File(context.cacheDir, "updates").apply { mkdirs() }
        val file = File(dir, "provider-test.apk")
        try {
            file.writeText("test")
            val uri = androidx.core.content.FileProvider.getUriForFile(
                context, context.packageName + ".files", file)
            assertEquals("content", uri.scheme)
            assertFalse("Le fichier reste privé et ne doit jamais être ouvert comme une URL web.",
                uri.toString().startsWith("https://"))
        } finally { file.delete() }
    }

    @Test fun updateCacheRemembersNewAndroidReleasesWithoutStoringWindowsHistory() {
        val release = AndroidUpdates.Release(
            "0.5.0-beta", "android-v0.5.0-beta", "All-Download Android",
            "Corrections de stabilité",
            "https://github.com/anderson76389/All-Download/releases/tag/android-v0.5.0-beta",
            "https://github.com/anderson76389/All-Download/releases/download/" +
                "android-v0.5.0-beta/All-Download-Android-0.5.0-beta.apk",
            5_000_000L)
        val encoded = AndroidUpdates.encodeCandidate(release)
        assertEquals("0.5.0-beta",
            AndroidUpdates.decodeCandidate(encoded, "0.4.0-beta")?.version)
        assertNull(AndroidUpdates.decodeCandidate(encoded, "0.5.0-beta"))
        val forged = org.json.JSONObject(encoded).put("apkUrl", "https://example.com/fake.apk")
        assertNull(AndroidUpdates.decodeCandidate(forged.toString(), "0.4.0-beta"))
        assertEquals("", AndroidUpdates.encodeCandidate(null))
    }

    @Test fun windowsSettingsAreActuallyAvailableOnAndroid() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navSettings).performClick()
            }
            instrumentation.waitForIdleSync()
            val settings = activity.findViewById<LinearLayout>(R.id.settingsPage)
            assertEquals(View.VISIBLE, settings.visibility)
            assertTrue("Navigation Windows des paramètres absente.",
                settings.childCount >= 4)
            val sectionTabs = activity.findViewById<LinearLayout>(R.id.settingsTabs)
            assertEquals(3, sectionTabs.childCount)
            val downloads = activity.findViewById<View>(R.id.settingsDownloadPanel)
            val application = activity.findViewById<View>(R.id.settingsApplicationPanel)
            val network = activity.findViewById<View>(R.id.settingsNetworkPanel)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.settingsTabDownload).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(View.VISIBLE, downloads.visibility)
            assertEquals(View.GONE, application.visibility)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.settingsTabNetwork).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals("Le panneau Réseau doit répondre aux clics.",
                View.VISIBLE, network.visibility)
            assertEquals(View.GONE, downloads.visibility)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.settingsTabApplication).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals("Le panneau Application doit répondre aux clics.",
                View.VISIBLE, application.visibility)
            assertEquals(View.GONE, network.visibility)
            assertTrue("Format vidéo non configurable.", DownloadOptions.validProxy(
                "socks5://127.0.0.1:1080"))
            assertFalse("URL proxy dangereuse acceptée.", DownloadOptions.validProxy(
                "https://example.com.evil@attacker"))
            assertFalse(DownloadOptions.validProxy("javascript:alert(1)"))
            assertFalse(DownloadOptions.validProxy("http://127.0.0.1:0"))
            assertEquals(6, context.packageManager.getPackageInfo(context.packageName, 0)
                .versionCode)
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun animatedAndroidUpdateDialogShowsAndCanBeDismissed() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        val update = AndroidUpdates.Release(
            "0.4.0-beta", "android-v0.4.0-beta",
            "All-Download Android 0.4.0 bêta",
            "Nouvelle interface et options de téléchargement",
            "https://github.com/anderson76389/All-Download/releases/tag/android-v0.4.0-beta",
            "https://github.com/anderson76389/All-Download/releases/download/" +
                "android-v0.4.0-beta/All-Download-Android-0.4.0-beta.apk",
            202000000L
        )
        var dialog: android.app.Dialog? = null
        try {
            instrumentation.runOnMainSync {
                dialog = AndroidUpdates.showDialog(activity, update)
            }
            instrumentation.waitForIdleSync()
            assertNotNull("Fenêtre de mise à jour non construite.", dialog)
            assertTrue("Popup de mise à jour Android non visible.", dialog!!.isShowing)
        } finally {
            instrumentation.runOnMainSync {
                dialog?.dismiss()
                activity.finish()
            }
        }
    }

    @Test fun queueRevisionSkipsWritesAndSupportsLargeLists() {
        val link = "https://example.org/perf-" + UUID.randomUUID() + ".mp4"
        val startRevision = DownloadQueue.revision()
        val task = DownloadQueue.enqueue(context, link, 0, 0)
        try {
            val afterCreate = DownloadQueue.revision()
            assertTrue("L'ajout doit incrémenter la révision.", afterCreate > startRevision)
            // A progress callback can repeat identical status and must not write storage.
            DownloadQueue.update(context, task.id, status = DownloadQueue.WAITING,
                progress = 0, message = "")
            assertEquals("Une mise à jour identique ne doit pas écrire sur disque.",
                afterCreate, DownloadQueue.revision())
            DownloadQueue.update(context, task.id, progress = 50)
            val afterProgress = DownloadQueue.revision()
            assertTrue(afterProgress > afterCreate)
            DownloadQueue.update(context, task.id, progress = 50)
            assertEquals("Progression inchangée : aucune écriture supplémentaire.",
                afterProgress, DownloadQueue.revision())
            assertEquals(50,
                DownloadQueue.snapshot(context).find { it.id == task.id }?.progress)
        } finally {
            DownloadQueue.remove(context, task.id)
        }
    }

    @Test fun queueRejectsInvalidUrlsWithoutLosingExistingTasks() {
        val size = DownloadQueue.snapshot(context).size
        for (badUrl in listOf("", "notaurl", "https://", "javascript:alert(1)",
                "https://user:pass@example.com/video.mp4")) {
            try {
                DownloadQueue.enqueue(context, badUrl, 0, 0)
                fail("URL invalide autorisée : " + badUrl)
            } catch (_: IllegalArgumentException) {}
        }
        assertEquals(size, DownloadQueue.snapshot(context).size)
    }

    @Test fun originalWindowsLogoIsSmallEnoughForLowMemoryAndroidLauncher() {
        val options = android.graphics.BitmapFactory.Options()
        options.inJustDecodeBounds = true
        android.graphics.BitmapFactory.decodeResource(
            context.resources, R.drawable.all_download_logo, options)
        assertTrue("Logo Android non trouvé.", options.outWidth > 0 && options.outHeight > 0)
        assertTrue("L'image originale est trop grande pour l'icône mobile.",
            options.outWidth <= 256 && options.outHeight <= 256)
        assertEquals("Conserver le logo Windows au format carré.", options.outWidth,
            options.outHeight)
    }

    @Test fun largeQueueDoesNotRenderHundredsOfCardsAtOnce() {
        val tasks = mutableListOf<DownloadQueue.Task>()
        var activity: MainActivity? = null
        try {
            for (index in 1..27) {
                tasks.add(DownloadQueue.enqueue(context,
                    "https://example.org/battery-test-${UUID.randomUUID()}-$index.mp4", 0, 0))
            }
            val instance = instrumentation.startActivitySync(
                Intent(context, MainActivity::class.java).addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
            ) as MainActivity
            activity = instance
            instrumentation.waitForIdleSync()
            instrumentation.runOnMainSync {
                instance.findViewById<Button>(R.id.navQueue).performClick()
            }
            instrumentation.waitForIdleSync()
            val cards = instance.findViewById<LinearLayout>(R.id.queueList)
            val initial = cards.childCount
            assertTrue("Les 24 premières tâches et un bouton doivent suffire.",
                initial in 2..25)
            val more = cards.getChildAt(initial - 1) as? Button
            assertNotNull("Le bouton Afficher plus doit permettre l'accès aux autres tâches.", more)
            instrumentation.runOnMainSync { more!!.performClick() }
            instrumentation.waitForIdleSync()
            assertTrue("Afficher plus ne doit pas masquer les tâches déjà visibles.",
                cards.childCount >= initial)
            assertTrue("La file doit rester bornée à 48 cartes avant un nouveau clic.",
                cards.childCount <= 49)
        } finally {
            activity?.let { instance ->
                instrumentation.runOnMainSync { instance.finish() }
            }
            tasks.forEach { DownloadQueue.remove(context, it.id) }
        }
    }

    @Test fun deletingQueuedTaskAlsoDeletesPrivatePartialFiles() {
        val task = DownloadQueue.enqueue(context,
            "https://example.org/private-partial-" + UUID.randomUUID() + ".mp4", 0, 0)
        val privateRoot = context.getExternalFilesDir(null) ?: context.filesDir
        val work = File(privateRoot,
            "All-Download/Donnees/temporaires/" + task.id)
        assertTrue(work.mkdirs())
        val leftover = File(work, "partial-video.mp4.part")
        leftover.writeText("simulation d'un téléchargement interrompu")
        assertTrue(leftover.exists())
        assertTrue("Supprimer la tâche doit réussir.", DownloadQueue.remove(context, task.id))
        assertFalse("Le fichier partiel doit disparaître pour libérer le stockage.",
            leftover.exists())
        assertFalse(work.exists())
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
