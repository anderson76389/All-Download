"""No media/network needed: real resource cancellation + closed-window lifecycle."""
import ast
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import Mock, patch

import yt_app


class ResourceShutdownTests(unittest.TestCase):
    def test_cancel_stops_download_and_metadata_processes(self):
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        running = Mock(pid=14001)
        metadata = Mock(pid=14002)
        metadata.poll.return_value = None
        api._active_download_process = running
        api._metadata_process_lock = threading.Lock()
        api._metadata_processes = {metadata}
        api._suspended_download_pids = []
        api.is_cancelled = False
        api.is_paused = True
        with patch.object(yt_app, "kill_process_tree") as kill:
            self.assertTrue(api.cancel_downloads())
        self.assertTrue(api.is_cancelled)
        self.assertFalse(api.is_paused)
        self.assertEqual({call.args[0] for call in kill.call_args_list},
                         {14001, 14002})

    @unittest.skipUnless(sys.platform == "win32", "Windows child process test")
    def test_actual_windows_download_and_metadata_processes_exit(self):
        processes = [
            subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                             creationflags=subprocess.CREATE_NO_WINDOW)
            for _ in range(2)
        ]
        try:
            api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
            api._active_download_process = processes[0]
            api._metadata_process_lock = threading.Lock()
            api._metadata_processes = {processes[1]}
            api._suspended_download_pids = []
            api.is_paused = False
            api.is_cancelled = False
            self.assertTrue(api.cancel_downloads())
            for process in processes:
                process.wait(timeout=8)
                self.assertIsNotNone(process.returncode)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=8)

    def test_idle_cancel_is_safe_for_legacy_api_test_fixtures(self):
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._active_download_process = None
        api._suspended_download_pids = []
        api.is_paused = False
        api.is_cancelled = False
        self.assertTrue(api.cancel_downloads())

    def test_native_window_closed_handler_cancels_before_discarding_gui(self):
        source = Path(yt_app.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        closed = [node for node in ast.walk(tree)
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and node.name == "on_window_closed"]
        self.assertEqual(len(closed), 1)
        body = ast.get_source_segment(source, closed[0])
        self.assertIn("api.cancel_downloads()", body)
        self.assertIn("api._window = None", body)


if __name__ == "__main__":
    unittest.main()
