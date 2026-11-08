package com.alldownload.android

import android.Manifest
import android.app.Activity
import android.content.ContentUris
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.FileProvider
import java.io.File

/**
 * Native Android adaptation of the Windows All-Download design:
 * #7c3aed accent, light/dark/OLED, real Windows logo, home/queue/files/settings.
 * No Windows executable, WebView2 or root storage permissions.
 */
class MainActivity : Activity() {
    companion object { private const val PICK_COOKIES = 441 }

    private data class Palette(
        val background: Int, val panel: Int, val input: Int, val border: Int,
        val foreground: Int, val muted: Int, val accent: Int
    )
    private val purple = Color.rgb(124, 58, 237)
    private val palePurple = Color.rgb(196, 181, 253)

    private val settings by lazy {
        getSharedPreferences("app_settings_v1", MODE_PRIVATE)
    }
    private fun themeChoice() = settings.getInt("theme", 0).coerceIn(0, 2)
    private fun palette(): Palette = when (themeChoice()) {
        1 -> Palette(Color.rgb(248, 250, 252), Color.WHITE,
            Color.rgb(241, 245, 249), Color.rgb(226, 232, 240),
            Color.rgb(15, 23, 42), Color.rgb(100, 116, 139), purple)
        2 -> Palette(Color.BLACK, Color.rgb(14, 14, 14),
            Color.rgb(20, 20, 20), Color.rgb(42, 42, 42),
            Color.WHITE, Color.rgb(161, 161, 170), palePurple)
        else -> Palette(Color.rgb(20, 20, 20), Color.rgb(33, 33, 33),
            Color.rgb(24, 24, 24), Color.rgb(53, 53, 53),
            Color.rgb(243, 244, 246), Color.rgb(161, 161, 170), palePurple)
    }

    private lateinit var scroll: ScrollView
    private lateinit var content: LinearLayout
    private lateinit var urlInput: EditText
    private lateinit var modeSpinner: Spinner
    private lateinit var qualitySpinner: Spinner
    private lateinit var themeSpinner: Spinner
    private lateinit var startButton: Button
    private lateinit var queueButton: Button
    private lateinit var cancelButton: Button
    private lateinit var pauseQueueButton: Button
    private lateinit var resumeQueueButton: Button
    private lateinit var clearFinishedButton: Button
    private lateinit var importCookiesButton: Button
    private lateinit var removeCookiesButton: Button
    private lateinit var cookieStatus: TextView
    private lateinit var statusText: TextView
    private lateinit var queueStatusText: TextView
    private lateinit var engineVersionText: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var queueList: LinearLayout
    private lateinit var filesList: LinearLayout

    private lateinit var homePage: LinearLayout
    private lateinit var queuePage: LinearLayout
    private lateinit var filesPage: LinearLayout
    private lateinit var settingsPage: LinearLayout
    private lateinit var tabs: List<Button>

