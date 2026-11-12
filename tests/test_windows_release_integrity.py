"""Offline checks for Windows release ZIP integrity contract."""
from pathlib import Path
import hashlib
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "build-windows.yml"
ARCHIVES = (
    "All-Download-Portable-Windows.zip",
    "All-Download-Classique-Windows.zip",
)


class WindowsReleaseIntegrityTests(unittest.TestCase):
    def test_workflow_hashes_and_publishes_both_windows_archives(self):
        content = WORKFLOW.read_text("utf-8")
        self.assertIn("Get-FileHash -Algorithm SHA256", content)
        self.assertIn('gh release create $tag $portable "$portable.sha256" $classic "$classic.sha256"', content)
        for archive in ARCHIVES:
            self.assertIn(archive, content)
            self.assertIn(archive + ".sha256", content)
        self.assertIn("Impossible de verifier les quatre assets Windows", content)

    def test_sha256_sidecar_format_supports_file_integrity_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ARCHIVES[0]
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("All-Download/media.txt", "untouched user media")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            sidecar = Path(str(path) + ".sha256")
            sidecar.write_text(f"{digest}  {path.name}\n", encoding="ascii")
            expected, name = sidecar.read_text("ascii").split()
            self.assertEqual(path.name, name)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
            with path.open("ab") as out:
                out.write(b"tampering")
            self.assertNotEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
