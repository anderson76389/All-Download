"""Les ZIP doivent transporter six vrais dossiers vides, sans .gitkeep."""
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import build_release_archives as arch


class ZipFolderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / "out"
        self.out.mkdir()
        for category in arch.MEDIA_DIRS:
            (self.root / category).mkdir()
        for fn in ("logo.ico", "logo.jpg", "yt_app.py"):
            (self.root / fn).write_bytes(b"TEST")
        portable = self.root / "dist" / "All-Download-Portable"
        portable.mkdir(parents=True)
        (portable / "All_Media_Download.exe").write_bytes(b"EXE")
        # Le packaging Windows copie les logos dans le dossier Portable.
        for asset in ("logo.ico", "logo.jpg"):
            (portable / asset).write_bytes(b"TEST")
        classic = self.root / "dist" / "All-Download-Installer"
        classic.mkdir(parents=True)
        (classic / "All-Download-Setup.exe").write_bytes(b"SETUP")

    def check(self, name):
        with zipfile.ZipFile(self.out / name) as z:
            files = set(z.namelist())
            for cat in arch.MEDIA_DIRS:
                if name == arch.PORTABLE_NAME:
                    self.assertIn(cat + "/", files)
                    self.assertTrue(z.getinfo(cat + "/").is_dir())
                else:
                    self.assertNotIn(cat + "/", files)
            self.assertFalse(any(".gitkeep" in entry for entry in files))
            self.assertIn("Code-source/yt_app.py", files)

    def test_portable(self):
        arch.build_portable(self.root, self.out, [Path("yt_app.py")])
        self.check(arch.PORTABLE_NAME)

    def test_classic(self):
        arch.build_classic(self.root, self.out, [Path("yt_app.py")])
        self.check(arch.CLASSIC_NAME)
