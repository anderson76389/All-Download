"""Windows GitHub Actions : vrais flux Twitch natifs, sans réencodage.

VOD 2919531847 : extraits de 8 s, MP4 supprimés à la fin de ce test.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yt_app
import twitch_hls

VOD = "https://www.twitch.tv/videos/2919531847"


def inspect_mp4(path):
    p = subprocess.run(
        [yt_app.FFPROBE_PATH, "-v", "error", "-show_entries",
         "format=duration,size:stream=codec_type,codec_name,width,height",
         "-of", "json", str(path)],
        capture_output=True, text=True, errors="replace", timeout=30, check=True
    )
    info = json.loads(p.stdout)
    video = next(x for x in info["streams"] if x.get("codec_type") == "video")
    assert any(x.get("codec_type") == "audio" for x in info["streams"])
    assert 6 <= float(info["format"]["duration"]) <= 11, info
    return video, info


def main():
    with tempfile.TemporaryDirectory(prefix="all-download-twitch-native-") as temp:
        base = Path(temp)
        yt_app.APP_DIR = str(base / "Donnees")
        yt_app.BIN_DIR = str(base / "Donnees" / "bin")
        yt_app.FFMPEG_PATH = str(base / "Donnees" / "bin" / "ffmpeg.exe")
        yt_app.FFPROBE_PATH = str(base / "Donnees" / "bin" / "ffprobe.exe")
        yt_app.YTDLP_PATH = str(base / "Donnees" / "bin" / "yt-dlp.exe")
        yt_app.setup_binaries()
        assert yt_app.is_valid_windows_executable(yt_app.FFMPEG_PATH)
        assert yt_app.is_valid_windows_executable(yt_app.FFPROBE_PATH)

        class Dummy:
            is_cancelled = False
            _active_download_process = None
        downloader = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        downloader.is_cancelled = False
        downloader._active_download_process = None
        root = base / "TWITCH"
        root.mkdir()

        preview = twitch_hls.metadata_for_vod("2919531847").get("seekPreviewsURL")
        assert preview
        chunked_url = twitch_hls.manifest_candidates(preview, "1080p (60fps)")[0][1]
        native_height = twitch_hls.probe_native_height(yt_app.FFPROBE_PATH, chunked_url)
        print("SOURCE_NATIVE_HEIGHT", native_height, flush=True)

        real_builder = yt_app.twitch_hls_ffmpeg_command
        def short_builder(*args, **kwargs):
            command = real_builder(*args, **kwargs)
            assert command[command.index("-c") + 1] == "copy", command
            assert not any(flag in command for flag in ("-vf", "-af", "-crf", "libx264", "scale", "-r"))
            command[command.index("-movflags"):command.index("-movflags")] = ["-t", "8"]
            print("NATIVE_FFMPEG_CODEC_COPY", True, flush=True)
            return command

        # 1080p demandé. Si "chunked" est un vrai 1080p natif, il doit être
        # préféré au 720p : aucune conversion artificielle.
        for quality in ("1080p (60fps)", "720p (60fps)"):
            with patch.object(yt_app, "twitch_hls_ffmpeg_command", side_effect=short_builder):
                success, reason = downloader._download_twitch_hls(
                    {"url": VOD, "title": "Validation native " + quality}, str(root),
                    quality, 1, 1, lambda *args: None
                )
            assert success, reason
            files = sorted(root.glob("*.mp4"), key=lambda path: path.stat().st_mtime)
            output = files[-1]
            video, data = inspect_mp4(output)
            height = video.get("height")
            assert height in (1080, 720), f"Résolution non native retenue : {height}"
            if quality.startswith("720"):
                assert height == 720, height
            if quality.startswith("1080") and native_height == 1080:
                assert height == 1080, "La source native 1080p a été ignorée."
            print("NATIVE_REAL_MP4_OK", json.dumps({
                "requested":quality,"height":height,"duration":data["format"]["duration"],
                "size":output.stat().st_size,"codec":video["codec_name"],"copy":True
            }, ensure_ascii=False), flush=True)
        print("NATIVE_1080_720_TEST_SUCCESS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        raise SystemExit(1)
