"""Essai facultatif d'une vraie VOD Twitch publique avec le Streamlink intégré.

Recherche des URL sur le catalogue PUBLIC de l'émission officielle Twitch.
Aucune connexion, aucun jeton, aucune VOD réservée aux abonnés, aucun contenu
conservé : l'essai lit un court fragment de flux en mémoire puis ferme le flux.
N'est pas une preuve de téléchargement complet (le test HLS/MP4 local l'est).
"""
from __future__ import annotations

import html
import re
import sys
import urllib.request

from streamlink import Streamlink
from twitch_streamlink_engine import select_video_stream

CATALOG_URL = "https://vodarchive.com/vods/twitch"
MAX_BYTES = 64 * 1024


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
        source_stream = None
        try:
            session = Streamlink()
            session.set_option("no-plugin-cache", True)
            session.set_option("stream-timeout", 12)
            session.set_option("http-timeout", 12)
            streams = session.streams(url)
            if not streams:
                print("Public VOD", vod_id, ": no stream")
                continue
            _, candidate = select_video_stream(streams, "360p")
            source_stream = candidate.open()
            head = source_stream.read(MAX_BYTES)
            if len(head) < 188 * 4:
                print("Public VOD", vod_id, ": short read", len(head))
                continue
            print("TWITCH_PUBLIC_SAMPLE=SUCCESS")
            print("Public Twitch VOD:", url)
            print("First streaming bytes read:", len(head), "- content discarded")
            return
        except Exception as exc:
            print("Public VOD", vod_id, "stream access error:", str(exc)[:250])
        finally:
            if source_stream is not None:
                source_stream.close()
    print("TWITCH_PUBLIC_SAMPLE=NO_ACCESSIBLE_PUBLIC_STREAM")
    sys.exit(2)


if __name__ == "__main__":
    main()
