"""Explicit, read-only Linux update check against official GitHub Releases.

Never downloads, executes or replaces binaries; opening the release is an
intentional, separate UI action. No background network traffic on startup.
"""
from __future__ import annotations

import json
import re
from urllib.request import Request, urlopen

CURRENT_LINUX_VERSION = "0.1.5-beta"
RELEASE_API = "https://api.github.com/repos/anderson76389/All-Download/releases?per_page=30"
RELEASE_ROOT = "https://github.com/anderson76389/All-Download/releases"
VERSION_PATTERN = re.compile(r"^linux-v([0-9]+)\.([0-9]+)\.([0-9]+)-beta$")
REQUIRED_ASSET = "All-Download-Linux-x86_64.tar.gz"
REQUIRED_CHECKSUM = REQUIRED_ASSET + ".sha256"
COMPACT_ASSET = "All-Download-Linux-x86_64.tar.xz"
COMPACT_CHECKSUM = COMPACT_ASSET + ".sha256"


def parse_linux_version(value: str):
    if not isinstance(value, str):
        return None
    match = VERSION_PATTERN.fullmatch(value)
    return tuple(map(int, match.groups())) if match else None


def check_linux_updates():
    """Return a safe, fixed-origin release link without installing anything."""
    current = parse_linux_version("linux-v" + CURRENT_LINUX_VERSION)
    assert current is not None
    request = Request(
        RELEASE_API,
        headers={
            "User-Agent": "All-Download-Linux/" + CURRENT_LINUX_VERSION,
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urlopen(request, timeout=8) as response:
            payload = response.read(350_001)
        if len(payload) > 350_000:
            raise ValueError("Réponse GitHub trop volumineuse.")
        releases = json.loads(payload.decode("utf-8"))
        if not isinstance(releases, list):
            raise ValueError("Réponse GitHub inattendue.")
        candidates = []
        for release in releases:
            if not isinstance(release, dict) or release.get("draft"):
                continue
            tag = release.get("tag_name")
            version = parse_linux_version(tag)
            assets = release.get("assets", [])
            if version is None or not isinstance(assets, list):
                continue
            names = {a.get("name") for a in assets if isinstance(a, dict)}
            if not {REQUIRED_ASSET, REQUIRED_CHECKSUM}.issubset(names):
                continue
            # Prefer the smaller xz package, but never without its checksum.
            preferred = (COMPACT_ASSET if {COMPACT_ASSET, COMPACT_CHECKSUM}.issubset(names)
                         else REQUIRED_ASSET)
            candidates.append((version, tag, preferred))
        if not candidates:
            return {"success": False, "error": "Aucune Release Linux complète trouvée."}
        latest, tag, asset = max(candidates, key=lambda item: item[0])
        # Never trust a URL delivered by a remote JSON response.
        url = RELEASE_ROOT + "/tag/" + tag
        return {
            "success": True,
            "available": latest > current,
            "current": CURRENT_LINUX_VERSION,
            "latest": tag.removeprefix("linux-v"),
            "url": url,
            "preferred_asset": asset,
            "checksum_asset": asset + ".sha256",
        }
    except (OSError, UnicodeError, ValueError, TimeoutError) as error:
        return {
            "success": False,
            "current": CURRENT_LINUX_VERSION,
            "error": "Vérification indisponible : " + str(error)[:140],
        }
