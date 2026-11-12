"""Offline security and interaction tests for Linux-only settings and launchers."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import URLError

from linux.app import DownloaderAPI
from linux.desktop import (
    DESKTOP_FILE,
    OWNERSHIP_MARKER,
    desktop_applications_dir,
    desktop_quote,
    install_linux_launcher,
    remove_linux_launcher,
)
from linux.extract_ui import extract
from linux.ui_extras import inject_linux_controls
from linux.update_check import CURRENT_LINUX_VERSION, check_linux_updates, parse_linux_version


def linux_release(tag, complete=True, compact=False, **overrides):
    assets = [
        {"name": "All-Download-Linux-x86_64.tar.gz"},
        {"name": "All-Download-Linux-x86_64.tar.gz.sha256"},
    ] if complete else [{"name": "All-Download-Linux-x86_64.tar.gz"}]
    if compact:
        assets.extend([
            {"name": "All-Download-Linux-x86_64.tar.xz"},
            {"name": "All-Download-Linux-x86_64.tar.xz.sha256"},
        ])
    return {"tag_name": tag, "assets": assets, "draft": False, **overrides}


def fake_api_response(releases):
    return io.BytesIO(json.dumps(releases).encode("utf-8"))


class LinuxDesktopUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="all-download-linux-update-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "All-Download"
        self.root.mkdir()
        self.xdg = Path(self.tmp.name) / "xdg"
        self.patched_xdg = mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(self.xdg)})
        self.patched_xdg.start()
        self.addCleanup(self.patched_xdg.stop)

    def test_release_check_ignores_unrelated_and_unverified_assets(self):
        payload = [
            linux_release("android-v999.0.0-beta"),
            linux_release("linux-v9.9.9-beta", complete=False),
            linux_release("linux-v0.1.8-beta", draft=True),
            linux_release("linux-v0.1.7-beta", compact=True),
            linux_release("linux-v0.1.2-beta"),
            linux_release("linux-v0.1.1-beta"),
        ]
        with mock.patch("linux.update_check.urlopen", return_value=fake_api_response(payload)) as mocked:
            result = check_linux_updates()
        self.assertTrue(result["success"], result)
        self.assertTrue(result["available"])
        self.assertEqual("0.1.7-beta", result["latest"])
        self.assertEqual("All-Download-Linux-x86_64.tar.xz", result["preferred_asset"])
        self.assertEqual("All-Download-Linux-x86_64.tar.xz.sha256", result["checksum_asset"])
        self.assertEqual(CURRENT_LINUX_VERSION, result["current"])
        self.assertEqual(
            "https://github.com/anderson76389/All-Download/releases/tag/linux-v0.1.7-beta",
            result["url"],
        )
        self.assertEqual(8, mocked.call_args.kwargs["timeout"])

    def test_release_check_does_not_trust_remote_redirect_urls(self):
        record = linux_release("linux-v0.1.5-beta", html_url="https://evil.example/download")
        record["assets"][0]["browser_download_url"] = "https://evil.example/binary"
        with mock.patch("linux.update_check.urlopen", return_value=fake_api_response([record])):
            result = check_linux_updates()
        self.assertTrue(result["url"].startswith(
            "https://github.com/anderson76389/All-Download/releases/tag/"))

    def test_compact_archive_without_checksum_is_never_preferred(self):
        broken = linux_release("linux-v0.1.5-beta")
        broken["assets"].append({"name": "All-Download-Linux-x86_64.tar.xz"})
        with mock.patch("linux.update_check.urlopen", return_value=fake_api_response([broken])):
            result = check_linux_updates()
        self.assertTrue(result["success"], result)
        self.assertEqual("All-Download-Linux-x86_64.tar.gz", result["preferred_asset"])

    def test_up_to_date_or_network_failure(self):
        with mock.patch("linux.update_check.urlopen", return_value=fake_api_response(
                [linux_release("linux-v0.1.4-beta")])):
            result = check_linux_updates()
        self.assertTrue(result["success"])
        self.assertFalse(result["available"])
        self.assertEqual("All-Download-Linux-x86_64.tar.gz", result["preferred_asset"])
        with mock.patch("linux.update_check.urlopen", side_effect=URLError("hors ligne")):
            result = check_linux_updates()
        self.assertFalse(result["success"])
        self.assertIn("indisponible", result["error"])

    def test_version_parser_rejects_other_products_and_nonstandard_tags(self):
        self.assertEqual((0, 1, 3), parse_linux_version("linux-v0.1.3-beta"))
        for value in ("android-v0.1.2-beta", "linux-v0.1.2-beta-evil",
                      "linux-v0.1.2", "../linux-v0.1.2-beta", "", None):
            self.assertIsNone(parse_linux_version(value))

    def test_html_linux_controls_only_add_to_settings(self):
        windows_html = extract(Path(__file__).resolve().parents[2] / "yt_app.py")
        html = inject_linux_controls(windows_html)
        self.assertIn("linuxExtraSettings", html)
        self.assertIn("linuxCheckUpdates", html)
        self.assertIn("linuxInstallShortcut", html)
        self.assertIn("linuxRemoveShortcut", html)
        self.assertEqual(1, html.count("section.id = 'linuxExtraSettings';"))
        self.assertIn('id="setSectionAppli"', windows_html)
        self.assertNotIn("linuxExtraSettings", windows_html)
        self.assertEqual(html, inject_linux_controls(html))
        api = DownloaderAPI(self.root)
        for method in ("check_linux_updates", "install_linux_launcher",
                       "remove_linux_launcher"):
            self.assertTrue(callable(getattr(api, method)))

    def test_desktop_launcher_install_remove_with_spaces_and_icon(self):
        executable = self.root / "All-Download-Linux"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
        (self.root / "logo.jpg").write_bytes(b"fake icon for desktop entry test")
        result = install_linux_launcher(self.root)
        self.assertTrue(result["success"], result)
        target = desktop_applications_dir() / DESKTOP_FILE
        data = target.read_text("utf-8")
        self.assertIn(OWNERSHIP_MARKER, data)
        self.assertIn('Exec="' + str(executable) + '"', data)
        self.assertIn('Icon=' + str(self.root / "logo.jpg"), data)
        self.assertTrue(remove_linux_launcher()["success"])
        self.assertFalse(target.exists())
        self.assertTrue(remove_linux_launcher()["success"])

    def test_desktop_entry_escapes_special_executable_path(self):
        quote = desktop_quote(Path('/home/me/A % " $ special'))
        self.assertIn("%%", quote)
        self.assertIn('\\"', quote)
        self.assertIn("\\$", quote)
        with self.assertRaises(ValueError):
            desktop_quote(Path("/home/me/bad\nname"))

    def test_never_overwrite_or_delete_external_shortcut(self):
        target = desktop_applications_dir() / DESKTOP_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        original = "[Desktop Entry]\nName=Another Application\n"
        target.write_text(original)
        executable = self.root / "All-Download-Linux"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
        self.assertFalse(install_linux_launcher(self.root)["success"])
        self.assertFalse(remove_linux_launcher()["success"])
        self.assertEqual(original, target.read_text())


if __name__ == "__main__":
    unittest.main()
