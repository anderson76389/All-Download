"""Publier deux ZIP complets : Portable et Windows Classique (installateur).

Les ZIP incluent les logos, les six dossiers et tous les fichiers suivis par Git
dans Code-source/, sans aucun telechargement personnel ni donnee locale.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import zipfile

MEDIA_DIRS = ("AUDIOS", "AUTRES", "CHAÎNES", "GIFS", "PLAYLIST", "VIDÉOS")
SOURCES = "Code-source"
PORTABLE_NAME = "All-Download-Portable-Windows.zip"
CLASSIC_NAME = "All-Download-Classique-Windows.zip"


def repository_files(root: Path) -> list[Path]:
    output = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z", "--cached"])
    tracked = [Path(path) for path in output.decode("utf-8").split("\0") if path]
    for relative in tracked:
        if not (root / relative).is_file():
            raise FileNotFoundError(f"Fichier Git absent : {relative}")
    return tracked


def add_source(archive: zipfile.ZipFile, root: Path, tracked: list[Path]) -> None:
    for relative in tracked:
        archive.write(root / relative, f"{SOURCES}/{relative.as_posix()}")


def check_zip(zip_path: Path, tracked: list[Path], executable: str) -> None:
    with zipfile.ZipFile(zip_path, "r") as archive:
        broken = archive.testzip()
        if broken:
            raise ValueError(f"ZIP corrompu : {broken}")
        names = set(archive.namelist())
        needed = {executable, "logo.ico", "logo.jpg"}
        needed.update(f"{name}/.gitkeep" for name in MEDIA_DIRS)
        needed.update(f"{SOURCES}/{path.as_posix()}" for path in tracked)
        missing = needed - names
        if missing:
            raise ValueError(f"ZIP incomplet : {sorted(missing)}")
        if zip_path.name == CLASSIC_NAME and "_internal/pythonnet/runtime/Python.Runtime.dll" in names:
            raise ValueError("La version classique ne doit plus inclure pythonnet en dossier !")
    print(f"ZIP valide : {zip_path} ({zip_path.stat().st_size:,} octets)")


def build_portable(root: Path, output: Path, tracked: list[Path]) -> None:
    app = root / "dist" / "All-Download-Portable"
    if not (app / "All_Media_Download.exe").is_file():
        raise FileNotFoundError("L'EXE Portable est absent")
    with zipfile.ZipFile(output / PORTABLE_NAME, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zf:
        for path in sorted(app.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(app).as_posix())
        add_source(zf, root, tracked)
    check_zip(output / PORTABLE_NAME, tracked, "All_Media_Download.exe")


def build_classic(root: Path, output: Path, tracked: list[Path]) -> None:
    setup = root / "dist" / "All-Download-Installer" / "All-Download-Setup.exe"
    if not setup.is_file():
        raise FileNotFoundError(f"Installateur Windows absent : {setup}")
    with zipfile.ZipFile(output / CLASSIC_NAME, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zf:
        zf.write(setup, setup.name)
        zf.write(root / "logo.ico", "logo.ico")
        zf.write(root / "logo.jpg", "logo.jpg")
        for category in MEDIA_DIRS:
            zf.write(root / category / ".gitkeep", f"{category}/.gitkeep")
        zf.writestr("INSTALLATION-WINDOWS.txt",
            "ALL-DOWNLOAD - WINDOWS CLASSIQUE\n\n"
            "1. Lancez All-Download-Setup.exe.\n"
            "2. Choisissez vos raccourcis et terminez l'installation.\n"
            "3. Les medias sont conserves dans votre dossier de telechargement,\n"
            "   et NON dans le dossier du programme.\n"
            "4. L'application peut etre desinstallee depuis Windows.\n\n"
            "L'avertissement de reputation SmartScreen peut subsister tant que\n"
            "le programme n'est pas signe par un editeur reconnu.\n")
        add_source(zf, root, tracked)
    check_zip(output / CLASSIC_NAME, tracked, "All-Download-Setup.exe")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=True)
    tracked = repository_files(root)
    build_portable(root, args.output, tracked)
    build_classic(root, args.output, tracked)


if __name__ == "__main__":
    main()
