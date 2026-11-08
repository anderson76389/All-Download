package com.alldownload.android

import android.app.Activity
import android.app.Dialog
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONArray
import java.net.HttpURLConnection
import java.net.URL

/** Only GitHub Android beta releases, never the Windows "latest" release. */
internal object AndroidUpdates {
    const val RELEASES_API =
        "https://api.github.com/repos/anderson76389/All-Download/releases?per_page=25"
    private const val PREFS = "android_update_preferences"
    private const val INTERVAL = 12L * 60L * 60L * 1000L

    data class Release(val version: String, val tag: String, val title: String,
        val summary: String, val page: String, val apkUrl: String, val size: Long)

    fun compareVersions(first: String, second: String): Int {
        val regex = Regex("^(\\d+)\\.(\\d+)\\.(\\d+)(?:-beta)?$")
        val a = regex.matchEntire(first) ?: return -1
        val b = regex.matchEntire(second) ?: return 1
        for (i in 1..3) {
            val n1 = a.groupValues[i].toIntOrNull() ?: return -1
            val n2 = b.groupValues[i].toIntOrNull() ?: return 1
            if (n1 != n2) return n1.compareTo(n2)
        }
        return 0
    }

    fun findNewer(json: String, localVersion: String): Release? {
        val entries = JSONArray(json)
        var newest: Release? = null
        for (index in 0 until entries.length()) {
            val obj = entries.optJSONObject(index) ?: continue
            if (obj.optBoolean("draft", false)) continue
            val tag = obj.optString("tag_name")
            val version = Regex("^android-v(\\d+\\.\\d+\\.\\d+-beta)$")
                .matchEntire(tag)?.groupValues?.get(1) ?: continue
            if (compareVersions(version, localVersion) <= 0) continue
            val page = obj.optString("html_url")
            if (!page.startsWith("https://github.com/anderson76389/All-Download/releases/tag/"))
                continue
            val assets = obj.optJSONArray("assets") ?: continue
            var apk = ""
            var size = 0L
            for (j in 0 until assets.length()) {
                val asset = assets.optJSONObject(j) ?: continue
                val expected = "All-Download-Android-$version.apk"
                if (asset.optString("name") != expected) continue
                val candidate = asset.optString("browser_download_url")
                if (candidate == "https://github.com/anderson76389/All-Download/" +
                    "releases/download/$tag/$expected") {
                    apk = candidate
                    size = asset.optLong("size")
                }
            }
            if (apk.isBlank() || size < 1_000_000L) continue
            val body = obj.optString("body")
                .replace(Regex("(?m)^#{1,6}\\s*"), "")
                .replace(Regex("[*_]+"), "")
                .trim().take(900)
            val found = Release(version, tag, obj.optString("name", "All-Download Android"),
                body.ifBlank { "Nouvelle version Android disponible." }, page, apk, size)
            if (newest == null || compareVersions(found.version, newest.version) > 0)
                newest = found
        }
        return newest
    }

    fun check(activity: Activity, force: Boolean = false,
              onStatus: ((String) -> Unit)? = null) {
        val prefs = activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (!force && !prefs.getBoolean("enabled", true)) return
        val now = System.currentTimeMillis()
        val last = prefs.getLong("last_attempt", 0L)
        if (!force && last > 0 && now - last in 0 until INTERVAL) return
        prefs.edit().putLong("last_attempt", now).apply()
        val handler = Handler(Looper.getMainLooper())
        Thread({
            val result = try {
                val conn = (URL(RELEASES_API).openConnection() as HttpURLConnection).apply {
                    connectTimeout = 6500
                    readTimeout = 6500
                    instanceFollowRedirects = false
                    setRequestProperty("User-Agent", "All-Download-Android-updater")
                    setRequestProperty("Accept", "application/vnd.github+json")
                }
                try {
                    if (conn.responseCode != 200)
                        throw IllegalStateException("GitHub : HTTP " + conn.responseCode)
                    val body = conn.inputStream.bufferedReader().use { it.readText() }
                    findNewer(body, BuildConfig.VERSION_NAME)
                } finally { conn.disconnect() }
            } catch (error: Exception) {
                handler.post {
                    if (!activity.isFinishing && !activity.isDestroyed)
                        onStatus?.invoke("Vérification impossible : " +
                            (error.localizedMessage ?: "réseau indisponible"))
                }
                return@Thread
            }
            handler.post {
                if (activity.isFinishing || activity.isDestroyed) return@post
                if (result == null) {
                    onStatus?.invoke("All-Download " + BuildConfig.VERSION_NAME + " est à jour.")
                    return@post
                }
                onStatus?.invoke("Nouvelle version : " + result.version)
                val shown = prefs.getString("last_shown", "")
                if (force || result.tag != shown) {
                    prefs.edit().putString("last_shown", result.tag).apply()
                    showDialog(activity, result)
                }
            }
        }, "all-download-update-check").start()
    }

