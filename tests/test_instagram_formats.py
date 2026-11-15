"""Instagram Reel URL and native portrait format regression tests (Windows)."""
import unittest

import yt_app


class InstagramFormatTests(unittest.TestCase):
    def test_real_hosts_only(self):
        for url in ("https://instagram.com/reel/ABC/", "https://www.instagram.com/p/ABC/",
                    "https://m.instagram.com/reels/ABC/"):
            self.assertTrue(yt_app.is_instagram_url(url))
        for url in ("https://notinstagram.com/reel/ABC/",
                    "https://instagram.com.evil.example/reel/ABC/",
                    "https://user@instagram.com/reel/ABC/",
                    "javascript:alert(1)", "https://www.youtube.com/watch?v=x"):
            self.assertFalse(yt_app.is_instagram_url(url))

    def test_normalize_only_individual_reels(self):
        self.assertEqual("https://www.instagram.com/reel/Abc-123/?igsh=test",
                         yt_app.normalized_instagram_url(
                             "https://www.instagram.com/reels/Abc-123/?igsh=test"))
        for url in ("https://www.instagram.com/reel/id/",
                    "https://www.instagram.com/share/reel/id/",
                    "https://www.instagram.com/reels/",
                    "https://instagram.com.evil.example/reels/id/"):
            self.assertEqual(url, yt_app.normalized_instagram_url(url))

    def test_visible_quality_uses_native_short_side_only_on_instagram(self):
        info = {"formats": [{"vcodec": "h264", "width": 1080,
                             "height": 1920, "fps": 30}]}
        self.assertEqual(["Meilleure qualité (Auto)", "1080p"],
                         yt_app.available_video_qualities(info, instagram_portrait=True))
        self.assertEqual(["Meilleure qualité (Auto)", "1920p"],
                         yt_app.available_video_qualities(info))

    def test_1080_portrait_short_side_does_not_upscale(self):
        selector = yt_app.instagram_portrait_format(1080)
        self.assertIn("bestvideo[width<=1080][height>1080]+bestaudio", selector)
        self.assertIn("best[width<=1080][height>1080]", selector)
        self.assertIn("bestvideo[height<=1080]+bestaudio", selector)
        self.assertTrue(selector.endswith("best[height<=?1080]"))
        self.assertFalse(selector.endswith("/best"))
        self.assertIn("width<=720", yt_app.instagram_portrait_format(720))


if __name__ == "__main__":
    unittest.main()
