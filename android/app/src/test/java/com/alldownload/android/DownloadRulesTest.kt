package com.alldownload.android

import org.junit.Assert.*
import org.junit.Test

class DownloadRulesTest {
    @Test fun exportsCurrentOutputsAndSelectedSidecarsOnly() {
        val dir = java.nio.file.Files.createTempDirectory("android-export").toFile()
        try {
            val complete = setOf("Video.part-Frag story.mp4", "Video.en.vtt", "Video.webp")
            (complete + listOf("Video.mp4.part", "Video.mp4.ytdl", "Video.mp4.part-Frag32"))
                .forEach { dir.resolve(it).writeText("data") }
            dir.resolve("twitch-source").mkdir()
            dir.resolve("twitch-source/older.mp4").writeText("old")
            assertEquals(complete, DownloadRules.exportableFiles(dir).map { it.name }.toSet())
        } finally {
            dir.deleteRecursively()
        }
    }

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

    @Test fun youtubeExtractorRefreshUsesOnlyTrustedDomains() {
        for (host in listOf("youtube.com", "www.youtube.com", "m.youtube.com",
            "music.youtube.com", "youtu.be", "youtube-nocookie.com")) {
            assertTrue(host, DownloadRules.isYoutubeHost("https://$host/watch?v=test"))
            assertTrue(host, DownloadRules.needsFreshExtractor("https://$host/watch?v=test"))
        }
        for (host in listOf("youtube.com.evil.example", "notyoutube.com",
            "example.com", "youtu.be.fake.test")) {
            assertFalse(host, DownloadRules.isYoutubeHost("https://$host/video"))
            assertFalse(host, DownloadRules.needsFreshExtractor("https://$host/video"))
        }
        assertTrue(DownloadRules.needsFreshExtractor("https://www.instagram.com/reel/test"))
        assertFalse(DownloadRules.needsFreshExtractor("https://attacker@youtube.com/video"))
        assertFalse(DownloadRules.needsFreshExtractor("javascript:alert(1)"))
    }

    @Test fun automaticQualityKeepsNativeSourceAndTwitchFallbackChecksHosts() {
        assertEquals("bestvideo+bestaudio/best",
            DownloadRules.videoFormat("https://twitch.tv/videos/2919531847", 3))
        assertTrue(DownloadRules.needsFreshExtractor("https://twitch.tv/videos/2919531847"))
        val preview = "https://d3stzm2eumvgb4.cloudfront.net/" +
            "c80b0f31f889fc5c54c7_aminematue_318199683938_1793818942/storyboards/2919531847-info.json"
        val auto = TwitchHls.candidates(preview, 3)
        assertTrue(auto.first().endsWith("/chunked/index-dvr.m3u8"))
        assertTrue(auto.any { it.contains("2160p60") })
        assertTrue(TwitchHls.candidates(preview, 1).all { it.contains("720p") })
        assertTrue(TwitchHls.candidates(preview.replace(".cloudfront.net", ".cloudfront.net.evil.test"), 3).isEmpty())
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
    @Test fun instagramHostRecognitionRejectsLookalikes() {
        for (url in listOf("https://instagram.com/reel/ABC/", "https://www.instagram.com/p/ABC/",
                "https://m.instagram.com/reel/ABC/?igsh=abc")) {
            assertTrue(url, DownloadRules.isInstagramHost(url))
        }
        for (url in listOf("https://notinstagram.com/reel/ABC/",
                "https://instagram.com.evil.test/reel/ABC/",
                "https://attacker@instagram.com/reel/ABC/", "javascript:alert(1)",
                "https://twitch.tv/videos/2919531847")) {
            assertFalse(url, DownloadRules.isInstagramHost(url))
        }
    }

    @Test fun instagramAuthFailuresGiveUsefulLocalRecoveryAdvice() {
        val blocked = "ERROR: [Instagram] ABC: Instagram sent an empty media response. " +
            "Log in to access this content."
        val withoutCookies = DownloadRules.instagramFailureMessage(blocked, false)
        assertTrue(withoutCookies.contains("Instagram"))
        assertTrue(withoutCookies.contains("cookies"))
        assertTrue(withoutCookies.contains("Paramètres"))
        val withCookies = DownloadRules.instagramFailureMessage(blocked, true)
        assertTrue(withCookies.contains("réimporte"))
        assertTrue(withCookies.contains("valides"))
        assertFalse(withCookies.contains("Log in"))
    }

    @Test fun instagramErrorsDoNotPromiseUnavailableDownloadsOrModifyOthers() {
        val extractorError = DownloadRules.instagramFailureMessage(
            "ERROR: [Instagram] ABC: unsupported URL", false)
        assertTrue(extractorError.contains("Actualise yt-dlp"))
        assertTrue(extractorError.contains("connexion"))
        val generic = "Erreur réseau temporaire"
        assertEquals(generic, DownloadRules.instagramFailureMessage(generic, false))
        assertEquals("X".repeat(280),
            DownloadRules.instagramFailureMessage("X".repeat(500), false))
    }

    @Test fun instagramPortraitReelsUseNativeShortSideInsteadOfRejecting1080x1920() {
        val reel = "https://www.instagram.com/reel/Chunk8-jurw/"
        val automatic = DownloadRules.videoFormat(reel, 0)
        assertTrue(automatic.contains("bestvideo[width<=1080][height>1080]+bestaudio"))
        assertTrue(automatic.contains("best[width<=1080][height>1080]"))
        assertTrue(automatic.contains("bestvideo[height<=1080]+bestaudio"))
        assertTrue(automatic.endsWith("best[height<=?1080]"))
        assertFalse(automatic.endsWith("/best"))
        assertTrue(DownloadRules.videoFormat(reel, 1).contains("width<=720"))
        assertTrue(DownloadRules.videoFormat(reel, 2).contains("width<=480"))
        assertTrue(DownloadRules.videoFormat(reel, 4).contains("width<=2160"))
        assertEquals("bestvideo+bestaudio/best", DownloadRules.videoFormat(reel, 3))
        // Do not loosen the 1080p cap on other websites or spoofed domains.
        assertEquals("bestvideo[height<=1080]+bestaudio/best[height<=?1080]",
            DownloadRules.videoFormat("https://www.youtube.com/watch?v=test", 0))
        assertEquals("bestvideo[height<=1080]+bestaudio/best[height<=?1080]",
            DownloadRules.videoFormat("https://instagram.com.evil.test/reel/id", 0))
    }

    @Test fun instagramReelsShareLinksNormalizeOnlyRealInstagramDomains() {
        assertEquals("https://www.instagram.com/reel/ABC123/?igsh=share123",
            DownloadRules.normalizedInstagramUrl(
                "https://www.instagram.com/reels/ABC123/?igsh=share123"))
        assertEquals("https://m.instagram.com/reel/Abc-123_/",
            DownloadRules.normalizedInstagramUrl("https://m.instagram.com/reels/Abc-123_/"))
        for (url in listOf("https://www.instagram.com/reel/ABC123/",
                "https://www.instagram.com/share/reel/ABC123/",
                "https://www.instagram.com/reels/", 
                "https://instagram.com.evil.example/reels/ABC123/",
                "https://attacker@instagram.com/reels/ABC123/",
                "https://example.com/path/reels/ABC123/")) {
            assertEquals(url, DownloadRules.normalizedInstagramUrl(url))
        }
    }

}
