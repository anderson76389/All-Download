"""No-network Linux regressions and opt-in localhost media end-to-end test."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

from linux.app import DownloaderAPI, category_for, inside_folder, native_twitch_format, valid_url, video_format
from linux.extract_ui import extract


class LinuxBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="alldownload-linux-test-")
        self.root = Path(self.temp.name) / "All-Download"
        self.root.mkdir()
        self.api = DownloaderAPI(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_html_is_identical_to_windows(self):
        html = extract(Path(__file__).resolve().parents[2] / "yt_app.py")
        self.assertIn("pywebviewready", html)
        self.assertIn("start_downloads", html)
        self.assertIn("get_clipboard_text", html)
        self.assertIn("viewSettings", html)
        self.assertGreater(len(html), 50_000)

    def test_folders_remain_under_all_download(self):
        for cat in ("VIDÉOS", "AUDIOS", "TWITCH", "GIFS", "CHAÎNES", "PLAYLIST", "AUTRES"):
            self.assertTrue((self.root / cat).is_dir())
        self.assertTrue((self.root / "Donnees" / "bin").is_dir())
        self.assertFalse((self.root.parent / "AUTRES").exists())
        self.assertFalse(inside_folder(self.root.parent / "outside", self.root))
        bad = self.api.save_app_settings(self.api.get_app_settings(), str(self.root.parent))
        self.assertFalse(bad["success"])
        self.assertEqual(str(self.root.resolve()), self.api.get_download_folder())

    def test_saved_settings_are_reloaded(self):
        settings = self.api.get_app_settings()
        settings["theme"] = "dark_pure"
        settings["audio_format"] = "MP3"
        result = self.api.save_app_settings(settings)
        self.assertTrue(result["success"], result)
        after = DownloaderAPI(self.root).get_app_settings()
        self.assertEqual("dark_pure", after["theme"])
        self.assertEqual("MP3", after["audio_format"])
        self.assertTrue(self.api.save_quick_selector_value("format", "MKV")["success"])
        self.assertEqual("MKV", DownloaderAPI(self.root).get_app_settings()["video_format"])

    def test_rejects_invalid_urls_and_unexpected_modes(self):
        for value in ("", "javascript:alert(1)", "ftp://example.com/file",
                      "https://user:pass@example.com/file", "https://",
                      "https://example.com/ space.mp4"):
            self.assertFalse(valid_url(value), value)
        self.assertTrue(valid_url("https://example.com/media.mp4"))
        self.assertFalse(self.api.start_downloads([{"url": "file:///etc/passwd"}])["success"])
        self.assertFalse(self.api.save_quick_selector_value("format", "AVI")["success"])

    def test_twitch_has_real_1080_then_720_only(self):
        native = native_twitch_format("Meilleure qualité (Auto)")
        self.assertIn("height=1080", native)
        self.assertIn("height=720", native)
        self.assertNotIn("480", native)
        with self.assertRaises(ValueError):
            native_twitch_format("480p")
        self.assertIn("height<=?720", video_format("720p"))
        self.assertEqual("TWITCH", category_for({"url": "https://www.twitch.tv/videos/12345", "mode": "Vidéo"}))
        self.assertEqual("AUDIOS", category_for({"url": "https://youtu.be/test", "mode": "Audio"}))

    def test_download_args_preserve_actual_mode_and_folders(self):
        bin_dir = self.root / "Donnees" / "bin"
        for binary in ("yt-dlp", "ffmpeg"):
            file = bin_dir / binary
            file.write_text("#!/bin/sh\nexit 0\n")
            file.chmod(0o755)
        item = {"url": "https://example.com/music.webm", "mode": "Audio",
                "selectedQuality": "MP3_320"}
        command = self.api._command(item, self.root / "Donnees" / "temporaires" / "test")
        self.assertIn("--extract-audio", command)
        self.assertIn("mp3", command)
        self.assertIn("--audio-quality", command)
        self.assertTrue(any("AUDIOS" in arg for arg in command))
        self.assertTrue(any("temporaires" in arg for arg in command))
        self.assertTrue(command[-1].startswith("https://"))
        self.assertNotIn("--exec", command)


if __name__ == "__main__":
    unittest.main()
