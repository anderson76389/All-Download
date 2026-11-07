"""Validation réelle ciblée Windows Twitch : qualité 720p et dossier TWITCH.

Extrait de 20 s uniquement dans Temp, sans mot de passe, cookie ni token.
Test sur l'URL donnée par l'utilisateur : https://www.twitch.tv/videos/2919531847
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yt_app
from twitch_vod import twitch_vod_id

VOD = "https://www.twitch.tv/videos/2919531847"

def main():
    with tempfile.TemporaryDirectory(prefix="all-download-twitch-quality-") as tmp:
        root = Path(tmp)
        yt_app.APP_DIR = str(root / "Donnees")
        yt_app.BIN_DIR = str(root / "Donnees" / "bin")
        yt_app.YTDLP_PATH = str(root / "Donnees" / "bin" / "yt-dlp.exe")
        yt_app.FFMPEG_PATH = str(root / "Donnees" / "bin" / "ffmpeg.exe")
        yt_app.FFPROBE_PATH = str(root / "Donnees" / "bin" / "ffprobe.exe")
        yt_app.setup_binaries()
        assert yt_app.is_valid_windows_executable(yt_app.FFMPEG_PATH)
        assert yt_app.is_valid_windows_executable(yt_app.FFPROBE_PATH)
        class FakeUI:
            events = []
            def evaluate_js(self, script):
                self.events.append(script)
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        api.config = {"settings": {"notify": "always", "video_format": "MP4"}}
        api.download_folder = str(root / "MEDIAS")
        api._window = FakeUI()
        api.is_cancelled = False
        api.is_paused = False
        api._active_download_process = None
        api._suspended_download_pids = []
        yt_app.ensure_media_directories(api.download_folder)
        assert "TWITCH" in yt_app.DOWNLOAD_CATEGORIES
        for name in yt_app.DOWNLOAD_CATEGORIES:
            assert (root / "MEDIAS" / name).is_dir()

        previous = root / "MEDIAS" / "AUTRES" / "Twitch_2919531847_ancien.mp4"
        previous.write_bytes(b"old file not touched")
        with patch.object(yt_app, "ensure_ytdlp_ready", return_value=False):
            data = api.extract_info(VOD)
        assert data.get("success"), data
        item = data["data"]
        formats = item["formats"]
        print("REAL_TWITCH_QUALITIES:", formats, flush=True)
        assert "Meilleure qualité (Auto)" in formats
        assert "720p (60fps)" in formats, "La VOD ne fournit pas actuellement la qualité 720p60"
        assert yt_app.get_media_download_dir(api.download_folder, item) == str(root / "MEDIAS" / "TWITCH")
        item["selectedQuality"] = "Meilleure qualité (Auto)"
        item["title"] = "TwitchQualite720"
        seen = []
        original = yt_app.twitch_hls_ffmpeg_command
        def short_command(*args):
            command = original(*args)
            command[command.index("-movflags"):command.index("-movflags")] = ["-t", "20"]
            return command
        with patch.object(yt_app, "twitch_hls_ffmpeg_command", short_command):
            ok, reason = api._download_twitch_hls(
                item, yt_app.get_media_download_dir(api.download_folder, item),
                item["selectedQuality"], 1, 1, lambda p, msg: seen.append((p, msg))
            )
        assert ok, reason
        files = list((root / "MEDIAS" / "TWITCH").glob("*.mp4"))
        assert len(files) == 1, files
        probe = subprocess.run(
            [yt_app.FFPROBE_PATH, "-v", "error",
             "-show_entries", "stream=codec_name,codec_type,width,height:format=duration,size",
             "-of", "json", str(files[0])],
            text=True, capture_output=True, errors="replace", timeout=25, check=True
        )
        streams = json.loads(probe.stdout)
        video = next(s for s in streams["streams"] if s.get("codec_type") == "video")
        assert video.get("height", 0) >= 360, video
        assert float(streams["format"]["duration"]) > 15, streams
        assert any(p == 100 for p, _ in seen)
        assert previous.read_bytes() == b"old file not touched"
        assert len(list((root / "MEDIAS" / "AUTRES").glob("*.mp4"))) == 1
        print("REAL_720P_TWITCH_SUCCESS:", json.dumps({
            "quality": "auto",
            "height": video["height"],
            "duration": streams["format"]["duration"],
            "file_bytes": files[0].stat().st_size,
            "folder": files[0].parent.name,
            "legacy_AUTRES_preserved": True,
            "progress_events": len(seen)
        }), flush=True)

if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        import traceback
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        raise SystemExit(1) from exc
