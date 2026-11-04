"""Tests YouTube + Deno : installation isolée et commandes yt-dlp, sans réseau réel."""
import io
import json
import os
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yt_app


def pe64():
    """PE x64 synthétique pour tester les contrôles d'en-tête, pas un vrai programme."""
    data = bytearray(65536)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 128)
    data[128:134] = b"PE\x00\x00\x64\x86"
    return bytes(data)


def make_archive(filename="deno.exe", content=None):
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(filename, pe64() if content is None else content)
    return memory.getvalue()


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
        return (self.stdout.getvalue(), "")


class DenoInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "Donnees avec espaces" / "bin" / "deno.exe"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        p = patch.object(yt_app, "DENO_PATH", str(self.path))
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(yt_app, "CRASH_LOG", str(Path(self.temp.name) / "crash.log"))
        p.start()
        self.addCleanup(p.stop)

    def run_deno(self, _cmd, **_kwargs):
        return SimpleNamespace(returncode=0, stdout="deno 2.9.8 (stable, release, x86_64-pc-windows-msvc)\nv8 14.0\n")

    def test_installs_official_archive_and_reuses_binary(self):
        urls = []
        data = make_archive()
        def fake_open(url, timeout):
            urls.append(url)
            return io.BytesIO(data)
        with patch.object(yt_app.urllib.request, "urlopen", side_effect=fake_open), patch.object(
            yt_app.subprocess, "run", side_effect=self.run_deno
        ):
            self.assertTrue(yt_app.ensure_deno_ready())
            self.assertEqual(self.path.read_bytes(), pe64())
            self.assertEqual(urls, [yt_app.DENO_URL])
            self.assertTrue(yt_app.ensure_deno_ready())
            self.assertEqual(urls, [yt_app.DENO_URL])
        self.assertFalse(Path(str(self.path) + ".candidate.exe").exists())
        self.assertFalse(Path(str(self.path) + ".download.zip").exists())

    def test_invalid_archive_preserves_old_program(self):
        self.path.write_bytes(b"previous invalid executable")
        with patch.object(yt_app.urllib.request, "urlopen", return_value=io.BytesIO(b"not zip")):
            self.assertFalse(yt_app.ensure_deno_ready())
        self.assertEqual(self.path.read_bytes(), b"previous invalid executable")
        self.assertFalse(Path(str(self.path) + ".download.zip").exists())

    def test_zip_traversal_is_rejected(self):
        with patch.object(yt_app.urllib.request, "urlopen", return_value=io.BytesIO(
            make_archive(filename="../deno.exe")
        )):
            self.assertFalse(yt_app.ensure_deno_ready())
        self.assertFalse(self.path.exists())
        self.assertFalse((Path(self.temp.name) / "deno.exe").exists())

    def test_old_version_never_replaces_original(self):
        self.path.write_bytes(pe64())
        original = self.path.read_bytes()
        def stale_run(_cmd, **_kwargs):
            return SimpleNamespace(returncode=0, stdout="deno 2.2.0\n")
        with patch.object(yt_app.urllib.request, "urlopen", return_value=io.BytesIO(make_archive())), patch.object(
            yt_app.subprocess, "run", side_effect=stale_run
        ):
            self.assertFalse(yt_app.ensure_deno_ready())
        self.assertEqual(self.path.read_bytes(), original)

    def test_accept_minimum_version_and_reject_older(self):
        self.path.write_bytes(pe64())
        for version, expected in (("2.3.0", True), ("2.2.9", False), ("1.45.5", False)):
            with self.subTest(version=version), patch.object(
                yt_app.subprocess, "run", return_value=SimpleNamespace(
                    returncode=0, stdout="deno " + version + "\n"
                )
            ):
                self.assertEqual(yt_app.is_supported_deno(str(self.path)), expected)

    def test_js_is_scoped_to_real_youtube_domains(self):
        urls = (
            "https://youtube.com/watch?v=abcdefgh",
            "https://youtu.be/abcdefgh",
            "https://music.youtube.com/watch?v=abcdefgh",
            "https://youtube.com/playlist?list=abc",
            "https://youtube.com/shorts/abcdefgh",
        )
        with patch.object(yt_app, "ensure_deno_ready", return_value=True) as ensure:
            for url in urls:
                with self.subTest(url=url):
                    self.assertEqual(yt_app.get_youtube_js_args(url), [
                        "--js-runtimes", "deno:" + str(self.path)
                    ])
            self.assertEqual(ensure.call_count, len(urls))
        with patch.object(yt_app, "ensure_deno_ready", side_effect=AssertionError("non YouTube")):
            for url in (
                "https://www.twitch.tv/videos/123456",
                "https://vimeo.com/123456",
                "https://youtube.com.evil.example/watch?v=1",
            ):
                self.assertEqual(yt_app.get_youtube_js_args(url), [])

    def test_no_deno_keeps_original_ytdlp_fallback(self):
        with patch.object(yt_app, "ensure_deno_ready", return_value=False):
            self.assertEqual(yt_app.get_youtube_js_args("https://youtube.com/watch?v=abcdef"), [])


class YoutubeCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        self.api.config = {
            "settings": {"video_embed_thumb": False, "video_write_thumb": False,
                         "video_add_metadata": False, "sponsor_enable": False,
                         "audio_format": "M4A", "audio_embed_thumb": False,
                         "audio_write_thumb": False, "audio_add_metadata": False}
        }
        self.api.download_folder = self.temp.name
        self.api.is_cancelled = False
        self.api.is_paused = False
        self.api._active_download_process = None
        self.api._window = None

    def test_metadata_gets_deno_args(self):
        commands = []
        info = {"title": "Test", "id": "abcdef", "formats": [{"height": 720}]}
        def popen(cmd, **_kwargs):
            commands.append(cmd)
            result = FakeProcess()
            result.communicate = lambda timeout=None: (json.dumps(info), "")
            return result
        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=True), patch.object(
            yt_app, "ensure_deno_ready", return_value=True
        ), patch.object(yt_app.subprocess, "Popen", side_effect=popen):
            result = self.api.extract_info("https://www.youtube.com/watch?v=abcdefgh")
        self.assertTrue(result["success"], result)
        cmd = commands[0]
        self.assertEqual(cmd[cmd.index("--js-runtimes") + 1], "deno:" + yt_app.DENO_PATH)

    def test_video_and_audio_downloads_get_deno_args(self):
        commands = []
        def popen(cmd, **_kwargs):
            commands.append(cmd)
            return FakeProcess()
        items = [
            {"url": "https://www.youtube.com/watch?v=abcdefgh", "title": "Test", "mode": "Vidéo"},
            {"url": "https://music.youtube.com/watch?v=abcdefg", "title": "Chanson", "mode": "Audio"},
            {"url": "https://www.twitch.tv/videos/1234567890", "title": "VOD", "mode": "Vidéo"},
        ]
        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=True), patch.object(
            yt_app, "ensure_deno_ready", return_value=True
        ), patch.object(yt_app.threading, "Thread", ImmediateThread), patch.object(
            yt_app.subprocess, "Popen", side_effect=popen):
            self.api.start_downloads(items)
        self.assertEqual(len(commands), 3)
        for command in commands[:2]:
            self.assertEqual(command[command.index("--js-runtimes") + 1], "deno:" + yt_app.DENO_PATH)
        self.assertNotIn("--js-runtimes", commands[2])


if __name__ == "__main__":
    unittest.main()
