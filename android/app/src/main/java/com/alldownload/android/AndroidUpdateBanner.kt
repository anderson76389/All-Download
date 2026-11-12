package com.alldownload.android

import android.app.Activity
import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView

/**
 * Native pinned update banner, like Kovelyx. No WebView, browser or polling.
 * The actual APK is downloaded into private app storage, verified and handed
 * to Android's system installer for the user's approval.
 */
internal class AndroidUpdateBanner(private val activity: Activity) {
    companion object {
        private const val PREFS = "android_update_banner_v1"
        private const val DISMISSED = "dismissed_release"
    }
    private val prefs = activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val density = activity.resources.displayMetrics.density
    private fun px(dp: Int) = (dp * density + .5f).toInt()
    private val theme = activity.getSharedPreferences("app_settings_v1", Context.MODE_PRIVATE)
        .getInt("theme", 0)
    private val light = theme == 1
    private val foreground = if (light) Color.rgb(15, 23, 42) else Color.WHITE
    private val muted = if (light) Color.rgb(100, 116, 139) else Color.rgb(181, 182, 195)
    private val purple = Color.rgb(124, 58, 237)
    private val panel = if (light) Color.WHITE
        else if (theme == 2) Color.rgb(14, 14, 14) else Color.rgb(27, 28, 36)
    private val border = if (light) Color.rgb(226, 232, 240)
        else if (theme == 2) Color.rgb(50, 50, 50) else Color.rgb(61, 61, 76)
    private var release: AndroidUpdates.Release? = null
    private var downloading = false
    private var latestMessage = ""

    private fun background(fill: Int, edge: Int, radius: Int) =
        GradientDrawable().apply {
            setColor(fill)
            cornerRadius = px(radius).toFloat()
            setStroke(px(1), edge)
        }

    private fun label(text: String, size: Float, color: Int, strong: Boolean = false) =
        TextView(activity).apply {
            this.text = text
            textSize = size
            setTextColor(color)
            includeFontPadding = false
            if (strong) setTypeface(typeface, Typeface.BOLD)
            maxLines = 2
            ellipsize = android.text.TextUtils.TruncateAt.END
        }

    val view = LinearLayout(activity).apply {
        orientation = LinearLayout.VERTICAL
        visibility = View.GONE
        background = background(panel, border, 16)
        setPadding(px(13), px(11), px(13), px(12))
    }
    private val caption = label("MISE À JOUR DISPONIBLE", 10f, purple, true)
    private val version = label("", 14f, foreground, true)
    private val status = label("Téléchargement et installation depuis All-Download.", 11f, muted)
    private val progress = ProgressBar(activity, null, android.R.attr.progressBarStyleHorizontal).apply {
        max = 100
        progress = 0
        visibility = View.GONE
        progressTintList = ColorStateList.valueOf(purple)
        progressBackgroundTintList = ColorStateList.valueOf(border)
    }
    private val install = Button(activity).apply {
        text = "Installer"
        isAllCaps = false
        textSize = 12f
        setTextColor(Color.WHITE)
        background = background(purple, purple, 12)
        minWidth = 0
        minimumWidth = 0
        minHeight = px(48)
        stateListAnimator = null
    }
    private val details = Button(activity).apply {
        text = "Détails"
        isAllCaps = false
        textSize = 12f
        // View.foreground is a Drawable; explicitly use the theme text color.
        setTextColor(this@AndroidUpdateBanner.foreground)
        background = background(panel, border, 12)
        minWidth = 0
        minimumWidth = 0
        minHeight = px(48)
        stateListAnimator = null
    }
    private val dismiss = Button(activity).apply {
        text = "Plus tard"
        contentDescription = "Ignorer cette version Android"
        isAllCaps = false
        textSize = 12f
        setTextColor(muted)
        background = background(panel, border, 12)
        minWidth = 0
        minimumWidth = 0
        minHeight = px(48)
        stateListAnimator = null
    }

