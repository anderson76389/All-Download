"""Le crash CLR connu provoque une relance automatique unique et bornée."""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import yt_app


class StartupRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.log = os.path.join(self.temp.name, "crash_log.txt")
        self.error = RuntimeError("Failed to resolve Python.Runtime.Loader.Initialize from Python.Runtime.dll")

    def test_clr_retry_runs_new_pyinstaller_environment_once(self):
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "platform", "win32"
        ), patch.object(yt_app, "CRASH_LOG", self.log), patch.object(
            yt_app.subprocess, "Popen", return_value=MagicMock()
        ) as popen:
            self.assertTrue(yt_app.retry_transient_gui_startup(self.error, []))
            args, kwargs = popen.call_args
            self.assertEqual(args[0][-1], yt_app.STARTUP_RETRY_FLAG)
            self.assertEqual(kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1")
            self.assertFalse(yt_app.retry_transient_gui_startup(
                self.error, [yt_app.STARTUP_RETRY_FLAG]))
            self.assertEqual(popen.call_count, 1)
        with open(self.log, encoding="utf-8") as log:
            self.assertIn("Erreur CLR transitoire", log.read())

    def test_webview_recovery_uses_separate_storage_profile(self):
        # Eviter un conflit avec les enfants WebView2 restes actifs apres un gel.
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "executable", os.path.join(self.temp.name, "All_Media_Download.exe")
        ):
            initial = yt_app.get_gui_webview_storage_path([])
            retry = yt_app.get_gui_webview_storage_path([yt_app.WEBVIEW_RETRY_FLAG])
            self.assertNotEqual(initial, retry)
            self.assertTrue(retry.endswith("webview-recuperation"))
            self.assertEqual(retry, yt_app.get_gui_webview_storage_path([yt_app.STARTUP_RETRY_FLAG]))
            marker = os.path.join(self.temp.name, ".all-download-installed")
            with open(marker, "w") as file:
                file.write("installed")
            self.assertTrue(yt_app.get_gui_webview_storage_path([]).endswith("webview-classique"))
            self.assertTrue(yt_app.get_gui_webview_storage_path([yt_app.WEBVIEW_RETRY_FLAG]).endswith("webview-classique-recuperation"))

    def test_webview_hang_relaunches_windows_exe_only_once(self):
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "platform", "win32"
        ), patch.object(yt_app, "STARTUP_LOG", os.path.join(self.temp.name, "startup_log.txt")), patch.object(
            yt_app.subprocess, "Popen", return_value=MagicMock()
        ) as popen:
            self.assertTrue(yt_app.restart_after_webview_timeout([]))
            args, kwargs = popen.call_args
            self.assertEqual(args[0][-1], yt_app.WEBVIEW_RETRY_FLAG)
            self.assertEqual(kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1")
            self.assertFalse(yt_app.restart_after_webview_timeout([yt_app.WEBVIEW_RETRY_FLAG]))
            self.assertFalse(yt_app.restart_after_webview_timeout([yt_app.STARTUP_RETRY_FLAG]))
            self.assertEqual(popen.call_count, 1)

    def test_webview_hang_never_relaunches_source_or_other_os(self):
        with patch.object(yt_app.sys, "frozen", False, create=True), patch.object(
            yt_app.sys, "platform", "win32"
        ), patch.object(yt_app.subprocess, "Popen") as popen:
            self.assertFalse(yt_app.restart_after_webview_timeout([]))
            popen.assert_not_called()

    def test_webview_watchdog_ignores_loaded_or_closed_window(self):
        import threading
        ready = threading.Event()
        closed = threading.Event()
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "platform", "win32"
        ), patch.object(yt_app, "restart_after_webview_timeout") as restart:
            ready.set()
            thread = yt_app.start_webview_startup_watchdog(ready, closed, timeout=0.02)
            thread.join(1)
            self.assertFalse(thread.is_alive())
            ready.clear()
            closed.set()
            thread = yt_app.start_webview_startup_watchdog(ready, closed, timeout=0.02)
            thread.join(1)
            self.assertFalse(thread.is_alive())
            restart.assert_not_called()

    def test_webview_watchdog_detects_silent_stall(self):
        import threading
        ready = threading.Event()
        closed = threading.Event()
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "platform", "win32"
        ), patch.object(yt_app, "STARTUP_LOG", os.path.join(self.temp.name, "startup_log.txt")), patch.object(
            yt_app, "restart_after_webview_timeout", return_value=False
        ) as restart:
            thread = yt_app.start_webview_startup_watchdog(ready, closed, timeout=0.02)
            thread.join(1)
            self.assertFalse(thread.is_alive())
            restart.assert_called_once()
        with open(os.path.join(self.temp.name, "startup_log.txt"), encoding="utf-8") as log:
            self.assertIn("HTML non chargee", log.read())

    def test_webview_restart_failure_does_not_kill_existing_process(self):
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "platform", "win32"
        ), patch.object(yt_app.subprocess, "Popen", side_effect=OSError("Access denied")), patch.object(
            yt_app, "STARTUP_LOG", os.path.join(self.temp.name, "startup_log.txt")
        ):
            self.assertFalse(yt_app.restart_after_webview_timeout([]))

    def test_other_errors_never_restart(self):
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "platform", "win32"
        ), patch.object(yt_app.subprocess, "Popen") as popen:
            self.assertFalse(yt_app.retry_transient_gui_startup(
                RuntimeError("HTML_FILE absent"), []))
            popen.assert_not_called()

    def test_source_mode_does_not_restart(self):
        with patch.object(yt_app.sys, "frozen", False, create=True), patch.object(
            yt_app.sys, "platform", "win32"
        ), patch.object(yt_app.subprocess, "Popen") as popen:
            self.assertFalse(yt_app.retry_transient_gui_startup(self.error, []))
            popen.assert_not_called()

    def test_failed_restart_keeps_original_error_visible(self):
        with patch.object(yt_app.sys, "frozen", True, create=True), patch.object(
            yt_app.sys, "platform", "win32"
        ), patch.object(yt_app, "CRASH_LOG", self.log), patch.object(
            yt_app.subprocess, "Popen", side_effect=OSError("Accès refusé")
        ):
            self.assertFalse(yt_app.retry_transient_gui_startup(self.error, []))


if __name__ == "__main__":
    unittest.main()
