"""Moteur Twitch VOD alternatif, indépendant de yt-dlp.

Utilise l'API publique de Streamlink, directement embarquée dans All-Download.
N'accède qu'aux flux rendus disponibles au client et ne contourne aucun contrôle
d'accès. Les fichiers sont produits dans AUTRES et ne remplacent aucun original.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import urllib.parse
from pathlib import Path

VIDEO_URL = re.compile(r"^/(?:videos/|[^/]+/v/)(\d{7,15})/?$", re.I)
MAX_VIDEO_BYTES = 100 * 1024 ** 3


class TwitchEngineError(Exception):
    """Erreur du moteur alternatif présentable dans la barre d'état."""


class TwitchEngineCancelled(TwitchEngineError):
    """Téléchargement interrompu par l'utilisateur."""


def parse_twitch_vod_id(url):
    try:
        parsed = urllib.parse.urlsplit(str(url))
        if parsed.scheme not in ("https", "http"):
            return None
        if (parsed.hostname or "").lower() not in ("twitch.tv", "www.twitch.tv", "m.twitch.tv"):
            return None
        match = VIDEO_URL.fullmatch(parsed.path)
        return match.group(1) if match else None
    except (TypeError, ValueError):
        return None


def select_video_stream(streams, quality="best"):
    """Choisir le meilleur HLS disponible, ou une résolution au plus proche."""
    if not streams:
        raise TwitchEngineError("Streamlink : aucun flux vidéo accessible pour cette VOD.")
    if quality in (None, "", "best", "Meilleure qualité (Auto)"):
        if "best" in streams:
            return "best", streams["best"]
    match = re.search(r"(\d{3,4})p", str(quality), re.I)
    if match:
        limit = int(match.group(1))
        ranked = []
        for name, stream in streams.items():
            res = re.fullmatch(r"(\d{3,4})p(?:\d{2,3})?", str(name))
            if res:
                height = int(res.group(1))
                if height <= limit:
                    ranked.append((height, name, stream))
        if ranked:
            ranked.sort(key=lambda v: (v[0], v[1]))
            _, name, stream = ranked[-1]
            return name, stream
    if "best" in streams:
        return "best", streams["best"]
    for name, stream in streams.items():
        if not str(name).endswith("_alt") and name != "audio_only":
            return name, stream
    raise TwitchEngineError("Streamlink : aucune qualité vidéo disponible.")


def _unused_target(folder, base_name, suffix):
    folder = Path(folder)
    for n in range(10000):
        stem = base_name if not n else f"{base_name} ({n})"
        final = folder / (stem + suffix)
        part = folder / (stem + suffix + ".part")
        if final.exists():
            continue
        try:
            filehandle = part.open("xb")
            return final, part, filehandle
        except FileExistsError:
            continue
    raise TwitchEngineError("Aucun nom de fichier libre dans AUTRES.")


def _remux_mp4(source_ts, ffmpeg_path, cancelled=None):
    """Remux sans perte, facultatif. Conserver le .ts si FFmpeg échoue."""
    if not ffmpeg_path or not os.path.isfile(ffmpeg_path):
        return source_ts
    target = source_ts.with_suffix(".mp4")
    for n in range(10000):
        candidate = (target if not n else
                     source_ts.with_name(source_ts.stem + f" ({n}).mp4"))
        part = Path(str(candidate) + ".part")
        if not candidate.exists() and not part.exists():
            target = candidate
            break
    else:
        return source_ts
    command = [
        ffmpeg_path, "-hide_banner", "-loglevel", "error", "-nostdin",
        "-i", str(source_ts), "-map", "0", "-c", "copy",
        "-movflags", "+faststart", "-f", "mp4", str(part),
    ]
    process = None
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        # Ne jamais laisser une conversion bloquer l'arrêt de l'application.
        def watcher():
            if cancelled and cancelled() and process.poll() is None:
                process.terminate()
        while process.poll() is None:
            threading.Event().wait(0.15)
            watcher()
        process.communicate(timeout=10)
        if process.returncode == 0 and part.is_file() and part.stat().st_size > 0:
            if target.exists():
                return source_ts
            os.rename(part, target)
            source_ts.unlink()
            return target
        return source_ts
    except (OSError, subprocess.SubprocessError):
        return source_ts
    finally:
        try:
            part.unlink(missing_ok=True)
        except OSError:
            pass


def download_twitch_vod(
    url, destination_root, *,
    quality="best", progress=None, cancelled=None, paused=None,
    ffmpeg_path=None, session_factory=None,
):
    """Télécharger une VOD accessible directement dans AUTRES.

    Retourne le chemin effectif du média une fois toutes les écritures terminées.
    session_factory permet des tests locaux sans appel réseau.
    """
    vod_id = parse_twitch_vod_id(url)
    if not vod_id:
        raise TwitchEngineError("Ce moteur accepte uniquement une URL de VOD Twitch.")
    if cancelled and cancelled():
        raise TwitchEngineCancelled("Téléchargement annulé.")
    if session_factory is None:
        try:
            from streamlink import Streamlink
        except ImportError as exc:
            raise TwitchEngineError(
                "Streamlink n'est pas inclus dans cette édition. Utilisez la version Windows actualisée."
            ) from exc
        session_factory = Streamlink

    session = session_factory()
    try:
        session.set_option("no-plugin-cache", True)
        session.set_option("stream-segment-attempts", 5)
        session.set_option("stream-segment-threads", 3)
        session.set_option("stream-timeout", 45)
        if ffmpeg_path and os.path.isfile(ffmpeg_path):
            session.set_option("ffmpeg-ffmpeg", ffmpeg_path)
        streams = session.streams(url)
        selected, stream = select_video_stream(streams, quality)
    except TwitchEngineError:
        raise
    except Exception as exc:
        raise TwitchEngineError(
            "Streamlink ne peut pas accéder à cette VOD Twitch : " + str(exc)[:400]
        ) from exc

    folder = Path(destination_root) / "AUTRES"
    folder.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(folder).free < 64 * 1024 ** 2:
        raise TwitchEngineError("Espace disque insuffisant pour enregistrer la VOD.")
    base_name = f"Twitch_VOD_{vod_id}_Streamlink_{re.sub(r'[^A-Za-z0-9_-]', '', selected)}"
    final, part, output = _unused_target(folder, base_name, ".ts")
    source = None
    written = 0
    try:
        with output:
            source = stream.open()
            while True:
                if cancelled and cancelled():
                    raise TwitchEngineCancelled("Téléchargement annulé.")
                while paused and paused():
                    if cancelled and cancelled():
                        raise TwitchEngineCancelled("Téléchargement annulé.")
                    threading.Event().wait(0.2)
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_VIDEO_BYTES:
                    raise TwitchEngineError("Téléchargement interrompu : taille limite dépassée.")
                output.write(chunk)
                if progress:
                    progress(written)
        if not written:
            raise TwitchEngineError("Streamlink n'a reçu aucune donnée vidéo.")
        if cancelled and cancelled():
            raise TwitchEngineCancelled("Téléchargement annulé.")
        if final.exists():
            raise TwitchEngineError("Un fichier du même nom est apparu pendant le téléchargement.")
        os.rename(part, final)
        if progress:
            progress(written)
        return str(_remux_mp4(final, ffmpeg_path, cancelled=cancelled))
    except Exception:
        try:
            part.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    finally:
        if source is not None:
            try:
                source.close()
            except Exception:
                pass
