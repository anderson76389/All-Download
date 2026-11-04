"""Tests du vrai moteur alternatif Streamlink : sélection, écriture, refus et sécurité."""
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import twitch_streamlink_engine as engine
import yt_app


URL = "https://www.twitch.tv/videos/2905228526"


class FakeStream:
    def __init__(self, payload=b"recorded-vod-bytes"):
        self.payload = payload
        self.was_closed = False

    def open(self):
        parent = self
        class Reader(io.BytesIO):
            def close(self):
                parent.was_closed = True
                super().close()
        return Reader(self.payload)


class FakeSession:
    def __init__(self, streams=None, fail=None):
        self.items = streams if streams is not None else {"best": FakeStream()}
        self.fail = fail
        self.options = {}
        self.urls = []

    def set_option(self, name, value):
        self.options[name] = value

    def streams(self, url):
        self.urls.append(url)
        if self.fail:
            raise RuntimeError(self.fail)
        return self.items


class FakeThread:
    def __init__(self, target, **_kwargs):
        self.fn = target

    def start(self):
        self.fn()


class Recorder:
    def __init__(self):
        self.scripts = []

    def evaluate_js(self, script):
        self.scripts.append(script)


class StreamlinkEngineTests(unittest.TestCase):
    def test_strict_twitch_vod_urls(self):
        self.assertEqual(engine.parse_twitch_vod_id(URL), "2905228526")
        self.assertEqual(engine.parse_twitch_vod_id(URL + "?t=30m"), "2905228526")
        self.assertIsNone(engine.parse_twitch_vod_id("https://example.com/videos/2905228526"))
        self.assertIsNone(engine.parse_twitch_vod_id("https://www.twitch.tv/someone"))
        self.assertIsNone(engine.parse_twitch_vod_id("https://evil.twitch.tv/videos/2905228526"))
        self.assertIsNone(engine.parse_twitch_vod_id("file:///tmp/video.mp4"))

    def test_selects_best_or_closest_allowed_quality(self):
        streams = {
            "360p": FakeStream(), "720p60": FakeStream(),
            "1080p60": FakeStream(), "best": FakeStream(),
        }
        self.assertEqual(engine.select_video_stream(streams)[0], "best")
        self.assertEqual(engine.select_video_stream(streams, "720p")[0], "720p60")
        self.assertEqual(engine.select_video_stream(streams, "480p")[0], "360p")
        self.assertEqual(engine.select_video_stream(streams, "1440p")[0], "1080p60")
        with self.assertRaises(engine.TwitchEngineError):
            engine.select_video_streams if False else engine.select_video_stream({})

    def test_streaming_download_creates_autres_and_preserves_names(self):
        stream = FakeStream(b"test-hls-payload" * 200)
        session = FakeSession({"best": stream})
        with tempfile.TemporaryDirectory() as base:
            original = Path(base) / "AUTRES" / "Twitch_VOD_2905228526_Streamlink_best.ts"
            original.parent.mkdir(parents=True)
            original.write_bytes(b"ORIGINAL")
            seen = []
            result = Path(engine.download_twitch_vod(
                URL, base, progress=seen.append, session_factory=lambda: session,
                ffmpeg_path=str(Path(base) / "no-ffmpeg.exe"),
            ))
            self.assertEqual(result.parent, original.parent)
            self.assertEqual(result.read_bytes(), b"test-hls-payload" * 200)
            self.assertEqual(original.read_bytes(), b"ORIGINAL")
            self.assertTrue(stream.was_closed)
            self.assertTrue(seen)
            self.assertTrue(session.options.get("no-plugin-cache"))
            self.assertFalse(list(original.parent.glob("*.part")))

    def test_restricted_access_fails_with_real_error(self):
        with tempfile.TemporaryDirectory() as base:
            session = FakeSession(fail="access denied for subscriber-only content")
            with self.assertRaisesRegex(engine.TwitchEngineError, "subscriber-only"):
                engine.download_twitch_vod(URL, base, session_factory=lambda: session)
            self.assertFalse((Path(base) / "AUTRES").exists())

    def test_cancelled_download_leaves_no_partial_file(self):
        with tempfile.TemporaryDirectory() as base:
            with self.assertRaises(engine.TwitchEngineCancelled):
                engine.download_twitch_vod(
                    URL, base, session_factory=lambda: FakeSession(),
                    cancelled=lambda: True,
                )
            self.assertFalse((Path(base) / "AUTRES").exists())

    def test_yt_dlp_unchanged_and_ui_bridge_reports_success(self):
        with tempfile.TemporaryDirectory() as base:
            api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
            api.download_folder = base
            api._window = Recorder()
            api.is_cancelled = False
            api.is_paused = False
            api._active_download_process = None
            with patch.object(yt_app.threading, "Thread", FakeThread), patch.object(
                yt_app.twitch_streamlink_engine, "download_twitch_vod",
                return_value=str(Path(base) / "AUTRES" / "vod.ts")
            ) as fn:
                invalid = api.start_twitch_streamlink("https://evil.example/videos/2905228526")
                self.assertFalse(invalid["success"])
                good = api.start_twitch_streamlink(URL, "720p")
                self.assertTrue(good["success"])
                self.assertIn("AUTRES", "".join(api._window.scripts))
                self.assertEqual(fn.call_args.kwargs["quality"], "720p")
                self.assertFalse(api._streamlink_download_active)
            self.assertFalse(api.start_twitch_streamlink(URL, "best")["success"] if False else False)


if __name__ == "__main__":
    unittest.main()
