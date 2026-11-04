"""Préparer une extension Chromium DÉMONSTRATION pour le test WebView2 Windows.

Ce contenu minimal est original et ne contient AUCUN fichier d'Andre Bradshaw.
Le dossier est créé près de l'EXE construit, jamais dans l'artifact partagé.
"""
from pathlib import Path
import json
import sys

def main():
    target = Path(sys.argv[1]).resolve()
    data = target / "Donnees"
    extension = data / "Extensions" / "TwitchVODDownloader"
    extension.mkdir(parents=True, exist_ok=True)
    (extension / "manifest.json").write_text(json.dumps({
        "manifest_version": 3,
        "name": "Twitch VOD Downloader (All-Download smoke test)",
        "version": "3.26",
        "description": "Temporary local extension fixture for WebView2 CI only",
        "content_scripts": [{
            "matches": ["https://www.twitch.tv/*"],
            "js": ["content.js"]
        }]
    }), encoding="utf-8")
    (extension / "content.js").write_text(
        "document.documentElement.dataset.allDownloadSmoke = 'installed';\n",
        encoding="utf-8")
    (extension / ".all-download-installed.json").write_text(json.dumps({
        "extension_id": "gaabmdjigfcnkgeommfpnoinpdmpfhaj",
        "version": "3.26", "source": "CI fixture (not shipped)"
    }), encoding="utf-8")
    (data / "config.json").write_text(json.dumps({
        "twitch_native_extension_enabled": True
    }), encoding="utf-8")
    print("Temporary WebView2 extension prepared:", extension)

if __name__ == "__main__":
    main()
