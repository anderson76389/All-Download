"""Tests hors réseau pour le secours HLS Twitch indépendant."""
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import twitch_hls

PREVIEW = (
    "https://d1abc1234.cloudfront.net/"
    "abcd1234abcd1234abcd_exemple_12345_1711234567/storyboards/123.jpg"
)
PLAYLIST = "#EXTM3U\n#EXT-X-VERSION:3\n#EXTINF:10.0,\n0.ts\n#EXTINF:9.2,\n1.ts\n#EXT-X-ENDLIST\n"


class HLSFallbackTests(unittest.TestCase):
    def test_cdn_validation_blocks_external_hosts_and_plain_http(self):
        self.assertTrue(twitch_hls.is_twitch_cdn(PREVIEW))
        for url in (
            "http://d1abc1234.cloudfront.net/a",
            "https://evil.test/a",
            "https://d1abc1234.cloudfront.net.evil.test/a",
            "https://cloudfront.net/a",
            "https://u:p@d1abc1234.cloudfront.net/a",
        ):
            self.assertFalse(twitch_hls.is_twitch_cdn(url), url)

    def test_manifest_candidates_from_real_preview_pattern(self):
        opts = twitch_hls.manifest_candidates(PREVIEW, "1080p (60fps)")
        self.assertEqual(opts[0][0], "1080p60")
        self.assertTrue(opts[0][1].endswith("/1080p60/index-dvr.m3u8"))
        self.assertFalse(any(q == "chunked" for q, _ in opts))
        with self.assertRaises(twitch_hls.HLSUnavailable):
            twitch_hls.manifest_candidates("https://test.com/a", "auto")

    def test_selected_quality_never_silently_downloads_source_higher_resolution(self):
        urls = twitch_hls.manifest_candidates(PREVIEW, "720p (60fps)")
        names = [name for name, _ in urls]
        self.assertEqual(names[0], "720p60")
        self.assertNotIn("chunked", names)
        self.assertNotIn("1080p60", names)
        self.assertIn("480p30", names)
        low = [name for name, _ in twitch_hls.manifest_candidates(PREVIEW, "720p (30fps)")]
        self.assertEqual(low[0], "720p30")
        self.assertNotIn("720p60", low)
        generic = [name for name, _ in twitch_hls.manifest_candidates(PREVIEW, "720p")]
        self.assertEqual(generic[0], "720p60")

    def test_read_manifest_parses_fragment_duration(self):
        response = io.BytesIO(PLAYLIST.encode("utf-8"))
        response.url = PREVIEW
        with patch.object(twitch_hls.urllib.request, "urlopen", return_value=response):
            count, duration = twitch_hls.read_public_manifest(
                twitch_hls.manifest_candidates(PREVIEW, "auto")[0][1])
        self.assertEqual(count, 2)
        self.assertAlmostEqual(duration, 19.2)

    def test_read_manifest_rejects_html_response(self):
        response = io.BytesIO(b"<html>blocked</html>")
        response.url = PREVIEW
        with patch.object(twitch_hls.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(twitch_hls.HLSUnavailable):
                twitch_hls.read_public_manifest(twitch_hls.manifest_candidates(PREVIEW, "auto")[0][1])

    def test_resolve_hls_finds_source(self):
        with patch.object(twitch_hls, "metadata_for_vod", return_value={
            "title": "VOD test", "seekPreviewsURL": PREVIEW
        }), patch.object(twitch_hls, "read_public_manifest", return_value=(803, 8001.0)):
            url, quality, duration, count = twitch_hls.resolve_hls(
                "https://www.twitch.tv/videos/2919531847")
        self.assertEqual((quality, duration, count), ("chunked", 8001.0, 803))
        self.assertTrue(url.startswith("https://"))

    def test_resolve_hls_missing_storyboard(self):
        with patch.object(twitch_hls, "metadata_for_vod", return_value={"seekPreviewsURL": None}):
            with self.assertRaises(twitch_hls.HLSUnavailable):
                twitch_hls.resolve_hls("https://twitch.tv/videos/2919531847")

    def test_resolve_hls_no_public_playlist(self):
        with patch.object(twitch_hls, "metadata_for_vod", return_value={"seekPreviewsURL": PREVIEW}), \
             patch.object(twitch_hls, "read_public_manifest", side_effect=HTTPError(
                 "https://cdn.test/a", 403, "Forbidden", None, None)):
            with self.assertRaises(twitch_hls.HLSUnavailable):
                twitch_hls.resolve_hls("https://twitch.tv/videos/2919531847")

    def test_progress(self):
        self.assertEqual(twitch_hls.progress_from_ffmpeg("out_time_ms=2000000", 10), 20)
        self.assertEqual(twitch_hls.progress_from_ffmpeg("out_time_us=100000000", 10), 99)
        self.assertIsNone(twitch_hls.progress_from_ffmpeg("progress=continue", 10))
        self.assertIsNone(twitch_hls.progress_from_ffmpeg("out_time_ms=1", 0))

    def test_output_paths_are_safe_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            item = "https://www.twitch.tv/videos/2919531847"
            temp, output = twitch_hls.media_paths(root, item, "Bonjour:Vidéo?")
            self.assertEqual(output.parent, Path(root))
            self.assertNotIn(":", output.name)
            output.write_bytes(b"user existing media")
            tmp2, new_output = twitch_hls.media_paths(root, item, "Bonjour:Vidéo?")
            self.assertEqual(new_output.name, "Twitch_2919531847_Bonjour_Vidéo_ (2).mp4")
            self.assertNotEqual(temp, tmp2)
            self.assertEqual(output.read_bytes(), b"user existing media")

    def test_requested_720_transcodes_source_without_upscaling(self):
        url = twitch_hls.manifest_candidates(PREVIEW, "auto")[0][1]
        command = twitch_hls.ffmpeg_command(
            "C:/app/ffmpeg.exe", url, "D:/out.mp4", max_height=720, max_fps=30
        )
        self.assertIn("scale=-2:min(ih\\,720)", command)
        self.assertIn("libx264", command)
        self.assertEqual(command[command.index("-r") + 1], "30")
        self.assertNotIn("-c", command)
        with self.assertRaises(twitch_hls.HLSUnavailable):
            twitch_hls.ffmpeg_command("ffmpeg", url, "out.mp4", max_height=0)

    def test_ffmpeg_arguments_no_shell(self):
        url = twitch_hls.manifest_candidates(PREVIEW, "auto")[0][1]
        cmd = twitch_hls.ffmpeg_command("C:/app/bin/ffmpeg.exe", url, "D:/sample.part.mp4")
        self.assertEqual(cmd[0], "C:/app/bin/ffmpeg.exe")
        self.assertIn("-progress", cmd)
        self.assertIn("pipe:1", cmd)
        self.assertIn("-n", cmd)
        self.assertIn("-c", cmd)
        self.assertIn("copy", cmd)
        with self.assertRaises(twitch_hls.HLSUnavailable):
            twitch_hls.ffmpeg_command("ffmpeg", "https://evil.test/a.m3u8", "out.mp4")

if __name__ == "__main__":
    unittest.main()
