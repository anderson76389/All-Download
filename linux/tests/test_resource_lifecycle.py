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


if __name__ == "__main__":
    unittest.main()
