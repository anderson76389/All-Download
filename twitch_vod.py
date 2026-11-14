"""Intégration facultative de TwitchDownloaderCLI pour les VOD Twitch.

Aucune dépendance Python/.NET ajoutée : le CLI Windows x64 autonome est téléchargé
à la demande depuis la release officielle, vérifié, puis exécuté en sous-processus.
Le moteur yt-dlp reste inchangé pour les autres contenus.
"""

import hashlib
import json
import os
import posixpath
import re
import shutil
import threading
import urllib.parse
import urllib.request
import zipfile

RELEASE_API = "https://api.github.com/repos/lay295/TwitchDownloader/releases/latest"
CLI_FILENAME = "TwitchDownloaderCLI.exe"
_MAX_ZIP_BYTES = 150 * 1024 * 1024
_MAX_EXE_BYTES = 300 * 1024 * 1024
_INSTALL_LOCK = threading.RLock()


def twitch_vod_id(url):
    """Reconnaître une vraie URL de VOD Twitch (jamais un clip ou un autre domaine)."""
    if not isinstance(url, str):
        return None
    try:
        parsed = urllib.parse.urlsplit(url.strip())
        if (parsed.scheme.lower() not in ("http", "https")
                or parsed.username or parsed.password
                or (parsed.hostname or "").lower() not in
                ("twitch.tv", "www.twitch.tv", "m.twitch.tv")):
            return None
        match = re.fullmatch(r"/videos/([0-9]{5,20})/?", parsed.path, re.IGNORECASE)
        return match.group(1) if match else None
    except ValueError:
        return None


TWITCH_VIDEO_QUALITIES = [
    "Meilleure qualité (Auto)",
    "1080p (60fps)", "720p (60fps)", "720p (30fps)",
    "480p (30fps)", "360p (30fps)", "160p (30fps)",
]



TWITCH_DEFAULT_QUALITY = "1080p (60fps)"


def preferred_twitch_quality(formats):
    """Prefer the best advertised native quality at or below 1080p."""
    options = [value for value in (formats or []) if isinstance(value, str)]
    def rank(value):
        match = re.fullmatch(r"(\d{3,4})p(?:\s*\((\d{2,3})fps\))?", value)
        return (int(match[1]), int(match[2] or 0)) if match else (0, 0)
    capped = [v for v in options if 0 < rank(v)[0] <= 1080]
    return max(capped, key=rank) if capped else TWITCH_DEFAULT_QUALITY



def fallback_metadata(url, formats=None):
    """Carte Twitch avec choix de qualité, même si yt-dlp refuse la VOD.

    Les profils proposés par défaut sont vérifiés au téléchargement. Lorsqu'une
    détection HLS réussit, la carte ne montre que les qualités réellement
    annoncées disponibles.
    """
    vod_id = twitch_vod_id(url)
    if not vod_id:
        return None
    formats = ["Meilleure qualité (Auto)"] + [
        value for value in (formats if formats is not None else TWITCH_VIDEO_QUALITIES[1:])
        if value in TWITCH_VIDEO_QUALITIES[1:]
    ]
    quality = preferred_twitch_quality(formats)
    return {
        "title": "VOD Twitch " + vod_id,
        "thumbnail": "",
        "duration": "—",
        "url": url,
        "mode": "Vidéo",
        "formats": formats,
        "selectedQuality": quality,
        "selectedQualityLabel": quality,
        "is_channel": False,
        "channel_title": "",
        "is_playlist": False,
        "playlist_title": "",
        "item_count": 1,
        "start_idx": 1,
        "end_idx": 1,
        "is_direct_download": False,
        "isError": False,
    }


def selected_quality_to_cli(quality):
    """Exemple : '1080p (60fps)' -> '1080p60', Auto -> aucun filtre."""
    if not isinstance(quality, str) or quality.startswith("Meilleure qualité"):
        return None
    match = re.fullmatch(r"\s*(\d{3,4})p(?:\s*\((\d{2,3})fps\))?\s*", quality)
    if not match:
        return None
    return match.group(1) + "p" + (match.group(2) or "")


def progress_percentage(line):
    """TwitchDownloader écrit [STATUS] et met parfois à jour sa ligne avec CR."""
    if not isinstance(line, str) or "[STATUS]" not in line:
        return None
    match = re.search(r"(?<!\d)(\d{1,3})(?:\.\d+)?\s*%", line)
    if not match:
        return None
    pct = int(match.group(1))
    return pct if 0 <= pct <= 100 else None