    private var selectedTab = 0
    private var lastQueueSignature = ""
    private val handler = Handler(Looper.getMainLooper())
    private val refresh = object : Runnable {
        override fun run() {
            val state = DownloadService.state
            startButton.isEnabled = !state.busy
            cancelButton.isEnabled = state.busy
            pauseQueueButton.isEnabled = state.busy
            resumeQueueButton.isEnabled = !state.busy
            queueButton.isEnabled = true
            importCookiesButton.isEnabled = !state.busy
            removeCookiesButton.isEnabled = !state.busy && CookieStore.existing(this@MainActivity) != null
            progressBar.progress = state.progress
            statusText.text = state.message
            if (selectedTab == 1) renderQueue()
            handler.postDelayed(this, 750)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        when (themeChoice()) {
            1 -> setTheme(R.style.Theme_AllDownload_Light)
            2 -> setTheme(R.style.Theme_AllDownload_Oled)
            else -> setTheme(R.style.Theme_AllDownload)
        }
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        scroll = findViewById(R.id.scroll)
        content = findViewById(R.id.mainContent)
        urlInput = findViewById(R.id.urlInput)
        modeSpinner = findViewById(R.id.modeSpinner)
        qualitySpinner = findViewById(R.id.qualitySpinner)
        themeSpinner = findViewById(R.id.themeSpinner)
        startButton = findViewById(R.id.startButton)
        queueButton = findViewById(R.id.queueButton)
        cancelButton = findViewById(R.id.cancelButton)
        pauseQueueButton = findViewById(R.id.pauseQueueButton)
        resumeQueueButton = findViewById(R.id.resumeQueueButton)
        clearFinishedButton = findViewById(R.id.clearFinishedButton)
        importCookiesButton = findViewById(R.id.importCookiesButton)
        removeCookiesButton = findViewById(R.id.removeCookiesButton)
        statusText = findViewById(R.id.statusText)
        queueStatusText = findViewById(R.id.queueStatusText)
        engineVersionText = findViewById(R.id.engineVersionText)
        progressBar = findViewById(R.id.progressBar)
        cookieStatus = findViewById(R.id.cookieStatus)
        queueList = findViewById(R.id.queueList)
        filesList = findViewById(R.id.filesList)
        homePage = findViewById(R.id.homePage)
        queuePage = findViewById(R.id.queuePage)
        filesPage = findViewById(R.id.filesPage)
        settingsPage = findViewById(R.id.settingsPage)

        tabs = listOf(
            findViewById(R.id.navHome), findViewById(R.id.navQueue),
            findViewById(R.id.navFiles), findViewById(R.id.navSettings))
        tabs.forEachIndexed { index, button ->
            button.setOnClickListener { selectTab(index) }
        }

        val modes = listOf("Vidéo", "Audio MP3", "Audio M4A", "Audio FLAC",
            "GIF", "Playlist", "Chaîne")
        val qualities = listOf("1080p (Twitch : 1080p → 720p)",
            "720p", "480p", "Auto (meilleure)", "2160p")
        modeSpinner.adapter = spinnerAdapter(modes)
        qualitySpinner.adapter = spinnerAdapter(qualities)
        if (savedInstanceState == null) {
            modeSpinner.setSelection(settings.getInt("last_mode", 0).coerceIn(0, 6))
            qualitySpinner.setSelection(settings.getInt("last_quality", 0).coerceIn(0, 4))
        }
        modeSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) {}
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                settings.edit().putInt("last_mode", position).apply()
            }
        }
        qualitySpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) {}
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                settings.edit().putInt("last_quality", position).apply()
            }
        }
        themeSpinner.adapter = spinnerAdapter(listOf("Sombre", "Clair", "OLED noir"))
        themeSpinner.setSelection(themeChoice())
        themeSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) {}
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (position == themeChoice()) return
                settings.edit().putInt("theme", position).apply()
                recreate()
            }
        }

        startButton.setOnClickListener { submitUrl(DownloadService.ACTION_START) }
        queueButton.setOnClickListener { submitUrl(DownloadService.ACTION_ADD_QUEUE) }
        cancelButton.setOnClickListener {
            startService(Intent(this, DownloadService::class.java)
                .setAction(DownloadService.ACTION_CANCEL))
        }
        pauseQueueButton.setOnClickListener {
            startService(Intent(this, DownloadService::class.java)
                .setAction(DownloadService.ACTION_PAUSE))
        }
        resumeQueueButton.setOnClickListener {
            startService(Intent(this, DownloadService::class.java)
                .setAction(DownloadService.ACTION_RUN_QUEUE))
        }
        clearFinishedButton.setOnClickListener {
            DownloadQueue.clearFinished(this)
            lastQueueSignature = ""
            renderQueue()
        }
        findViewById<Button>(R.id.quickVideoButton).setOnClickListener {
            modeSpinner.setSelection(0)
            selectTab(0)
            urlInput.requestFocus()
        }
        findViewById<Button>(R.id.quickAudioButton).setOnClickListener {
            modeSpinner.setSelection(1)
            selectTab(0)
            urlInput.requestFocus()
        }

        findViewById<CheckBox>(R.id.autoUpdateCheck).apply {
            isChecked = settings.getBoolean("auto_update", true)
            setOnCheckedChangeListener { _, checked ->
                settings.edit().putBoolean("auto_update", checked).apply()
            }
        }
        importCookiesButton.setOnClickListener {
            val pick = Intent(Intent.ACTION_OPEN_DOCUMENT)
                .addCategory(Intent.CATEGORY_OPENABLE).setType("*/*")
            startActivityForResult(pick, PICK_COOKIES)
        }
        removeCookiesButton.setOnClickListener {
            if (CookieStore.delete(this)) {
                updateCookieStatus()
                Toast.makeText(this, "Cookies locaux supprimés.", Toast.LENGTH_SHORT).show()
            } else Toast.makeText(this, "Suppression impossible.", Toast.LENGTH_LONG).show()
        }
        updateCookieStatus()
        engineVersionText.text = "yt-dlp et FFmpeg intégrés • All-Download " + BuildConfig.VERSION_NAME
        AndroidSettingsPanels.populate(this, settingsPage) { message ->
            engineVersionText.text = message
            if (message.contains("est à jour") || message.startsWith("Vérification impossible"))
                Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        }
        applyPalette()
        processSharedUrl(intent)
        if (savedInstanceState != null) {
            urlInput.setText(savedInstanceState.getString("url", urlInput.text.toString()))
            modeSpinner.setSelection(savedInstanceState.getInt("mode", 0))
            qualitySpinner.setSelection(savedInstanceState.getInt("quality", 0))
            selectedTab = savedInstanceState.getInt("tab", 0).coerceIn(0, 3)
        }
        selectTab(selectedTab)
        configureWideScreen()
    }

    private fun spinnerAdapter(items: List<String>): ArrayAdapter<String> =
        object : ArrayAdapter<String>(this, R.layout.spinner_item, items) {
            override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
                val view = super.getView(position, convertView, parent)
                if (view is TextView) {
                    view.setTextColor(palette().foreground)
                    view.setBackgroundColor(palette().input)
                }
                return view
            }
            override fun getDropDownView(position: Int, convertView: View?,
                                         parent: ViewGroup): View {
                val view = super.getDropDownView(position, convertView, parent)
                if (view is TextView) {
                    view.setTextColor(palette().foreground)
                    view.setBackgroundColor(palette().panel)
                }
                return view
            }
        }.apply { setDropDownViewResource(R.layout.spinner_item) }

    private fun selectTab(tab: Int) {
        val changed = selectedTab != tab
        selectedTab = tab
        homePage.visibility = if (tab == 0) View.VISIBLE else View.GONE
        queuePage.visibility = if (tab == 1) View.VISIBLE else View.GONE
        filesPage.visibility = if (tab == 2) View.VISIBLE else View.GONE
        settingsPage.visibility = if (tab == 3) View.VISIBLE else View.GONE
        val colors = palette()
        tabs.forEachIndexed { index, button ->
            val selected = index == tab
            button.background = rounded(
                if (selected) purple else colors.panel,
                if (selected) purple else colors.border, 12)
            button.setTextColor(if (selected) Color.WHITE else colors.foreground)
            button.isAllCaps = false
        }
        if (tab == 1) {
            lastQueueSignature = ""
            renderQueue()
        } else if (tab == 2) renderFolders()
        else if (tab == 3) updateCookieStatus()
        if (changed && !settings.getBoolean("reduce_motion", false)) {
            val target = listOf(homePage, queuePage, filesPage, settingsPage)[tab]
            target.animate().cancel()
            target.alpha = 0f
            target.animate().alpha(1f).setDuration(180).start()
        }
        scroll.post { scroll.smoothScrollTo(0, 0) }
    }

    private fun submitUrl(action: String) {
        val url = urlInput.text.toString().trim()
        val parsed = try { Uri.parse(url) } catch (_: Exception) { null }
        if (parsed == null || parsed.scheme !in listOf("https", "http") ||
            parsed.host.isNullOrBlank() || parsed.userInfo != null) {
            urlInput.error = "Colle un lien HTTP(S) valide."
            return
        }
        if (Build.VERSION.SDK_INT <= 28 &&
            checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) !=
                PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE,
                Manifest.permission.WRITE_EXTERNAL_STORAGE), 102)
            Toast.makeText(this,
                "Autorise le stockage puis relance le téléchargement.", Toast.LENGTH_LONG).show()
            return
        }
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 103)
        }
        val service = Intent(this, DownloadService::class.java).apply {
            this.action = action
            putExtra(DownloadService.EXTRA_URL, url)
            putExtra(DownloadService.EXTRA_MODE, modeSpinner.selectedItemPosition)
            putExtra(DownloadService.EXTRA_QUALITY, qualitySpinner.selectedItemPosition)
        }
        if (action == DownloadService.ACTION_START && Build.VERSION.SDK_INT >= 26)
            startForegroundService(service)
        else startService(service)
        if (action == DownloadService.ACTION_ADD_QUEUE) selectTab(1)
    }

    private fun renderQueue() {
        val jobs = DownloadQueue.snapshot(this)
        val signature = jobs.joinToString("|") {
            it.id + ":" + it.status + ":" + it.progress + ":" + it.message
        }
        if (signature == lastQueueSignature) return
        lastQueueSignature = signature
        val colors = palette()
        queueList.removeAllViews()
        val waiting = jobs.count { it.status == DownloadQueue.WAITING }
        val running = jobs.count { it.status == DownloadQueue.RUNNING }
        val done = jobs.count { it.status == DownloadQueue.DONE }
        queueStatusText.text = jobs.size.toString() + " tâche(s) • " +
            waiting + " en attente • " + running + " en cours • " + done + " terminée(s)"
        if (jobs.isEmpty()) {
            queueList.addView(infoCard("La file est vide",
                "Depuis l'accueil, ajoutez une vidéo ou un audio pour commencer."))
            return
        }
        for (job in jobs.asReversed()) {
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(16), dp(15), dp(16), dp(12))
                background = rounded(colors.panel, colors.border, 18)
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                        bottomMargin = dp(11)
                    }
            }
            val label = when (job.status) {
                DownloadQueue.WAITING -> "En attente"
                DownloadQueue.RUNNING -> "En cours"
                DownloadQueue.PAUSED -> "En pause"
                DownloadQueue.DONE -> "Terminé"
                DownloadQueue.ERROR -> "Erreur"
                else -> "Annulé"
            }
            card.addView(text("•  " + label + "  ·  " +
                listOf("Vidéo", "MP3", "M4A", "FLAC", "GIF", "Playlist", "Chaîne")
                    .getOrElse(job.mode) { "Vidéo" }, 14,
                if (job.status == DownloadQueue.ERROR) Color.rgb(239, 68, 68)
                else if (job.status == DownloadQueue.DONE) Color.rgb(34, 197, 94)
                else purple, true))
            card.addView(text(job.url, 13, colors.foreground, false).apply {
                maxLines = 2
                ellipsize = android.text.TextUtils.TruncateAt.END
                setPadding(0, dp(9), 0, dp(7))
            })
            if (job.message.isNotBlank()) {
                card.addView(text(job.message, 12, colors.muted, false).apply {
                    maxLines = 3
                    ellipsize = android.text.TextUtils.TruncateAt.END
                })
            }
            if (job.progress > 0) {
                card.addView(ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
                    max = 100
                    progress = job.progress
                    progressTintList = ColorStateList.valueOf(purple)
                    layoutParams = LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT, dp(7)).apply {
                        topMargin = dp(12)
                    }
                })
            }
            val actions = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.END
            }
            if (job.status in listOf(DownloadQueue.PAUSED,
                    DownloadQueue.ERROR, DownloadQueue.CANCELLED)) {
                actions.addView(smallAction("↻ Réessayer") {
                    DownloadQueue.retry(this, job.id)
                    lastQueueSignature = ""
                    renderQueue()
                })
            }
            if (job.status != DownloadQueue.RUNNING) {
                actions.addView(smallAction("Supprimer") {
                    if (DownloadQueue.remove(this, job.id)) {
                        lastQueueSignature = ""
                        renderQueue()
                    }
                })
            }
            card.addView(actions)
            queueList.addView(card)
        }
    }

    private fun renderFolders() {
        filesList.removeAllViews()
        val categories = listOf(
            "VIDÉOS" to "▶", "AUDIOS" to "♫", "TWITCH" to "▣",
            "GIFS" to "▤", "CHAÎNES" to "▦", "PLAYLIST" to "☷", "AUTRES" to "◈")
        categories.forEach { (name, symbol) ->
            val files = filesForCategory(name)
            val item = infoCard(symbol + "  " + name,
                files.size.toString() + " fichier(s) · Téléchargements/All-Download/" + name)
            item.setOnClickListener { showFolderContents(name) }
            filesList.addView(item)
        }
    }

    private data class MediaEntry(val name: String, val uri: Uri)
    private fun filesForCategory(category: String): List<MediaEntry> {
        val results = mutableListOf<MediaEntry>()
        if (Build.VERSION.SDK_INT >= 29) {
            val columns = arrayOf(MediaStore.MediaColumns._ID,
                MediaStore.MediaColumns.DISPLAY_NAME)
            try {
                contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                    columns, MediaStore.MediaColumns.RELATIVE_PATH + "=?",
                    arrayOf(Environment.DIRECTORY_DOWNLOADS + "/All-Download/" + category + "/"),
                    MediaStore.MediaColumns.DATE_ADDED + " DESC")?.use { rows ->
                    while (rows.moveToNext()) {
                        results.add(MediaEntry(rows.getString(1),
                            ContentUris.withAppendedId(
                                MediaStore.Downloads.EXTERNAL_CONTENT_URI, rows.getLong(0))))
                    }
                }
            } catch (_: SecurityException) {}
        } else {
            @Suppress("DEPRECATION")
            val directory = File(Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS), "All-Download/" + category)
            directory.listFiles()?.filter { it.isFile }?.forEach {
                try {
                    results.add(MediaEntry(it.name, FileProvider.getUriForFile(this,
                        packageName + ".files", it)))
                } catch (_: Exception) {}
            }
        }
        return results
    }

    private fun showFolderContents(category: String) {
        filesList.removeAllViews()
        filesList.addView(smallAction("‹  Toutes les catégories") { renderFolders() })
        val media = filesForCategory(category)
        filesList.addView(infoCard(category,
            if (media.isEmpty()) "Aucun fichier dans ce dossier."
            else media.size.toString() + " fichier(s)"))
        media.take(150).forEach { entry ->
            val card = infoCard("◉  " + entry.name, "Toucher pour ouvrir")
            card.setOnClickListener {
                try {
                    startActivity(Intent(Intent.ACTION_VIEW).apply {
                        setDataAndType(entry.uri, MediaExporter.mediaMime(entry.name))
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    })
                } catch (_: Exception) {
                    Toast.makeText(this, "Aucune application disponible pour ce fichier.",
                        Toast.LENGTH_LONG).show()
                }
            }
            filesList.addView(card)
        }
        if (media.size > 150)
            filesList.addView(infoCard("Liste partielle",
                "150 premiers fichiers affichés. Tous restent dans le dossier All-Download."))
    }

    private fun infoCard(title: String, description: String): LinearLayout {
        val colors = palette()
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(17), dp(16), dp(17))
            background = rounded(colors.panel, colors.border, 17)
            layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(10) }
            addView(text(title, 17, colors.foreground, true))
            addView(text(description, 12, colors.muted, false).apply {
                setPadding(0, dp(7), 0, 0)
                maxLines = 3
                ellipsize = android.text.TextUtils.TruncateAt.END
            })
        }
    }

    private fun smallAction(label: String, action: () -> Unit): Button =
        Button(this).apply {
            text = label
            isAllCaps = false
            textSize = 12f
            minHeight = dp(42)
            minimumHeight = dp(42)
            setTextColor(palette().foreground)
            setOnClickListener { action() }
        }

    private fun text(value: String, size: Int, color: Int, bold: Boolean) =
        TextView(this).apply {
            text = value
            textSize = size.toFloat()
            setTextColor(color)
            if (bold) setTypeface(typeface, android.graphics.Typeface.BOLD)
        }

    private fun rounded(fill: Int, border: Int, radius: Int) =
        GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            setColor(fill)
            cornerRadius = dp(radius).toFloat()
            setStroke(dp(1), border)
        }

    private fun applyPalette() {
        val colors = palette()
        scroll.setBackgroundColor(colors.background)
        fun visit(view: View) {
            when (view) {
                is Button -> {
                    if (view.id == R.id.startButton ||
                        view.id == R.id.resumeQueueButton || view.tag == "primary") {
                        view.background = rounded(purple, purple, 13)
                        view.setTextColor(Color.WHITE)
                    } else {
                        view.setTextColor(colors.foreground)
                    }
                }
                is EditText -> {
                    view.background = rounded(colors.input, colors.border, 13)
                    view.setTextColor(colors.foreground)
                    view.setHintTextColor(colors.muted)
                }
                is TextView -> {
                    view.setTextColor(when (view.tag) {
                        "muted" -> colors.muted
                        "accent" -> colors.accent
                        else -> colors.foreground
                    })
                }
            }
            if (view.tag == "card") view.background = rounded(colors.panel, colors.border, 20)
            if (view.tag == "input" && view !is EditText) {
                view.background = rounded(colors.input, colors.border, 13)
            }
            if (view is ViewGroup) for (index in 0 until view.childCount)
                visit(view.getChildAt(index))
        }
        visit(content)
        progressBar.progressTintList = ColorStateList.valueOf(purple)
        progressBar.progressBackgroundTintList = ColorStateList.valueOf(colors.border)
        selectTab(selectedTab)
    }

    /** Two-column tablet/large foldable layout: left navigation and right content.
     * The same page instances and event listeners are re-used, not duplicated.
     */
    private fun configureWideScreen() {
        val widthDp = resources.configuration.screenWidthDp
        if (widthDp < 720) return
        content.layoutParams = content.layoutParams.apply {
            width = dp(widthDp.coerceAtMost(1200))
        }
        content.setPadding(dp(20), dp(24), dp(20), dp(40))
        val menu = findViewById<LinearLayout>(R.id.navigation)
        val bar = menu.parent as? android.widget.HorizontalScrollView ?: return
        bar.removeView(menu)
        content.removeView(bar)

        val pages = listOf(homePage, queuePage, filesPage, settingsPage)
        pages.forEach { content.removeView(it) }

        val split = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                    topMargin = dp(22)
                }
        }
        val sidebar = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(9), dp(10), dp(9), dp(12))
            background = rounded(palette().panel, palette().border, 19)
        }
        menu.orientation = LinearLayout.VERTICAL
        menu.layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT)
        tabs.forEach { button ->
            button.layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(52)).apply {
                    bottomMargin = dp(9)
                }
        }
        sidebar.addView(menu)
        split.addView(sidebar, LinearLayout.LayoutParams(dp(210),
            ViewGroup.LayoutParams.WRAP_CONTENT))
        val mainColumn = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(17), 0, 0, 0)
        }
        pages.forEach { page ->
            val original = page.layoutParams
            mainColumn.addView(page, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                    topMargin = dp(0)
                })
        }
        split.addView(mainColumn, LinearLayout.LayoutParams(0,
            ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        content.addView(split)
        selectTab(selectedTab)
    }

    @Deprecated("Android document picker callback")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != PICK_COOKIES || resultCode != RESULT_OK) return
        try {
            val uri = data?.data ?: return
            val input = contentResolver.openInputStream(uri)
                ?: throw java.io.IOException("Impossible de lire ce fichier.")
            CookieStore.importFromStream(this, input)
            updateCookieStatus()
            Toast.makeText(this, "Cookies enregistrés uniquement dans l’application.",
                Toast.LENGTH_LONG).show()
        } catch (error: Exception) {
            Toast.makeText(this, error.localizedMessage ?: "Import impossible.",
                Toast.LENGTH_LONG).show()
        }
    }

    private fun updateCookieStatus() {
        val exists = CookieStore.existing(this) != null
        cookieStatus.text = if (exists)
            "Session importée • stockage privé local"
        else "Aucun cookie importé • vidéos publiques"
        removeCookiesButton.isEnabled = exists
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        processSharedUrl(intent)
        selectTab(0)
    }

    private fun processSharedUrl(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND || intent.type != "text/plain") return
        val shared = intent.getStringExtra(Intent.EXTRA_TEXT).orEmpty()
        val candidate = Regex("https?://[^\\s<>]+").find(shared)?.value
        if (!candidate.isNullOrBlank()) urlInput.setText(candidate)
    }

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density + .5f).toInt()

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putString("url", urlInput.text.toString())
        outState.putInt("mode", modeSpinner.selectedItemPosition)
        outState.putInt("quality", qualitySpinner.selectedItemPosition)
        outState.putInt("tab", selectedTab)
        super.onSaveInstanceState(outState)
    }

    override fun onResume() {
        super.onResume()
        handler.removeCallbacks(refresh)
        handler.post(refresh)
        // GitHub Android prerelease check: only once every 12 h when enabled.
        AndroidUpdates.check(this)
    }

    override fun onPause() {
        handler.removeCallbacks(refresh)
        super.onPause()
    }
}
