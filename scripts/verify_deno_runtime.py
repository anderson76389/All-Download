"""Installer et exécuter le VRAI Deno Windows x64 dans un dossier temporaire.

Test GitHub Actions distinct des tests unitaires : pas d'EXE factice, aucun
outil ajouté au dépôt, ni au ZIP Portable/Classique, ni aux données personnelles.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import re
import subprocess

import yt_app


def main():
    with TemporaryDirectory(prefix="all-download-deno-reel-") as temporary:
        executable = Path(temporary) / "deno.exe"
        with patch.object(yt_app, "DENO_PATH", str(executable)):
            if not yt_app.ensure_deno_ready():
                raise RuntimeError("Impossible d'installer le vrai Deno depuis la Release officielle.")
            result = subprocess.run(
                [str(executable), "--version"], capture_output=True,
                text=True, check=True, timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            match = re.search(r"(?m)^deno (\d+)\.(\d+)\.(\d+)", result.stdout)
            if not match or tuple(map(int, match.groups())) < (2, 3, 0):
                raise RuntimeError("Version Deno incompatible : " + repr(result.stdout))
            print("SUCCÈS DENO WINDOWS X64 :", result.stdout.splitlines()[0])
            print("EXE téléchargé et vérifié :", executable.stat().st_size, "octets")
            print("Installation uniquement temporaire ; aucune Release publiée.")


if __name__ == "__main__":
    main()
