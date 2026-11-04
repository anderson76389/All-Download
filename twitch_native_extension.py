"""Activation locale de Twitch VOD Downloader dans WebView2.

L'extension d'Andre Bradshaw n'est PAS redistribuée. L'utilisateur doit déjà
l'avoir installée dans Chrome. Nous copions ses fichiers (sans les données de
profil, cookies ni identifiants) dans Donnees/Extensions avant chargement.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path

CHROME_EXTENSION_ID = "gaabmdjigfcnkgeommfpnoinpdmpfhaj"
CHROME_PROFILE_DIR = ("Google", "Chrome", "User Data")
MAX_EXTENSION_SIZE = 40 * 1024 * 1024


class NativeExtensionError(Exception):
    pass


def _read_manifest(folder):
    path = Path(folder) / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise NativeExtensionError("Manifest Chrome de l'extension introuvable ou invalide.") from exc
    if not isinstance(data, dict) or data.get("manifest_version") not in (2, 3):
        raise NativeExtensionError("Manifest de l'extension Chrome non pris en charge.")
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)*", str(data.get("version", ""))):
        raise NativeExtensionError("Numéro de version d'extension invalide.")
    return data


def chrome_extension_candidates(localappdata=None):
    root = Path(localappdata or os.environ.get("LOCALAPPDATA") or Path.home()) / Path(*CHROME_PROFILE_DIR)
    if not root.is_dir():
        return []
    candidates = []
    for profile in root.iterdir():
        if not profile.is_dir() or not (
            profile.name == "Default" or profile.name.startswith("Profile ")
        ):
            continue
        location = profile / "Extensions" / CHROME_EXTENSION_ID
        if not location.is_dir():
            continue
        for version in location.iterdir():
            if not version.is_dir() or not (version / "manifest.json").is_file():
                continue
            try:
                manifest = _read_manifest(version)
            except NativeExtensionError:
                continue
            numeric = tuple(int(x) for x in manifest["version"].split("."))
            candidates.append((numeric, str(version), profile.name, manifest["version"]))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [{
        "path": path, "profile": profile, "version": version
    } for _, path, profile, version in candidates]


def native_extension_folder(data_dir):
    return Path(data_dir) / "Extensions" / "TwitchVODDownloader"


def existing_native_extension(data_dir):
    target = native_extension_folder(data_dir)
    if not (target / ".all-download-installed.json").is_file():
        return None
    try:
        data = json.loads((target / ".all-download-installed.json").read_text(encoding="utf-8"))
        manifest = _read_manifest(target)
    except (OSError, ValueError, NativeExtensionError):
        return None
    if data.get("extension_id") != CHROME_EXTENSION_ID:
        return None
    return {"path": str(target), "version": manifest["version"]}


def install_local_chrome_extension(data_dir, source=None, localappdata=None):
    """Installer UNIQUEMENT les fichiers du Chrome local, jamais les cookies."""
    candidates = chrome_extension_candidates(localappdata)
    if source:
        source = str(Path(source).resolve())
        candidate = next((entry for entry in candidates
                          if str(Path(entry["path"]).resolve()) == source), None)
    else:
        candidate = candidates[0] if candidates else None
    if not candidate:
        raise NativeExtensionError(
            "Extension Chrome introuvable. Installez Twitch VOD Downloader "
            "d'Andre Bradshaw dans Chrome, puis relancez cette opération."
        )
    source_dir = Path(candidate["path"])
    target = native_extension_folder(data_dir)
    if target.is_dir():
        old = existing_native_extension(data_dir)
        if old and old["version"] == candidate["version"]:
            return old
        # Ne jamais remplacer des fichiers d'extension utilisés par WebView2.
        raise NativeExtensionError(
            "Une version est déjà intégrée. Désactivez-la et retirez son dossier "
            "avant d'en importer une nouvelle version."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".twitch-vod-", dir=target.parent))
    copied_bytes = 0
    try:
        for root, dirs, files in os.walk(source_dir, followlinks=False):
            relative = Path(root).relative_to(source_dir)
            dirs[:] = [d for d in dirs
                       if d != "_metadata" and not (Path(root) / d).is_symlink()]
            destination = staging / relative
            destination.mkdir(parents=True, exist_ok=True)
            for name in files:
                source_file = Path(root) / name
                if source_file.is_symlink() or name.startswith(".all-download"):
                    continue
                size = source_file.stat().st_size
                copied_bytes += size
                if copied_bytes > MAX_EXTENSION_SIZE:
                    raise NativeExtensionError("Fichiers d'extension trop volumineux.")
                shutil.copy2(source_file, destination / name)
        _read_manifest(staging)
        (staging / ".all-download-installed.json").write_text(
            json.dumps({
                "extension_id": CHROME_EXTENSION_ID,
                "version": candidate["version"],
                "source": "Chrome local",
            }, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        staging.rename(target)
        return {"path": str(target), "version": candidate["version"]}
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
