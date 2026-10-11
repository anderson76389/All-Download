<div align="center">

<img src="./logo.jpg" alt="Logo All-Download" width="140">

# ALL-DOWNLOAD

**⚡ Vidéos, musiques, GIF, playlists et chaînes : tout au même endroit.**

Téléchargeur multimédia **Windows**, avec interface en français, propulsé par [yt-dlp](https://github.com/yt-dlp/yt-dlp) et [FFmpeg](https://ffmpeg.org/).

[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?style=flat-square)](https://github.com/anderson76389/All-Download)
[![Python](https://img.shields.io/badge/Python-3-3776AB?style=flat-square&logo=python&logoColor=white)](./yt_app.py)
[![Build Windows](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml/badge.svg)](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml)

**[⬇ Télécharger pour Windows](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml)** · **[📂 Code source](./yt_app.py)**

</div>

---

## ✨ Fonctionnalités

- **Vidéo** — qualité automatique ou résolution choisie, jusqu'à la 4K si disponible ; MP4 et MKV.
- **Audio** — extraction et conversion en FLAC, M4A ou MP3.
- **GIF** — conversion de vidéos et récupération de GIF directs compatibles.
- **Playlists et chaînes** — téléchargement groupé, avec sélection des éléments.
- **File d'attente** — progression, pause, reprise, annulation et journaux.
- **Personnalisation** — miniatures, métadonnées, thèmes clair/sombre/OLED et normalisation audio.
- **Options avancées** — SponsorBlock, cookies, proxy et paramètres d'extracteur.

La compatibilité dépend des plateformes et des flux accessibles via yt-dlp. La conversion en FLAC n'améliore pas la qualité d'une source déjà compressée.

## ⬇️ Installation sur Windows

1. Ouvrez les **[compilations Windows](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml)**.
2. Choisissez une exécution réussie, puis téléchargez **`All-Download-Windows`** sous **Artifacts** (connexion GitHub parfois nécessaire).
3. Décompressez l'archive et lancez **`All_Media_Download.exe`**. L'application récupère yt-dlp et FFmpeg au premier lancement s'ils sont absents.

**Prérequis :** Windows, WebView2, connexion Internet et espace disque.

> Le fichier [`dist/All_Media_Download.exe`](./dist/All_Media_Download.exe) présent dans le dépôt est une **ancienne compilation**. Pour obtenir les dernières corrections, utilisez l'artefact de la dernière compilation réussie.

## 🚀 Utilisation et dossiers

Collez une URL → ajoutez le média à la liste → choisissez **Vidéo**, **Audio** ou **GIF**, et sa qualité → cliquez sur **Télécharger**.

Dossier de destination par défaut :

```text
%USERPROFILE%\Downloads\MediaDownloader
```

| Dossier | Contenu |
| --- | --- |
| `VIDÉOS/` | Vidéos YouTube individuelles |
| `AUDIOS/` | Fichiers audio individuels, de YouTube ou d'autres plateformes |
| `GIFS/` | GIF téléchargés directement ou convertis |
| `CHAÎNES/` | Chaînes YouTube, avec un sous-dossier par chaîne |
| `PLAYLIST/` | Playlists YouTube, avec un sous-dossier par playlist |
| `AUTRES/` | Autres médias |

Ces **six dossiers** sont créés automatiquement. Le dossier historique `AUDIO/` est migré vers `AUDIOS/` sans écraser les fichiers homonymes ; en cas de conflit, ceux-ci restent dans l'ancien dossier.

## 🛠️ Code source

Le dépôt contient le programme `yt_app.py`, les logos `logo.jpg` et `logo.ico`, la configuration de compilation `All_Media_Download.spec`, les tests dans `tests/test_download_folders.py` et le workflow GitHub Actions. Les dossiers multimédias sont conservés sur GitHub avec des fichiers `.gitkeep`.

Pour lancer le logiciel depuis Python sous Windows :

```powershell
python -m pip install pywebview
python yt_app.py
```

Pour compiler l'exécutable :

```powershell
python -m pip install pyinstaller pywebview
python -m PyInstaller --clean --noconfirm All_Media_Download.spec
```

Les tests automatisés sont exécutés avant chaque compilation Windows.

## 🔧 Problèmes courants

- **Lien non pris en charge :** vérifiez le site, l'URL et l'extracteur yt-dlp.
- **Accès refusé :** vérifiez vos droits et, si nécessaire, les cookies.
- **Conversion impossible :** vérifiez FFmpeg et l'espace disque.
- **Plantage au lancement :** consultez `%LOCALAPPDATA%\AllMediaDownload\crash_log.txt` et ouvrez un [signalement](https://github.com/anderson76389/All-Download/issues).

**Utilisation responsable :** téléchargez uniquement les contenus pour lesquels vous disposez des autorisations nécessaires. Les protections DRM ne sont pas contournées.

---

<div align="center">

**All-Download** · Créé et maintenu par [anderson76389](https://github.com/anderson76389)

</div>
