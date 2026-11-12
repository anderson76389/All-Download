#!/usr/bin/env python3
"""Verify downloaded Windows ZIP / Android APK / Linux archive using its SHA-256 sidecar.

Offline, read-only, bounded-memory. A matching SHA-256 checks integrity, NOT
publisher authenticity: also verify Android's signing certificate and source.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import re
import sys

FILE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,200}$")
SHA_LINE = re.compile(r"^([a-fA-F0-9]{64})[ \t]+\*?([A-Za-z0-9._-]+)$")
VALID = (".zip", ".apk", ".tar.xz", ".tar.gz")

class VerificationError(ValueError):
    pass

def verify_asset(archive: Path, checksum_path: Path | None = None) -> str:
    archive = Path(archive)
    if not archive.is_file() or not archive.name.endswith(VALID):
        raise VerificationError("Archive absente ou extension non prise en charge.")
    if not FILE_PATTERN.fullmatch(archive.name):
        raise VerificationError("Nom d'archive non autorisé.")
    checksum = checksum_path or Path(str(archive) + ".sha256")
    if not checksum.is_file() or checksum.stat().st_size > 4096:
        raise VerificationError("Checksum .sha256 manquant ou anormalement volumineux.")
    try:
        text = checksum.read_text("ascii").strip()
    except UnicodeError as e:
        raise VerificationError("Checksum non ASCII.") from e
    match = SHA_LINE.fullmatch(text)
    if match is None or match.group(2) != archive.name:
        raise VerificationError("Empreinte SHA-256 ou nom de fichier incorrect.")
    h = hashlib.sha256()
    with archive.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    actual = h.hexdigest()
    if actual != match.group(1).lower():
        raise VerificationError("Archive corrompue ou différente de l'empreinte officielle.")
    return actual

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path,
                        help="Archives avec fichier .sha256 de même nom à côté")
    args = parser.parse_args()
    failures = 0
    for archive in args.files:
        try:
            h = verify_asset(archive)
            print("OK", archive.name, h)
        except (VerificationError, OSError) as exc:
            print("ÉCHEC", archive, exc, file=sys.stderr)
            failures += 1
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