    init {
        val header = LinearLayout(activity).apply {
            gravity = Gravity.CENTER_VERTICAL
            orientation = LinearLayout.HORIZONTAL
        }
        val icon = ImageView(activity).apply {
            setImageResource(R.drawable.ic_update)
            imageTintList = ColorStateList.valueOf(purple)
            contentDescription = null
            setPadding(px(7), px(7), px(7), px(7))
            background = background(if (light) Color.rgb(245, 239, 255)
                else Color.rgb(54, 42, 73), border, 11)
        }
        header.addView(icon, LinearLayout.LayoutParams(px(37), px(37)).apply {
            marginEnd = px(10)
        })
        val headings = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            addView(caption)
            addView(version, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                topMargin = px(3)
            })
        }
        header.addView(headings, LinearLayout.LayoutParams(0,
            ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        view.addView(header)
        view.addView(status, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            topMargin = px(7)
        })
        view.addView(progress, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, px(4)).apply {
            topMargin = px(7)
        })
        val actions = LinearLayout(activity).apply {
            gravity = Gravity.CENTER_VERTICAL
            orientation = LinearLayout.HORIZONTAL
        }
        actions.addView(install, LinearLayout.LayoutParams(0, px(48), 1.3f))
        actions.addView(details, LinearLayout.LayoutParams(0, px(48), 1f).apply {
            marginStart = px(6)
        })
        actions.addView(dismiss, LinearLayout.LayoutParams(0, px(48), 1f).apply {
            marginStart = px(6)
        })
        view.addView(actions, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            topMargin = px(9)
        })
        install.setOnClickListener { installRelease() }
        details.setOnClickListener {
            release?.let { AndroidUpdates.showDialog(activity, it) }
        }
        dismiss.setOnClickListener {
            if (downloading) AndroidApkInstaller.cancelDownload(activity.applicationContext)
            release?.let { prefs.edit().putString(DISMISSED, it.tag).apply() }
            hide()
        }
    }

    fun show(candidate: AndroidUpdates.Release?) {
        if (!AndroidUpdates.enabled(activity) || candidate == null ||
            prefs.getString(DISMISSED, "") == candidate.tag) {
            hide()
            return
        }
        if (release?.tag != candidate.tag) {
            release = candidate
            downloading = false
            latestMessage = ""
            install.isEnabled = true
            install.text = "Installer"
            progress.visibility = View.GONE
            version.text = "All-Download Android " + candidate.version
            status.text = "Mise à jour disponible sans navigateur."
        }
        if (view.visibility != View.VISIBLE) {
            view.visibility = View.VISIBLE
            val reduced = activity.getSharedPreferences("app_settings_v1",
                Context.MODE_PRIVATE).getBoolean("reduce_motion", false)
            if (!reduced) {
                view.alpha = 0f
                view.translationY = -px(12).toFloat()
                view.animate().alpha(1f).translationY(0f).setDuration(250).start()
            }
        }
    }

    fun hide() {
        view.animate().cancel()
        view.visibility = View.GONE
        view.alpha = 1f
        view.translationY = 0f
    }

    /** Keep an available update visible after returning from the OS installer. */
    fun onReturnToApp() {
        if (downloading && !AndroidApkInstaller.isBusy()) {
            downloading = false
            install.isEnabled = true
            install.text = "Réessayer"
        }
    }

    private fun installRelease() {
        if (downloading) return
        val chosen = release ?: return
        downloading = true
        install.isEnabled = false
        install.text = "Téléchargement…"
        status.text = "Préparation de l'APK officielle…"
        AndroidApkInstaller.downloadAndInstall(activity, chosen) { message, failed ->
            if (activity.isFinishing || activity.isDestroyed) return@downloadAndInstall
            latestMessage = message
            status.text = message
            val percent = Regex("APK : (\\d+) %").find(message)
                ?.groupValues?.getOrNull(1)?.toIntOrNull()
            if (percent != null) {
                progress.visibility = View.VISIBLE
                progress.progress = percent.coerceIn(0, 100)
            }
            when {
                failed -> {
                    downloading = false
                    install.isEnabled = true
                    install.text = "Réessayer"
                }
                message == "Installateur Android ouvert" -> {
                    downloading = false
                    install.isEnabled = true
                    install.text = "Réessayer"
                    progress.visibility = View.GONE
                }
                message.contains("APK vérifié") -> {
                    install.text = "Installation…"
                    progress.progress = 100
                }
            }
        }
    }
}
