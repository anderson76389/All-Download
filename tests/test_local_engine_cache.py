"""Séparer caches de yt-dlp et Deno dans Donnees sans modifier l'OS."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yt_app


class ImmediateThread:
    def __init__(self, target, **_kwargs):
        self.target = target

    def start(self):
        self.target()


class FakeProcess:
    def __init__(self, data="", returncode=0):
        self.pid = 4321
        self.stdout = io.StringIO(data)
        self.returncode = returncode

    def communicate(self, timeout=None):
        return (self.stdout.getvalue(), "")


class Recorder:
    def __init__(self):
        self.scripts = []

    def evaluate_js(self, script):
        self.scripts.append(script)


class LocalCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name) / "Donnees"
        self.ytdlp_cache = root / "cache" / "yt-dlp"
        self.deno_cache = root / "cache" / "deno"
        self.cache = root / "cache"
        for name, path in (
            ("CACHE_DIR", self.cache),
            ("YTDLP_CACHE_DIR", self.ytdlp_cache),
            ("DENO_CACHE_DIR", self.deno_cache),
        ):
            patcher = patch.object(yt_app, name, str(path))
            patcher.start()
            self.addCleanup(patcher.stop)
        self.api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        self.api.config = {
            "settings": {
                "video_embed_thumb": False, "video_write_thumb": False,
                "video_add_metadata": False, "sponsor_enable": False,
            }
        }
        self.api.download_folder = self.temp.name
        self.api.is_cancelled = False
        self.api.is_paused = False
        self.api._active_download_process = None
        self.api._window = Recorder()

    def test_cache_paths_are_private_to_child_processes(self):
        old_deno = os.environ.get("DENO_DIR")
        old_xdg = os.environ.get("XDG_CACHE_HOME")
        env = yt_app.get_media_runtime_env()
        self.assertEqual(env["DENO_DIR"], str(self.deno_cache))
        self.assertEqual(env["XDG_CACHE_HOME"], str(self.cache))
        self.assertTrue(self.deno_cache.is_dir())
        self.assertTrue(self.ytdlp_cache.is_dir())
        self.assertEqual(os.environ.get("DENO_DIR"), old_deno)
        self.assertEqual(os.environ.get("XDG_CACHE_HOME"), old_xdg)

    def test_metadata_analysis_uses_local_cache_and_no_global_config(self):
        commands = []
        environments = []
        def popen(command, **kwargs):
            commands.append(command)
            environments.append(kwargs["env"])
            p = FakeProcess()
            p.communicate = lambda timeout=None: (
                json.dumps({"title": "test", "formats": [{"height": 720}]}), "")
            return p
        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=True), patch.object(
            yt_app.subprocess, "Popen", side_effect=popen
        ):
            result = self.api.extract_info("https://www.twitch.tv/videos/1234567890")
        self.assertTrue(result["success"], result)
        command = commands[0]
        self.assertIn("--ignore-config", command)
        self.assertEqual(command[command.index("--cache-dir") + 1], str(self.ytdlp_cache))
        self.assertEqual(environments[0]["DENO_DIR"], str(self.deno_cache))
        self.assertEqual(environments[0]["XDG_CACHE_HOME"], str(self.cache))

    def test_download_keeps_failure_reason_visible_and_cache_local(self):
        commands = []
        environments = []
        def popen(command, **kwargs):
            commands.append(command)
            environments.append(kwargs["env"])
            return FakeProcess(
                "ERROR: [twitch:vod] Failed to download m3u8 information: HTTP Error 403: Forbidden\n",
                returncode=1
            )
        item = {
            "url": "https://www.twitch.tv/videos/1234567890",
            "title": "VOD à tester", "mode": "Vidéo",
            "selectedQuality": "Meilleure qualité (Auto)"
        }
        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=True), patch.object(
            yt_app.threading, "Thread", ImmediateThread
        ), patch.object(yt_app.subprocess, "Popen", side_effect=popen):
            self.api.start_downloads([item])
        command = commands[0]
        self.assertIn("--ignore-config", command)
        self.assertEqual(command[command.index("--cache-dir") + 1], str(self.ytdlp_cache))
        self.assertEqual(environments[0]["DENO_DIR"], str(self.deno_cache))
        final = [x for x in self.api._window.scripts if x.startswith("updateDownloadProgress(")]
        self.assertTrue(final, "Aucun état final renvoyé à l'interface")
        self.assertIn("403", final[-1], final[-1])
        message = json.loads(final[-1][len("updateDownloadProgress(0, "):-1])
        self.assertIn("Échec", message)
        self.assertNotIn("Traitement terminé", final[-1])


if __name__ == "__main__":
    unittest.main()
