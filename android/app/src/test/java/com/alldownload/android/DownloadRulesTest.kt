package com.alldownload.android

import org.junit.Assert.*
import org.junit.Test

class DownloadRulesTest {
    @Test fun recognizesOnlyGenuineTwitchVod() {
        assertTrue(DownloadRules.isTwitchVod("https://www.twitch.tv/videos/2919531847"))
        assertTrue(DownloadRules.isTwitchVod("https://m.twitch.tv/videos/2919531847/"))
        assertFalse(DownloadRules.isTwitchVod("https://twitch.tv.evil.example/videos/2919531847"))
        assertFalse(DownloadRules.isTwitchVod("https://www.twitch.tv/videos/2919531847/clip"))
        assertFalse(DownloadRules.isTwitchVod("https://www.twitch.tv/directory"))
        assertFalse(DownloadRules.isTwitchVod("https://example.com/video.mp4"))
        assertFalse(DownloadRules.isTwitchVod("javascript:alert(1)"))
        assertFalse(DownloadRules.isTwitchVod("https://attacker@twitch.tv/videos/2919531847"))
    }

    @Test fun keepsTwitchNativeQualityOnly() {
        val format = DownloadRules.videoFormat("https://twitch.tv/videos/2919531847", 0)
        assertTrue(format.contains("height=1080"))
        assertTrue(format.contains("height=720"))
        assertFalse(format.contains("height=480"))
        assertFalse(format.contains("height<=1080"))
        assertEquals("bestvideo[height=720]+bestaudio/best[height=720]",
            DownloadRules.videoFormat("https://twitch.tv/videos/2919531847", 1))
    }

    @Test fun directFileWithUnknownResolutionIsSupportedWithoutForcing4k() {
        val format = DownloadRules.videoFormat("https://example.com/video.mp4", 0)
        assertTrue(format.contains("height<=1080"))
        assertTrue(format.endsWith("/best[height<=?1080]"))
        assertFalse(format.endsWith("/best"))
        assertFalse(format.contains("height=?"))
    }

    @Test fun qualityManualLimits() {
        for ((index, height) in listOf(1 to 720, 2 to 480, 4 to 2160)) {
            val format = DownloadRules.videoFormat("https://youtube.com/watch?v=test", index)
            assertTrue(format.contains("height<=$height"))
        }
    }

    @Test fun updatesOnlyGenuineSocialDomainsAndNeverForTwitch() {
        for (host in listOf(
            "reddit.com", "v.redd.it", "www.pinterest.com", "co.pinterest.fr",
            "x.com", "mobile.twitter.com", "instagram.com", "vm.tiktok.com",
            "facebook.com", "fb.watch", "vimeo.com", "bsky.app", "dailymotion.com"
        )) {
            assertTrue(host, DownloadRules.isSocialVideoHost("https://$host/video/123"))
        }
        for (host in listOf("twitch.tv", "youtube.com", "example.com",
            "x.com.evil.example", "notinstagram.com", "reddit.com.fake.test")) {
            assertFalse(host, DownloadRules.isSocialVideoHost("https://$host/video/123"))
        }
        assertFalse(DownloadRules.isSocialVideoHost("javascript:alert(1)"))
        assertFalse(DownloadRules.isSocialVideoHost(
            "https://stealer@www.instagram.com/reel/abc"))
    }

    @Test fun foldersDoNotEscapeAllDownloadAndStayClassified() {
        assertEquals("TWITCH", DownloadRules.categoryFor("https://www.twitch.tv/videos/2919531847", 0))
        assertEquals("VIDÉOS", DownloadRules.categoryFor("https://youtu.be/id", 0))
        assertEquals("VIDÉOS", DownloadRules.categoryFor("https://m.youtube.com/watch?v=id", 0))
        assertEquals("AUTRES", DownloadRules.categoryFor("https://fake-youtube.com/watch?v=id", 0))
        assertEquals("TWITCH", DownloadRules.categoryFor("https://www.twitch.tv/someone/clip/id", 0))
        assertEquals("TWITCH", DownloadRules.categoryFor("https://clips.twitch.tv/SomeClipId", 0))
        assertEquals("AUTRES", DownloadRules.categoryFor("https://twitch.tv.evil.example/clip/id", 0))
        assertEquals("AUDIOS", DownloadRules.categoryFor("https://www.twitch.tv/videos/2919531847", 1))
        assertEquals("GIFS", DownloadRules.categoryFor("https://youtu.be/id", 4))
        assertEquals("PLAYLIST", DownloadRules.categoryFor("https://youtu.be/id", 5))
        assertEquals("CHAÎNES", DownloadRules.categoryFor("https://youtu.be/id", 6))
    }
}
