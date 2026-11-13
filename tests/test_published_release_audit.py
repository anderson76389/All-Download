"""Unit regressions for the published-release auditor (no network or binary downloads)."""
from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "audit_release_assets.py"
SPEC = importlib.util.spec_from_file_location("all_download_release_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class ReachedChecksum(Exception):
    """Means Android release tag validation was passed."""


class PublishedReleaseAuditRegressionTests(unittest.TestCase):
    def test_android_stable_and_beta_tags_are_accepted(self):
        for tag in ("android-v1.0.0", "android-v1.3.27", "android-v0.6.22-beta"):
            with self.subTest(tag=tag):
                with mock.patch.object(audit, "verify_checksum",
                                       side_effect=ReachedChecksum):
                    with self.assertRaises(ReachedChecksum):
                        audit.check_android(Path("/not-used"), tag)

    def test_android_malformed_tags_are_rejected(self):
        for tag in ("", "android-v1.0", "android-v1.0.0-rc1",
                    "android-v1.0.0-beta-extra", "linux-v1.0.0",
                    "android-v1.0.0/../../other"):
            with self.subTest(tag=tag):
                with self.assertRaisesRegex(AssertionError, "Invalid Android release tag"):
                    audit.check_android(Path("/not-used"), tag)

    def test_windows_release_rejects_missing_checksum(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "All-Download-Portable-Windows.zip"
            archive.write_bytes(b"x" * 2048)
            with self.assertRaisesRegex(AssertionError, "sidecar missing"):
                audit.check_windows(Path(temp))

    def test_windows_release_rejects_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "All-Download-Portable-Windows.zip"
            archive.write_bytes(b"x" * 2048)
            Path(str(archive) + ".sha256").write_text(
                "0" * 64 + "  " + archive.name + "\n", encoding="ascii")
            with self.assertRaisesRegex(AssertionError, "SHA-256 mismatch"):
                audit.check_windows(Path(temp))

    def test_valid_checksum_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "All-Download-Portable-Windows.zip"
            data = b"release-integrity" * 150
            archive.write_bytes(data)
            Path(str(archive) + ".sha256").write_text(
                hashlib.sha256(data).hexdigest() + "  " + archive.name + "\n",
                encoding="ascii")
            audit.verify_checksum(archive)


if __name__ == "__main__":
    unittest.main()
