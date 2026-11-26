import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

script = Path(__file__).resolve().parents[1] / ".github/scripts/test_public_youtube_twitch.py"
spec = importlib.util.spec_from_file_location("public_media_probe", script)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class PublicMediaProbeTests(unittest.TestCase):
    def test_long_metadata_survives_subprocess_capture(self):
        code = "import json; print(json.dumps({'id': 'video', 'title': 'x' * 20000}))"
        status, output, _ = probe.run([sys.executable, "-c", code], 10)
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output)["id"], "video")

    def test_403_is_classified_before_truncation_and_urls_are_redacted(self):
        error = "Server returned 403 Forbidden https://media.example/?sig=" + "x" * 1000
        with patch.object(probe, "run", return_value=(1, "", error)):
            _, status, reason = probe.download("yt-dlp", probe.CASES[0][2], Path("."))
        self.assertEqual(status, "BLOCKED")
        self.assertNotIn("sig=", reason)
