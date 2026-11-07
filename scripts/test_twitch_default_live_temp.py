"""Validation réseau Twitch après correction du path HLS et du défaut 1080/720.

N'utilise ni cookies ni OAuth. MP4 de 8 s dans TEMP, supprimés en fin.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yt_app
import twitch_hls
from twitch_vod import fallback_metadata, preferred_twitch_quality

VOD = "https://www.twitch.tv/videos/2919531847"


def main():
    with tempfile.TemporaryDirectory(prefix="twitch-default-1080-720-") as td:
        root = Path(td)
        yt_app.APP_DIR = str(root / "Donnees")
        yt_app.BIN_DIR = str(root / "Donnees" / "bin")
        yt_app.YTDLP_PATH = str(root / "Donnees" / "bin" / "yt-dlp.exe")
        yt_app.FFMPEG_PATH = str(root / "Donnees" / "bin" / "ffmpeg.exe")
        yt_app.FFPROBE_PATH = str(root / "Donnees" / "bin" / "ffprobe.exe")
        yt_app.setup_binaries()
        assert yt_app.is_valid_windows_executable(yt_app.FFMPEG_PATH)
        assert yt_app.is_valid_windows_executable(yt_app.FFPROBE_PATH)

        info = fallback_metadata(VOD)
        print("TWITCH_CARD_DEFAULT", json.dumps({
            "selectedQuality": info["selectedQuality"],
            "formats": info["formats"][:5],
            "720_only": preferred_twitch_quality(["Meilleure qualité (Auto)", "720p (60fps)"])
        }, ensure_ascii=False), flush=True)
        assert info["selectedQuality"] == "1080p (60fps)"
        assert preferred_twitch_quality(["Meilleure qualité (Auto)", "720p (60fps)"]) == "720p (60fps)"

        meta = twitch_hls.metadata_for_vod("2919531847")
        preview = meta.get("seekPreviewsURL")
        assert preview and "cloudfront.net" in preview
        entries = twitch_hls.manifest_candidates(preview, "1080p (60fps)")
        assert entries[0][0] == "1080p60"
        for label, manifest in entries:
            assert manifest.count("/") >= 4
            assert not manifest.split("/")[3].isdigit(), "HLS prefix a été remplacé par la hauteur " + label

        for requested in ("1080p (60fps)", "720p (60fps)"):
            manifest, label, total, segs = twitch_hls.resolve_hls(VOD, requested)
            print("REAL_HLS_QUALITY", json.dumps({
                "requested": requested, "selected": label, "duration": total,
                "segments": segs
            }, ensure_ascii=False), flush=True)
            assert segs > 20
            output = root / ("twitch_" + requested[:4] + ".mp4")
            cmd = twitch_hls.ffmpeg_command(yt_app.FFMPEG_PATH, manifest, output)
            cmd[cmd.index("-movflags"):cmd.index("-movflags")] = ["-t", "8"]
            process = subprocess.run(cmd, text=True, capture_output=True, errors="replace", timeout=70)
            assert process.returncode == 0, "FFmpeg:" + process.stderr[-900:]
            probe = subprocess.run(
                [yt_app.FFPROBE_PATH, "-v", "error",
                 "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height",
                 "-of", "json", str(output)],
                capture_output=True, text=True, errors="replace", timeout=30, check=True
            )
            info = json.loads(probe.stdout)
            vid = next(s for s in info["streams"] if s.get("codec_type") == "video")
            assert 6 <= float(info["format"]["duration"]) <= 12
            assert any(s.get("codec_type") == "audio" for s in info["streams"])
            if requested.startswith("720p"):
                assert vid.get("height", 9999) <= 720
            else:
                assert vid.get("height", 9999) <= 1080
            print("REAL_MP4_OK", json.dumps({
                "requested":requested,"hls_quality":label, "height":vid.get("height"),
                "seconds":info["format"]["duration"],"size":output.stat().st_size
            }, ensure_ascii=False), flush=True)
        print("REAL_TEST_PASS_1080_720", flush=True)


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        import traceback
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        raise SystemExit(1)
