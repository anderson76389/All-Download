import os
import sys
import gc
import re
import json
import time
import random
import urllib.request
import urllib.parse
import zipfile
import shutil
import subprocess
import threading
import traceback
import faulthandler
from datetime import datetime
import ctypes
from ctypes import wintypes
import multiprocessing
from pathlib import Path
import webview

# 1. Protection PyInstaller
if __name__ == '__main__':
    multiprocessing.freeze_support()

# 2. Chemins globaux
APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "AllMediaDownload")
BIN_DIR = os.path.join(APP_DIR, "bin")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
HTML_FILE = os.path.join(APP_DIR, "index.html")
CRASH_LOG = os.path.join(APP_DIR, "crash_log.txt")

os.makedirs(APP_DIR, exist_ok=True)
os.makedirs(BIN_DIR, exist_ok=True)

# 3. Sous PyInstaller (--noconsole), stdout/stderr peuvent etre None.
# Utiliser un vrai descripteur vers NUL plutot que fileno() = -1 :
# certaines dependances .NET/WebView2 interrogent fileno() au demarrage.
if sys.stdout is None or not hasattr(sys.stdout, "write"):
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None or not hasattr(sys.stderr, "write"):
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# 4. Diagnostic fiable : conserver l'historique des exceptions et
# capturer aussi les erreurs fatales du processus Python si possible.
# Le flux reste ouvert : faulthandler en a besoin pendant toute l'exécution.
_CRASH_STREAM = None
try:
    _CRASH_STREAM = open(CRASH_LOG, "a", encoding="utf-8", buffering=1)
    faulthandler.enable(file=_CRASH_STREAM, all_threads=True)
except (OSError, RuntimeError):
    _CRASH_STREAM = None

def handle_exception(exc_type, exc_value, exc_traceback):
    try:
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] Exception non gérée\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except Exception:
        pass

sys.excepthook = handle_exception
if hasattr(threading, 'excepthook'):
    threading.excepthook = lambda args: handle_exception(args.exc_type, args.exc_value, args.exc_traceback)

# 5. Reduire l'activite de fond de WebView2 sans forcer un seul processus
# de rendu et sans desactiver l'acceleration GPU (qui evite du CPU).
# Les arguments personnalisés fournis par l'utilisateur sont conservés.
os.environ.setdefault(
    "WEBVIEW2_ADDITIONAL_BROWSER_ARGS",
    "--disable-background-networking --disable-features=TranslateUI"
)

# 6. Support HiDPI Windows
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

YTDLP_PATH = os.path.join(BIN_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(BIN_DIR, "ffmpeg.exe")

YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

# L'ancien repertoire servait aussi de dossier de developpement/test.
# Ne plus enregistrer les nouveaux medias au milieu de yt_app.py, build, dist...
LEGACY_DOWNLOAD_BASE = os.path.join(os.path.expanduser("~"), "Downloads", "MediaDownloader")
DEFAULT_DOWNLOAD_BASE = os.path.join(os.path.expanduser("~"), "Downloads", "All-Download-Medias")

# Dossiers locaux, séparés du dépôt GitHub. Ne jamais écraser les anciens médias.
DOWNLOAD_CATEGORIES = ("AUTRES", "VIDÉOS", "CHAÎNES", "AUDIOS", "PLAYLIST", "GIFS")


def is_legacy_download_folder(path):
    """Reconnaitre uniquement l'ancien chemin par defaut, pas un dossier personnalise."""
    if not isinstance(path, str) or not path.strip():
        return False
    try:
        return os.path.normcase(os.path.abspath(os.path.expanduser(path))) == (
            os.path.normcase(os.path.abspath(LEGACY_DOWNLOAD_BASE))
        )
    except (OSError, ValueError, TypeError):
        return False


def choose_initial_download_folder(config):
    """Isoler les nouvelles sorties de l'ancien projet sans déplacer les médias.

    Une destination personnalisée reste prioritaire, sauf l'ancien répertoire
    MediaDownloader : celui-ci etait utilise comme dossier de test.
    """
    saved = config.get("download_folder")
    # Les deux éditions partagent config.json, mais pas leur destination
    # automatique : Portable près de l'EXE, Classique dans Téléchargements.
    # Seul un chemin choisi volontairement doit suivre les deux éditions.
    custom = config.get("download_folder_custom")
    if isinstance(saved, str) and saved.strip() and (
        custom is True or (
            custom is not False
            and not is_legacy_download_folder(saved)
            and os.path.normcase(os.path.abspath(saved)) != os.path.normcase(os.path.abspath(DEFAULT_DOWNLOAD_BASE))
        )
    ):
        return saved

    if getattr(sys, "frozen", False):
        executable_dir = os.path.dirname(os.path.abspath(sys.executable))
        # Ne jamais utiliser le dossier de l'ancien projet comme destination,
        # meme si celui-ci contient deja les six sous-dossiers.
        if is_legacy_download_folder(executable_dir):
            return DEFAULT_DOWNLOAD_BASE
        # L'édition installée écrit hors du répertoire de désinstallation.
        if os.path.isfile(os.path.join(executable_dir, ".all-download-installed")):
            return DEFAULT_DOWNLOAD_BASE
        if all(os.path.isdir(os.path.join(executable_dir, d)) for d in DOWNLOAD_CATEGORIES):
            try:
                import tempfile
                with tempfile.TemporaryFile(dir=executable_dir):
                    pass
                return executable_dir
            except OSError:
                pass
    return DEFAULT_DOWNLOAD_BASE

def ensure_media_directories(root):
    os.makedirs(root, exist_ok=True)

    # Mise à niveau AUDIO -> AUDIOS en conservant les téléchargements existants.
    old_dir = os.path.join(root, "AUDIO")
    audio_dir = os.path.join(root, "AUDIOS")
    if os.path.isdir(old_dir):
        if not os.path.exists(audio_dir):
            try:
                os.rename(old_dir, audio_dir)
            except OSError:
                pass
        if os.path.isdir(old_dir):
            # Si AUDIOS existe déjà, fusionner sans écraser les fichiers homonymes.
            for current_dir, _subdirs, files in os.walk(old_dir, topdown=False):
                relative_dir = os.path.relpath(current_dir, old_dir)
                destination = audio_dir if relative_dir == "." else os.path.join(audio_dir, relative_dir)
                for filename in files:
                    source = os.path.join(current_dir, filename)
                    target = os.path.join(destination, filename)
                    if not os.path.exists(target):
                        try:
                            os.makedirs(destination, exist_ok=True)
                            os.rename(source, target)
                        except OSError:
                            pass
                try:
                    os.rmdir(current_dir)  # Supprime uniquement les dossiers vides.
                except OSError:
                    pass

    for category in DOWNLOAD_CATEGORIES:
        os.makedirs(os.path.join(root, category), exist_ok=True)

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|]', "_", str(name)).strip()
    return clean if clean else "Media_Folder"

def get_media_download_dir(root, item):
    """Destination unique pour l'interface et les téléchargements."""
    url = str(item.get("url") or "")
    mode = item.get("mode", "Vidéo")
    is_yt = "youtube.com" in url.lower() or "youtu.be" in url.lower()
    direct_gif = bool(item.get("is_direct_download")) and urllib.parse.urlparse(url).path.lower().endswith(".gif")

    if mode == "GIF" or direct_gif:
        return os.path.join(root, "GIFS")
    if is_yt and item.get("is_channel") and item.get("channel_title"):
        return os.path.join(root, "CHAÎNES", sanitize_filename(item["channel_title"]))
    if is_yt and item.get("is_playlist") and item.get("playlist_title"):
        return os.path.join(root, "PLAYLIST", sanitize_filename(item["playlist_title"]))
    if mode == "Audio":
        return os.path.join(root, "AUDIOS")
    if is_yt:
        return os.path.join(root, "VIDÉOS")
    return os.path.join(root, "AUTRES")

def kill_process_tree(pid):
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def normalize_media_url(url):
    url = str(url).strip()
    if not url:
        return url

    if "x.com" in url:
        url = re.sub(r'https?://(?:www\.)?x\.com', 'https://twitter.com', url)

    if "pin.it" in url:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "facebookexternalhit/1.2 (+http://www.facebook.com/externalhit_uatext.php)"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                url = resp.geturl()
        except Exception:
            pass

    if "pinterest." in url:
        p_match = re.search(r'pinterest\.[a-z\.]+/pin/(\d+)', url)
        if p_match:
            pin_id = p_match.group(1)
            return f"https://www.pinterest.com/pin/{pin_id}/"

    return url

# Extracteur universel Pinterest (Évite le blocage RGPD 'Pinterest - France')
def extract_pinterest_direct(url):
    clean_url = normalize_media_url(url)
    pin_id_match = re.search(r'pin/(\d+)', clean_url)
    pin_id = pin_id_match.group(1) if pin_id_match else None

    widget_data = None
    if pin_id:
        try:
            w_url = f"https://widgets.pinterest.com/v3/pidgets/pins/info/?pin_ids={pin_id}"
            w_req = urllib.request.Request(w_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            })
            with urllib.request.urlopen(w_req, timeout=6) as resp:
                w_json = json.loads(resp.read().decode('utf-8', errors='replace'))
                pins = w_json.get("data", {}).get("pins", [])
                if pins:
                    widget_data = pins[0]
        except Exception:
            pass

    crawler_html = ""
    fetch_urls = [f"https://www.pinterest.com/pin/{pin_id}/"] if pin_id else []
    fetch_urls.append(clean_url)

    for f_url in fetch_urls:
        try:
            c_req = urllib.request.Request(f_url, headers={
                "User-Agent": "facebookexternalhit/1.2 (+http://www.facebook.com/externalhit_uatext.php)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9"
            })
            with urllib.request.urlopen(c_req, timeout=6) as resp:
                html = resp.read().decode('utf-8', errors='replace')
                if html and "Pinterest - France" not in html:
                    crawler_html = html
                    break
        except Exception:
            continue

    title = ""
    if widget_data:
        title = widget_data.get("description") or widget_data.get("title") or ""
    if not title and crawler_html:
        m_t = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', crawler_html, re.I)
        if m_t:
            title = m_t.group(1)
    if not title and crawler_html:
        m_t2 = re.search(r'<title>(.*?)</title>', crawler_html, re.I)
        if m_t2:
            title = m_t2.group(1)

    title = re.sub(r'\s*\|\s*Pinterest.*$', '', title, flags=re.I).strip()
    title = title.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"').strip()
    if not title or title.lower() in ["pinterest", "pinterest - france", "explore"]:
        title = f"Pinterest_Pin_{pin_id}" if pin_id else "Pinterest_Media"

    video_url = None
    if crawler_html:
        for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', crawler_html, re.DOTALL | re.I):
            try:
                ld = json.loads(m.group(1))
                if isinstance(ld, dict) and ld.get("@type") == "VideoObject":
                    video_url = ld.get("contentUrl")
                    break
            except Exception:
                pass

    if not video_url and crawler_html:
        m_v = re.search(r'<meta\s+property=["\']og:video(?::secure_url)?["\']\s+content=["\']([^"\']+)["\']', crawler_html, re.I)
        if m_v:
            video_url = m_v.group(1)

    if not video_url and crawler_html:
        v_matches = re.findall(r'https?://v\.pinimg\.com/videos/[^\s"\'<>]+\.mp4', crawler_html)
        if v_matches:
            v_matches.sort(key=lambda x: 1080 if "1080p" in x else (720 if "720p" in x else 360), reverse=True)
            video_url = v_matches[0]

    thumb_url = ""
    orig_img_url = ""
    if widget_data and "images" in widget_data:
        orig_img_url = widget_data.get("images", {}).get("orig", {}).get("url", "")
        thumb_url = orig_img_url

    if not orig_img_url and crawler_html:
        m_img = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', crawler_html, re.I)
        if m_img:
            thumb_url = m_img.group(1)
            orig_img_url = re.sub(r'/[0-9]+x[0-9]*/', '/originals/', thumb_url)
            orig_img_url = re.sub(r'/[0-9]+x/', '/originals/', orig_img_url)

    if not thumb_url and widget_data:
        thumb_url = widget_data.get("images", {}).get("236x", {}).get("url", "")

    is_video = bool(video_url)
    final_media_url = video_url if is_video else orig_img_url

    if not final_media_url:
        return None

    formats = ["720p", "480p", "360p"] if is_video else ["Qualité Originale"]

    return {
        "title": title[:82] + ("..." if len(title) > 85 else ""),
        "thumbnail": thumb_url or final_media_url,
        "duration": "00:30" if is_video else "00:00",
        "url": final_media_url,
        "mode": "Vidéo" if is_video else "Image",
        "formats": formats,
        "selectedQuality": formats[0],
        "selectedQualityLabel": f"{formats[0]} (Pinterest)" if is_video else "Qualité Originale",
        "is_channel": False,
        "channel_title": "Pinterest",
        "is_playlist": False,
        "playlist_title": "Pinterest",
        "item_count": 1,
        "start_idx": 1,
        "end_idx": 1,
        "is_direct_download": not is_video,
        "isError": False
    }

UA_MAP = {
    "chrome_win10": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "chrome_mac14": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "chrome_mac15": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "chrome_android14": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.135 Mobile Safari/537.36",
    "chrome_android12": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36",
    "edge_win10": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36 Edg/101.0.1210.53",
    "firefox_mac14_135": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:135.0) Gecko/20100101 Firefox/135.0",
    "firefox_mac14_133": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:133.0) Gecko/20100101 Firefox/133.0",
    "safari_ios18": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Mobile/15E148 Safari/604.1",
    "safari_mac15": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
}

