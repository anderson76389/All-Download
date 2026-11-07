"""Deno Windows x64 local, facultatif pour yt-dlp/YouTube.

Téléchargement à la demande depuis les releases officielles de denoland/deno.
Pas d'installation globale, pas de dépendance PATH, pas de remplacement des
autres outils. Les erreurs ne doivent jamais bloquer yt-dlp ou Twitch.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import urllib.request
import zipfile

RELEASE_API = "https://api.github.com/repos/denoland/deno/releases/latest"
ARCHIVE_NAME = "deno-x86_64-pc-windows-msvc.zip"
EXE_NAME = "deno.exe"
MAX_ARCHIVE_BYTES = 150 * 1024 * 1024
MAX_EXE_BYTES = 250 * 1024 * 1024
MIN_DENO_VERSION = (2, 3, 0)
_INSTALL_LOCK = threading.RLock()
_VALIDATED = set()


def is_youtube_url(url):
    """Seuls les véritables domaines YouTube déclenchent l'installation."""
    if not isinstance(url, str):
        return False
    try:
        from urllib.parse import urlsplit
        parsed = urlsplit(url.strip())
        host = (parsed.hostname or "").lower()
        return (parsed.scheme in ("https", "http")
                and not parsed.username and not parsed.password
                and (host == "youtube.com" or host.endswith(".youtube.com")
                     or host == "youtu.be" or host.endswith(".youtu.be")
                     or host == "youtube-nocookie.com"
                     or host.endswith(".youtube-nocookie.com")))
    except ValueError:
        return False


def _deno_version(path):
    try:
        proc = subprocess.run(
            [str(path), "--version"], stdin=subprocess.DEVNULL,
            capture_output=True, text=True, errors="replace", timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode != 0:
            return None
        match = re.search(r"(?m)^deno (\d+)\.(\d+)\.(\d+)(?:\s|$)", proc.stdout)
        if not match:
            return None
        return tuple(int(part) for part in match.groups())
    except (subprocess.SubprocessError, OSError, ValueError):
        return None


def _valid_deno(path, validator):
    if not os.path.isfile(path) or not validator(path):
        _VALIDATED.discard(path)
        return False
    if path in _VALIDATED:
        return True
    version = _deno_version(path)
    if version is None or version < MIN_DENO_VERSION:
        return False
    _VALIDATED.add(path)
    return True


def _release_asset():
    request = urllib.request.Request(RELEASE_API, headers={
        "User-Agent": "All-Download-Deno",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Réponse GitHub Deno trop volumineuse.")
    data = json.loads(raw)
    for item in data.get("assets", []):
        if item.get("name") != ARCHIVE_NAME:
            continue
        url = item.get("browser_download_url")
        size = item.get("size")
        digest = item.get("digest")
        if (isinstance(url, str)
                and url.startswith("https://github.com/denoland/deno/releases/download/")
                and url.endswith("/" + ARCHIVE_NAME)
                and isinstance(size, int) and 0 < size <= MAX_ARCHIVE_BYTES
                and isinstance(digest, str)
                and re.fullmatch(r"sha256:[a-fA-F0-9]{64}", digest)):
            return url, size, digest[7:].lower()
    raise ValueError("Archive Deno Windows x64 officielle vérifiable introuvable.")


def ensure_deno_ready(bin_dir, validator):
    """Retourne (disponible, raison), en conservant l'ancien EXE intact."""
    target = os.path.join(bin_dir, EXE_NAME)
    if _valid_deno(target, validator):
        return True, ""
    with _INSTALL_LOCK:
        if _valid_deno(target, validator):
            return True, ""
        archive_path = target + ".zip.part"
        temporary = target + ".tmp"
        try:
            os.makedirs(bin_dir, exist_ok=True)
            url, size, expected_hash = _release_asset()
            actual_hash = hashlib.sha256()
            size_read = 0
            request = urllib.request.Request(url, headers={
                "User-Agent": "All-Download-Deno"
            })
            with urllib.request.urlopen(request, timeout=90) as response, \
                    open(archive_path, "wb") as output:
                while True:
                    data = response.read(1024 * 1024)
                    if not data:
                        break
                    size_read += len(data)
                    if size_read > MAX_ARCHIVE_BYTES or size_read > size:
                        raise ValueError("Archive Deno trop volumineuse.")
                    actual_hash.update(data)
                    output.write(data)
            if size_read != size:
                raise ValueError("Archive Deno incomplète.")
            if actual_hash.hexdigest() != expected_hash:
                raise ValueError("Empreinte SHA-256 Deno incorrecte.")
            with zipfile.ZipFile(archive_path) as archive:
                matches = [
                    entry for entry in archive.infolist()
                    if not entry.is_dir() and entry.filename == EXE_NAME
                ]
                if (len(matches) != 1 or
                        not 65536 <= matches[0].file_size <= MAX_EXE_BYTES):
                    raise ValueError("deno.exe Windows x64 absent ou invalide.")
                with archive.open(matches[0]) as source, open(temporary, "wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
            if not _valid_deno(temporary, validator):
                raise ValueError("Deno téléchargé invalide ou version trop ancienne.")
            os.replace(temporary, target)
            _VALIDATED.discard(temporary)
            _VALIDATED.add(target)
            return True, ""
        except Exception as exc:
            return False, str(exc)[:210] or "Installation de Deno impossible."
        finally:
            _VALIDATED.discard(temporary)
            for path in (archive_path, temporary):
                try:
                    os.remove(path)
                except (FileNotFoundError, OSError):
                    pass


def yt_dlp_args(bin_dir, validator):
    """Options yt-dlp uniquement si Deno Windows est bien validé."""
    ready, _ = ensure_deno_ready(bin_dir, validator)
    if not ready:
        return []
    return ["--js-runtimes", "deno:" + os.path.join(bin_dir, EXE_NAME)]
