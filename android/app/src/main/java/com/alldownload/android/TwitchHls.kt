package com.alldownload.android

import android.content.Context
import java.io.File
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
            else -> listOf("chunked", "1080p60", "1080p30", "720p60", "720p30")
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

    fun probeHeight(context: Context, manifest: String, interrupted: () -> Boolean): Int? {
        val output = File.createTempFile("twitch-probe-", ".json", context.cacheDir)
        var process: Process? = null
        try {
            val native = context.applicationInfo.nativeLibraryDir
            val packages = File(context.noBackupFilesDir, "youtubedl-android/packages")
            val builder = ProcessBuilder(File(native, "libffprobe.so").absolutePath,
                "-v", "error", "-rw_timeout", "8000000", "-select_streams", "v:0",
                "-show_entries", "stream=height", "-of", "json", manifest)
                .redirectOutput(output).redirectError(File("/dev/null"))
            builder.environment()["LD_LIBRARY_PATH"] =
                "$packages/python/usr/lib:$packages/ffmpeg/usr/lib:$native"
            builder.environment()["TMPDIR"] = context.cacheDir.absolutePath
            process = builder.start()
            val deadline = System.nanoTime() + 25_000_000_000L
            while (true) {
                if (interrupted() || System.nanoTime() >= deadline) return null
                val exit = try { process.exitValue() } catch (_: IllegalThreadStateException) { null }
                if (exit != null) {
                    if (exit != 0 || output.length() > 8192) return null
                    val height = JSONObject(output.readText()).optJSONArray("streams")
                        ?.optJSONObject(0)?.optInt("height") ?: return null
                    return height.takeIf { it in 144..4320 }
                }
                Thread.sleep(100)
            }
        } catch (_: Exception) {
            return null
        } finally {
            process?.destroy()
            process?.inputStream?.close()
            process?.errorStream?.close()
            process?.outputStream?.close()
            output.delete()
        }
    }

    fun resolve(url: String, quality: Int, sourceHeightProbe: ((String) -> Int?)? = null,
                interrupted: () -> Boolean): String {
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
        var source720: String? = null
        for (candidate in candidates(preview, quality)) {
            if (source720 != null && candidate.contains("/720p")) return source720
            check(!interrupted()) { "Interrompu." }
            try {
                val manifest = read(connect(candidate), 2_000_000)
                if (manifest.startsWith("#EXTM3U") && manifest.contains("#EXTINF:")) {
                    if (quality == 0 && candidate.contains("/chunked/")) {
                        when (sourceHeightProbe?.invoke(candidate)) {
                            1080 -> return candidate
                            720 -> source720 = candidate
                        }
                        continue
                    }
                    return candidate
                }
            } catch (error: Exception) {
                if (interrupted()) throw error
            }
        }
        if (source720 != null) return source720
        error("VOD Twitch supprimée, restreinte ou sans flux public dans cette qualité.")
    }
}
