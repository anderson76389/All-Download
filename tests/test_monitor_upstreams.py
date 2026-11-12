"""Upstream maintenance must make at most one bounded request per known project."""
import io
import json
from unittest import mock
import unittest

from scripts.monitor_upstreams import fetch_latest, MAX_RESPONSE

class FakeReply(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *_):
        self.close()

class UpstreamMonitorTests(unittest.TestCase):
    def test_only_fixed_official_repos_and_read_only_api(self):
        data = {"tag_name": "2026.11.12",
                "html_url": "https://github.com/yt-dlp/yt-dlp/releases/tag/2026.11.12"}
        with mock.patch("scripts.monitor_upstreams.urlopen",
                        return_value=FakeReply(json.dumps(data).encode())) as call:
            self.assertEqual("2026.11.12", fetch_latest("yt-dlp/yt-dlp")["tag"])
            request = call.call_args.args[0]
            self.assertEqual("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest",
                             request.full_url)
            self.assertEqual(9, call.call_args.kwargs["timeout"])
        with self.assertRaises(ValueError):
            fetch_latest("attacker/repo")

    def test_rejects_untrusted_release_urls_and_oversize(self):
        data = {"tag_name": "2026.11.12",
                "html_url": "https://github.com/attacker/repo/releases/tag/2026.11.12"}
        with mock.patch("scripts.monitor_upstreams.urlopen",
                        return_value=FakeReply(json.dumps(data).encode())):
            with self.assertRaises(ValueError):
                fetch_latest("yt-dlp/yt-dlp")
        with mock.patch("scripts.monitor_upstreams.urlopen",
                        return_value=FakeReply(b"x" * (MAX_RESPONSE + 1))):
            with self.assertRaises(ValueError):
                fetch_latest("yt-dlp/yt-dlp")

if __name__ == "__main__":
    unittest.main()
