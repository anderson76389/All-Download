"""All-Download Linux: backend Linux natif et interface HTML identique à Windows.

Les binaires et les données restent dans le répertoire décompressé All-Download.
Aucune modification de yt_app.py ou des versions Windows/Android.
"""
from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CATEGORIES = ("AUTRES", "VIDÉOS", "CHAÎNES", "AUDIOS", "PLAYLIST", "GIFS", "TWITCH")
DEFAULTS = {
    "sortie_type": "video", "video_format": "MP4", "post_process_video": "Aucun",
    "video_origin_stream": False, "video_embed_thumb": True,
    "video_write_thumb": True, "video_add_metadata": True,
    "audio_format": "FLAC", "post_process_audio": "Aucun",
    "audio_embed_thumb": True, "audio_write_thumb": True, "audio_add_metadata": True,
    "sponsor_enable": True, "sponsor_remove": "sponsor", "sponsor_mark": "none",
    "sponsor_api": "https://sponsor.ajay.app", "exact_cut": False,
    "theme": "dark", "extra_selector": "none", "audio_sample_rate": "source",
    "notify": "never", "proxy_toggle": False, "proxy_url": "",
    "impersonation": "none", "extractor_args": "",
}
USER_AGENTS = {
    "chrome_win10": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "chrome_mac14": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "chrome_mac15": "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_0) AppleWebKit/537.36 Chrome/133.0.0.0 Safari/537.36",
    "chrome_android14": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/131.0.0.0 Mobile Safari/537.36",
    "chrome_android12": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/99.0.0.0 Mobile Safari/537.36",
    "edge_win10": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "firefox_mac14_135": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:135.0) Gecko/20100101 Firefox/135.0",
    "firefox_mac14_133": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:133.0) Gecko/20100101 Firefox/133.0",
    "safari_ios18": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) AppleWebKit/605.1.15 Version/18.4 Mobile Safari/604.1",
    "safari_mac15": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15",
}

def cleanup_old_workspaces(folder: Path, *, now: float | None = None,
                           max_removals: int = 16, max_scan: int = 256) -> int:
    """Remove old app-created scratch dirs without touching user downloads.

    Only names generated from uuid.uuid4().hex are eligible. Skip symlinks,
    non-directories and anything modified in the last seven days. Bound the
    scan/deletion work to keep first-launch CPU/disk usage predictable.
    """
    root = Path(folder)
    if root.is_symlink() or not root.is_dir():
        return 0
    current = time.time() if now is None else now
    cutoff = current - 7 * 24 * 60 * 60
    removed = 0
    try:
        for index, child in enumerate(root.iterdir()):
            if index >= max_scan or removed >= max_removals:
                break
            if not re.fullmatch(r"[0-9a-f]{32}", child.name):
                continue
            if child.is_symlink() or not child.is_dir():
                continue
            try:
                if child.stat().st_mtime >= cutoff:
                    continue
                shutil.rmtree(child)
                removed += 1
            except OSError:
                # A concurrent process may still own a temporary workspace.
                continue
    except OSError:
        pass
    return removed


