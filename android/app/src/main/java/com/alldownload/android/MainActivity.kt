package com.alldownload.android

import android.Manifest
import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import java.util.concurrent.Executors
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
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
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
    private var settingsPanelsCreated = false
    private var lastQueueRevision = -1L
    private var lastHomeQueueRevision = -1L
    private lateinit var homeQueuePreview: LinearLayout
    private var queueVisible = 24
    private var lastDrawnState: DownloadService.UiState? = null
    private val fileExecutor = Executors.newSingleThreadExecutor()
    private var fileRequestId = 0
    private val handler = Handler(Looper.getMainLooper())
    /** Refresh only while visible, and touch views only when state changed. */
    private val refresh = object : Runnable {
        override fun run() {
            val state = DownloadService.state
            if (lastDrawnState != state) {
                if (lastDrawnState?.busy != state.busy) {
                    startButton.isEnabled = !state.busy
                    cancelButton.isEnabled = state.busy
                    pauseQueueButton.isEnabled = state.busy
                    resumeQueueButton.isEnabled = !state.busy
                    importCookiesButton.isEnabled = !state.busy
                    removeCookiesButton.isEnabled = !state.busy &&
                        CookieStore.existing(this@MainActivity) != null
                    cancelButton.visibility = if (state.busy) View.VISIBLE else View.GONE
                }
                if (lastDrawnState?.progress != state.progress)
                    progressBar.progress = state.progress
                if (lastDrawnState?.message != state.message)
                    statusText.text = state.message
                lastDrawnState = state
            }
            if (selectedTab == 1 && lastQueueRevision != DownloadQueue.revision())
                renderQueue()
            if (selectedTab == 0 && lastHomeQueueRevision != DownloadQueue.revision())
                renderHomeQueue()
            handler.postDelayed(this, when {
                state.busy -> 1800L
                selectedTab == 1 -> 3000L
                else -> 8000L
            })
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
        // Android 15+ enforces edge-to-edge for target SDK 35.
        if (Build.VERSION.SDK_INT >= 35) {
            ViewCompat.setOnApplyWindowInsetsListener(scroll) { view, insets ->
                val safe = insets.getInsets(WindowInsetsCompat.Type.systemBars() or
                    WindowInsetsCompat.Type.displayCutout())
                view.setPadding(safe.left, safe.top, safe.right, safe.bottom)
                insets
            }
            ViewCompat.requestApplyInsets(scroll)
        }
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
        homeQueuePreview = findViewById(R.id.homeQueuePreview)
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
                styleQuickModes()
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

        urlInput.setOnEditorActionListener { _, actionId, event ->
            val done = actionId == android.view.inputmethod.EditorInfo.IME_ACTION_DONE ||
                (event?.keyCode == android.view.KeyEvent.KEYCODE_ENTER &&
                    event.action == android.view.KeyEvent.ACTION_DOWN)
            if (done) {
                submitUrl(DownloadService.ACTION_ADD_QUEUE)
                true
            } else false
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
            lastQueueRevision = -1L
            renderQueue()
        }
        findViewById<Button>(R.id.clearFailedButton).setOnClickListener {
            DownloadQueue.clearStatuses(this, setOf(DownloadQueue.ERROR, DownloadQueue.CANCELLED))
            lastQueueRevision = -1L
            renderQueue()
        }
        findViewById<Button>(R.id.clearWaitingButton).setOnClickListener {
            DownloadQueue.clearStatuses(this, setOf(DownloadQueue.WAITING, DownloadQueue.PAUSED))
            lastQueueRevision = -1L
            renderQueue()
        }
        findViewById<Button>(R.id.openFullQueueButton).setOnClickListener {
            selectTab(1)
        }
        findViewById<Button>(R.id.pasteUrlButton).setOnClickListener {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val value = clipboard.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString()
                .orEmpty().trim()
            if (DownloadRules.isValidVideoUrl(value)) {
                urlInput.setText(value)
                urlInput.setSelection(value.length)
            } else Toast.makeText(this, "Aucune URL HTTP(S) valide à coller.",
                Toast.LENGTH_SHORT).show()
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
        listOf(R.id.quickGifButton to 4, R.id.quickPlaylistButton to 5,
            R.id.quickTwitchButton to 0).forEach { (buttonId, mode) ->
            findViewById<Button>(buttonId).setOnClickListener {
                modeSpinner.setSelection(mode)
                if (buttonId == R.id.quickTwitchButton) qualitySpinner.setSelection(0)
                selectTab(0)
                urlInput.requestFocus()
            }
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
        // Keep cold startup light: advanced settings are built only on first opening.
        applyPalette()
        processSharedUrl(intent)
        if (savedInstanceState != null) {
            urlInput.setText(savedInstanceState.getString("url", urlInput.text.toString()))
            modeSpinner.setSelection(savedInstanceState.getInt("mode", 0))
            qualitySpinner.setSelection(savedInstanceState.getInt("quality", 0))
            selectedTab = savedInstanceState.getInt("tab", 0).coerceIn(0, 3)
        }
        selectTab(selectedTab)
        // Keep a Windows-like sidebar on large tablets; phones dock the same tabs
        // below the content instead of spending vertical space above the URL field.
        if (resources.configuration.screenWidthDp >= 720) configureWideScreen()
        else configurePhoneNavigation()
        arrangeOptionPills()
        styleQuickModes()
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

    private fun ensureSettingsPanels() {
        if (settingsPanelsCreated) return
        settingsPanelsCreated = true
        AndroidSettingsPanels.populate(this, settingsPage) { message ->
            engineVersionText.text = message
            if (message.contains("est à jour") || message.startsWith("Vérification impossible"))
                Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        }
    }

    private fun selectTab(tab: Int) {
        val changed = selectedTab != tab
        selectedTab = tab
        homePage.visibility = if (tab == 0) View.VISIBLE else View.GONE
        queuePage.visibility = if (tab == 1) View.VISIBLE else View.GONE
        filesPage.visibility = if (tab == 2) View.VISIBLE else View.GONE
        settingsPage.visibility = if (tab == 3) View.VISIBLE else View.GONE
        if (tab == 3) ensureSettingsPanels()
        val colors = palette()
        tabs.forEachIndexed { index, button ->
            val selected = index == tab
            button.background = rounded(
                if (selected) purple else colors.input,
                if (selected) purple else colors.border, 12)
            button.setTextColor(if (selected) Color.WHITE else colors.foreground)
            button.isAllCaps = false
            button.stateListAnimator = null
            button.elevation = 0f
            button.contentDescription = when (index) {
                0 -> "Accueil"
                1 -> "File d'attente"
                2 -> "Dossiers"
                else -> "Paramètres"
            }
        }
        if (tab == 0) renderHomeQueue()
        if (tab == 1) {
            lastQueueRevision = -1L
            queueVisible = 24
            renderQueue()
        } else if (tab == 2) renderFolders()
        else if (tab == 3) updateCookieStatus()
        if (changed) {
            urlInput.clearFocus()
            (getSystemService(Context.INPUT_METHOD_SERVICE) as?
                android.view.inputmethod.InputMethodManager)
                ?.hideSoftInputFromWindow(urlInput.windowToken, 0)
        }
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
        urlInput.clearFocus()
        (getSystemService(Context.INPUT_METHOD_SERVICE) as?
            android.view.inputmethod.InputMethodManager)
            ?.hideSoftInputFromWindow(urlInput.windowToken, 0)
        val service = Intent(this, DownloadService::class.java).apply {
            this.action = action
            putExtra(DownloadService.EXTRA_URL, url)
            putExtra(DownloadService.EXTRA_MODE, modeSpinner.selectedItemPosition)
            putExtra(DownloadService.EXTRA_QUALITY, qualitySpinner.selectedItemPosition)
        }
        if (action == DownloadService.ACTION_START && Build.VERSION.SDK_INT >= 26)
            startForegroundService(service)
        else startService(service)
        // Windows' Add button keeps the central queue visible on the same page.
        // The dedicated queue tab remains available for complete management.
        if (action == DownloadService.ACTION_ADD_QUEUE) {
            lastHomeQueueRevision = -1L
            renderHomeQueue()
        }
    }

    /** Mini Windows-style file view on the home page, capped to three cheap cards. */
    private fun renderHomeQueue() {
        val revision = DownloadQueue.revision()
        if (revision == lastHomeQueueRevision) return
        lastHomeQueueRevision = revision
        val jobs = DownloadQueue.snapshot(this)
        homeQueuePreview.removeAllViews()
        if (jobs.isEmpty()) {
            homeQueuePreview.addView(LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                gravity = Gravity.CENTER
                setPadding(dp(12), dp(26), dp(12), dp(30))
                addView(text("↓", 34, palette().accent, true).apply {
                    gravity = Gravity.CENTER
                })
                addView(text("Votre file d'attente est vide", 15,
                    palette().foreground, true).apply {
                    gravity = Gravity.CENTER
                    setPadding(0, dp(8), 0, 0)
                })
                addView(text("Ajoutez des vidéos, playlists ou chaînes pour commencer.",
                    12, palette().muted, false).apply {
                    gravity = Gravity.CENTER
                    setPadding(0, dp(5), 0, 0)
                })
            })
            return
        }
        homeQueuePreview.addView(infoCard(
            jobs.size.toString() + " élément(s)",
            "En cours : " + jobs.count { it.status == DownloadQueue.RUNNING } +
                " · En attente : " + jobs.count { it.status == DownloadQueue.WAITING } +
                " · Terminés : " + jobs.count { it.status == DownloadQueue.DONE }))
        jobs.asReversed().take(5).forEach { job ->
            val stateLabel = when (job.status) {
                DownloadQueue.RUNNING -> "Téléchargement"
                DownloadQueue.WAITING -> "En attente"
                DownloadQueue.PAUSED -> "En pause"
                DownloadQueue.DONE -> "Terminé"
                DownloadQueue.ERROR -> "Échec"
                else -> "Annulé"
            }
            val shortUrl = job.url.take(92) + if (job.url.length > 92) "…" else ""
            val preview = infoCard(stateLabel + " · " + job.progress + " %", shortUrl)
            preview.setOnClickListener { selectTab(1) }
            homeQueuePreview.addView(preview)
        }
    }

    private fun renderQueue() {
        val jobs = DownloadQueue.snapshot(this)
        val revision = DownloadQueue.revision()
        if (revision == lastQueueRevision) return
        lastQueueRevision = revision
        val colors = palette()
        queueList.removeAllViews()
        val waiting = jobs.count { it.status == DownloadQueue.WAITING }
        val running = jobs.count { it.status == DownloadQueue.RUNNING }
        val done = jobs.count { it.status == DownloadQueue.DONE }
        queueStatusText.text = jobs.size.toString() + " tâche(s) • " +
            waiting + " en attente • " + running + " en cours • " + done + " terminée(s)"
        if (jobs.isEmpty()) {
            queueList.addView(LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                gravity = Gravity.CENTER
                setPadding(dp(12), dp(44), dp(12), dp(36))
                addView(text("↓", 40, colors.accent, true).apply {
                    gravity = Gravity.CENTER
                })
                addView(text("Votre file d'attente est vide", 17,
                    colors.foreground, true).apply {
                    gravity = Gravity.CENTER
                    setPadding(0, dp(8), 0, 0)
                })
                addView(text("Ajoutez un lien depuis l'accueil.", 12,
                    colors.muted, false).apply {
                    gravity = Gravity.CENTER
                    setPadding(0, dp(6), 0, 0)
                })
            })
            return
        }
        for (job in jobs.asReversed().take(queueVisible)) {
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(12), dp(12), dp(12), dp(12))
                background = rounded(colors.panel, colors.border, 16)
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
            // The Windows media-card silhouette, without expensive network thumbnails.
            // The badge uses the *actual* job media type and never invents metadata.
            val media = listOf("Vidéo", "MP3", "M4A", "FLAC", "GIF", "Playlist", "Chaîne")
                .getOrElse(job.mode) { "Vidéo" }
            val glyph = when (job.mode) {
                1, 2, 3 -> "♫"
                4 -> "GIF"
                5, 6 -> "☷"
                else -> "▶"
            }
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            val thumbnail = TextView(this).apply {
                text = glyph
                textSize = if (job.mode == 4) 15f else 26f
                gravity = Gravity.CENTER
                setTextColor(colors.accent)
                background = rounded(colors.input, colors.border, 11)
                contentDescription = "Type de média : $media"
            }
            row.addView(thumbnail, LinearLayout.LayoutParams(dp(56), dp(56)).apply {
                marginEnd = dp(12)
            })
            val details = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
            details.addView(text("$label · $media · ${job.progress} %", 13,
                if (job.status == DownloadQueue.ERROR) Color.rgb(239, 68, 68)
                else if (job.status == DownloadQueue.DONE) Color.rgb(34, 197, 94)
                else colors.accent, true))
            details.addView(text(job.url, 12, colors.foreground, false).apply {
                maxLines = 2
                ellipsize = android.text.TextUtils.TruncateAt.END
                setPadding(0, dp(6), 0, 0)
            })
            row.addView(details, LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            card.addView(row)
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
                    lastQueueRevision = -1L
                    renderQueue()
                })
            }
            if (job.status != DownloadQueue.RUNNING) {
                actions.addView(smallAction("Supprimer") {
                    if (DownloadQueue.remove(this, job.id)) {
                        lastQueueRevision = -1L
                        renderQueue()
                    }
                })
            }
            actions.addView(smallAction("Copier le lien") {
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE)
                    as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newPlainText("Lien All-Download", job.url))
                Toast.makeText(this, "Lien copié.", Toast.LENGTH_SHORT).show()
            })
            // Three actions may exceed 320dp; scroll only the action strip, not the card.
            val actionScroll = android.widget.HorizontalScrollView(this).apply {
                isHorizontalScrollBarEnabled = false
                isFillViewport = true
            }
            actionScroll.addView(actions, android.widget.FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT))
            card.addView(actionScroll, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                topMargin = dp(8)
            })
            queueList.addView(card)
        }
        if (jobs.size > queueVisible) {
            queueList.addView(smallAction(
                "Afficher plus (" + (jobs.size - queueVisible) + " restantes)") {
                queueVisible = (queueVisible + 24).coerceAtMost(jobs.size)
                lastQueueRevision = -1L
                renderQueue()
            })
        }
    }

    /** Android MediaStore and filesystem queries always run off the UI thread. */
    private fun renderFolders() {
        val request = ++fileRequestId
        filesList.removeAllViews()
        filesList.addView(infoCard("Dossiers All-Download", "Chargement des catégories…"))
        val categories = listOf(
            "VIDÉOS" to "▶", "AUDIOS" to "♫", "TWITCH" to "▣",
            "GIFS" to "▤", "CHAÎNES" to "▦", "PLAYLIST" to "☷", "AUTRES" to "◈")
        fileExecutor.execute {
            val counts = categories.map { (name, symbol) ->
                Triple(name, symbol, filesForCategory(name, 0).count)
            }
            runOnUiThread {
                if (request != fileRequestId || isFinishing || isDestroyed ||
                    selectedTab != 2) return@runOnUiThread
                filesList.removeAllViews()
                for ((name, symbol, count) in counts) {
                    val item = infoCard(symbol + "  " + name,
                        "$count fichier(s) · Téléchargements/All-Download/" + name)
                    item.setOnClickListener { showFolderContents(name) }
                    filesList.addView(item)
                }
            }
        }
    }

    private data class MediaEntry(val name: String, val uri: Uri)
    private data class FolderResult(val count: Int, val entries: List<MediaEntry>)

    private fun filesForCategory(category: String, limit: Int): FolderResult {
        val results = ArrayList<MediaEntry>(limit)
        if (Build.VERSION.SDK_INT >= 29) {
            val columns = arrayOf(MediaStore.MediaColumns._ID,
                MediaStore.MediaColumns.DISPLAY_NAME)
            try {
                contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                    columns, MediaStore.MediaColumns.RELATIVE_PATH + "=?",
                    arrayOf(Environment.DIRECTORY_DOWNLOADS + "/All-Download/" + category + "/"),
                    MediaStore.MediaColumns.DATE_ADDED + " DESC")?.use { rows ->
                    val total = rows.count
                    while (results.size < limit && rows.moveToNext()) {
                        results.add(MediaEntry(rows.getString(1),
                            ContentUris.withAppendedId(
                                MediaStore.Downloads.EXTERNAL_CONTENT_URI, rows.getLong(0))))
                    }
                    return FolderResult(total, results)
                }
            } catch (_: Exception) {
                return FolderResult(0, emptyList())
            }
        } else {
            @Suppress("DEPRECATION")
            val directory = File(Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS), "All-Download/" + category)
            val all = directory.listFiles()?.filter { it.isFile } ?: emptyList()
            if (limit > 0) {
                for (file in all.take(limit)) {
                    try {
                        results.add(MediaEntry(file.name,
                            FileProvider.getUriForFile(this, packageName + ".files", file)))
                    } catch (_: Exception) {}
                }
            }
            return FolderResult(all.size, results)
        }
        return FolderResult(0, emptyList())
    }

    private fun showFolderContents(category: String, limit: Int = 50) {
        val request = ++fileRequestId
        filesList.removeAllViews()
        filesList.addView(infoCard(category, "Chargement des fichiers…"))
        fileExecutor.execute {
            val folder = filesForCategory(category, limit)
            runOnUiThread {
                if (request != fileRequestId || isFinishing || isDestroyed ||
                    selectedTab != 2) return@runOnUiThread
                filesList.removeAllViews()
                filesList.addView(smallAction("‹  Toutes les catégories") { renderFolders() })
                filesList.addView(infoCard(category,
                    if (folder.count == 0) "Aucun fichier dans ce dossier."
                    else "${folder.count} fichier(s)"))
                folder.entries.forEach { entry ->
                    val card = infoCard("◉  " + entry.name, "Toucher pour ouvrir")
                    card.setOnClickListener {
                        try {
                            startActivity(Intent(Intent.ACTION_VIEW).apply {
                                setDataAndType(entry.uri, MediaExporter.mediaMime(entry.name))
                                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                            })
                        } catch (_: Exception) {
                            Toast.makeText(this,
                                "Aucune application disponible pour ce fichier.",
                                Toast.LENGTH_LONG).show()
                        }
                    }
                    filesList.addView(card)
                }
                if (folder.count > limit)
                    filesList.addView(smallAction(
                        "Afficher plus (" + (folder.count - limit) + " restants)") {
                        showFolderContents(category, (limit + 50).coerceAtMost(2000))
                    })
            }
        }
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
            background = rounded(palette().input, palette().border, 10)
            elevation = 0f
            stateListAnimator = null
            setPadding(dp(9), 0, dp(9), 0)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(42)).apply {
                marginStart = dp(4)
            }
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
                        view.elevation = 0f
                        view.stateListAnimator = null
                    } else {
                        view.background = rounded(colors.input, colors.border, 13)
                        view.setTextColor(colors.foreground)
                        view.elevation = 0f
                        view.stateListAnimator = null
                    }
                    view.isAllCaps = false
                    view.setPadding(dp(12), view.paddingTop, dp(12), view.paddingBottom)
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
            if (view.tag == "card") {
                view.background = rounded(colors.panel, colors.border, 18)
                view.elevation = 0f
            }
            if (view.tag == "input" && view !is EditText) {
                view.background = rounded(colors.input, colors.border, 13)
            }
            if (view is ViewGroup) for (index in 0 until view.childCount)
                visit(view.getChildAt(index))
        }
        visit(content)
        findViewById<View>(R.id.navigation).background = rounded(colors.panel, colors.border, 16)
        styleQuickModes()
        progressBar.progressTintList = ColorStateList.valueOf(purple)
        progressBar.progressBackgroundTintList = ColorStateList.valueOf(colors.border)
        selectTab(selectedTab)
    }


    /** Use the exact same action IDs/listeners on every device: presentation only. */
    private fun styleQuickModes() {
        if (!::modeSpinner.isInitialized) return
        val colors = palette()
        val selected = modeSpinner.selectedItemPosition
        // Video resolutions do not apply to audio-only extraction. Keep the
        // setting saved, but never show an irrelevant 1080p selector for MP3/FLAC.
        findViewById<View>(R.id.downloadQualityGroup)?.visibility =
            if (selected in 1..3) View.GONE else View.VISIBLE
        val modes = listOf(R.id.quickVideoButton to 0, R.id.quickAudioButton to 1,
            R.id.quickGifButton to 4, R.id.quickPlaylistButton to 5,
            R.id.quickTwitchButton to -1)
        modes.forEach { (id, mode) ->
            val button = findViewById<Button>(id) ?: return@forEach
            val active = mode == selected ||
                (id == R.id.quickAudioButton && selected in 1..3)
            button.background = rounded(
                if (active) purple else colors.input,
                if (active) purple else colors.border, 12)
            button.setTextColor(if (active) Color.WHITE else colors.foreground)
            button.elevation = 0f
            button.stateListAnimator = null
        }
    }

    /** Compact Windows option pair on tablets/foldables; stacked, readable on phones. */
    private fun arrangeOptionPills() {
        val options = findViewById<LinearLayout>(R.id.downloadOptions)
        val mode = findViewById<LinearLayout>(R.id.downloadModeGroup)
        val quality = findViewById<LinearLayout>(R.id.downloadQualityGroup)
        if (resources.configuration.screenWidthDp >= 580) {
            options.orientation = LinearLayout.HORIZONTAL
            mode.layoutParams = LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
            quality.layoutParams = LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(10)
                topMargin = 0
            }
        } else {
            options.orientation = LinearLayout.VERTICAL
            mode.layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            quality.layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                topMargin = dp(8)
            }
        }
    }

    /**
     * Phone shell: main content scrolls, while the Windows-inspired four-section
     * control bar remains accessible at the bottom. No duplicate action buttons.
     * The original navigation View is moved; all click listeners remain attached.
     */
    private fun configurePhoneNavigation() {
        val menu = findViewById<LinearLayout>(R.id.navigation)
        val bar = menu.parent as? android.widget.HorizontalScrollView ?: return
        val host = scroll.parent as? ViewGroup ?: return
        // Capture the footer before detaching ScrollView from the Activity root;
        // Activity.findViewById cannot find children of a detached view hierarchy.
        val footer = homePage.findViewById<LinearLayout>(R.id.statusFooterCard)
        content.removeView(bar)
        host.removeView(scroll)

        val shell = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(palette().background)
        }
        shell.addView(scroll, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        // Windows has a persistent status/progress strip. Reparent that exact
        // already-bound view; downloads and their progress observers stay intact.
        (footer.parent as? ViewGroup)?.removeView(footer)
        footer.setPadding(dp(12), dp(7), dp(12), dp(8))
        shell.addView(footer, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            marginStart = dp(8)
            marginEnd = dp(8)
            bottomMargin = dp(6)
        })

        // HorizontalScrollView extends FrameLayout: its direct child must keep
        // FrameLayout.LayoutParams (LinearLayout.LayoutParams crashes onMeasure).
        menu.layoutParams = android.widget.FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        tabs.forEachIndexed { index, button ->
            button.minWidth = 0
            button.minimumWidth = 0
            button.textSize = 11f
            button.text = listOf("Accueil", "File", "Dossiers", "Réglages")[index]
            button.layoutParams = LinearLayout.LayoutParams(0, dp(48), 1f).apply {
                marginStart = dp(2)
                marginEnd = dp(2)
            }
        }
        bar.background = rounded(palette().panel, palette().border, 0)
        bar.setPadding(dp(7), dp(6), dp(7), dp(6))
        bar.isFillViewport = true
        shell.addView(bar, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        host.addView(shell, ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))

        // Android 15+ edge-to-edge: bottom navigation must sit above the gesture bar.
        if (Build.VERSION.SDK_INT >= 35) {
            ViewCompat.setOnApplyWindowInsetsListener(scroll) { view, insets ->
                val safe = insets.getInsets(WindowInsetsCompat.Type.systemBars() or
                    WindowInsetsCompat.Type.displayCutout())
                view.setPadding(safe.left, safe.top, safe.right, 0)
                insets
            }
            ViewCompat.setOnApplyWindowInsetsListener(bar) { view, insets ->
                val safe = insets.getInsets(WindowInsetsCompat.Type.systemBars() or
                    WindowInsetsCompat.Type.displayCutout())
                view.setPadding(dp(7) + safe.left, dp(6),
                    dp(7) + safe.right, dp(6) + safe.bottom)
                insets
            }
            ViewCompat.requestApplyInsets(shell)
        }
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
        // Resume only a user-authorized APK installation after Android's settings screen.
        AndroidApkInstaller.onResume(this)
        // GitHub prerelease updates are cached for 30 minutes and never open a browser.
        AndroidUpdates.check(this)
    }

    override fun onPause() {
        handler.removeCallbacks(refresh)
        super.onPause()
    }

    override fun onDestroy() {
        handler.removeCallbacks(refresh)
        fileRequestId++
        fileExecutor.shutdownNow()
        super.onDestroy()
    }
}
