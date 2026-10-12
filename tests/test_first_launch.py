"""Tests du tout premier lancement : FFmpeg et yt-dlp absents au depart."""
import io
import os
import shutil
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import yt_app


class FirstLaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = self.tmp.name
        self.bin = os.path.join(self.base, "bin")
        os.makedirs(self.bin)
        self.ytdlp_path = os.path.join(self.bin, "yt-dlp.exe")
        self.ffmpeg_path = os.path.join(self.bin, "ffmpeg.exe")
        self.ffprobe_path = os.path.join(self.bin, "ffprobe.exe")
        for key, value in (
            ("APP_DIR", self.base),
            ("BIN_DIR", self.bin),
            ("YTDLP_PATH", self.ytdlp_path),
            ("FFMPEG_PATH", self.ffmpeg_path),
            ("CRASH_LOG", os.path.join(self.base, "crash_log.txt")),
            ("YTDLP_URL", "https://test.invalid/yt-dlp.exe"),
            ("FFMPEG_URL", "https://test.invalid/ffmpeg.zip"),
        ):
            p = patch.object(yt_app, key, value)
            p.start()
            self.addCleanup(p.stop)

    def make_archive(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as zf:
            zf.writestr("ffmpeg-release/bin/ffmpeg.exe", b"ffmpeg binary" * 65536)
            zf.writestr("ffmpeg-release/bin/ffprobe.exe", b"ffprobe binary" * 65536)
        return data.getvalue()

    def test_first_run_streams_binaries_and_removes_zip(self):
        archive = self.make_archive()
        requests = []

        def fake_open(url, timeout):
            requests.append((url, timeout))
            return io.BytesIO(archive if url.endswith(".zip") else b"yt-dlp binary")

        with patch.object(yt_app.urllib.request, "urlopen", side_effect=fake_open):
            yt_app.setup_binaries()

        with open(self.ytdlp_path, "rb") as file:
            self.assertEqual(file.read(), b"yt-dlp binary")
        with open(self.ffmpeg_path, "rb") as file:
            self.assertEqual(file.read(), b"ffmpeg binary" * 65536)
        with open(self.ffprobe_path, "rb") as file:
            self.assertEqual(file.read(), b"ffprobe binary" * 65536)
        self.assertEqual(len(requests), 2)
        self.assertFalse(os.path.exists(os.path.join(self.base, "ffmpeg.zip")))
        self.assertFalse(os.path.exists(self.ffmpeg_path + ".tmp"))

    def test_second_run_does_not_redownload_or_replace(self):
        with open(self.ytdlp_path, "wb") as file:
            file.write(b"already installed")
        with open(self.ffmpeg_path, "wb") as file:
            file.write(b"already installed")
        with patch.object(yt_app.urllib.request, "urlopen", side_effect=AssertionError("Unexpected download")):
            yt_app.setup_binaries()
        with open(self.ytdlp_path, "rb") as file:
            self.assertEqual(file.read(), b"already installed")
        with open(self.ffmpeg_path, "rb") as file:
            self.assertEqual(file.read(), b"already installed")

    def test_failed_download_leaves_no_broken_binary(self):
        with patch.object(yt_app.urllib.request, "urlopen", side_effect=OSError("connection lost")):
            self.assertFalse(yt_app.safe_download_file("https://test.invalid/file", self.ffmpeg_path))
        self.assertFalse(os.path.exists(self.ffmpeg_path))
        self.assertFalse(os.path.exists(self.ffmpeg_path + ".tmp"))
        with open(os.path.join(self.base, "crash_log.txt"), encoding="utf-8") as file:
            self.assertIn("connection lost", file.read())

    def test_incomplete_archive_is_not_installed(self):
        def fake_open(url, timeout):
            return io.BytesIO(b"invalid ZIP" if url.endswith(".zip") else b"yt-dlp binary")

        with patch.object(yt_app.urllib.request, "urlopen", side_effect=fake_open):
            yt_app.setup_binaries()
        self.assertFalse(os.path.exists(self.ffmpeg_path))
        self.assertFalse(os.path.exists(os.path.join(self.base, "ffmpeg.zip")))
        with open(os.path.join(self.base, "crash_log.txt"), encoding="utf-8") as file:
            self.assertIn("BadZipFile", file.read())


if __name__ == "__main__":
    unittest.main()