def build_command(cli_path, url, title, quality, destination, ffmpeg_path, cache_dir):
    """Construire la commande sans shell, sans écrasement ni boîte de dialogue."""
    vod_id = twitch_vod_id(url)
    if not vod_id:
        raise ValueError("URL de VOD Twitch invalide.")
    name = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "_", str(title or "VOD Twitch")).strip(" .")
    name = (name[:90].rstrip(" .") or "Twitch_VOD")
    # Préfixe stable : même si le titre est réservé sous Windows, le nom est valide.
    output = os.path.join(destination, "Twitch_" + vod_id + "_" + name + ".mp4")
    cmd = [
        cli_path, "videodownload", "--id", vod_id,
        "--output", output, "--collision", "Rename",
        "--banner=false", "--ffmpeg-path", ffmpeg_path,
        "--temp-path", cache_dir,
    ]
    quality_arg = selected_quality_to_cli(quality)
    if quality_arg:
        cmd.extend(["--quality", quality_arg])
    return cmd


def _get_release_asset():
    req = urllib.request.Request(
        RELEASE_API,
        headers={
            "User-Agent": "All-Download-TwitchDownloaderCLI",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=35) as response:
        release = json.load(response)
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        url = asset.get("browser_download_url", "")
        if (re.fullmatch(r"TwitchDownloaderCLI-.+-Windows-x64\.zip", name)
                and url.startswith(
                    "https://github.com/lay295/TwitchDownloader/releases/download/")
                and isinstance(asset.get("size"), int)
                and 0 < asset["size"] <= _MAX_ZIP_BYTES):
            return asset
    raise ValueError("Aucune archive officielle TwitchDownloaderCLI Windows x64 trouvée.")


def ensure_cli_ready(bin_dir, validator):
    """Installer l'EXE atomiquement. Retourne (succès, erreur en français).

    Le fichier existant n'est jamais supprimé/remplacé s'il est valide.
    Aucun binaire non vérifié n'est exécuté.
    """
    target = os.path.join(bin_dir, CLI_FILENAME)
    if validator(target):
        return True, ""
    with _INSTALL_LOCK:
        if validator(target):
            return True, ""
        zip_tmp = target + ".zip.part"
        exe_tmp = target + ".tmp"
        try:
            os.makedirs(bin_dir, exist_ok=True)
            asset = _get_release_asset()
            digest = asset.get("digest", "")
            expected = digest[7:].lower() if isinstance(digest, str) and re.fullmatch(
                r"sha256:[0-9a-fA-F]{64}", digest) else None
            checksum = hashlib.sha256()
            downloaded = 0
            req = urllib.request.Request(
                asset["browser_download_url"],
                headers={"User-Agent": "All-Download-TwitchDownloaderCLI"},
            )
            with urllib.request.urlopen(req, timeout=90) as response, open(zip_tmp, "wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > _MAX_ZIP_BYTES:
                        raise ValueError("Archive TwitchDownloader anormalement volumineuse.")
                    output.write(chunk)
                    checksum.update(chunk)
            if downloaded != asset["size"]:
                raise ValueError("Archive TwitchDownloader incomplète.")
            if expected and checksum.hexdigest() != expected:
                raise ValueError("Empreinte SHA-256 TwitchDownloader incorrecte.")
            with zipfile.ZipFile(zip_tmp) as archive:
                executables = [
                    member for member in archive.infolist()
                    if not member.is_dir()
                    and posixpath.basename(member.filename) == CLI_FILENAME
                ]
                if len(executables) != 1 or not (
                    65536 <= executables[0].file_size <= _MAX_EXE_BYTES
                ):
                    raise ValueError("Exécutable TwitchDownloader absent ou invalide dans l'archive.")
                with archive.open(executables[0]) as source, open(exe_tmp, "wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
            if not validator(exe_tmp):
                raise ValueError("TwitchDownloaderCLI n'est pas un exécutable Windows x64 valide.")
            os.replace(exe_tmp, target)
            return True, ""
        except Exception as exc:
            return False, str(exc) or "Installation de TwitchDownloaderCLI impossible."
        finally:
            for path in (zip_tmp, exe_tmp):
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass
                except OSError:
                    pass
