"""Audit des interactions réelles entre les appels UI et le moteur Python.

Ces tests ne téléchargent rien. Ils vérifient le rejet des soumissions parallèles,
la fermeture des indicateurs d'attente en cas d'erreur et la récupération du
moteur après un échec.
"""
import io
import json
import os
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import yt_app


class WindowRecorder:
    def __init__(self):
        self.scripts = []

    def evaluate_js(self, script):
        self.scripts.append(script)


class DownloadInteractionAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        self.api._window = WindowRecorder()
        self.api.config = {"settings": {"notify": "never"}}
        self.api.download_folder = self.tmp.name
        self.api._active_download_process = None
        self.api._suspended_download_pids = []
        self.api.is_cancelled = False
        self.api.is_paused = False
        self.item = {
            "url": "https://www.youtube.com/watch?v=test123",
            "title": "Un titre de test", "mode": "Vidéo",
            "selectedQuality": "1080p",
        }

    def wait_stopped(self):
        for _ in range(100):
            if not getattr(self.api, "_download_running", False):
                return
            time.sleep(0.05)
        self.fail("Le moteur est resté bloqué sur une tâche terminée")

    def test_invalid_or_empty_queue_does_not_start_a_thread(self):
        for value in ([], None, "invalid", [{}], [{"url": 123}],
                      [{"url": "  "}]):
            response = self.api.start_downloads(value)
            self.assertFalse(response["success"], value)
            self.assertFalse(getattr(self.api, "_download_running", False))

    def test_concurrent_jobs_rejected_and_job_finishes_cleanly(self):
        entered = threading.Event()
        unblock = threading.Event()

        def offline_ytdlp():
            entered.set()
            unblock.wait(4)
            return False

        with patch.object(yt_app, "ensure_ytdlp_ready", side_effect=offline_ytdlp):
            first = self.api.start_downloads([self.item])
            self.assertTrue(first["success"], first)
            try:
                self.assertTrue(entered.wait(3), "La tâche initiale n'a pas démarré")
                second = self.api.start_downloads([self.item])
                self.assertFalse(second["success"])
                self.assertIn("déjà en cours", second["error"])
            finally:
                unblock.set()
            self.wait_stopped()

        scripts = self.api._window.scripts
        self.assertTrue(any("yt-dlp est absent" in x for x in scripts))
        self.assertTrue(any("finishDownloadUIState()" in x for x in scripts))
        self.assertIsNone(self.api._active_download_process)
        self.assertFalse(self.api.is_paused)

        # Une erreur précédente ne bloque pas les requêtes suivantes.
        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=False):
            third = self.api.start_downloads([self.item])
            self.assertTrue(third["success"])
            self.wait_stopped()

    def test_unexpected_exception_unlocks_and_reports_error(self):
        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=True), \
             patch.object(yt_app, "get_media_download_dir",
                          side_effect=OSError("destination suddenly inaccessible")):
            result = self.api.start_downloads([self.item])
            self.assertTrue(result["success"])
            self.wait_stopped()
        self.assertTrue(any("inattendu" in x for x in self.api._window.scripts))
        self.assertTrue(any("finishDownloadUIState()" in x for x in self.api._window.scripts))
        self.assertIsNone(self.api._active_download_process)

    def test_cancelling_while_no_process_does_not_delete_user_files(self):
        old_path = os.path.join(self.tmp.name, "TWITCH", "already_downloaded.mp4")
        os.makedirs(os.path.dirname(old_path), exist_ok=True)
        with open(old_path, "wb") as file:
            file.write(b"private media")
        self.assertTrue(self.api.cancel_downloads())
        with open(old_path, "rb") as file:
            self.assertEqual(file.read(), b"private media")

    def test_failed_config_replacement_preserves_previous_settings(self):
        path = os.path.join(self.tmp.name, "config.json")
        original = {"settings": {"theme": "dark_pure"}, "cookie_browser": "none"}
        with open(path, "w", encoding="utf-8") as file:
            json.dump(original, file)
        self.api.config = dict(original)
        with patch.object(yt_app, "CONFIG_FILE", path), \
             patch.object(yt_app.os, "replace", side_effect=OSError("disk busy")):
            self.assertFalse(self.api.save_auth_config("", "firefox"))
        with open(path, encoding="utf-8") as file:
            self.assertEqual(json.load(file), original)
        self.assertEqual(self.api.config, original)
        self.assertFalse(any(name.endswith(".tmp") for name in os.listdir(self.tmp.name)))
        with patch.object(yt_app, "CONFIG_FILE", path):
            self.assertTrue(self.api.save_auth_config("", "firefox"))
        with open(path, encoding="utf-8") as file:
            self.assertEqual(json.load(file)["cookie_browser"], "firefox")

    def test_direct_pinterest_download_never_overwrites_existing_file(self):
        root = os.path.join(self.tmp.name, "GIFS")
        os.makedirs(root)
        existing = os.path.join(root, "Mon GIF.gif")
        with open(existing, "wb") as media:
            media.write(b"GIF89a-personal-original")
        with patch.object(yt_app.urllib.request, "urlopen",
                          return_value=io.BytesIO(b"GIF89a-new-media")):
            output = yt_app.save_direct_media(
                "https://i.pinimg.com/abc.gif?format=gif", root, "Mon GIF"
            )
        self.assertEqual(os.path.basename(output), "Mon GIF (2).gif")
        with open(existing, "rb") as media:
            self.assertEqual(media.read(), b"GIF89a-personal-original")
        with open(output, "rb") as media:
            self.assertEqual(media.read(), b"GIF89a-new-media")
        self.assertFalse(any(name.endswith(".part") for name in os.listdir(root)))

    def test_failed_or_cancelled_direct_transfer_cleans_partial_file(self):
        class FailingResponse:
            def __enter__(self):
                self.reads = 0
                return self
            def __exit__(self, *_):
                return False
            def read(self, size):
                self.reads += 1
                if self.reads == 1:
                    return b"GIF89a"
                raise OSError("network interruption")
        root = os.path.join(self.tmp.name, "GIFS")
        os.makedirs(root)
        with patch.object(yt_app.urllib.request, "urlopen", return_value=FailingResponse()):
            with self.assertRaises(OSError):
                yt_app.save_direct_media("https://i.pinimg.com/abc.gif", root, "Failed")
        self.assertEqual(os.listdir(root), [])
        with patch.object(yt_app.urllib.request, "urlopen", return_value=io.BytesIO(b"GIF89a")):
            with self.assertRaises(InterruptedError):
                yt_app.save_direct_media(
                    "https://i.pinimg.com/abc.gif", root, "Cancelled",
                    on_chunk=lambda: (_ for _ in ()).throw(InterruptedError())
                )
        self.assertEqual(os.listdir(root), [])

    def test_direct_download_rejects_non_http_url_without_touching_files(self):
        with self.assertRaises(ValueError):
            yt_app.save_direct_media("file:///C:/secret.gif", self.tmp.name, "test")
        self.assertFalse(os.listdir(self.tmp.name))


if __name__ == "__main__":
    unittest.main()