# -------------------------------------------------------------
# INTERFACE HTML / CSS / JS
# -------------------------------------------------------------
HTML_PAGE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; }
  html, body { width: 100%; height: 100%; overflow: hidden; }

  .page-view { display: flex; flex-direction: column; width: 100%; height: 100%; }

  input, textarea, select { user-select: text !important; -webkit-user-select: text !important; pointer-events: auto !important; }
  button, .pill-dropdown, .dropdown-item, .popover-item, .ctx-item { cursor: pointer; user-select: none; }

  /* THÈMES */
  body.theme-light { background: #f8fafc; color: #0f172a; }
  body.theme-light .media-card, body.theme-light .input-wrapper, body.theme-light .card-adv, body.theme-light .log-banner, body.theme-light .btn-settings { background: #ffffff; border-color: #e2e8f0; color: #0f172a; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
  body.theme-light .url-input { color: #0f172a; }
  body.theme-light .card-title, body.theme-light .setting-sec-title, body.theme-light .setting-label, body.theme-light .section-title, body.theme-light .logs-title { color: #0f172a; }
  body.theme-light .pill-dropdown { background: #ffffff; color: #0f172a; border-color: #cbd5e1; }
  body.theme-light .pill-dropdown:hover, body.theme-light .pill-dropdown.active { border-color: #7c3aed; background: #f5f3ff; }
  body.theme-light .footer { background: #ffffff; border-color: #e2e8f0; }
  body.theme-light .tools-cluster, body.theme-light .trash-group { background: #f1f5f9; border-color: #cbd5e1; }
  body.theme-light .trash-main, body.theme-light .trash-arrow, body.theme-light .tool-cluster-btn { color: #475569; }
  body.theme-light .terminal-box { background: #ffffff; color: #1e293b; border-color: #e2e8f0; }
  body.theme-light .dropdown-popover, body.theme-light .popover-menu, body.theme-light .context-menu { background: #ffffff !important; color: #0f172a; border-color: #e2e8f0; box-shadow: 0 10px 25px rgba(0,0,0,0.08); }
  body.theme-light .dropdown-item, body.theme-light .popover-item, body.theme-light .ctx-item { color: #334155; }
  body.theme-light .dropdown-item:hover, body.theme-light .popover-item:hover, body.theme-light .ctx-item:hover { background: #f5f3ff; color: #7c3aed; }
  body.theme-light .dropdown-item.selected, body.theme-light .dropdown-item .check { color: #7c3aed; }
  body.theme-light .setting-input, body.theme-light .setting-textarea, body.theme-light .range-input { background: #ffffff; border-color: #cbd5e1; color: #0f172a; }
  body.theme-light .btn-add, body.theme-light .btn-download-all, body.theme-light .btn-dl-playlist { background: #7c3aed; color: #ffffff; }
  body.theme-light .btn-add:hover, body.theme-light .btn-download-all:hover, body.theme-light .btn-dl-playlist:hover { background: #6d28d9; }
  body.theme-light .tab-btn.active, body.theme-light .mode-pill-btn.active { background: #f5f3ff; color: #7c3aed; border-color: #7c3aed; }
  body.theme-light .center-cluster { border-color: #7c3aed; background: #ffffff; }
  body.theme-light .status-bar { background: #f5f3ff; color: #7c3aed; }
  body.theme-light .progress-fill { background: #7c3aed; }
  body.theme-light .v-separator, body.theme-light .bottom-v-separator { background: #e2e8f0; }
  body.theme-light .input-wrapper:focus-within { border-color: #7c3aed; }
  body.theme-light .card-act-btn { color: #64748b; }
  body.theme-light .card-act-btn:hover { background: #f1f5f9; color: #0f172a; }
  body.theme-light .card-meta, body.theme-light .setting-desc, body.theme-light .setting-subtext, body.theme-light .switch-desc, body.theme-light .playlist-count-text { color: #64748b; }
  body.theme-light .skeleton-card { background: #ffffff; border-color: #e2e8f0; }
  body.theme-light .skeleton-thumb { background: #f1f5f9; color: #94a3b8; }
  body.theme-light .skeleton-bar { background: #e2e8f0; }
  body.theme-light .skeleton-fill { background: #7c3aed; }
  body.theme-light .skeleton-status { color: #7c3aed; }

  body.theme-dark { background: #141414; color: #f3f4f6; }
  body.theme-dark .media-card, body.theme-dark .input-wrapper, body.theme-dark .card-adv, body.theme-dark .log-banner, body.theme-dark .btn-settings { background: #212121; border-color: #2e2e2e; color: #f3f4f6; }
  body.theme-dark .setting-input, body.theme-dark .setting-textarea, body.theme-dark .range-input { background: #212121; border-color: #2e2e2e; color: #f3f4f6; }
  body.theme-dark .footer { background: #1c1c1c; border-color: #282828; }
  body.theme-dark .url-input { color: #f3f4f6; }
  body.theme-dark .card-title, body.theme-dark .setting-sec-title, body.theme-dark .setting-label, body.theme-dark .section-title, body.theme-dark .logs-title { color: #f3f4f6; }
  body.theme-dark .pill-dropdown { background: #181818; border-color: #333333; color: #f3f4f6; }
  body.theme-dark .pill-dropdown:hover, body.theme-dark .pill-dropdown.active { border-color: #00e676; background: #222222; }
  body.theme-dark .dropdown-popover, body.theme-dark .popover-menu, body.theme-dark .context-menu { background: #1e1e1e !important; border-color: #333333; color: #f3f4f6; box-shadow: 0 10px 25px rgba(0,0,0,0.7); }
  body.theme-dark .dropdown-item, body.theme-dark .popover-item, body.theme-dark .ctx-item { color: #e5e7eb; }
  body.theme-dark .dropdown-item:hover, body.theme-dark .popover-item:hover, body.theme-dark .ctx-item:hover { background: #2a2a2a; color: #ffffff; }
  body.theme-dark .tools-cluster, body.theme-dark .trash-group { background: #262626; border-color: #333333; }
  body.theme-dark .trash-main, body.theme-dark .trash-arrow, body.theme-dark .tool-cluster-btn, body.theme-dark .card-act-btn { color: #d1d5db; }
  body.theme-dark .card-meta, body.theme-dark .setting-desc, body.theme-dark .setting-subtext, body.theme-dark .switch-desc, body.theme-dark .playlist-count-text { color: #9ca3af; }
  body.theme-dark .terminal-box { background: #0c0c0c; border-color: #222222; color: #cfcfcf; }
  body.theme-dark .v-separator, body.theme-dark .bottom-v-separator { background: #383838; }
  body.theme-dark .btn-add, body.theme-dark .btn-download-all, body.theme-dark .btn-dl-playlist { background: #00e676; color: #000000; }
  body.theme-dark .btn-add:hover, body.theme-dark .btn-download-all:hover, body.theme-dark .btn-dl-playlist:hover { background: #00c853; }
  body.theme-dark .tab-btn.active, body.theme-dark .mode-pill-btn.active { background: #0e301e; color: #00e676; border-color: #00e676; }
  body.theme-dark .center-cluster { border-color: #00e676; background: #242424; }
  body.theme-dark .status-bar { background: #0e301e; color: #00e676; }
  body.theme-dark .progress-fill { background: #00e676; }
  body.theme-dark .dropdown-item.selected, body.theme-dark .dropdown-item .check { color: #00e676; }
  body.theme-dark .skeleton-card { background: #212121; border-color: #2e2e2e; }
  body.theme-dark .skeleton-thumb { background: #181818; color: #6b7280; }
  body.theme-dark .skeleton-bar { background: #111111; }
  body.theme-dark .skeleton-fill { background: #00e676; }
  body.theme-dark .skeleton-status { color: #00e676; }
  body.theme-dark .input-wrapper:focus-within { border-color: #00e676; }

  body.theme-dark_pure { background: #000000; color: #f3f4f6; }
  body.theme-dark_pure .media-card, body.theme-dark_pure .input-wrapper, body.theme-dark_pure .card-adv, body.theme-dark_pure .log-banner, body.theme-dark_pure .btn-settings { background: #0d0d0d; border-color: #1f1f1f; color: #f3f4f6; }
  body.theme-dark_pure .setting-input, body.theme-dark_pure .setting-textarea, body.theme-dark_pure .range-input { background: #0d0d0d; border-color: #1f1f1f; color: #f3f4f6; }
  body.theme-dark_pure .footer { background: #080808; border-color: #1a1a1a; }
  body.theme-dark_pure .url-input { color: #f3f4f6; }
  body.theme-dark_pure .card-title, body.theme-dark_pure .setting-sec-title, body.theme-dark_pure .setting-label, body.theme-dark_pure .section-title, body.theme-dark_pure .logs-title { color: #f3f4f6; }
  body.theme-dark_pure .pill-dropdown { background: #080808; border-color: #1f1f1f; color: #f3f4f6; }
  body.theme-dark_pure .pill-dropdown:hover, body.theme-dark_pure .pill-dropdown.active { border-color: #00e676; background: #141414; }
  body.theme-dark_pure .dropdown-popover, body.theme-dark_popover-menu, body.theme-dark_pure .context-menu { background: #0d0d0d !important; border-color: #262626; color: #f3f4f6; box-shadow: 0 10px 25px rgba(0,0,0,0.85); }
  body.theme-dark_pure .dropdown-item, body.theme-dark_pure .popover-item, body.theme-dark_pure .ctx-item { color: #e5e7eb; }
  body.theme-dark_pure .dropdown-item:hover, body.theme-dark_pure .popover-item:hover, body.theme-dark_pure .ctx-item:hover { background: #1a1a1a; color: #ffffff; }
  body.theme-dark_pure .tools-cluster, body.theme-dark_pure .trash-group { background: #0d0d0d; border-color: #1f1f1f; }
  body.theme-dark_pure .trash-main, body.theme-dark_pure .trash-arrow, body.theme-dark_pure .tool-cluster-btn, body.theme-dark_pure .card-act-btn { color: #d1d5db; }
  body.theme-dark_pure .card-meta, body.theme-dark_pure .setting-desc, body.theme-dark_pure .setting-subtext, body.theme-dark_pure .switch-desc, body.theme-dark_pure .playlist-count-text { color: #9ca3af; }
  body.theme-dark_pure .terminal-box { background: #050505; border-color: #1a1a1a; color: #cfcfcf; }
  body.theme-dark_pure .v-separator, body.theme-dark_pure .bottom-v-separator { background: #222222; }
  body.theme-dark_pure .btn-add, body.theme-dark_pure .btn-download-all, body.theme-dark_pure .btn-dl-playlist { background: #00e676; color: #000000; }
  body.theme-dark_pure .btn-add:hover, body.theme-dark_pure .btn-download-all:hover, body.theme-dark_pure .btn-dl-playlist:hover { background: #00c853; }
  body.theme-dark_pure .tab-btn.active, body.theme-dark_pure .mode-pill-btn.active { background: #071a10; color: #00e676; border-color: #00e676; }
  body.theme-dark_pure .center-cluster { border-color: #00e676; background: #0d0d0d; }
  body.theme-dark_pure .status-bar { background: #071a10; color: #00e676; }
  body.theme-dark_pure .progress-fill { background: #00e676; }
  body.theme-dark_pure .dropdown-item.selected, body.theme-dark_pure .dropdown-item .check { color: #00e676; }
  body.theme-dark_pure .skeleton-card { background: #0d0d0d; border-color: #1f1f1f; }
  body.theme-dark_pure .skeleton-thumb { background: #050505; color: #4b5563; }
  body.theme-dark_pure .skeleton-bar { background: #050505; }
  body.theme-dark_pure .skeleton-fill { background: #00e676; }
  body.theme-dark_pure .skeleton-status { color: #00e676; }
  body.theme-dark_pure .input-wrapper:focus-within { border-color: #00e676; }

  .svg-icon { width: 16px; height: 16px; fill: currentColor; display: inline-block; vertical-align: middle; }
  .svg-icon-lg { width: 20px; height: 20px; fill: currentColor; }

  /* ANIMATION FLUIDE DES SWITCHES */
  .switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
    flex-shrink: 0;
  }
  .switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }
  .slider {
    position: absolute;
    cursor: pointer;
    top: 0; left: 0; right: 0; bottom: 0;
    background-color: #cbd5e1;
    transition: background-color 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    border-radius: 999px;
  }
  .slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: #ffffff;
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }
  input:checked + .slider {
    background-color: #7c3aed;
  }
  input:checked + .slider:before {
    transform: translateX(20px);
  }
  body.theme-dark .slider, body.theme-dark_pure .slider {
    background-color: #333333;
  }
  body.theme-dark input:checked + .slider, body.theme-dark_pure input:checked + .slider {
    background-color: #00e676;
  }
  body.theme-dark input:checked + .slider:before, body.theme-dark_pure input:checked + .slider:before {
    background-color: #000000;
  }

  /* ANIMATION DES ERREURS (-18 / PRIVÉ) */
  @keyframes errorShake {
    0%, 100% { transform: translateX(0); }
    20%, 60% { transform: translateX(-6px); }
    40%, 80% { transform: translateX(6px); }
  }
  .media-card.error {
    border-color: #ff4d4f !important;
    animation: errorShake 0.45s ease-in-out;
  }
  @keyframes pulseBadge {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.8; transform: scale(1.03); }
  }
  .error-badge {
    background: #ff4d4f; color: #fff; font-size: 11px; font-weight: 700;
    padding: 4px 12px; border-radius: 999px; display: inline-flex;
    align-items: center; gap: 6px; width: fit-content;
    animation: pulseBadge 1.8s infinite ease-in-out;
  }

  /* ANIMATION DE CHARGEMENT */
  @keyframes indeterminateBar {
    0% { transform: translateX(-100%); width: 35%; }
    50% { transform: translateX(100%); width: 60%; }
    100% { transform: translateX(300%); width: 35%; }
  }
  .progress-fill.indeterminate {
    position: absolute;
    height: 100%;
    border-radius: 999px;
    animation: indeterminateBar 1.3s infinite ease-in-out;
  }
  @keyframes btnSpin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  .btn-spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #ffffff;
    border-radius: 50%;
    display: inline-block;
    animation: btnSpin 0.8s linear infinite;
    margin-right: 6px;
    vertical-align: middle;
  }

  .app-container { max-width: 1800px; width: 100%; margin: 0 auto; display: flex; flex-direction: column; flex: 1; min-height: 0; padding: 0 clamp(16px, 2.5vw, 42px); }

  /* HEADER */
  .header { display: flex; padding: 18px 0; gap: 12px; align-items: center; width: 100%; flex-shrink: 0; }
  .input-wrapper { flex: 1; display: flex; align-items: center; border-radius: 999px; padding: 0 8px; overflow: hidden; transition: border-color 0.2s; position: relative; border-width: 1px; border-style: solid; height: 44px; }
  .url-input { flex: 1; background: transparent; border: none; padding: 10px 20px; font-size: 13.5px; outline: none; }

  .btn-add { border: none; font-weight: 700; font-size: 13.5px; padding: 10px 26px; border-radius: 999px; cursor: pointer; transition: background 0.15s, transform 0.05s; height: 44px; display: flex; align-items: center; justify-content: center; }
  .btn-add:active { transform: scale(0.98); }

  .btn-settings { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.15s; border-width: 1px; border-style: solid; }

  /* MENU CONTEXTUEL */
  .context-menu { position: fixed; border-radius: 12px; padding: 6px; display: none; flex-direction: column; width: 175px; z-index: 100000; }
  .context-menu.open { display: flex; }
  .ctx-item { background: transparent; border: none; padding: 9px 14px; text-align: left; font-size: 12.5px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 8px; }

  .main-content { flex: 1; min-height: 0; overflow-y: auto; padding: 4px 0 16px 0; position: relative; width: 100%; }
  .main-content::-webkit-scrollbar { width: 5px; }
  .main-content::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 999px; }
  body.theme-dark .main-content::-webkit-scrollbar-thumb, body.theme-dark_pure .main-content::-webkit-scrollbar-thumb { background: #383838; }

  .empty-view { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #888; }
  .empty-icon { font-size: 60px; margin-bottom: 12px; }
  .empty-title { font-size: 18px; font-weight: 700; margin-bottom: 4px; }
  .empty-sub { font-size: 12px; }

  .card-list { display: flex; flex-direction: column; gap: 12px; width: 100%; }
  .media-card { display: flex; border-radius: 14px; padding: 14px 16px; gap: 16px; align-items: center; position: relative; transition: border-color 0.2s; border-width: 1px; border-style: solid; min-height: 120px; width: 100%; }

  .thumb-container { position: relative; width: 160px; height: 100px; border-radius: 10px; overflow: hidden; background: #0e0e0e; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
  .thumb { width: 100%; height: 100%; object-fit: cover; }
  
  .card-body { flex: 1; display: flex; flex-direction: column; justify-content: space-between; min-height: 100px; min-width: 0; gap: 6px; }
  
  /* TITRE MULTI-LIGNES SUR SA PROPRE LIGNE */
  .card-title-row { width: 100%; }
  .card-title { font-size: 14.5px; font-weight: 700; white-space: normal; word-break: break-word; overflow-wrap: break-word; line-height: 1.35; max-height: 44px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; width: 100%; }

  .card-bottom-row { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: auto; }
  .card-controls { display: flex; gap: 10px; align-items: center; flex-shrink: 0; margin-left: auto; }

  /* CARTE PLAYLIST / CHAINE */
  .playlist-label { font-size: 12.5px; font-weight: 500; margin-top: 2px; }
  .playlist-range-row { display: flex; align-items: center; gap: 10px; }
  .playlist-range-row span { font-size: 12.5px; font-weight: 600; }
  .range-input { width: 75px; height: 32px; border-radius: 6px; border-width: 1px; border-style: solid; text-align: center; font-size: 13px; font-weight: 700; outline: none; }
  .btn-dl-playlist { border: none; padding: 8px 24px; border-radius: 6px; font-size: 13px; font-weight: 700; cursor: pointer; transition: all 0.15s; }

  .v-separator { width: 1px; height: 95px; align-self: center; flex-shrink: 0; margin: 0 4px; }
  .bottom-v-separator { width: 1px; height: 26px; align-self: center; flex-shrink: 0; margin: 0 2px; }

  /* DROPDOWNS */
  .pill-dropdown {
    position: relative;
    padding: 8px 18px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    transition: all 0.15s;
    border-width: 1px;
    border-style: solid;
    height: 38px;
  }

  .dropdown-popover {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    border-radius: 12px;
    padding: 6px;
    display: none;
    flex-direction: column;
    min-width: 165px;
    max-height: 260px;
    overflow-y: auto;
    z-index: 10000;
    border-width: 1px;
    border-style: solid;
    scrollbar-width: thin;
  }
  .dropdown-popover.open { display: flex; }
  .dropdown-popover.upward { top: auto; bottom: calc(100% + 6px); }
  .dropdown-popover::-webkit-scrollbar { width: 4px; }
  .dropdown-popover::-webkit-scrollbar-thumb { background: #475569; border-radius: 999px; }

  .dropdown-item { padding: 8px 14px; border-radius: 8px; font-size: 12.5px; display: flex; align-items: center; gap: 8px; cursor: pointer; transition: background 0.1s; white-space: nowrap; }

  .error-msg { font-size: 11px; color: #aaa; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 550px; }
  .btn-logs-card { background: #383133; border: none; color: #ddd; font-size: 11.5px; font-weight: 600; padding: 6px 14px; border-radius: 999px; cursor: pointer; width: fit-content; margin-top: 2px; }
  .card-meta { font-size: 12px; }

  /* BOUTONS CARTE */
  .card-actions { display: flex; flex-direction: column; gap: 6px; align-items: center; padding-left: 2px; }
  .card-act-btn { background: transparent; border: none; cursor: pointer; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: all 0.15s; }
  .card-act-btn:hover { background: rgba(125,125,125,0.15); color: #fff; }
  body.theme-light .card-act-btn:hover { color: #0f172a; }
  .card-act-btn.close:hover { color: #ff4d4f; background: rgba(255,77,79,0.15); }

  .skeleton-card { display: flex; border-radius: 14px; padding: 14px; gap: 14px; align-items: center; border-width: 1px; border-style: solid; width: 100%; }
  .skeleton-thumb { width: 160px; height: 100px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .skeleton-bar { height: 5px; border-radius: 999px; overflow: hidden; position: relative; margin-top: 6px; }
  .skeleton-fill { width: 40%; height: 100%; border-radius: 999px; animation: pulse 1.2s infinite ease-in-out; }
  @keyframes pulse { 0% { transform: translateX(-100%); } 100% { transform: translateX(300%); } }

  .footer { border-top-width: 1px; border-top-style: solid; display: flex; flex-direction: column; position: relative; z-index: 100; width: 100%; flex-shrink: 0; }
  .status-bar { font-size: 12.5px; font-weight: 600; padding: 6px 20px; text-align: center; }
  .progress-line { height: 3px; background: transparent; width: 100%; position: relative; }

  .actions-bar { display: flex; padding: 12px 24px; align-items: center; justify-content: space-between; gap: 14px; max-width: 1800px; margin: 0 auto; width: 100%; }
  .actions-left, .actions-center, .actions-right { display: flex; align-items: center; gap: 10px; }

  .tools-cluster { display: flex; border-width: 1px; border-style: solid; border-radius: 999px; padding: 3px; }
  .tool-cluster-btn { background: transparent; border: none; width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.15s; }

  .center-cluster { display: flex; border-width: 1px; border-style: solid; border-radius: 999px; padding: 3px 6px; gap: 6px; align-items: center; }
  .center-cluster .pill-dropdown { border: none; background: transparent; height: 36px; padding: 6px 14px; }

  .trash-group { display: flex; border-width: 1px; border-style: solid; border-radius: 999px; overflow: visible; position: relative; }
  .trash-main { border: none; background: transparent; padding: 9px 14px; cursor: pointer; display: flex; align-items: center; border-radius: 999px 0 0 999px; transition: all 0.15s; height: 42px; }
  .trash-main:hover { color: #ff4d4f; }
  .trash-arrow { border: none; border-left-width: 1px; border-left-style: solid; border-left-color: inherit; background: transparent; padding: 9px 12px; cursor: pointer; display: flex; align-items: center; border-radius: 0 999px 999px 0; transition: all 0.15s; height: 42px; }

  .btn-download-all { border: none; font-size: 13.5px; font-weight: 700; padding: 11px 28px; border-radius: 999px; cursor: pointer; transition: background 0.15s, transform 0.05s; height: 42px; display: flex; align-items: center; justify-content: center; }

  .popover-menu { position: absolute; bottom: calc(100% + 8px); right: 0; border-radius: 14px; padding: 6px; display: none; flex-direction: column; width: 250px; z-index: 99999; border-width: 1px; border-style: solid; }
  .popover-menu.open { display: flex; }
  .popover-item { background: transparent; border: none; padding: 8px 12px; text-align: left; font-size: 12px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 10px; }

  .switch-row { display: flex; flex-direction: column; gap: 4px; margin-bottom: 14px; }
  .switch-header { display: flex; justify-content: space-between; align-items: center; }
  .switch-label { font-size: 12px; font-weight: 600; }
  .switch-desc { font-size: 11px; line-height: 1.4; }

  /* PARAMÈTRES */
  .settings-header { display: flex; padding: 16px 24px; justify-content: space-between; align-items: center; border-bottom-width: 1px; border-bottom-style: solid; border-bottom-color: inherit; }
  .settings-nav { display: flex; gap: 8px; align-items: center; }
  .tab-btn { background: transparent; border: none; color: #888; font-weight: 600; font-size: 13px; padding: 7px 18px; border-radius: 999px; cursor: pointer; transition: all 0.15s; }
  .settings-content { flex: 1; overflow-y: auto; padding: 24px 32px; display: flex; flex-direction: column; gap: 20px; max-width: 1480px; margin: 0 auto; width: 100%; }
  
  .setting-section { display: flex; flex-direction: column; gap: 12px; margin-bottom: 10px; }
  .setting-sec-title { font-size: 15px; font-weight: 700; }
  .setting-sec-desc { font-size: 12px; margin-top: -8px; margin-bottom: 8px; }

  .setting-field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
  .setting-label { font-size: 12px; font-weight: 600; }
  .setting-subtext { font-size: 11px; }
  
  .mode-selector { display: flex; border-radius: 999px; padding: 3px; width: fit-content; gap: 4px; margin-bottom: 10px; border-width: 1px; border-style: solid; border-color: inherit; }
  .mode-pill-btn { background: transparent; border: none; color: #888; font-weight: 600; font-size: 12px; padding: 6px 18px; border-radius: 999px; cursor: pointer; }

  .setting-input { border-radius: 8px; padding: 10px 14px; font-size: 12px; outline: none; width: 100%; border-width: 1px; border-style: solid; }
  .setting-textarea { border-radius: 8px; padding: 10px 14px; font-size: 12px; outline: none; width: 100%; resize: vertical; min-height: 70px; font-family: monospace; border-width: 1px; border-style: solid; }

  /* LOGS */
  .logs-header { display: flex; padding: 16px 24px; justify-content: space-between; align-items: center; border-bottom-width: 1px; border-bottom-style: solid; border-bottom-color: inherit; }
  .logs-title { font-size: 15px; font-weight: 700; }
  .logs-content { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
  .section-title { font-size: 14px; font-weight: 700; margin-bottom: 4px; }
  .log-banner { display: flex; align-items: center; border-radius: 12px; padding: 12px 16px; gap: 12px; border: 1px solid #2b2b2b; }
  .badge-fail { background: #ff4d4f; color: #fff; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; }
  .badge-ok { background: #00e676; color: #000; width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 11px; }
  .banner-text { font-size: 12px; flex: 1; word-break: break-word; }
  .terminal-box { border: 1px solid #222; border-radius: 12px; padding: 14px; font-family: 'Consolas', monospace; font-size: 11px; height: 200px; overflow-y: auto; white-space: pre-wrap; line-height: 1.5; }

  /* AUTH */
  .auth-header { display: flex; padding: 16px 24px; justify-content: space-between; align-items: center; border-bottom-width: 1px; border-bottom-style: solid; border-bottom-color: inherit; }
  .auth-content { flex: 1; overflow-y: auto; padding: 24px 32px; display: flex; flex-direction: column; gap: 18px; max-width: 1320px; margin: 0 auto; width: 100%; }
  .badge-rec { background: #0284c7; color: #fff; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 999px; margin-left: 8px; }
  .card-adv { border-radius: 14px; overflow: hidden; transition: all 0.2s; border-width: 1px; border-style: solid; }
  .card-adv-header { padding: 16px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
  .card-adv-body { padding: 0 16px 16px 16px; display: none; }
  .card-adv.open .card-adv-body { display: block; }
  .card-adv.open .arrow-adv { transform: rotate(180deg); }
  .arrow-adv { transition: transform 0.2s; }
  .secret-box { background: #181b22; border: 1px solid #262d3d; border-radius: 12px; padding: 14px; display: flex; align-items: center; gap: 14px; margin-top: 10px; }
  .btn-secret-activate { background: #0284c7; border: none; color: #fff; font-weight: 700; font-size: 13px; padding: 8px 20px; border-radius: 999px; cursor: pointer; }

  /* Responsive sans changer le theme ni la structure des boutons. */
  .header, .settings-header, .logs-header, .auth-header { min-width: 0; }
  .settings-header, .logs-header, .auth-header { gap: 14px; flex-wrap: wrap; }
  .settings-nav { flex-wrap: wrap; justify-content: center; }
  .url-input, .input-wrapper, .card-body, .setting-field, .settings-content { min-width: 0; }
  .extra-quick-wrap { display: none; align-items: center; gap: 8px; min-width: 0; }
  .extra-quick-wrap label { font-size: 12px; font-weight: 600; white-space: nowrap; }
  .extra-quick-wrap select { max-width: 168px; padding: 7px 10px; }
  .app-toast { position: fixed; z-index: 120000; right: clamp(18px, 3vw, 44px); top: 18px; max-width: min(410px, calc(100vw - 36px)); padding: 13px 18px; border-radius: 12px; background: #242b38; color: #fff; font-size: 13px; box-shadow: 0 8px 30px rgba(0,0,0,0.25); display: none; overflow-wrap: anywhere; }
  .app-toast.visible { display: block; }
  @media (min-width: 1400px) {
    .header { padding-block: 22px; }
    .url-input { font-size: 15px; }
    .card-title { font-size: 16px; max-height: 50px; }
    .card-meta, .playlist-label { font-size: 13px; }
    .setting-sec-title { font-size: 18px; }
    .setting-label, .setting-input, .setting-textarea { font-size: 14px; }
    .setting-subtext, .switch-desc { font-size: 12px; }
    .empty-title { font-size: 22px; }
    .empty-sub { font-size: 14px; text-align: center; }
  }
  @media (min-width: 1580px) {
    #cardList[style*="display: flex"] {
      display: grid !important;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      align-content: start; gap: 18px;
    }
    .media-card { min-width: 0; }
    .thumb-container, .skeleton-thumb { width: clamp(160px, 11vw, 210px); height: clamp(100px, 7vw, 130px); }
    .settings-content { max-width: 1580px; }
    #setSectionTelech[style*="display: flex"],
    #setSectionAppli[style*="display: flex"],
    #setSectionReseau[style*="display: flex"] {
      display: grid !important;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      align-content: start; align-items: start; column-gap: clamp(30px, 4vw, 70px); row-gap: 18px;
    }
    .settings-content > .setting-section { min-width: 0; }
    .settings-content > div[style*="height:1px"] { display: none; }
  }
  @media (max-width: 1150px) {
    .actions-bar { flex-wrap: wrap; justify-content: center; row-gap: 10px; }
    .actions-center { order: -1; width: 100%; justify-content: center; }
    .actions-left, .actions-right { flex: 1 1 auto; }
    .actions-right { justify-content: flex-end; }
    .settings-header { padding: 12px 16px; }
  }
  @media (max-width: 760px) {
    .header { flex-wrap: wrap; gap: 8px; }
    .input-wrapper { flex-basis: 100%; }
    .media-card { flex-wrap: wrap; padding: 12px; }
    .card-body { flex: 1 1 270px; }
    .media-card .v-separator { display: none; }
    .card-actions { flex-direction: row; flex-wrap: wrap; margin-left: auto; }
    .card-bottom-row { align-items: flex-start; }
    .card-controls { flex-wrap: wrap; min-width: 0; }
    .empty-sub { padding: 0 12px; text-align: center; }
    .settings-content { padding: 18px 16px; }
    .settings-nav { order: 3; flex-basis: 100%; }
    .tab-btn { padding: 8px 12px; }
  }
</style>
</head>
<body class="theme-light" id="appBody">

  <!-- MENU CONTEXTUEL CLIC DROIT -->
  <div class="context-menu" id="inputContextMenu">
    <button class="ctx-item" onmousedown="copyUrlText(event)">📄 Copier</button>
    <button class="ctx-item" onmousedown="pasteFromClipboard(event)">📋 Coller l'URL</button>
    <button class="ctx-item" onmousedown="selectAllUrl(event)">🔍 Tout sélectionner</button>
    <button class="ctx-item" onmousedown="clearUrlInput(event)">✕ Effacer</button>
  </div>

  <div id="appToast" class="app-toast" role="status" aria-live="polite"></div>
  <!-- VUE 1 : PRINCIPALE -->
  <div class="page-view" id="viewMain">
    <div class="app-container">
      <div class="header">
        <div class="input-wrapper" id="inputWrapper" oncontextmenu="showContextMenu(event)">
          <input type="text" id="urlInput" class="url-input" placeholder="Entrez l'URL d'une vidéo/playlist/chaîne pour l'ajouter à la file d'attente" onkeydown="if(event.key==='Enter') addVideo()" oncontextmenu="showContextMenu(event)">
        </div>
        <button class="btn-add" onclick="addVideo()">Ajouter</button>
        <button class="btn-settings" onclick="showSettingsView()" title="Paramètres">
          <svg class="svg-icon-lg" viewBox="0 0 24 24"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>
        </button>
      </div>

      <div class="main-content" id="mainContent">
        <div class="empty-view" id="emptyView">
          <div class="empty-icon">
            <svg style="width:54px;height:54px;fill:currentColor;" viewBox="0 0 24 24"><path d="M4 12l1.41 1.41L11 7.83V20h2V7.83l5.58 5.59L20 12l-8-8-8 8z"/></svg>
          </div>
          <div class="empty-title">Votre file d'attente est vide</div>
          <div class="empty-sub">Ajoutez des vidéos, playlists ou chaînes entières pour commencer.</div>
        </div>
        <div class="card-list" id="cardList" style="display: none;"></div>
      </div>
    </div>

    <div class="footer">
      <div class="status-bar" id="statusBar">Prêt à télécharger ! 0 élément en file d'attente.</div>
      <div class="progress-line"><div class="progress-fill" id="progressFill"></div></div>
      
      <div class="actions-bar">
        <div class="actions-left">
          <div class="tools-cluster">
            <button class="tool-cluster-btn" onclick="openFolderSafe()" title="Ouvrir le dossier">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
            </button>
            <button class="tool-cluster-btn" onclick="showAuthView()" title="Authentification / Cookies">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/></svg>
            </button>
            <button class="tool-cluster-btn" onclick="showLogsView()" title="Journaux / Logs">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z"/></svg>
            </button>
          </div>
        </div>

        <div class="actions-center">
          <div class="center-cluster">
            <div class="pill-dropdown" id="globalModePill" onclick="toggleDropdown('globalModePopover', event)">
              <span id="globalModeText">Vidéo</span>
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>
              <div class="dropdown-popover upward" id="globalModePopover">
                <div class="dropdown-item selected" onclick="selectGlobalMode('Vidéo', event)"><span class="check">✓</span>Vidéo</div>
                <div class="dropdown-item" onclick="selectGlobalMode('Audio', event)"><span class="check"></span>Audio</div>
                <div class="dropdown-item" onclick="selectGlobalMode('GIF', event)"><span class="check"></span>GIF</div>
              </div>
            </div>

            <div class="bottom-v-separator"></div>

            <div class="pill-dropdown" id="globalQualPill" onclick="toggleDropdown('globalQualPopover', event)">
              <span id="globalQualText">Meilleure qualité (Auto)</span>
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>
              <div class="dropdown-popover upward" id="globalQualPopover"></div>
            </div>
          </div>
          <div class="extra-quick-wrap" id="extraQuickWrap">
            <label for="extraQuickValue" id="extraQuickLabel">Conteneur</label>
            <select id="extraQuickValue" class="setting-input" onchange="selectExtraQuickValue(this.value)"></select>
          </div>
        </div>

        <div class="actions-right">
          <div class="trash-group">
            <button class="trash-main" onclick="clearQueue()" title="Tout supprimer">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
            </button>
            <button class="trash-arrow" onclick="toggleTrashPopover(event)">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>
            </button>
            
            <div class="popover-menu" id="popoverMenu">
              <button class="popover-item" onclick="clearSuccess();">
                <svg class="svg-icon" viewBox="0 0 24 24"><path d="M19.36 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.64-4.96zM10 17l-3.5-3.5 1.41-1.41L10 14.17l5.59-5.59L17 10l-7 7z"/></svg>
                Supprimer les téléchargements réussis
              </button>
              <button class="popover-item" onclick="clearFailed();">
                <svg class="svg-icon" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
                Supprimer les échoués
              </button>
              <button class="popover-item" onclick="clearQueue();">
                <svg class="svg-icon" viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                Supprimer les en attente
              </button>
              <button class="popover-item" onclick="cancelDownloadsSafe(); closeAllPopovers();">
                <svg class="svg-icon" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                Annuler les téléchargements
              </button>
              <button class="popover-item" onclick="pauseDownloadsSafe(); closeAllPopovers();">
                <svg class="svg-icon" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                Tout mettre en pause
              </button>
              <button class="popover-item" onclick="resumeDownloadsSafe(); closeAllPopovers();">
                <svg class="svg-icon" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                Reprendre tout
              </button>
            </div>
          </div>

          <button class="btn-download-all" onclick="startDownloads()">Télécharger</button>
        </div>
      </div>
    </div>
  </div>

  <!-- VUE 2 : PARAMÈTRES -->
  <div class="page-view" id="viewSettings" style="display: none;">
    <div class="settings-header">
      <button class="btn-logs-card" style="padding: 8px 16px; font-size: 13px;" onclick="cancelSettings()">‹ Retour</button>
      <div class="settings-nav">
        <button class="tab-btn active" id="tabBtnTelech" onclick="switchSettingsTab('telech')">Téléchargement</button>
        <button class="tab-btn" id="tabBtnAppli" onclick="switchSettingsTab('appli')">Appli</button>
        <button class="tab-btn" id="tabBtnReseau" onclick="switchSettingsTab('reseau')">Réseau</button>
      </div>
      <button class="btn-download-all" style="padding: 8px 24px; height: 38px;" onclick="saveSettings()">Enregistrer</button>
    </div>

    <!-- ONGLET 1 : TÉLÉCHARGEMENT -->
    <div class="settings-content" id="setSectionTelech">
      <div class="setting-section">
        <div class="setting-sec-title">📂 Dossier des téléchargements</div>
        <div class="setting-sec-desc">Choisissez où enregistrer les médias. Les dossiers AUDIOS, VIDÉOS, GIFS, CHAÎNES, PLAYLIST et AUTRES seront créés automatiquement.</div>
        <div class="setting-field">
          <label class="setting-label" for="setDownloadFolder">Emplacement actuel :</label>
          <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            <input id="setDownloadFolder" type="text" class="setting-input" spellcheck="false" autocomplete="off" placeholder="C:\\Users\\...\\Téléchargements" style="flex:1 1 300px; min-width:220px;">
            <button type="button" class="btn-logs-card" onclick="browseDownloadFolder()" style="padding:10px 16px; white-space:nowrap;">Parcourir…</button>
            <button type="button" class="btn-logs-card" onclick="resetDownloadFolder()" style="padding:10px 16px; white-space:nowrap;">Par défaut</button>
          </div>
          <div class="setting-subtext">Vous pouvez choisir un dossier sur un autre disque (D:, E:, etc.) ou coller un chemin complet. Aucun fichier existant ne sera déplacé ni supprimé.</div>
          <div id="downloadFolderError" role="alert" aria-live="polite" style="display:none; color:#e35f5f; margin-top:8px; font-size:12px;"></div>
        </div>
      </div>
      <div class="setting-section">
        <div class="setting-sec-title">Sortie</div>
        <div class="setting-sec-desc">Configurer le type de fichiers téléchargés.</div>

        <div class="mode-selector">
          <button class="mode-pill-btn active" id="btnSortieVideo" onclick="setSortieMode('video')">Vidéo</button>
          <button class="mode-pill-btn" id="btnSortieAudio" onclick="setSortieMode('audio')">Audio</button>
        </div>

        <!-- OPTIONS VIDÉO -->
        <div id="sortieVideoFields">
          <div class="setting-field">
            <div class="setting-label">Format vidéo :</div>
            <select class="setting-input" id="setVideoFormat">
              <option value="MP4">MP4 (Meilleure compatibilité universelle)</option>
              <option value="MKV">MKV (Meilleure conservation des pistes / Haute fidélité)</option>
            </select>
            <div class="setting-subtext">Choisissez le conteneur vidéo préféré.</div>
          </div>

          <div class="setting-field">
            <div class="setting-label">Post-traitement vidéo :</div>
            <select class="setting-input" id="setPostProcessVideo">
              <option value="Aucun">Aucun</option>
              <option value="Remuxer">Remuxer en MP4</option>
              <option value="Normaliser">Normaliser l'audio</option>
            </select>
            <div class="setting-subtext">S'exécute une fois le téléchargement terminé.</div>
          </div>

          <div class="switch-row">
            <div class="switch-header">
              <div class="switch-label">Garder les flux d'origine</div>
              <label class="switch"><input type="checkbox" id="setVideoOriginStream"><span class="slider"></span></label>
            </div>
            <div class="switch-desc">Évite les changements de conteneur et le réencodage.</div>
          </div>

          <div class="switch-row">
            <div class="switch-header">
              <div class="switch-label">Ajouter l'image de couverture :</div>
              <label class="switch"><input type="checkbox" id="setVideoEmbedThumb" checked><span class="slider"></span></label>
            </div>
            <div class="switch-desc">Incorpore la miniature en qualité maximale dans la vidéo.</div>
          </div>

          <div class="switch-row">
            <div class="switch-header">
              <div class="switch-label">Enregistrer la miniature :</div>
              <label class="switch"><input type="checkbox" id="setVideoWriteThumb" checked><span class="slider"></span></label>
            </div>
            <div class="switch-desc">Télécharge la meilleure miniature disponible en JPG HD à côté de la vidéo.</div>
          </div>

          <div class="switch-row">
            <div class="switch-header">
              <div class="switch-label">Ajouter titre & artiste :</div>
              <label class="switch"><input type="checkbox" id="setVideoAddMetadata" checked><span class="slider"></span></label>
            </div>
            <div class="switch-desc">Écrit les métadonnées officielles dans le fichier vidéo.</div>
          </div>
        </div>

        <!-- OPTIONS AUDIO -->
        <div id="sortieAudioFields" style="display: none;">
          <div class="setting-field">
            <div class="setting-label">Format audio :</div>
            <select class="setting-input" id="setAudioFormat">
              <option value="FLAC">FLAC (Qualité Studio Master Lossless sans perte)</option>
              <option value="M4A">M4A (Format natif haute fidélité)</option>
              <option value="MP3">MP3 320 kbps (CBR Haute Définition maximale)</option>
            </select>
            <div class="setting-subtext">Choisissez le format audio préféré.</div>
          </div>

          <div class="setting-field">
            <div class="setting-label">Post-traitement audio :</div>
            <select class="setting-input" id="setPostProcessAudio">
              <option value="Aucun">Aucun</option>
              <option value="Normaliser">Normaliser l'audio (Loudnorm EBU R128)</option>
            </select>
            <div class="setting-subtext">S'exécute une fois le téléchargement terminé.</div>
          </div>

          <div class="switch-row">
            <div class="switch-header">
              <div class="switch-label">Ajouter l'image de couverture (pochette) :</div>
              <label class="switch"><input type="checkbox" id="setAudioEmbedThumb" checked><span class="slider"></span></label>
            </div>
            <div class="switch-desc">Incorpore la pochette dans les tags ID3/FLAC du fichier audio.</div>
          </div>

          <div class="switch-row">
            <div class="switch-header">
              <div class="switch-label">Enregistrer la miniature séparée :</div>
              <label class="switch"><input type="checkbox" id="setAudioWriteThumb" checked><span class="slider"></span></label>
            </div>
            <div class="switch-desc">Enregistre l'image de la miniature en JPG HD à côté du fichier audio.</div>
          </div>

          <div class="switch-row">
            <div class="switch-header">
              <div class="switch-label">Ajouter titre & artiste :</div>
              <label class="switch"><input type="checkbox" id="setAudioAddMetadata" checked><span class="slider"></span></label>
            </div>
            <div class="switch-desc">Écrit les tags audio ID3 officiels (artiste, titre, album).</div>
          </div>
        </div>
      </div>

      <div style="height:1px; background:inherit; border-top:1px solid rgba(125,125,125,0.2); margin:10px 0;"></div>

      <div class="setting-section">
        <div class="setting-sec-title">SponsorBlock</div>
        <div class="setting-sec-desc">Supprimer ou marquer les segments sponsorisés via l'API officielle.</div>

        <div class="switch-row">
          <div class="switch-header">
            <div class="switch-label">Activer SponsorBlock :</div>
            <label class="switch"><input type="checkbox" id="setSponsorEnable" checked><span class="slider"></span></label>
          </div>
          <div class="switch-desc">Supprime automatiquement les segments sponsorisés et auto-promos sur YouTube.</div>
        </div>

        <div class="setting-field">
          <div class="setting-label">Parties à supprimer</div>
          <select class="setting-input" id="setSponsorRemove">
            <option value="sponsor">Uniquement les segments publicitaires intégrés</option>
            <option value="all">Tous les segments sponsors, intros, outros & auto-promos</option>
            <option value="none">Aucune partie à supprimer</option>
          </select>
        </div>

        <div class="setting-field">
          <div class="setting-label">Parties à marquer</div>
          <select class="setting-input" id="setSponsorMark">
            <option value="none">Ne pas marquer de chapitres</option>
            <option value="chapters">Créer des chapitres automatiques pour chaque section</option>
          </select>
        </div>

        <div class="setting-field">
          <div class="setting-label">URL de l'API</div>
          <input type="text" class="setting-input" id="setSponsorApi" value="https://sponsor.ajay.app">
        </div>

        <div class="switch-row">
          <div class="switch-header">
            <div class="switch-label">Découpe précise :</div>
            <label class="switch"><input type="checkbox" id="setExactCut"><span class="slider"></span></label>
          </div>
          <div class="switch-desc">Force la découpe sur les images clés exactes via FFmpeg.</div>
        </div>
      </div>
    </div>

    <!-- ONGLET 2 : APPLI -->
    <div class="settings-content" id="setSectionAppli" style="display: none;">
      <div class="setting-section">
        <div class="setting-sec-title">Apparence</div>
        <div class="setting-sec-desc">Configurer l'aspect et le ressenti de l'application.</div>

        <div class="setting-field">
          <div class="setting-label">Thème :</div>
          <select class="setting-input" id="setTheme" onchange="previewTheme(this.value)">
            <option value="light">Clair</option>
            <option value="dark">Sombre</option>
            <option value="dark_pure">Sombre Oled</option>
          </select>
        </div>

        <div class="setting-field">
          <div class="setting-label">Sélecteur supplémentaire :</div>
          <select class="setting-input" id="setExtraSelector">
            <option value="none">Aucun</option>
            <option value="format">Format de conteneur</option>
            <option value="audio_rate">Échantillonnage audio</option>
          </select>
          <div class="setting-subtext">Affiche un choix rapide dans la barre du bas : MP4/MKV en mode Vidéo, ou 44,1/48 kHz en mode Audio. La fréquence ne restaure pas la qualité de la source.</div>
        </div>
      </div>

      <div style="height:1px; background:inherit; border-top:1px solid rgba(125,125,125,0.2); margin:10px 0;"></div>

      <div class="setting-section">
        <div class="setting-sec-title">Notifications</div>
        <div class="setting-sec-desc">Affiche un message discret dans All-Download à la fin des téléchargements, sans processus supplémentaire.</div>

        <div class="setting-field">
          <div class="setting-label">Afficher les notifications :</div>
          <select class="setting-input" id="setNotify">
            <option value="never">Jamais</option>
            <option value="finish">Uniquement à la fin du téléchargement</option>
            <option value="always">Toujours</option>
          </select>
        </div>
      </div>
    </div>

    <!-- ONGLET 3 : RÉSEAU -->
    <div class="settings-content" id="setSectionReseau" style="display: none;">
      <div class="setting-section">
        <div class="setting-sec-title">Réseau</div>
        <div class="setting-sec-desc">Configurer comment l'application se connecte à Internet.</div>

        <div class="switch-row">
          <div class="switch-header">
            <div class="switch-label">Se connecter via un proxy :</div>
            <label class="switch"><input type="checkbox" id="setProxyToggle"><span class="slider"></span></label>
          </div>
        </div>

        <div class="setting-field">
          <div class="setting-label">Configuration du proxy :</div>
          <input type="text" class="setting-input" id="setProxyUrl" placeholder="socks5://user:pass@127.0.0.1:1080/">
        </div>

        <div class="setting-field">
          <div class="setting-label">Impersonation :</div>
          <select class="setting-input" id="setImpersonation">
            <option value="none">✓ Ne pas simuler</option>
            <option value="random">Simuler un client aléatoire</option>
            <option value="chrome_win10">Chrome 131 - Windows 10</option>
            <option value="chrome_mac14">Chrome 131 - macOS 14</option>
            <option value="chrome_mac15">Chrome 133 - macOS 15</option>
            <option value="chrome_android14">Chrome 131 - Android 14</option>
            <option value="chrome_android12">Chrome 99 - Android 12</option>
            <option value="edge_win10">Edge 101 - Windows 10</option>
            <option value="firefox_mac14_135">Firefox 135 - macOS 14</option>
            <option value="firefox_mac14_133">Firefox 133 - macOS 14</option>
            <option value="safari_ios18">Safari 18.4 - iOS 18.4</option>
            <option value="safari_mac15">Safari 18.0 - macOS 15</option>
          </select>
          <div class="setting-subtext">Simuler un OS ou navigateur pour contourner les restrictions.</div>
        </div>

        <div class="setting-field">
          <div class="setting-label">Arguments d'extracteur :</div>
          <textarea class="setting-textarea" id="setExtractorArgs" placeholder="youtube:player_js_variant=main"></textarea>
        </div>
      </div>
    </div>
  </div>

  <!-- VUE 3 : LOGS -->
  <div class="page-view" id="viewLogs" style="display: none;">
    <div class="logs-header">
      <button class="btn-logs-card" style="padding: 8px 16px; font-size: 13px;" onclick="openView('viewMain')">‹ Retour</button>
      <div class="logs-title">Journaux</div>
      <button class="btn-download-all" onclick="openView('viewMain'); startDownloads();">Télécharger</button>
    </div>

    <div class="logs-content">
      <div class="section-title" id="errHeader">Erreurs (0)</div>
      <div id="errList" style="display: flex; flex-direction: column; gap: 8px;"></div>

      <div class="section-title">Éléments ignorés (0)</div>
      <div class="log-banner">
        <div class="badge-ok">✓</div>
        <div class="banner-text">Aucun élément n'a été ignoré par les filtres.</div>
      </div>

      <div class="section-title">Avertissements (0)</div>
      <div class="log-banner">
        <div class="badge-ok">✓</div>
        <div class="banner-text">Aucun avertissement trouvé.</div>
      </div>

      <div class="section-title">Tous les journaux</div>
      <div class="terminal-box" id="terminalOutput">En attente d'opérations...</div>
    </div>
  </div>

  <!-- VUE 4 : AUTH -->
  <div class="page-view" id="viewAuth" style="display: none;">
    <div class="auth-header">
      <button class="btn-logs-card" style="padding: 8px 16px; font-size: 13px;" onclick="openView('viewMain')">‹ Retour</button>
      <div style="font-size: 15px; font-weight: 700;">Authentification</div>
      <button class="btn-download-all" style="padding: 8px 20px;" onclick="saveAuth()">Enregistrer</button>
    </div>

    <div class="auth-content">
      <div>
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
          <span style="font-size: 14px; font-weight: 700;">Cookies</span>
          <span class="badge-rec">Recommandé</span>
        </div>
        <div style="font-size: 12px; color: #888; margin-bottom: 16px;">
          Utiliser des sessions connectées depuis un fichier cookies ou importer depuis votre navigateur.
        </div>

        <div style="font-size: 12px; font-weight: 600; margin-bottom: 6px;">Charger les cookies depuis un fichier cookies.txt</div>
        <div style="display: flex; gap: 8px; margin-bottom: 18px;">
          <input type="text" id="cookieFile" class="url-input" style="border-radius: 8px; font-size: 12px;" placeholder="Sélectionnez un fichier..." readonly>
          <button class="btn-add" style="border-radius: 8px; padding: 6px 16px;" onclick="chooseCookieFile()">Parcourir</button>
          <button class="btn-logs-card" style="border-radius: 8px; padding: 6px 14px; margin-top:0;" onclick="clearCookieFile()" title="Effacer le fichier pour utiliser le navigateur">✕ Effacer</button>
        </div>

        <div style="font-size: 12px; font-weight: 600; margin-bottom: 6px;">Charger automatiquement les cookies depuis un navigateur :</div>
        <div class="pill-dropdown" id="browserSelectPill" style="width:100%; border-radius:10px; padding:10px 14px; justify-content:space-between;" onclick="toggleDropdown('browserSelectPopover', event)">
          <span id="browserSelectText">Ne pas charger les cookies depuis un navigateur</span>
          <svg class="svg-icon" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>
          <div class="dropdown-popover" style="width:100%;" id="browserSelectPopover">
            <div class="dropdown-item selected" onclick="selectBrowser('none', 'Ne pas charger les cookies depuis un navigateur', event)"><span class="check">✓</span>Ne pas charger les cookies depuis un navigateur</div>
            <div class="dropdown-item" onclick="selectBrowser('chrome', 'Google Chrome', event)"><span class="check"></span>Google Chrome</div>
            <div class="dropdown-item" onclick="selectBrowser('firefox', 'Mozilla Firefox', event)"><span class="check"></span>Mozilla Firefox</div>
            <div class="dropdown-item" onclick="selectBrowser('brave', 'Brave', event)"><span class="check"></span>Brave</div>
            <div class="dropdown-item" onclick="selectBrowser('edge', 'Microsoft Edge', event)"><span class="check"></span>Microsoft Edge</div>
            <div class="dropdown-item" onclick="selectBrowser('opera', 'Opera', event)"><span class="check"></span>Opera</div>
          </div>
        </div>
      </div>
    </div>
  </div>

<script>
  let queue = [];
  let terminalLogs = [];
  let currentBrowser = 'none';
  let activeSavedTheme = 'light';
  let currentGlobalMode = 'Vidéo';
  let currentGlobalQuality = 'Meilleure qualité (Auto)';

  function callApi(method, ...args) {
    if (window.pywebview && window.pywebview.api && typeof window.pywebview.api[method] === 'function') {
      return window.pywebview.api[method](...args);
    }
    return Promise.resolve(null);
  }

  function openView(viewId) {
    document.querySelectorAll('.page-view').forEach(p => p.style.display = 'none');
    const target = document.getElementById(viewId);
    if (target) target.style.display = 'flex';
    closeAllPopovers();
  }

  document.addEventListener('click', function(e) {
    if (!e.target.closest('.pill-dropdown') && !e.target.closest('.trash-group') && !e.target.closest('.context-menu')) {
      closeAllPopovers();
    }
  });

  function closeAllPopovers() {
    document.querySelectorAll('.dropdown-popover').forEach(p => p.classList.remove('open'));
    document.querySelectorAll('.pill-dropdown').forEach(p => p.classList.remove('active'));
    const trashPop = document.getElementById('popoverMenu');
    if (trashPop) trashPop.classList.remove('open');
    hideContextMenu();
  }

  function toggleDropdown(popId, e) {
    if (e) { e.stopPropagation(); }
    const pop = document.getElementById(popId);
    if (!pop) return;
    const wasOpen = pop.classList.contains('open');
    closeAllPopovers();
    if (!wasOpen) {
      pop.classList.add('open');
      if (pop.parentElement && pop.parentElement.classList.contains('pill-dropdown')) {
        pop.parentElement.classList.add('active');
      }
    }
  }

  function toggleTrashPopover(e) {
    if (e) { e.stopPropagation(); }
    const p = document.getElementById('popoverMenu');
    if (!p) return;
    const wasOpen = p.classList.contains('open');
    closeAllPopovers();
    if (!wasOpen) {
      p.classList.add('open');
    }
  }

  function showContextMenu(e) {
    e.preventDefault();
    e.stopPropagation();
    closeAllPopovers();
    const menu = document.getElementById('inputContextMenu');
    menu.style.left = Math.min(e.clientX, window.innerWidth - 180) + 'px';
    menu.style.top = Math.min(e.clientY, window.innerHeight - 130) + 'px';
    menu.classList.add('open');
  }

  function hideContextMenu() {
    const menu = document.getElementById('inputContextMenu');
    if (menu) menu.classList.remove('open');
  }

  function copyUrlText(e) {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    const input = document.getElementById('urlInput');
    if (input.value) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(input.value).catch(() => {
          input.select();
          document.execCommand('copy');
        });
      } else {
        input.select();
        document.execCommand('copy');
      }
    }
    hideContextMenu();
  }

  function selectAllUrl(e) {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    const input = document.getElementById('urlInput');
    input.focus();
    input.select();
    hideContextMenu();
  }

  function clearUrlInput(e) {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    const input = document.getElementById('urlInput');
    input.value = '';
    input.focus();
    hideContextMenu();
  }

  function pasteFromClipboard(e) {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    hideContextMenu();
    const input = document.getElementById('urlInput');
    
    if (navigator.clipboard && navigator.clipboard.readText) {
      navigator.clipboard.readText().then(text => {
        if (text && text.trim().length > 0) {
          input.value = text.trim();
          input.focus();
        } else {
          fallbackPythonPaste();
        }
      }).catch(() => {
        fallbackPythonPaste();
      });
    } else {
      fallbackPythonPaste();
    }
  }

  function fallbackPythonPaste() {
    callApi('get_clipboard_text').then(text => {
      if (text && typeof text === 'string' && text.trim().length > 0) {
        const input = document.getElementById('urlInput');
        input.value = text.trim();
        input.focus();
      }
    });
  }

  function appendTerminal(msg) {
    terminalLogs.push(msg);
    if (terminalLogs.length > 250) terminalLogs.shift();
    const box = document.getElementById('terminalOutput');
    if (box) {
      box.innerText = terminalLogs.join('\\n');
      box.scrollTop = box.scrollHeight;
    }
  }

  function applyTheme(themeVal) {
    activeSavedTheme = themeVal;
    const body = document.getElementById('appBody');
    body.className = '';
    if (themeVal === 'dark') body.classList.add('theme-dark');
    else if (themeVal === 'dark_pure') body.classList.add('theme-dark_pure');
    else body.classList.add('theme-light');
  }

  function previewTheme(themeVal) {
    const body = document.getElementById('appBody');
    body.className = '';
    if (themeVal === 'dark') body.classList.add('theme-dark');
    else if (themeVal === 'dark_pure') body.classList.add('theme-dark_pure');
    else body.classList.add('theme-light');
  }

  function updateGlobalQualityDropdown() {
    const pop = document.getElementById('globalQualPopover');
    if (!pop) return;

    if (currentGlobalMode === 'Audio') {
      pop.innerHTML = `
        <div class="dropdown-item ${currentGlobalQuality==='FLAC'?'selected':''}" onclick="selectGlobalQual('FLAC', 'FLAC (Studio Master)', event)"><span class="check">${currentGlobalQuality==='FLAC'?'✓':''}</span>FLAC (Studio Master)</div>
        <div class="dropdown-item ${currentGlobalQuality==='M4A'?'selected':''}" onclick="selectGlobalQual('M4A', 'M4A (Format natif)', event)"><span class="check">${currentGlobalQuality==='M4A'?'✓':''}</span>M4A (Format natif)</div>
        <div class="dropdown-item ${currentGlobalQuality==='MP3_320'?'selected':''}" onclick="selectGlobalQual('MP3_320', 'MP3 (320 kbps)', event)"><span class="check">${currentGlobalQuality==='MP3_320'?'✓':''}</span>MP3 (320 kbps)</div>
      `;
    } else if (currentGlobalMode === 'GIF') {
      pop.innerHTML = `
        <div class="dropdown-item ${currentGlobalQuality==='GIF'?'selected':''}" onclick="selectGlobalQual('GIF', 'GIF (Haute Qualité)', event)"><span class="check">${currentGlobalQuality==='GIF'?'✓':''}</span>GIF (Haute Qualité)</div>
        <div class="dropdown-item ${currentGlobalQuality==='GIF_30'?'selected':''}" onclick="selectGlobalQual('GIF_30', 'GIF (Fluide 30fps)', event)"><span class="check">${currentGlobalQuality==='GIF_30'?'✓':''}</span>GIF (Fluide 30fps)</div>
      `;
    } else {
      pop.innerHTML = `
        <div class="dropdown-item ${currentGlobalQuality==='Meilleure qualité (Auto)'?'selected':''}" onclick="selectGlobalQual('Meilleure qualité (Auto)', 'Meilleure qualité (Auto)', event)"><span class="check">${currentGlobalQuality==='Meilleure qualité (Auto)'?'✓':''}</span>Meilleure qualité (Auto)</div>
        <div class="dropdown-item ${currentGlobalQuality==='2160p (4K UHD)'?'selected':''}" onclick="selectGlobalQual('2160p (4K UHD)', '2160p (4K UHD)', event)"><span class="check">${currentGlobalQuality==='2160p (4K UHD)'?'✓':''}</span>2160p (4K UHD)</div>
        <div class="dropdown-item ${currentGlobalQuality==='1440p (2K QHD)'?'selected':''}" onclick="selectGlobalQual('1440p (2K QHD)', '1440p (2K QHD)', event)"><span class="check">${currentGlobalQuality==='1440p (2K QHD)'?'✓':''}</span>1440p (2K QHD)</div>
        <div class="dropdown-item ${currentGlobalQuality==='1080p (Full HD)'?'selected':''}" onclick="selectGlobalQual('1080p (Full HD)', '1080p (Full HD)', event)"><span class="check">${currentGlobalQuality==='1080p (Full HD)'?'✓':''}</span>1080p (Full HD)</div>
        <div class="dropdown-item ${currentGlobalQuality==='720p (HD)'?'selected':''}" onclick="selectGlobalQual('720p (HD)', '720p (HD)', event)"><span class="check">${currentGlobalQuality==='720p (HD)'?'✓':''}</span>720p (HD)</div>
        <div class="dropdown-item ${currentGlobalQuality==='480p (SD)'?'selected':''}" onclick="selectGlobalQual('480p (SD)', '480p (SD)', event)"><span class="check">${currentGlobalQuality==='480p (SD)'?'✓':''}</span>480p (SD)</div>
      `;
    }
  }

  function selectGlobalMode(mode, e) {
    if (e) { e.stopPropagation(); }
    currentGlobalMode = mode;
    document.getElementById('globalModeText').innerText = mode;
    
    if (mode === 'Audio') {
      currentGlobalQuality = 'FLAC';
      document.getElementById('globalQualText').innerText = 'FLAC (Studio Master)';
    } else if (mode === 'GIF') {
      currentGlobalQuality = 'GIF';
      document.getElementById('globalQualText').innerText = 'GIF (Haute Qualité)';
    } else {
      currentGlobalQuality = 'Meilleure qualité (Auto)';
      document.getElementById('globalQualText').innerText = 'Meilleure qualité (Auto)';
    }

    updateGlobalQualityDropdown();
    closeAllPopovers();

    queue.forEach(item => {
      if (!item.isError) {
        item.mode = mode;
        if (mode === 'Audio') {
          item.selectedQuality = 'FLAC';
          item.selectedQualityLabel = 'FLAC (Studio Master)';
        } else if (mode === 'GIF') {
          item.selectedQuality = 'GIF';
          item.selectedQualityLabel = 'GIF (Haute Qualité)';
        } else {
          item.selectedQuality = (item.formats && item.formats[0]) || 'Meilleure qualité (Auto)';
          item.selectedQualityLabel = (item.formats && item.formats[0]) || 'Meilleure qualité (Auto)';
        }
      }
    });
    renderCards();
  }

  function selectGlobalQual(val, label, e) {
    if (e) { e.stopPropagation(); }
    currentGlobalQuality = val;
    document.getElementById('globalQualText').innerText = label;
    updateGlobalQualityDropdown();
    closeAllPopovers();

    queue.forEach(item => {
      if (!item.isError) {
        item.selectedQuality = val;
        item.selectedQualityLabel = label;
      }
    });
    renderCards();
  }

  let currentSettingsMode = 'video';
  function setSortieMode(mode) {
    currentSettingsMode = mode;
    document.getElementById('btnSortieVideo').classList.toggle('active', mode === 'video');
    document.getElementById('btnSortieAudio').classList.toggle('active', mode === 'audio');
    
    if (mode === 'video') {
      document.getElementById('sortieVideoFields').style.display = 'block';
      document.getElementById('sortieAudioFields').style.display = 'none';
    } else {
      document.getElementById('sortieVideoFields').style.display = 'none';
      document.getElementById('sortieAudioFields').style.display = 'block';
    }
  }

  function setDownloadFolderError(message) {
    const el = document.getElementById('downloadFolderError');
    el.textContent = message || '';
    el.style.display = message ? 'block' : 'none';
  }

  function browseDownloadFolder() {
    setDownloadFolderError('');
    callApi('browse_download_folder').then(path => {
      if (path) document.getElementById('setDownloadFolder').value = path;
    }).catch(() => setDownloadFolderError("Impossible d'ouvrir le sélecteur de dossiers Windows."));
  }

  function resetDownloadFolder() {
    setDownloadFolderError('');
    callApi('get_default_download_folder').then(path => {
      if (path) document.getElementById('setDownloadFolder').value = path;
    }).catch(() => setDownloadFolderError("Impossible de retrouver le dossier par défaut."));
  }

  function showSettingsView() {
    openView('viewSettings');
    setDownloadFolderError('');
    callApi('get_download_folder').then(path => {
      if (path) document.getElementById('setDownloadFolder').value = path;
    });
    callApi('get_app_settings').then(s => {
      if (!s) return;
      setSortieMode(s.sortie_type || 'video');
      
      // Options Vidéo
      document.getElementById('setVideoFormat').value = s.video_format || 'MP4';
      document.getElementById('setPostProcessVideo').value = s.post_process_video || 'Aucun';
      document.getElementById('setVideoOriginStream').checked = !!s.video_origin_stream;
      document.getElementById('setVideoEmbedThumb').checked = s.video_embed_thumb !== false;
      document.getElementById('setVideoWriteThumb').checked = s.video_write_thumb !== false;
      document.getElementById('setVideoAddMetadata').checked = s.video_add_metadata !== false;
      
      // Options Audio
      document.getElementById('setAudioFormat').value = s.audio_format || 'FLAC';
      document.getElementById('setPostProcessAudio').value = s.post_process_audio || 'Aucun';
      document.getElementById('setAudioEmbedThumb').checked = s.audio_embed_thumb !== false;
      document.getElementById('setAudioWriteThumb').checked = s.audio_write_thumb !== false;
      document.getElementById('setAudioAddMetadata').checked = s.audio_add_metadata !== false;
      
      // SponsorBlock
      document.getElementById('setSponsorEnable').checked = s.sponsor_enable !== false;
      document.getElementById('setSponsorRemove').value = s.sponsor_remove || 'sponsor';
      document.getElementById('setSponsorMark').value = s.sponsor_mark || 'none';
      document.getElementById('setSponsorApi').value = s.sponsor_api || 'https://sponsor.ajay.app';
      document.getElementById('setExactCut').checked = !!s.exact_cut;
      
      // Appli & Réseau
      document.getElementById('setTheme').value = s.theme || 'light';
      document.getElementById('setExtraSelector').value = s.extra_selector || 'none';
      document.getElementById('setNotify').value = s.notify || 'never';
      document.getElementById('setProxyToggle').checked = !!s.proxy_toggle;
      document.getElementById('setProxyUrl').value = s.proxy_url || '';
      document.getElementById('setImpersonation').value = s.impersonation || 'none';
      document.getElementById('setExtractorArgs').value = s.extractor_args || '';
    });
  }

  function cancelSettings() {
    applyTheme(activeSavedTheme);
    openView('viewMain');
  }

  function switchSettingsTab(tab) {
    document.querySelectorAll('.settings-nav .tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('setSectionTelech').style.display = 'none';
    document.getElementById('setSectionAppli').style.display = 'none';
    document.getElementById('setSectionReseau').style.display = 'none';

    if (tab === 'telech') {
      document.getElementById('tabBtnTelech').classList.add('active');
      document.getElementById('setSectionTelech').style.display = 'flex';
    } else if (tab === 'appli') {
      document.getElementById('tabBtnAppli').classList.add('active');
      document.getElementById('setSectionAppli').style.display = 'flex';
    } else if (tab === 'reseau') {
      document.getElementById('tabBtnReseau').classList.add('active');
      document.getElementById('setSectionReseau').style.display = 'flex';
    }
  }

  function saveSettings() {
    const s = {
      sortie_type: currentSettingsMode,
      video_format: document.getElementById('setVideoFormat').value,
      post_process_video: document.getElementById('setPostProcessVideo').value,
      video_origin_stream: document.getElementById('setVideoOriginStream').checked,
      video_embed_thumb: document.getElementById('setVideoEmbedThumb').checked,
      video_write_thumb: document.getElementById('setVideoWriteThumb').checked,
      video_add_metadata: document.getElementById('setVideoAddMetadata').checked,
      audio_format: document.getElementById('setAudioFormat').value,
      post_process_audio: document.getElementById('setPostProcessAudio').value,
      audio_embed_thumb: document.getElementById('setAudioEmbedThumb').checked,
      audio_write_thumb: document.getElementById('setAudioWriteThumb').checked,
      audio_add_metadata: document.getElementById('setAudioAddMetadata').checked,
      sponsor_enable: document.getElementById('setSponsorEnable').checked,
      sponsor_remove: document.getElementById('setSponsorRemove').value,
      sponsor_mark: document.getElementById('setSponsorMark').value,
      sponsor_api: document.getElementById('setSponsorApi').value,
      exact_cut: document.getElementById('setExactCut').checked,
      theme: document.getElementById('setTheme').value,
      extra_selector: document.getElementById('setExtraSelector').value,
      notify: document.getElementById('setNotify').value,
      proxy_toggle: document.getElementById('setProxyToggle').checked,
      proxy_url: document.getElementById('setProxyUrl').value,
      impersonation: document.getElementById('setImpersonation').value,
      extractor_args: document.getElementById('setExtractorArgs').value
    };
    const destination = document.getElementById('setDownloadFolder').value.trim();
    if (!destination) {
      switchSettingsTab('telech');
      setDownloadFolderError('Choisissez un dossier de téléchargement.');
      return;
    }
    setDownloadFolderError('');
    callApi('save_app_settings', s, destination).then(result => {
      if (result && result.success === true) {
        applyTheme(s.theme);
        document.getElementById('setDownloadFolder').value = result.path;
        openView('viewMain');
      } else {
        switchSettingsTab('telech');
        setDownloadFolderError(result && result.error ? result.error : "Impossible d'enregistrer ce dossier.");
      }
    }).catch(() => {
      switchSettingsTab('telech');
      setDownloadFolderError("Impossible d'enregistrer les paramètres.");
    });
  }

  function showAuthView() {
    openView('viewAuth');
    callApi('get_auth_config').then(cfg => {
      if (!cfg) return;
      document.getElementById('cookieFile').value = cfg.cookie_file || '';
      currentBrowser = cfg.cookie_browser || 'none';
      const textMap = {
        'none': 'Ne pas charger les cookies depuis un navigateur',
        'chrome': 'Google Chrome',
        'firefox': 'Mozilla Firefox',
        'brave': 'Brave',
        'edge': 'Microsoft Edge',
        'opera': 'Opera'
      };
      document.getElementById('browserSelectText').innerText = textMap[currentBrowser] || textMap['none'];
    });
  }

  function selectBrowser(val, text, e) {
    if (e) { e.stopPropagation(); }
    currentBrowser = val;
    document.getElementById('browserSelectText').innerText = text;
    closeAllPopovers();
  }

  function clearCookieFile() {
    document.getElementById('cookieFile').value = '';
  }

  function saveAuth() {
    const f = document.getElementById('cookieFile').value;
    callApi('save_auth_config', f, currentBrowser).then(() => {
      openView('viewMain');
    });
  }

  function showLogsView() {
    openView('viewLogs');
    refreshLogsViewData();
  }

  function refreshLogsViewData() {
    const errList = document.getElementById('errList');
    const errHeader = document.getElementById('errHeader');
    const errors = queue.filter(item => item.isError);

    errHeader.innerText = `Erreurs (${errors.length})`;
    if (errors.length === 0) {
      errList.innerHTML = `
        <div class="log-banner">
          <div class="badge-ok">✓</div>
          <div class="banner-text">Aucune erreur enregistrée.</div>
        </div>`;
    } else {
      let html = '';
      errors.forEach(item => {
        html += `
          <div class="log-banner">
            <div class="badge-fail">! Échec</div>
            <div class="banner-text"><b>${item.title}</b><br><span style="color:#aaa;">${item.error}</span></div>
          </div>`;
      });
      errList.innerHTML = html;
    }
  }

  function openFolderSafe() {
    callApi('open_folder');
  }

  function cancelDownloadsSafe() {
    callApi('cancel_downloads');
    resetDownloadUIState();
  }

  function pauseDownloadsSafe() {
    callApi('pause_downloads');
  }

  function resumeDownloadsSafe() {
    callApi('resume_downloads');
  }

  function updateView() {
    const emptyView = document.getElementById('emptyView');
    const cardList = document.getElementById('cardList');
    const statusBar = document.getElementById('statusBar');

    if (queue.length === 0) {
      emptyView.style.display = 'flex';
      cardList.style.display = 'none';
      statusBar.innerText = "Prêt à télécharger ! 0 élément en file d'attente.";
    } else {
      emptyView.style.display = 'none';
      cardList.style.display = 'flex';
      statusBar.innerText = `Prêt à télécharger ! ${queue.length} élément(s) en file d'attente.`;
    }
  }

  function addVideo() {
    const input = document.getElementById('urlInput');
    const url = input.value.trim();
    if (!url) return;
    input.value = '';

    const tempId = 'skel_' + Date.now();
    const skelHtml = `
      <div class="skeleton-card" id="${tempId}">
        <div class="skeleton-thumb">
          <svg style="width:32px;height:32px;fill:currentColor;" viewBox="0 0 24 24"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8 12.5v-9l6 4.5-6 4.5z"/></svg>
        </div>
        <div style="flex:1;">
          <div class="card-title" style="font-size:14px; font-weight:600;">${url}</div>
          <div class="skeleton-bar"><div class="skeleton-fill"></div></div>
          <div class="skeleton-status" style="font-size:11px; margin-top:4px; font-weight:600;">Récupération des métadonnées...</div>
        </div>
      </div>`;
    
    document.getElementById('cardList').insertAdjacentHTML('beforeend', skelHtml);
    document.getElementById('emptyView').style.display = 'none';
    document.getElementById('cardList').style.display = 'flex';

    appendTerminal(`[analyse] Extraction de l'URL : ${url}`);

    callApi('extract_info', url).then(res => {
      const el = document.getElementById(tempId);
      if (el) el.remove();

      if (res && res.success) {
        res.data.mode = (res.data.mode === 'Image' || res.data.mode === 'GIF') ? res.data.mode : currentGlobalMode;
        if (res.data.mode === 'Audio') {
          res.data.selectedQuality = 'FLAC';
          res.data.selectedQualityLabel = 'FLAC (Studio Master)';
        } else if (res.data.mode === 'GIF') {
          res.data.selectedQuality = 'GIF';
          res.data.selectedQualityLabel = 'GIF (Haute Qualité)';
        } else if (res.data.mode === 'Image') {
          res.data.selectedQuality = 'Original';
          res.data.selectedQualityLabel = 'Qualité Originale';
        } else {
          res.data.selectedQuality = (res.data.formats && res.data.formats[0]) || 'Meilleure qualité (Auto)';
          res.data.selectedQualityLabel = (res.data.formats && res.data.formats[0]) || 'Meilleure qualité (Auto)';
        }
        queue.push(res.data);
        appendTerminal(`[info] Analyse terminée : ${res.data.title}`);
      } else {
        const errMsg = res ? res.error : "Erreur de connexion";
        queue.push({
          title: url,
          url: url,
          error: errMsg,
          isError: true,
          isRestricted: res && res.is_restricted
        });
        appendTerminal(`[error] ${errMsg}`);
      }
      renderCards();
      updateView();
    }).catch(err => {
      const el = document.getElementById(tempId);
      if (el) el.remove();
      queue.push({ title: url, url: url, error: String(err), isError: true });
      renderCards();
      updateView();
    });
  }

  function updatePlaylistRange(idx) {
    const sInput = document.getElementById(`p_start_${idx}`);
    const eInput = document.getElementById(`p_end_${idx}`);
    if (sInput && eInput) {
      queue[idx].start_idx = parseInt(sInput.value) || 1;
      queue[idx].end_idx = parseInt(eInput.value) || (queue[idx].item_count || 1);
    }
  }

  function renderCards() {
    const list = document.getElementById('cardList');
    list.innerHTML = '';

    queue.forEach((item, index) => {
      const card = document.createElement('div');
      card.className = 'media-card' + (item.isError ? ' error' : '');

      const thumbImg = item.thumbnail ? `<img class="thumb" src="${item.thumbnail}" onerror="this.style.display='none'">` : '';

      if (item.isError) {
        const badgeText = item.isRestricted ? "🔒 Contenu Restreint (+18 / Privé)" : "Erreur d'accès";
        card.innerHTML = `
          <div class="thumb-container" style="background:#ff4d4f;">${thumbImg}</div>
          <div class="card-body">
            <div class="card-title-row">
              <div class="card-title">${item.title}</div>
            </div>
            <div class="card-bottom-row">
              <div class="error-badge">
                <svg style="width:12px;height:12px;fill:#fff;" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
                ${badgeText}
              </div>
              <button class="btn-logs-card" onclick="showAuthView()">Importer cookies</button>
              <button class="btn-logs-card" onclick="showLogsView()">Voir logs</button>
            </div>
          </div>
          <div class="v-separator"></div>
          <div class="card-actions">
            <button class="card-act-btn close" onclick="removeItem(${index})" title="Fermer">✕</button>
            <button class="card-act-btn" onclick="openItemExternal(${index})" title="Ouvrir dans le navigateur">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg>
            </button>
            <button class="card-act-btn" onclick="retryItem(${index})" title="Réessayer">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
            </button>
            <button class="card-act-btn" onclick="showLogsView()" title="Informations">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
            </button>
          </div>
        `;
      } else if (item.is_playlist || item.is_channel) {
        const count = item.item_count || 1;
        const startVal = item.start_idx || 1;
        const endVal = item.end_idx || count;

        let plQualOptions = '';
        if (item.mode === 'Audio') {
          plQualOptions = `
            <div class="dropdown-item ${item.selectedQuality==='FLAC'?'selected':''}" onclick="setCardQuality(${index}, 'FLAC', 'FLAC (Studio Master)', event)"><span class="check">${item.selectedQuality==='FLAC'?'✓':''}</span>FLAC (Studio Master)</div>
            <div class="dropdown-item ${item.selectedQuality==='M4A'?'selected':''}" onclick="setCardQuality(${index}, 'M4A', 'M4A (Format natif)', event)"><span class="check">${item.selectedQuality==='M4A'?'✓':''}</span>M4A (Format natif)</div>
            <div class="dropdown-item ${item.selectedQuality==='MP3_320'?'selected':''}" onclick="setCardQuality(${index}, 'MP3_320', 'MP3 (320 kbps)', event)"><span class="check">${item.selectedQuality==='MP3_320'?'✓':''}</span>MP3 (320 kbps)</div>
          `;
        } else {
          plQualOptions = `
            <div class="dropdown-item ${(!item.selectedQuality || item.selectedQuality==='Meilleure qualité (Auto)')?'selected':''}" onclick="setCardQuality(${index}, 'Meilleure qualité (Auto)', 'Meilleure qualité (Auto)', event)"><span class="check">${(!item.selectedQuality || item.selectedQuality==='Meilleure qualité (Auto)')?'✓':''}</span>Meilleure qualité (Auto)</div>
            <div class="dropdown-item ${item.selectedQuality==='2160p'?'selected':''}" onclick="setCardQuality(${index}, '2160p', '2160p (4K UHD)', event)"><span class="check">${item.selectedQuality==='2160p'?'✓':''}</span>2160p (4K UHD)</div>
            <div class="dropdown-item ${item.selectedQuality==='1440p'?'selected':''}" onclick="setCardQuality(${index}, '1440p', '1440p (2K QHD)', event)"><span class="check">${item.selectedQuality==='1440p'?'✓':''}</span>1440p (2K QHD)</div>
            <div class="dropdown-item ${item.selectedQuality==='1080p'?'selected':''}" onclick="setCardQuality(${index}, '1080p', '1080p (Full HD)', event)"><span class="check">${item.selectedQuality==='1080p'?'✓':''}</span>1080p (Full HD)</div>
            <div class="dropdown-item ${item.selectedQuality==='720p'?'selected':''}" onclick="setCardQuality(${index}, '720p', '720p (HD)', event)"><span class="check">${item.selectedQuality==='720p'?'✓':''}</span>720p (HD)</div>
            <div class="dropdown-item ${item.selectedQuality==='480p'?'selected':''}" onclick="setCardQuality(${index}, '480p', '480p (SD)', event)"><span class="check">${item.selectedQuality==='480p'?'✓':''}</span>480p (SD)</div>
          `;
        }

        const countLabel = item.is_channel ? `Les ${count} vidéos de la chaîne sont sélectionnées` : `Les ${count} éléments sont sélectionnés`;
        const btnLabel = item.is_channel ? "Télécharger la chaîne" : "Télécharger tous les éléments";

        card.innerHTML = `
          <div class="thumb-container">${thumbImg}</div>
          <div class="card-body">
            <div class="card-title-row" style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px;">
              <div class="card-title">${item.title}</div>
              <div class="playlist-count-text" style="font-size:12px; font-weight:600; white-space:nowrap; flex-shrink:0;">${countLabel}</div>
            </div>
            <div class="playlist-label">Sélectionnez les éléments à télécharger :</div>
            <div class="card-bottom-row">
              <div class="playlist-range-row">
                <span>Début</span>
                <input type="number" class="range-input" id="p_start_${index}" value="${startVal}" min="1" max="${count}" onchange="updatePlaylistRange(${index})">
                <span>Fin</span>
                <input type="number" class="range-input" id="p_end_${index}" value="${endVal}" min="1" max="${count}" onchange="updatePlaylistRange(${index})">
              </div>
              <div style="display:flex; align-items:center; gap:8px; margin-left:auto; flex-wrap:wrap;">
                <div class="pill-dropdown" onclick="toggleDropdown('pl_mode_pop_${index}', event)">
                  <span>${item.mode || 'Vidéo'}</span>
                  <svg class="svg-icon" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>
                  <div class="dropdown-popover" id="pl_mode_pop_${index}">
                    <div class="dropdown-item ${item.mode==='Vidéo'?'selected':''}" onclick="setCardMode(${index}, 'Vidéo', event)"><span class="check">${item.mode==='Vidéo'?'✓':''}</span>Vidéo</div>
                    <div class="dropdown-item ${item.mode==='Audio'?'selected':''}" onclick="setCardMode(${index}, 'Audio', event)"><span class="check">${item.mode==='Audio'?'✓':''}</span>Audio</div>
                  </div>
                </div>

                <div class="pill-dropdown" onclick="toggleDropdown('pl_qual_pop_${index}', event)">
                  <span>${item.selectedQualityLabel || (item.mode==='Audio'?'FLAC (Studio Master)':'Meilleure qualité (Auto)')}</span>
                  <svg class="svg-icon" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>
                  <div class="dropdown-popover" id="pl_qual_pop_${index}">
                    ${plQualOptions}
                  </div>
                </div>

                <button class="btn-dl-playlist" onclick="downloadSingle(${index})">${btnLabel}</button>
              </div>
            </div>
          </div>
          <div class="v-separator"></div>
          <div class="card-actions">
            <button class="card-act-btn close" onclick="removeItem(${index})" title="Fermer">✕</button>
            <button class="card-act-btn" onclick="openItemExternal(${index})" title="Ouvrir dans le navigateur">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg>
            </button>
            <button class="card-act-btn" onclick="downloadSingle(${index})" title="Télécharger">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.64-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
            </button>
            <button class="card-act-btn" onclick="showLogsView()" title="Informations">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
            </button>
          </div>
        `;
      } else {
        let qualPopoverHtml = '';
        if (item.mode === 'Audio') {
          qualPopoverHtml = `
            <div class="dropdown-item ${item.selectedQuality==='FLAC'?'selected':''}" onclick="setCardQuality(${index}, 'FLAC', 'FLAC (Studio Master)', event)"><span class="check">${item.selectedQuality==='FLAC'?'✓':''}</span>FLAC (Studio Master)</div>
            <div class="dropdown-item ${item.selectedQuality==='M4A'?'selected':''}" onclick="setCardQuality(${index}, 'M4A', 'M4A (Format natif)', event)"><span class="check">${item.selectedQuality==='M4A'?'✓':''}</span>M4A (Format natif)</div>
            <div class="dropdown-item ${item.selectedQuality==='MP3_320'?'selected':''}" onclick="setCardQuality(${index}, 'MP3_320', 'MP3 (320 kbps)', event)"><span class="check">${item.selectedQuality==='MP3_320'?'✓':''}</span>MP3 (320 kbps)</div>
          `;
        } else if (item.mode === 'GIF') {
          qualPopoverHtml = `
            <div class="dropdown-item ${item.selectedQuality==='GIF'?'selected':''}" onclick="setCardQuality(${index}, 'GIF', 'GIF (Haute Qualité)', event)"><span class="check">${item.selectedQuality==='GIF'?'✓':''}</span>GIF (Haute Qualité)</div>
            <div class="dropdown-item ${item.selectedQuality==='GIF_30'?'selected':''}" onclick="setCardQuality(${index}, 'GIF_30', 'GIF (Fluide 30fps)', event)"><span class="check">${item.selectedQuality==='GIF_30'?'✓':''}</span>GIF (Fluide 30fps)</div>
          `;
        } else if (item.mode === 'Image') {
          qualPopoverHtml = `
            <div class="dropdown-item selected"><span class="check">✓</span>Qualité Originale</div>
          `;
        } else {
          item.formats.forEach(f => {
            const isSel = item.selectedQuality === f;
            qualPopoverHtml += `<div class="dropdown-item ${isSel?'selected':''}" onclick="setCardQuality(${index}, '${f}', '${f}', event)"><span class="check">${isSel?'✓':''}</span>${f}</div>`;
          });
        }

        let is_yt = Boolean(item.url && (item.url.toLowerCase().indexOf("youtube.com") !== -1 || item.url.toLowerCase().indexOf("youtu.be") !== -1));
        let is_direct_gif = item.is_direct_download && (item.url || '').toLowerCase().split(/[?#]/)[0].endsWith('.gif');
        let destInfo = 'Dossier: /AUTRES';
        if (item.mode === 'GIF' || is_direct_gif) {
          destInfo = 'Dossier: /GIFS';
        } else if (is_yt && item.is_channel && item.channel_title) {
          destInfo = 'Dossier: /CHAÎNES';
        } else if (is_yt && item.is_playlist && item.playlist_title) {
          destInfo = 'Dossier: /PLAYLIST';
        } else if (item.mode === 'Audio') {
          destInfo = 'Dossier: /AUDIOS';
        } else if (is_yt) {
          destInfo = 'Dossier: /VIDÉOS';
        }

        card.innerHTML = `
          <div class="thumb-container">${thumbImg}</div>
          <div class="card-body">
            <div class="card-title-row">
              <div class="card-title">${item.title}</div>
            </div>
            <div class="card-bottom-row">
              <div class="card-meta">Durée : ${item.duration} &nbsp;•&nbsp; ${destInfo}</div>
              <div class="card-controls">
                <div class="pill-dropdown" onclick="toggleDropdown('card_mode_pop_${index}', event)">
                  <span>${item.mode}</span>
                  <svg class="svg-icon" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>
                  <div class="dropdown-popover" id="card_mode_pop_${index}">
                    <div class="dropdown-item ${item.mode==='Vidéo'?'selected':''}" onclick="setCardMode(${index}, 'Vidéo', event)"><span class="check">${item.mode==='Vidéo'?'✓':''}</span>Vidéo</div>
                    <div class="dropdown-item ${item.mode==='Audio'?'selected':''}" onclick="setCardMode(${index}, 'Audio', event)"><span class="check">${item.mode==='Audio'?'✓':''}</span>Audio</div>
                    <div class="dropdown-item ${item.mode==='GIF'?'selected':''}" onclick="setCardMode(${index}, 'GIF', event)"><span class="check">${item.mode==='GIF'?'✓':''}</span>GIF</div>
                  </div>
                </div>

                <div class="pill-dropdown" onclick="toggleDropdown('card_qual_pop_${index}', event)">
                  <span>${item.selectedQualityLabel || item.selectedQuality}</span>
                  <svg class="svg-icon" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>
                  <div class="dropdown-popover" id="card_qual_pop_${index}">
                    ${qualPopoverHtml}
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="v-separator"></div>
          <div class="card-actions">
            <button class="card-act-btn close" onclick="removeItem(${index})" title="Fermer">✕</button>
            <button class="card-act-btn" onclick="openItemExternal(${index})" title="Ouvrir dans le navigateur">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg>
            </button>
            <button class="card-act-btn" onclick="downloadSingle(${index})" title="Télécharger">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.64-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
            </button>
            <button class="card-act-btn" onclick="showLogsView()" title="Informations">
              <svg class="svg-icon" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
            </button>
          </div>
        `;
      }
      list.appendChild(card);
    });
  }

  function setCardMode(idx, mode, e) {
    if (e) { e.stopPropagation(); }
    queue[idx].mode = mode;
    if (mode === 'Audio') {
      queue[idx].selectedQuality = 'FLAC';
      queue[idx].selectedQualityLabel = 'FLAC (Studio Master)';
    } else if (mode === 'GIF') {
      queue[idx].selectedQuality = 'GIF';
      queue[idx].selectedQualityLabel = 'GIF (Haute Qualité)';
    } else {
      queue[idx].selectedQuality = (queue[idx].formats && queue[idx].formats[0]) || 'Meilleure qualité (Auto)';
      queue[idx].selectedQualityLabel = (queue[idx].formats && queue[idx].formats[0]) || 'Meilleure qualité (Auto)';
    }
    closeAllPopovers();
    renderCards();
  }

  function setCardQuality(idx, val, label, e) {
    if (e) { e.stopPropagation(); }
    queue[idx].selectedQuality = val;
    queue[idx].selectedQualityLabel = label;
    closeAllPopovers();
    renderCards();
  }

  function removeItem(idx) {
    queue.splice(idx, 1);
    renderCards();
    updateView();
  }

  function retryItem(idx) {
    const url = queue[idx].url;
    removeItem(idx);
    document.getElementById('urlInput').value = url;
    addVideo();
  }

  function clearQueue() {
    queue = [];
    closeAllPopovers();
    renderCards();
    updateView();
  }

  function clearFailed() {
    queue = queue.filter(item => !item.isError);
    closeAllPopovers();
    renderCards();
    updateView();
  }

  function markDownloadSuccess(url) {
    // Le moteur nous confirme une réussite réelle (code de sortie yt-dlp 0).
    const item = queue.find(x => !x.isError && x.url === url && x.status !== 'success');
    if (item) {
      item.status = 'success';
      renderCards();
    }
  }

  function clearSuccess() {
    queue = queue.filter(item => item.status !== 'success');
    closeAllPopovers();
    renderCards();
    updateView();
  }

  /* GESTION ANIMATION CHARGEMENT AVANT LE TÉLÉCHARGEMENT */
  function startDownloadUIState() {
    const btn = document.querySelector('.btn-download-all');
    if (btn) {
      btn.dataset.originalText = btn.innerHTML;
      btn.innerHTML = '<span class="btn-spinner"></span>Préparation...';
      btn.style.pointerEvents = 'none';
      btn.style.opacity = '0.85';
    }
    const bar = document.getElementById('progressFill');
    if (bar) {
      bar.style.width = '30%';
      bar.classList.add('indeterminate');
    }
    const status = document.getElementById('statusBar');
    if (status) {
      status.innerText = 'Initialisation et préparation des flux...';
    }
  }

  function resetDownloadUIState() {
    const btn = document.querySelector('.btn-download-all');
    if (btn && btn.dataset.originalText) {
      btn.innerHTML = btn.dataset.originalText;
      btn.style.pointerEvents = 'auto';
      btn.style.opacity = '1';
    }
    const bar = document.getElementById('progressFill');
    if (bar) {
      bar.classList.remove('indeterminate');
    }
  }

  function startDownloads() {
    const valid = queue.filter(i => !i.isError);
    if (valid.length === 0) return;
    // 'valid' n'a pas forcement les memes index que la file d'attente
    // lorsqu'une entrée en erreur a ete retiree.
    queue.forEach((item, index) => {
      if (!item.isError && (item.is_playlist || item.is_channel)) {
        updatePlaylistRange(index);
      }
    });
    startDownloadUIState();
    callApi('start_downloads', valid);
  }

  function downloadSingle(idx) {
    if (queue[idx].is_playlist || queue[idx].is_channel) updatePlaylistRange(idx);
    startDownloadUIState();
    callApi('start_downloads', [queue[idx]]);
  }

  function openExternal(url) {
    callApi('open_external', url);
  }

  // Garder l'URL en donnees et non dans le code HTML du bouton.
  // Les apostrophes et autres caractères d'URL ne cassent plus le clic.
  function openItemExternal(index) {
    const item = queue[index];
    if (item && item.url) openExternal(item.url);
  }

  function updateDownloadProgress(pct, statusText) {
    const bar = document.getElementById('progressFill');
    if (bar) {
      if (pct > 0) {
        bar.classList.remove('indeterminate');
        bar.style.width = pct + '%';
      }
    }
    document.getElementById('statusBar').innerText = statusText;
    appendTerminal(statusText);

    if (pct >= 100 || statusText.toLowerCase().includes('terminé')) {
      resetDownloadUIState();
    }
  }

  function chooseCookieFile() {
    callApi('select_cookie_file').then(p => {
      if (p) document.getElementById('cookieFile').value = p;
    });
  }

  updateGlobalQualityDropdown();
  applyTheme('light');

  function initApp() {
    callApi('get_app_settings').then(s => {
      if (s && s.theme) applyTheme(s.theme);
    });
  }

  window.addEventListener('pywebviewready', initApp);
  window.addEventListener('DOMContentLoaded', initApp);
</script>
</body>
</html>
"""

# -------------------------------------------------------------
# BACKEND API PYTHON (UNIVERSAL EXTRACTOR + 4K / AUDIO HD)
# -------------------------------------------------------------
class DownloaderAPI:
    def __init__(self):
        self.window = None
        self.config = self._load_config()
        if "download_folder_custom" not in self.config:
            saved = self.config.get("download_folder")
            self.config["download_folder_custom"] = bool(
                isinstance(saved, str) and saved.strip()
                and not is_legacy_download_folder(saved)
                and os.path.normcase(os.path.abspath(saved))
                    != os.path.normcase(os.path.abspath(DEFAULT_DOWNLOAD_BASE))
            )
        self.download_folder = choose_initial_download_folder(self.config)
        ensure_media_directories(self.download_folder)
        # Corriger aussi le chemin déjà enregistré sur les anciennes versions,
        # en conservant les réglages, cookies et autres préférences.
        if is_legacy_download_folder(self.config.get("download_folder")):
            self._save_config()
        self.is_cancelled = False
        self.is_paused = False
        self._active_download_process = None

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception: pass
        return {}

    def _save_config(self):
        self.config["download_folder"] = self.download_folder
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except (OSError, TypeError, ValueError):
            return False

    def get_download_folder(self):
        return self.download_folder

    def get_default_download_folder(self):
        return choose_initial_download_folder({"download_folder_custom": False})

    def browse_download_folder(self):
        if self.window is None:
            return None
        try:
            initial = self.download_folder if os.path.isdir(self.download_folder) else os.path.expanduser("~")
            result = self.window.create_file_dialog(
                webview.FileDialog.FOLDER, directory=initial
            )
            if result:
                return os.path.normpath(result[0])
        except Exception as exc:
            handle_exception(type(exc), exc, exc.__traceback__)
        return None

    def get_app_settings(self):
        return self.config.get("settings", {
            "sortie_type": "video",
            "video_format": "MP4",
            "post_process_video": "Aucun",
            "video_origin_stream": False,
            "video_embed_thumb": True,
            "video_write_thumb": True,
            "video_add_metadata": True,
            "audio_format": "FLAC",
            "post_process_audio": "Aucun",
            "audio_embed_thumb": True,
            "audio_write_thumb": True,
            "audio_add_metadata": True,
            "sponsor_enable": True,
            "sponsor_remove": "sponsor",
            "sponsor_mark": "none",
            "sponsor_api": "https://sponsor.ajay.app",
            "exact_cut": False,
            "theme": "light",
            "extra_selector": "none",
            "notify": "never",
            "proxy_toggle": False,
            "proxy_url": "",
            "impersonation": "none",
            "extractor_args": ""
        })

    def save_app_settings(self, settings_dict, download_folder=None):
        if not isinstance(settings_dict, dict):
            return {"success": False, "error": "Paramètres invalides."}
        requested = download_folder if download_folder is not None else self.download_folder
        if not isinstance(requested, str) or not requested.strip():
            return {"success": False, "error": "Choisissez un dossier de téléchargement."}
        requested = os.path.expanduser(os.path.expandvars(requested.strip().strip('"')))
        if not os.path.isabs(requested):
            return {"success": False, "error": "Indiquez un chemin absolu (C:\\..., D:\\... ou un dossier réseau)."}
        requested = os.path.normpath(requested)
        try:
            ensure_media_directories(requested)
            import tempfile
            with tempfile.TemporaryFile(dir=requested):
                pass
        except (OSError, ValueError) as exc:
            return {"success": False, "error": f"Dossier inaccessible ou non modifiable : {exc}"}

        old_config = dict(self.config)
        old_folder = self.download_folder
        automatic = self.get_default_download_folder()
        self.download_folder = requested
        self.config["download_folder_custom"] = (
            os.path.normcase(os.path.abspath(requested))
            != os.path.normcase(os.path.abspath(automatic))
        )
        self.config["settings"] = settings_dict
        if not self._save_config():
            self.config = old_config
            self.download_folder = old_folder
            return {"success": False, "error": "Impossible d'enregistrer la configuration Windows."}
        return {"success": True, "path": self.download_folder}

    def get_clipboard_text(self):
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            user32.OpenClipboard.argtypes = [wintypes.HWND]
            user32.OpenClipboard.restype = wintypes.BOOL
            user32.CloseClipboard.argtypes = []
            user32.CloseClipboard.restype = wintypes.BOOL
            user32.GetClipboardData.argtypes = [wintypes.UINT]
            user32.GetClipboardData.restype = wintypes.HANDLE
            kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
            kernel32.GlobalUnlock.restype = wintypes.BOOL

            CF_UNICODETEXT = 13
            if not user32.OpenClipboard(None):
                return ""
            try:
                h_clip = user32.GetClipboardData(CF_UNICODETEXT)
                if not h_clip:
                    return ""
                p_text = kernel32.GlobalLock(h_clip)
                if not p_text:
                    return ""
                try:
                    text = ctypes.wstring_at(p_text)
                    return text or ""
                finally:
                    kernel32.GlobalUnlock(h_clip)
            finally:
                user32.CloseClipboard()
        except Exception:
            return ""

    def _get_cookie_args(self):
        c_file = self.config.get("cookie_file", "").strip()
        c_browser = self.config.get("cookie_browser", "none")
        if c_file and os.path.exists(c_file):
            return ["--cookies", c_file]
        if c_browser and c_browser != "none":
            return ["--cookies-from-browser", c_browser]
        return []

    def open_folder(self):
        try:
            ensure_media_directories(self.download_folder)
            os.startfile(self.download_folder)
        except Exception: pass

    def open_external(self, url):
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception: pass

    def get_auth_config(self):
        return {
            "cookie_file": self.config.get("cookie_file", ""),
            "cookie_browser": self.config.get("cookie_browser", "none")
        }

    def save_auth_config(self, file_path, browser):
        self.config["cookie_file"] = file_path
        self.config["cookie_browser"] = browser
        self._save_config()
        return True

    def select_cookie_file(self):
        try:
            res = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=('Fichiers Cookies (*.txt;*.cookies)', 'Tous les fichiers (*.*)'))
            return res[0] if res else ""
        except Exception:
            return ""

    def cancel_downloads(self):
        self.is_cancelled = True
        # Annuler aussi le transfert yt-dlp en cours, pas seulement la file.
        proc = getattr(self, "_active_download_process", None)
        if proc is not None:
            try:
                kill_process_tree(proc.pid)
            except Exception:
                pass
        return True

    def pause_downloads(self):
        self.is_paused = True

    def resume_downloads(self):
        self.is_paused = False

    def extract_info(self, raw_url):
        url = normalize_media_url(raw_url)

        # 1. Résolveur direct Pinterest
        if "pinterest." in url or "pin.it" in url:
            pin_data = extract_pinterest_direct(url)
            if pin_data:
                return {"success": True, "data": pin_data}

        # 2. Extraction complète universelle via yt-dlp
        settings = self.get_app_settings()

        has_video_id = bool("v=" in url or "youtu.be/" in url)
        is_pure_playlist = bool(("list=" in url or "/playlist" in url) and not has_video_id)
        is_channel = bool(any(k in url.lower() for k in ["/channel/", "/c/", "/user/", "@"]) and not has_video_id)

        cmd = [
            YTDLP_PATH, "-J",
            "--no-warnings",
            "--force-ipv4",
            "--socket-timeout", "15",
            "--retries", "3"
        ] + self._get_cookie_args()

        imp_val = settings.get("impersonation", "none")
        if imp_val == "random":
            cmd.extend(["--user-agent", random.choice(list(UA_MAP.values()))])
        elif imp_val in UA_MAP:
            cmd.extend(["--user-agent", UA_MAP[imp_val]])

        if "twitter.com" in url or "x.com" in url:
            cmd.extend(["--extractor-args", "twitter:api=syndication"])

        if has_video_id:
            cmd.append("--no-playlist")
        elif is_pure_playlist or is_channel:
            cmd.extend(["--flat-playlist", "--playlist-end", "1000"])

        if settings.get("proxy_toggle") and settings.get("proxy_url"):
            cmd.extend(["--proxy", settings.get("proxy_url")])

        cmd.append(url)

        proc = None
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            stdout, stderr = proc.communicate(timeout=60)
            
            if proc.returncode != 0:
                err_lower = stderr.lower()
                is_restricted = False
                if any(k in err_lower for k in ["sign in", "confirm your age", "age-restricted", "age restricted", "inappropriate"]):
                    err_clean = "Contenu restreint (+18 ans) : Connectez vos cookies via l'icône clé en bas à gauche."
                    is_restricted = True
                elif any(k in err_lower for k in ["private video", "this video is private", "privée"]):
                    err_clean = "Contenu privé : Accès réservé. Connectez vos cookies pour y accéder."
                    is_restricted = True
                elif "403" in stderr:
                    err_clean = "Accès refusé (Erreur 403) : Authentification ou cookies requis."
                    is_restricted = True
                elif "could not copy" in err_lower or "database is locked" in err_lower:
                    err_clean = "Base de données navigateur verrouillée : Fermez complètement votre navigateur pour lire les cookies."
                    is_restricted = True
                else:
                    err_clean = stderr.strip() or "Erreur de connexion ou ressource introuvable."
                return {"success": False, "error": err_clean, "is_restricted": is_restricted}
            
            info = json.loads(stdout)
            
            video_map = {}
            for f in info.get("formats", []):
                h = f.get("height")
                if not h:
                    res_str = f.get("resolution") or f.get("format_note") or ""
                    m = re.search(r'(\d{3,4})p?', res_str)
                    if m: h = int(m.group(1))
                
                if h and isinstance(h, int) and h >= 144:
                    fps = f.get("fps") or 30
                    if h not in video_map or fps > video_map[h]:
                        video_map[h] = int(fps)

            sorted_formats = ["Meilleure qualité (Auto)"]
            if video_map:
                standard_tiers = [4320, 2160, 1440, 1080, 720, 480, 360, 240, 144]
                max_detected = max(video_map.keys())
                for tier in standard_tiers:
                    if tier <= max_detected and tier not in video_map:
                        video_map[tier] = 30

                for h in sorted(video_map.keys(), reverse=True):
                    fps = video_map[h]
                    fps_str = f" ({fps}fps)" if fps and fps > 30 else ""
                    sorted_formats.append(f"{h}p{fps_str}")
            else:
                sorted_formats.extend(["1080p", "720p", "480p", "360p"])

            dur = info.get("duration")
            if dur is not None and isinstance(dur, (int, float)):
                m, s = divmod(int(dur), 60)
                h, m = divmod(m, 60)
                dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
            else:
                dur_str = "00:00"

            thumb_url = info.get("thumbnail") or ""
            if info.get("thumbnails"):
                valid_thumbs = [t for t in info["thumbnails"] if t.get("url")]
                if valid_thumbs:
                    thumb_url = valid_thumbs[-1].get("url", "")

            raw_title = info.get("title") or info.get("description") or info.get("id") or "Media_Download"
            if len(raw_title) > 85:
                raw_title = raw_title[:82] + "..."

            channel_title = info.get("channel") or info.get("uploader") or info.get("channel_id") or "Chaine"
            playlist_title = info.get("title", "Playlist") if is_pure_playlist else (info.get("playlist_title") or "Playlist")
            item_count = len(info.get("entries", [])) if "entries" in info else (info.get("playlist_count") or 1)
            if not item_count:
                item_count = 1

            data = {
                "title": raw_title,
                "thumbnail": thumb_url,
                "duration": dur_str,
                "url": url,
                "mode": "Vidéo",
                "formats": sorted_formats,
                "selectedQuality": sorted_formats[0],
                "selectedQualityLabel": sorted_formats[0],
                "is_channel": is_channel,
                "channel_title": channel_title,
                "is_playlist": is_pure_playlist,
                "playlist_title": playlist_title,
                "item_count": item_count,
                "start_idx": 1,
                "end_idx": item_count,
                "is_direct_download": False,
                "isError": False
            }
            return {"success": True, "data": data}
        except subprocess.TimeoutExpired:
            if proc: kill_process_tree(proc.pid)
            return {"success": False, "error": "Délai d'attente dépassé lors de l'analyse."}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            gc.collect()

    def start_downloads(self, items):
        self.is_cancelled = False
        settings = self.get_app_settings()

        def _worker():
            total = len(items)
            completed = 0
            for idx, item in enumerate(items, 1):
                while self.is_paused and not self.is_cancelled:
                    time.sleep(0.3)

                if self.is_cancelled: break
                
                url = item["url"]
                mode = item.get("mode", "Vidéo")
                quality = item.get("selectedQuality", "Meilleure qualité (Auto)")

                is_yt = bool(url and ("youtube.com" in url.lower() or "youtu.be" in url.lower()))
                is_channel = item.get("is_channel", False)
                channel_title = item.get("channel_title")
                is_playlist = item.get("is_playlist", False)
                playlist_title = item.get("playlist_title")

                # Routage centralisé : GIFS, AUDIOS, CHAÎNES, PLAYLIST, VIDÉOS, AUTRES.
                target_dir = get_media_download_dir(self.download_folder, item)
                os.makedirs(target_dir, exist_ok=True)

                # Téléchargement direct d'image / GIF Pinterest
                if item.get("is_direct_download"):
                    try:
                        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1]
                        if not ext or len(ext) > 5:
                            ext = ".jpg"
                        out_name = sanitize_filename(item.get("title", "Pinterest_Media")) + ext
                        out_path = os.path.join(target_dir, out_name)
                        
                        req = urllib.request.Request(url, headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Referer": "https://www.pinterest.com/"
                        })
                        with urllib.request.urlopen(req, timeout=20) as resp, open(out_path, "wb") as f_out:
                            f_out.write(resp.read())
                        
                        completed += 1
                        if self.window:
                            try:
                                self.window.evaluate_js(f"markDownloadSuccess({json.dumps(url)})")
                                self.window.evaluate_js(f"updateDownloadProgress(100, {json.dumps('Téléchargement terminé – ' + out_name)})")
                            except Exception:
                                pass
                        continue
                    except Exception:
                        pass

                # Téléchargement universel via yt-dlp
                cmd = [
                    YTDLP_PATH,
                    "--ffmpeg-location", BIN_DIR,
                    "--windows-filenames",
                    "--newline",
                    "--force-ipv4",
                    "--socket-timeout", "15",
                    "-P", target_dir,
                    "-o", f"{sanitize_filename(item.get('title', 'Media'))}.%(ext)s" if "v.pinimg.com" in url else "%(title)s.%(ext)s"
                ] + self._get_cookie_args()

                if "twitter.com" in url or "x.com" in url:
                    cmd.extend(["--extractor-args", "twitter:api=syndication"])

                if is_playlist or is_channel:
                    s_idx = item.get("start_idx", 1)
                    e_idx = item.get("end_idx", item.get("item_count", 1))
                    cmd.extend([
                        "--yes-playlist",
                        "--playlist-start", str(s_idx),
                        "--playlist-end", str(e_idx),
                        "--ignore-errors",
                        "--no-abort-on-error"
                    ])
                elif ("v=" in url or "youtu.be/" in url):
                    cmd.append("--no-playlist")

                # Séparation stricte Vidéo vs Audio
                if mode == "Audio":
                    embed_thumb = settings.get("audio_embed_thumb", True)
                    write_thumb = settings.get("audio_write_thumb", True)
                    add_meta = settings.get("audio_add_metadata", True)
                else:
                    embed_thumb = settings.get("video_embed_thumb", True)
                    write_thumb = settings.get("video_write_thumb", True)
                    add_meta = settings.get("video_add_metadata", True)

                if embed_thumb or write_thumb:
                    cmd.extend(["--convert-thumbnails", "jpg"])

                if embed_thumb:
                    cmd.append("--embed-thumbnail")
                if write_thumb:
                    cmd.append("--write-thumbnail")

                if add_meta:
                    cmd.append("--add-metadata")

                # Proxy
                if settings.get("proxy_toggle") and settings.get("proxy_url"):
                    cmd.extend(["--proxy", settings.get("proxy_url")])

                # SponsorBlock
                if is_yt and settings.get("sponsor_enable", True):
                    s_remove = settings.get("sponsor_remove", "sponsor")
                    if s_remove in ["all", "sponsor"]:
                        cmd.extend(["--sponsorblock-remove", s_remove])

                    if settings.get("sponsor_mark") == "chapters":
                        cmd.extend(["--sponsorblock-mark", "all"])

                    sponsor_api = settings.get("sponsor_api", "").strip()
                    if sponsor_api and sponsor_api != "https://sponsor.ajay.app":
                        cmd.extend(["--sponsorblock-api", sponsor_api.rstrip('/')])

                    if settings.get("exact_cut", False):
                        cmd.append("--force-keyframes-at-cuts")

                # Impersonation
                imp_val = settings.get("impersonation", "none")
                if imp_val == "random":
                    rand_ua = random.choice(list(UA_MAP.values()))
                    cmd.extend(["--user-agent", rand_ua])
                elif imp_val in UA_MAP:
                    cmd.extend(["--user-agent", UA_MAP[imp_val]])

                # Arguments personnalisés
                extra_args = settings.get("extractor_args", "").strip()
                if extra_args:
                    for arg in extra_args.splitlines():
                        if arg.strip():
                            cmd.extend(["--extractor-args", arg.strip()])

                # AUDIO / GIF / VIDÉO (Format universel garanti sans erreur 404/format unavailable)
                if mode == "Audio":
                    cmd.append("-x")
                    audio_choice = settings.get("audio_format", "FLAC")
                    if quality == "MP3_320" or audio_choice == "MP3":
                        cmd.extend(["--audio-format", "mp3", "--audio-quality", "0"])
                    elif quality == "M4A" or audio_choice == "M4A":
                        cmd.extend(["--audio-format", "m4a"])
                    else:
                        cmd.extend(["--audio-format", "flac"])

                    if settings.get("post_process_audio") == "Normaliser":
                        cmd.extend(["--postprocessor-args", "ffmpeg:-af loudnorm"])
                elif mode == "GIF":
                    cmd.extend([
                        "-f", "bestvideo+bestaudio/best",
                        "--recode-video", "gif"
                    ])
                else:
                    if settings.get("post_process_video") == "Normaliser":
                        cmd.extend(["--postprocessor-args", "ffmpeg:-af loudnorm"])
                    elif settings.get("post_process_video") == "Remuxer":
                        cmd.extend(["--remux-video", "mp4"])

                    target_ext = settings.get("video_format", "MP4").lower()

                    if quality == "Meilleure qualité (Auto)" or not quality:
                        cmd.extend(["-f", "bestvideo+bestaudio/best"])
                    else:
                        h_match = re.search(r'(\d+)p?', str(quality))
                        if h_match:
                            h = h_match.group(1)
                            cmd.extend([
                                "-f", f"bestvideo[height<=?{h}]+bestaudio/best[height<=?{h}]/best",
                                "--format-sort", f"res:{h},fps"
                            ])
                        else:
                            cmd.extend(["-f", "bestvideo+bestaudio/best"])
                    
                    if not settings.get("video_origin_stream", False):
                        cmd.extend(["--merge-output-format", target_ext])

                cmd.append(url)
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )

                self._active_download_process = proc
                if self.is_cancelled:
                    kill_process_tree(proc.pid)

                last_pct = -1
                last_time = 0
                for line in iter(proc.stdout.readline, ""):
                    clean = line.strip()
                    if "[download]" in clean and "%" in clean:
                        m = re.search(r"(\d+\.\d+)%", clean)
                        if m:
                            pct = float(m.group(1))
                            curr_time = time.time()
                            if int(pct) != last_pct or (curr_time - last_time) > 0.3:
                                last_pct = int(pct)
                                last_time = curr_time
                                msg = f"[{idx}/{total}] {clean}"
                                try:
                                    if self.window:
                                        self.window.evaluate_js(f"updateDownloadProgress({pct}, {json.dumps(msg)})")
                                except Exception: pass

                proc.communicate()
                self._active_download_process = None

                if not self.is_cancelled and getattr(proc, "returncode", None) == 0:
                    completed += 1
                    try:
                        if self.window:
                            self.window.evaluate_js(f"markDownloadSuccess({json.dumps(url)})")
                    except Exception:
                        pass

            self._active_download_process = None
            try:
                if self.window:
                    if self.is_cancelled:
                        status = f"Annulé – {completed}/{total} élément(s) téléchargé(s)."
                    else:
                        status = f"Traitement terminé – {completed}/{total} élément(s) téléchargé(s)."
                    self.window.evaluate_js(f"updateDownloadProgress(100, {json.dumps(status)})")
            except Exception:
                pass
            gc.collect()

        threading.Thread(target=_worker, daemon=True).start()

def _log_binary_setup_error(error):
    """Ne plus cacher silencieusement les erreurs du premier lancement."""
    try:
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] Installation des outils : {type(error).__name__}: {error}\n")
    except OSError:
        pass


def safe_download_file(url, target_path):
    """Téléchargement progressif et atomique : pas de fichier EXE incomplet."""
    tmp_path = target_path + ".tmp"
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with urllib.request.urlopen(url, timeout=45) as response, open(tmp_path, "wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        if os.path.getsize(tmp_path) == 0:
            raise ValueError("Fichier téléchargé vide")
        os.replace(tmp_path, target_path)
        return True
    except Exception as exc:
        _log_binary_setup_error(exc)
        return False
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def setup_binaries():
    """Premier lancement : ne pas charger FFmpeg intégralement dans la RAM."""
    try:
        if not os.path.isfile(YTDLP_PATH) or os.path.getsize(YTDLP_PATH) == 0:
            safe_download_file(YTDLP_URL, YTDLP_PATH)

        if not os.path.isfile(FFMPEG_PATH) or os.path.getsize(FFMPEG_PATH) == 0:
            zip_p = os.path.join(APP_DIR, "ffmpeg.zip")
            if not safe_download_file(FFMPEG_URL, zip_p):
                return
            try:
                with zipfile.ZipFile(zip_p, "r") as zf:
                    for member in zf.infolist():
                        if os.path.basename(member.filename).lower() not in ("ffmpeg.exe", "ffprobe.exe"):
                            continue
                        target_file = os.path.join(BIN_DIR, os.path.basename(member.filename))
                        temp_file = target_file + ".tmp"
                        try:
                            with zf.open(member, "r") as source, open(temp_file, "wb") as output:
                                shutil.copyfileobj(source, output, length=1024 * 1024)
                            if os.path.getsize(temp_file) == 0:
                                raise ValueError("Exécutable FFmpeg vide")
                            os.replace(temp_file, target_file)
                        finally:
                            if os.path.exists(temp_file):
                                try:
                                    os.remove(temp_file)
                                except OSError:
                                    pass
            finally:
                if os.path.exists(zip_p):
                    try:
                        os.remove(zip_p)
                    except OSError:
                        pass
    except Exception as exc:
        _log_binary_setup_error(exc)
    finally:
        gc.collect()

if __name__ == '__main__':
    try:
        # Afficher l'interface avant les verifications de yt-dlp et FFmpeg.
        # webview.start(func=...) demarre la fonction dans un thread seulement
        # une fois la boucle graphique initialisee (pas en concurrence avec CLR).
        api = DownloaderAPI()
        window = webview.create_window(
            'All Media Download',
            html=HTML_PAGE,
            js_api=api,
            width=1080,
            height=760,
            min_size=(920, 620),
            background_color='#f8fafc'
        )
        api.window = window

        # Conserver le moteur Windows deja utilise et les reglages performants.
        # L'initialisation des binaires se fait en arriere-plan apres le GUI.
        webview.start(func=setup_binaries, debug=False)
    except Exception as exc:
        handle_exception(type(exc), exc, exc.__traceback__)
        try:
            # Afficher aussi l'erreur precise dans la boite Windows :
            # l'utilisateur peut nous transmettre une capture sans chercher le journal.
            error_detail = f"{type(exc).__name__} : {exc}"
            if len(error_detail) > 900:
                error_detail = error_detail[:900] + "..."
            ctypes.windll.user32.MessageBoxW(
                0,
                "All-Download n'a pas pu démarrer.\n\n"
                "Cause signalée :\n" + error_detail + "\n\n"
                "Journal complet :\n" + CRASH_LOG,
                "All-Download - erreur de démarrage",
                0x10
            )
        except Exception:
            pass
        sys.exit(1)