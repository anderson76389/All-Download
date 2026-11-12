"""Release checks must catch tampering, missing files and checksum substitution."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.verify_release_asset import VerificationError, verify_asset


class ReleaseAssetIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.asset = self.root / "All-Download-Android-0.6.22-beta.apk"
        self.asset.write_bytes(b"\x01\x02" * 1_000)
        self.sidecar = Path(str(self.asset) + ".sha256")
        self.sha = hashlib.sha256(self.asset.read_bytes()).hexdigest()
        self.sidecar.write_text(self.sha + "  " + self.asset.name + "\n")

    def test_correct_asset_passes_and_does_not_modify_files(self):
        data = self.asset.read_bytes()
        self.assertEqual(self.sha, verify_asset(self.asset))
        self.assertEqual(data, self.asset.read_bytes())

    def test_corrupted_archive_is_refused(self):
        self.asset.write_bytes(self.asset.read_bytes() + b"corruption")
        with self.assertRaises(VerificationError):
            verify_asset(self.asset)

    def test_wrong_filename_or_checksum_is_refused(self):
        self.sidecar.write_text(self.sha + "  unrelated.apk\n")
        with self.assertRaises(VerificationError):
            verify_asset(self.asset)
        self.sidecar.write_text("invalid checksum\n")
        with self.assertRaises(VerificationError):
            verify_asset(self.asset)

    def test_missing_checksum_and_overlarge_reply_are_refused(self):
        self.sidecar.unlink()
        with self.assertRaises(VerificationError):
            verify_asset(self.asset)
        self.sidecar.write_bytes(b"f" * 5_000)
        with self.assertRaises(VerificationError):
            verify_asset(self.asset)

    def test_windows_and_linux_formats(self):
        for name in ("All-Download-Portable-Windows.zip",
                     "All-Download-Classique-Windows.zip",
                     "All-Download-Linux-x86_64.tar.xz"):
            archive = self.root / name
            archive.write_bytes(b"small synthetic archive")
            sha = hashlib.sha256(archive.read_bytes()).hexdigest()
            Path(str(archive) + ".sha256").write_text(sha + "  " + name)
            self.assertEqual(sha, verify_asset(archive))


if __name__ == "__main__":
    unittest.main()
