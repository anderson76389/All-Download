"""Test Windows réel, jetable : Twitch HLS sans CLI + Deno local officiel.

Aucune VOD complète téléchargée ; MP4 de 8 secondes uniquement. Aucun
fichier créé dans la distribution ou le dépôt.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yt_app
import deno_runtime

VOD = "https://www.twitch.tv/videos/2919531847"
YOUTUBE = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


def require(condition, text):
    if not condition:
        raise AssertionError(text)


def main():
    with tempfile.TemporaryDirectory(prefix="all-download-real-twitch-deno-") as temporary:
        root = Path(temporary)
        yt_app.APP_DIR = str(root / "Donnees")
        yt_app.BIN_DIR = str(root / "Donnees" / "bin")
        yt_app.YTDLP_CACHE_DIR = str(root / "Donnees" / "cache" / "yt-dlp")
        yt_app.YTDLP_PATH = str(root / "Donnees" / "bin" / "yt-dlp.exe")
        yt_app.DENO_PATH = str(root / "Donnees" / "bin" / "deno.exe")
        yt_app.FFMPEG_PATH = str(root / "Donnees" / "bin" / "ffmpeg.exe")
        yt_app.FFPROBE_PATH = str(root / "Donnees" / "bin" / "ffprobe.exe")
        yt_app.setup_binaries()
        for name, path in (("yt-dlp", yt_app.YTDLP_PATH),
                           ("FFmpeg", yt_app.FFMPEG_PATH),
                           ("FFprobe", yt_app.FFPROBE_PATH)):
            require(yt_app.is_valid_windows_executable(path),
                    name + " x64 non disponible")

        require(not Path(yt_app.DENO_PATH).exists(),
                "Deno ne doit pas être requis par Twitch")
        download_dir = root / "TWITCH"
        download_dir.mkdir()

        original_builder = yt_app.twitch_hls_ffmpeg_command
        def short_mp4(*args, **kwargs):
            cmd = original_builder(*args, **kwargs)
            require(cmd[cmd.index("-c") + 1] == "copy",
                    "Risque de réencodage Twitch")
            require("-vf" not in cmd and "-r" not in cmd and "libx264" not in cmd,
                    "La résolution ne doit pas être fabriquée")
            insert = cmd.index("-movflags")
            return cmd[:insert] + ["-t", "8"] + cmd[insert:]

        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api._window = None
        api.is_cancelled = False
        api.is_paused = False
        api._active_download_process = None

        # On simule explicitement GitHub/CLI indisponible : le moteur HLS doit
        # réellement produire un MP4 AVEC audio et vidéo, sans conversion.
        with patch.object(yt_app, "ensure_cli_ready",
                          return_value=(False, "Le serveur CLI est hors ligne")) as cli, \
             patch.object(yt_app, "twitch_hls_ffmpeg_command",
                          side_effect=short_mp4):
            success = api._download_twitch_video(
                {"url": VOD, "title": "Twitch reel sans CLI"},
                str(download_dir), "1080p (60fps)", 1, 1
            )
        cli.assert_called_once()
        require(success, "HLS Twitch a échoué sans TwitchDownloaderCLI")
        require(not Path(yt_app.DENO_PATH).exists(),
                "Twitch ne doit pas installer Deno")
        videos = list(download_dir.glob("*.mp4"))
        require(len(videos) == 1, "Le secours HLS n'a pas produit un seul MP4")
        video_path = videos[0]
        info = subprocess.run(
            [yt_app.FFPROBE_PATH, "-v", "error", "-show_entries",
             "format=duration,size:stream=codec_type,codec_name,height",
             "-of", "json", str(video_path)],
            capture_output=True, text=True, timeout=30, check=True
        )
        metadata = json.loads(info.stdout)
        stream_types = {x.get("codec_type") for x in metadata["streams"]}
        height = next(x["height"] for x in metadata["streams"]
                      if x.get("codec_type") == "video")
        seconds = float(metadata["format"]["duration"])
        require(6 <= seconds <= 12, "Extrait MP4 avec mauvaise durée")
        require(height in (1080, 720), "Qualité Twitch inventée")
        require({"audio", "video"} <= stream_types, "Audio ou vidéo absent")
        print("REAL_TWITCH_HLS_WITHOUT_CLI_PASS", json.dumps({
            "height": height, "seconds": seconds,
            "bytes": video_path.stat().st_size,
            "audio": "audio" in stream_types,
            "video": "video" in stream_types,
            "codec_copy": True,
        }), flush=True)

        # On installe ensuite Deno à partir de l'archive officielle et teste
        # le vrai moteur téléchargé, sans changer PATH ni toucher à Twitch.
        deno_args = yt_app.youtube_js_args(YOUTUBE)
        require(deno_args == ["--js-runtimes", "deno:" + yt_app.DENO_PATH],
                "Deno n'a pas été préparé localement")
        require(yt_app.is_valid_windows_executable(yt_app.DENO_PATH),
                "Deno local non valide")
        version = subprocess.run(
            [yt_app.DENO_PATH, "--version"], capture_output=True,
            text=True, timeout=20, check=True
        )
        print("REAL_DENO_WINDOWS_X64_PASS", json.dumps({
            "path": yt_app.DENO_PATH,
            "version": version.stdout.splitlines()[0],
            "no_global_install": True,
        }), flush=True)
        require(yt_app.youtube_js_args(VOD) == [],
                "Deno a été ajouté à la route Twitch")
        check = subprocess.run(
            [yt_app.YTDLP_PATH, *deno_args, "--version"],
            capture_output=True, text=True, timeout=20, check=True
        )
        print("REAL_YTDLP_WITH_DENO_FLAGS_PASS", check.stdout.strip(), flush=True)
        print("REAL_TWITCH_AND_DENO_WINDOWS_SUCCESS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        import traceback
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        raise SystemExit(1)
