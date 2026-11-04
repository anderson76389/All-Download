"""Test de bout en bout : une vraie vidéo originale est téléchargée par Streamlink.

- Génère une vidéo H.264/AAC avec FFmpeg sans contenu tiers
- La sert comme véritable playlist HLS HTTP locale
- Télécharge toute la vidéo par le moteur Twitch, dans AUTRES
- Vérifie le MP4 résultant par décodage FFmpeg, image ET audio
- Vérifie non-écrasement, absence de .part et taille non nulle

Aucun réseau Twitch ou média externe n'est nécessaire pour cette preuve
de téléchargement de bout en bout.
"""
from __future__ import annotations

import http.server
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from streamlink import Streamlink
from streamlink.stream.hls import HLSStream
from twitch_streamlink_engine import download_twitch_vod


class StaticVideoHandler(http.server.BaseHTTPRequestHandler):
    root = None

    def do_GET(self):
        mapping = {
            "/test.m3u8": ("test.m3u8", "application/vnd.apple.mpegurl"),
            "/clip.ts": ("clip.ts", "video/mp2t"),
        }
        if self.path not in mapping:
            self.send_error(404)
            return
        name, content_type = mapping[self.path]
        body = (self.root / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def run_checked(command, timeout=40):
    result = subprocess.run(
        command, capture_output=True, text=True, errors="replace", timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        raise RuntimeError(
            f"La commande FFmpeg a échoué ({result.returncode}) : "
            + (result.stderr or "")[-1500:]
        )
    return result


def ffmpeg_binary():
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        return get_ffmpeg_exe()
    except ImportError:
        candidate = shutil.which("ffmpeg")
        if not candidate:
            raise RuntimeError("Ce test de vidéo exige FFmpeg ou imageio-ffmpeg.")
        return candidate


def main():
    ffmpeg = ffmpeg_binary()
    with tempfile.TemporaryDirectory(prefix="all-download-twitch-valid-hls-") as folder:
        root = Path(folder)
        source_dir = root / "fixture"
        source_dir.mkdir()
        segment = source_dir / "clip.ts"
        playlist = source_dir / "test.m3u8"

        # Fichier vidéo réellement décodable, créé spécifiquement pour le test.
        run_checked([
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=600:sample_rate=48000",
            "-t", "3", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
            "-f", "mpegts", str(segment),
        ])
        assert segment.stat().st_size > 10000, "La vidéo générée est trop petite."
        playlist.write_text(
            "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:3\n"
            "#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:3.000,\nclip.ts\n#EXT-X-ENDLIST\n",
            encoding="ascii",
        )
        StaticVideoHandler.root = source_dir
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), StaticVideoHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/test.m3u8"

            class LocalHLSSession:
                def __init__(self):
                    self.delegate = Streamlink()

                def set_option(self, key, value):
                    self.delegate.set_option(key, value)

                def streams(self, _twitch_url):
                    return {"best": HLSStream(self.delegate, url)}

            output_root = root / "programme"
            original = output_root / "AUTRES" / "Twitch_VOD_2905228526_Streamlink_best.ts"
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(b"NE_PAS_ECRASER")
            progress = []
            result = Path(download_twitch_vod(
                "https://www.twitch.tv/videos/2905228526",
                str(output_root),
                ffmpeg_path=ffmpeg,
                session_factory=LocalHLSSession,
                progress=progress.append,
            ))
            assert result.suffix.lower() == ".mp4", f"Remux MP4 non exécuté : {result}"
            assert result.parent == output_root / "AUTRES", "Sortie hors AUTRES."
            assert result.is_file() and result.stat().st_size > 10000, "MP4 vide."
            assert original.read_bytes() == b"NE_PAS_ECRASER", "Fichier existant écrasé."
            assert not list(result.parent.glob("*.part")), "Fichier .part abandonné."
            assert not list(result.parent.glob("*Streamlink_best.ts"))[1:], "TS source non nettoyé."
            assert progress and progress[-1] > 10000, "Progression non communiquée."

            # Décode le média complet, audio et vidéo, et vérifie les durées.
            run_checked([
                ffmpeg, "-v", "error", "-i", str(result),
                "-map", "0:v:0", "-f", "null", "-",
            ])
            run_checked([
                ffmpeg, "-v", "error", "-i", str(result),
                "-map", "0:a:0", "-f", "null", "-",
            ])
            print(
                "STREAMLINK_FULL_VIDEO=SUCCESS",
                "format=MP4",
                "size_bytes=", result.stat().st_size,
                "audio_video_decoded=true",
                "folder=AUTRES",
                "original_preserved=true",
                "no_partial_files=true",
            )
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
