"""Tests du Deno local : aucune requête réseau, aucun vrai EXE téléchargé."""
import hashlib
import io
import json
import os
import struct
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import deno_runtime


class LocalDenoTests(unittest.TestCase):
    def setUp(self):
        deno_runtime._VALIDATED.clear()
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.addCleanup(deno_runtime._VALIDATED.clear)

    @staticmethod
    def windows_exe():
        data = bytearray(70_000)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3c, 128)
        data[128:132] = b"PE\0\0"
        struct.pack_into("<H", data, 132, 0x8664)
        return bytes(data)

    @staticmethod
    def fake_validator(path):
        with open(path, "rb") as file:
            return file.read(2) == b"MZ"

    def release_data(self, corrupted_hash=False):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zipout:
            zipout.writestr("deno.exe", self.windows_exe())
        data = buf.getvalue()
        asset_url = ("https://github.com/denoland/deno/releases/download/"
                     "v2.9.8/deno-x86_64-pc-windows-msvc.zip")
        digest = hashlib.sha256(data).hexdigest()
        if corrupted_hash:
            digest = "0" * 64
        release = {"assets": [{
            "name": deno_runtime.ARCHIVE_NAME,
            "size": len(data),
            "digest": "sha256:" + digest,
            "browser_download_url": asset_url,
        }]}
        return asset_url, data, release

    def test_official_verified_deno_installed_once_in_local_bin(self):
        url, zipbytes, release = self.release_data()
        def opener(request, timeout=None):
            if request.full_url == deno_runtime.RELEASE_API:
                return io.BytesIO(json.dumps(release).encode())
            self.assertEqual(request.full_url, url)
            return io.BytesIO(zipbytes)
        with patch.object(deno_runtime.urllib.request, "urlopen", side_effect=opener) as net, \
             patch.object(deno_runtime, "_deno_version", return_value=(2, 9, 8)) as version:
            ok, reason = deno_runtime.ensure_deno_ready(
                self.root.name, self.fake_validator
            )
            self.assertTrue(ok, reason)
            self.assertEqual(net.call_count, 2)
            target = os.path.join(self.root.name, deno_runtime.EXE_NAME)
            self.assertEqual(open(target, "rb").read(), self.windows_exe())
            self.assertTrue(deno_runtime.yt_dlp_args(
                self.root.name, self.fake_validator
            ) == ["--js-runtimes", "deno:" + target])
            self.assertEqual(net.call_count, 2)
            version.assert_called_once()
            self.assertFalse(os.path.exists(target + ".zip.part"))
            self.assertFalse(os.path.exists(target + ".tmp.exe"))

    def test_integrity_mismatch_removes_temporary_files(self):
        _, zipbytes, release = self.release_data(corrupted_hash=True)
        def opener(request, timeout=None):
            if request.full_url == deno_runtime.RELEASE_API:
                return io.BytesIO(json.dumps(release).encode())
            return io.BytesIO(zipbytes)
        with patch.object(deno_runtime.urllib.request, "urlopen", side_effect=opener), \
             patch.object(deno_runtime, "_deno_version", return_value=(2, 9, 8)):
            ok, reason = deno_runtime.ensure_deno_ready(self.root.name, self.fake_validator)
        self.assertFalse(ok)
        self.assertIn("SHA-256", reason)
        self.assertEqual(os.listdir(self.root.name), [])

    def test_bogus_release_or_old_deno_is_rejected(self):
        with patch.object(deno_runtime.urllib.request, "urlopen",
                          return_value=io.BytesIO(b'{"assets":[]}')):
            ok, reason = deno_runtime.ensure_deno_ready(self.root.name, self.fake_validator)
        self.assertFalse(ok)
        self.assertIn("introuvable", reason)

        target = os.path.join(self.root.name, deno_runtime.EXE_NAME)
        with open(target, "wb") as f:
            f.write(self.windows_exe())
        with patch.object(deno_runtime, "_deno_version", return_value=(2, 2, 9)), \
             patch.object(deno_runtime, "_release_asset",
                          side_effect=OSError("offline")):
            ok, reason = deno_runtime.ensure_deno_ready(self.root.name, self.fake_validator)
        self.assertFalse(ok)
        self.assertEqual(open(target, "rb").read(), self.windows_exe())

    def test_web_error_is_nonfatal_and_no_partial_files(self):
        with patch.object(deno_runtime.urllib.request, "urlopen",
                          side_effect=OSError("network offline")):
            ok, reason = deno_runtime.ensure_deno_ready(
                self.root.name, self.fake_validator
            )
        self.assertFalse(ok)
        self.assertIn("network offline", reason)
        self.assertEqual(os.listdir(self.root.name), [])

    def test_only_real_youtube_domains_trigger_deno(self):
        valid = ("https://www.youtube.com/watch?v=123",
                 "https://music.youtube.com/watch?v=123",
                 "https://youtu.be/abc", "https://youtube.com/playlist?list=abc")
        for url in valid:
            self.assertTrue(deno_runtime.is_youtube_url(url), url)
        for url in ("https://twitch.tv/videos/2919531847",
                    "https://youtube.com.evil.test/watch?v=x",
                    "https://site.test/?q=youtube.com",
                    "file:///youtube.com/video",
                    "https://evil.test/@youtube.com",
                    "https://pinterest.com/pin/12"):
            self.assertFalse(deno_runtime.is_youtube_url(url), url)

    def test_deno_cache_is_forced_into_application_data_not_appdata(self):
        from types import SimpleNamespace
        import yt_app
        self.assertEqual(yt_app.local_ytdlp_environment()["DENO_DIR"],
                         os.path.join(yt_app.APP_DIR, "cache", "deno"))
        self.assertEqual(yt_app.local_ytdlp_environment()["DENO_NO_UPDATE_CHECK"], "1")
        path = os.path.join(self.root.name, "Donnees", "bin", "deno.exe.tmp.exe")
        with patch.object(deno_runtime.subprocess, "run",
                          return_value=SimpleNamespace(
                              returncode=0, stdout="deno 2.9.8\nv8 13.0\n")
                          ) as process:
            self.assertEqual(deno_runtime._deno_version(path), (2, 9, 8))
        self.assertEqual(
            process.call_args.kwargs["env"]["DENO_DIR"],
            os.path.join(self.root.name, "Donnees", "cache", "deno")
        )
        self.assertEqual(process.call_args.kwargs["env"]["DENO_NO_UPDATE_CHECK"], "1")

    def test_youtube_can_fall_back_without_deno(self):
        import yt_app
        with patch.object(yt_app, "is_valid_windows_executable",
                          return_value=True), \
             patch.object(yt_app, "ensure_deno_ready",
                          return_value=(False, "offline")):
            self.assertEqual(yt_app.youtube_js_args(
                "https://music.youtube.com/watch?v=abc"), [])
        with patch.object(yt_app, "ensure_deno_ready",
                          side_effect=AssertionError("Twitch called Deno")):
            self.assertEqual(yt_app.youtube_js_args(
                "https://www.twitch.tv/videos/2919531847"), [])

    def test_js_runtime_argument_applies_only_to_youtube(self):
        import yt_app
        with patch.object(yt_app, "is_valid_windows_executable",
                          return_value=True), \
             patch.object(yt_app, "ensure_deno_ready",
                          return_value=(True, "")) as provision:
            args = yt_app.youtube_js_args("https://youtu.be/123")
            self.assertEqual(args, ["--js-runtimes", "deno:" + yt_app.DENO_PATH])
            self.assertTrue(yt_app.DENO_PATH.startswith(yt_app.BIN_DIR))
            self.assertEqual(yt_app.youtube_js_args(
                "https://twitch.tv/videos/2919531847"), [])
            provision.assert_called_once()


if __name__ == "__main__":
    unittest.main()
