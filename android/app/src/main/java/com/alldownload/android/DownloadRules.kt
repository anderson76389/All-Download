package com.alldownload.android

import java.net.URI

/** Règles pures, testables sur JVM (sans Android ni réseau). */
internal object DownloadRules {
    private fun uri(url: String): URI? = try {
        URI(url.trim()).takeIf {
            it.scheme?.lowercase() in setOf("http", "https") && it.userInfo == null &&
                !it.host.isNullOrBlank()
        }
    } catch (_: Exception) { null }

    /**
     * N'actualiser automatiquement yt-dlp que pour les réseaux sociaux
     * dont les extracteurs changent fréquemment. Twitch reste inchangé.
     * Comparaison stricte des domaines (aucun suffixe trompeur).
     */
    fun isSocialVideoHost(url: String): Boolean {
        val host = uri(url)?.host?.lowercase() ?: return false
        val domains = setOf(
            "reddit.com", "redd.it", "pinterest.com", "pin.it",
            "x.com", "twitter.com", "instagram.com", "tiktok.com",
            "facebook.com", "fb.watch", "fb.com", "vimeo.com",
            "bsky.app", "dailymotion.com", "dai.ly"
        )
        return domains.any { host == it || host.endsWith(".$it") } ||
            Regex("""(^|\\.)pinterest\\.[a-z]{2,4}$""").containsMatchIn(host)
    }

    fun isTwitchVod(url: String): Boolean {
        val parsed = uri(url) ?: return false
        return parsed.host.lowercase() in setOf("twitch.tv", "www.twitch.tv", "m.twitch.tv") &&
            Regex("^/videos/[0-9]{5,20}/?$").matches(parsed.path.orEmpty())
    }

    fun categoryFor(url: String, mode: Int): String {
        if (mode == 5) return "PLAYLIST"
        if (mode == 6) return "CHAÎNES"
        if (mode in 1..3) return "AUDIOS"
        if (mode == 4) return "GIFS"
        if (isTwitchVod(url)) return "TWITCH"
        val host = uri(url)?.host?.lowercase().orEmpty()
        return if (host == "youtu.be" || host == "youtube.com" ||
            host.endsWith(".youtube.com")) "VIDÉOS" else "AUTRES"
    }

    /**
     * Ne JAMAIS permettre à la sélection automatique Twitch de dégrader au-dessous
     * de 720p ni d'inventer une résolution. En mode manuel, aucune autre hauteur.
     *
     * Pour les liens directs non-Twitch, autoriser les résolutions inconnues,
     * sinon les flux MP4 bruts (sans métadonnées hauteur) ne peuvent pas télécharger.
     */
    fun videoFormat(url: String, quality: Int): String {
        if (isTwitchVod(url)) return when (quality) {
            1 -> "bestvideo[height=720]+bestaudio/best[height=720]"
            2 -> "bestvideo[height=480]+bestaudio/best[height=480]"
            else -> "bestvideo[height=1080]+bestaudio/best[height=1080]/bestvideo[height=720]+bestaudio/best[height=720]"
        }
        return when (quality) {
            1 -> "bestvideo[height<=720]+bestaudio/best[height<=?720]"
            2 -> "bestvideo[height<=480]+bestaudio/best[height<=?480]"
            3 -> "bestvideo+bestaudio/best"
            4 -> "bestvideo[height<=2160]+bestaudio/best[height<=?2160]"
            else -> "bestvideo[height<=1080]+bestaudio/best[height<=?1080]"
        }
    }
}
