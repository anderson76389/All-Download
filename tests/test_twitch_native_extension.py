"""Tests de l'installation locale et facultative de l'extension Twitch Chrome."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import twitch_native_extension as ext
import yt_app


class NativeExtensionTests(unittest.TestCase):
    def fake_chrome(self, root):
        folder = (Path(root) / "Google" / "Chrome" / "User Data" / "Default"
                  / "Extensions" / ext.CHROME_EXTENSION_ID / "3.26_0")
        folder.mkdir(parents=True)
        (folder / "manifest.json").write_text(json.dumps({
            "manifest_version": 3,
            "name": "Twitch VOD Downloader",
            "version": "3.26",
            "content_scripts": [{"matches": ["https://www.twitch.tv/*"],
                                 "js": ["content.js"]}],
        }))
        (folder / "content.js").write_text("console.log('extension de test')", encoding="utf-8")
        (folder / "_metadata").mkdir()
        (folder / "_metadata" / "verified_contents.json").write_text("{}")
        return folder

    def test_copy_local_extension_without_chrome_private_data(self):
        with tempfile.TemporaryDirectory() as root:
            origin = self.fake_chrome(root)
            data = Path(root) / "donnees"
            with patch.dict("os.environ", {"LOCALAPPDATA": root}):
                result = ext.install_local_chrome_extension(data)
                second = ext.install_local_chrome_extension(data)
            self.assertEqual(result["path"], second["path"])
            self.assertEqual(result["version"], "3.26")
            copied = Path(result["path"])
            self.assertTrue((copied / "manifest.json").exists())
            self.assertTrue((copied / "content.js").exists())
            self.assertFalse((copied / "_metadata").exists())
            self.assertTrue((origin / "_metadata").exists())
            self.assertEqual(ext.existing_native_extension(data)["version"], "3.26")

    def test_missing_extension_does_not_create_downloaded_code(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.dict("os.environ", {"LOCALAPPDATA": root}):
                with self.assertRaises(ext.NativeExtensionError):
                    ext.install_local_chrome_extension(Path(root) / "donnees")
            self.assertFalse((Path(root) / "donnees" / "Extensions").exists())

    def test_extension_integration_is_opt_in(self):
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api.config = {}
        with tempfile.TemporaryDirectory() as root:
            with patch.object(yt_app, "APP_DIR", root), patch.object(
                yt_app, "CONFIG_FILE", str(Path(root) / "config.json")
            ):
                result = api.open_twitch_native_extension(
                    "https://www.twitch.tv/videos/2905228526")
                self.assertFalse(result["success"])
                self.assertFalse(api.config.get("twitch_native_extension_enabled", False))
        self.assertFalse(api.open_twitch_native_extension(
            "https://example.com/videos/2905228526")["success"])


if __name__ == "__main__":
    unittest.main()
