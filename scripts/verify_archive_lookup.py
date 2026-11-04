"""Vérification en ligne non bloquante du fournisseur d'archives publiques.

Ne télécharge aucun contenu. Résultat vide = pas de copie vérifiable.
Exécuter indépendamment des tests unitaires pour éviter les faux échecs réseau.
"""
from public_archive import ArchiveError, search_twitch_public_archives

URL = "https://www.twitch.tv/videos/2905228526"


def main():
    try:
        candidates = search_twitch_public_archives(URL)
    except ArchiveError as exc:
        print("Archive publique : service indisponible :", exc)
        raise SystemExit(1)
    print("Recherche Internet Archive réellement exécutée pour la VOD 2905228526.")
    print("Fichiers exacts avec licence ouverte :", len(candidates))
    for candidate in candidates:
        print(" -", candidate["archive_page"], candidate["file"])
    if not candidates:
        print("Aucune copie vérifiable. Le logiciel doit afficher honnêtement ce résultat.")


if __name__ == "__main__":
    main()
