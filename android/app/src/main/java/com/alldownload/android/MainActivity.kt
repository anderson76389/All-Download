package com.alldownload.android

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {
    private lateinit var urlInput: EditText
    private lateinit var modeSpinner: Spinner
    private lateinit var qualitySpinner: Spinner
    private lateinit var startButton: Button
    private lateinit var cancelButton: Button
    private lateinit var progressBar: ProgressBar
    private lateinit var statusText: TextView

    private val handler = Handler(Looper.getMainLooper())
    private val refresh = object : Runnable {
        override fun run() {
            val state = DownloadService.state
            startButton.isEnabled = !state.busy
            cancelButton.isEnabled = state.busy
            progressBar.progress = state.progress
            statusText.text = state.message
            handler.postDelayed(this, 650)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        urlInput = findViewById(R.id.urlInput)
        modeSpinner = findViewById(R.id.modeSpinner)
        qualitySpinner = findViewById(R.id.qualitySpinner)
        startButton = findViewById(R.id.startButton)
        cancelButton = findViewById(R.id.cancelButton)
        progressBar = findViewById(R.id.progressBar)
        statusText = findViewById(R.id.statusText)

        modeSpinner.adapter = ArrayAdapter(
            this, R.layout.spinner_item,
            listOf("Vidéo", "Audio MP3", "Audio M4A", "Audio FLAC", "GIF", "Playlist", "Chaîne")
        ).apply { setDropDownViewResource(R.layout.spinner_item) }
        qualitySpinner.adapter = ArrayAdapter(
            this, R.layout.spinner_item,
            listOf("1080p (Twitch : 1080p → 720p)", "720p", "480p", "Auto (meilleure)", "2160p")
        ).apply { setDropDownViewResource(R.layout.spinner_item) }

        startButton.setOnClickListener { start() }
        cancelButton.setOnClickListener {
            startService(Intent(this, DownloadService::class.java).setAction(DownloadService.ACTION_CANCEL))
        }
        processSharedUrl(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        processSharedUrl(intent)
    }

    private fun processSharedUrl(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND || intent.type != "text/plain") return
        val text = intent.getStringExtra(Intent.EXTRA_TEXT).orEmpty()
        val candidate = Regex("https?://[^\\s<>]+").find(text)?.value
        if (!candidate.isNullOrBlank()) urlInput.setText(candidate)
    }

    private fun start() {
        val url = urlInput.text.toString().trim()
        val parsed = try { Uri.parse(url) } catch (_: Exception) { null }
        if (parsed == null || parsed.scheme !in listOf("https", "http")
            || parsed.host.isNullOrBlank() || parsed.userInfo != null) {
            urlInput.error = "Colle un lien HTTP(S) valide."
            return
        }
        if (Build.VERSION.SDK_INT <= 28 &&
            checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE, Manifest.permission.WRITE_EXTERNAL_STORAGE), 102)
            Toast.makeText(this, "Autorise le stockage puis relance le téléchargement.", Toast.LENGTH_LONG).show()
            return
        }
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 103)
        }
        val service = Intent(this, DownloadService::class.java).apply {
            action = DownloadService.ACTION_START
            putExtra(DownloadService.EXTRA_URL, url)
            putExtra(DownloadService.EXTRA_MODE, modeSpinner.selectedItemPosition)
            putExtra(DownloadService.EXTRA_QUALITY, qualitySpinner.selectedItemPosition)
        }
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(service) else startService(service)
    }

    override fun onResume() {
        super.onResume()
        handler.removeCallbacks(refresh)
        handler.post(refresh)
    }

    override fun onPause() {
        handler.removeCallbacks(refresh)
        super.onPause()
    }
}
