"""Audit des interactions réelles entre les appels UI et le moteur Python.

Ces tests ne téléchargent rien. Ils vérifient le rejet des soumissions parallèles,
la fermeture des indicateurs d'attente en cas d'erreur et la récupération du
moteur après un échec.
"""
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


if __name__ == "__main__":
    unittest.main()
