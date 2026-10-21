"""La vraie edition Portable garde son etat dans le dossier de l'EXE."""
import json
import os
import faulthandler
import runpy
import tempfile
import unittest
from unittest.mock import patch

import yt_app


class PortableStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = self.temp.name
        self.legacy = os.path.join(self.home, "AppData", "Local")
        self.portable = os.path.join(self.home, "All-Download-Portable")
        os.makedirs(self.legacy)
        os.makedirs(self.portable)
        self.exe = os.path.join(self.portable, "All_Media_Download.exe")

    def load_mode(self, installed=False):
        marker = os.path.join(self.portable, ".all-download-installed")
        if installed:
            with open(marker, "w") as dest:
                dest.write("classique")
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "executable", self.exe
        ), patch.dict(os.environ, {"LOCALAPPDATA": self.legacy}):
            app = runpy.run_path(yt_app.__file__, run_name="all_download_storage_test")
        # runpy execute le bloc de diagnostic a nouveau dans CE processus.
        # Sous Windows, fermer le descripteur ouvre par faulthandler, sinon
        # TemporaryDirectory ne peut plus supprimer crash_log.txt.
        faulthandler.disable()
        crash_stream = app.get("_CRASH_STREAM")
        if crash_stream is not None:
            crash_stream.close()
        return app

    def selected_folder(self, app):
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "executable", self.exe
        ):
            return app["choose_initial_download_folder"]({})

    def test_clean_portable_uses_only_adjacent_data_and_media(self):
        app = self.load_mode()
        self.assertTrue(app["PORTABLE_DATA_LOCAL"])
        data = os.path.join(self.portable, "Donnees")
        self.assertEqual(app["APP_DIR"], data)
        for key, name in (
            ("CONFIG_FILE", "config.json"),
            ("CRASH_LOG", "crash_log.txt"),
            ("STARTUP_LOG", "startup_log.txt"),
        ):
            self.assertEqual(app[key], os.path.join(data, name))
        self.assertEqual(app["BIN_DIR"], os.path.join(data, "bin"))
        self.assertEqual(self.selected_folder(app), self.portable)
        app["ensure_media_directories"](self.portable)
        for category in app["DOWNLOAD_CATEGORIES"]:
            self.assertTrue(os.path.isdir(os.path.join(self.portable, category)))
        self.assertFalse(os.path.exists(os.path.join(self.home, "All-Download-Medias")))
        self.assertFalse(os.path.exists(os.path.join(self.legacy, "AllMediaDownload")))

    def test_legacy_preferences_migrate_without_moving_existing_media(self):
        previous = os.path.join(self.legacy, "AllMediaDownload")
        os.makedirs(previous)
        old_media = os.path.join(self.home, "Downloads", "All-Download-Medias")
        os.makedirs(os.path.join(old_media, "VIDÉOS"))
        old_video = os.path.join(old_media, "VIDÉOS", "ancienne.mp4")
        with open(old_video, "wb") as output:
            output.write(b"ne jamais supprimer")
        previous_config = {
            "settings": {"theme": "dark_pure", "video_format": "MKV"},
            "cookie_browser": "firefox",
            "download_folder_custom": False,
            "download_folder": old_media,
        }
        with open(os.path.join(previous, "config.json"), "w", encoding="utf-8") as output:
            json.dump(previous_config, output)
        app = self.load_mode()
        # L'API fonctionne avec les chemins du module recharge.
        with patch.object(yt_app, "CONFIG_FILE", app["CONFIG_FILE"]), patch.object(
            yt_app, "DEFAULT_DOWNLOAD_BASE", old_media
        ), patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "executable", self.exe
        ):
            api = yt_app.DownloaderAPI()
        self.assertEqual(api.download_folder, self.portable)
        self.assertEqual(api.config["settings"]["theme"], "dark_pure")
        self.assertEqual(api.config["cookie_browser"], "firefox")
        with open(old_video, "rb") as source:
            self.assertEqual(source.read(), b"ne jamais supprimer")
        with open(os.path.join(previous, "config.json"), encoding="utf-8") as source:
            self.assertEqual(json.load(source), previous_config)

    def test_old_ffmpeg_is_copied_only_once_without_overwriting(self):
        previous_bin = os.path.join(self.legacy, "AllMediaDownload", "bin")
        os.makedirs(previous_bin)
        with open(os.path.join(previous_bin, "ffmpeg.exe"), "wb") as output:
            output.write(b"ancien outil")
        app = self.load_mode()
        app["import_legacy_portable_tools"]()
        new_ffmpeg = os.path.join(app["BIN_DIR"], "ffmpeg.exe")
        with open(new_ffmpeg, "rb") as source:
            self.assertEqual(source.read(), b"ancien outil")
        with open(new_ffmpeg, "wb") as output:
            output.write(b"nouvel outil")
        app["import_legacy_portable_tools"]()
        with open(new_ffmpeg, "rb") as source:
            self.assertEqual(source.read(), b"nouvel outil")

    def test_classic_installer_keeps_media_and_preferences_beside_exe(self):
        app = self.load_mode(installed=True)
        data = os.path.join(self.portable, "Donnees")
        self.assertFalse(app["PORTABLE_DATA_LOCAL"])
        self.assertTrue(app["APP_DATA_LOCAL"])
        self.assertEqual(app["APP_DIR"], data)
        self.assertEqual(app["CONFIG_FILE"], os.path.join(data, "config.json"))
        self.assertEqual(app["BIN_DIR"], os.path.join(data, "bin"))
        self.assertEqual(app["CRASH_LOG"], os.path.join(data, "crash_log.txt"))
        self.assertEqual(self.selected_folder(app), self.portable)
        app["ensure_media_directories"](self.portable)
        self.assertTrue(all(
            os.path.isdir(os.path.join(self.portable, category))
            for category in app["DOWNLOAD_CATEGORIES"]
        ))

    def test_classic_upgrades_existing_settings_without_moving_medias(self):
        previous = os.path.join(self.legacy, "AllMediaDownload")
        os.makedirs(previous)
        legacy_config = os.path.join(previous, "config.json")
        old_root = os.path.join(self.home, "Downloads", "All-Download-Medias")
        os.makedirs(os.path.join(old_root, "AUDIOS"))
        old_audio = os.path.join(old_root, "AUDIOS", "old.mp3")
        with open(old_audio, "wb") as file:
            file.write(b"original")
        with open(legacy_config, "w", encoding="utf-8") as file:
            json.dump({
                "settings": {"theme": "dark_pure"},
                "download_folder": old_root,
                "download_folder_custom": False
            }, file)
        app = self.load_mode(installed=True)
        local_config = app["CONFIG_FILE"]
        self.assertTrue(os.path.isfile(local_config))
        with patch.object(yt_app, "CONFIG_FILE", local_config), patch.object(
            yt_app, "DEFAULT_DOWNLOAD_BASE", old_root
        ), patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "executable", self.exe
        ):
            api = yt_app.DownloaderAPI()
        self.assertEqual(api.download_folder, self.portable)
        self.assertEqual(api.config["settings"]["theme"], "dark_pure")
        with open(old_audio, "rb") as file:
            self.assertEqual(file.read(), b"original")
        with open(legacy_config, encoding="utf-8") as file:
            self.assertEqual(json.load(file)["download_folder"], old_root)

    def test_classic_custom_destination_survives_upgrade(self):
        previous = os.path.join(self.legacy, "AllMediaDownload")
        os.makedirs(previous)
        custom = os.path.join(self.home, "Mes-Medias")
        os.makedirs(custom)
        with open(os.path.join(previous, "config.json"), "w", encoding="utf-8") as file:
            json.dump({"download_folder": custom, "download_folder_custom": True}, file)
        app = self.load_mode(installed=True)
        with patch.object(yt_app, "CONFIG_FILE", app["CONFIG_FILE"]), patch.object(
            yt_app.sys, "frozen", True, create=True
        ), patch.object(yt_app.sys, "executable", self.exe):
            api = yt_app.DownloaderAPI()
        self.assertEqual(api.download_folder, custom)
        self.assertTrue(api.config["download_folder_custom"])


if __name__ == "__main__":
    unittest.main()
