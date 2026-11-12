"""Real public YouTube/Twitch network diagnostic using the native yt-dlp engine.

This is a diagnostic, NOT proof that every video on those services is downloadable.
Each test must produce a playable file to be marked PASS. Website-side errors
are reported as BLOCKED, never converted into test successes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CASES = (
    ("youtube", "YouTube public video (app Android fixture)",
     "https://www.youtube.com/watch?v=DTi8wZ1a1TA"),
    ("youtube_alt", "YouTube public extractor test video",
     "https://www.youtube.com/watch?v=BaW_jenozKc"),
    ("twitch_clip", "Twitch public clip",
     "https://www.twitch.tv/aminematue/clip/ResoluteYummyDaikonBibleThump-2TAOvt5En3sdDMZm"),
    ("twitch_vod", "Twitch VOD (may expire or require authentication)",
     "https://www.twitch.tv/videos/2919531847"),
)
REMOTE_BLOCKERS = (
    "sign in to confirm", "not a bot", "login required", "sign in to",
    "subscriber-only", "subscriber only", "http error 403", "http error 404",
    "http error 429", "video unavailable", "not available", "private video",
    "this video is not available", "no video formats found",
    "requested format is not available", "unsupported url",
    "this clip is not available", "unable to download webpage",
    "failed to download m3u8", "geo-restricted", "not found",
    "requires authentication", "this video is no longer available",
    "this video is only available", "unable to extract",
)


def run(command: list[str], timeout: int) -> tuple[int, str, str]:
    try:
        p = subprocess.run(command, text=True, capture_output=True, timeout=timeout,
                           errors="replace", stdin=subprocess.DEVNULL)
        return p.returncode, p.stdout[-10000:], p.stderr[-9000:]
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout after {timeout}s"
    except OSError as error:
        return 126, "", f"Local binary unavailable: {error}"


def classify(error: str) -> str:
    lowered = error.lower()
    if any(token in lowered for token in REMOTE_BLOCKERS):
        return "BLOCKED"
    if "timed out" in lowered or "timeout after" in lowered or "temporary failure" in lowered:
        return "BLOCKED"
    return "ERROR"


def metadata(binary: str, url: str) -> tuple[dict | None, str, str]:
    base = [binary, "--ignore-config", "--no-playlist", "--no-warnings",
            "--socket-timeout", "15", "--retries", "1", "--extractor-retries", "1",
            "--no-check-certificate"] if False else [
            binary, "--ignore-config", "--no-playlist", "--no-warnings",
            "--socket-timeout", "15", "--retries", "1", "--extractor-retries", "1",
        ]
    code, stdout, stderr = run(base + ["--dump-single-json", "--skip-download", url], 85)
    if code != 0:
        return None, classify(stderr or stdout), (stderr or stdout)[-450:]
    try:
        info = json.loads(stdout)
        if not isinstance(info, dict) or not info.get("id"):
            return None, "ERROR", "Extracted JSON has no media ID"
        return info, "PASS", ""
    except (ValueError, TypeError) as error:
        return None, "ERROR", f"Malformed yt-dlp metadata: {error}"


def download(binary: str, url: str, folder: Path) -> tuple[dict | None, str, str]:
    output = str(folder / "public-test-%(id)s.%(ext)s")
    command = [
        binary, "--ignore-config", "--no-playlist", "--no-warnings",
        "--socket-timeout", "15", "--retries", "1", "--fragment-retries", "1",
        "--extractor-retries", "1", "--no-overwrites",
        "--max-filesize", "80M", "--download-sections", "*0-5",
        "--format", "bv*[height<=720]+ba/b[height<=720]/best",
        "--merge-output-format", "mp4", "-o", output, url,
    ]
    code, stdout, stderr = run(command, 130)
    if code:
        detail = (stderr or stdout)[-450:]
        return None, classify(detail), detail
    videos = [
        f for f in folder.rglob("*") if f.is_file()
        and f.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov", ".ts")
        and f.stat().st_size > 2048
    ]
    if not videos:
        return None, "ERROR", "yt-dlp exit=0 but no nonempty video was produced"
    video = max(videos, key=lambda f: f.stat().st_size)
    code, out, err = run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height,codec_name", "-of", "json", str(video)], 25
    )
    if code:
        return None, "ERROR", f"FFprobe cannot decode exported video: {err[-350:]}"
    try:
        streams = json.loads(out).get("streams", [])
        video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"
                             and stream.get("width", 0) > 0 and stream.get("height", 0) > 0), None)
        if not video_stream:
            return None, "ERROR", "Exported video has no decodable video stream"
        return {"bytes": video.stat().st_size,
                "height": video_stream["height"], "width": video_stream["width"],
                "codec": video_stream.get("codec_name", "unknown")}, "PASS", ""
    except (ValueError, TypeError, KeyError) as error:
        return None, "ERROR", f"Unable to parse FFprobe result: {error}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", required=True, choices=("windows", "linux"))
    parser.add_argument("--yt-dlp", required=True)
    parser.add_argument("--json-out", default="live-media-results.json")
    args = parser.parse_args()
    binary = str(Path(args.yt_dlp).resolve())
    if not Path(binary).is_file():
        raise SystemExit(f"yt-dlp executable not present: {binary}")
    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        raise SystemExit("FFmpeg/FFprobe not available on PATH")
    print(f"Testing actual public media on {args.platform}; binaries: {binary}", flush=True)
    results = []
    with tempfile.TemporaryDirectory(prefix="all-download-public-media-") as scratch:
        for case, label, url in CASES:
            print(f"=== {label} ({case}) ===", flush=True)
            info, metadata_status, meta_error = metadata(binary, url)
            record = {"case": case, "label": label, "url": url,
                      "metadata": metadata_status, "download": "NOT_ATTEMPTED",
                      "media_info": None}
            if info:
                formats = info.get("formats") or []
                heights = sorted({f.get("height") for f in formats
                                  if isinstance(f, dict) and isinstance(f.get("height"), int)
                                  and f.get("height") > 0}, reverse=True)
                record["media_info"] = {
                    "id": str(info.get("id", ""))[:64],
                    "title": str(info.get("title", ""))[:110],
                    "available_heights": heights[:15],
                }
                folder = Path(scratch) / case
                folder.mkdir()
                video, download_status, download_error = download(binary, url, folder)
                record["download"] = download_status
                if video:
                    record["exported"] = video
                if download_error:
                    record["download_reason"] = download_error
            elif meta_error:
                record["metadata_reason"] = meta_error
            print(json.dumps(record, ensure_ascii=False), flush=True)
            results.append(record)
    output = Path(args.json_out)
    output.write_text(json.dumps({"platform": args.platform, "cases": results},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    passed = sum(x["download"] == "PASS" for x in results)
    metadata_pass = sum(x["metadata"] == "PASS" for x in results)
    blocked = sum(x["metadata"] == "BLOCKED" or x["download"] == "BLOCKED" for x in results)
    errors = sum(x["metadata"] == "ERROR" or x["download"] == "ERROR" for x in results)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    text = (f"### Real YouTube/Twitch probes on {args.platform}\n"
            f"**Playable downloads: {passed}/4; metadata extracted: {metadata_pass}/4; "
            f"service/network blocked: {blocked}/4; other errors: {errors}/4.**\n\n"
            "| Media | Metadata | Playable downloaded file | Detail |\n"
            "|---|---|---|---|\n")
    for row in results:
        detail = row.get("exported") or row.get("download_reason") or row.get("metadata_reason") or ""
        detail = str(detail).replace("|", "/").replace("\n", " ")[:160]
        text += f"| {row['case']} | {row['metadata']} | {row['download']} | {detail} |\n"
    text += ("\n**A blocked test is INCONCLUSIVE, not a successful download.** "
             "Media is downloaded into a disposable temporary folder only.\n")
    print(text, flush=True)
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(text)
    if errors:
        print(f"::warning::{errors} unexpected probe failures; review JSON artifact.", flush=True)
    if blocked:
        print(f"::warning::{blocked} upstream access restrictions; no conclusion for affected media.", flush=True)
    if not passed:
        print("::warning::No YouTube/Twitch video successfully downloaded on this runner.", flush=True)
    # Diagnostic CI reports external failures accurately but never treats them as media PASS.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
