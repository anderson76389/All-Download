"""Regression coverage for real yt-dlp media quality metadata.

YouTube/Twitch quality choices must come from source formats, never from a
made-up ladder or from audio-only streams.
"""
import json
import unittest
from unittest.mock import patch

import yt_app


class SourceQualityTests(unittest.TestCase):
    def test_only_real_resolutions_show_up(self):
        formats = yt_app.available_video_qualities({
            "formats": [
                {"height": 1080, "fps": 60, "vcodec": "avc1.640028"},
                {"height": 480, "fps": 30, "vcodec": "h264"},
                {"height": 1080, "fps": 30, "vcodec": "h264"},
                {"height": 720, "vcodec": "none"},
                {"height": 2160, "vcodec": "none"},
            ]
        })
        self.assertEqual(formats, ["Meilleure qualité (Auto)", "1080p (60fps)", "480p"])
        self.assertNotIn("720p", formats)
        self.assertNotIn("2160p", formats)

    def test_flat_playlist_or_no_formats_does_not_invent_qualities(self):
        only_auto = ["Meilleure qualité (Auto)"]
        for data in ({}, {"formats": None}, {"formats": []},
                     {"formats": [{"vcodec": "none", "height": 1080}]},
                     {"formats": "invalid"}):
            self.assertEqual(yt_app.available_video_qualities(data), only_auto)

    def test_invalid_format_metadata_never_breaks_extraction(self):
        self.assertEqual(yt_app.available_video_qualities({"formats": [
            {"height": 720, "fps": "unknown", "vcodec": "h264"},
            {"height": True, "format_note": "1080p60", "fps": 60},
            {"height": 360, "fps": None},
            {"height": -1, "format_note": "audio only", "vcodec": "none"},
            "wrong", None, {"height": "?", "format_note": "4K"},
            {"height": 99999},
        ]}), ["Meilleure qualité (Auto)", "1080p (60fps)", "720p", "360p"])

    def test_extraction_card_uses_confirmed_options_only(self):
        class Process:
            returncode = 0
            def communicate(self, timeout=None):
                return json.dumps({
                    "id": "hello", "title": "Real 1080p only",
                    "duration": 14,
                    "formats": [{"height": 1080, "fps": 30, "vcodec": "avc1"}],
                }), ""

        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api.config = {"settings": {}}
        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=True), \
             patch.object(api, "get_app_settings", return_value={}), \
             patch.object(yt_app.subprocess, "Popen", return_value=Process()):
            result = api.extract_info("https://www.youtube.com/watch?v=1234")
        self.assertTrue(result["success"], result)
        self.assertEqual(result["data"]["formats"],
                         ["Meilleure qualité (Auto)", "1080p"])
        self.assertEqual(result["data"]["selectedQuality"], "Meilleure qualité (Auto)")


if __name__ == "__main__":
    unittest.main()
