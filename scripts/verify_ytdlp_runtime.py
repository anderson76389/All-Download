"""Test Windows d'un VRAI yt-dlp telecharge, sans aucun binaire factice.

Ne rien copier dans dist/, ni Donnees/ des archives : l'outil n'est utilise
que dans un repertoire temporaire du runner puis supprime.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

import yt_app


def main():
    with tempfile.TemporaryDirectory(prefix="all-download-real-ytdlp-") as tmp:
        executable = Path(tmp) / "yt-dlp.exe"
        if not yt_app.safe_download_file(yt_app.YTDLP_URL, str(executable)):
            raise RuntimeError("Telechargement du vrai yt-dlp.exe impossible")
        if not yt_app.is_valid_windows_executable(str(executable)):
            raise RuntimeError("yt-dlp.exe telecharge n'est pas un executable PE x64 valide")
        info = subprocess.run(
            [str(executable), "--version"], capture_output=True,
            text=True, timeout=45, check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        version = info.stdout.strip()
        if not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}(?:[.\w-]*)?", version):
            raise RuntimeError("yt-dlp --version n'a pas retourne une version : " + repr(version))
        print("SUCCES REEL : yt-dlp Windows x64 execute --version ->", version)
        print("Taille de l'EXE valide:", os.path.getsize(executable), "octets")
        print("Le vrai outil a ete teste hors des ZIP et sans toucher aux medias")


if __name__ == "__main__":
    main()
