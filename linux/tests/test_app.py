"""No-network Linux regressions and opt-in localhost media end-to-end test."""
import importlib.util
import re
import sys
import time
from unittest import mock
import json
import os
import tempfile
import unittest
from pathlib import Path

from linux.app import DownloaderAPI, category_for, cleanup_old_workspaces, inside_folder, is_twitch_vod_url, native_twitch_format, should_emit_progress, valid_url, video_format
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

    def test_twitch_failure_retries_native_source_then_marks_success(self):
        url = "https://www.twitch.tv/videos/2919531847"
        manifest = "https://public.cloudfront.net/source/chunked/index-dvr.m3u8"
        self.api._js = mock.Mock()
        with mock.patch.object(self.api, "_command", side_effect=lambda *_: ["yt-dlp", "-o", "out.mp4", url]), \
             mock.patch.object(self.api, "_run_transfer", side_effect=[(1, "403"), (0, "")]) as transfer, \
             mock.patch("twitch_hls.resolve_hls", return_value=(manifest, "source", 10, 1)):
            self.api._worker([{"url": url, "mode": "Vidéo"}])
        self.assertEqual(transfer.call_count, 2)
        self.assertEqual(transfer.call_args.args[0][-1], manifest)
        self.api._js.assert_any_call("markDownloadSuccess", url)
        self.assertFalse(self.api._running)

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
        self.assertEqual("bestvideo+bestaudio/best", native_twitch_format("Meilleure qualité (Auto)"))
        native = native_twitch_format("1080p")
        self.assertIn("height=1080", native)
        self.assertIn("height=720", native)
        self.assertNotIn("480", native)
        with self.assertRaises(ValueError):
            native_twitch_format("480p")
        self.assertIn("height<=?720", video_format("720p"))
        self.assertEqual("TWITCH", category_for({"url": "https://www.twitch.tv/videos/12345", "mode": "Vidéo"}))
        self.assertEqual("AUDIOS", category_for({"url": "https://youtu.be/test", "mode": "Audio"}))

    def test_twitch_selected_1080_falls_back_to_real_native_720(self):
        # The quality preselected after metadata extraction was "1080p".
        # Previously that path had no 720p fallback even when Auto did.
        for selected in ("1080p", "1080p (60fps)"):
            fmt = native_twitch_format(selected)
            self.assertIn("height=1080", fmt)
            self.assertIn("height=720", fmt)
            self.assertNotIn("480", fmt)
            self.assertEqual(fmt.count("height=1080"), 2)
        limited = native_twitch_format("720p")
        self.assertIn("height=720", limited)
        self.assertNotIn("height=1080", limited)

    def test_old_linux_scratch_cleanup_never_removes_downloads(self):
        scratch = self.root / "Donnees" / "temporaires"
        old = scratch / ("a" * 32)
        recent = scratch / ("b" * 32)
        manual = scratch / "important-user-folder"
        outside = self.root / "VIDÉOS" / "user-video.mp4"
        old.mkdir()
        recent.mkdir()
        manual.mkdir()
        (old / "partial.part").write_bytes(b"old interrupted video segment")
        outside.write_bytes(b"keep this video")
        clock = time.time()
        os.utime(old, (clock - 9 * 86400, clock - 9 * 86400))
        os.utime(recent, (clock - 2 * 86400, clock - 2 * 86400))
        os.utime(manual, (clock - 20 * 86400, clock - 20 * 86400))
        self.assertEqual(1, cleanup_old_workspaces(scratch, now=clock))
        self.assertFalse(old.exists())
        self.assertTrue(recent.is_dir())
        self.assertTrue(manual.is_dir())
        self.assertEqual(b"keep this video", outside.read_bytes())
        self.assertEqual(0, cleanup_old_workspaces(scratch, now=clock))

    def test_cleanup_refuses_symlink_and_limits_work(self):
        scratch = self.root / "Donnees" / "temporaires"
        outside = self.root / "AUTRES" / "safe"
        outside.mkdir()
        clock = time.time()
        target = scratch / ("c" * 32)
        target.symlink_to(outside, target_is_directory=True)
        old = scratch / ("d" * 32)
        old.mkdir()
        os.utime(old, (clock - 9 * 86400, clock - 9 * 86400))
        self.assertEqual(0, cleanup_old_workspaces(scratch, now=clock, max_removals=0))
        self.assertEqual(1, cleanup_old_workspaces(scratch, now=clock, max_removals=1))
        self.assertTrue(target.is_symlink())
        self.assertTrue(outside.is_dir())
        self.assertEqual(0, cleanup_old_workspaces(target, now=clock))

    def test_progress_notifications_throttled_without_losing_completion(self):
        self.assertTrue(should_emit_progress(0.2, 1.0, -1, 0))
        self.assertFalse(should_emit_progress(0.3, 1.1, 0.2, 1.0))
        self.assertTrue(should_emit_progress(0.4, 1.6, 0.2, 1.0))
        self.assertTrue(should_emit_progress(2.0, 1.1, 0.2, 1.0))
        self.assertTrue(should_emit_progress(0.0, 1.1, 99.0, 1.0))
        self.assertTrue(should_emit_progress(100.0, 1.1, 99.8, 1.0))

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
        self.assertEqual("0.5", command[command.index("--progress-delta") + 1])
        self.assertTrue(any("AUDIOS" in arg for arg in command))
        self.assertTrue(any("temporaires" in arg for arg in command))
        self.assertTrue(command[-1].startswith("https://"))
        self.assertNotIn("--exec", command)


    def test_every_windows_ui_bridge_action_has_a_linux_implementation(self):
        """A future Windows UI change must not silently create dead Linux buttons."""
        html = extract(Path(__file__).resolve().parents[2] / "yt_app.py")
        calls = set(re.findall(r"""callApi\(\s*['"]([a-zA-Z_0-9]+)['"]""", html))
        self.assertGreaterEqual(len(calls), 16)
        missing = sorted(name for name in calls if not callable(getattr(self.api, name, None)))
        self.assertEqual([], missing, "Linux UI controls without native methods")
        for callback in ("markDownloadSuccess", "markDownloadFailure",
                         "updateDownloadProgress", "finishDownloadUIState", "showAppToast"):
            self.assertIn("function " + callback + "(", html)

    def test_mkv_remux_matches_video_container_selection(self):
        bin_dir = self.root / "Donnees" / "bin"
        for binary in ("yt-dlp", "ffmpeg"):
            executable = bin_dir / binary
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
        settings = self.api.get_app_settings()
        settings.update(video_format="MKV", post_process_video="Remuxer")
        self.assertTrue(self.api.save_app_settings(settings)["success"])
        command = self.api._command(
            {"url": "https://example.org/movie.mp4", "mode": "Vidéo",
             "selectedQuality": "1080p"}, self.api.temp / "video")
        self.assertEqual("mkv", command[command.index("--merge-output-format") + 1])
        self.assertEqual("mkv", command[command.index("--remux-video") + 1])

    def test_sponsorblock_uses_only_genuine_youtube_hosts(self):
        bin_dir = self.root / "Donnees" / "bin"
        for name in ("yt-dlp", "ffmpeg"):
            binary = bin_dir / name
            binary.write_text("#!/bin/sh\nexit 0\n")
            binary.chmod(0o755)
        settings = self.api.get_app_settings()
        settings.update(sponsor_enable=True, sponsor_remove="sponsor",
                        sponsor_mark="chapters")
        self.assertTrue(self.api.save_app_settings(settings)["success"])
        for url, expected in (
            ("https://www.youtube.com/watch?v=abc123", True),
            ("https://music.youtube.com/watch?v=abc123", True),
            ("https://youtu.be/abc123", True),
            ("https://notyoutube.com/watch?v=abc123", False),
            ("https://youtube.com.evil.example/watch?v=abc123", False),
            ("https://evil.example/watch?v=youtube.com", False),
        ):
            command = self.api._command(
                {"url": url, "mode": "Vidéo", "selectedQuality": "720p"},
                self.api.temp / "video")
            self.assertEqual("--sponsorblock-remove" in command, expected, url)
            self.assertEqual("--sponsorblock-mark" in command, expected, url)

    def test_twitch_vod_format_applies_only_to_real_twitch_hosts(self):
        self.assertTrue(is_twitch_vod_url("https://www.twitch.tv/videos/123456789"))
        self.assertTrue(is_twitch_vod_url("https://m.twitch.tv/videos/123456789"))
        for url in (
            "https://www.twitch.tv.evil.example/videos/123456789",
            "https://not-twitch.tv/videos/123456789",
            "https://www.twitch.tv/videos/12345wrong",
            "https://www.twitch.tv/not-videos/123456789",
            "https://www.twitch.tv/videos/1"
        ):
            self.assertFalse(is_twitch_vod_url(url), url)
        bin_dir = self.root / "Donnees" / "bin"
        for name in ("yt-dlp", "ffmpeg"):
            executable = bin_dir / name
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
        for url, twitch in (
            ("https://www.twitch.tv/videos/123456789", True),
            ("https://www.twitch.tv.evil.example/videos/123456789", False)
        ):
            cmd = self.api._command(
                {"url": url, "mode": "Vidéo", "selectedQuality": "1080p"},
                self.api.temp / "vod")
            chosen = cmd[cmd.index("--format") + 1]
            self.assertEqual("height=1080" in chosen, twitch)

    def test_cookie_import_rejects_large_file_without_loading_it_into_memory(self):
        import types
        filename = self.root / "oversize-cookies.txt"
        with filename.open("wb") as handle:
            handle.write(b"# Netscape HTTP Cookie File\n")
            handle.truncate(3_000_000)
        self.api._window = types.SimpleNamespace(create_file_dialog=lambda *_a, **_kw: [str(filename)])
        mock_webview = types.SimpleNamespace(FileDialog=types.SimpleNamespace(OPEN="open"))
        with mock.patch.dict(sys.modules, {"webview": mock_webview}), mock.patch.object(
                Path, "read_bytes", side_effect=AssertionError("Large file should not be read")
        ):
            self.assertIsNone(self.api.select_cookie_file())
        self.assertFalse((self.api.data / "cookies.txt").exists())

    @unittest.skipUnless(sys.platform.startswith("linux"), "POSIX process-group test")
    def test_pause_resume_cancel_does_not_leave_running_processes(self):
        """Exercise actual SIGSTOP / SIGCONT / SIGTERM against a local stub."""
        bin_dir = self.root / "Donnees" / "bin"
        downloader = bin_dir / "yt-dlp"
        downloader.write_text(
            "#!/bin/sh\n"
            "echo '[download] 2.0% of media'\n"
            "sleep 15\n"
            "echo '[download] 100.0% of media'\n")
        downloader.chmod(0o755)
        ffmpeg = bin_dir / "ffmpeg"
        ffmpeg.write_text("#!/bin/sh\nexit 0\n")
        ffmpeg.chmod(0o755)
        result = self.api.start_downloads([{
            "url": "https://example.org/synthetic.mp4", "mode": "Vidéo"
        }])
        self.assertTrue(result["success"], result)
        try:
            deadline = time.monotonic() + 8
            while self.api._current is None and time.monotonic() < deadline:
                time.sleep(.05)
            proc = self.api._current
            self.assertIsNotNone(proc, "Local yt-dlp stub was not started")
            self.assertIsNone(proc.poll())
            pause = self.api.pause_downloads()
            self.assertEqual({"success": True, "mode": "active"}, pause)
            self.assertTrue(self.api._paused)
            self.assertEqual({"success": True}, self.api.resume_downloads())
            self.assertFalse(self.api._paused)
            self.assertTrue(self.api.cancel_downloads())
            deadline = time.monotonic() + 8
            while self.api._running and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertFalse(self.api._running, "Cancelled process did not stop")
            self.assertIsNotNone(proc.poll(), "yt-dlp stub survived cancellation")
            self.assertEqual([], list(self.api.temp.iterdir()),
                             "Cancelled task left temporary files behind")
        finally:
            self.api.cancel_downloads()


if __name__ == "__main__":
    unittest.main()
