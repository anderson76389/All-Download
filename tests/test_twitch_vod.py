"""Tests hors réseau pour l'intégration TwitchDownloaderCLI et son routage."""

import hashlib
import io
import json
import os
import struct
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import twitch_vod


class TwitchVodTests(unittest.TestCase):
    def test_accept_only_actual_twitch_vods(self):
        valid = (
            "https://www.twitch.tv/videos/1234567890",
            "https://twitch.tv/videos/1234567890?t=1h20m",
            "https://m.twitch.tv/videos/1234567890/",
        )
        for url in valid:
            self.assertEqual(twitch_vod.twitch_vod_id(url), "1234567890")
        invalid = (
            "https://evil.test/twitch.tv/videos/1234567890",
            "https://twitch.tv.evil.test/videos/1234567890",
            "https://www.twitch.tv/someone",
            "https://www.twitch.tv/someone/clip/InterestingClip",
            "https://clips.twitch.tv/InterestingClip",
            "https://www.twitch.tv/videos/notanid",
            "file:///videos/1234567890",
            "https://user:pass@twitch.tv/videos/1234567890",
        )
        for url in invalid:
            self.assertIsNone(twitch_vod.twitch_vod_id(url), url)

    def test_fallback_card_can_enter_existing_queue(self):
        url = "https://www.twitch.tv/videos/1234567890"
        info = twitch_vod.fallback_metadata(url)
        self.assertEqual(info["url"], url)
        self.assertEqual(info["mode"], "Vidéo")
        self.assertEqual(info["selectedQuality"], info["formats"][0])
        self.assertEqual(info["item_count"], 1)
        self.assertIsNone(twitch_vod.fallback_metadata("https://twitch.tv/user"))

    def test_quality_progress_and_safe_command(self):
        url = "https://www.twitch.tv/videos/1234567890"
        command = twitch_vod.build_command(
            "C:/bin/TwitchDownloaderCLI.exe", url, 'CON? Bad:Title',
            "1080p (60fps)", "D:/AUTRES", "C:/bin/ffmpeg.exe", "D:/cache")
        self.assertEqual(command[1:4], ["videodownload", "--id", "1234567890"])
        self.assertEqual(command[command.index("--quality") + 1], "1080p60")
        self.assertEqual(command[command.index("--collision") + 1], "Rename")
        self.assertEqual(command[command.index("--ffmpeg-path") + 1], "C:/bin/ffmpeg.exe")
        self.assertTrue(command[command.index("--output") + 1].endswith(".mp4"))
        self.assertNotIn("?", command[command.index("--output") + 1])
        self.assertEqual(twitch_vod.selected_quality_to_cli("Meilleure qualité (Auto)"), None)
        self.assertEqual(twitch_vod.selected_quality_to_cli("720p"), "720p")
        self.assertEqual(twitch_vod.progress_percentage("[STATUS] - Downloading 68%"), 68)
        self.assertIsNone(twitch_vod.progress_percentage("[INFO] - 89%"))
        self.assertIsNone(twitch_vod.progress_percentage("[STATUS] - 900%"))

    def test_install_official_release_with_digest_and_preserve_existing(self):
        # Binaire PE de test : jamais exécuté. On vérifie format, atomisation et SHA-256.
        exe = bytearray(70000)
        exe[:2] = b"MZ"
        struct.pack_into("<I", exe, 0x3c, 128)
        exe[128:132] = b"PE\x00\x00"
        struct.pack_into("<H", exe, 132, 0x8664)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as archive:
            archive.writestr("Windows/TwitchDownloaderCLI.exe", bytes(exe))
        zip_bytes = zip_buffer.getvalue()
        asset = {
            "name": "TwitchDownloaderCLI-test-Windows-x64.zip",
            "browser_download_url": "https://github.com/lay295/TwitchDownloader/releases/download/test/TwitchDownloaderCLI-test-Windows-x64.zip",
            "size": len(zip_bytes),
            "digest": "sha256:" + hashlib.sha256(zip_bytes).hexdigest(),
        }

        def fake_open(req, timeout=None):
            if req.full_url == twitch_vod.RELEASE_API:
                return io.BytesIO(json.dumps({"assets": [asset]}).encode())
            self.assertEqual(req.full_url, asset["browser_download_url"])
            return io.BytesIO(zip_bytes)

        with tempfile.TemporaryDirectory() as root:
            with patch("twitch_vod.urllib.request.urlopen", side_effect=fake_open) as opener:
                import yt_app
                self.assertEqual(
                    twitch_vod.ensure_cli_ready(root, yt_app.is_valid_windows_executable),
                    (True, ""),
                )
                self.assertEqual(opener.call_count, 2)
                output_path = os.path.join(root, twitch_vod.CLI_FILENAME)
                self.assertEqual(open(output_path, "rb").read(), bytes(exe))
                self.assertEqual(
                    twitch_vod.ensure_cli_ready(root, yt_app.is_valid_windows_executable),
                    (True, ""),
                )
                self.assertEqual(opener.call_count, 2)
                self.assertFalse(os.path.exists(output_path + ".tmp"))
                self.assertFalse(os.path.exists(output_path + ".zip.part"))

    def test_reject_modified_archive_without_touching_installed_files(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("TwitchDownloaderCLI.exe", b"untrusted executable")
        content = archive.getvalue()
        asset = {
            "name": "TwitchDownloaderCLI-test-Windows-x64.zip",
            "browser_download_url": "https://github.com/lay295/TwitchDownloader/releases/download/test/TwitchDownloaderCLI-test-Windows-x64.zip",
            "size": len(content),
            "digest": "sha256:" + "0" * 64,
        }

        def fake_open(req, timeout=None):
            if req.full_url == twitch_vod.RELEASE_API:
                return io.BytesIO(json.dumps({"assets": [asset]}).encode())
            return io.BytesIO(content)

        with tempfile.TemporaryDirectory() as root:
            with patch("twitch_vod.urllib.request.urlopen", side_effect=fake_open):
                good, error = twitch_vod.ensure_cli_ready(root, lambda _: False)
            self.assertFalse(good)
            self.assertIn("SHA-256", error)
            self.assertFalse(os.path.exists(os.path.join(root, twitch_vod.CLI_FILENAME)))


class IntegrationTests(unittest.TestCase):
    def test_extract_info_falls_back_when_ytdlp_not_available(self):
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api.config = {}
        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=False):
            result = api.extract_info("https://www.twitch.tv/videos/1234567890")
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["title"], "VOD Twitch 1234567890")

    def test_twitch_video_does_not_require_ytdlp_and_uses_existing_queue(self):
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api.config = {}
        api.is_cancelled = False
        api.is_paused = False
        api._active_download_process = None
        api._suspended_download_pids = []
        api._window = None
        item = {
            "url": "https://www.twitch.tv/videos/1234567890",
            "title": "Twitch VOD",
            "mode": "Vidéo",
            "selectedQuality": "Meilleure qualité (Auto)",
        }
        class ImmediateThread:
            def __init__(self, target, **kwargs):
                self.target = target
            def start(self):
                self.target()

        with tempfile.TemporaryDirectory() as root:
            api.download_folder = root
            with patch.object(yt_app.threading, "Thread", ImmediateThread), \
                 patch.object(yt_app, "ensure_ytdlp_ready") as ytdlp, \
                 patch.object(api, "_download_twitch_video", return_value=True) as twitch:
                api.start_downloads([item])
            ytdlp.assert_not_called()
            twitch.assert_called_once()
            self.assertEqual(os.path.basename(twitch.call_args.args[1]), "AUTRES")


    def test_twitch_cli_rejection_displays_real_error_not_clr_exit_code(self):
        import io
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = type("Ui", (), {"events": [], "evaluate_js": lambda self, x: self.events.append(x)})()
        api.is_cancelled = False
        api.is_paused = False
        api._active_download_process = None
        api._suspended_download_pids = []
        class FakeProcess:
            pid = 10001
            stdout = io.StringIO(
                "[STATUS] - Fetching Video Info [1/4]\\n"
                "Unhandled exception. System.AggregateException: "
                "(Insufficient access to VOD, OAuth may be required.)\\n"
            )
            def wait(self):
                return 3762504530
            def poll(self):
                return 3762504530
        with tempfile.TemporaryDirectory() as root, \
             patch.object(yt_app, "BIN_DIR", root), \
             patch.object(yt_app, "APP_DIR", root), \
             patch.object(yt_app, "FFMPEG_PATH", os.path.join(root, "ffmpeg.exe")), \
             patch.object(yt_app, "ensure_cli_ready", return_value=(True, "")), \
             patch.object(yt_app, "is_valid_windows_executable", return_value=True), \
             patch.object(yt_app, "build_twitch_command", return_value=["cmd"]), \
             patch.object(yt_app.subprocess, "Popen", return_value=FakeProcess()):
            success = api._download_twitch_video(
                {"url": "https://twitch.tv/videos/1234567890"}, root,
                "Meilleure qualité (Auto)", 1, 1
            )
        self.assertFalse(success)
        self.assertTrue(any("refuse" in x and "showAppToast" in x
                            for x in api._window.events))
        self.assertFalse(any("3762504530" in x for x in api._window.events))

    def test_queue_failure_is_reported_as_error_not_success(self):
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api.config = {}
        api.is_cancelled = False
        api.is_paused = False
        api._active_download_process = None
        api._suspended_download_pids = []
        api._window = type("Ui", (), {"events": [], "evaluate_js": lambda self, x: self.events.append(x)})()
        class ImmediateThread:
            def __init__(self, target, **kwargs):
                self.target = target
            def start(self):
                self.target()
        with tempfile.TemporaryDirectory() as root:
            api.download_folder = root
            with patch.object(yt_app.threading, "Thread", ImmediateThread), \
                 patch.object(yt_app, "ensure_ytdlp_ready") as ytdlp, \
                 patch.object(api, "_download_twitch_video", return_value=False):
                api.start_downloads([{"url": "https://twitch.tv/videos/1234567890",
                                      "mode": "Vidéo"}])
        ytdlp.assert_not_called()
        self.assertTrue(any("avec erreurs" in x
                            for x in api._window.events))


if __name__ == "__main__":
    unittest.main()
