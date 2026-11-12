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
import android.graphics.drawable.LayerDrawable
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
import android.widget.EditText
import android.widget.ImageView
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
        else -> Palette(Color.rgb(17, 18, 24), Color.rgb(27, 28, 36),
            Color.rgb(35, 36, 46), Color.rgb(51, 53, 66),
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
    private var updateBanner: AndroidUpdateBanner? = null

    private var selectedTab = 0
    private var phoneKeyboardVisible = false
    private var settingsPanelsCreated = false
    private var lastQueueRevision = -1L
    private var lastHomeQueueRevision = -1L
    private lateinit var homeQueuePreview: LinearLayout
    private var queueVisible = 24
    private var queueCleanupExpanded = false
    // Fallback only when Android's clipboard is inaccessible immediately after an in-app copy.
    private var recentCopiedUrl = ""
    private var recentCopiedAt = 0L
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
                    updatePhoneStatusDock()
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
        val qualities = listOf("1080p (sinon 720p)",
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
        queueCleanupExpanded =
            savedInstanceState?.getBoolean("queueCleanupExpanded", false) ?: false
        findViewById<Button>(R.id.queueCleanupToggle).setOnClickListener {
            queueCleanupExpanded = !queueCleanupExpanded
            updateQueueCleanupVisibility()
        }
        updateQueueCleanupVisibility()
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
            val systemValue = try {
                clipboard.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString()
                    .orEmpty().trim()
            } catch (_: SecurityException) { "" }
            val age = android.os.SystemClock.elapsedRealtime() - recentCopiedAt
            val value = if (DownloadRules.isValidVideoUrl(systemValue)) systemValue
                else if (age in 0..60_000L && DownloadRules.isValidVideoUrl(recentCopiedUrl))
                    recentCopiedUrl else ""
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

        findViewById<android.widget.Switch>(R.id.autoUpdateCheck).apply {
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
        if (savedInstanceState != null) {
            urlInput.setText(savedInstanceState.getString("url", urlInput.text.toString()))
            modeSpinner.setSelection(savedInstanceState.getInt("mode", 0))
            qualitySpinner.setSelection(savedInstanceState.getInt("quality", 0))
            selectedTab = savedInstanceState.getInt("tab", 0).coerceIn(0, 3)
        }
        processSharedUrl(intent)
        selectTab(selectedTab)
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED &&
            !settings.getBoolean("notifications_prompted", false)) {
            settings.edit().putBoolean("notifications_prompted", true).apply()
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 103)
        }
        // Keep a Windows-like sidebar on large tablets; phones dock the same tabs
        // below the content instead of spending vertical space above the URL field.
        if (resources.configuration.screenWidthDp >= 600) configureWideScreen()
        else configurePhoneNavigation()
        attachUpdateBanner()
        arrangeOptionPills()
        arrangeQuickAccess()
        configureResponsiveActions()
        styleQuickModes()
    }

    private fun spinnerAdapter(items: List<String>): ArrayAdapter<String> =
        object : ArrayAdapter<String>(this, R.layout.spinner_item, items) {
            override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
                val view = super.getView(position, convertView, parent)
                if (view is TextView) {
                    view.setTextColor(palette().foreground)
                    view.gravity = Gravity.CENTER_VERTICAL
                    view.setSingleLine(true)
                    view.ellipsize = android.text.TextUtils.TruncateAt.END
                    view.setPadding(dp(14), 0, dp(10), 0)
                }
                return view
            }
            override fun getDropDownView(position: Int, convertView: View?,
                                         parent: ViewGroup): View {
                val view = super.getDropDownView(position, convertView, parent)
                if (view is TextView) {
                    view.setTextColor(palette().foreground)
                    view.setPadding(dp(14), dp(12), dp(14), dp(12))
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
        styleNavigation()
        // Show the compact progress dock only during an active transfer.
        updatePhoneStatusDock()
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
        // Switching tabs must cancel stale scroll positions immediately: an
        // animated scroll could leave the previous tab at the wrong offset.
        scroll.scrollTo(0, 0)
        scroll.post { scroll.scrollTo(0, 0) }
    }

    private fun submitUrl(action: String) {
        val url = urlInput.text.toString().trim()
        val parsed = try { Uri.parse(url) } catch (_: Exception) { null }
        if (parsed == null || parsed.scheme !in listOf("https", "http") ||
            parsed.host.isNullOrBlank() || parsed.userInfo != null) {
            urlInput.error = "Colle un lien HTTP(S) valide."
            return
        }
        // Clear the previous validation popup as soon as a valid link is submitted.
        urlInput.error = null
        if (Build.VERSION.SDK_INT <= 28 &&
            checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) !=
                PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE,
                Manifest.permission.WRITE_EXTERNAL_STORAGE), 102)
            Toast.makeText(this,
                "Autorise le stockage puis relance le téléchargement.", Toast.LENGTH_LONG).show()
            return
        }
        if (action == DownloadService.ACTION_START && Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 103)
        }
        urlInput.clearFocus()
        (getSystemService(Context.INPUT_METHOD_SERVICE) as?
            android.view.inputmethod.InputMethodManager)
            ?.hideSoftInputFromWindow(urlInput.windowToken, 0)
        if (action == DownloadService.ACTION_ADD_QUEUE) {
            // Adding is a local queue edit. Waiting for onStartCommand could make
            // the immediate preview miss the new task until the next 8s refresh.
            try {
                DownloadQueue.enqueue(this, url, modeSpinner.selectedItemPosition,
                    qualitySpinner.selectedItemPosition)
                lastHomeQueueRevision = -1L
                renderHomeQueue()
                Toast.makeText(this, "Ajouté à la file d’attente.", Toast.LENGTH_SHORT).show()
            } catch (error: Exception) {
                urlInput.error = error.localizedMessage ?: "Impossible d'ajouter le lien."
            }
            return
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
                setPadding(dp(12), dp(15), dp(12), dp(17))
                addView(ImageView(this@MainActivity).apply {
                    setImageResource(R.drawable.ic_download)
                    imageTintList = ColorStateList.valueOf(palette().accent)
                    contentDescription = "File vide"
                }, LinearLayout.LayoutParams(dp(28), dp(28)))
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
        jobs.asReversed().take(3).forEach { job ->
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

    /** Keep destructive/bulk queue actions available without crowding the main list. */
    private fun updateQueueCleanupVisibility() {
        findViewById<View>(R.id.queueCleanupActions).visibility =
            if (queueCleanupExpanded) View.VISIBLE else View.GONE
        findViewById<Button>(R.id.queueCleanupToggle).apply {
            text = if (queueCleanupExpanded) "Masquer les options de nettoyage"
                else "Afficher les options de nettoyage"
            contentDescription = text
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
                setPadding(dp(18), dp(30), dp(18), dp(30))
                background = rounded(colors.panel, colors.border, 18)
                addView(ImageView(this@MainActivity).apply {
                    setImageResource(R.drawable.ic_playlist)
                    imageTintList = ColorStateList.valueOf(colors.accent)
                    contentDescription = "Aucun téléchargement"
                }, LinearLayout.LayoutParams(dp(32), dp(32)))
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
                setPadding(dp(16), dp(16), dp(16), dp(15))
                background = rounded(colors.panel, colors.border, 18)
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                        bottomMargin = dp(20)
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
            val mediaIcon = when (job.mode) {
                1, 2, 3 -> R.drawable.ic_audio
                4 -> R.drawable.ic_gif
                5 -> R.drawable.ic_playlist
                6 -> R.drawable.ic_stream
                else -> R.drawable.ic_video
            }
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            val thumbnail = ImageView(this).apply {
                setImageResource(mediaIcon)
                imageTintList = ColorStateList.valueOf(colors.accent)
                background = rounded(colors.input, colors.border, 12)
                setPadding(dp(11), dp(11), dp(11), dp(11))
                contentDescription = "Type de média : $media"
            }
            row.addView(thumbnail, LinearLayout.LayoutParams(dp(46), dp(46)).apply {
                marginEnd = dp(12)
            })
            val details = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
            val statusRow = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            statusRow.addView(text("$label · $media", 12,
                if (job.status == DownloadQueue.ERROR) Color.rgb(239, 68, 68)
                else if (job.status == DownloadQueue.DONE) Color.rgb(34, 197, 94)
                else colors.accent, true).apply {
                maxLines = 1
                ellipsize = android.text.TextUtils.TruncateAt.END
            }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            statusRow.addView(text("${job.progress} %", 12, colors.muted, true),
                LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT).apply { marginStart = dp(8) })
            details.addView(statusRow)
            details.addView(text(job.url, 13, colors.foreground, false).apply {
                maxLines = 2
                ellipsize = android.text.TextUtils.TruncateAt.END
                setPadding(0, dp(7), 0, 0)
            })
            row.addView(details, LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            card.addView(row)
            if (job.message.isNotBlank()) {
                card.addView(text(job.message, 12, colors.muted, false).apply {
                    maxLines = 3
                    ellipsize = android.text.TextUtils.TruncateAt.END
                }, LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                    topMargin = dp(12)
                })
            }
            if (job.progress > 0) {
                card.addView(ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
                    max = 100
                    progress = job.progress
                    progressTintList = ColorStateList.valueOf(purple)
                    layoutParams = LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT, dp(4)).apply {
                        topMargin = dp(10)
                    }
                })
            }
            // Distinct button footer: no horizontal scrolling or clipped labels.
            // The same queue actions and listeners are preserved on every device.
            val footer = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
            }
            if (job.status in listOf(DownloadQueue.PAUSED,
                    DownloadQueue.ERROR, DownloadQueue.CANCELLED)) {
                footer.addView(smallAction("Réessayer", R.drawable.ic_retry) {
                    DownloadQueue.retry(this, job.id)
                    lastQueueRevision = -1L
                    renderQueue()
                }.apply {
                    layoutParams = LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT, dp(48)).apply {
                        bottomMargin = dp(10)
                    }
                })
            }
            val actions = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            fun appendAction(label: String, icon: Int, onClick: () -> Unit) {
                val action = smallAction(label, icon, onClick)
                actions.addView(action, LinearLayout.LayoutParams(0, dp(48), 1f).apply {
                    if (actions.childCount > 0) marginStart = dp(10)
                })
            }
            if (job.status != DownloadQueue.RUNNING) {
                appendAction("Supprimer", R.drawable.ic_trash) {
                    if (DownloadQueue.remove(this, job.id)) {
                        lastQueueRevision = -1L
                        renderQueue()
                    }
                }
            }
            appendAction("Copier", R.drawable.ic_copy) {
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE)
                    as ClipboardManager
                try {
                    clipboard.setPrimaryClip(ClipData.newPlainText("Lien All-Download", job.url))
                    recentCopiedUrl = job.url
                    recentCopiedAt = android.os.SystemClock.elapsedRealtime()
                    Toast.makeText(this, "Lien copié.", Toast.LENGTH_SHORT).show()
                } catch (_: SecurityException) {
                    Toast.makeText(this, "Presse-papiers inaccessible.", Toast.LENGTH_LONG).show()
                }
            }
            adaptActionRow(actions)
            footer.addView(actions)
            card.addView(View(this).apply {
                setBackgroundColor(colors.border)
            }, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(1)).apply {
                topMargin = dp(15)
            })
            card.addView(footer, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                topMargin = dp(12)
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
        val categories = listOf("VIDÉOS", "AUDIOS", "TWITCH", "GIFS",
            "CHAÎNES", "PLAYLIST", "AUTRES")
        fileExecutor.execute {
            val counts = categories.map { name ->
                name to filesForCategory(name, 0).count
            }
            runOnUiThread {
                if (request != fileRequestId || isFinishing || isDestroyed ||
                    selectedTab != 2) return@runOnUiThread
                filesList.removeAllViews()
                for ((name, count) in counts) {
                    val item = mediaCard(name, "$count fichier(s)", folderIcon(name))
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
                filesList.addView(smallAction("Dossiers", R.drawable.ic_back) { renderFolders() })
                filesList.addView(infoCard(category,
                    if (folder.count == 0) "Aucun fichier dans ce dossier."
                    else "${folder.count} fichier(s)"))
                folder.entries.forEach { entry ->
                    val card = mediaCard(entry.name, "Ouvrir", when {
                        entry.name.endsWith(".mp3", true) ||
                            entry.name.endsWith(".m4a", true) ||
                            entry.name.endsWith(".flac", true) -> R.drawable.ic_audio
                        entry.name.endsWith(".mp4", true) ||
                            entry.name.endsWith(".mkv", true) ||
                            entry.name.endsWith(".webm", true) -> R.drawable.ic_video
                        entry.name.endsWith(".gif", true) -> R.drawable.ic_gif
                        else -> R.drawable.ic_file
                    })
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

    /** Vector icon tiles make folders and files align exactly on all screens. */
    private fun folderIcon(category: String): Int = when (category) {
        "VIDÉOS" -> R.drawable.ic_folder_video
        "AUDIOS" -> R.drawable.ic_folder_audio
        "TWITCH" -> R.drawable.ic_folder_twitch
        "GIFS" -> R.drawable.ic_folder_gif
        "CHAÎNES" -> R.drawable.ic_folder_channel
        "PLAYLIST" -> R.drawable.ic_folder_playlist
        else -> R.drawable.ic_folder_other
    }

    private fun mediaCard(title: String, subtitle: String, iconRes: Int): LinearLayout {
        val colors = palette()
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            minimumHeight = dp(76)
            setPadding(dp(14), dp(10), dp(14), dp(10))
            background = rounded(colors.panel, colors.border, 17)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(9) }
            addView(ImageView(this@MainActivity).apply {
                setImageResource(iconRes)
                imageTintList = ColorStateList.valueOf(colors.accent)
                scaleType = ImageView.ScaleType.FIT_CENTER
                setPadding(dp(9), dp(9), dp(9), dp(9))
                background = rounded(colors.input, colors.border, 13)
                contentDescription = null
            }, LinearLayout.LayoutParams(dp(50), dp(50)).apply { marginEnd = dp(13) })
            val detail = LinearLayout(this@MainActivity).apply {
                orientation = LinearLayout.VERTICAL
                addView(text(title, 15, colors.foreground, true).apply {
                    maxLines = 1
                    ellipsize = android.text.TextUtils.TruncateAt.END
                })
                addView(text(subtitle, 12, colors.muted, false).apply {
                    maxLines = 1
                    ellipsize = android.text.TextUtils.TruncateAt.END
                    setPadding(0, dp(4), 0, 0)
                })
            }
            addView(detail, LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            addView(ImageView(this@MainActivity).apply {
                setImageResource(R.drawable.ic_chevron)
                imageTintList = ColorStateList.valueOf(colors.muted)
                contentDescription = null
            }, LinearLayout.LayoutParams(dp(18), dp(18)).apply { marginStart = dp(8) })
        }
    }

    private fun infoCard(title: String, description: String): LinearLayout {
        val colors = palette()
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(15), dp(13), dp(15), dp(13))
            background = rounded(colors.panel, colors.border, 17)
            layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(10) }
            addView(text(title, 15, colors.foreground, true))
            addView(text(description, 12, colors.muted, false).apply {
                setPadding(0, dp(7), 0, 0)
                maxLines = 3
                ellipsize = android.text.TextUtils.TruncateAt.END
            })
        }
    }

    private fun smallAction(label: String, iconRes: Int = 0, action: () -> Unit): Button =
        Button(this).apply {
            text = label
            isAllCaps = false
            textSize = 12f
            minHeight = dp(48)
            minimumHeight = dp(48)
            setTextColor(palette().foreground)
            background = rounded(palette().input, palette().border, 10)
            elevation = 0f
            stateListAnimator = null
            setPadding(dp(10), 0, dp(10), 0)
            if (iconRes != 0) setButtonIcon(this, iconRes, palette().foreground, 16)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(48)).apply {
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


    /** Low-power native Liquid Glass: translucent gradient, rim and static highlight. */
    private fun glassSurface(sidebar: Boolean = false): android.graphics.drawable.Drawable {
        val light = themeChoice() == 1
        val oled = themeChoice() == 2
        val radius = dp(if (sidebar) 22 else 30).toFloat()
        val shades = when {
            light -> intArrayOf(Color.argb(248,255,255,255),
                Color.argb(232,243,238,251), Color.argb(245,235,230,249))
            oled -> intArrayOf(Color.argb(242,44,34,62),
                Color.argb(234,18,17,26), Color.argb(248,8,8,14))
            else -> intArrayOf(Color.argb(242,54,43,82),
                Color.argb(233,34,30,53), Color.argb(248,23,23,37))
        }
        val base = GradientDrawable(GradientDrawable.Orientation.TL_BR, shades).apply {
            cornerRadius = radius
            setStroke(dp(1), if (light) Color.argb(171,202,189,226)
                else Color.argb(130,149,130,185))
        }
        val shine = GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
            intArrayOf(if (light) Color.argb(112,255,255,255)
                else Color.argb(65,255,255,255), Color.TRANSPARENT)).apply {
            cornerRadius = radius
        }
        return LayerDrawable(arrayOf(base, shine)).apply {
            setLayerInset(1, dp(2), dp(2), dp(2), dp(2))
        }
    }

    private fun navigationPill(selected: Boolean): GradientDrawable {
        if (!selected) return rounded(Color.TRANSPARENT, Color.TRANSPARENT, 22)
        return GradientDrawable(GradientDrawable.Orientation.TL_BR, intArrayOf(
            Color.rgb(135,80,238), Color.rgb(101,55,201))).apply {
            cornerRadius = dp(22).toFloat()
            setStroke(dp(1), Color.argb(150,210,193,255))
        }
    }

    private fun styleNavigation() {
        val wide = resources.configuration.screenWidthDp >= 600
        val colors = palette()
        val icons = intArrayOf(R.drawable.nav_home, R.drawable.nav_queue,
            R.drawable.nav_folders, R.drawable.nav_settings)
        val shortNames = arrayOf("Accueil", "File", "Dossiers", "Réglages")
        val fullNames = arrayOf("Accueil", "File d'attente", "Dossiers", "Réglages")
        tabs.forEachIndexed { index, button ->
            val foreground = if (index == selectedTab) Color.WHITE else colors.foreground
            val icon = getDrawable(icons[index])?.mutate()?.apply {
                setTint(foreground)
                setBounds(0, 0, dp(21), dp(21))
            }
            if (wide) {
                button.setCompoundDrawablesRelative(icon, null, null, null)
                button.gravity = Gravity.CENTER_VERTICAL or Gravity.START
                button.text = if (resources.configuration.screenWidthDp < 840)
                    shortNames[index] else fullNames[index]
                button.textSize = 13f
                button.setPadding(dp(16), 0, dp(8), 0)
                button.compoundDrawablePadding = dp(11)
            } else {
                button.setCompoundDrawablesRelative(null, icon, null, null)
                button.gravity = Gravity.CENTER
                button.text = shortNames[index]
                button.textSize = 11f
                button.setPadding(0, dp(6), 0, dp(6))
                button.compoundDrawablePadding = dp(5)
            }
            button.backgroundTintList = null
            button.background = navigationPill(index == selectedTab)
            button.setTextColor(foreground)
            button.isAllCaps = false
            button.setSingleLine(true)
            button.ellipsize = android.text.TextUtils.TruncateAt.END
            button.includeFontPadding = false
            button.stateListAnimator = null
            button.elevation = 0f
            button.minWidth = 0
            button.minHeight = 0
            button.contentDescription = fullNames[index]
        }
    }

    /** Windows-style Material section glyphs, rendered as native tinted vectors. */
    private fun styleSectionHeaders() {
        val tint = palette().accent
        val sections = listOf(
            R.id.homeTitleIcon to R.drawable.ic_queue_add,
            R.id.optionsTitleIcon to R.drawable.ic_sliders,
            R.id.homeQueueTitleIcon to R.drawable.nav_queue,
            R.id.queuePageTitleIcon to R.drawable.nav_queue,
            R.id.queueControlsTitleIcon to R.drawable.ic_play,
            R.id.queueCleanupTitleIcon to R.drawable.ic_trash,
            R.id.queueItemsTitleIcon to R.drawable.ic_playlist,
            R.id.filesPageTitleIcon to R.drawable.nav_folders,
            R.id.settingsPageTitleIcon to R.drawable.nav_settings,
            R.id.quickAccessTitleIcon to R.drawable.ic_playlist,
            R.id.statusFooterTitleIcon to R.drawable.ic_download,
            R.id.settingsAppearanceTitleIcon to R.drawable.ic_sliders,
            R.id.settingsEngineTitleIcon to R.drawable.ic_download,
            R.id.settingsCookiesTitleIcon to R.drawable.ic_security
        )
        sections.forEach { (labelId, iconId) ->
            findViewById<TextView>(labelId)?.apply {
                val icon = getDrawable(iconId)?.mutate()?.apply {
                    setTint(tint)
                    setBounds(0, 0, dp(19), dp(19))
                }
                setCompoundDrawablesRelative(icon, null, null, null)
                compoundDrawablePadding = dp(9)
                gravity = Gravity.CENTER_VERTICAL or Gravity.START
                minHeight = dp(26)
                includeFontPadding = false
                maxLines = 2
                ellipsize = android.text.TextUtils.TruncateAt.END
            }
        }
    }

    private fun applyPalette() {
        val colors = palette()
        scroll.setBackgroundColor(colors.background)
        fun visit(view: View) {
            when (view) {
                is Button -> {
                    if (view.id == R.id.startButton ||
                        view.id == R.id.resumeQueueButton || view.tag == "primary") {
                        view.background = rounded(purple, purple, 14)
                        view.setTextColor(Color.WHITE)
                        view.elevation = 0f
                        view.stateListAnimator = null
                    } else {
                        view.background = rounded(colors.input, colors.border, 14)
                        view.setTextColor(colors.foreground)
                        view.elevation = 0f
                        view.stateListAnimator = null
                    }
                    view.isAllCaps = false
                    view.setPadding(dp(12), view.paddingTop, dp(12), view.paddingBottom)
                }
                is EditText -> {
                    view.background = rounded(colors.input, colors.border, 14)
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
                view.background = rounded(colors.panel, colors.border, 17)
                view.elevation = 0f
            }
            if (view.tag == "input" && view !is EditText) {
                view.background = rounded(colors.input, colors.border, 14)
            }
            if (view is ViewGroup) for (index in 0 until view.childCount)
                visit(view.getChildAt(index))
        }
        visit(content)
        styleSectionHeaders()
        findViewById<View>(R.id.navigation).setBackgroundColor(Color.TRANSPARENT)
        styleQuickModes()
        styleActionIcons()
        progressBar.progressTintList = ColorStateList.valueOf(purple)
        progressBar.progressBackgroundTintList = ColorStateList.valueOf(colors.border)
        statusText.maxLines = 1
        statusText.ellipsize = android.text.TextUtils.TruncateAt.END
        queueStatusText.maxLines = 2
        queueStatusText.ellipsize = android.text.TextUtils.TruncateAt.END
        selectTab(selectedTab)
    }


    /** The same vector weight and baseline on all Android devices and themes. */
    private fun setButtonIcon(button: Button, iconRes: Int, tint: Int, size: Int = 18) {
        val icon = getDrawable(iconRes)?.mutate()?.apply {
            setTint(tint)
            setBounds(0, 0, dp(size), dp(size))
        }
        button.setCompoundDrawablesRelative(icon, null, null, null)
        button.compoundDrawablePadding = dp(7)
        button.includeFontPadding = false
        button.isAllCaps = false
        button.setSingleLine(true)
        button.ellipsize = android.text.TextUtils.TruncateAt.END
        button.minWidth = 0
        button.minimumWidth = 0
        MobileIconLabel.centered(button, dp(7))
    }

    private fun styleActionIcons() {
        val foreground = palette().foreground
        listOf(
            Triple(R.id.startButton, R.drawable.ic_download, Color.WHITE),
            Triple(R.id.queueButton, R.drawable.ic_queue_add, foreground),
            Triple(R.id.pasteUrlButton, R.drawable.ic_paste, foreground),
            Triple(R.id.resumeQueueButton, R.drawable.ic_play, Color.WHITE),
            Triple(R.id.pauseQueueButton, R.drawable.ic_pause, foreground),
            Triple(R.id.cancelButton, R.drawable.ic_stop, foreground),
            Triple(R.id.openFullQueueButton, R.drawable.nav_queue, foreground),
            Triple(R.id.queueCleanupToggle, R.drawable.ic_sliders, foreground),
            Triple(R.id.clearFinishedButton, R.drawable.ic_done, foreground),
            Triple(R.id.clearFailedButton, R.drawable.ic_error, foreground),
            Triple(R.id.clearWaitingButton, R.drawable.ic_waiting, foreground),
            Triple(R.id.importCookiesButton, R.drawable.ic_file, foreground),
            Triple(R.id.removeCookiesButton, R.drawable.ic_trash, foreground)
        ).forEach { (id, icon, tint) ->
            val button = findViewById<Button>(id)
            setButtonIcon(button, icon, tint, if (id == R.id.pasteUrlButton) 16 else 18)
            // These full-width actions intentionally use consistent leading
            // icon/text alignment, unlike the centred compact shortcuts.
            if (id == R.id.resumeQueueButton || id == R.id.pauseQueueButton ||
                id == R.id.clearFinishedButton || id == R.id.clearFailedButton ||
                id == R.id.clearWaitingButton || id == R.id.queueCleanupToggle ||
                id == R.id.importCookiesButton || id == R.id.removeCookiesButton) {
                MobileIconLabel.leading(button, dp(15), dp(9))
                button.compoundDrawablePadding = dp(9)
                button.textSize = 13f
            }
        }
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
        val icons = mapOf(
            R.id.quickVideoButton to R.drawable.ic_video,
            R.id.quickAudioButton to R.drawable.ic_audio,
            R.id.quickGifButton to R.drawable.ic_gif,
            R.id.quickPlaylistButton to R.drawable.ic_playlist,
            R.id.quickTwitchButton to R.drawable.ic_stream
        )
        modes.forEach { (id, mode) ->
            val button = findViewById<Button>(id) ?: return@forEach
            val active = mode == selected ||
                (id == R.id.quickAudioButton && selected in 1..3)
            button.background = rounded(
                if (active) purple else colors.input,
                if (active) purple else colors.border, 18)
            button.setTextColor(if (active) Color.WHITE else colors.foreground)
            button.elevation = 0f
            button.stateListAnimator = null
            setButtonIcon(button, icons.getValue(id),
                if (active) Color.WHITE else colors.foreground, 17)
        }
    }

    /**
     * Keep all five Windows-style shortcuts simultaneously visible on narrow
     * phones and medium foldables: 3 equal cells + 2 equal cells.
     * Reparent the original Buttons, preserving all actual download listeners.
     * Wide tablets retain the single compact row from the XML layout.
     */
    private fun arrangeQuickAccess() {
        if (resources.configuration.screenWidthDp >= 900) return
        val group = findViewById<LinearLayout>(R.id.quickModesRow)
        val ids = listOf(
            R.id.quickVideoButton, R.id.quickAudioButton, R.id.quickGifButton,
            R.id.quickPlaylistButton, R.id.quickTwitchButton
        )
        val items = ids.map { findViewById<Button>(it) }
        items.forEach { (it.parent as? ViewGroup)?.removeView(it) }
        group.removeAllViews()
        group.orientation = LinearLayout.VERTICAL
        group.layoutParams = android.widget.FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        (group.parent as? android.widget.HorizontalScrollView)?.isFillViewport = true

        fun addRow(buttons: List<Button>, second: Boolean) {
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            group.addView(row, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                if (second) topMargin = dp(7)
            })
            buttons.forEachIndexed { index, button ->
                button.minWidth = 0
                button.minimumWidth = 0
                button.textSize = 12f
                button.setSingleLine(true)
                button.ellipsize = android.text.TextUtils.TruncateAt.END
                button.layoutParams = LinearLayout.LayoutParams(0, dp(48), 1f).apply {
                    if (index > 0) marginStart = dp(7)
                }
                row.addView(button)
            }
        }
        addRow(items.take(3), false)
        addRow(items.drop(3), true)
    }

    /** Compact Windows option pair on tablets/foldables; stacked, readable on phones. */
    /** Reflow the original buttons using their available width, including on foldables.
     * Keep the same instances and listeners; enlarged system text needs taller rows.
     */
    private fun adaptActionRow(row: LinearLayout) {
        fun reflow() {
            if (row.width <= 0) return
            val stacked = row.width - row.paddingLeft - row.paddingRight < dp(300) ||
                resources.configuration.fontScale > 1.2f
            val height = dp((52 * resources.configuration.fontScale.coerceAtLeast(1f))
                .toInt().coerceAtMost(104))
            val signature = "actions:$stacked:$height"
            if (row.tag == signature) return
            row.tag = signature
            row.orientation = if (stacked) LinearLayout.VERTICAL else LinearLayout.HORIZONTAL
            for (index in 0 until row.childCount) {
                val button = row.getChildAt(index) as? Button ?: continue
                button.setSingleLine(false)
                button.maxLines = 2
                button.minWidth = 0
                button.minimumWidth = 0
                button.layoutParams = LinearLayout.LayoutParams(
                    if (stacked) ViewGroup.LayoutParams.MATCH_PARENT else 0,
                    height, if (stacked) 0f else 1f).apply {
                    if (index > 0) {
                        if (stacked) topMargin = dp(12) else marginStart = dp(12)
                    }
                }
            }
        }
        row.addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ -> reflow() }
        row.post { reflow() }
    }

    private fun configureResponsiveActions() {
        listOf(R.id.startButton, R.id.resumeQueueButton, R.id.clearFailedButton)
            .forEach { id -> adaptActionRow(findViewById<Button>(id).parent as LinearLayout) }
        // These labels can span two lines on a compact phone or with enlarged text.
        listOf(R.id.queueCleanupToggle, R.id.clearFinishedButton,
            R.id.openFullQueueButton).forEach { id ->
            findViewById<Button>(id).apply {
                setSingleLine(false)
                maxLines = 2
                minimumHeight = dp(52)
                layoutParams = layoutParams.apply {
                    height = ViewGroup.LayoutParams.WRAP_CONTENT
                }
                setPadding(paddingLeft, dp(10), paddingRight, dp(10))
            }
        }
    }

    private fun arrangeOptionPills() {
        val options = findViewById<LinearLayout>(R.id.downloadOptions)
        val mode = findViewById<LinearLayout>(R.id.downloadModeGroup)
        val quality = findViewById<LinearLayout>(R.id.downloadQualityGroup)
        if (resources.configuration.screenWidthDp >= 900) {
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
    private fun updatePhoneStatusDock() {
        if (resources.configuration.screenWidthDp >= 600) return
        val footer = findViewById<View>(R.id.statusFooterCard)
        if (footer.parent == homePage) return
        footer.visibility = if (!phoneKeyboardVisible && selectedTab < 2 &&
            DownloadService.state.busy) View.VISIBLE else View.GONE
    }

    private fun configurePhoneNavigation() {
        val menu = findViewById<LinearLayout>(R.id.navigation)
        val oldScrollBar = menu.parent as? android.widget.HorizontalScrollView ?: return
        val host = scroll.parent as? ViewGroup ?: return
        val footer = homePage.findViewById<LinearLayout>(R.id.statusFooterCard)

        // HorizontalScrollView measures its child at unconstrained width.
        // That pushed the first/last tabs off screen on narrow phones.
        // Replace the holder, not the four original buttons/listeners.
        oldScrollBar.removeView(menu)
        content.removeView(oldScrollBar)
        host.removeView(scroll)
        val shell = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(palette().background)
        }
        shell.addView(scroll, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        (footer.parent as? ViewGroup)?.removeView(footer)
        footer.background = glassSurface()
        footer.setPadding(dp(13), dp(7), dp(13), dp(7))
        footer.findViewById<TextView>(R.id.statusFooterTitleIcon).textSize = 12f
        footer.findViewById<TextView>(R.id.statusText).textSize = 12f
        progressBar.layoutParams = progressBar.layoutParams.apply { height = dp(3) }
        shell.addView(footer, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            marginStart = dp(12)
            marginEnd = dp(12)
            bottomMargin = dp(6)
        })

        val navDock = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(5), dp(5), dp(5), dp(5))
            background = glassSurface()
            elevation = dp(4).toFloat()
        }
        menu.orientation = LinearLayout.HORIZONTAL
        menu.setBackgroundColor(Color.TRANSPARENT)
        tabs.forEach { button ->
            button.layoutParams = LinearLayout.LayoutParams(0, dp(64), 1f).apply {
                marginStart = dp(1)
                marginEnd = dp(1)
            }
        }
        navDock.addView(menu, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, dp(64)))
        shell.addView(navDock, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            marginStart = dp(12)
            marginEnd = dp(12)
            bottomMargin = dp(10)
        })
        host.addView(shell, ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))

        // The phone shell owns system insets; the dock sits above gesture navigation.
        // Hide fixed controls while the keyboard is open to leave input room.
        ViewCompat.setOnApplyWindowInsetsListener(shell) { view, insets ->
            val safe = insets.getInsets(WindowInsetsCompat.Type.systemBars() or
                WindowInsetsCompat.Type.displayCutout())
            phoneKeyboardVisible = insets.isVisible(WindowInsetsCompat.Type.ime())
            navDock.visibility = if (phoneKeyboardVisible) View.GONE else View.VISIBLE
            updatePhoneStatusDock()
            if (Build.VERSION.SDK_INT >= 35)
                view.setPadding(safe.left, safe.top, safe.right,
                    if (phoneKeyboardVisible) 0 else safe.bottom)
            insets
        }
        ViewCompat.setOnApplyWindowInsetsListener(scroll) { view, insets ->
            // Insets are handled exactly once by the containing phone shell.
            view.setPadding(0, 0, 0, 0)
            insets
        }
        ViewCompat.requestApplyInsets(shell)
        updatePhoneStatusDock()
        styleNavigation()
    }

    /**
     * No permanent brand/header chrome: the Android app's identity lives in
     * its launcher icon, package label and update dialog. Keep only a
     * dismissible update notice, inline with the page and GONE at rest.
     * This avoids a dead band at the top on phones and unfolded devices.
     */
    private fun attachUpdateBanner() {
        val banner = AndroidUpdateBanner(this)
        updateBanner = banner
        content.addView(banner.view, 0, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            bottomMargin = dp(10)
        })
    }

    /** Two-column tablet/large foldable layout: left navigation and right content.
     * The same page instances and event listeners are re-used, not duplicated.
     */
    private fun configureWideScreen() {
        val widthDp = resources.configuration.screenWidthDp
        if (widthDp < 600) return
        content.layoutParams = content.layoutParams.apply {
            width = ViewGroup.LayoutParams.MATCH_PARENT
        }
        content.setPadding(dp(16), dp(20), dp(16), dp(32))
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
                    topMargin = dp(16)
                }
        }
        val sidebar = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(9), dp(10), dp(9), dp(12))
            background = glassSurface(sidebar = true)
            elevation = dp(4).toFloat()
        }
        menu.orientation = LinearLayout.VERTICAL
        menu.layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT)
        tabs.forEach { button ->
            button.layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(48)).apply {
                    bottomMargin = dp(6)
                }
        }
        menu.setBackgroundColor(Color.TRANSPARENT)
        sidebar.addView(menu)
        split.addView(sidebar, LinearLayout.LayoutParams(dp(if (widthDp < 840) 172 else 210),
            ViewGroup.LayoutParams.WRAP_CONTENT))
        val mainColumn = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(if (widthDp < 840) 10 else 17), 0, 0, 0)
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
        if (intent?.action != Intent.ACTION_SEND) return
        val url = SharedVideoLinks.extract(intent)
        if (url != null) {
            selectedTab = 0
            urlInput.setText(url)
            urlInput.setSelection(url.length)
        } else {
            Toast.makeText(this,
                "Partage le lien de la vidéo (HTTP/HTTPS), pas le fichier local.",
                Toast.LENGTH_LONG).show()
        }
    }

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density + .5f).toInt()

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putString("url", urlInput.text.toString())
        outState.putInt("mode", modeSpinner.selectedItemPosition)
        outState.putInt("quality", qualitySpinner.selectedItemPosition)
        outState.putInt("tab", selectedTab)
        outState.putBoolean("queueCleanupExpanded", queueCleanupExpanded)
        super.onSaveInstanceState(outState)
    }

    override fun onResume() {
        super.onResume()
        handler.removeCallbacks(refresh)
        handler.post(refresh)
        DownloadService.showOpenNotification(this)
        // Resume only a user-authorized APK installation after Android's settings screen.
        AndroidApkInstaller.onResume(this)
        // Like Kovelyx: restore a pinned banner immediately, then refresh from GitHub.
        // Installation remains inside All-Download until Android requests user approval.
        updateBanner?.onReturnToApp()
        updateBanner?.show(AndroidUpdates.cachedCandidate(this))
        AndroidUpdates.check(this, onRelease = { release -> updateBanner?.show(release) })
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 103 && grantResults.firstOrNull() ==
            PackageManager.PERMISSION_GRANTED && !isFinishing) {
            DownloadService.showOpenNotification(this)
        }
    }

    override fun onPause() {
        // Keep the lightweight "Fermer" action in the shade while this task is
        // still in Recents. Only the UI polling pauses; no idle service runs.
        handler.removeCallbacks(refresh)
        super.onPause()
    }

    override fun onDestroy() {
        handler.removeCallbacks(refresh)
        fileRequestId++
        fileExecutor.shutdownNow()
        DownloadService.hideOpenNotification(this)
        super.onDestroy()
    }
}