def resumable_workspace_name(item: dict) -> str:
    """Stable, private workspace for yt-dlp .part fragments across failed attempts.

    Hash a short selection of transfer parameters (not titles or cookies) so a
    retry uses the same location without leaking a potentially signed URL.
    """
    key = json.dumps({name: item.get(name) for name in
                      ("url", "mode", "selectedQuality", "start_idx", "end_idx")},
                     sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def valid_url(value: str) -> bool:
    if not isinstance(value, str) or len(value) > 16384:
        return False
    try:
        parsed = urlsplit(value.strip())
        return parsed.scheme in ("https", "http") and bool(parsed.hostname) and not (
            parsed.username or parsed.password or any(c.isspace() for c in value)
        )
    except ValueError:
        return False


def inside_folder(child: Path, root: Path) -> bool:
    try:
        return child.resolve().is_relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return False


def is_twitch_vod_url(url: str) -> bool:
    """Recognize only actual Twitch VOD addresses, never similarly named hosts."""
    if not valid_url(url):
        return False
    parsed = urlsplit(url.strip())
    return (parsed.hostname or "").lower() in (
        "twitch.tv", "www.twitch.tv", "m.twitch.tv"
    ) and bool(re.fullmatch(r"/videos/[0-9]{5,20}/?", parsed.path or ""))


def category_for(item: dict) -> str:
    url = str(item.get("url", "")).lower()
    host = urlsplit(url).hostname or ""
    if item.get("is_channel"):
        return "CHAÎNES"
    if item.get("is_playlist"):
        return "PLAYLIST"
    if item.get("mode") == "Audio":
        return "AUDIOS"
    if item.get("mode") == "GIF":
        return "GIFS"
    if host in ("twitch.tv", "www.twitch.tv", "clips.twitch.tv", "m.twitch.tv"):
        return "TWITCH"
    if host in ("youtube.com", "www.youtube.com", "music.youtube.com", "youtu.be"):
        return "VIDÉOS"
    return "AUTRES"


def native_twitch_format(quality: str) -> str:
    """Sélection native sans interpolation ni montée artificielle en résolution."""
    match = re.search(r"(\d{3,4})p", str(quality))
    if match:
        height = int(match.group(1))
        if height not in (720, 1080):
            raise ValueError("Pour les VOD Twitch : 1080p ou 720p natif uniquement.")
        if height == 720:
            return "bestvideo[height=720]+bestaudio/best[height=720]"
    # "1080p" is the default preferred quality for Twitch; if the actual
    # source has no 1080p, request native 720p rather than failing or
    # upscaling a 720p stream. No 480p and no artificial conversion.
    return ("bestvideo[height=1080]+bestaudio/best[height=1080]/"
            "bestvideo[height=720]+bestaudio/best[height=720]")


def video_format(quality: str, is_twitch_vod: bool = False) -> str:
    if is_twitch_vod:
        return native_twitch_format(quality)
    match = re.search(r"(\d{3,4})p", str(quality))
    if not match:
        return "bestvideo+bestaudio/best"
    height = int(match.group(1))
    return (f"bestvideo[height<=?{height}]+bestaudio/"
            f"best[height<=?{height}]")


def should_emit_progress(percent: float, now: float, previous: float, previous_at: float) -> bool:
    """Avoid overwhelming Qt with repeated yt-dlp progress messages."""
    return (previous < 0 or percent >= 100 or percent < previous or
            percent - previous >= 1 or now - previous_at >= .5)


def _duration(value) -> str:
    try:
        seconds = max(0, int(value))
    except (TypeError, ValueError):
        return "00:00"
    return f"{seconds // 3600:02}:{(seconds // 60) % 60:02}:{seconds % 60:02}" if seconds >= 3600 else f"{seconds // 60:02}:{seconds % 60:02}"


class DownloaderAPI:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or app_root()).resolve()
        self.data = self.root / "Donnees"
        self.bin_dir = self.data / "bin"
        self.cache = self.data / "cache" / "yt-dlp"
        self.temp = self.data / "temporaires"
        self.config_path = self.data / "config.json"
        for directory in (self.data, self.bin_dir, self.cache, self.temp,
                          *(self.root / category for category in CATEGORIES)):
            directory.mkdir(parents=True, exist_ok=True)
        # Old interrupted yt-dlp workspaces can otherwise accumulate after a
        # crash. This bounded, idle startup cleanup never touches media folders.
        cleanup_old_workspaces(self.temp)
        if not os.access(self.root, os.W_OK):
            raise PermissionError("Le dossier All-Download est en lecture seule.")
        self._lock = threading.RLock()
        self._window = None
        self._running = False
        self._cancel = False
        self._paused = False
        self._current: subprocess.Popen | None = None
        try:
            raw = json.loads(self.config_path.read_text("utf-8"))
            self.config = raw if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            self.config = {}
        requested = self.config.get("download_folder", "")
        folder = Path(str(requested)).expanduser() if requested else self.root
        self.download_folder = str(folder.resolve()) if inside_folder(folder, self.root) else str(self.root)
        Path(self.download_folder).mkdir(parents=True, exist_ok=True)
        for cat in CATEGORIES:
            (Path(self.download_folder) / cat).mkdir(exist_ok=True)

    def _save(self) -> bool:
        payload = dict(self.config, download_folder=self.download_folder)
        candidate = self.config_path.with_name(self.config_path.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            with candidate.open("w", encoding="utf-8") as output:
                json.dump(payload, output, ensure_ascii=False, indent=2)
                output.flush()
                os.fsync(output.fileno())
            os.replace(candidate, self.config_path)
            return True
        except (OSError, TypeError, ValueError):
            return False
        finally:
            candidate.unlink(missing_ok=True)

    def _tool(self, name: str, required: bool = True) -> str:
        candidates = [self.bin_dir / name, self.root / "bin" / name]
        found = next((str(path) for path in candidates if path.is_file() and os.access(path, os.X_OK)), None)
        found = found or shutil.which(name)
        if not found and required:
            raise FileNotFoundError(f"{name} absent. Vérifiez le dossier bin/ de la version Linux.")
        return found or ""

    def _env(self):
        env = os.environ.copy()
        env["XDG_CACHE_HOME"] = str(self.data / "cache")
        env["DENO_DIR"] = str(self.data / "cache" / "deno")
        env["DENO_NO_UPDATE_CHECK"] = "1"
        return env

    def _js(self, fn: str, *args) -> None:
        window = self._window
        if window is not None:
            try:
                window.evaluate_js(fn + "(" + ", ".join(json.dumps(a, ensure_ascii=False) for a in args) + ")")
            except Exception:
                pass

    def check_linux_updates(self):
        from linux.update_check import check_linux_updates
        return check_linux_updates()

    def install_linux_launcher(self):
        from linux.desktop import install_linux_launcher
        return install_linux_launcher(self.root)

    def remove_linux_launcher(self):
        from linux.desktop import remove_linux_launcher
        return remove_linux_launcher()

    def get_download_folder(self):
        return self.download_folder

    def get_default_download_folder(self):
        return str(self.root)

    def browse_download_folder(self):
        if self._window is None:
            return None
        try:
            import webview
            paths = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=self.download_folder)
            if paths:
                selected = Path(paths[0]).resolve()
                return str(selected) if inside_folder(selected, self.root) else {
                    "error": "Choisissez All-Download ou un sous-dossier, pas un dossier extérieur."
                }
        except Exception:
            return {"error": "Le sélecteur de dossiers Linux n'est pas disponible."}
        return None

    def get_app_settings(self):
        saved = self.config.get("settings")
        return {**DEFAULTS, **saved} if isinstance(saved, dict) else dict(DEFAULTS)

    def save_quick_selector_value(self, kind, value):
        options = {"format": ("video_format", ("MP4", "MKV")),
                   "audio_rate": ("audio_sample_rate", ("source", "44100", "48000"))}
        if kind not in options or value not in options[kind][1]:
            return {"success": False, "error": "Option non valide."}
        key = options[kind][0]
        previous = dict(self.config)
        data = self.get_app_settings()
        data[key] = value
        self.config["settings"] = data
        if not self._save():
            self.config = previous
            return {"success": False, "error": "Impossible d'enregistrer."}
        return {"success": True, "value": value}

    def save_app_settings(self, settings_dict, download_folder=None):
        if not isinstance(settings_dict, dict) or not set(settings_dict).issubset(DEFAULTS):
            return {"success": False, "error": "Paramètres non reconnus."}
        requested = Path(str(download_folder or self.download_folder)).expanduser()
        if not requested.is_absolute() or not inside_folder(requested, self.root):
            return {"success": False, "error": "Le dossier doit rester à l'intérieur d'All-Download."}
        if self._running:
            return {"success": False, "error": "Terminez le téléchargement avant de modifier le dossier."}
        previous = dict(self.config)
        previous_folder = self.download_folder
        try:
            requested.mkdir(parents=True, exist_ok=True)
            for category in CATEGORIES:
                (requested / category).mkdir(exist_ok=True)
            check_name = requested / (".writable-" + uuid.uuid4().hex)
            with check_name.open("w") as check:
                check.write("")
            check_name.unlink()
        except OSError as error:
            return {"success": False, "error": f"Dossier non modifiable : {error}"}
        self.download_folder = str(requested.resolve())
        self.config["settings"] = {**DEFAULTS, **settings_dict}
        if not self._save():
            self.download_folder = previous_folder
            self.config = previous
            return {"success": False, "error": "Enregistrement impossible."}
        return {"success": True, "path": self.download_folder}

    def get_clipboard_text(self):
        for cmd in (["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"],
                    ["xsel", "--clipboard", "--output"]):
            if not shutil.which(cmd[0]):
                continue
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=2, check=False)
                if result.returncode == 0:
                    return result.stdout[:16384].decode("utf-8", "replace")
            except (OSError, subprocess.TimeoutExpired):
                continue
        return ""

    def open_folder(self):
        try:
            subprocess.Popen(["xdg-open", self.download_folder], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            return False

    def open_external(self, url):
        return bool(valid_url(url) and webbrowser.open(url))

    def get_auth_config(self):
        return {"cookie_file": self.config.get("cookie_file", ""),
                "cookie_browser": self.config.get("cookie_browser", "none")}

    def save_auth_config(self, file_path, browser):
        if browser not in ("none", "chrome", "firefox", "brave", "edge", "opera"):
            return False
        source = str(file_path or "").strip()
        if source and (not Path(source).is_file() or not inside_folder(Path(source), self.root)):
            return False
        previous = dict(self.config)
        self.config["cookie_file"] = source
        self.config["cookie_browser"] = browser
        if not self._save():
            self.config = previous
            return False
        return True

    def select_cookie_file(self):
        if self._window is None:
            return None
        try:
            import webview
            paths = self._window.create_file_dialog(webview.FileDialog.OPEN,
                                                     directory=str(self.root))
            if not paths:
                return None
            selected = Path(paths[0])
            # Reject oversized or non-regular files *before* allocating memory.
            if not selected.is_file() or selected.stat().st_size > 2_000_000:
                return None
            raw = selected.read_bytes()
            if len(raw) > 2_000_000 or not raw.lstrip().startswith(
                (b"# Netscape HTTP Cookie File", b"# HTTP Cookie File")
            ):
                return None
            destination = self.data / "cookies.txt"
            destination.write_bytes(raw)
            destination.chmod(0o600)
            return str(destination)
        except (OSError, ValueError, AttributeError):
            return None

    def _common_args(self, url, settings) -> list[str]:
        args = ["--cache-dir", str(self.cache), "--newline",
                "--progress-delta", "0.5",  # keep the Qt bridge responsive on long downloads
                "--socket-timeout", "20", "--retries", "5",
                "--fragment-retries", "5", "--continue", "--no-overwrites"]
        cookie_file = str(self.config.get("cookie_file") or "")
        if cookie_file and Path(cookie_file).is_file() and inside_folder(Path(cookie_file), self.root):
            args.extend(["--cookies", cookie_file])
        elif self.config.get("cookie_browser", "none") != "none":
            args.extend(["--cookies-from-browser", str(self.config["cookie_browser"])])
        if settings.get("proxy_toggle") and settings.get("proxy_url"):
            args.extend(["--proxy", str(settings["proxy_url"])])
        ua = USER_AGENTS.get(settings.get("impersonation"))
        if settings.get("impersonation") == "random":
            ua = USER_AGENTS["chrome_android14"]
        if ua:
            args.extend(["--user-agent", ua])
        extractor_args = settings.get("extractor_args", "")
        if isinstance(extractor_args, str) and len(extractor_args) <= 500:
            for entry in extractor_args.splitlines():
                if entry.strip():
                    args.extend(["--extractor-args", entry.strip()])
        host = (urlsplit(url).hostname or "").lower()
        if host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com"):
            deno = self._tool("deno", required=False)
            if deno:
                args.extend(["--js-runtimes", "deno:" + deno])
        return args

    def extract_info(self, raw_url):
        url = str(raw_url or "").strip()
        if not valid_url(url):
            return {"success": False, "error": "Lien HTTP(S) invalide."}
        try:
            from twitch_vod import twitch_vod_id, fallback_metadata, preferred_twitch_quality
            twitch = bool(twitch_vod_id(url))
        except ImportError:
            twitch = False
            fallback_metadata = None
            preferred_twitch_quality = None
        try:
            settings = self.get_app_settings()
            args = [self._tool("yt-dlp"), "--dump-single-json", "--no-warnings"]
            args += self._common_args(url, settings)
            is_youtube_video = bool("v=" in url or "youtu.be/" in url)
            is_playlist = not is_youtube_video and ("list=" in url or "/playlist" in url)
            is_channel = not is_youtube_video and any(x in url for x in ("/channel/", "/user/", "/c/", "/@"))
            if is_playlist or is_channel:
                args.extend(["--flat-playlist", "--playlist-end", "1000"])
            else:
                args.append("--no-playlist")
            run = subprocess.run(args + [url], stdin=subprocess.DEVNULL,
                                 capture_output=True, text=True, errors="replace",
                                 timeout=75, env=self._env())
            if run.returncode:
                if twitch and fallback_metadata is not None:
                    return {"success": True, "data": fallback_metadata(url)}
                return {"success": False, "error": (run.stderr.strip() or "Extraction impossible.")[-400:]}
            info = json.loads(run.stdout)
            heights = sorted({int(item["height"]) for item in info.get("formats", [])
                              if isinstance(item, dict) and isinstance(item.get("height"), int)
                              and item["height"] >= 144}, reverse=True)
            formats = ["Meilleure qualité (Auto)"] + [f"{h}p" for h in heights]
            if twitch and preferred_twitch_quality:
                preferred = preferred_twitch_quality(formats)
            else:
                preferred = formats[0]
            playlist_entries = info.get("entries", [])
            if not isinstance(playlist_entries, list):
                playlist_entries = []
            count = max(1, len(playlist_entries) or int(info.get("playlist_count") or 1))
            return {"success": True, "data": {
                "title": str(info.get("title") or info.get("id") or "Média")[:85],
                "thumbnail": str(info.get("thumbnail") or ""),
                "duration": _duration(info.get("duration")), "url": url, "mode": "Vidéo",
                "formats": formats, "selectedQuality": preferred,
                "selectedQualityLabel": preferred, "is_channel": is_channel,
                "channel_title": str(info.get("channel") or info.get("uploader") or "Chaîne"),
                "is_playlist": is_playlist, "playlist_title": str(info.get("title") or "Playlist"),
                "item_count": count, "start_idx": 1, "end_idx": count, "isError": False
            }}
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            return {"success": False, "error": str(error)[:400]}

    def _command(self, item, workspace: Path) -> list[str]:
        url = str(item.get("url", "")).strip()
        if not valid_url(url):
            raise ValueError("URL invalide.")
        settings = self.get_app_settings()
        target = Path(self.download_folder) / category_for(item)
        target.mkdir(parents=True, exist_ok=True)
        ffmpeg = self._tool("ffmpeg")
        cmd = [self._tool("yt-dlp")] + self._common_args(url, settings)
        cmd += ["--ffmpeg-location", str(Path(ffmpeg).parent),
                "-P", f"home:{target}", "-P", f"temp:{workspace}",
                "-o", "%(title).150B [%(id)s].%(ext)s"]
        playlist = bool(item.get("is_channel") or item.get("is_playlist"))
        if playlist:
            start = max(1, int(item.get("start_idx", 1)))
            end = max(start, min(1000, int(item.get("end_idx", 1000))))
            cmd += ["--yes-playlist", "--playlist-start", str(start), "--playlist-end", str(end),
                    "--ignore-errors"]
        else:
            cmd.append("--no-playlist")
        mode = item.get("mode", "Vidéo")
        quality = str(item.get("selectedQuality") or "Meilleure qualité (Auto)")
        if mode == "Audio":
            cmd += ["--extract-audio"]
            fmt = quality if quality in ("M4A", "FLAC", "MP3_320") else settings.get("audio_format", "FLAC")
            if fmt in ("MP3", "MP3_320"):
                cmd += ["--audio-format", "mp3", "--audio-quality", "320K"]
            else:
                cmd += ["--audio-format", fmt.lower() if fmt in ("M4A", "FLAC") else "flac"]
        elif mode == "GIF":
            cmd += ["-f", "bestvideo+bestaudio/best", "--recode-video", "gif"]
        else:
            is_twitch = is_twitch_vod_url(url)
            cmd += ["--format", video_format(quality, is_twitch)]
            container = "mkv" if settings.get("video_format") == "MKV" else "mp4"
            if not settings.get("video_origin_stream"):
                cmd += ["--merge-output-format", container]
            if settings.get("post_process_video") == "Remuxer":
                cmd += ["--remux-video", container]
        audio = mode == "Audio"
        if settings.get("audio_embed_thumb" if audio else "video_embed_thumb"):
            cmd.append("--embed-thumbnail")
        if settings.get("audio_write_thumb" if audio else "video_write_thumb"):
            cmd.append("--write-thumbnail")
        if settings.get("audio_add_metadata" if audio else "video_add_metadata"):
            cmd.append("--add-metadata")
        # Hostname must match exactly (or a genuine YouTube subdomain).
        # A forged hostname such as notyoutube.com must never receive
        # YouTube-only post-processing flags.
        host = (urlsplit(url).hostname or "").lower()
        youtube_host = host in ("youtube.com", "youtu.be") or host.endswith(".youtube.com")
        if mode == "Vidéo" and youtube_host:
            if settings.get("sponsor_enable"):
                remove = settings.get("sponsor_remove")
                if remove in ("sponsor", "all"):
                    cmd += ["--sponsorblock-remove", remove]
                if settings.get("sponsor_mark") == "chapters":
                    cmd += ["--sponsorblock-mark", "all"]
                if settings.get("exact_cut"):
                    cmd.append("--force-keyframes-at-cuts")
        return cmd + [url]

    def _terminate(self):
        proc = self._current
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGCONT)
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass

    def cancel_downloads(self):
        with self._lock:
            if not self._running:
                return False
            self._cancel = True
            self._paused = False
            self._terminate()
            return True

    def pause_downloads(self):
        with self._lock:
            if not self._running:
                return {"success": False, "error": "Aucun téléchargement actif."}
            self._paused = True
            if self._current and self._current.poll() is None:
                try:
                    os.killpg(self._current.pid, signal.SIGSTOP)
                except ProcessLookupError:
                    return {"success": True, "mode": "queue"}
                return {"success": True, "mode": "active"}
            return {"success": True, "mode": "queue"}

    def resume_downloads(self):
        with self._lock:
            if not self._running:
                return {"success": False, "error": "Aucune file active."}
            self._paused = False
            if self._current and self._current.poll() is None:
                try:
                    os.killpg(self._current.pid, signal.SIGCONT)
                except ProcessLookupError:
                    pass
            return {"success": True}

    def _worker(self, items):
        completed = 0
        total = len(items)
        try:
            for index, item in enumerate(items, 1):
                while self._paused and not self._cancel:
                    time.sleep(.15)
                if self._cancel:
                    break
                url = item["url"]
                workspace = self.temp / resumable_workspace_name(item)
                workspace.mkdir(parents=True, exist_ok=True)
                succeeded = False
                try:
                    cmd = self._command(item, workspace)
                    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            text=True, errors="replace", bufsize=1,
                                            env=self._env(), start_new_session=True)
                    with self._lock:
                        self._current = proc
                        if self._cancel:
                            self._terminate()
                        elif self._paused:
                            os.killpg(proc.pid, signal.SIGSTOP)
                    reason = ""
                    previous_pct, previous_at = -1.0, 0.0
                    if proc.stdout is not None:
                        with proc.stdout:
                            for line in proc.stdout:
                                if "ERROR:" in line:
                                    reason = line.strip()[-280:]
                                match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
                                if match:
                                    percent = float(match.group(1))
                                    now = time.monotonic()
                                    if should_emit_progress(percent, now, previous_pct, previous_at):
                                        self._js("updateDownloadProgress", percent,
                                                 f"[{index}/{total}] {line.strip()[:160]}")
                                        previous_pct, previous_at = percent, now
                    exit_code = proc.wait()
                    with self._lock:
                        self._current = None
                    if exit_code == 0 and not self._cancel:
                        succeeded = True
                        completed += 1
                        self._js("markDownloadSuccess", url)
                        if self.get_app_settings().get("notify") == "always":
                            self._js("showAppToast", "Téléchargé : " + str(item.get("title", "")))
                    elif not self._cancel:
                        self._js("markDownloadFailure", url, reason or f"yt-dlp : code {exit_code}")
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    self._js("markDownloadFailure", url, str(error)[:250])
                finally:
                    # A network failure must NOT discard yt-dlp's .part files.
                    # Reusing this workspace plus --continue enables best-effort
                    # resume. Explicit cancellation/success still release space.
                    # Startup cleanup removes unreferenced work older than 7 days.
                    if succeeded or self._cancel:
                        shutil.rmtree(workspace, ignore_errors=True)
            message = ("Annulé" if self._cancel else
                       f"Terminé : {completed}/{total} téléchargement(s)")
            self._js("updateDownloadProgress", 100 if not self._cancel else 0, message)
            if self.get_app_settings().get("notify") in ("always", "finish"):
                self._js("showAppToast", message)
        finally:
            with self._lock:
                self._current = None
                self._running = False
                self._paused = False
            self._js("finishDownloadUIState")

    def start_downloads(self, items):
        if not isinstance(items, list) or not items or len(items) > 300 or any(
            not isinstance(x, dict) or not valid_url(x.get("url", "")) for x in items
        ):
            return {"success": False, "error": "File invalide (maximum 300 URLs HTTP(S))."}
        with self._lock:
            if self._running:
                return {"success": False, "error": "Téléchargement déjà en cours."}
            try:
                self._tool("yt-dlp")
                self._tool("ffmpeg")
            except FileNotFoundError as error:
                return {"success": False, "error": str(error)}
            self._running = True
            self._cancel = False
            self._paused = False
        try:
            threading.Thread(target=self._worker, args=(list(items),),
                             daemon=True, name="AllDownload-Linux-Worker").start()
        except RuntimeError as error:
            with self._lock:
                self._running = False
            return {"success": False, "error": str(error)}
        return {"success": True}


