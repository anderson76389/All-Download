package com.alldownload.android

import android.app.Activity
import android.app.Dialog
import android.content.Context
import android.content.Intent
import org.json.JSONObject
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Handler
import android.os.PowerManager
import java.util.concurrent.atomic.AtomicBoolean
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
        "https://api.github.com/repos/anderson76389/All-Download/releases?per_page=100"
    private const val PREFS = "android_update_preferences"
    private const val INTERVAL = 30L * 60L * 1000L
    private val checking = AtomicBoolean(false)

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

 
    /** Keep only the Android candidate, not hundreds of Windows release JSON objects. */
    internal fun encodeCandidate(release: Release?): String =
        if (release == null) "" else JSONObject().apply {
            put("version", release.version)
            put("tag", release.tag)
            put("title", release.title)
            put("summary", release.summary)
            put("page", release.page)
            put("apkUrl", release.apkUrl)
            put("size", release.size)
        }.toString()

    /** Revalidate persisted links before reusing a 304 Not Modified response. */
    internal fun decodeCandidate(raw: String, localVersion: String): Release? {
        val saved = try { JSONObject(raw) } catch (_: Exception) { return null }
        val version = saved.optString("version")
        val tag = "android-v$version"
        val expectedApk = "https://github.com/anderson76389/All-Download/" +
            "releases/download/$tag/All-Download-Android-$version.apk"
        val expectedPage =
            "https://github.com/anderson76389/All-Download/releases/tag/$tag"
        if (!Regex("^\\d+\\.\\d+\\.\\d+-beta$").matches(version) ||
            compareVersions(version, localVersion) <= 0 ||
            saved.optString("tag") != tag ||
            saved.optString("page") != expectedPage ||
            saved.optString("apkUrl") != expectedApk ||
            saved.optLong("size") < 1_000_000L) return null
        return Release(version, tag, saved.optString("title"),
            saved.optString("summary"), expectedPage, expectedApk,
            saved.optLong("size"))
    }

    fun check(activity: Activity, force: Boolean = false,
              onStatus: ((String) -> Unit)? = null) {
        val prefs = activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (!force && !prefs.getBoolean("enabled", true)) return
        // Don't wake the network in system battery-saver mode unless user asks.
        if (!force && (activity.getSystemService(Context.POWER_SERVICE)
                as PowerManager).isPowerSaveMode) return
        val now = System.currentTimeMillis()
        val last = prefs.getLong("last_attempt", 0L)
        if (!force && last > 0 && now - last in 0 until INTERVAL) return
        if (!checking.compareAndSet(false, true)) return
        prefs.edit().putLong("last_attempt", now).apply()
        val handler = Handler(Looper.getMainLooper())
        Thread({
            val result = try {
                var match: Release? = null
                // Many stable Windows releases may hide Android betas from page 1.
                // Pagination is bounded and only read-only GitHub API requests are made.
                for (page in 1..4) {
                    val conn = (URL(RELEASES_API + "&page=" + page)
                        .openConnection() as HttpURLConnection).apply {
                        connectTimeout = 6500
                        readTimeout = 6500
                        instanceFollowRedirects = false
                        setRequestProperty("User-Agent", "All-Download-Android-updater")
                        setRequestProperty("Accept", "application/vnd.github+json")
                        val cached = prefs.getString("etag_releases_$page", "").orEmpty()
                        if (!force && cached.isNotBlank())
                            setRequestProperty("If-None-Match", cached)
                    }
                    var responseEtag: String? = null
                    val body = try {
                        when (conn.responseCode) {
                            304 -> null // Reuse our compact verified Android release entry.
                            200 -> {
                                val response = conn.inputStream.bufferedReader().use { it.readText() }
                                responseEtag = conn.getHeaderField("ETag")
                                response
                            }
                            else -> throw IllegalStateException("GitHub : HTTP " + conn.responseCode)
                        }
                    } finally { conn.disconnect() }
                    if (body != null) {
                        val releaseCount = JSONArray(body).length()
                        match = findNewer(body, BuildConfig.VERSION_NAME)
                        // Store the ETag and its matching candidate together. If an activity
                        // was destroyed before displaying the popup, a later 304 still works.
                        val edit = prefs.edit()
                            .putString("candidate_releases_$page", encodeCandidate(match))
                            .putBoolean("last_releases_page_$page", releaseCount < 100)
                        if (!responseEtag.isNullOrBlank())
                            edit.putString("etag_releases_$page", responseEtag)
                        edit.apply()
                    } else {
                        match = decodeCandidate(
                            prefs.getString("candidate_releases_$page", "").orEmpty(),
                            BuildConfig.VERSION_NAME)
                    }
                    if (match != null ||
                        prefs.getBoolean("last_releases_page_$page", false)) break
                }
                match
            } catch (error: Exception) {
                handler.post {
                    if (!activity.isFinishing && !activity.isDestroyed)
                        onStatus?.invoke("Vérification impossible : " +
                            (error.localizedMessage ?: "réseau indisponible"))
                }
                checking.set(false)
                return@Thread
            }
            checking.set(false)
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

    fun showDialog(activity: Activity, release: Release): Dialog {
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
            this.background = GradientDrawable().apply {
                setColor(background)
                cornerRadius = px(14).toFloat()
            }
        }
        val image = ImageView(activity).apply {
            setImageResource(R.drawable.all_download_android_logo)
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
        val status = text(
            "L'APK sera téléchargé et vérifié dans All-Download, sans navigateur.", 12f, secondary)
        card.addView(status, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                topMargin = px(10)
            })
        val install = Button(activity).apply {
            text = "Installer la mise à jour"
            isAllCaps = false
            setTextColor(Color.WHITE)
            this.background = GradientDrawable().apply {
                setColor(purple)
                cornerRadius = px(13).toFloat()
            }
            setOnClickListener {
                isEnabled = false
                text = "Préparation de l'APK…"
                AndroidApkInstaller.downloadAndInstall(activity, release) { message, failed ->
                    if (activity.isFinishing || activity.isDestroyed) return@downloadAndInstall
                    status.text = message
                    this.text = if (failed) "Réessayer" else "Téléchargement en cours…"
                    if (failed) isEnabled = true
                    if (message == "Installateur Android ouvert") dialog.dismiss()
                }
            }
        }
        card.addView(install, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, px(53)).apply { topMargin = px(14) })
        card.addView(text(
            "Android peut demander une autorisation et une confirmation. Pour conserver vos données entre les versions, toutes les APK doivent être signées avec la même clé privée.",
            11f, secondary).apply {
            setPadding(px(2), px(10), px(2), px(2))
        })
        val later = Button(activity).apply {
            text = "Plus tard"
            isAllCaps = false
            setTextColor(foreground)
            setOnClickListener {
                AndroidApkInstaller.cancelDownload(activity.applicationContext)
                dialog.dismiss()
            }
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
        return dialog
    }
}
