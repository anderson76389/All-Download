"""Twitch : classer l'accès refusé et importer une copie locale sans l'écraser."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import yt_app


class TwitchBridgeTests(unittest.TestCase):
    def test_subscriber_only_error_classification(self):
        text = "ERROR: [twitch:vod] 2905228526: You must be logged into an account that has access to this subscriber-only content."
        self.assertTrue(yt_app.is_twitch_subscriber_error(text))
        self.assertFalse(yt_app.is_twitch_subscriber_error("ERROR: Unable to download webpage: HTTP Error 403"))

    def test_local_copy_keeps_original_and_existing_names(self):
        with tempfile.TemporaryDirectory() as root:
            src = Path(root) / "external" / "my vod.mp4"
            src.parent.mkdir()
            src.write_bytes(b"video-data" * 1000)
            dest = Path(root) / "All-Download"
            dest.joinpath("AUTRES").mkdir(parents=True)
            existing = dest / "AUTRES" / "my vod.mp4"
            existing.write_bytes(b"existing")
            result = yt_app.copy_twitch_recording(str(src), str(dest))
            self.assertFalse(result["already_present"])
            self.assertEqual(existing.read_bytes(), b"existing")
            self.assertEqual(Path(result["path"]).read_bytes(), src.read_bytes())
            self.assertEqual(src.read_bytes(), b"video-data" * 1000)
            self.assertEqual(Path(result["path"]).parent, dest / "AUTRES")
            again = yt_app.copy_twitch_recording(result["path"], str(dest))
            self.assertTrue(again["already_present"])

    def test_rejects_empty_or_nonvideo_file(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            empty = base / "empty.mp4"
            empty.write_bytes(b"")
            with self.assertRaises(ValueError):
                yt_app.copy_twitch_recording(empty, base)
            fake = base / "notvideo.exe"
            fake.write_bytes(b"random")
            with self.assertRaises(ValueError):
                yt_app.copy_twitch_recording(fake, base)

    def test_chrome_open_is_limited_to_twitch_vods(self):
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        with patch.object(yt_app, "locate_google_chrome", return_value="C:/Chrome/chrome.exe"), patch.object(
            yt_app.subprocess, "Popen", return_value=SimpleNamespace(pid=1)
        ) as popen:
            self.assertFalse(api.open_twitch_in_chrome("https://evil.example/videos/1")["success"])
            popen.assert_not_called()
            self.assertTrue(api.open_twitch_in_chrome("https://www.twitch.tv/videos/2905228526")["success"])
            self.assertEqual(popen.call_args.args[0], [
                "C:/Chrome/chrome.exe", "--new-tab", "https://www.twitch.tv/videos/2905228526"
            ])

    def test_subscriber_error_from_metadata_has_specific_code(self):
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api.config = {"settings": {}}
        err = ("ERROR: [twitch:vod] 2905228526: You must be logged into an account "
               "that has access to this subscriber-only content.")
        class FakeProcess:
            returncode = 1
            pid = 123
            def communicate(self, timeout=None):
                return ("", err)
        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=True), patch.object(
            yt_app.subprocess, "Popen", return_value=FakeProcess()
        ):
            result = api.extract_info("https://www.twitch.tv/videos/2905228526")
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "twitch_subscriber_only")
        self.assertTrue(result["is_restricted"])
        self.assertIn("Chrome", result["error"])


if __name__ == "__main__":
    unittest.main()
