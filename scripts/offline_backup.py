#!/usr/bin/env python3
"""Offline Git history and optional portable-data backup. Archives are NOT encrypted."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import zipfile

BUNDLE = "sources/all-download.bundle"
MANIFEST = "manifest.json"
CATEGORIES = frozenset(("Donnees", "AUTRES", "AUDIOS", "VIDÉOS", "GIFS",
                        "CHAÎNES", "PLAYLIST", "TWITCH"))
UNNEEDED = frozenset(("cache", "temporaires", "webview", "__pycache__"))
KEY_SUFFIXES = (".p12", ".pfx", ".jks", ".keystore", ".pem", ".key")
CHUNK = 1024 * 1024

class BackupError(ValueError):
    pass

def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()

def digest_zip_member(archive: zipfile.ZipFile, member: str) -> str:
    h = hashlib.sha256()
    with archive.open(member) as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()

def git(repo: Path, *args: str) -> None:
    p = subprocess.run(("git", "-C", str(repo), *args),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       check=False, timeout=120)
    if p.returncode:
        raise BackupError("Git : " + p.stderr.decode("utf-8", "replace")[-600:])

def portable_files(root: Path):
    if not root.is_dir() or root.is_symlink():
        raise BackupError("Le dossier portable est absent ou symbolique.")
    for top in sorted(CATEGORIES):
        folder = root / top
        if not folder.exists():
            continue
        if folder.is_symlink():
            raise BackupError("Dossier symbolique non autorisé : " + top)
        if not folder.is_dir():
            continue
        for base, directories, names in os.walk(folder, followlinks=False):
            current = Path(base)
            for name in list(directories):
                child = current / name
                rel = child.relative_to(root)
                if child.is_symlink():
                    raise BackupError("Lien symbolique non autorisé : " + str(rel))
                if top == "Donnees" and len(rel.parts) == 2 and name.lower() in UNNEEDED:
                    directories.remove(name)
            for name in names:
                file = current / name
                rel = file.relative_to(root)
                if file.is_symlink():
                    raise BackupError("Lien symbolique non autorisé : " + str(rel))
                if not file.is_file() or name.lower().endswith(KEY_SUFFIXES):
                    continue
                yield file, "user-data/" + rel.as_posix()

def make_backup(repo: Path, output: Path, data_root: Path | None = None,
                allow_sensitive: bool = False) -> None:
    repo = repo.resolve()
    output = output.absolute()
    if output.exists() or Path(str(output) + ".sha256").exists():
        raise BackupError("Cette sauvegarde existe déjà : aucun écrasement autorisé.")
    if data_root is not None and not allow_sensitive:
        raise BackupError("Les données peuvent contenir des cookies : ajoutez --accept-unencrypted.")
    if not (repo / ".git").exists():
        raise BackupError("Cloner le dépôt avec Git : archive ZIP GitHub insuffisante.")
    if output.is_relative_to(repo):
        raise BackupError("Placer la sauvegarde hors du dépôt Git.")
    output.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "rev-parse", "--verify", "HEAD")
    with tempfile.TemporaryDirectory(prefix="all-download-backup-", dir=output.parent) as scratch:
        scratch = Path(scratch)
        bundle = scratch / "sources.bundle"
        git(repo, "bundle", "create", str(bundle), "--all")
        members = [(bundle, BUNDLE)]
        if data_root is not None:
            members.extend(portable_files(data_root))
        manifest = {"format": 1, "product": "All-Download", "encrypted": False, "files": []}
        candidate = scratch / "backup.zip"
        with zipfile.ZipFile(candidate, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=4, allowZip64=True) as archive:
            for source, name in members:
                archive.write(source, name)
                manifest["files"].append({"path": name, "size": source.stat().st_size,
                                          "sha256": digest_file(source)})
            archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, sort_keys=True))
        checksum = digest_file(candidate)
        os.replace(candidate, output)
        Path(str(output) + ".sha256").write_text(
            checksum + "  " + output.name + "\n", encoding="ascii")

def _safe_name(name: str) -> bool:
    p = PurePosixPath(name)
    return (not name.startswith("/") and "\\" not in name and
            all(part not in ("", ".", "..") for part in p.parts) and
            (name == BUNDLE or
             (len(p.parts) >= 3 and p.parts[0] == "user-data" and
              p.parts[1] in CATEGORIES)))

def verify_backup(backup: Path) -> dict:
    sidecar = Path(str(backup) + ".sha256")
    if sidecar.is_file():
        expected = sidecar.read_text("ascii").split()
        if len(expected) != 2 or expected[1] != backup.name or expected[0] != digest_file(backup):
            raise BackupError("Empreinte SHA-256 de l'archive incorrecte.")
    with zipfile.ZipFile(backup) as archive:
        entries = archive.infolist()
        names = [item.filename for item in entries]
        if names.count(MANIFEST) != 1 or len(names) != len(set(names)):
            raise BackupError("Manifeste absent ou noms dupliqués.")
        if archive.getinfo(MANIFEST).file_size > 2_000_000:
            raise BackupError("Manifeste trop volumineux.")
        manifest = json.loads(archive.read(MANIFEST))
        if manifest.get("format") != 1 or manifest.get("product") != "All-Download":
            raise BackupError("Format de sauvegarde inconnu.")
        records = manifest.get("files")
        if not isinstance(records, list) or len(records) > 100_000:
            raise BackupError("Liste de fichiers invalide.")
        expected_names = {record.get("path") for record in records if isinstance(record, dict)}
        if not expected_names or BUNDLE not in expected_names or len(expected_names) != len(records):
            raise BackupError("Fichiers du bundle manquants ou dupliqués.")
        if set(names) != expected_names | {MANIFEST}:
            raise BackupError("Fichier inattendu dans l'archive.")
        for record in records:
            name = record["path"]
            if not isinstance(name, str) or not _safe_name(name):
                raise BackupError("Chemin d'archive dangereux.")
            info = archive.getinfo(name)
            if info.is_dir() or ((info.external_attr >> 16) & 0o170000) == 0o120000:
                raise BackupError("Lien symbolique ou répertoire interdit.")
            if not isinstance(record.get("size"), int) or info.file_size != record["size"]:
                raise BackupError("Taille de fichier incorrecte : " + name)
            if digest_zip_member(archive, name) != record.get("sha256"):
                raise BackupError("SHA-256 invalide : " + name)
    return manifest

def restore_backup(backup: Path, destination: Path) -> None:
    verify_backup(backup)
    destination = destination.absolute()
    if destination.exists():
        raise BackupError("Destination déjà présente : récupération sans écrasement uniquement.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="all-download-restore-", dir=destination.parent) as temp:
        bundle = Path(temp) / "source.bundle"
        with zipfile.ZipFile(backup) as archive:
            with archive.open(BUNDLE) as source, bundle.open("wb") as output:
                shutil.copyfileobj(source, output, length=CHUNK)
            p = subprocess.run(("git", "clone", "--quiet", str(bundle), str(destination)),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=120, check=False)
            if p.returncode:
                raise BackupError("Restauration Git impossible : " +
                                  p.stderr.decode("utf-8", "replace")[-500:])
            for item in archive.namelist():
                if not item.startswith("user-data/"):
                    continue
                target = destination / item.removeprefix("user-data/")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, length=CHUNK)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("create")
    create.add_argument("--repository", type=Path, default=Path.cwd())
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--data-root", type=Path)
    create.add_argument("--accept-unencrypted", action="store_true")
    check = sub.add_parser("verify")
    check.add_argument("backup", type=Path)
    restore = sub.add_parser("restore")
    restore.add_argument("backup", type=Path)
    restore.add_argument("--destination", type=Path, required=True)
    a = parser.parse_args()
    try:
        if a.action == "create":
            make_backup(a.repository, a.output, a.data_root, a.accept_unencrypted)
            print("Sauvegarde et SHA-256 créés (non chiffrés) :", a.output)
        elif a.action == "verify":
            print("Sauvegarde vérifiée :", len(verify_backup(a.backup)["files"]), "fichiers")
        else:
            restore_backup(a.backup, a.destination)
            print("Restauration hors ligne réussie :", a.destination)
        return 0
    except (BackupError, OSError, ValueError, subprocess.TimeoutExpired,
            zipfile.BadZipFile) as error:
        parser.exit(1, "Erreur : " + str(error) + "\n")

if __name__ == "__main__":
    raise SystemExit(main())