    fun enabled(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean("enabled", true)

    fun setEnabled(context: Context, value: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean("enabled", value).apply()
    }

    fun showDialog(activity: Activity, release: Release) {
        val light = activity.getSharedPreferences("app_settings_v1",
            Context.MODE_PRIVATE).getInt("theme", 0) == 1
        val background = if (light) Color.WHITE else Color.rgb(33, 33, 33)
        val foreground = if (light) Color.rgb(15, 23, 42) else Color.WHITE
        val secondary = if (light) Color.rgb(100, 116, 139) else Color.rgb(177, 177, 190)
        val dp = activity.resources.displayMetrics.density
        fun px(value: Int) = (value * dp + .5f).toInt()
        fun text(value: String, size: Float, color: Int, bold: Boolean = false) =
            TextView(activity).apply {
                this.text = value
                textSize = size
                setTextColor(color)
                if (bold) setTypeface(typeface, Typeface.BOLD)
                gravity = Gravity.CENTER_HORIZONTAL
            }
        val purple = Color.rgb(124, 58, 237)
        val card = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(px(24), px(25), px(24), px(20))
            background = GradientDrawable().apply {
                setColor(background)
                cornerRadius = px(26).toFloat()
            }
        }
        val image = ImageView(activity).apply {
            setImageResource(R.drawable.all_download_logo)
            scaleType = ImageView.ScaleType.CENTER_CROP
        }
        card.addView(image, LinearLayout.LayoutParams(px(74), px(74)))
        card.addView(text("MISE À JOUR DISPONIBLE", 12f, purple, true).apply {
            setPadding(0, px(15), 0, 0)
        })
        card.addView(text("All-Download " + release.version, 23f, foreground, true).apply {
            setPadding(0, px(7), 0, 0)
        })
        card.addView(text("Nouveautés Android", 15f, foreground, true).apply {
            setPadding(0, px(16), 0, 0)
        })
        val notes = ScrollView(activity).apply {
            addView(text(release.summary, 13f, secondary).apply {
                gravity = Gravity.START
                setPadding(px(4), px(8), px(4), px(8))
            })
        }
        card.addView(notes, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, px(155)))
        val dialog = Dialog(activity)
        val install = Button(activity).apply {
            text = "Télécharger la mise à jour"
            isAllCaps = false
            setTextColor(Color.WHITE)
            background = GradientDrawable().apply {
                setColor(purple)
                cornerRadius = px(13).toFloat()
            }
            setOnClickListener {
                dialog.dismiss()
                val open = Intent(Intent.ACTION_VIEW, Uri.parse(release.apkUrl))
                    .addCategory(Intent.CATEGORY_BROWSABLE)
                try { activity.startActivity(open) }
                catch (_: Exception) {
                    activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(release.page)))
                }
            }
        }
        card.addView(install, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, px(53)).apply { topMargin = px(14) })
        val later = Button(activity).apply {
            text = "Plus tard"
            isAllCaps = false
            setTextColor(foreground)
            setOnClickListener { dialog.dismiss() }
        }
        card.addView(later, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, px(47)))
        dialog.setContentView(card)
        dialog.show()
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        dialog.window?.setLayout(
            (activity.resources.displayMetrics.widthPixels - px(36)).coerceAtMost(px(460)),
            ViewGroup.LayoutParams.WRAP_CONTENT)
        val reduced = activity.getSharedPreferences("app_settings_v1", Context.MODE_PRIVATE)
            .getBoolean("reduce_motion", false)
        if (!reduced) {
            card.alpha = 0f
            card.scaleX = .89f
            card.scaleY = .89f
            card.animate().alpha(1f).scaleX(1f).scaleY(1f)
                .setDuration(270).start()
        }
    }
}
