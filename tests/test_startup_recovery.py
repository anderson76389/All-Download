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
