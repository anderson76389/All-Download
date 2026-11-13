"""Prevent publishing Windows 1.0 under an updater-incompatible tag."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class StableWindowsReleaseContractTests(unittest.TestCase):
    def test_windows_release_stays_latest_and_preserves_both_packages(self):
        workflow = (ROOT / ".github/workflows/build-windows.yml").read_text("utf-8")
        self.assertIn('$tag = "build-$env:GITHUB_RUN_NUMBER"', workflow)
        self.assertIn("All-Download Windows 1.0 stable", workflow)
        self.assertIn("--latest", workflow)
        self.assertIn("All-Download-Portable-Windows.zip.sha256", workflow)
        self.assertIn("All-Download-Classique-Windows.zip.sha256", workflow)
        self.assertIn("All-Download-Portable-Windows.zip", workflow)
        self.assertIn("All-Download-Classique-Windows.zip", workflow)

    def test_stable_build_keeps_user_media_and_portable_storage(self):
        workflow = (ROOT / ".github/workflows/build-windows.yml").read_text("utf-8")
        self.assertIn("Tester le routage et la preservation des medias", workflow)
        self.assertIn("Verifier obligatoirement 12 demarrages Windows reactifs", workflow)
        self.assertIn("Installer la version classique sur Windows", workflow)
        self.assertIn("Test CI obligatoire", workflow)

if __name__ == "__main__":
    unittest.main()
