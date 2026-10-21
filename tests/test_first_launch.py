"""Tests du tout premier lancement : FFmpeg et yt-dlp absents au depart."""
import io
import os
import shutil
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import yt_app


def valid_pe64_stub():
    """PE x64 synthetique pour les tests, jamais livre aux utilisateurs."""
    payload = bytearray(65536)
    payload[:2] = b"MZ"
    payload[0x3C:0x40] = (0x80).to_bytes(4, "little")
    payload[0x80:0x86] = bytes((80, 69, 0, 0, 0x64, 0x86))
    return bytes(payload)


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
            zf.writestr("ffmpeg-release/bin/ffmpeg.exe", valid_pe64_stub())
            zf.writestr("ffmpeg-release/bin/ffprobe.exe", valid_pe64_stub())
        return data.getvalue()

    def test_first_run_streams_binaries_and_removes_zip(self):
        archive = self.make_archive()
        requests = []

        def fake_open(url, timeout):
            requests.append((url, timeout))
            return io.BytesIO(archive if url.endswith(".zip") else valid_pe64_stub())

        with patch.object(yt_app.urllib.request, "urlopen", side_effect=fake_open):
            yt_app.setup_binaries()

        with open(self.ytdlp_path, "rb") as file:
            self.assertEqual(file.read(), valid_pe64_stub())
        with open(self.ffmpeg_path, "rb") as file:
            self.assertEqual(file.read(), valid_pe64_stub())
        with open(self.ffprobe_path, "rb") as file:
            self.assertEqual(file.read(), valid_pe64_stub())
        self.assertEqual(len(requests), 2)
        self.assertFalse(os.path.exists(os.path.join(self.base, "ffmpeg.zip")))
        self.assertFalse(os.path.exists(self.ffmpeg_path + ".tmp"))

    def test_second_run_does_not_redownload_or_replace(self):
        with open(self.ytdlp_path, "wb") as file:
            file.write(valid_pe64_stub())
        with open(self.ffmpeg_path, "wb") as file:
            file.write(valid_pe64_stub())
        with patch.object(yt_app.urllib.request, "urlopen", side_effect=AssertionError("Unexpected download")):
            yt_app.setup_binaries()
        with open(self.ytdlp_path, "rb") as file:
            self.assertEqual(file.read(), valid_pe64_stub())
        with open(self.ffmpeg_path, "rb") as file:
            self.assertEqual(file.read(), valid_pe64_stub())

    def test_fake_two_byte_mz_cannot_pass_windows_exe_validation(self):
        for filename in (self.ytdlp_path, self.ffmpeg_path, self.ffprobe_path):
            with open(filename, "wb") as out:
                out.write(b"MZ")
            self.assertFalse(yt_app.is_valid_windows_executable(filename))

    def test_valid_pe64_stub_passes_static_pe_check(self):
        with open(self.ytdlp_path, "wb") as out:
            out.write(valid_pe64_stub())
        self.assertTrue(yt_app.is_valid_windows_executable(self.ytdlp_path))

    def test_faux_executables_du_zip_151_sont_repares(self):
        for filename in (self.ytdlp_path, self.ffmpeg_path, self.ffprobe_path):
            with open(filename, "wb") as out:
                out.write(b"MZ")
        archive = self.make_archive()
        urls = []
        def fake_open(url, timeout):
            urls.append(url)
            return io.BytesIO(archive if url.endswith(".zip") else valid_pe64_stub())
        with patch.object(yt_app.urllib.request, "urlopen", side_effect=fake_open):
            yt_app.setup_binaries()
        self.assertEqual(len(urls), 2)
        self.assertTrue(all(yt_app.is_valid_windows_executable(name)
                            for name in (self.ytdlp_path, self.ffmpeg_path, self.ffprobe_path)))

    def test_invalid_yt_dlp_download_is_rejected_and_old_file_preserved(self):
        with open(self.ytdlp_path, "wb") as out:
            out.write(b"MZ")
        with patch.object(yt_app.urllib.request, "urlopen", return_value=io.BytesIO(b"MZ")):
            self.assertFalse(yt_app.safe_download_file(yt_app.YTDLP_URL, self.ytdlp_path))
        with open(self.ytdlp_path, "rb") as original:
            self.assertEqual(original.read(), b"MZ")
        self.assertFalse(os.path.exists(self.ytdlp_path + ".tmp"))

    def test_ensure_ytdlp_recovers_without_ffmpeg_download(self):
        with open(self.ytdlp_path, "wb") as out:
            out.write(b"MZ")
        requested = []
        def fake_open(url, timeout):
            requested.append(url)
            if url.endswith(".zip"):
                raise AssertionError("ffmpeg ne doit pas etre telecharge pour lire des metadonnees")
            return io.BytesIO(valid_pe64_stub())
        with patch.object(yt_app.urllib.request, "urlopen", side_effect=fake_open):
            self.assertTrue(yt_app.ensure_ytdlp_ready())
        self.assertEqual(requested, [yt_app.YTDLP_URL])
        self.assertFalse(os.path.exists(self.ffmpeg_path))

    def test_failed_download_leaves_no_broken_binary(self):
        with patch.object(yt_app.urllib.request, "urlopen", side_effect=OSError("connection lost")):
            self.assertFalse(yt_app.safe_download_file("https://test.invalid/file", self.ffmpeg_path))
        self.assertFalse(os.path.exists(self.ffmpeg_path))
        self.assertFalse(os.path.exists(self.ffmpeg_path + ".tmp"))
        with open(os.path.join(self.base, "crash_log.txt"), encoding="utf-8") as file:
            self.assertIn("connection lost", file.read())

    def test_incomplete_archive_is_not_installed(self):
        def fake_open(url, timeout):
            return io.BytesIO(b"invalid ZIP" if url.endswith(".zip") else valid_pe64_stub())

        with patch.object(yt_app.urllib.request, "urlopen", side_effect=fake_open):
            yt_app.setup_binaries()
        self.assertFalse(os.path.exists(self.ffmpeg_path))
        self.assertFalse(os.path.exists(os.path.join(self.base, "ffmpeg.zip")))
        with open(os.path.join(self.base, "crash_log.txt"), encoding="utf-8") as file:
            self.assertIn("BadZipFile", file.read())


if __name__ == "__main__":
    unittest.main()