def load_html() -> str:
    bundled = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    html_file = bundled / "ui.html"
    if html_file.is_file():
        html = html_file.read_text(encoding="utf-8")
    else:
        # Running from the repository reuses the exact Windows HTML source.
        from extract_ui import extract
        html = extract(Path(__file__).resolve().parents[1] / "yt_app.py")
    # Additional Linux-only controls; the Windows source remains unchanged.
    from linux.ui_extras import inject_linux_controls
    return inject_linux_controls(html)


def main() -> int:
    if not sys.platform.startswith("linux"):
        raise SystemExit("Ce lanceur est réservé à Linux.")
    import webview
    api = DownloaderAPI()
    html = load_html()
    theme = api.get_app_settings().get("theme", "dark")
    if theme not in ("light", "dark", "dark_pure"):
        theme = "dark"
    html = html.replace('<body class="theme-light" id="appBody">',
                        f'<body class="theme-{theme}" id="appBody">', 1)
    window = webview.create_window("All-Download Linux", html=html, js_api=api,
                                   width=1080, height=760, min_size=(920, 620),
                                   background_color={"light": "#f8fafc", "dark": "#141414",
                                                     "dark_pure": "#000000"}[theme])
    api._window = window
    def on_linux_window_closed(*_):
        # Interrupt yt-dlp/FFmpeg immediately instead of waiting for Qt to exit.
        api.cancel_downloads()
        api._window = None
    window.events.closed += on_linux_window_closed
    if "--smoke-ui" in sys.argv:
        def close_after_loaded(*_):
            threading.Thread(target=lambda: (time.sleep(1), window.destroy()),
                             daemon=True).start()
        window.events.loaded += close_after_loaded
    try:
        webview.start(gui="qt", debug=False, private_mode=True,
                      storage_path=str(api.data / "webview"))
    finally:
        # Also release children on a failed Qt startup / unexpected exit.
        api.cancel_downloads()
        api._window = None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
