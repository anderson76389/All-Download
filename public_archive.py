"""Archives publiques optionnelles pour All-Download.

Aucune extraction des jetons Twitch, aucun contournement de contenu privé.
Le seul fournisseur actuellement activé est Internet Archive : recherche dans
les métadonnées publiques et fichiers dont la licence ouverte est explicite.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

ARCHIVE_BASE = "https://archive.org"
SUPPORTED_EXTENSIONS = frozenset({".mp4", ".mkv", ".webm", ".mov", ".ts"})
MAX_MEDIA_BYTES = 40 * 1024**3
MAX_JSON_BYTES = 3 * 1024**2
VOD_ID_PATTERN = re.compile(r"(?<!\d)(\d{7,15})(?!\d)")
IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,99}$")


class ArchiveError(Exception):
    """Erreur récupérable, présentable dans l'interface."""


class ArchiveCancelled(ArchiveError):
    """Opération interrompue par l'utilisateur."""


def extract_twitch_vod_id(url):
    parsed = urllib.parse.urlsplit(str(url))
    host = (parsed.hostname or "").lower()
    if host not in ("twitch.tv", "www.twitch.tv", "m.twitch.tv"):
        return None
    match = re.fullmatch(r"/videos/(\d{7,15})/?", parsed.path, re.IGNORECASE)
    if not match:
        match = re.fullmatch(r"/[^/]+/v/(\d{7,15})/?", parsed.path, re.IGNORECASE)
    return match.group(1) if match else None


def _request(url, timeout=12):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={
            "User-Agent": "All-Download/1.0 (public Internet Archive metadata)",
            "Accept": "application/json",
        }), timeout=timeout
    )


def _json(url):
    with _request(url) as response:
        if urllib.parse.urlsplit(response.geturl()).hostname != "archive.org":
            raise ArchiveError("Réponse de métadonnées provenant d'un domaine inattendu.")
        raw = response.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            raise ArchiveError("Métadonnées trop volumineuses.")
    return json.loads(raw.decode("utf-8"))


def _scalar(value):
    if isinstance(value, list):
        return " ".join(str(part) for part in value[:30])
    return str(value or "")


def _public_license(metadata):
    """Éviter de traiter une copie non déclarée libre comme source autorisée."""
    license_url = _scalar(metadata.get("licenseurl", "")).strip()
    try:
        parsed = urllib.parse.urlsplit(license_url)
    except ValueError:
        return None
    domain = (parsed.hostname or "").lower()
    if domain not in ("creativecommons.org", "www.creativecommons.org"):
        return None
    if (parsed.scheme == "https"
            and (parsed.path.startswith("/licenses/")
                 or parsed.path.startswith("/publicdomain/"))):
        return license_url
    return None


def _references_exact_id(metadata, files, vod_id):
    pattern = re.compile(r"(?<!\d)" + re.escape(vod_id) + r"(?!\d)")
    fields = ("identifier", "title", "description", "source", "subject",
              "external-identifier", "external_identifier")
    if any(pattern.search(_scalar(metadata.get(key))) for key in fields):
        return True
    return any(pattern.search(str(f.get("name") or "")) for f in files[:100])


