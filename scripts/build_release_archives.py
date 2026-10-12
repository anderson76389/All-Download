"""Construire les ZIP Windows complets pour les GitHub Releases.

Chaque ZIP contient l'application prête à exécuter à la racine, les six dossiers
de médias, les logos et une copie de TOUS les fichiers suivis par Git
(dans Code-source/). Aucun fichier non suivi ou personnel n'est inclus.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import zipfile


MEDIA_DIRS = ("AUDIOS", "AUTRES", "CHAÎNES", "GIFS", "PLAYLIST", "VIDÉOS")
SOURCE_NAME = "Code-source"


def repository_files(repository: Path) -> list[Path]:
    raw = subprocess.check_output(
        ["git", "-C", str(repository), "ls-files", "-z", "--cached"]
    )
    paths = [Path(p) for p in raw.decode("utf-8").split("\0") if p]
    for path in paths:
        if not (repository / path).is_file():
            raise FileNotFoundError(f"Fichier suivi introuvable : {path}")
    return paths


def build_archive(
    repository: Path, runtime: Path, output: Path, tracked: list[Path]
) -> None:
    if not (runtime / "All_Media_Download.exe").is_file():
        raise FileNotFoundError(f"EXE absent : {runtime}")
    if not (runtime / "logo.ico").is_file() or not (runtime / "logo.jpg").is_file():
        raise FileNotFoundError("Un logo manque dans la distribution")
    for name in MEDIA_DIRS:
        if not (runtime / name).is_dir():
            raise FileNotFoundError(f"Dossier de téléchargement absent : {name}")

    output.parent.mkdir(parents=True, exist_ok=True)
    # Zip64 permet aussi de conserver les distributions Windows importantes.
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED,
        compresslevel=6, allowZip64=True
    ) as archive:
        files = sorted(
            (p for p in runtime.rglob("*") if p.is_file()),
            key=lambda p: p.relative_to(runtime).as_posix()
        )
        for path in files:
            archive.write(path, path.relative_to(runtime).as_posix())
        for tracked_path in tracked:
            archive.write(
                repository / tracked_path,
                f"{SOURCE_NAME}/{tracked_path.as_posix()}"
            )

    with zipfile.ZipFile(output, "r") as archive:
        corrupted = archive.testzip()
        if corrupted:
            raise ValueError(f"Fichier ZIP corrompu : {corrupted}")
        names = set(archive.namelist())
        expected = {
            "All_Media_Download.exe",
            "logo.ico", "logo.jpg",
            "Code-source/yt_app.py",
            "Code-source/README.md",
            "Code-source/.github/workflows/build-windows.yml",
            "Code-source/All_Media_Download.spec",
            "Code-source/All_Media_Download-Portable.spec",
        }
        expected.update(f"{d}/.gitkeep" for d in MEDIA_DIRS)
        expected.update(f"{SOURCE_NAME}/{p.as_posix()}" for p in tracked)
        missing = expected - names
        if missing:
            raise ValueError(f"Fichiers manquants dans {output}: {sorted(missing)}")
    print(f"ZIP vérifié : {output.name} ({output.stat().st_size:,} octets)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    tracked = repository_files(root)
    build_archive(
        root, root / "dist/All-Download-Portable",
        args.output / "All-Download-Portable-Windows.zip", tracked
    )
    build_archive(
        root, root / "dist/All_Media_Download",
        args.output / "All-Download-Classique-Windows.zip", tracked
    )


if __name__ == "__main__":
    main()
