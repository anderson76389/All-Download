"""Tests unitaires ciblés sur les réglages appliqués aux téléchargements et à l'interface."""
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import yt_app


class ThreadNow:
    def __init__(self, target, daemon=True):
        self.target = target

    def start(self):
        self.target()


class ProcessOk:
    def __init__(self):
        self.stdout = io.StringIO("")
        self.pid = 10242
        self.returncode = 0

    def communicate(self):
        return ("", "")


class Recorder:
    def __init__(self):
        self.scripts = []

    def evaluate_js(self, script):
        self.scripts.append(script)


class SettingsWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        self.api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        self.api.download_folder = self.root
        self.api.is_cancelled = False
        self.api.is_paused = False
        self.api.window = Recorder()
        self.api._active_download_process = None
        self.api.config = {"settings": {"sponsor_enable": False}}
        self.config_path = os.path.join(self.root, "config.json")
        p = patch.object(yt_app, "CONFIG_FILE", self.config_path)
        p.start()
        self.addCleanup(p.stop)

    def download(self, mode="Vidéo", quality="Meilleure qualité (Auto)", **settings):
        self.api.config["settings"] = {"sponsor_enable": False, **settings}
        commands = []

        def popen(args, **kwargs):
            commands.append(list(args))
            return ProcessOk()

        item = {"url": "https://www.youtube.com/watch?v=1234", "mode": mode,
                "title": "Un test", "selectedQuality": quality}
        with patch.object(yt_app.threading, "Thread", ThreadNow), patch.object(
            yt_app.subprocess, "Popen", side_effect=popen
        ):
            self.api.start_downloads([item])
        self.assertEqual(len(commands), 1)
        return commands[0]

    def test_video_container_and_origin_stream(self):
        cmd = self.download(video_format="MKV", video_origin_stream=False)
        self.assertEqual(cmd[cmd.index("--merge-output-format") + 1], "mkv")
        cmd = self.download(video_format="MP4", video_origin_stream=True)
        self.assertNotIn("--merge-output-format", cmd)

    def test_video_post_processing(self):
        cmd = self.download(post_process_video="Remuxer")
        self.assertIn("--remux-video", cmd)
        cmd = self.download(post_process_video="Normaliser")
        self.assertIn("ffmpeg:-af loudnorm", cmd)

    def test_audio_selection_priority_and_sample_rate(self):
        cmd = self.download("Audio", "FLAC", audio_format="MP3",
                            extra_selector="audio_rate", audio_sample_rate="48000",
                            post_process_audio="Normaliser")
        self.assertEqual(cmd[cmd.index("--audio-format") + 1], "flac")
        pp = cmd[cmd.index("--postprocessor-args") + 1]
        self.assertIn("-ar 48000", pp)
        self.assertIn("-af loudnorm", pp)

        cmd = self.download("Audio", "M4A", audio_format="FLAC")
        self.assertEqual(cmd[cmd.index("--audio-format") + 1], "m4a")
        cmd = self.download("Audio", "MP3_320", audio_format="FLAC")
        self.assertEqual(cmd[cmd.index("--audio-format") + 1], "mp3")
        self.assertEqual(cmd[cmd.index("--audio-quality") + 1], "320K")
        cmd = self.download("Audio", "FLAC", audio_sample_rate="48000", extra_selector="none")
        self.assertNotIn("--postprocessor-args", cmd)

    def test_metadata_thumbnail_options_are_applied(self):
        cmd = self.download(video_embed_thumb=False, video_write_thumb=False,
                            video_add_metadata=False)
        for flag in ("--embed-thumbnail", "--write-thumbnail", "--add-metadata"):
            self.assertNotIn(flag, cmd)
        cmd = self.download("Audio", "M4A", audio_embed_thumb=True,
                            audio_write_thumb=True, audio_add_metadata=True)
        for flag in ("--embed-thumbnail", "--write-thumbnail", "--add-metadata"):
            self.assertIn(flag, cmd)

    def test_proxy_sponsorblock_and_extractor_args(self):
        cmd = self.download(sponsor_enable=True, sponsor_remove="sponsor",
                            sponsor_mark="chapters", exact_cut=True,
                            proxy_toggle=True, proxy_url="socks5://127.0.0.1:1080",
                            extractor_args="youtube:player_client=default")
        for flag in ("--proxy", "--sponsorblock-remove", "--sponsorblock-mark",
                     "--extractor-args", "--force-keyframes-at-cuts"):
            self.assertIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("--proxy") + 1], "socks5://127.0.0.1:1080")

    def test_notifications_never_finish_and_always(self):
        for notify in ("never", "finish", "always"):
            with self.subTest(notify=notify):
                self.api.window.scripts.clear()
                self.download(notify=notify)
                scripts = [x for x in self.api.window.scripts if "showAppToast(" in x]
                self.assertEqual(len(scripts), 0 if notify == "never" else
                                 1 if notify == "finish" else 2)

    def test_quick_selector_persists_without_losing_other_settings(self):
        self.api.config["settings"] = {"theme": "dark", "video_format": "MP4"}
        result = self.api.save_quick_selector_value("format", "MKV")
        self.assertTrue(result["success"])
        self.assertEqual(self.api.get_app_settings()["video_format"], "MKV")
        result = self.api.save_quick_selector_value("audio_rate", "44100")
        self.assertTrue(result["success"])
        self.assertEqual(self.api.get_app_settings()["audio_sample_rate"], "44100")
        self.assertEqual(self.api.get_app_settings()["theme"], "dark")
        with open(self.config_path, encoding="utf-8") as file:
            loaded = json.load(file)
        self.assertEqual(loaded["settings"]["video_format"], "MKV")
        self.assertFalse(self.api.save_quick_selector_value("audio_rate", "garbage")["success"])
        self.assertFalse(self.api.save_quick_selector_value("format", "AVI")["success"])

    def test_fullscreen_and_compact_layout_rules_exist(self):
        page = yt_app.HTML_PAGE
        for expected in ("max-width: 1800px", "max-width: 1480px",
                         "@media (min-width: 1580px)", "@media (max-width: 760px)",
                         "grid-template-columns: repeat(2, minmax(0, 1fr))",
                         "extraQuickWrap", "appToast"):
            self.assertIn(expected, page)


if __name__ == "__main__":
    unittest.main()