def search_twitch_public_archives(url, *, max_results=4):
    """Rechercher par ID exact. Une recherche sans résultat n'autorise aucun fallback."""
    vod_id = extract_twitch_vod_id(url)
    if not vod_id:
        raise ValueError("Seules les adresses de VOD Twitch sont acceptées.")
    query = {
        "q": f'"{vod_id}" AND mediatype:movies',
        "rows": "12", "output": "json",
        "fl[]": ["identifier", "title"],
    }
    search_url = ARCHIVE_BASE + "/advancedsearch.php?" + urllib.parse.urlencode(query, doseq=True)
    try:
        found = _json(search_url).get("response", {}).get("docs", [])
        candidates = []
        for doc in found[:12]:
            identifier = str(doc.get("identifier") or "")
            if not IDENTIFIER_PATTERN.fullmatch(identifier):
                continue
            details = _json(ARCHIVE_BASE + "/metadata/" + identifier)
            metadata = details.get("metadata") or {}
            files = details.get("files") or []
            license_url = _public_license(metadata)
            if not license_url or metadata.get("mediatype") != "movies":
                continue
            if not _references_exact_id(metadata, files, vod_id):
                continue
            for entry in files[:150]:
                filename = str(entry.get("name") or "")
                if (not filename or "/" in filename or "\\" in filename
                        or filename in (".", "..")
                        or Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS
                        or str(entry.get("private", "")).lower() == "true"):
                    continue
                try:
                    size = int(entry.get("size", 0))
                except (TypeError, ValueError):
                    continue
                if size < 1 or size > MAX_MEDIA_BYTES:
                    continue
                candidates.append({
                    "provider": "Internet Archive",
                    "vod_id": vod_id,
                    "identifier": identifier,
                    "file": filename,
                    "title": _scalar(metadata.get("title"))[:140],
                    "size": size,
                    "license": license_url,
                    "archive_page": ARCHIVE_BASE + "/details/" + urllib.parse.quote(identifier),
                })
                if len(candidates) >= max_results:
                    return candidates
        return candidates
    except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise ArchiveError("Recherche des archives indisponible : " + str(exc)) from exc


def download_public_archive(candidate, destination_root, *, progress=None, cancelled=None, opener=None):
    """Téléchargement progressif dans AUTRES, sans écrasement ou téléchargement hors IA."""
    if candidate.get("provider") != "Internet Archive":
        raise ArchiveError("Fournisseur inconnu.")
    identifier = str(candidate.get("identifier", ""))
    filename = str(candidate.get("file", ""))
    if not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ArchiveError("Identifiant d'archive invalide.")
    if (not filename or "/" in filename or "\\" in filename
            or filename in (".", "..") or Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS):
        raise ArchiveError("Nom de fichier d'archive invalide.")
    size = int(candidate.get("size", 0))
    if size < 1 or size > MAX_MEDIA_BYTES:
        raise ArchiveError("Taille du fichier d'archive invalide.")

    folder = Path(destination_root) / "AUTRES"
    folder.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(folder).free < size + 16 * 1024**2:
        raise ArchiveError("Espace disque insuffisant dans AUTRES.")
    final = None
    temp = None
    for i in range(10000):
        suffix = "" if i == 0 else f" ({i})"
        proposed = folder / (Path(filename).stem[:150] + suffix + Path(filename).suffix.lower())
        partial = folder / (proposed.name + ".part")
        if proposed.exists():
            continue
        try:
            output = partial.open("xb")
            final, temp = proposed, partial
            break
        except FileExistsError:
            continue
    else:
        raise ArchiveError("Impossible de créer un fichier libre dans AUTRES.")

    url = ARCHIVE_BASE + "/download/" + identifier + "/" + urllib.parse.quote(filename)
    request_fn = opener or _request
    received = 0
    try:
        with output, request_fn(url, timeout=30) as response:
            host = (urllib.parse.urlsplit(response.geturl()).hostname or "").lower()
            if not (host == "archive.org" or host.endswith(".archive.org")):
                raise ArchiveError("Téléchargement redirigé hors du fournisseur d'archives.")
            while True:
                if cancelled and cancelled():
                    raise ArchiveCancelled("Téléchargement annulé.")
                part = response.read(1024 * 1024)
                if not part:
                    break
                received += len(part)
                if received > MAX_MEDIA_BYTES or received > size + 1024 * 1024:
                    raise ArchiveError("Le fichier dépasse la taille publiée.")
                output.write(part)
                if progress:
                    progress(min(99, round(received * 100 / size)))
        if received != size:
            raise ArchiveError("Fichier incomplet : taille différente des métadonnées.")
        if final.exists():
            raise ArchiveError("Un fichier portant ce nom est apparu pendant le téléchargement.")
        os.rename(temp, final)
        if progress:
            progress(100)
        return str(final)
    except Exception:
        if temp is not None:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
        raise
