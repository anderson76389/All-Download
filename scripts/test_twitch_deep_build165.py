"""Tests intégration réels (Windows, réseau) pour build-165, sans publier de vidéo.

Tous les MP4 sont créés dans TemporaryDirectory puis effacés.
Aucun cookie/OAuth n'est utilisé. Le téléchargement complet de la VOD (> 2 h)
n'est PAS tenté : extrait prolongé, segments milieu/fin, pause/reprise/annulation.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import yt_app
import twitch_hls

VOD = "https://www.twitch.tv/videos/2919531847"
PUBLIC_VOD = "https://www.twitch.tv/videos/2915087502"


def report(test, **result):
    print("TEST_RESULT " + test + " " + json.dumps(result, ensure_ascii=False), flush=True)


def new_api(download_root):
    class Probe:
        def __init__(self):
            self.events = []
        def evaluate_js(self, value):
            self.events.append(value)
    api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
    api._window = Probe()
    api.config = {"settings": {"notify": "always", "video_format": "MP4"}}
    api.download_folder = str(download_root)
    api.is_cancelled = False
    api.is_paused = False
    api._active_download_process = None
    api._suspended_download_pids = []
    yt_app.ensure_media_directories(str(download_root))
    return api


def ffmpeg_shortened(seconds, realtime=False, start=None):
    original = yt_app.twitch_hls_ffmpeg_command
    def build(*args):
        command = original(*args)
        if realtime:
            command[command.index("-i"):command.index("-i")] = ["-re"]
        if start is not None:
            command[command.index("-i"):command.index("-i")] = ["-ss", str(start)]
        command[command.index("-movflags"):command.index("-movflags")] = ["-t", str(seconds)]
        return command
    return build


def ffprobe(path):
    probe = subprocess.run(
        [yt_app.FFPROBE_PATH, "-v", "error",
         "-show_entries", "format=duration,size:stream=codec_type,codec_name",
         "-of", "json", str(path)],
        capture_output=True, text=True, errors="replace", timeout=35, check=True
    )
    obj = json.loads(probe.stdout)
    return float(obj["format"]["duration"]), {s["codec_type"] for s in obj.get("streams", [])}


def wait_until_active(api, seconds=22):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        proc = api._active_download_process
        if proc is not None and proc.poll() is None:
            return proc
        time.sleep(0.12)
    raise AssertionError("FFmpeg n'a pas démarré dans le délai")


def main():
    with tempfile.TemporaryDirectory(prefix="all-download-deep-twitch-") as root:
        root = Path(root)
        bin_dir = root / "Donnees" / "bin"
        bin_dir.mkdir(parents=True)
        yt_app.BIN_DIR = str(bin_dir)
        yt_app.APP_DIR = str(root / "Donnees")
        yt_app.FFMPEG_PATH = str(bin_dir / "ffmpeg.exe")
        yt_app.FFPROBE_PATH = str(bin_dir / "ffprobe.exe")
        yt_app.YTDLP_PATH = str(bin_dir / "yt-dlp.exe")
        yt_app.setup_binaries()
        assert yt_app.is_valid_windows_executable(yt_app.FFMPEG_PATH), "FFmpeg exe invalide"
        assert yt_app.is_valid_windows_executable(yt_app.FFPROBE_PATH), "FFprobe exe invalide"

        print("DEBUT_VALIDATION", VOD, flush=True)
        manifest, quality, duration, segments = twitch_hls.resolve_hls(VOD)
        assert duration > 500 and segments > 60
        report("MANIFEST_UTILISATEUR", quality=quality, seconds=round(duration, 2),
               segments=segments, access="public_https", oauth=False)

        public_manifest, public_quality, public_duration, public_count = twitch_hls.resolve_hls(PUBLIC_VOD)
        assert public_count > 50 and public_duration > 500
        report("MANIFEST_PUBLIC_TEMOIN", quality=public_quality,
               segments=public_count, seconds=round(public_duration, 2))

        # La sélection d'une qualité doit fonctionner sans altérer l'Auto.
        chosen, resolved_label, _, _ = twitch_hls.resolve_hls(VOD, "720p (60fps)")
        assert resolved_label in ("720p60", "chunked", "1080p60", "720p30", "480p30", "360p30", "160p30")
        report("QUALITE_720P", selected=resolved_label)

        api = new_api(root / "MEDIAS")
        target = root / "MEDIAS" / "AUTRES"
        item = {"url": VOD, "title": "Test 90 secondes", "mode": "Vidéo"}
        progress = []
        with patch.object(yt_app, "twitch_hls_ffmpeg_command", ffmpeg_shortened(90)):
            success, error = api._download_twitch_hls(
                item, str(target), "Meilleure qualité (Auto)", 1, 1,
                lambda pct, label: progress.append(pct)
            )
        assert success, "90 secondes: " + error
        outputs = sorted(target.glob("*.mp4"))
        assert len(outputs) == 1
        video_duration, codecs = ffprobe(outputs[0])
        assert video_duration >= 80, ("Durée insuffisante", video_duration)
        assert {"audio", "video"} <= codecs
        assert 100 in progress and any(x > 0 and x < 100 for x in progress)
        report("TELECHARGEMENT_90S", success=success, duration=round(video_duration, 2),
               bytes=outputs[0].stat().st_size, audio=True, video=True,
               progress_updates=len(progress))

        # Test de segment au milieu et en fin de VOD : pas seulement au début.
        for label, start in (("MILIEU", int(duration / 2)), ("FIN", max(60, int(duration - 85)))):
            destination = root / ("extra_" + label.lower() + ".mp4")
            cmd = [
                yt_app.FFMPEG_PATH, "-nostdin", "-hide_banner", "-loglevel", "warning",
                "-ss", str(start), "-i", manifest,
                "-t", "12", "-map", "0:v:0", "-map", "0:a?",
                "-c", "copy", "-movflags", "+faststart", "-n", str(destination)
            ]
            p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=95)
            assert p.returncode == 0 and destination.is_file(), (
                "Segment " + label + ": " + p.stderr[-800:])
            clip_duration, clip_codecs = ffprobe(destination)
            assert clip_duration > 4 and "video" in clip_codecs
            report("SEGMENT_" + label, start_sec=start, duration=round(clip_duration, 2),
                   bytes=destination.stat().st_size)
            destination.unlink()

        # La pause réelle doit suspendre le processus FFmpeg et sa reprise réussir.
        pause_api = new_api(root / "MEDIAS_PAUSE")
        pause_target = root / "MEDIAS_PAUSE" / "AUTRES"
        holder = {}
        with patch.object(yt_app, "twitch_hls_ffmpeg_command", ffmpeg_shortened(18, realtime=True)):
            def run_pause():
                holder["result"] = pause_api._download_twitch_hls(
                    {"url": VOD, "title": "TestPause"}, str(pause_target),
                    "Meilleure qualité (Auto)", 1, 1, lambda *args: None)
            thread = threading.Thread(target=run_pause, daemon=True)
            thread.start()
            proc = wait_until_active(pause_api)
            time.sleep(1.3)
            state = pause_api.pause_downloads()
            assert state.get("success") and state.get("mode") == "active", state
            import psutil
            current = psutil.Process(proc.pid)
            assert current.status() == psutil.STATUS_STOPPED, ("FFmpeg non suspendu", current.status())
            time.sleep(1.7)
            assert current.status() == psutil.STATUS_STOPPED
            resumed = pause_api.resume_downloads()
            assert resumed.get("success"), resumed
            thread.join(timeout=50)
            assert not thread.is_alive(), "Téléchargement bloqué après reprise"
        assert holder.get("result", (False,))[0], holder
        pause_files = list(pause_target.glob("*.mp4"))
        assert len(pause_files) == 1
        pause_duration, _ = ffprobe(pause_files[0])
        assert pause_duration > 12
        report("PAUSE_REPRISE", active_pause=True, duration=round(pause_duration, 2))

        # Annuler un HLS en cours doit arrêter FFmpeg et supprimer le MP4 partiel.
        cancel_api = new_api(root / "MEDIAS_CANCEL")
        cancel_target = root / "MEDIAS_CANCEL" / "AUTRES"
        cancelled = {}
        with patch.object(yt_app, "twitch_hls_ffmpeg_command", ffmpeg_shortened(90, realtime=True)):
            def run_cancel():
                cancelled["result"] = cancel_api._download_twitch_hls(
                    {"url": VOD, "title": "TestCancel"}, str(cancel_target),
                    "Meilleure qualité (Auto)", 1, 1, lambda *args: None)
            thread2 = threading.Thread(target=run_cancel, daemon=True)
            thread2.start()
            proc2 = wait_until_active(cancel_api)
            time.sleep(1.5)
            assert cancel_api.cancel_downloads() is True
            thread2.join(timeout=15)
            assert not thread2.is_alive(), "Annulation n'a pas arrêté FFmpeg"
        assert not cancelled.get("result", (True,))[0]
        leftovers = list(cancel_target.glob("*.mp4"))
        assert not leftovers, "MP4 final subsiste après annulation: " + str(leftovers)
        partials = list(cancel_target.glob("*.part.mp4"))
        assert not partials, "Fichier temporaire subsiste: " + str(partials)
        report("ANNULATION", process_stopped=True, no_partial_files=True)

        # Toute la suite hors réseau continue de tourner via workflow séparé.
        print("RESULTAT_FINAL SUCCESS : durée longue + début/milieu/fin + qualité + pause/reprise + annulation", flush=True)


if __name__ == "__main__":
    main()
