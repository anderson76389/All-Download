"""Offline Linux regressions: shutdown and bounded retry settings."""
import ast
from pathlib import Path
import tempfile
import unittest

from linux.app import DownloaderAPI


class LinuxResourceLifecycleTests(unittest.TestCase):
    def test_closed_window_cancels_children_before_releasing_window(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text("utf-8")
        tree = ast.parse(source)
        callbacks = [node for node in ast.walk(tree)
                     if isinstance(node, ast.FunctionDef)
                     and node.name == "on_linux_window_closed"]
        self.assertEqual(len(callbacks), 1)
        callback = ast.get_source_segment(source, callbacks[0])
        self.assertIn("api.cancel_downloads()", callback)
        self.assertIn("api._window = None", callback)
        self.assertIn("window.events.closed += on_linux_window_closed", source)
        self.assertIn("finally:\n        # Also release children", source)

    def test_download_args_use_resume_with_bounded_retries(self):
        with tempfile.TemporaryDirectory() as folder:
            api = DownloaderAPI(Path(folder) / "All-Download")
            args = api._common_args("https://www.twitch.tv/videos/2919531847",
                                    api.get_app_settings())
        self.assertIn("--continue", args)
        self.assertEqual("5", args[args.index("--retries") + 1])
        self.assertEqual("5", args[args.index("--fragment-retries") + 1])
        self.assertEqual("20", args[args.index("--socket-timeout") + 1])


class LinuxPartialResumeTests(unittest.TestCase):
    def test_failed_transfer_keeps_part_and_retry_reuses_then_cleans_it(self):
        from unittest import mock
        import sys
        from linux.app import resumable_workspace_name
        item = {"url": "https://example.org/stream/123", "mode": "Vidéo",
                "selectedQuality": "1080p"}
        with tempfile.TemporaryDirectory() as root:
            api = DownloaderAPI(Path(root) / "All-Download")
            workspace = api.temp / resumable_workspace_name(item)
            marker = workspace / "video.mp4.part"
            def fail_command(_item, _workspace):
                return [sys.executable, "-c",
                        "from pathlib import Path; import sys; " +
                        "Path(" + repr(str(marker)) + ").write_bytes(b'partial'); sys.exit(2)"]
            with mock.patch.object(api, "_command", side_effect=fail_command):
                api._worker([item])
            self.assertEqual(b"partial", marker.read_bytes())
            self.assertTrue(workspace.is_dir())
            def resume_command(_item, new_workspace):
                self.assertEqual(workspace, new_workspace)
                return [sys.executable, "-c",
                        "from pathlib import Path; import sys; " +
                        "sys.exit(0 if Path(" + repr(str(marker)) + ").is_file() else 3)"]
            with mock.patch.object(api, "_command", side_effect=resume_command):
                api._worker([item])
            self.assertFalse(workspace.exists(),
                             "A finished transfer must not leave spare .part files")

    def test_workspace_key_is_stable_and_sensitive_urls_not_exposed(self):
        from linux.app import resumable_workspace_name
        item = {"url": "https://example.org/test?id=secret-token",
                "mode": "Vidéo", "selectedQuality": "1080p"}
        first = resumable_workspace_name(item)
        self.assertEqual(first, resumable_workspace_name(dict(item)))
        self.assertRegex(first, r"^[0-9a-f]{32}$")
        self.assertNotIn("secret", first)
        self.assertNotEqual(first, resumable_workspace_name(
            {**item, "selectedQuality": "720p"}))


if __name__ == "__main__":
    unittest.main()
