#!/usr/bin/env python3
"""Read-only, low-cost weekly GitHub metadata check: no video/API scraping or builds."""
from __future__ import annotations
import json
import os
import re
from urllib.request import Request, urlopen

UPSTREAMS = (
    ("yt-dlp", "yt-dlp/yt-dlp"),
    ("FFmpeg-Builds", "yt-dlp/FFmpeg-Builds"),
    ("TwitchDownloader", "lay295/TwitchDownloader"),
)
MAX_RESPONSE = 2_000_000
VERSION = re.compile(r"^[A-Za-z0-9._+/-]{1,100}$")

def fetch_latest(slug: str) -> dict:
    if slug not in {item[1] for item in UPSTREAMS}:
        raise ValueError("Upstream not explicitly allowed.")
    request = Request("https://api.github.com/repos/" + slug + "/releases/latest",
                      headers={"User-Agent": "All-Download-maintenance-check",
                               "Accept": "application/vnd.github+json"})
    with urlopen(request, timeout=9) as response:
        raw = response.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise ValueError("Upstream response oversized.")
    obj = json.loads(raw)
    tag = obj.get("tag_name", "")
    page = obj.get("html_url", "")
    if not isinstance(tag, str) or not VERSION.fullmatch(tag):
        raise ValueError("Unexpected upstream version.")
    if not isinstance(page, str) or not page.startswith(
            "https://github.com/" + slug + "/releases/tag/"):
        raise ValueError("Unexpected upstream release URL.")
    return {"tag": tag, "url": page}

def main() -> int:
    lines = ["### Sources externes All-Download (vérification hebdomadaire)",
             "",
             "| Dépendance | Release actuelle amont |",
             "|:--|:--|"]
    failures = []
    for name, repo in UPSTREAMS:
        try:
            release = fetch_latest(repo)
            lines.append("| " + name + " | " + release["tag"] + " |")
            print(name + ": " + release["tag"] + " -> " + release["url"])
        except (OSError, TimeoutError, ValueError, TypeError, KeyError) as error:
            failures.append(name)
            lines.append("| " + name + " | indisponible |")
            print("::warning::" + name + " : " + str(error)[:180])
    lines.extend(["", "Lecture seule : aucune mise à jour automatique, aucun téléchargement "
                  "de média, aucun test de compatibilité prétendu réussi."])
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write("\n".join(lines) + "\n")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
