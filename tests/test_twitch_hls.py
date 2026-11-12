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
        self.assertEqual([q for q, _ in opts], ["chunked", "1080p60", "1080p30", "720p60", "720p30"])
        self.assertTrue(opts[1][1].endswith("/1080p60/index-dvr.m3u8"))
        with self.assertRaises(twitch_hls.HLSUnavailable):
            twitch_hls.manifest_candidates("https://test.com/a", "auto")

    def test_selected_quality_never_silently_downloads_source_higher_resolution(self):
        urls = twitch_hls.manifest_candidates(PREVIEW, "720p (60fps)")
        names = [name for name, _ in urls]
        self.assertEqual(names, ["chunked", "720p60", "720p30"])
        self.assertNotIn("1080p60", names)
        self.assertNotIn("480p30", names)
        low = [name for name, _ in twitch_hls.manifest_candidates(PREVIEW, "720p (30fps)")]
        self.assertEqual(low, ["chunked", "720p30"])
        self.assertNotIn("720p60", low)
        generic = [name for name, _ in twitch_hls.manifest_candidates(PREVIEW, "720p")]
        self.assertEqual(generic, ["chunked", "720p60", "720p30"])

    def test_twitch_selected_quality_uses_full_storyboard_path_not_quality_number(self):
        expected = "abcd1234abcd1234abcd_exemple_12345_1711234567"
        profiles = twitch_hls.manifest_candidates(PREVIEW, "1080p (60fps)")
        self.assertEqual([x for x, _ in profiles][:3],
                         ["chunked", "1080p60", "1080p30"])
        for name, url in profiles:
            self.assertIn("/" + expected + "/" + name + "/index-dvr.m3u8", url)
            self.assertNotIn("/1080/" + name, url)
        manual_720 = twitch_hls.manifest_candidates(PREVIEW, "720p (60fps)")
        self.assertEqual(manual_720[0][0], "chunked")
        self.assertNotIn("1080p60", [x for x, _ in manual_720])
        self.assertTrue(all("/" + expected + "/" in url for _, url in manual_720))

    def test_twitch_1080_automatically_tries_720_when_1080_missing(self):
        checked = []
        def probe(url, timeout=12):
            checked.append(url)
            if "/720p60/" in url:
                return (40, 400.0)
            raise HTTPError(url, 403, "Forbidden", None, None)
        with patch.object(twitch_hls, "metadata_for_vod",
                          return_value={"seekPreviewsURL": PREVIEW}), \
             patch.object(twitch_hls, "read_public_manifest", side_effect=probe):
            manifest, quality, duration, count = twitch_hls.resolve_hls(
                "https://www.twitch.tv/videos/2919531847", "1080p (60fps)")
        self.assertEqual(quality, "720p60")
        self.assertEqual((duration, count), (400.0, 40))
        self.assertIn("/720p60/index-dvr.m3u8", manifest)
        self.assertIn("/1080p60/", checked[0])
        self.assertIn("/1080p30/", checked[1])
        self.assertIn("/720p60/", checked[2])

    def test_native_720_chunked_never_preempts_available_1080(self):
        checked = []
        def read(url, timeout=12):
            checked.append(url)
            return 80, 800.0
        with patch.object(twitch_hls, "metadata_for_vod",
                          return_value={"seekPreviewsURL": PREVIEW}), \
             patch.object(twitch_hls, "read_public_manifest", side_effect=read):
            url, label, _, _ = twitch_hls.resolve_hls(
                "https://www.twitch.tv/videos/2919531847", "1080p (60fps)",
                source_height_probe=lambda _: 720)
        self.assertEqual(label, "1080p60")
        self.assertIn("/1080p60/", url)
        self.assertIn("/chunked/", checked[0])

    def test_native_720_chunked_is_valid_fallback_after_1080_failure(self):
        checked = []
        def read(url, timeout=12):
            checked.append(url)
            if "/chunked/" in url:
                return 80, 800.0
            raise HTTPError(url, 403, "Forbidden", None, None)
        with patch.object(twitch_hls, "metadata_for_vod",
                          return_value={"seekPreviewsURL": PREVIEW}), \
             patch.object(twitch_hls, "read_public_manifest", side_effect=read):
            url, label, _, _ = twitch_hls.resolve_hls(
                "https://www.twitch.tv/videos/2919531847", "1080p (60fps)",
                source_height_probe=lambda _: 720)
        self.assertEqual(label, "source native 720p")
        self.assertIn("/chunked/", url)
        self.assertTrue(any("/1080p60/" in item for item in checked))
        self.assertTrue(any("/1080p30/" in item for item in checked))

    def test_unknown_or_lower_source_resolution_is_not_labeled_1080p(self):
        with patch.object(twitch_hls, "metadata_for_vod",
                          return_value={"seekPreviewsURL": PREVIEW}), \
             patch.object(twitch_hls, "read_public_manifest", return_value=(803, 8001.0)):
            for native_height in (480, 1440, None):
                url, label, _, _ = twitch_hls.resolve_hls(
                    "https://www.twitch.tv/videos/2919531847", "1080p (60fps)",
                    source_height_probe=lambda _: native_height
                )
                self.assertEqual(label, "1080p60")
                self.assertIn("/1080p60/", url)
            with self.assertRaises(twitch_hls.HLSUnavailable):
                with patch.object(twitch_hls, "read_public_manifest",
                                  side_effect=lambda url, timeout=12: (803, 8001.0)
                                  if "/chunked/" in url else
                                  (_ for _ in ()).throw(HTTPError(url, 403, "Forbidden", None, None))):
                    twitch_hls.resolve_hls(
                        "https://www.twitch.tv/videos/2919531847",
                        source_height_probe=lambda _: 480
                    )

    def test_source_720_native_accepted_and_not_transcoded(self):
        with patch.object(twitch_hls, "metadata_for_vod",
                          return_value={"seekPreviewsURL": PREVIEW}), \
             patch.object(twitch_hls, "read_public_manifest", return_value=(803, 8001.0)):
            _, label, _, _ = twitch_hls.resolve_hls(
                "https://www.twitch.tv/videos/2919531847", "1080p (60fps)",
                source_height_probe=lambda _: 720
            )
            self.assertEqual(label, "source native 720p")
            _, label_720, _, _ = twitch_hls.resolve_hls(
                "https://www.twitch.tv/videos/2919531847", "720p (60fps)",
                source_height_probe=lambda _: 1080
            )
            self.assertEqual(label_720, "720p60")

    def test_probe_native_height_ffprobe_output(self):
        from types import SimpleNamespace
        url = twitch_hls.manifest_candidates(PREVIEW, "1080p (60fps)")[0][1]
        with patch.object(twitch_hls.subprocess, "run", return_value=SimpleNamespace(
            returncode=0, stdout='{"streams":[{"height":1080}]}'
        )) as proc:
            self.assertEqual(twitch_hls.probe_native_height("ffprobe.exe", url), 1080)
        command = proc.call_args.args[0]
        self.assertIn("-show_entries", command)
        self.assertNotIn("-c:v", command)
        with patch.object(twitch_hls.subprocess, "run", return_value=SimpleNamespace(
            returncode=1, stdout=""
        )):
            self.assertIsNone(twitch_hls.probe_native_height("ffprobe.exe", url))

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
                "https://www.twitch.tv/videos/2919531847",
                source_height_probe=lambda _: 1080)
        self.assertEqual((quality, duration, count), ("source native 1080p", 8001.0, 803))
        self.assertTrue(url.endswith("/chunked/index-dvr.m3u8"))

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

    def test_native_video_is_remuxed_without_any_reencoding(self):
        url = twitch_hls.manifest_candidates(PREVIEW, "auto")[0][1]
        command = twitch_hls.ffmpeg_command("C:/app/ffmpeg.exe", url, "D:/out.mp4")
        self.assertEqual(command[command.index("-c") + 1], "copy")
        self.assertNotIn("-vf", command)
        self.assertNotIn("-r", command)
        self.assertNotIn("libx264", command)
        self.assertNotIn("scale", " ".join(command))

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
