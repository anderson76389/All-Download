"""Contrôles sans réseau : vrais processus Windows et sauvegarde cookies vérifiée."""
import os
import sys
import tempfile
import time
import unittest
import subprocess
from unittest.mock import patch

import psutil
import yt_app


class RealPauseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        self.api.is_paused = False
        self.api.is_cancelled = False
        self.api._active_download_process = None
        self.api._suspended_download_pids = []
        self.log = os.path.join(self.tmp.name, "heartbeat.txt")

    def _wait_length(self, n=3, timeout=6):
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                if os.path.getsize(self.log) >= n:
                    return os.path.getsize(self.log)
            except FileNotFoundError:
                pass
            time.sleep(0.05)
        self.fail("Le processus du test n'a pas créé son fichier dans les délais")

    def test_pause_active_process_actually_stops_and_resumes_writes(self):
        code = (
            "import time,sys\n"
            "with open(sys.argv[1], 'a', encoding='ascii') as f:\n"
            " while True:\n"
            "  f.write('X'); f.flush(); time.sleep(0.05)\n"
        )
        proc = subprocess.Popen(
            [sys.executable, "-c", code, self.log],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.api._active_download_process = proc
        try:
            self._wait_length()
            paused = self.api.pause_downloads()
            self.assertEqual(paused, {"success": True, "mode": "active"})
            self.assertTrue(self.api.is_paused)
            self.assertIn(proc.pid, self.api._suspended_download_pids)
            old_size = os.path.getsize(self.log)
            time.sleep(0.5)
            self.assertEqual(os.path.getsize(self.log), old_size,
                             "Le processus a continué à écrire alors qu'il était suspendu")
            resumed = self.api.resume_downloads()
            self.assertTrue(resumed["success"], resumed)
            self.assertFalse(self.api.is_paused)
            self._wait_length(old_size + 3)
        finally:
            self.api._resume_active_processes()
            proc.kill()
            proc.wait(timeout=5)

    def test_pause_and_resume_queue_when_no_process_active(self):
        self.assertEqual(self.api.pause_downloads(), {"success": True, "mode": "queue"})
        self.assertTrue(self.api.is_paused)
        self.assertTrue(self.api.resume_downloads()["success"])
        self.assertFalse(self.api.is_paused)


class CookiePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        self.api.config = {"cookie_browser": "none", "cookie_file": ""}
        self.api.download_folder = self.tmp.name
        self.config_file = os.path.join(self.tmp.name, "config.json")

    def test_cookie_save_round_trip_uses_real_json_file(self):
        with patch.object(yt_app, "CONFIG_FILE", self.config_file):
            self.assertTrue(self.api.save_auth_config("", "firefox"))
            fresh = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
            fresh.config = fresh._load_config()
            self.assertEqual(fresh.config["cookie_browser"], "firefox")
            self.assertFalse(self.api.save_auth_config("", "not-a-browser"))
            self.assertEqual(self.api.config["cookie_browser"], "firefox")

    def test_failed_cookie_write_does_not_claim_success(self):
        with patch.object(self.api, "_save_config", return_value=False):
            self.assertFalse(self.api.save_auth_config("cookies.txt", "chrome"))
        self.assertEqual(self.api.config["cookie_browser"], "none")
        self.assertEqual(self.api.config["cookie_file"], "")


if __name__ == "__main__":
    unittest.main()
