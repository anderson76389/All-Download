"""Test réel et non intrusif du refus Twitch 2905228526.

Télécharge le vrai yt-dlp officiel Windows dans un répertoire TEMP jetable.
Extrait les métadonnées Twitch, mais ne télécharge AUCUN fichier média et
n'essaie pas de contourner les restrictions d'accès.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import yt_app

URL = "https://www.twitch.tv/videos/2905228526"


def main():
    with tempfile.TemporaryDirectory(prefix="all-download-twitch-live-") as folder:
        exe = Path(folder) / "yt-dlp.exe"
        if not yt_app.safe_download_file(yt_app.YTDLP_URL, str(exe)):
            raise RuntimeError("Impossible de télécharger le véritable yt-dlp pour le test.")
        if not yt_app.is_valid_windows_executable(str(exe)):
            raise RuntimeError("yt-dlp Windows téléchargé non valide.")

        version = subprocess.run(
            [str(exe), "--version"], text=True, capture_output=True,
            timeout=30, check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        ).stdout.strip()
        print("Version yt-dlp Windows réellement exécutée :", version)
        print("URL vérifiée :", URL)

        try:
            test = subprocess.run(
                [str(exe), "--ignore-config", "--no-warnings",
                 "--no-playlist", "--skip-download", "--dump-single-json", URL],
                text=True, capture_output=True, errors="replace", timeout=95,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
        except subprocess.TimeoutExpired:
            print("Twitch : analyse réseau expirée après 95s, aucun contenu téléchargé.")
            return

        result = (test.stderr or "") + "\n" + (test.stdout if test.returncode else "")
        if test.returncode == 0:
            print("TWITCH_REAL_STATUS = METADATA_ACCESSIBLE")
            print("Les métadonnées ont pu être extraites. Cela ne prouve PAS un téléchargement complet.")
        elif yt_app.is_twitch_subscriber_error(result):
            print("TWITCH_REAL_STATUS = SUBSCRIBER_ONLY")
            print("Twitch refuse l'accès à la VOD sans compte autorisé.")
            print("La recherche d'une archive autorisée reste un moteur distinct.")
        elif "HTTP Error 403" in result or "Forbidden" in result:
            print("TWITCH_REAL_STATUS = HTTP_403")
            print("Accès refusé par le site : l'origine exacte dépend de Twitch.")
        else:
            print("TWITCH_REAL_STATUS = AUTRE_ERREUR")
            print("yt-dlp a échoué pour une autre raison, code", test.returncode)
            print("Extrait final de l'erreur (données sensibles masquées) :")
            import re
            safe = re.sub(
                r"(?i)((?:access_token|oauth|token|sig|signature|key)=)[^&\s]+",
                r"\1[masqué]", (test.stderr or "")[-350:]
            )
            print(safe)

if __name__ == "__main__":
    main()
