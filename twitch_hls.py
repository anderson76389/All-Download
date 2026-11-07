"""Secours HLS Twitch sans compte, indépendant du CLI et de voddownloader.com.

Seules les métadonnées et les playlists servies sans authentification par Twitch
et son CDN officiel sont interrogées. Aucun cookie, token ni serveur tiers privé.
Les mécanismes HLS ont été réimplémentés après l'analyse de l'extension Chrome
Twitch VOD Downloader 3.26 transmise par le propriétaire du projet.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from twitch_vod import twitch_vod_id, selected_quality_to_cli

GQL_URL = "https://gql.twitch.tv/gql"
PUBLIC_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
DEFAULT_QUALITIES = ("chunked", "1080p60", "720p60", "720p30", "480p30", "360p30", "160p30")
STORYBOARD = re.compile(r"^/([A-Za-z0-9]{20}_[A-Za-z0-9_]+_\d+_\d+)/storyboards(?:/|$)")


class HLSUnavailable(ValueError):
    """Absence de flux HLS librement accessible ou réponse inattendue."""


def is_twitch_cdn(url):
    try:
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").lower()
        return (parsed.scheme == "https" and parsed.username is None
                and parsed.password is None and parsed.port in (None, 443)
                and host.endswith(".cloudfront.net") and host != ".cloudfront.net"
                and parsed.fragment == "")
    except ValueError:
        return False


def metadata_for_vod(vod_id, timeout=18):
    """Métadonnées publiques; pas de réutilisation des tokens du navigateur."""
    data = {
        "query": "query($id: ID!) { video(id:$id) { id title seekPreviewsURL owner { login } } }",
        "variables": {"id": str(vod_id)}
    }
    request = urllib.request.Request(
        GQL_URL, data=json.dumps(data).encode("utf-8"), method="POST",
        headers={
            "Client-Id": PUBLIC_CLIENT_ID,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://www.twitch.tv",
        }
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(512_001)
        if len(body) > 512_000:
            raise HLSUnavailable("Réponse Twitch trop volumineuse.")
        obj = json.loads(body)
        video = (obj.get("data") or {}).get("video")
        if not isinstance(video, dict):
            raise HLSUnavailable("Aucune métadonnée de VOD accessible.")
        return video
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        if isinstance(exc, HLSUnavailable):
            raise
        raise HLSUnavailable("Métadonnées Twitch indisponibles : " + str(exc)[:160]) from exc


def manifest_candidates(preview_url, quality):
    if not isinstance(preview_url, str) or not is_twitch_cdn(preview_url):
        raise HLSUnavailable("URL de storyboard Twitch absente ou non reconnue.")
    parsed = urllib.parse.urlsplit(preview_url)
    match = STORYBOARD.match(parsed.path)
    if not match:
        raise HLSUnavailable("Format des aperçus de cette VOD non compatible.")
    selected = selected_quality_to_cli(quality)
    # La résolution demandée est prioritaire, sans perdre la source automatique.
    qualities = ((selected,) + tuple(q for q in DEFAULT_QUALITIES if q != selected)
                 if selected else DEFAULT_QUALITIES)
    return [(q, urllib.parse.urlunsplit(
        ("https", parsed.netloc, "/" + match.group(1) + "/" + q + "/index-dvr.m3u8", "", "")
    )) for q in qualities]


def read_public_manifest(url, timeout=12):
    if not is_twitch_cdn(url):
        raise HLSUnavailable("Domaine CDN non autorisé.")
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0",
                      "Accept": "application/vnd.apple.mpegurl, */*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if not is_twitch_cdn(response.url):
            raise HLSUnavailable("Redirection hors du CDN Twitch.")
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise HLSUnavailable("Manifest HLS trop volumineux.")
    text = body.decode("utf-8-sig", errors="replace")
    if not text.startswith("#EXTM3U"):
        raise HLSUnavailable("Le CDN n'a pas retourné une playlist HLS.")
    durations = []
    for line in text.splitlines():
        if line.startswith("#EXTINF:"):
            try:
                durations.append(float(line.split(":", 1)[1].split(",", 1)[0]))
            except (IndexError, ValueError):
                continue
    if not durations:
        raise HLSUnavailable("Manifest sans segments vidéo.")
    return len(durations), sum(durations)


def resolve_hls(url, quality="Meilleure qualité (Auto)", timeout=12):
    """(manifest_url, nom_qualité, durée, nombre_segments); aucune vidéo téléchargée."""
    vod_id = twitch_vod_id(url)
    if not vod_id:
        raise HLSUnavailable("URL Twitch VOD invalide.")
    meta = metadata_for_vod(vod_id)
    preview = meta.get("seekPreviewsURL")
    if not preview:
        raise HLSUnavailable("Twitch ne fournit pas de storyboard pour cette VOD.")
    failures = []
    for name, candidate in manifest_candidates(preview, quality):
        try:
            count, duration = read_public_manifest(candidate, timeout=timeout)
            return candidate, name, duration, count
        except (HLSUnavailable, urllib.error.URLError, TimeoutError, OSError) as exc:
            failures.append(f"{name}: {str(exc)[:65]}")
    raise HLSUnavailable("Aucun flux HLS accessible : " + "; ".join(failures[:2]))


def media_paths(target_dir, url, title):
    """Un fichier temporaire aléatoire puis un MP4 final sans écrasement."""
    vod_id = twitch_vod_id(url)
    if not vod_id:
        raise HLSUnavailable("URL Twitch VOD invalide.")
    safe = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "_", str(title or "VOD Twitch")).strip(" .")
    safe = (safe[:85].rstrip(" .") or "VOD Twitch")
    directory = Path(target_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"Twitch_{vod_id}_{safe}"
    filename = directory / (stem + ".mp4")
    for attempt in range(2, 1000):
        if not filename.exists():
            break
        filename = directory / f"{stem} ({attempt}).mp4"
    else:
        raise HLSUnavailable("Trop de fichiers portant ce nom.")
    temp = directory / f".{stem}.{uuid.uuid4().hex}.part.mp4"
    return temp, filename


def ffmpeg_command(ffmpeg_path, manifest_url, temp_path):
    if not is_twitch_cdn(manifest_url):
        raise HLSUnavailable("URL de playlist Twitch non autorisée.")
    return [
        str(ffmpeg_path), "-nostdin", "-hide_banner", "-loglevel", "warning",
        "-progress", "pipe:1", "-i", manifest_url,
        "-map", "0:v:0", "-map", "0:a?", "-c", "copy",
        "-movflags", "+faststart", "-n", str(temp_path),
    ]


def progress_from_ffmpeg(line, duration):
    if not isinstance(line, str) or duration <= 0:
        return None
    match = re.fullmatch(r"out_time_(?:ms|us)=(\d+)", line.strip())
    if not match:
        return None
    return max(0, min(99, int(int(match.group(1)) / (duration * 1_000_000) * 100)))
