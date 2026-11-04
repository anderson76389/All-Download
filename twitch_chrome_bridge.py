"""Pont local Chrome -> All-Download pour les fichiers produits par une extension.

L'extension existante effectue elle-même le téléchargement ; aucun token Chrome,
service privé, ni contrôle d'accès Twitch ne sont copié ou contourné.
La surveillance est ponctuelle et volontaire, à partir de l'instant de la demande.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

VIDEO_EXTENSIONS = frozenset((".mp4", ".mkv", ".ts", ".webm", ".mov", ".m4v"))
INCOMPLETE_EXTENSIONS = frozenset((".crdownload", ".part", ".tmp", ".download"))
MAX_FILE_BYTES = 100 * 1024**3


class ChromeBridgeError(Exception):
    pass


def default_chrome_download_folder():
    """Par défaut Chrome utilise le dossier Téléchargements du compte Windows."""
    return str(Path.home() / "Downloads")


def _scan_files(folder):
    """Lister seulement les fichiers vidéos directs et non les liens symboliques."""
    result = {}
    with os.scandir(folder) as entries:
        for item in entries:
            try:
                if not item.is_file(follow_symlinks=False):
                    continue
                if Path(item.name).suffix.lower() not in VIDEO_EXTENSIONS:
                    continue
                stat = item.stat(follow_symlinks=False)
                if 0 < stat.st_size <= MAX_FILE_BYTES:
                    result[item.name] = (stat.st_size, stat.st_mtime_ns)
            except (OSError, ValueError):
                continue
    return result


def snapshot_downloads(folder):
    path = Path(folder)
    if not path.is_dir():
        raise ChromeBridgeError(
            "Dossier de téléchargements Chrome introuvable. Choisissez son emplacement."
        )
    return _scan_files(path)


def monitor_chrome_downloads(
    folder, baseline, on_video, *,
    cancelled=None, poll_seconds=1.5, max_seconds=5400,
    stable_polls=3, now=None, sleep=None,
):
    """Informer pour chaque nouvelle vidéo Chrome terminée (pas les .crdownload).

    Le callback reçoit un chemin, ne renvoie jamais son contenu au navigateur.
    Une création et une modification d'un fichier existant sont prises en compte,
    mais jamais un média inchangé depuis le début de la surveillance.
    """
    path = Path(folder)
    if not path.is_dir():
        raise ChromeBridgeError("Dossier Chrome inaccessible.")
    now = now or time.monotonic
    sleep = sleep or time.sleep
    started_at = now()
    witnessed = {}
    completed = set()
    count = 0
    while now() - started_at < max_seconds:
        if cancelled and cancelled():
            return count
        try:
            current = _scan_files(path)
            incomplete = {e.name.lower() for e in os.scandir(path)
                          if Path(e.name).suffix.lower() in INCOMPLETE_EXTENSIONS}
        except OSError as exc:
            raise ChromeBridgeError("Dossier Chrome devenu inaccessible : " + str(exc)) from exc
        for name, signature in sorted(current.items(), key=lambda kv: kv[1][1]):
            if cancelled and cancelled():
                return count
            if baseline.get(name) == signature or (name, signature) in completed:
                continue
            size, modified = signature
            last = witnessed.get(name)
            # Le navigateur peut créer le fichier final avant d'avoir fini
            # d'écrire : sa taille et sa date doivent être STABLES.
            stable_count = (last[1] + 1) if last and last[0] == signature else 1
            witnessed[name] = (signature, stable_count)
            if stable_count < stable_polls:
                continue
            if (name + ".crdownload").lower() in incomplete:
                continue
            source = path / name
            try:
                if source.is_symlink() or not source.is_file():
                    continue
                if source.stat().st_size != size:
                    continue
                on_video(str(source))
                completed.add((name, signature))
                baseline[name] = signature
                count += 1
            except FileNotFoundError:
                continue
        sleep(poll_seconds)
    return count
