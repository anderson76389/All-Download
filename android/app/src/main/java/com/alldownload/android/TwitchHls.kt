package com.alldownload.android

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL

/** Public Twitch CDN fallback; no account, external resolver or transcoding. */
internal object TwitchHls {
    fun candidates(preview: String, quality: Int): List<String> {
        val uri = try { URI(preview) } catch (_: Exception) { return emptyList() }
        if (uri.scheme != "https" || uri.userInfo != null ||
            uri.port !in listOf(-1, 443) ||
            uri.host?.endsWith(".cloudfront.net") != true) return emptyList()
        val path = Regex("^/([A-Za-z0-9]{20}_[A-Za-z0-9_]+_\\d+_\\d+)/storyboards(?:/|$)")
            .find(uri.path.orEmpty())?.groupValues?.get(1) ?: return emptyList()
        val profiles = when (quality) {
            1 -> listOf("720p60", "720p30")
            2 -> listOf("480p30")
            3 -> listOf("chunked", "2160p60", "1440p60", "1080p60", "1080p30",
                "720p60", "720p30", "480p30", "360p30", "160p30")
            4 -> listOf("2160p60", "1440p60", "1080p60", "1080p30", "720p60", "720p30")
            else -> listOf("1080p60", "1080p30", "720p60", "720p30")
        }
        return profiles.map { "https://${uri.host}/$path/$it/index-dvr.m3u8" }
    }

    private fun read(connection: HttpURLConnection, limit: Int): String {
        try {
            check(connection.responseCode == 200) { "Twitch HTTP ${connection.responseCode}" }
            return connection.inputStream.use { input ->
                val bytes = input.readBytesBounded(limit)
                bytes.toString(Charsets.UTF_8).removePrefix("\uFEFF")
            }
        } finally { connection.disconnect() }
    }

    private fun java.io.InputStream.readBytesBounded(limit: Int): ByteArray {
        val output = java.io.ByteArrayOutputStream()
        val buffer = ByteArray(8192)
        while (true) {
            val count = read(buffer)
            if (count < 0) break
            check(output.size() + count <= limit) { "Réponse Twitch trop volumineuse." }
            output.write(buffer, 0, count)
        }
        return output.toByteArray()
    }

    private fun connect(url: String) = (URL(url).openConnection() as HttpURLConnection).apply {
        connectTimeout = 8000
        readTimeout = 8000
        instanceFollowRedirects = false
        setRequestProperty("User-Agent", "All-Download-Android")
    }

    fun resolve(url: String, quality: Int, interrupted: () -> Boolean): String {
        check(DownloadRules.isTwitchVod(url)) { "URL Twitch VOD invalide." }
        check(!interrupted()) { "Interrompu." }
        val id = URI(url).path.trimEnd('/').substringAfterLast('/')
        val query = JSONObject().put("query",
            "query(\$id: ID!) { video(id:\$id) { seekPreviewsURL } }")
            .put("variables", JSONObject().put("id", id)).toString()
        val connection = connect("https://gql.twitch.tv/gql").apply {
            requestMethod = "POST"
            doOutput = true
            setRequestProperty("Client-Id", "kimne78kx3ncx6brgo4mv6wki5h1ko")
            setRequestProperty("Content-Type", "application/json")
        }
        val body = try {
            connection.outputStream.use { it.write(query.toByteArray(Charsets.UTF_8)) }
            read(connection, 512000)
        } finally { connection.disconnect() }
        val preview = JSONObject(body).optJSONObject("data")?.optJSONObject("video")
            ?.optString("seekPreviewsURL").orEmpty()
        for (candidate in candidates(preview, quality)) {
            check(!interrupted()) { "Interrompu." }
            try {
                val manifest = read(connect(candidate), 2_000_000)
                if (manifest.startsWith("#EXTM3U") && manifest.contains("#EXTINF:")) return candidate
            } catch (error: Exception) {
                if (interrupted()) throw error
            }
        }
        error("VOD Twitch supprimée, restreinte ou sans flux public dans cette qualité.")
    }
}
