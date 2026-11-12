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
            val wide = activity.resources.configuration.screenWidthDp >= 600
            if (wide) {
                assertSame("La barre d'état doit rester dans la page sur tablette",
                    home, footer.parent)
                assertEquals(if (activity.resources.configuration.screenWidthDp >= 900)
                    LinearLayout.HORIZONTAL else LinearLayout.VERTICAL, options.orientation)
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
            assertEquals("Le sélecteur 1080p ne doit pas apparaître en MP3.",
                View.GONE, activity.findViewById<View>(R.id.downloadQualityGroup).visibility)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.quickPlaylistButton).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(5, mode.selectedItemPosition)
            assertEquals(View.VISIBLE,
                activity.findViewById<View>(R.id.downloadQualityGroup).visibility)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navQueue).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(View.VISIBLE, activity.findViewById<View>(R.id.queuePage).visibility)
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun phoneTabsAndFolderHeadingNeverHideBehindPinnedChrome() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            if (activity.resources.configuration.screenWidthDp >= 600) return
            val tabs = activity.findViewById<LinearLayout>(R.id.navigation)
            val footer = activity.findViewById<View>(R.id.statusFooterCard)
            if (!DownloadService.state.busy)
                assertEquals("Un panneau Prêt permanent masque les options.",
                    View.GONE, footer.visibility)
            assertEquals("Quatre onglets fixes, sans défilement horizontal.",
                4, tabs.childCount)
            for (index in 0 until tabs.childCount) {
                val child = tabs.getChildAt(index)
                assertTrue("Onglet de largeur nulle.", child.width > 0)
                assertTrue("Onglet tronqué à gauche.", child.left >= 0)
                assertTrue("Onglet tronqué à droite.", child.right <= tabs.width)
            }
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navFiles).performClick()
            }
            instrumentation.waitForIdleSync()
            val content = activity.findViewById<View>(R.id.mainContent)
            val heading = activity.findViewById<View>(R.id.filesPageTitleIcon)
            val contentLocation = IntArray(2)
            val headingLocation = IntArray(2)
            content.getLocationOnScreen(contentLocation)
            heading.getLocationOnScreen(headingLocation)
            assertTrue("Le titre Dossiers doit être visible dans le contenu, sans en-tête fixe.",
                headingLocation[1] >= contentLocation[1])
            assertEquals("Le panneau d'état ne doit pas recouvrir les dossiers.",
                View.GONE, footer.visibility)
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun glassNavigationKeepsVectorIconsVisibleOnPhoneAndTablet() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val nav = activity.findViewById<LinearLayout>(R.id.navigation)
            val wide = activity.resources.configuration.screenWidthDp >= 600
            val bar = nav.parent as View
            val screenWidth = activity.resources.displayMetrics.widthPixels
            val actions = intArrayOf(R.id.navHome, R.id.navQueue,
                R.id.navFiles, R.id.navSettings)
            for (id in actions) {
                val button = activity.findViewById<Button>(id)
                assertTrue("Bouton de navigation non cliquable.", button.isClickable)
                val icons = button.compoundDrawablesRelative
                assertNotNull("Icône vectorielle de navigation manquante.",
                    if (wide) icons[0] else icons[1])
                assertTrue("Libellé de navigation invisible.", button.text.isNotBlank())
            }
            if (!wide) {
                assertTrue("Capsule de navigation sans largeur.", bar.width > 0)
                assertTrue("La capsule déborde du téléphone.", bar.width <= screenWidth)
                assertTrue("La dernière action est hors écran.",
                    nav.getChildAt(nav.childCount - 1).right <= nav.width)
                assertNotNull("Aspect verre non installé.", bar.background)
            } else {
                assertEquals(LinearLayout.VERTICAL, nav.orientation)
                assertNotNull("Barre latérale transparente absente.", nav.parent?.parent)
            }
            // The exact original listeners must remain wired after view reparenting.
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navQueue).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(View.VISIBLE,
                activity.findViewById<View>(R.id.queuePage).visibility)
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navSettings).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(View.VISIBLE,
                activity.findViewById<View>(R.id.settingsPage).visibility)
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun vectorsAndButtonLabelsAreUniformAcrossScreenWidths() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val actionIds = listOf(
                R.id.startButton, R.id.queueButton, R.id.pasteUrlButton,
                R.id.quickVideoButton, R.id.quickAudioButton, R.id.quickGifButton,
                R.id.quickPlaylistButton, R.id.quickTwitchButton,
                R.id.resumeQueueButton, R.id.pauseQueueButton
            )
            for (id in actionIds) {
                val button = activity.findViewById<Button>(id)
                assertNotNull("Missing vector icon for $id", button.compoundDrawablesRelative[0])
                assertTrue("Empty button label $id", button.text.isNotBlank())
                assertTrue("Action sans limite de lignes cohérente : $id", button.maxLines in 1..2)
                if (button.isShown) {
                    val layout = button.layout
                    assertTrue("Texte coupé verticalement : $id",
                        layout.height <= button.height - button.compoundPaddingTop -
                            button.compoundPaddingBottom)
                    for (line in 0 until layout.lineCount)
                        assertEquals("Libellé tronqué : $id", 0, layout.getEllipsisCount(line))
                }
                assertFalse("Legacy text glyph used as icon for $id",
                    button.text.any { it in "▶♫↓＋Ⅱ🎬🎵📁" })
                // Hidden pages are intentionally GONE and are not measured until opened.
                if (button.isShown)
                    assertTrue("Visible button has no touch width: $id", button.width > 0)
            }
            assertNotNull("Le logo All-Download reste dans les ressources du lanceur.",
                activity.getDrawable(R.drawable.all_download_android_logo))
            for (res in listOf(R.drawable.ic_video, R.drawable.ic_audio,
                    R.drawable.ic_gif, R.drawable.ic_playlist, R.drawable.ic_stream,
                    R.drawable.ic_file, R.drawable.ic_download)) {
                assertNotNull("Vector drawable not loaded", activity.getDrawable(res))
            }
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun windowsStyleSectionIconsAndSettingsTabsHaveNativeVectors() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val sectionIds = listOf(
                R.id.homeTitleIcon, R.id.optionsTitleIcon, R.id.homeQueueTitleIcon,
                R.id.queuePageTitleIcon, R.id.filesPageTitleIcon, R.id.settingsPageTitleIcon)
            for (id in sectionIds) {
                val label = activity.findViewById<TextView>(id)
                assertNotNull("Section title missing: $id", label)
                assertNotNull("Native Windows-style icon missing: $id",
                    label.compoundDrawablesRelative[0])
            }
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navSettings).performClick()
            }
            instrumentation.waitForIdleSync()
            for (id in listOf(R.id.settingsTabDownload, R.id.settingsTabApplication,
                    R.id.settingsTabNetwork)) {
                val button = activity.findViewById<Button>(id)
                val stacked = activity.resources.configuration.screenWidthDp < 390 ||
                    activity.resources.configuration.fontScale > 1.2f
                assertNotNull("Settings tab icon missing: $id",
                    button.compoundDrawablesRelative[if (stacked) 1 else 0])
                assertTrue("Settings tab label empty: $id", button.text.isNotBlank())
            }
            val mediaCards = activity.findViewById<LinearLayout>(
                R.id.settingsDownloadPanel)
            assertTrue("Expected at least one media settings section", mediaCards.childCount > 0)
            val firstCard = mediaCards.getChildAt(0) as LinearLayout
            val heading = firstCard.getChildAt(0) as TextView
            assertNotNull("Settings section icon missing",
                heading.compoundDrawablesRelative[0])
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun quickAccessButtonsNeverHideOffscreenOnCompactScreens() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val grid = activity.findViewById<LinearLayout>(R.id.quickModesRow)
            val ids = intArrayOf(R.id.quickVideoButton, R.id.quickAudioButton,
                R.id.quickGifButton, R.id.quickPlaylistButton, R.id.quickTwitchButton)
            if (activity.resources.configuration.screenWidthDp < 900) {
                assertEquals("Cinq raccourcis doivent former deux lignes",
                    LinearLayout.VERTICAL, grid.orientation)
                assertEquals(2, grid.childCount)
                val firstRow = grid.getChildAt(0) as LinearLayout
                val secondRow = grid.getChildAt(1) as LinearLayout
                assertEquals(3, firstRow.childCount)
                assertEquals(2, secondRow.childCount)
                val screenDp = activity.resources.displayMetrics.density
                ids.forEach { id ->
                    val button = activity.findViewById<Button>(id)
                    assertTrue("Le raccourci a une largeur nulle : $id", button.width > 0)
                    assertTrue("Raccourci trop bas : $id", button.height / screenDp >= 47.5f)
                    assertTrue("Libellé illisible : $id", button.text.isNotBlank())
                    assertEquals(1, button.maxLines)
                    assertTrue("Bouton qui déborde à droite : $id",
                        button.right <= (button.parent as LinearLayout).width)
                    assertTrue("Bouton qui déborde à gauche : $id", button.left >= 0)
                }
                assertTrue("La rangée est trop large pour l'écran",
                    grid.width <= activity.resources.displayMetrics.widthPixels)
                instrumentation.runOnMainSync {
                    activity.findViewById<Button>(R.id.quickPlaylistButton).performClick()
                    activity.findViewById<Button>(R.id.quickTwitchButton).performClick()
                }
                instrumentation.waitForIdleSync()
                assertEquals("Twitch doit conserver la qualité vidéo native", 0,
                    activity.findViewById<Spinner>(R.id.qualitySpinner).selectedItemPosition)
            } else {
                assertEquals("Tablettes larges : garder la barre compacte",
                    LinearLayout.HORIZONTAL, grid.orientation)
                assertEquals(5, grid.childCount)
            }
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun readableAlignmentAndResponsiveTextAcrossAllPages() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val density = activity.resources.displayMetrics.density
            fun dp(px: Int): Int = (px / density + .5f).toInt()
            val paste = activity.findViewById<Button>(R.id.pasteUrlButton)
            val add = activity.findViewById<Button>(R.id.queueButton)
            assertTrue("Presse-papiers trop étroit avec son pictogramme", dp(paste.width) >= 87)
            assertEquals("Action de file différente de Windows", "Ajouter", add.text.toString())
            assertEquals("Icône de file manquante", true,
                add.compoundDrawablesRelative[0] != null)
            for (id in intArrayOf(R.id.quickVideoButton, R.id.quickAudioButton,
                    R.id.quickGifButton, R.id.quickPlaylistButton, R.id.quickTwitchButton)) {
                val button = activity.findViewById<Button>(id)
                assertTrue("Raccourci sous les 48 dp : $id", dp(button.height) >= 48)
                assertEquals("Texte sur plusieurs lignes : $id", 1, button.maxLines)
            }
            for (id in intArrayOf(R.id.homeTitleIcon, R.id.optionsTitleIcon,
                    R.id.homeQueueTitleIcon, R.id.queuePageTitleIcon,
                    R.id.filesPageTitleIcon, R.id.settingsPageTitleIcon,
                    R.id.quickAccessTitleIcon, R.id.statusFooterTitleIcon,
                    R.id.settingsAppearanceTitleIcon, R.id.settingsEngineTitleIcon,
                    R.id.settingsCookiesTitleIcon)) {
                val heading = activity.findViewById<TextView>(id)
                assertNotNull("Titre non présent : $id", heading)
                assertNotNull("Pictogramme de titre non présent : $id",
                    heading.compoundDrawablesRelative[0])
                assertEquals("Un titre long doit pouvoir revenir sur deux lignes : $id",
                    2, heading.maxLines)
            }
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navSettings).performClick()
            }
            instrumentation.waitForIdleSync()
            val stacked = activity.resources.configuration.screenWidthDp < 390 ||
                activity.resources.configuration.fontScale > 1.2f
            for (id in intArrayOf(R.id.settingsTabDownload,
                    R.id.settingsTabApplication, R.id.settingsTabNetwork)) {
                val button = activity.findViewById<Button>(id)
                assertTrue("Onglet réglages inaccessible : $id", button.isClickable)
                assertTrue("Onglet réglages trop petit : $id", dp(button.height) >= 48)
                assertTrue("Onglet hors de sa grille : $id", button.width > 0)
                assertNotNull("Icône mal placée : $id",
                    button.compoundDrawablesRelative[if (stacked) 1 else 0])
                val measuredText = button.paint.measureText(button.text.toString())
                assertTrue("Libellé coupé dans l'onglet : $id",
                    measuredText <= button.width - button.paddingLeft - button.paddingRight + 2f)
            }
            val group = activity.findViewById<LinearLayout>(R.id.settingsDownloadPanel)
            val firstCard = group.getChildAt(0) as LinearLayout
            val toggleRow = (0 until firstCard.childCount)
                .map { firstCard.getChildAt(it) }
                .filterIsInstance<LinearLayout>()
                .first { row -> (0 until row.childCount).any {
                    row.getChildAt(it) is android.widget.Switch
                } }
            val captions = toggleRow.getChildAt(0) as LinearLayout
            val toggle = toggleRow.getChildAt(1) as android.widget.Switch
            assertEquals("Titre et description doivent partager le même alignement.",
                (captions.getChildAt(0) as TextView).left,
                (captions.getChildAt(1) as TextView).left)
            assertTrue("L'interrupteur doit être à droite, sans chevaucher le texte.",
                toggle.left >= captions.right)
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun sevenFolderGlyphsRenderAsDistinctVisibleShapes() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val resourceIds = intArrayOf(
                R.drawable.ic_folder_video, R.drawable.ic_folder_audio,
                R.drawable.ic_folder_twitch, R.drawable.ic_folder_gif,
                R.drawable.ic_folder_channel, R.drawable.ic_folder_playlist,
                R.drawable.ic_folder_other
            )
            val bitmaps = resourceIds.map { res ->
                val bitmap = android.graphics.Bitmap.createBitmap(96, 96,
                    android.graphics.Bitmap.Config.ARGB_8888)
                val drawable = activity.getDrawable(res)!!
                drawable.setBounds(0, 0, 96, 96)
                drawable.draw(android.graphics.Canvas(bitmap))
                val pixels = IntArray(96 * 96)
                bitmap.getPixels(pixels, 0, 96, 0, 0, 96, 96)
                assertTrue("Folder vector contains no visible pixels: $res",
                    pixels.any { it != android.graphics.Color.TRANSPARENT })
                bitmap
            }
            for (i in bitmaps.indices) {
                for (j in 0 until i) {
                    assertFalse("Folder $i and $j have identical visual symbols.",
                        bitmaps[i].sameAs(bitmaps[j]))
                }
            }
            bitmaps.forEach { it.recycle() }
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun unifiedIconCatalogLoadsAndQueueActionsRetainTheirLabels() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val glyphs = intArrayOf(
                R.drawable.nav_home, R.drawable.nav_queue, R.drawable.nav_folders,
                R.drawable.nav_settings, R.drawable.ic_download, R.drawable.ic_queue_add,
                R.drawable.ic_audio, R.drawable.ic_video, R.drawable.ic_gif,
                R.drawable.ic_playlist, R.drawable.ic_stream, R.drawable.ic_metadata,
                R.drawable.ic_notifications, R.drawable.ic_done, R.drawable.ic_error,
                R.drawable.ic_waiting, R.drawable.ic_folder_video, R.drawable.ic_folder_audio,
                R.drawable.ic_folder_twitch, R.drawable.ic_folder_gif,
                R.drawable.ic_folder_channel, R.drawable.ic_folder_playlist,
                R.drawable.ic_folder_other
            )
            for (resId in glyphs) {
                assertNotNull("Icône native manquante : $resId", activity.getDrawable(resId))
            }
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navQueue).performClick()
            }
            instrumentation.waitForIdleSync()
            val actionIds = intArrayOf(
                R.id.resumeQueueButton, R.id.pauseQueueButton,
                R.id.clearFinishedButton, R.id.clearFailedButton, R.id.clearWaitingButton
            )
            actionIds.forEach { id ->
                val action = activity.findViewById<Button>(id)
                assertNotNull("Pictogramme de file manquant : $id",
                    action.compoundDrawablesRelative[0])
                assertTrue("Texte de file manquant : $id", action.text.isNotBlank())
                assertTrue("Action de file non cliquable : $id", action.isClickable)
            }
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun minimalistLiquidGlassAndDownloadActionsKeepWorking() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val download = activity.findViewById<Button>(R.id.startButton)
            val enqueue = activity.findViewById<Button>(R.id.queueButton)
            assertSame("Les actions Télécharger et Dans la file doivent partager une ligne.",
                download.parent, enqueue.parent)
            assertTrue(download.isClickable && enqueue.isClickable)
            val navigation = activity.findViewById<LinearLayout>(R.id.navigation)
            assertTrue("La navigation utilise le verre natif à double couche.",
                (navigation.parent as View).background is android.graphics.drawable.LayerDrawable)
            val links = listOf(R.id.navHome, R.id.navQueue, R.id.navFiles, R.id.navSettings)
            assertTrue(links.all { activity.findViewById<Button>(it).isClickable })
            val shortcuts = listOf(R.id.quickVideoButton, R.id.quickAudioButton,
                R.id.quickGifButton, R.id.quickPlaylistButton, R.id.quickTwitchButton)
            assertTrue(shortcuts.all { activity.findViewById<Button>(it).isClickable })
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun removedBrandHeaderKeepsOptionalUpdateBannerAcrossPages() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val content = activity.findViewById<LinearLayout>(R.id.mainContent)
            val scroll = activity.findViewById<View>(R.id.scroll)
            val notice = content.getChildAt(0)
            assertNotNull("Un avis de mise à jour conditionnel doit rester disponible.", notice)
            assertTrue("L'avis doit défiler avec la page et non être une barre épinglée.",
                notice.parent === content && content.parent === scroll)
            assertTrue("Le premier bloc doit être un avis et pas l'ancien logo.",
                notice is LinearLayout)
            for (id in intArrayOf(R.id.navHome, R.id.navQueue,
                    R.id.navFiles, R.id.navSettings)) {
                instrumentation.runOnMainSync {
                    activity.findViewById<Button>(id).performClick()
                }
                instrumentation.waitForIdleSync()
                assertSame("L'avis de mise à jour ne doit pas être recréé en navigation.",
                    notice, content.getChildAt(0))
            }
            assertEquals("La marque reste le nom de l'application et non un bandeau.",
                "All-Download",
                context.packageManager.getApplicationLabel(context.applicationInfo).toString())
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun pinnedUpdateBannerCanBeDismissedUntilTheNextRelease() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        val prefs = activity.getSharedPreferences("android_update_banner_v1",
            android.content.Context.MODE_PRIVATE)
        val wasEnabled = AndroidUpdates.enabled(activity)
        try {
            instrumentation.runOnMainSync {
                AndroidUpdates.setEnabled(activity, true)
                prefs.edit().clear().commit()
                val banner = AndroidUpdateBanner(activity)
                fun release(version: String) = AndroidUpdates.Release(
                    version, "android-v" + version, "All-Download Android " + version,
                    "Corrections d'affichage",
                    "https://github.com/anderson76389/All-Download/releases/tag/android-v" + version,
                    "https://github.com/anderson76389/All-Download/releases/download/android-v" +
                        version + "/All-Download-Android-" + version + ".apk", 2_000_000)
                banner.show(release("99.0.0-beta"))
                assertEquals(View.VISIBLE, banner.view.visibility)
                val actions = banner.view.getChildAt(3) as LinearLayout
                assertEquals(3, actions.childCount)
                assertTrue((actions.getChildAt(0) as Button).text.contains("Installer"))
                (actions.getChildAt(2) as Button).performClick()
                assertEquals(View.GONE, banner.view.visibility)
                banner.show(release("99.0.0-beta"))
                assertEquals("Dismissed tag must not pop up again", View.GONE,
                    banner.view.visibility)
                banner.show(release("99.0.1-beta"))
                assertEquals("A newer release must show again", View.VISIBLE,
                    banner.view.visibility)
                banner.hide()
            }
        } finally {
            instrumentation.runOnMainSync {
                prefs.edit().clear().commit()
                AndroidUpdates.setEnabled(activity, wasEnabled)
                activity.finish()
            }
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
            assertNotNull("Le logo Android doit rester présent dans les ressources.",
                activity.getDrawable(R.drawable.all_download_android_logo))
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
            val wide = activity.resources.configuration.screenWidthDp >= 600
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

    @Test fun queueSectionsHaveDistinctCardsAndReadableActionSpacing() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navQueue).performClick()
            }
            instrumentation.waitForIdleSync()
            val density = activity.resources.displayMetrics.density
            fun minimum(dp: Int) = (dp * density + .5f).toInt()
            val parent = activity.findViewById<LinearLayout>(R.id.queuePage)
            val sections = listOf(
                R.id.queueHeaderCard, R.id.queueControlsCard, R.id.queueItemsHeader,
                R.id.queueList, R.id.queueCleanupCard)
                .map { activity.findViewById<View>(it) }
            assertEquals("Les cinq blocs de File doivent rester dans leur ordre.",
                sections, (0 until parent.childCount).map { parent.getChildAt(it) })
            for ((index, section) in sections.withIndex()) {
                assertTrue("Bloc de file sans largeur.", section.width > 0)
                assertTrue("Bloc de file sorti de son conteneur.",
                    section.left >= 0 && section.right <= parent.width)
                if (index < sections.lastIndex) {
                    val next = sections[index + 1]
                    assertTrue("Blocs de File collés ou chevauchés : $index",
                        next.top - section.bottom >= minimum(12))
                }
            }
            for (id in listOf(R.id.queueHeaderCard, R.id.queueControlsCard,
                    R.id.queueCleanupCard)) {
                val card = activity.findViewById<View>(id)
                assertNotNull("Le bloc doit être une carte distincte.", card.background)
                assertTrue("Espace intérieur manquant : $id",
                    card.paddingLeft >= minimum(14))
            }
            val cleanup = activity.findViewById<LinearLayout>(R.id.queueCleanupActions)
            assertEquals("Le nettoyage ne doit pas encombrer la liste au départ.",
                View.GONE, cleanup.visibility)
            val toggle = activity.findViewById<Button>(R.id.queueCleanupToggle)
            assertTrue("Le bouton de nettoyage doit être accessible.",
                toggle.isClickable && toggle.height >= minimum(48))
            instrumentation.runOnMainSync { toggle.performClick() }
            instrumentation.waitForIdleSync()
            assertEquals("Les outils doivent s'ouvrir sur demande.",
                View.VISIBLE, cleanup.visibility)
            assertTrue("Le bouton d'ouverture doit devenir un bouton de fermeture.",
                toggle.text.toString().contains("Masquer"))
            for (id in listOf(R.id.resumeQueueButton, R.id.pauseQueueButton,
                    R.id.clearFinishedButton, R.id.clearFailedButton,
                    R.id.clearWaitingButton)) {
                val button = activity.findViewById<Button>(id)
                assertTrue("Cible tactile trop basse : $id", button.height >= minimum(48))
                assertTrue("Bouton masqué à droite : $id",
                    button.left >= 0 && button.right <= (button.parent as View).width)
            }
            val run = activity.findViewById<Button>(R.id.resumeQueueButton)
            val pause = activity.findViewById<Button>(R.id.pauseQueueButton)
            assertTrue("Les contrôles se chevauchent.", run.right < pause.left)
            val failed = activity.findViewById<Button>(R.id.clearFailedButton)
            val waiting = activity.findViewById<Button>(R.id.clearWaitingButton)
            assertTrue("Les actions de nettoyage se chevauchent.", failed.right < waiting.left)
            instrumentation.runOnMainSync { toggle.performClick() }
            instrumentation.waitForIdleSync()
            assertEquals(View.GONE, cleanup.visibility)
            for (id in listOf(R.id.queueControlsTitleIcon,
                    R.id.queueCleanupTitleIcon, R.id.queueItemsTitleIcon)) {
                val title = activity.findViewById<TextView>(id)
                assertNotNull("Icône de section absente.", title.compoundDrawablesRelative[0])
                assertTrue("Titre de section vide.", title.text.isNotBlank())
            }
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun queueItemButtonsFitWithoutHorizontalScrolling() {
        val job = DownloadQueue.enqueue(context,
            "https://example.org/queue-layout-${UUID.randomUUID()}.mp4", 0, 0)
        DownloadQueue.update(context, job.id, status = DownloadQueue.ERROR,
            progress = 43, message = "Échec réseau simulé pour vérifier la présentation.")
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navQueue).performClick()
            }
            instrumentation.waitForIdleSync()
            val queue = activity.findViewById<LinearLayout>(R.id.queueList)
            val card = queue.getChildAt(0) as LinearLayout
            assertNotNull("La carte de téléchargement doit être encadrée.", card.background)
            // Header / optional message / progress / divider / action footer.
            val footer = card.getChildAt(card.childCount - 1) as LinearLayout
            assertEquals(LinearLayout.VERTICAL, footer.orientation)
            assertEquals("La reprise est séparée de la suppression.", 2, footer.childCount)
            val retry = footer.getChildAt(0) as Button
            assertEquals("Réessayer", retry.text.toString())
            val actions = footer.getChildAt(1) as LinearLayout
            assertEquals(2, actions.childCount)
            val delete = actions.getChildAt(0) as Button
            val copy = actions.getChildAt(1) as Button
            assertEquals("Supprimer", delete.text.toString())
            assertEquals("Copier", copy.text.toString())
            val density = activity.resources.displayMetrics.density
            assertTrue(retry.height >= (48f * density).toInt())
            assertTrue(delete.width > 0 && copy.width > 0)
            assertTrue("Boutons d'une carte collés.", copy.left - delete.right >=
                (8f * density).toInt())
            assertTrue("Dernière action hors écran.", copy.right <= actions.width)
            assertFalse("La file ne doit plus utiliser de barre d'actions horizontale.",
                (0 until card.childCount).any {
                    card.getChildAt(it) is android.widget.HorizontalScrollView
                })
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
            DownloadQueue.remove(context, job.id)
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

    @Test fun manualUpdateIsAvailableAfterDismissingAutomaticBanner() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        val prefs = activity.getSharedPreferences("android_update_banner_v1",
            android.content.Context.MODE_PRIVATE)
        val previousDismissed = prefs.getString("dismissed_release", null)
        val wasEnabled = AndroidUpdates.enabled(activity)
        try {
            instrumentation.runOnMainSync {
                AndroidUpdates.setEnabled(activity, true)
                val version = "99.0.0-beta"
                val tag = "android-v$version"
                val candidate = AndroidUpdates.Release(version, tag, "Test de mise à jour",
                    "Test du bouton manuel",
                    "https://github.com/anderson76389/All-Download/releases/tag/$tag",
                    "https://github.com/anderson76389/All-Download/releases/download/" +
                        "$tag/All-Download-Android-$version.apk", 2_000_000L)
                prefs.edit().putString("dismissed_release", tag).commit()
                val banner = AndroidUpdateBanner(activity)
                banner.show(candidate)
                assertEquals("La notification automatique doit rester masquée.",
                    View.GONE, banner.view.visibility)
                val manualDialog = AndroidUpdates.showManualUpdate(activity, candidate)
                assertNotNull("La recherche manuelle doit ignorer « Plus tard ».",
                    manualDialog)
                assertTrue("La fenêtre d'installation doit être ouverte dans l'application.",
                    manualDialog!!.isShowing)
                manualDialog.dismiss()
                assertNull("Aucune boîte de dialogue si la version est déjà installée.",
                    AndroidUpdates.showManualUpdate(activity, null))
            }
        } finally {
            instrumentation.runOnMainSync {
                prefs.edit().apply {
                    if (previousDismissed == null) remove("dismissed_release")
                    else putString("dismissed_release", previousDismissed)
                }.commit()
                AndroidUpdates.setEnabled(activity, wasEnabled)
                activity.finish()
            }
        }
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
            assertEquals(BuildConfig.VERSION_CODE,
                context.packageManager.getPackageInfo(context.packageName, 0).versionCode)
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

    @Test fun customAndroidLauncherIsSquareAndDoesNotReplaceWindowsArtwork() {
        val androidIcon = android.graphics.BitmapFactory.decodeResource(
            context.resources, R.drawable.all_download_android_logo)
        val windowsIcon = android.graphics.BitmapFactory.decodeResource(
            context.resources, R.drawable.all_download_logo)
        assertNotNull("Android-only logo not generated by Gradle", androidIcon)
        assertNotNull("Windows original compact resource disappeared", windowsIcon)
        try {
            assertEquals(192, androidIcon.width)
            assertEquals(192, androidIcon.height)
            assertFalse("The Android logo must be distinct from Windows",
                androidIcon.sameAs(windowsIcon))
        } finally {
            androidIcon.recycle()
            windowsIcon.recycle()
        }
        val options = android.graphics.BitmapFactory.Options().apply {
            inJustDecodeBounds = true
        }
        android.graphics.BitmapFactory.decodeResource(
            context.resources, R.drawable.all_download_launcher, options)
        assertEquals("Adaptive Android launcher must keep its safe zone",
            288, options.outWidth)
        assertEquals(288, options.outHeight)
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
    @Test fun compactActionRowsWrapWithoutClippingAndKeepTheirActions() {
        val job = DownloadQueue.enqueue(context,
            "https://example.org/compact-${UUID.randomUUID()}.mp4", 0, 0)
        DownloadQueue.update(context, job.id, DownloadQueue.ERROR)
        val activity = instrumentation.startActivitySync(Intent(context, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val density = activity.resources.displayMetrics.density
            fun dp(n: Int) = (n * density + .5f).toInt()
            instrumentation.runOnMainSync {
                val input = activity.findViewById<EditText>(R.id.urlInput)
                input.setText("not a URL")
                activity.findViewById<Button>(R.id.startButton).performClick()
                assertNotNull("Télécharger doit valider le lien.", input.error)
                input.error = null
                activity.findViewById<Button>(R.id.queueButton).performClick()
                assertNotNull("Ajouter doit aussi valider le lien.", input.error)
                val validUrl = "https://example.org/immediate-add-${UUID.randomUUID()}.mp4"
                input.setText(validUrl)
                activity.findViewById<Button>(R.id.queueButton).performClick()
                val added = DownloadQueue.snapshot(context).singleOrNull { it.url == validUrl }
                assertNotNull("Ajouter doit enregistrer la tâche immédiatement.", added)
                assertNull("Une URL corrigée ne doit plus garder la fenêtre d'erreur.", input.error)
                val preview = activity.findViewById<LinearLayout>(R.id.homeQueuePreview)
                fun containsUrl(view: View): Boolean = when (view) {
                    is TextView -> view.text.toString().contains(validUrl)
                    is android.view.ViewGroup -> (0 until view.childCount)
                        .any { containsUrl(view.getChildAt(it)) }
                    else -> false
                }
                assertTrue("L’aperçu doit afficher immédiatement le nouveau lien.", containsUrl(preview))
                DownloadQueue.remove(context, added!!.id)
            }
            val row = activity.findViewById<Button>(R.id.startButton).parent as LinearLayout
            instrumentation.runOnMainSync {
                row.layoutParams = row.layoutParams.apply { width = dp(240) }
                row.requestLayout()
            }
            instrumentation.waitForIdleSync()
            // Wait for the layout-listener reflow as well as the resulting traversal.
            instrumentation.runOnMainSync { row.requestLayout() }
            instrumentation.waitForIdleSync()
            assertEquals(LinearLayout.VERTICAL, row.orientation)
            val first = row.getChildAt(0) as Button
            val second = row.getChildAt(1) as Button
            assertTrue("Actions trop proches.", second.top - first.bottom >= dp(10))
            for (button in listOf(first, second)) {
                assertTrue(button.height >= dp(48))
                assertTrue(button.hasOnClickListeners())
                assertTrue(button.right <= row.width)
                for (line in 0 until button.layout.lineCount)
                    assertEquals("Action tronquée : ${button.text}", 0,
                        button.layout.getEllipsisCount(line))
            }
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navQueue).performClick()
            }
            instrumentation.waitForIdleSync()
            val card = activity.findViewById<LinearLayout>(R.id.queueList).getChildAt(0) as LinearLayout
            val footer = card.getChildAt(card.childCount - 1) as LinearLayout
            val actions = footer.getChildAt(1) as LinearLayout
            instrumentation.runOnMainSync { (actions.getChildAt(1) as Button).performClick() }
            instrumentation.runOnMainSync { activity.findViewById<Button>(R.id.navHome).performClick() }
            instrumentation.waitForIdleSync()
            // Let the page transition finish before measuring the touch target.
            // Copy opens a SystemUI clipboard overlay on Android 13+. A real
            // user returns to the input before pasting; perform that foreground
            // touch before requiring clipboard-read focus.
            val inputTarget = activity.findViewById<EditText>(R.id.urlInput)
            val inputPoint = IntArray(2)
            instrumentation.runOnMainSync { inputTarget.getLocationOnScreen(inputPoint) }
            val focusTouchTime = android.os.SystemClock.uptimeMillis()
            for (action in listOf(android.view.MotionEvent.ACTION_DOWN, android.view.MotionEvent.ACTION_UP)) {
                val event = android.view.MotionEvent.obtain(focusTouchTime,
                    android.os.SystemClock.uptimeMillis(), action,
                    inputPoint[0] + inputTarget.width / 2f,
                    inputPoint[1] + inputTarget.height / 2f, 0)
                event.source = android.view.InputDevice.SOURCE_TOUCHSCREEN
                assertTrue(instrumentation.uiAutomation.injectInputEvent(event, true))
                event.recycle()
                if (action == android.view.MotionEvent.ACTION_DOWN)
                    android.os.SystemClock.sleep(80)
            }
            val focusDeadline = android.os.SystemClock.elapsedRealtime() + 5000
            var focused = false
            while (!focused && android.os.SystemClock.elapsedRealtime() < focusDeadline) {
                instrumentation.runOnMainSync { focused = activity.hasWindowFocus() }
                if (!focused) android.os.SystemClock.sleep(50)
            }
            // An app-owned popup can hold focus while clipboard access remains
            // allowed for the app UID. The actual pasted URL is the requirement.
            val paste = activity.findViewById<Button>(R.id.pasteUrlButton)
            val bounds = android.graphics.Rect()
            val screenPoint = IntArray(2)
            instrumentation.runOnMainSync {
                assertTrue("Coller doit être visible avant l'appui réel.", paste.getGlobalVisibleRect(bounds))
                paste.getLocationOnScreen(screenPoint)
            }
            // A real touch activates the app window and exercises the production
            // Paste handler under Android's foreground clipboard restrictions.
            val x = screenPoint[0] + paste.width / 2f
            val y = screenPoint[1] + paste.height / 2f
            val now = android.os.SystemClock.uptimeMillis()
            for (action in listOf(android.view.MotionEvent.ACTION_DOWN, android.view.MotionEvent.ACTION_UP)) {
                val event = android.view.MotionEvent.obtain(now, android.os.SystemClock.uptimeMillis(),
                    action, x, y, 0)
                event.source = android.view.InputDevice.SOURCE_TOUCHSCREEN
                assertTrue("L'appui tactile doit être injecté par Android.",
                    instrumentation.uiAutomation.injectInputEvent(event, true))
                event.recycle()
                if (action == android.view.MotionEvent.ACTION_DOWN)
                    android.os.SystemClock.sleep(80)
            }
            // Input injection and waitForIdleSync do not guarantee the app has
            // received the queued input event. Observe the production result.
            val pasteDeadline = android.os.SystemClock.elapsedRealtime() + 5000
            var pasted = ""
            while (pasted != job.url && android.os.SystemClock.elapsedRealtime() < pasteDeadline) {
                instrumentation.runOnMainSync {
                    pasted = activity.findViewById<EditText>(R.id.urlInput).text.toString()
                }
                if (pasted != job.url) android.os.SystemClock.sleep(50)
            }
            // Android 13+ may show a system clipboard overlay which temporarily owns
            // input focus; an injected tap then goes to SystemUI, not our button.
            // If that happened, verify the *real app listener* explicitly as well,
            // rather than misdiagnosing an OS overlay as a failed paste handler.
            if (pasted != job.url) {
                instrumentation.runOnMainSync { paste.performClick() }
                instrumentation.waitForIdleSync()
            }
            val activeWindow = instrumentation.uiAutomation.rootInActiveWindow
            assertEquals("Copier puis Coller doit fournir le lien exact. " +
                "Activity focus=$focused; active=${activeWindow?.packageName}/${activeWindow?.className}", job.url,
                activity.findViewById<EditText>(R.id.urlInput).text.toString())
            instrumentation.runOnMainSync { activity.findViewById<Button>(R.id.navQueue).performClick() }
            instrumentation.waitForIdleSync()
            val retryCard = activity.findViewById<LinearLayout>(R.id.queueList).getChildAt(0) as LinearLayout
            val retryFooter = retryCard.getChildAt(retryCard.childCount - 1) as LinearLayout
            instrumentation.runOnMainSync { (retryFooter.getChildAt(0) as Button).performClick() }
            instrumentation.waitForIdleSync()
            assertEquals("Réessayer doit remettre la tâche en attente.", DownloadQueue.WAITING,
                DownloadQueue.snapshot(context).first { it.id == job.id }.status)
            val updated = activity.findViewById<LinearLayout>(R.id.queueList).getChildAt(0) as LinearLayout
            val newFooter = updated.getChildAt(updated.childCount - 1) as LinearLayout
            val newActions = newFooter.getChildAt(0) as LinearLayout
            instrumentation.runOnMainSync { (newActions.getChildAt(0) as Button).performClick() }
            assertFalse("Supprimer doit retirer la bonne tâche.",
                DownloadQueue.snapshot(context).any { it.id == job.id })
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
            DownloadQueue.remove(context, job.id)
        }
    }

    @Test fun settingsSwitchRowsPersistEachValueAndCanBeRestored() {
        val activity = instrumentation.startActivitySync(Intent(context, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)) as MainActivity
        val prefs = DownloadOptions.get(context)
        val keys = mapOf(
            "Remuxer dans le conteneur choisi" to "remux_video",
            "Ajouter titre et artiste" to "embed_metadata",
            "Enregistrer la miniature" to "write_thumbnail",
            "Intégrer la couverture" to "embed_thumbnail",
            "Enregistrer les sous-titres" to "write_subtitles",
            "Sous-titres automatiques" to "auto_subtitles",
            "Activer SponsorBlock" to "sponsor_enable",
            "Marquer les sections en chapitres" to "sponsor_mark",
            "Découpe précise" to "sponsor_exact",
            "Utiliser un proxy" to "proxy_enabled",
            "Notification de fin de téléchargement" to "notify_finished",
            "Réduire les animations" to "reduce_motion")
        val saved = keys.values.associateWith { key ->
            if (prefs.contains(key)) prefs.getBoolean(key, false) else null
        }
        try {
            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navSettings).performClick()
            }
            instrumentation.waitForIdleSync()
            fun controls(view: View): List<android.widget.Switch> = when (view) {
                is android.widget.Switch -> listOf(view)
                is android.view.ViewGroup -> (0 until view.childCount)
                    .flatMap { controls(view.getChildAt(it)) }
                else -> emptyList()
            }
            val switches = controls(activity.findViewById(R.id.settingsPage))
            for ((caption, key) in keys) {
                val control = switches.single { it.contentDescription?.toString() == caption }
                val before = control.isChecked
                instrumentation.runOnMainSync { (control.parent as View).performClick() }
                assertEquals("Le clic de ligne doit changer $caption", !before, control.isChecked)
                assertEquals("Le réglage $key doit être enregistré.", !before,
                    prefs.getBoolean(key, before))
                instrumentation.runOnMainSync { control.performClick() }
                assertEquals("Le clic direct doit restaurer $caption", before,
                    prefs.getBoolean(key, !before))
            }
        } finally {
            val editor = prefs.edit()
            saved.forEach { (key, value) ->
                if (value == null) editor.remove(key) else editor.putBoolean(key, value)
            }
            editor.commit()
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun compactMobileIconsAreCenteredWithTheirLabelsAcrossPages() {
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        instrumentation.waitForIdleSync()
        try {
            val density = activity.resources.displayMetrics.density
            fun dp(n: Int) = (n * density + .5f).toInt()

            fun verifyGroupedCenter(id: Int) {
                val button = activity.findViewById<Button>(id)
                val icon = button.compoundDrawablesRelative[0]
                assertNotNull("Icône absente pour $id", icon)
                assertTrue("Bouton non mesuré : $id", button.width > 0)
                assertEquals("Icône/texte non alignés verticalement : $id",
                    android.view.Gravity.CENTER_VERTICAL,
                    button.gravity and android.view.Gravity.VERTICAL_GRAVITY_MASK)
                assertTrue("Marge droite absente : $id", button.paddingEnd >= dp(6))
                val groupWidth = icon!!.bounds.width() + button.compoundDrawablePadding +
                    button.paint.measureText(button.text.toString())
                if (groupWidth <= button.width - dp(16)) {
                    val groupCenter = button.paddingStart + groupWidth / 2f
                    assertTrue("Ensemble logo/texte décentré : $id " +
                        "(centre=$groupCenter, attendu=${button.width / 2f})",
                        kotlin.math.abs(groupCenter - button.width / 2f) <= dp(3))
                } else {
                    assertTrue("Icône hors de sa cellule : $id",
                        button.paddingStart >= dp(6))
                }
            }

            for (id in intArrayOf(
                R.id.startButton, R.id.queueButton, R.id.pasteUrlButton,
                R.id.quickVideoButton, R.id.quickAudioButton, R.id.quickGifButton,
                R.id.quickPlaylistButton, R.id.quickTwitchButton
            )) verifyGroupedCenter(id)

            for (id in intArrayOf(R.id.homeTitleIcon, R.id.optionsTitleIcon,
                R.id.homeQueueTitleIcon, R.id.queuePageTitleIcon, R.id.filesPageTitleIcon,
                R.id.settingsPageTitleIcon, R.id.queueControlsTitleIcon,
                R.id.queueCleanupTitleIcon)) {
                val title = activity.findViewById<TextView>(id)
                assertNotNull("Logo de section perdu : $id",
                    title.compoundDrawablesRelative[0])
                assertEquals("Titre et logo non alignés verticalement : $id",
                    android.view.Gravity.CENTER_VERTICAL,
                    title.gravity and android.view.Gravity.VERTICAL_GRAVITY_MASK)
            }

            instrumentation.runOnMainSync {
                activity.findViewById<Button>(R.id.navSettings).performClick()
            }
            instrumentation.waitForIdleSync()
            val stacked = activity.resources.configuration.screenWidthDp < 390 ||
                activity.resources.configuration.fontScale > 1.2f
            if (!stacked) {
                for (id in intArrayOf(R.id.settingsTabDownload,
                    R.id.settingsTabApplication, R.id.settingsTabNetwork)) {
                    verifyGroupedCenter(id)
                }
            }
            for (id in intArrayOf(R.id.importCookiesButton, R.id.removeCookiesButton)) {
                val button = activity.findViewById<Button>(id)
                assertEquals("Grande action alignée à gauche : $id",
                    android.view.Gravity.START,
                    button.gravity and android.view.Gravity.RELATIVE_HORIZONTAL_GRAVITY_MASK)
                assertTrue("Gouttière gauche incohérente : $id",
                    button.paddingStart >= dp(12))
            }
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
        }
    }

    @Test fun captureMobilePagesForVisualReview() {
        val activity = instrumentation.startActivitySync(Intent(context, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)) as MainActivity
        val output = File(context.getExternalFilesDir(null), "ui-audit").apply { mkdirs() }
        try {
            val pages = listOf(R.id.navHome to "home", R.id.navQueue to "queue",
                R.id.navFiles to "folders", R.id.navSettings to "settings-media",
                R.id.settingsTabApplication to "settings-app", R.id.settingsTabNetwork to "settings-network")
            for ((id, name) in pages) {
                instrumentation.runOnMainSync { activity.findViewById<Button>(id).performClick() }
                instrumentation.waitForIdleSync()
                if (name == "settings-media") {
                    instrumentation.runOnMainSync { activity.findViewById<Button>(R.id.settingsTabDownload).performClick() }
                    instrumentation.waitForIdleSync()
                }
                // Finish the brief page transition before taking evidence.
                android.os.SystemClock.sleep(250)
                val bitmap = instrumentation.uiAutomation.takeScreenshot()
                assertNotNull("Capture indisponible : $name", bitmap)
                val file = File(output, "ui-audit-${activity.resources.configuration.fontScale}-$name.png")
                file.outputStream().use {
                    bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, it)
                }
                bitmap.recycle()
                // AGP may uninstall the target APK after the suite; public exports
                // remain available for the runner to collect as visual evidence.
                MediaExporter.export(context, file, "AUTRES") { false }
                file.delete()
            }
        } finally { instrumentation.runOnMainSync { activity.finish() } }
    }

    @Test fun settingsSelectorsAndAdvancedFieldsPersistDisplayedValues() {
        val activity = instrumentation.startActivitySync(Intent(context, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)) as MainActivity
        val prefs = DownloadOptions.get(context)
        val saved = prefs.all
        try {
            instrumentation.runOnMainSync { activity.findViewById<Button>(R.id.navSettings).performClick() }
            instrumentation.waitForIdleSync()
            fun views(view: View): List<View> = listOf(view) +
                if (view is android.view.ViewGroup) (0 until view.childCount)
                    .flatMap { views(view.getChildAt(it)) } else emptyList()
            val all = views(activity.findViewById(R.id.settingsPage))
            val choices = listOf(
                Triple("Format vidéo", "video_format", "MKV"),
                Triple("Qualité MP3", "audio_quality", "320K"),
                Triple("Segments à supprimer", "sponsor_remove", "none"),
                Triple("Navigateur annoncé (User-Agent)", "user_agent", "android_firefox"))
            for ((title, key, expected) in choices) {
                instrumentation.runOnMainSync {
                    activity.findViewById<Button>(if (key == "user_agent")
                        R.id.settingsTabNetwork else R.id.settingsTabDownload).performClick()
                }
                instrumentation.waitForIdleSync()
                val spinner = all.filterIsInstance<Spinner>()
                    .single { it.contentDescription?.toString() == title }
                instrumentation.runOnMainSync { spinner.setSelection(spinner.count - 1) }
                instrumentation.waitForIdleSync()
                assertEquals("Sélection non appliquée : $title", expected, prefs.getString(key, null))
            }
            instrumentation.runOnMainSync { activity.findViewById<Button>(R.id.settingsTabNetwork).performClick() }
            instrumentation.waitForIdleSync()
            for ((title, key, expected) in listOf(
                    Triple("Tentatives en cas d’erreur", "network_retries", 15),
                    Triple("Téléchargements de fragments simultanés", "fragments", 8),
                    Triple("Délai réseau (secondes)", "network_timeout", 60))) {
                val spinner = all.filterIsInstance<Spinner>()
                    .single { it.contentDescription?.toString() == title }
                instrumentation.runOnMainSync { spinner.setSelection(spinner.count - 1) }
                instrumentation.waitForIdleSync()
                assertEquals(expected, prefs.getInt(key, -1))
            }
            for ((title, key) in listOf("Adresse du proxy" to "proxy_url",
                    "Arguments d'extracteur avancés" to "extractor_args")) {
                val input = all.filterIsInstance<EditText>()
                    .single { it.contentDescription?.toString() == title }
                instrumentation.runOnMainSync { input.setText("x".repeat(600)) }
                assertEquals("Le champ doit respecter la limite du moteur.", 500, input.length())
                assertEquals("Valeur affichée différente de la valeur sauvée.", input.text.toString(),
                    prefs.getString(key, null))
            }
        } finally {
            val editor = prefs.edit().clear()
            saved.forEach { (key, value) -> when (value) {
                is Boolean -> editor.putBoolean(key, value)
                is Int -> editor.putInt(key, value)
                is Long -> editor.putLong(key, value)
                is Float -> editor.putFloat(key, value)
                is String -> editor.putString(key, value)
                is Set<*> -> editor.putStringSet(key, value.filterIsInstance<String>().toSet())
            } }
            editor.commit()
            instrumentation.runOnMainSync { activity.finish() }
        }
    }


    /**
     * Regression: the two similarly named update switches control different
     * features. App-engine updates must not disable APK announcements, and
     * the APK announcement switch must survive a fresh Activity instance.
     */
    @Test fun engineUpdateAndApkAlertsRemainIndependentAfterRelaunch() {
        val prefs = DownloadOptions.get(context)
        val savedEngine = if (prefs.contains("auto_update"))
            prefs.getBoolean("auto_update", true) else null
        val savedUiAlert = if (prefs.contains("update_alerts"))
            prefs.getBoolean("update_alerts", true) else null
        val savedApkAlert = AndroidUpdates.enabled(context)
        var activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java).addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        try {
            fun findAlertControl(root: View): android.widget.Switch? {
                if (root is android.widget.Switch &&
                    root.contentDescription?.toString() == "Me prévenir des nouvelles versions")
                    return root
                if (root is android.view.ViewGroup) {
                    for (index in 0 until root.childCount) {
                        findAlertControl(root.getChildAt(index))?.let { return it }
                    }
                }
                return null
            }
            fun openApplicationSettings() {
                instrumentation.runOnMainSync {
                    activity.findViewById<Button>(R.id.navSettings).performClick()
                    activity.findViewById<Button>(R.id.settingsTabApplication).performClick()
                }
                instrumentation.waitForIdleSync()
            }
            openApplicationSettings()
            val engine = activity.findViewById<android.widget.Switch>(R.id.autoUpdateCheck)
            val alerts = findAlertControl(activity.findViewById(R.id.settingsPage))
            assertNotNull("Le contrôle des mises à jour APK doit exister.", alerts)
            assertTrue("Le réglage moteur est inaccessible.", engine.isShown)
            assertTrue("Le réglage APK est inaccessible.", alerts!!.isShown)
            val initialEngine = engine.isChecked
            val initialAlerts = alerts.isChecked
            instrumentation.runOnMainSync {
                engine.performClick()
                alerts.performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals(!initialEngine, prefs.getBoolean("auto_update", initialEngine))
            assertEquals(!initialAlerts, AndroidUpdates.enabled(context))
            assertEquals(!initialAlerts, prefs.getBoolean("update_alerts", initialAlerts))
            instrumentation.runOnMainSync { activity.finish() }
            instrumentation.waitForIdleSync()

            activity = instrumentation.startActivitySync(
                Intent(context, MainActivity::class.java).addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
            ) as MainActivity
            openApplicationSettings()
            assertEquals("L'option yt-dlp doit persister après réouverture.", !initialEngine,
                activity.findViewById<android.widget.Switch>(R.id.autoUpdateCheck).isChecked)
            assertEquals("L'option APK doit persister après réouverture.", !initialAlerts,
                findAlertControl(activity.findViewById(R.id.settingsPage))?.isChecked)
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
            val edit = prefs.edit()
            if (savedEngine == null) edit.remove("auto_update")
            else edit.putBoolean("auto_update", savedEngine)
            if (savedUiAlert == null) edit.remove("update_alerts")
            else edit.putBoolean("update_alerts", savedUiAlert)
            edit.commit()
            AndroidUpdates.setEnabled(context, savedApkAlert)
        }
    }

    /** All five quick-access listeners remain connected after responsive reparenting. */
    @Test fun everyHomeShortcutChangesRealDownloadModeWithoutStartingTransfer() {
        val prefs = DownloadOptions.get(context)
        val savedMode = if (prefs.contains("last_mode"))
            prefs.getInt("last_mode", 0) else null
        val savedQuality = if (prefs.contains("last_quality"))
            prefs.getInt("last_quality", 0) else null
        val activity = instrumentation.startActivitySync(
            Intent(context, MainActivity::class.java).addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ) as MainActivity
        try {
            val modes = activity.findViewById<Spinner>(R.id.modeSpinner)
            val quality = activity.findViewById<Spinner>(R.id.qualitySpinner)
            val qualityGroup = activity.findViewById<View>(R.id.downloadQualityGroup)
            val shortcuts = listOf(
                R.id.quickVideoButton to 0,
                R.id.quickAudioButton to 1,
                R.id.quickGifButton to 4,
                R.id.quickPlaylistButton to 5
            )
            for ((buttonId, expectedMode) in shortcuts) {
                instrumentation.runOnMainSync {
                    activity.findViewById<Button>(buttonId).performClick()
                }
                instrumentation.waitForIdleSync()
                assertEquals("Raccourci déconnecté : $buttonId",
                    expectedMode, modes.selectedItemPosition)
                assertEquals("Le raccourci doit revenir à l'accueil.",
                    View.VISIBLE, activity.findViewById<View>(R.id.homePage).visibility)
                assertEquals(if (expectedMode == 1) View.GONE else View.VISIBLE,
                    qualityGroup.visibility)
            }
            instrumentation.runOnMainSync {
                modes.setSelection(3) // FLAC: quality is irrelevant.
            }
            instrumentation.waitForIdleSync()
            assertEquals(View.GONE, qualityGroup.visibility)
            instrumentation.runOnMainSync {
                quality.setSelection(2)
                activity.findViewById<Button>(R.id.quickTwitchButton).performClick()
            }
            instrumentation.waitForIdleSync()
            assertEquals("Twitch doit préparer un téléchargement vidéo.",
                0, modes.selectedItemPosition)
            assertEquals("Twitch doit revenir à la qualité 1080p par défaut.",
                0, quality.selectedItemPosition)
            assertEquals(View.VISIBLE, qualityGroup.visibility)
            assertFalse("Les raccourcis ne doivent pas lancer un transfert.",
                DownloadService.state.busy)
        } finally {
            instrumentation.runOnMainSync { activity.finish() }
            val edit = prefs.edit()
            if (savedMode == null) edit.remove("last_mode")
            else edit.putInt("last_mode", savedMode)
            if (savedQuality == null) edit.remove("last_quality")
            else edit.putInt("last_quality", savedQuality)
            edit.commit()
        }
    }

}
