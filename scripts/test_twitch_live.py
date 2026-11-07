"""Vérification live ciblée sur Windows: vraie VOD publique, 6 secondes seulement.

Ce script ne conserve ni vidéos ni identifiants et ne modifie aucun fichier utilisateur.
Il appelle start_downloads() comme l’interface, avec une découpe limitée au test.
"""
import json
import os
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import yt_app

VODS = [
    ("Kamet0", "https://www.twitch.tv/videos/2918765022"),
    ("mistermv", "https://www.twitch.tv/videos/2906716261"),
    ("StreamDatabase", "https://www.twitch.tv/videos/2905908970"),
    ("mistermv2", "https://www.twitch.tv/videos/2908472298"),
]

class UiProbe:
    def __init__(self):
        self.events = []

    def evaluate_js(self, statement):
        self.events.append(statement)
        if "showAppToast" in statement or "markDownloadSuccess" in statement:
            print("EVENEMENT_UI:", statement[:400], flush=True)

class ImmediateThread:
    def __init__(self, target, **kwargs):
        self.target = target

    def start(self):
        self.target()

def main():
    with tempfile.TemporaryDirectory(prefix="all-download-twitch-live-") as root:
        directory = Path(root)
        bin_dir = directory / "Donnees" / "bin"
        bin_dir.mkdir(parents=True)
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        print("FFMPEG_RUNNER:", ffmpeg, flush=True)
        yt_app.BIN_DIR = str(bin_dir)
        yt_app.APP_DIR = str(directory / "Donnees")
        yt_app.FFMPEG_PATH = str(bin_dir / "ffmpeg.exe")
        yt_app.YTDLP_PATH = str(bin_dir / "yt-dlp.exe")
        if ffmpeg and yt_app.is_valid_windows_executable(ffmpeg):
            shutil.copy2(ffmpeg, yt_app.FFMPEG_PATH)
        else:
            yt_app.setup_binaries()
        assert yt_app.is_valid_windows_executable(yt_app.FFMPEG_PATH), "FFmpeg Windows x64 absent"
        if not ffprobe or not Path(ffprobe).is_file():
            ffprobe = str(bin_dir / "ffprobe.exe")
        if not Path(ffprobe).is_file():
            print("Installation de ffprobe pour validation MP4", flush=True)
            yt_app.setup_binaries()
        assert Path(ffprobe).is_file(), "ffprobe indisponible"

        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api.config = {"settings": {"notify": "always", "video_format": "MP4"}}
        api.download_folder = str(directory / "MEDIAS")
        api._window = UiProbe()
        api.is_cancelled = False
        api.is_paused = False
        api._active_download_process = None
        api._suspended_download_pids = []
        yt_app.ensure_media_directories(api.download_folder)
        # Diagnostic CLI : aide en console avant le vrai téléchargement.
        from twitch_vod import ensure_cli_ready, CLI_FILENAME
        ok, reason = ensure_cli_ready(str(bin_dir), yt_app.is_valid_windows_executable)
        assert ok, "Installation du CLI impossible: " + reason
        cli_path = str(bin_dir / CLI_FILENAME)
        probe = subprocess.run([cli_path, "videodownload", "--help"],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=30)
        print("CLI_HELP_RC:", probe.returncode, "OUTPUT:", probe.stdout[-1800:],
              "STDERR:", probe.stderr[-1800:], flush=True)
        real_popen = subprocess.Popen

        def logging_popen(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            if process.stdout is not None:
                real_pipe = process.stdout
                class LoggingPipe:
                    def readline(self):
                        line = real_pipe.readline()
                        if line:
                            print("CLI_OUTPUT:", repr(line[:1000]), flush=True)
                        return line
                process.stdout = LoggingPipe()
            return process

        real_builder = yt_app.build_twitch_command

        def short_clip_command(*args, **kwargs):
            command = real_builder(*args, **kwargs)
            command.extend(["--beginning", "00:00:02", "--ending", "00:00:08"])
            print("CLI_COMMAND:", [x if x != args[0] else "TwitchDownloaderCLI.exe" for x in command], flush=True)
            return command

        for channel, vod_url in VODS:
            api._window.events.clear()
            item = {"url": vod_url, "mode": "Vidéo", "title": "Live Test " + channel,
                    "selectedQuality": "Meilleure qualité (Auto)", "is_direct_download": False}
            print("VOD_TEST:", channel, vod_url, flush=True)
            with patch.object(yt_app, "build_twitch_command", short_clip_command), \
                 patch.object(yt_app.subprocess, "Popen", side_effect=logging_popen), \
                 patch.object(yt_app.threading, "Thread", ImmediateThread), \
                 patch.object(yt_app, "ensure_ytdlp_ready", side_effect=AssertionError("yt-dlp ne doit pas être nécessaire")):
                api.start_downloads([item])
            files = list((directory / "MEDIAS" / "AUTRES").glob("*.mp4"))
            if files:
                print("VOD_SUCCESS:", channel, vod_url, flush=True)
                break
            print("VOD_ACCESS_FAILURE:", channel, vod_url, flush=True)

        files = list((directory / "MEDIAS" / "AUTRES").glob("*.mp4"))
        print("MP4_OUTPUTS:", [(str(f), f.stat().st_size) for f in files], flush=True)
        if not files and Path(yt_app.YTDLP_PATH).is_file():
            for channel, vod_url in (VODS[0], VODS[1]):
                try:
                    probe_yt = subprocess.run(
                        [yt_app.YTDLP_PATH, "--ignore-config", "--no-warnings",
                         "--skip-download", "--no-playlist", "--print", "%(id)s %(title)s",
                         vod_url],
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=45
                    )
                    print("YTDLP_PROBE:", channel, "returncode", probe_yt.returncode,
                          "stdout", probe_yt.stdout[-800:],
                          "stderr", probe_yt.stderr[-1300:], flush=True)
                except Exception as err:
                    print("YTDLP_PROBE_ERROR:", channel, str(err), flush=True)
        assert len(files) == 1 and files[0].stat().st_size >= 30000, "Aucun MP4 téléchargé ou fichier incomplet"
        assert any("markDownloadSuccess(" in event for event in api._window.events), "Interface non notifiée du succès"
        details = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                 "format=duration,size:stream=codec_name,codec_type", "-of", "json", str(files[0])],
                 capture_output=True, text=True, timeout=30, check=True)
        report = json.loads(details.stdout)
        print("FFPROBE:", json.dumps(report, ensure_ascii=False), flush=True)
        assert float(report["format"]["duration"]) >= 2.0, "MP4 illisible ou trop court"
        assert any(x.get("codec_type") == "video" for x in report.get("streams", [])), "Pas de flux vidéo"
        print("SUCCESS: téléchargement de VOD Twitch réelle, MP4 valide, UI notifiée.", flush=True)

if __name__ == "__main__":
    main()
