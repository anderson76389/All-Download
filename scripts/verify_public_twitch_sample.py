"""Essai facultatif du VRAI téléchargement All-Download d'une VOD Twitch publique.

Depuis la liste de VOD de la chaîne Twitch officielle, recherche une diffusion
publiquement accessible. Utilise directement la fonction de téléchargement du
logiciel pour récupérer un bref extrait (>=512 KiB) dans AUTRES, puis l'annule.
Le test vérifie que le moteur reçoit des octets et ne laisse pas de fichier
partiel. Aucune copie tierce n'est conservée. Le test de la vidéo complète
HLS/MP4 utilise une œuvre de test originale distincte.
"""
from __future__ import annotations

import html
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

from twitch_streamlink_engine import (
    TwitchEngineCancelled,
    download_twitch_vod,
)

CATALOG_URL = "https://vodarchive.com/vods/twitch"
MIN_BYTES = 512 * 1024


def main():
    try:
        req = urllib.request.Request(CATALOG_URL, headers={
            "User-Agent": "Mozilla/5.0 (All-Download non-commercial quality check)",
            "Accept": "text/html",
        })
        with urllib.request.urlopen(req, timeout=12) as response:
            source = html.unescape(response.read(2 * 1024 * 1024).decode("utf-8", "replace"))
    except Exception as exc:
        print("TWITCH_PUBLIC_SAMPLE=LISTING_UNAVAILABLE", str(exc)[:180])
        sys.exit(2)

    ids = list(dict.fromkeys(
        re.findall(r"(?:www\.)?twitch\.tv/videos/(\d{8,15})", source, flags=re.I)
    ))[:4]
    if not ids:
        print("TWITCH_PUBLIC_SAMPLE=NO_VERIFIED_VIDEO_IDS_IN_LISTING")
        sys.exit(2)

    print("VOD Twitch candidates from public listing:", ids)
    for vod_id in ids:
        url = f"https://www.twitch.tv/videos/{vod_id}"
        transferred = [0]

        def progress(size):
            transferred[0] = max(transferred[0], size)

        def cancelled():
            # Dès qu'un court extrait a été réellement écrit, demander l'annulation.
            return transferred[0] >= MIN_BYTES

        try:
            with tempfile.TemporaryDirectory(prefix="all-download-twitch-public-smoke-") as folder:
                try:
                    result = download_twitch_vod(
                        url,
                        folder,
                        quality="360p",
                        progress=progress,
                        cancelled=cancelled,
                        ffmpeg_path=None,
                    )
                except TwitchEngineCancelled:
                    if transferred[0] < MIN_BYTES:
                        raise RuntimeError("Annulé avant de recevoir le fragment demandé.")
                    target_dir = Path(folder) / "AUTRES"
                    assert target_dir.is_dir(), "Répertoire AUTRES non créé."
                    assert not list(target_dir.iterdir()), (
                        "Un téléchargement interrompu a laissé un fichier sur le disque."
                    )
                    print("TWITCH_PUBLIC_ENGINE_DOWNLOAD=SUCCESS")
                    print("Public VOD:", url)
                    print("Written before cleanup:", transferred[0], "bytes")
                    print("Cancelled and cleaned without residue: yes")
                    return
                else:
                    result = Path(result)
                    if transferred[0] >= MIN_BYTES and result.is_file():
                        print("TWITCH_PUBLIC_ENGINE_DOWNLOAD=SUCCESS_COMPLETE")
                        print("Public VOD:", url, "bytes:", result.stat().st_size)
                        return
                    raise RuntimeError("VOD terminée sans taille vidéo suffisante.")
        except Exception as exc:
            print("Public VOD", vod_id, "failed:", str(exc)[:320])
    print("TWITCH_PUBLIC_ENGINE_DOWNLOAD=NO_ACCESSIBLE_PUBLIC_STREAM")
    sys.exit(2)


if __name__ == "__main__":
    main()
