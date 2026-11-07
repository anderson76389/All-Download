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
        self.assertEqual(info["selectedQuality"], "1080p (60fps)")
        self.assertEqual(info["selectedQualityLabel"], "1080p (60fps)")
        self.assertIn("720p (60fps)", info["formats"])
        self.assertIn("480p (30fps)", info["formats"])
        fallback_720 = twitch_vod.fallback_metadata(url, formats=["720p (60fps)"])
        self.assertEqual(fallback_720["formats"], ["Meilleure qualité (Auto)", "720p (60fps)"])
        self.assertEqual(fallback_720["selectedQuality"], "720p (60fps)")
        self.assertEqual(info["item_count"], 1)
        self.assertIsNone(twitch_vod.fallback_metadata("https://twitch.tv/user"))

    def test_default_quality_selection_prefers_1080_then_720(self):
        picker = twitch_vod.preferred_twitch_quality
        self.assertEqual(picker(["Meilleure qualité (Auto)", "1080p", "720p"]), "1080p")
        self.assertEqual(picker(["Meilleure qualité (Auto)", "720p (60fps)", "480p (30fps)"]),
                         "720p (60fps)")
        self.assertEqual(picker(["Meilleure qualité (Auto)", "1080p (30fps)", "720p (60fps)"]),
                         "1080p (30fps)")
        self.assertEqual(picker(["Meilleure qualité (Auto)"]), "1080p (60fps)")
        self.assertEqual(picker(["Meilleure qualité (Auto)", "480p"]), "480p")

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
        self.assertEqual(result["data"]["selectedQuality"], "1080p (60fps)")
        self.assertIn("720p (60fps)", result["data"]["formats"])
        self.assertIn("480p (30fps)", result["data"]["formats"])

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
            self.assertEqual(os.path.basename(twitch.call_args.args[1]), "TWITCH")


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
             patch.object(yt_app.subprocess, "Popen", return_value=FakeProcess()), \
             patch.object(api, "_download_twitch_hls", return_value=(False, "Aucun manifest HLS")):
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


    def test_twitch_hls_does_not_convert_when_no_native_quality_exists(self):
        import yt_app
        from twitch_hls import HLSUnavailable
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = None
        api.is_cancelled = False
        api._active_download_process = None
        with tempfile.TemporaryDirectory() as root:
            with patch.object(yt_app, "resolve_hls",
                              side_effect=HLSUnavailable("Aucun 1080p ou 720p natif")) as lookup, \
                 patch.object(yt_app.subprocess, "Popen") as popen, \
                 patch.object(yt_app, "twitch_hls_ffmpeg_command") as convert:
                success, reason = api._download_twitch_hls(
                    {"url": "https://twitch.tv/videos/2919531847", "title": "Test"},
                    root, "1080p (60fps)", 1, 1, lambda *args: None
                )
            self.assertFalse(success)
            self.assertIn("Aucun 1080p ou 720p natif", reason)
            lookup.assert_called_once()
            self.assertTrue(callable(lookup.call_args.kwargs["source_height_probe"]))
            popen.assert_not_called()
            convert.assert_not_called()

    def test_twitch_hls_preserves_native_stream_without_transcoding(self):
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = None
        api.is_cancelled = False
        api._active_download_process = None
        class FakeProcess:
            pid = 10001
            stdout = io.StringIO("out_time_ms=5000000\n")
            def wait(self):
                return 0
            def poll(self):
                return 0
        with tempfile.TemporaryDirectory() as root:
            temp = os.path.join(root, ".twitch.part.mp4")
            final = os.path.join(root, "Twitch_2919531847.mp4")
            def fake_open(*args, **kwargs):
                with open(temp, "wb") as output:
                    output.write(b"native media" * 200)
                return FakeProcess()
            with patch.object(yt_app, "resolve_hls", return_value=(
                    "https://example.cloudfront.net/stream/720p60/index-dvr.m3u8",
                    "720p60", 8030, 803)) as lookup, \
                 patch.object(yt_app, "twitch_hls_paths",
                              return_value=(__import__("pathlib").Path(temp), __import__("pathlib").Path(final))), \
                 patch.object(yt_app, "twitch_hls_ffmpeg_command",
                              return_value=["ffmpeg", "-c", "copy"]) as builder, \
                 patch.object(yt_app.subprocess, "Popen", side_effect=fake_open) as popen:
                success, reason = api._download_twitch_hls(
                    {"url": "https://twitch.tv/videos/2919531847", "title": "Test"},
                    root, "1080p (60fps)", 1, 1, lambda *args: None
                )
            self.assertTrue(success, reason)
            self.assertTrue(os.path.isfile(final))
            lookup.assert_called_once()
            builder.assert_called_once()
            self.assertEqual(len(builder.call_args.args), 3)
            self.assertEqual(builder.call_args.kwargs, {})
            self.assertNotIn("-vf", popen.call_args.args[0])
            self.assertIn("copy", popen.call_args.args[0])

    def test_twitch_cli_refusal_retries_hls_and_succeeds(self):
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = None
        api.is_cancelled = False
        api._active_download_process = None
        class FakeProcess:
            pid = 10001
            stdout = io.StringIO("Unhandled exception. (Insufficient access to VOD)\n")
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
             patch.object(yt_app.subprocess, "Popen", return_value=FakeProcess()), \
             patch.object(api, "_download_twitch_hls", return_value=(True, "")) as fallback:
            success = api._download_twitch_video(
                {"url": "https://twitch.tv/videos/2919531847"}, root,
                "Meilleure qualité (Auto)", 1, 1
            )
        self.assertTrue(success)
        fallback.assert_called_once()

    def test_hls_fallback_reports_success_and_preserves_existing_file(self):
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = None
        api.is_cancelled = False
        api._active_download_process = None
        with tempfile.TemporaryDirectory() as root:
            first_output = os.path.join(root, "Twitch_2919531847_VOD.mp4")
            with open(first_output, "wb") as existing:
                existing.write(b"old file must remain")
            from pathlib import Path
            new_output = Path(root, "Twitch_2919531847_VOD (2).mp4")
            temp_output = Path(root, ".test-part.mp4")
            def fake_popen(*args, **kwargs):
                temp_output.write_bytes(b"sample output" * 200)
                class FakeProcess:
                    pid = 10001
                    stdout = io.StringIO("out_time_ms=3000000\nout_time_ms=6000000\n")
                    def wait(self):
                        return 0
                    def poll(self):
                        return 0
                return FakeProcess()
            with patch.object(yt_app, "resolve_hls",
                              return_value=("https://d1.example.cloudfront.net/abcd/chunked/index-dvr.m3u8",
                                            "chunked", 10, 1)), \
                 patch.object(yt_app, "twitch_hls_paths", return_value=(temp_output, new_output)), \
                 patch.object(yt_app, "twitch_hls_ffmpeg_command", return_value=["ffmpeg.exe"]), \
                 patch.object(yt_app.subprocess, "Popen", side_effect=fake_popen):
                success, reason = api._download_twitch_hls(
                    {"url": "https://twitch.tv/videos/2919531847", "title": "VOD"},
                    root, "Meilleure qualité (Auto)", 1, 1,
                    lambda pct, label: None
                )
            self.assertTrue(success, reason)
            self.assertEqual(open(first_output, "rb").read(), b"old file must remain")
            self.assertTrue(new_output.is_file())
            self.assertFalse(temp_output.exists())



    def test_no_cli_download_or_github_access_still_uses_native_hls(self):
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = None
        api.is_cancelled = False
        api.is_paused = False
        api._active_download_process = None
        with tempfile.TemporaryDirectory() as root, \
             patch.object(yt_app, "ensure_cli_ready",
                          return_value=(False, "GitHub indisponible")) as cli, \
             patch.object(yt_app, "is_valid_windows_executable", return_value=True), \
             patch.object(yt_app.subprocess, "Popen",
                          side_effect=AssertionError("Le CLI absent ne doit jamais être lancé")) as launch, \
             patch.object(api, "_download_twitch_hls",
                          return_value=(True, "")) as hls:
            ok = api._download_twitch_video(
                {"url": "https://twitch.tv/videos/2919531847", "title": "Amine"},
                root, "1080p (60fps)", 1, 1
            )
        self.assertTrue(ok)
        cli.assert_called_once()
        launch.assert_not_called()
        hls.assert_called_once()
        self.assertEqual(hls.call_args.args[2], "1080p (60fps)")
        self.assertFalse(api.is_cancelled)

    def test_cli_launch_exception_falls_back_to_native_hls(self):
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = None
        api.is_cancelled = False
        api._active_download_process = None
        with tempfile.TemporaryDirectory() as root, \
             patch.object(yt_app, "ensure_cli_ready", return_value=(True, "")), \
             patch.object(yt_app, "is_valid_windows_executable", return_value=True), \
             patch.object(yt_app, "build_twitch_command",
                          return_value=["TwitchDownloaderCLI.exe"]), \
             patch.object(yt_app.subprocess, "Popen", side_effect=OSError("blocked by Windows")), \
             patch.object(api, "_download_twitch_hls",
                          return_value=(True, "")) as hls:
            self.assertTrue(api._download_twitch_video(
                {"url": "https://twitch.tv/videos/2919531847"},
                root, "720p (60fps)", 1, 1
            ))
        hls.assert_called_once()
        self.assertEqual(hls.call_args.args[2], "720p (60fps)")

    def test_healthy_cli_is_still_prioritized_and_not_duplicated_by_hls(self):
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = None
        api.is_cancelled = False
        api._active_download_process = None
        class DoneProcess:
            pid = 10001
            stdout = io.StringIO("[STATUS] Downloading 100%\n")
            def poll(self):
                return 0
            def wait(self):
                return 0
        with tempfile.TemporaryDirectory() as root, \
             patch.object(yt_app, "ensure_cli_ready", return_value=(True, "")), \
             patch.object(yt_app, "is_valid_windows_executable", return_value=True), \
             patch.object(yt_app, "build_twitch_command",
                          return_value=["TwitchDownloaderCLI.exe", "videodownload"]) as cli_command, \
             patch.object(yt_app.subprocess, "Popen",
                          return_value=DoneProcess()) as launch, \
             patch.object(api, "_download_twitch_hls") as hls:
            self.assertTrue(api._download_twitch_video(
                {"url": "https://twitch.tv/videos/2919531847"},
                root, "1080p (60fps)", 1, 1
            ))
        cli_command.assert_called_once()
        launch.assert_called_once()
        hls.assert_not_called()
        self.assertIsNone(api._active_download_process)

    def test_cancellation_does_not_trigger_an_extra_hls_download(self):
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = None
        api.is_cancelled = True
        api._active_download_process = None
        with tempfile.TemporaryDirectory() as root, \
             patch.object(yt_app, "ensure_cli_ready") as cli, \
             patch.object(api, "_download_twitch_hls") as hls:
            self.assertFalse(api._download_twitch_video(
                {"url": "https://twitch.tv/videos/2919531847"},
                root, "1080p (60fps)", 1, 1
            ))
        cli.assert_not_called()
        hls.assert_not_called()

    def test_no_unverified_ffmpeg_means_hls_not_launched(self):
        import yt_app
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = None
        api.is_cancelled = False
        api._active_download_process = None
        with tempfile.TemporaryDirectory() as root, \
             patch.object(yt_app, "ensure_cli_ready",
                          return_value=(False, "offline")), \
             patch.object(yt_app, "is_valid_windows_executable", return_value=False), \
             patch.object(yt_app, "setup_binaries") as provision, \
             patch.object(api, "_download_twitch_hls") as hls:
            self.assertFalse(api._download_twitch_video(
                {"url": "https://twitch.tv/videos/2919531847"},
                root, "1080p (60fps)", 1, 1
            ))
        provision.assert_called_once()
        hls.assert_not_called()



if __name__ == "__main__":
    unittest.main()
