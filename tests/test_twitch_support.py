"""Régressions ciblées Twitch / mise à jour de yt-dlp, sans accès réseau."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yt_app


class ImmediateThread:
    def __init__(self, target, **_kwargs):
        self.target = target

    def start(self):
        self.target()


class FakeProcess:
    def __init__(self, output="", code=0):
        self.stdout = io.StringIO(output)
        self.returncode = code
        self.pid = 12345

    def communicate(self, timeout=None):
        return ("", "")


class Recorder:
    def __init__(self):
        self.scripts = []

    def evaluate_js(self, script):
        self.scripts.append(script)


class TwitchUrlTests(unittest.TestCase):
    def test_twitch_vods_but_not_clips_or_lives(self):
        for link in (
            "https://www.twitch.tv/videos/1234567890",
            "https://twitch.tv/videos/1234567890?t=2h3m",
            "https://www.twitch.tv/streamer/v/1234567890",
            "https://www.twitch.tv/streamer/schedule?vodID=1234567890",
        ):
            with self.subTest(link=link):
                self.assertTrue(yt_app.is_twitch_vod_url(link))
        for link in (
            "https://www.twitch.tv/streamer",
            "https://clips.twitch.tv/FunnyClip",
            "https://example.org/videos/1234567890",
            "https://www.twitch.tv/videos/not-a-number",
        ):
            with self.subTest(link=link):
                self.assertFalse(yt_app.is_twitch_vod_url(link))

    def test_twitch_metadata_has_longer_timeout_and_is_not_playlist(self):
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api.config = {"settings": {}}
        info = {"id": "v1234567890", "title": "Ma VOD Twitch",
                "formats": [{"height": 1080, "fps": 60}]}
        commands = []
        timeouts = []

        def popen(cmd, **kwargs):
            commands.append(cmd)
            process = FakeProcess(code=0)
            def communicate(timeout=None):
                timeouts.append(timeout)
                return (json.dumps(info), "")
            process.communicate = communicate
            return process

        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=True), patch.object(
            yt_app.subprocess, "Popen", side_effect=popen
        ):
            result = api.extract_info("https://www.twitch.tv/videos/1234567890")
        self.assertTrue(result["success"], result)
        self.assertEqual(timeouts, [120])
        self.assertNotIn("--flat-playlist", commands[0])
        self.assertFalse(result["data"]["is_playlist"])


class TwitchDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        self.api.config = {
            "settings": {"video_format": "MP4", "video_embed_thumb": False,
                         "video_write_thumb": False, "video_add_metadata": False,
                         "sponsor_enable": False}
        }
        self.api.download_folder = self.tmp.name
        self.api._window = Recorder()
        self.api.is_cancelled = False
        self.api.is_paused = False
        self.api._active_download_process = None

    def _run(self, url, quality, process):
        commands = []
        item = {"url": url, "title": "Une VOD", "mode": "Vidéo",
                "selectedQuality": quality}
        def popen(cmd, **kwargs):
            commands.append(cmd)
            return process
        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=True), patch.object(
            yt_app.threading, "Thread", ImmediateThread
        ), patch.object(yt_app, "get_youtube_js_args", return_value=[]), patch.object(yt_app.subprocess, "Popen", side_effect=popen):
            self.api.start_downloads([item])
        return commands[0]

    def test_twitch_uses_muxed_hls_format_and_fragment_retries(self):
        cmd = self._run("https://www.twitch.tv/videos/1234567890",
                        "Meilleure qualité (Auto)", FakeProcess())
        self.assertEqual(cmd[cmd.index("-f") + 1], "best/bestvideo+bestaudio")
        self.assertEqual(cmd[cmd.index("--fragment-retries") + 1], "15")
        self.assertIn("--retry-sleep", cmd)
        self.assertTrue(any("markDownloadSuccess(" in script
                            for script in self.api._window.scripts))

    def test_youtube_format_is_preserved(self):
        cmd = self._run("https://www.youtube.com/watch?v=abcdefgh",
                        "Meilleure qualité (Auto)", FakeProcess())
        self.assertEqual(cmd[cmd.index("-f") + 1], "bestvideo+bestaudio/best")
        self.assertNotIn("--fragment-retries", cmd)

    def test_twitch_failure_is_reported_to_interface(self):
        self._run("https://www.twitch.tv/videos/1234567890",
                  "Meilleure qualité (Auto)",
                  FakeProcess("ERROR: HTTP Error 403: Forbidden\n", code=1))
        scripts = self.api._window.scripts
        self.assertTrue(any("403" in script and "Twitch" in script
                            for script in scripts), scripts)
        self.assertFalse(any("markDownloadSuccess(" in script for script in scripts))
        self.assertTrue(any("showAppToast(" in script for script in scripts))


class YtdlpUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.exe = Path(self.tmp.name) / "yt-dlp.exe"
        self.exe.write_bytes(b"version existante")
        self.api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        self.api._active_download_process = None

    def test_failed_download_does_not_destroy_old_binary(self):
        with patch.object(yt_app, "YTDLP_PATH", str(self.exe)), patch.object(
            yt_app, "is_valid_windows_executable", return_value=True
        ), patch.object(yt_app, "safe_download_file", return_value=False), patch.object(
            yt_app.subprocess, "run",
            return_value=SimpleNamespace(returncode=0, stdout="2025.01.01\n")
        ):
            result = self.api.update_ytdlp()
        self.assertFalse(result["success"])
        self.assertEqual(self.exe.read_bytes(), b"version existante")

    def test_update_checks_downloaded_binary_then_replaces(self):
        def fake_download(_url, dest):
            Path(dest).write_bytes(b"nouvelle version")
            return True
        def fake_run(cmd, **_kwargs):
            version = "2026.10.26" if cmd[0].endswith(".update.exe") else "2025.01.01"
            return SimpleNamespace(returncode=0, stdout=version + "\n")

        with patch.object(yt_app, "YTDLP_PATH", str(self.exe)), patch.object(
            yt_app, "is_valid_windows_executable", return_value=True
        ), patch.object(yt_app, "safe_download_file", side_effect=fake_download), patch.object(
            yt_app.subprocess, "run", side_effect=fake_run
        ):
            result = self.api.update_ytdlp()
        self.assertEqual(result, {"success": True, "updated": True, "version": "2026.10.26"})
        self.assertEqual(self.exe.read_bytes(), b"nouvelle version")
        self.assertFalse(Path(str(self.exe) + ".update.exe").exists())

    def test_busy_downloader_prevents_update(self):
        self.api._active_download_process = object()
        with patch.object(yt_app, "safe_download_file") as download:
            result = self.api.update_ytdlp()
        self.assertFalse(result["success"])
        download.assert_not_called()
        self.assertEqual(self.exe.read_bytes(), b"version existante")


if __name__ == "__main__":
    unittest.main()
