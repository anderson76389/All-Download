"""Tests du connecteur interface vers la surveillance Chrome."""
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yt_app
import twitch_chrome_bridge as bridge


class BridgeApiTests(unittest.TestCase):
    def make_api(self, root):
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = SimpleNamespace(evaluate_js=lambda _: None)
        api.download_folder = str(Path(root) / "AllDownload")
        api.config = {"chrome_download_folder": str(Path(root) / "Downloads")}
        api._chrome_bridge_active = False
        api._chrome_bridge_stop = threading.Event()
        api.is_cancelled = False
        return api

    def test_chrome_auto_import_moves_no_original_and_keeps_main_engine(self):
        with tempfile.TemporaryDirectory() as root:
            downloads = Path(root) / "Downloads"
            downloads.mkdir()
            source = downloads / "twitch_video.m4v"
            source.write_bytes(b"VIDEO_CONTENT" * 50)
            api = self.make_api(root)

            class ImmediateThread:
                def __init__(self, target, **kwargs):
                    self.target = target
                def start(self):
                    self.target()

            def fake_monitor(folder, baseline, callback, **kwargs):
                self.assertEqual(folder, str(downloads))
                callback(str(source))
                return 1

            with patch.object(api, "open_twitch_in_chrome", return_value={"success": True}), patch.object(
                yt_app.threading, "Thread", ImmediateThread
            ), patch.object(bridge, "monitor_chrome_downloads", side_effect=fake_monitor):
                outcome = api.start_chrome_extension_bridge("https://www.twitch.tv/videos/2905228526")
            self.assertTrue(outcome["success"])
            saved = Path(root) / "AllDownload" / "AUTRES" / "twitch_video.m4v"
            self.assertEqual(saved.read_bytes(), source.read_bytes())
            self.assertFalse(api._chrome_bridge_active)
            self.assertFalse(api.is_cancelled)

    def test_stop_is_independent(self):
        with tempfile.TemporaryDirectory() as root:
            api = self.make_api(root)
            api._chrome_bridge_active = True
            self.assertTrue(api.stop_chrome_extension_bridge()["success"])
            self.assertTrue(api._chrome_bridge_stop.is_set())
            self.assertFalse(api.is_cancelled)


if __name__ == "__main__":
    unittest.main()
