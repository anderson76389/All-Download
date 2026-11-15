"""Linux Instagram native portrait selector and trusted URL regression tests."""
import unittest

from linux.app import (available_video_heights, is_instagram_url,
                       normalized_instagram_url, video_format)


class InstagramFormatsLinuxTests(unittest.TestCase):
    def test_exact_hosts_only(self):
        self.assertTrue(is_instagram_url("https://www.instagram.com/reel/ABC/"))
        self.assertFalse(is_instagram_url("https://instagram.com.evil.test/reel/ABC"))
        self.assertFalse(is_instagram_url("https://user@instagram.com/reel/ABC"))

    def test_reels_share_normalization(self):
        self.assertEqual("https://www.instagram.com/reel/ABC/?igsh=s",
                         normalized_instagram_url("https://www.instagram.com/reels/ABC/?igsh=s"))
        for url in ("https://www.instagram.com/reels/", "https://www.instagram.com/reel/ABC/",
                    "https://www.instagram.com/share/reel/ABC/",
                    "https://instagram.com.evil.test/reels/ABC/"):
            self.assertEqual(url, normalized_instagram_url(url))

    def test_instagram_metadata_shows_1080_tier_for_1080x1920(self):
        media = {"formats": [{"vcodec": "h264", "width": 1080,
                              "height": 1920}]}
        self.assertEqual([1080], available_video_heights(media, True))
        self.assertEqual([1920], available_video_heights(media))
        self.assertEqual([], available_video_heights({"formats": []}, True))
        self.assertEqual([], available_video_heights(None, True))

    def test_1080_portrait_format_preserves_native_short_side(self):
        expr = video_format("1080p", is_instagram=True)
        self.assertIn("bestvideo[width<=1080][height>1080]+bestaudio", expr)
        self.assertIn("best[width<=1080][height>1080]", expr)
        self.assertTrue(expr.endswith("best[height<=?1080]"))
        self.assertFalse(expr.endswith("/best"))
        self.assertIn("width<=720", video_format("720p", is_instagram=True))

    def test_twitch_and_normal_video_unchanged(self):
        self.assertEqual("bestvideo[height<=?1080]+bestaudio/best[height<=?1080]",
                         video_format("1080p"))
        self.assertEqual("bestvideo[height=1080]+bestaudio/best[height=1080]/"
                         "bestvideo[height=720]+bestaudio/best[height=720]",
                         video_format("1080p", is_twitch_vod=True))
        self.assertEqual("bestvideo+bestaudio/best",
                         video_format("Meilleure qualité (Auto)", is_instagram=True))


if __name__ == "__main__":
    unittest.main()
