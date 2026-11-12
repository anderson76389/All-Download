# All-Download Linux x86_64 — bêta

**Version 0.1.3-beta :** les VOD Twitch dont la qualité préférée est 1080p retombent sur le **720p natif** si le 1080p n'existe pas (sans upscaling). Les dossiers temporaires d'une exécution interrompue depuis plus de sept jours sont nettoyés prudemment au démarrage : 16 dossiers maximum et uniquement dans `Donnees/temporaires/`. La recherche manuelle de mises à jour privilégie désormais l'archive `.tar.xz` si son SHA-256 est fourni. Le raccourci Linux et les fonctions 0.1.2 restent disponibles.

La version Linux reprend le **HTML/CSS/JS Windows à l'identique** (extrait automatiquement de yt_app.py), mais utilise une fenêtre native Qt WebEngine et des binaires Linux yt-dlp/FFmpeg. **Aucun EXE Windows n'est exécuté.**

## Installer et démarrer

1. Télécharger All-Download-Linux-x86_64.tar.xz (ou .tar.gz) depuis la Release Linux 0.1.3-beta.
2. Décompresser le dossier All-Download dans un emplacement où l'utilisateur peut écrire.
3. Ouvrir ce dossier, puis lancer All-Download-Linux (pas besoin de sudo).
4. Les médias sont stockés dans les sept dossiers VIDÉOS, AUDIOS, GIFS, TWITCH, PLAYLIST, CHAÎNES et AUTRES. Paramètres, cookies facultatifs et cache restent sous Donnees/.

### Mises à jour et raccourcis de bureau

- **Paramètres → Appli → Linux → Vérifier les mises à jour Linux :** recherche sur demande parmi les Releases Linux officielles de ce dépôt. Un bouton permet d'ouvrir la page de la nouvelle version. L'application ne télécharge et n'installe rien automatiquement.
- **Ajouter au menu des applications :** crée un fichier `all-download-linux.desktop` dans `~/.local/share/applications/` (ou `$XDG_DATA_HOME/applications/`). Le chemin absolu pointe vers l'exécutable de votre dossier portable. Le raccourci est réversible depuis le même écran, sans sudo.
- **Mise à jour manuelle :** fermer l'application avant de remplacer les fichiers de la version précédente ; faire une sauvegarde de `Donnees/` et des dossiers de médias. Ne pas déplacer ou supprimer vos données par erreur.
- L'archive `.tar.xz` est une variante plus compressée ; l'archive `.tar.gz` reste disponible. Un fichier SHA-256 accompagne chacune.
- Si vous déplacez All-Download vers un autre répertoire, recréez le raccourci depuis les paramètres pour actualiser son chemin.

### Compatibilité et limites

- Version Linux **x86_64 glibc** compilée et testée en CI sur Ubuntu 22.04, puis le paquet est lancé et testé sur Ubuntu 24.04. Qt WebEngine peut nécessiter des bibliothèques graphiques système selon la distribution.
- Modes vidéo, audio MP3/M4A/FLAC, GIF, chaînes, playlists, qualités, miniatures, métadonnées, proxy, thèmes et boutons de file d'attente sont implémentés dans un backend Linux natif. Les résultats réels dépendent des sites.
- yt-dlp Linux, FFmpeg et FFprobe sont inclus dans l'archive publiée. La version Linux n'exécute pas TwitchDownloaderCLI.exe : les Twitch VOD passent par yt-dlp et n'ont pas toutes les garanties du moteur spécialisé Windows.
- Pause/Reprise utilise des signaux de processus Linux; Annuler termine les processus de téléchargement. Certains services peuvent exiger un accès authentifié.
- Certaines vidéos YouTube demandent Deno; le placer dans Donnees/bin/deno si nécessaire. Il n'est pas embarqué dans la première archive.
- Pas encore d'installateur .deb/.rpm ni de mises à jour Linux automatiques. Le contrôle des Releases est manuel ; les APK Android et ZIP Windows restent indépendants.
- Linux nécessite une session graphique (X11/Wayland) et les bibliothèques Qt6 nécessaires. Les contenus protégés par DRM ne sont pas pris en charge.

## Développement depuis le dépôt

Sous Linux, avec Python 3.10+, yt-dlp et FFmpeg dans le PATH et une session graphique :

    python3 -m venv .venv
    . .venv/bin/activate
    pip install "pywebview[qt]==6.2.1"
    python3 linux/app.py

Le script linux/extract_ui.py extrait exactement l'interface HTML de yt_app.py, **sans exécuter** les instructions Windows. Les binaires peuvent également être placés sous Donnees/bin/. Le projet doit rester dans un dossier modifiable afin de préserver toutes les données en local.

Le workflow Build and test Linux (beta) vérifie l'extraction HTML, la syntaxe et les tests de logique Linux, fabrique un paquet PyInstaller et crée une Release préliminaire distincte uniquement en cas de réussite. La compatibilité avec toutes les distributions et plateformes vidéo nécessite encore des essais réels.
