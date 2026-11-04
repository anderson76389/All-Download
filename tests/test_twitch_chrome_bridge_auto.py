"""Tests du pont local entre Chrome et les dossiers AUTRES."""
import tempfile
import threading
import time
import unittest
from pathlib import Path

import twitch_chrome_bridge as bridge


class BrowserImportTests(unittest.TestCase):
    def test_new_video_detected_after_chrome_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "existing.mp4").write_bytes(b"old")
            baseline = bridge.snapshot_downloads(root)
            found = []
            stop = threading.Event()

            def producer():
                time.sleep(0.10)
                part = root / "new.mp4.crdownload"
                part.write_bytes(b"stream" * 500)
                time.sleep(0.10)
                part.rename(root / "new.mp4")

            threading.Thread(target=producer, daemon=True).start()

            def record(path):
                found.append(path)
                stop.set()

            count = bridge.monitor_chrome_downloads(
                root, baseline, record, cancelled=stop.is_set,
                poll_seconds=0.02, stable_polls=3, max_seconds=2,
            )
            self.assertEqual(count, 1)
            self.assertEqual([Path(p).name for p in found], ["new.mp4"])
            self.assertEqual((root / "existing.mp4").read_bytes(), b"old")

    def test_incomplete_files_are_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "incomplete.mp4.crdownload").write_bytes(b"stream")
            found = []
            count = bridge.monitor_chrome_downloads(
                folder, bridge.snapshot_downloads(folder), found.append,
                poll_seconds=0.02, stable_polls=2, max_seconds=0.12,
            )
            self.assertEqual(count, 0)
            self.assertFalse(found)

    def test_stopping_monitor_does_not_remove_local_files(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "existing.mp4"
            target.write_bytes(b"keep")
            cancel = threading.Event()
            cancel.set()
            count = bridge.monitor_chrome_downloads(
                folder, bridge.snapshot_downloads(folder), lambda p: None,
                cancelled=cancel.is_set,
            )
            self.assertEqual(count, 0)
            self.assertEqual(target.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
