"""Diagnostic public, sans cookie, inspiré de l'architecture HLS analysée.
Ne copie aucun fichier de l'extension et n'utilise pas sa base de données privée.
Ne télécharge aucun segment vidéo (uniquement métadonnées + manifests HLS).
"""
import json
import re
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
VODS = [("utilisateur", "2919531847"), ("temoin_public", "2915087502")]
QUALITIES = ["chunked", "1080p60", "720p60", "480p30", "360p30"]
STREAM_PATH = re.compile(r"^/([a-zA-Z0-9]{20}_[a-zA-Z0-9_]+_\d+_\d+)/storyboards(?:/|$)")


def get_json(payload):
    request = Request(
        "https://gql.twitch.tv/gql",
        data=json.dumps(payload).encode(),
        headers={"Client-Id": CLIENT_ID, "Content-Type": "application/json",
                 "Accept": "application/json", "Origin": "https://www.twitch.tv",
                 "User-Agent": "Mozilla/5.0"},
        method="POST",
    )
    with urlopen(request, timeout=16) as response:
        return json.loads(response.read(500000))


def metadata(vod):
    attempts = [
        "query($id: ID!) { video(id:$id) { id title seekPreviewsURL owner { login } } }",
        "query($id: ID!) { video(id:$id) { id title animatedPreviewURL previewThumbnailURL owner { login } } }",
    ]
    collected = {}
    errors = []
    for query in attempts:
        try:
            body = get_json({"query": query, "variables": {"id": vod}})
            video = (body.get("data") or {}).get("video") or {}
            collected.update({key: value for key, value in video.items() if value})
            errors.extend((x.get("message") or "")[:130] for x in body.get("errors", []))
        except (HTTPError, URLError, OSError, ValueError, TypeError) as exc:
            errors.append(type(exc).__name__ + ": " + str(exc)[:120])
    return collected, errors


def candidates(url):
    if not isinstance(url, str):
        return []
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host.endswith(".cloudfront.net"):
        return []
    match = STREAM_PATH.match(parts.path)
    if not match:
        return []
    return [(quality, urlunsplit(("https", host, "/" + match[1] + "/" +
                                   quality + "/index-dvr.m3u8", "", ""))) for quality in QUALITIES]


def check_manifest(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=12) as response:
            body = response.read(250000).decode("utf-8-sig", errors="replace")
            if not response.url.startswith("https://") or ".cloudfront.net/" not in response.url:
                return {"state": "bad_redirect"}
            matches = len(re.findall(r"^#EXTINF:", body, re.M))
            return {"state": "accessible" if body.startswith("#EXTM3U") and matches else "no_segments",
                    "segments": matches, "http_status": response.status}
    except HTTPError as exc:
        return {"state": "http_" + str(exc.code)}
    except (URLError, OSError, ValueError, TimeoutError) as exc:
        return {"state": type(exc).__name__, "detail": str(exc)[:90]}



def test_mp4_stream(url, vod_id):
    """Télécharge 6 secondes en dossier TEMP puis vérifie la lecture vidéo."""
    import subprocess
    import tempfile
    from pathlib import Path
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix="twitch_hls_six_seconds_") as tmp:
        output = Path(tmp) / ("Twitch_" + vod_id + "_test.mp4")
        command = [
            ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "warning",
            "-i", url, "-t", "6", "-map", "0:v:0", "-map", "0:a?",
            "-c", "copy", "-movflags", "+faststart", "-n", str(output)
        ]
        process = subprocess.run(command, capture_output=True, text=True,
                                 errors="replace", timeout=120)
        print("FFMPEG_DOWNLOAD", process.returncode, "stderr", process.stderr[-1800:], flush=True)
        if process.returncode != 0 or not output.is_file():
            print("MP4_RESULT FAIL_DOWNLOAD", flush=True)
            return
        size = output.stat().st_size
        verify = subprocess.run(
            [ffmpeg, "-nostdin", "-v", "error", "-i", str(output),
             "-t", "3", "-f", "null", "NUL"],
            capture_output=True, text=True, errors="replace", timeout=60
        )
        print("MP4_RESULT", "VALID" if verify.returncode == 0 and size > 30000 else "INVALID",
              "size_bytes", size, "decode_exit", verify.returncode,
              "decode_errors", verify.stderr[-1300:], flush=True)

def main():
    for label, vid in VODS:
        info, errors = metadata(vid)
        print("VIDEO", label, vid, "title=", info.get("title"),
              "channel=", (info.get("owner") or {}).get("login"), flush=True)
        print("GQL_ERRORS", json.dumps(errors, ensure_ascii=False), flush=True)
        all_candidates = []
        for field in ("seekPreviewsURL", "animatedPreviewURL", "previewThumbnailURL"):
            url = info.get(field)
            print("PREVIEW", field, "present=", bool(url),
                  "cloudfront=", bool(url and ".cloudfront.net/" in url), flush=True)
            all_candidates.extend(candidates(url))
        seen = set()
        reached = False
        for quality, url in all_candidates:
            if url in seen:
                continue
            seen.add(url)
            result = check_manifest(url)
            print("MANIFEST", quality, json.dumps(result), flush=True)
            if result["state"] == "accessible":
                reached = True
                break
        print("RESULT", label, "HLS_PUBLIC_FOUND" if reached else
              "NO_HLS_PUBLIC_FOUND_FROM_PREVIEW", flush=True)
        if reached and label == "utilisateur":
            test_mp4_stream(url, vid)


if __name__ == "__main__":
    main()
