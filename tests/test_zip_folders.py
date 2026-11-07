"""Les ZIP doivent transporter sept vrais dossiers vides, sans .gitkeep."""
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
        # Reproduire les deux-octets MZ installes par erreur dans la Build 151.
        # Meme s'ils sont present dans dist avant l'archivage, le nouveau ZIP
        # ne doit jamais contenir les outils et donnees du runner.
        for tool in ("yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe"):
            test_tool = portable / "Donnees" / "bin" / tool
            test_tool.parent.mkdir(parents=True, exist_ok=True)
            test_tool.write_bytes(b"MZ")
        (portable / "Donnees" / "startup_log.txt").write_text("test only")
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
                    entry = f"{arch.PORTABLE_ROOT}/{cat}/"
                    self.assertIn(entry, files)
                    self.assertTrue(z.getinfo(entry).is_dir())
                else:
                    self.assertNotIn(cat + "/", files)
            self.assertFalse(any(".gitkeep" in entry for entry in files))
            if name == arch.PORTABLE_NAME:
                prefix = arch.PORTABLE_ROOT + "/"
                self.assertTrue(all(entry.startswith(prefix) for entry in files))
                self.assertTrue(z.getinfo(prefix + "Donnees/").is_dir())
                self.assertTrue(z.getinfo(prefix + "Donnees/bin/").is_dir())
                self.assertFalse(any(entry.startswith(prefix + "Donnees/")
                                     and entry not in (prefix + "Donnees/", prefix + "Donnees/bin/")
                                     for entry in files))
                self.assertIn(prefix + "All_Media_Download.exe", files)
                self.assertIn(prefix + "Code-source/yt_app.py", files)
            else:
                self.assertFalse(any(entry.startswith(("Donnees/", "bin/")) for entry in files))
                self.assertIn("Code-source/yt_app.py", files)

    def test_portable(self):
        arch.build_portable(self.root, self.out, [Path("yt_app.py")])
        self.check(arch.PORTABLE_NAME)
        # Une extraction dans n'importe quel répertoire ne doit jamais
        # disperser l'EXE, les catégories ou les données à sa racine.
        destination = self.root / "Extraction"
        with zipfile.ZipFile(self.out / arch.PORTABLE_NAME) as archive:
            archive.extractall(destination)
        self.assertEqual([entry.name for entry in destination.iterdir()],
                         [arch.PORTABLE_ROOT])
        inside = destination / arch.PORTABLE_ROOT
        self.assertTrue((inside / "All_Media_Download.exe").is_file())
        self.assertTrue((inside / "Donnees" / "bin").is_dir())
        for category in arch.MEDIA_DIRS:
            self.assertTrue((inside / category).is_dir())

    def test_classic(self):
        arch.build_classic(self.root, self.out, [Path("yt_app.py")])
        self.check(arch.CLASSIC_NAME)
