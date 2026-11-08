package com.alldownload.android

import android.content.Context
import android.net.Uri
import com.yausername.youtubedl_android.YoutubeDLRequest

/** User settings shared by the native UI and the yt-dlp worker. */
internal object DownloadOptions {
    const val STORE = "app_settings_v1"

    fun get(context: Context) =
        context.getSharedPreferences(STORE, Context.MODE_PRIVATE)

    fun apply(context: Context, request: YoutubeDLRequest, url: String, mode: Int) {
        val prefs = get(context)
        val retries = prefs.getInt("network_retries", 5).coerceIn(1, 15)
        val fragments = prefs.getInt("fragments", 2).coerceIn(1, 8)
        val timeout = prefs.getInt("network_timeout", 20).coerceIn(10, 60)
        request.addOption("--retries", retries)
        request.addOption("--fragment-retries", retries)
        request.addOption("--socket-timeout", timeout)
        request.addOption("--concurrent-fragments", fragments)

        val video = mode == 0 || mode == 5 || mode == 6
        val audio = mode in 1..3
        if (video) {
            if (prefs.getString("video_format", "MP4") == "MKV")
                request.addOption("--merge-output-format", "mkv")
            // Else: service retains its tested default MP4 merge-output format.
        }
        if (audio || video) {
            if (prefs.getBoolean("embed_metadata", false)) {
                request.addOption("--add-metadata")
            }
            if (prefs.getBoolean("write_thumbnail", false)) {
                request.addOption("--write-thumbnail")
            }
            if (prefs.getBoolean("embed_thumbnail", false)) {
                request.addOption("--embed-thumbnail")
            }
        }
        if (prefs.getBoolean("write_subtitles", false) && video) {
            request.addOption("--write-subs")
            if (prefs.getBoolean("auto_subtitles", false))
                request.addOption("--write-auto-subs")
            request.addOption("--sub-langs", "fr.*,en.*")
        }
        val host = try { Uri.parse(url).host.orEmpty().lowercase() }
                   catch (_: Exception) { "" }
        val youtube = host == "youtube.com" || host.endsWith(".youtube.com")
            || host == "youtu.be" || host == "music.youtube.com"
        if (youtube && video && prefs.getBoolean("sponsor_enable", false)) {
            val remove = prefs.getString("sponsor_remove", "sponsor")
            val mark = prefs.getBoolean("sponsor_mark", false)
            if (remove == "all" || remove == "sponsor")
                request.addOption("--sponsorblock-remove", remove)
            if (mark) request.addOption("--sponsorblock-mark", "all")
            if (prefs.getBoolean("sponsor_exact", false))
                request.addOption("--force-keyframes-at-cuts")
        }
        if (prefs.getBoolean("proxy_enabled", false)) {
            val proxy = prefs.getString("proxy_url", "").orEmpty().trim()
            if (validProxy(proxy)) request.addOption("--proxy", proxy)
        }
        val agent = when (prefs.getString("user_agent", "auto")) {
            "android_chrome" -> "Mozilla/5.0 (Linux; Android 14; Mobile) " +
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
            "android_firefox" -> "Mozilla/5.0 (Android 14; Mobile; rv:131.0) " +
                "Gecko/131.0 Firefox/131.0"
            else -> null
        }
        if (agent != null) request.addOption("--user-agent", agent)
        val extractor = prefs.getString("extractor_args", "").orEmpty().trim()
        if (extractor.isNotEmpty() && extractor.length <= 500 &&
            '\n' !in extractor && '\r' !in extractor) {
            request.addOption("--extractor-args", extractor)
        }
    }

    fun validProxy(value: String): Boolean {
        if (value.isBlank() || value.length > 500 ||
            value.any { it.isWhitespace() || it.isISOControl() }) return false
        val uri = try { java.net.URI(value) } catch (_: Exception) { return false }
        if (uri.scheme?.lowercase() !in setOf("http", "https", "socks4", "socks5", "socks5h"))
            return false
        return !uri.host.isNullOrBlank() && uri.port in 1..65535
    }
}
