"""Tests de rangement : chemins, migration non destructive et commandes yt-dlp simulées."""
import io
import os
import tempfile
import unittest
from unittest.mock import patch

import yt_app


class ImmediateThread:
    def __init__(self, target, daemon=True):
        self.target = target

    def start(self):
        self.target()


class FakeProcess:
    def __init__(self):
        self.stdout = io.StringIO("")
        self.pid = 99999
        self.returncode = 0

    def communicate(self):
        return ("", "")


class DownloadFolderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = self.temp.name

    def item(self, url, mode="Vidéo", **extra):
        return {"url": url, "mode": mode, "title": "MediaTest", **extra}

    def test_six_categories_created(self):
        yt_app.ensure_media_directories(self.root)
        self.assertTrue(all(
            os.path.isdir(os.path.join(self.root, category))
            for category in ("AUTRES", "VIDÉOS", "CHAÎNES", "AUDIOS", "PLAYLIST", "GIFS")
        ))


    def test_portable_exe_uses_six_folders_next_to_exe(self):
        yt_app.ensure_media_directories(self.root)
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "executable", os.path.join(self.root, "All_Media_Download.exe")
        ):
            self.assertEqual(yt_app.choose_initial_download_folder({}), self.root)

    def test_installed_version_saves_downloads_outside_application_folder(self):
        # Les six dossiers presents a cote de l'EXE installe ne doivent pas
        # recevoir les medias : le desinstalleur pourrait les supprimer.
        yt_app.ensure_media_directories(self.root)
        with open(os.path.join(self.root, ".all-download-installed"), "w", encoding="utf-8") as f:
            f.write("installed\n")
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "executable", os.path.join(self.root, "All_Media_Download.exe")
        ):
            self.assertEqual(
                yt_app.choose_initial_download_folder({}), yt_app.DEFAULT_DOWNLOAD_BASE
            )

    def test_custom_destination_is_preserved(self):
        yt_app.ensure_media_directories(self.root)
        other = os.path.join(self.root, "Personnalise")
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "executable", os.path.join(self.root, "All_Media_Download.exe")
        ):
            self.assertEqual(
                yt_app.choose_initial_download_folder({"download_folder": other}), other
            )

    def test_no_portable_folders_uses_clean_new_destination(self):
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "executable", os.path.join(self.root, "All_Media_Download.exe")
        ):
            self.assertEqual(
                yt_app.choose_initial_download_folder({}), yt_app.DEFAULT_DOWNLOAD_BASE
            )

    def test_legacy_saved_folder_is_not_reused(self):
        legacy_dir = os.path.join(self.root, "MediaDownloader")
        new_dir = os.path.join(self.root, "All-Download-Medias")
        os.makedirs(legacy_dir)
        # Le projet de test et les medias anciens ne doivent pas etre deplaces.
        with open(os.path.join(legacy_dir, "yt_app.py"), "w", encoding="utf-8") as file:
            file.write("ancien projet")
        yt_app.ensure_media_directories(legacy_dir)

        with patch.object(yt_app, "LEGACY_DOWNLOAD_BASE", legacy_dir), patch.object(
            yt_app, "DEFAULT_DOWNLOAD_BASE", new_dir
        ), patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "executable", os.path.join(legacy_dir, "All_Media_Download.exe")
        ):
            selected = yt_app.choose_initial_download_folder({"download_folder": legacy_dir})
            self.assertEqual(selected, new_dir)
            yt_app.ensure_media_directories(selected)
            self.assertTrue(os.path.isfile(os.path.join(legacy_dir, "yt_app.py")))
            self.assertTrue(os.path.isdir(os.path.join(legacy_dir, "VIDÉOS")))
            self.assertTrue(os.path.isdir(os.path.join(new_dir, "VIDÉOS")))

    def test_legacy_config_is_rewritten_without_losing_preferences(self):
        import json
        old_dir = os.path.join(self.root, "MediaDownloader")
        new_dir = os.path.join(self.root, "All-Download-Medias")
        config_file = os.path.join(self.root, "config.json")
        original = {
            "download_folder": old_dir,
            "settings": {"theme": "dark_pure", "video_format": "MKV"},
            "cookie_browser": "firefox"
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(original, f)

        with patch.object(yt_app, "CONFIG_FILE", config_file), patch.object(
            yt_app, "LEGACY_DOWNLOAD_BASE", old_dir
        ), patch.object(yt_app, "DEFAULT_DOWNLOAD_BASE", new_dir), patch.object(
            yt_app.sys, "frozen", True, create=True
        ), patch.object(
            yt_app.sys, "executable", os.path.join(self.root, "installed", "All_Media_Download.exe")
        ):
            api = yt_app.DownloaderAPI()
            self.assertEqual(api.download_folder, new_dir)
            with open(config_file, encoding="utf-8") as f:
                migrated = json.load(f)
            self.assertEqual(migrated["download_folder"], new_dir)
            self.assertEqual(migrated["settings"], original["settings"])
            self.assertEqual(migrated["cookie_browser"], "firefox")

    def test_current_custom_location_remains_unchanged(self):
        with patch.object(yt_app, "LEGACY_DOWNLOAD_BASE", os.path.join(self.root, "MediaDownloader")):
            custom = os.path.join(self.root, "My-Other-Downloads")
            self.assertEqual(
                yt_app.choose_initial_download_folder({"download_folder": custom}), custom
            )

    def test_legacy_audio_migrates_without_losing_files(self):
        old_dir = os.path.join(self.root, "AUDIO")
        os.makedirs(os.path.join(old_dir, "album"))
        with open(os.path.join(old_dir, "album", "song.mp3"), "wb") as f:
            f.write(b"existing audio")
        yt_app.ensure_media_directories(self.root)
        new_file = os.path.join(self.root, "AUDIOS", "album", "song.mp3")
        with open(new_file, "rb") as f:
            self.assertEqual(f.read(), b"existing audio")
        self.assertFalse(os.path.exists(old_dir))

    def test_legacy_audio_merge_never_overwrites_duplicates(self):
        old_dir = os.path.join(self.root, "AUDIO")
        new_dir = os.path.join(self.root, "AUDIOS")
        os.makedirs(old_dir)
        os.makedirs(new_dir)
        for directory, filename, data in [
            (old_dir, "same.mp3", b"old original"),
            (old_dir, "extra.mp3", b"another song"),
            (new_dir, "same.mp3", b"new original"),
        ]:
            with open(os.path.join(directory, filename), "wb") as f:
                f.write(data)
        yt_app.ensure_media_directories(self.root)
        with open(os.path.join(new_dir, "same.mp3"), "rb") as f:
            self.assertEqual(f.read(), b"new original")
        with open(os.path.join(old_dir, "same.mp3"), "rb") as f:
            self.assertEqual(f.read(), b"old original")
        with open(os.path.join(new_dir, "extra.mp3"), "rb") as f:
            self.assertEqual(f.read(), b"another song")

    def test_all_routing_priorities(self):
        video = "https://www.youtube.com/watch?v=abcdef"
        others = "https://example.com/media"
        cases = [
            (self.item(video), os.path.join("VIDÉOS")),
            (self.item(others), os.path.join("AUTRES")),
            (self.item(video, "Audio"), os.path.join("AUDIOS")),
            (self.item(others, "Audio"), os.path.join("AUDIOS")),
            (self.item(video, "GIF"), os.path.join("GIFS")),
            (self.item(others, "GIF"), os.path.join("GIFS")),
            (self.item("https://v.pinimg.com/pin.gif?size=large", "Image", is_direct_download=True), "GIFS"),
            (self.item("https://v.pinimg.com/pin.png", "Image", is_direct_download=True), "AUTRES"),
            (self.item("https://www.youtube.com/playlist?list=abc", is_playlist=True, playlist_title="Ma liste"), os.path.join("PLAYLIST", "Ma liste")),
            (self.item("https://www.youtube.com/@mychannel", is_channel=True, channel_title="Ma chaîne"), os.path.join("CHAÎNES", "Ma chaîne")),
            (self.item("https://www.youtube.com/playlist?list=abc", mode="Audio", is_playlist=True, playlist_title="Album"), os.path.join("PLAYLIST", "Album")),
            (self.item("https://www.youtube.com/playlist?list=abc", mode="GIF", is_playlist=True, playlist_title="Album"), "GIFS"),
        ]
        for item, destination in cases:
            with self.subTest(item=item):
                self.assertEqual(
                    yt_app.get_media_download_dir(self.root, item),
                    os.path.join(self.root, destination)
                )

    def create_api(self):
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api.download_folder = self.root
        api.config = {"settings": {"sponsor_enable": False}}
        api.is_paused = False
        api.is_cancelled = False
        api.window = None
        return api

    def test_download_commands_use_right_directories(self):
        api = self.create_api()
        items = [
            (self.item("https://youtube.com/watch?v=1"), "VIDÉOS"),
            (self.item("https://youtube.com/watch?v=2", "Audio"), "AUDIOS"),
            (self.item("https://example.com/sound", "Audio"), "AUDIOS"),
            (self.item("https://youtube.com/watch?v=3", "GIF"), "GIFS"),
            (self.item("https://example.com/movie", "GIF"), "GIFS"),
            (self.item("https://example.com/video"), "AUTRES"),
            (self.item("https://youtube.com/playlist?list=abc", is_playlist=True, playlist_title="Liste"), os.path.join("PLAYLIST", "Liste")),
            (self.item("https://youtube.com/@canal", is_channel=True, channel_title="Canal"), os.path.join("CHAÎNES", "Canal")),
        ]
        commands = []

        def fake_popen(cmd, **_kwargs):
            commands.append(cmd)
            return FakeProcess()

        with patch.object(yt_app.threading, "Thread", ImmediateThread), patch.object(yt_app.subprocess, "Popen", fake_popen):
            api.start_downloads([item for item, _ in items])

        self.assertEqual(len(commands), len(items))
        for cmd, (_item, expected) in zip(commands, items):
            with self.subTest(destination=expected):
                self.assertEqual(cmd[cmd.index("-P") + 1], os.path.join(self.root, expected))
                self.assertTrue(os.path.isdir(os.path.join(self.root, expected)))

    def test_cancel_stops_current_process(self):
        api = self.create_api()
        api._active_download_process = FakeProcess()
        with patch.object(yt_app, "kill_process_tree") as stop:
            self.assertTrue(api.cancel_downloads())
        self.assertTrue(api.is_cancelled)
        stop.assert_called_once_with(99999)

    def test_success_is_reported_only_for_succeeded_downloads(self):
        api = self.create_api()

        class Recorder:
            def __init__(self):
                self.scripts = []

            def evaluate_js(self, script):
                self.scripts.append(script)

        api.window = Recorder()
        with patch.object(yt_app.threading, "Thread", ImmediateThread), patch.object(
            yt_app.subprocess, "Popen", return_value=FakeProcess()
        ):
            api.start_downloads([self.item("https://youtube.com/watch?v=42")])
        self.assertTrue(any("markDownloadSuccess(" in x for x in api.window.scripts))

        api.window.scripts.clear()
        failed = FakeProcess()
        failed.returncode = 1
        with patch.object(yt_app.threading, "Thread", ImmediateThread), patch.object(
            yt_app.subprocess, "Popen", return_value=failed
        ):
            api.start_downloads([self.item("https://youtube.com/watch?v=43")])
        self.assertFalse(any("markDownloadSuccess(" in x for x in api.window.scripts))
        self.assertTrue(any("0/1" in x for x in api.window.scripts))

    def test_direct_pinterest_gif_saved_in_gifs(self):
        api = self.create_api()
        gif = self.item(
            "https://v.pinimg.com/asset.gif?quality=original",
            "Image", title="Mon GIF", is_direct_download=True
        )
        with patch.object(yt_app.threading, "Thread", ImmediateThread), patch.object(
            yt_app.urllib.request, "urlopen", return_value=io.BytesIO(b"GIF89aFAKE")
        ), patch.object(yt_app.subprocess, "Popen", side_effect=AssertionError("GIF direct: yt-dlp inutile")):
            api.start_downloads([gif])
        target = os.path.join(self.root, "GIFS", "Mon GIF.gif")
        with open(target, "rb") as f:
            self.assertEqual(f.read(), b"GIF89aFAKE")


if __name__ == "__main__":
    unittest.main()
