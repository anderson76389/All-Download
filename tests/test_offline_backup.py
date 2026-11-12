"""Offline backup integrity / restore / no-overwrite regressions."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from scripts.offline_backup import BackupError, make_backup, restore_backup, verify_backup


class OfflineRecoveryTests(unittest.TestCase):
    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("Git required")
        self.tmp = tempfile.TemporaryDirectory(prefix="all-download-offline-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "hello.txt").write_text("Version 1.0", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "hello.txt"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Offline test",
                        "-c", "user.email=test@example.invalid", "commit", "-qm",
                        "offline source snapshot"], check=True)
        self.backup = self.root / "backup.zip"

    def test_complete_source_and_private_data_restorable_without_network(self):
        portable = self.root / "portable"
        (portable / "Donnees").mkdir(parents=True)
        (portable / "AUDIOS").mkdir()
        (portable / "Donnees" / "config.json").write_text('{"theme":"OLED"}')
        (portable / "Donnees" / "release.p12").write_bytes(b"Never back up signing keys")
        (portable / "AUDIOS" / "track.mp3").write_bytes(b"\x00" * 2048)
        make_backup(self.repo, self.backup, portable, allow_sensitive=True)
        manifest = verify_backup(self.backup)
        self.assertEqual(3, len(manifest["files"]))
        restored = self.root / "restored"
        restore_backup(self.backup, restored)
        self.assertEqual("Version 1.0", (restored / "hello.txt").read_text("utf-8"))
        self.assertEqual('{"theme":"OLED"}',
                         (restored / "Donnees" / "config.json").read_text("utf-8"))
        self.assertEqual(2048, (restored / "AUDIOS" / "track.mp3").stat().st_size)
        self.assertFalse((restored / "Donnees" / "release.p12").exists())
        self.assertTrue((restored / ".git").is_dir())

    def test_archive_and_restore_never_overwrite_existing_files(self):
        make_backup(self.repo, self.backup)
        with self.assertRaises(BackupError):
            make_backup(self.repo, self.backup)
        restored = self.root / "restored"
        restored.mkdir()
        (restored / "important.txt").write_text("keep")
        with self.assertRaises(BackupError):
            restore_backup(self.backup, restored)
        self.assertEqual("keep", (restored / "important.txt").read_text())

    def test_tampering_and_traversal_are_rejected(self):
        make_backup(self.repo, self.backup)
        with zipfile.ZipFile(self.backup) as source:
            entries = [(name, source.read(name)) for name in source.namelist()]
        with zipfile.ZipFile(self.backup, "w") as target:
            for name, contents in entries:
                target.writestr(name, b"broken" if name.endswith(".bundle") else contents)
        with self.assertRaises(BackupError):
            verify_backup(self.backup)
        self.backup.with_name(self.backup.name + ".sha256").unlink()
        with self.assertRaises(BackupError):
            verify_backup(self.backup)
        make_backup(self.repo, self.root / "second.zip")
        tampered = self.root / "second.zip"
        with zipfile.ZipFile(tampered, "a") as archive:
            archive.writestr("user-data/Donnees/../../other", b"evil")
        with self.assertRaises(BackupError):
            verify_backup(tampered)

    def test_private_data_opt_in_required(self):
        root = self.root / "portable"
        root.mkdir()
        with self.assertRaisesRegex(BackupError, "accept-unencrypted"):
            make_backup(self.repo, self.backup, root)
        self.assertFalse(self.backup.exists())


if __name__ == "__main__":
    unittest.main()
