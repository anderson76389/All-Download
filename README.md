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
- **File d'attente** — plusieurs liens, suivi de la progression et journaux.
- **Personnalisation** — miniatures, métadonnées, thèmes clair/sombre/OLED et normalisation audio.
- **Options avancées** — SponsorBlock, cookies, proxy et paramètres d'extracteur.

La compatibilité dépend des plateformes et des flux accessibles via yt-dlp. La conversion en FLAC n'améliore pas la qualité d'une source déjà compressée.

## ⬇️ Installation sur Windows

1. Ouvrez les **[compilations Windows](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml)** et sélectionnez la dernière exécution réussie.
2. Sous **Artifacts**, téléchargez **`All-Download-Portable-Windows`** (édition recommandée, un seul EXE) puis décompressez le ZIP. Une connexion GitHub peut être nécessaire.
3. Lancez **`All_Media_Download.exe`** depuis le dossier extrait. Les logos et les six dossiers de médias sont fournis à côté de l'EXE. Au premier lancement, l'application récupère yt-dlp et FFmpeg s'ils sont absents.

**Alternative :** `All-Download-Dossier-Windows` comprend le dossier `_internal/` et évite l'extraction temporaire de l'application. Sur certaines installations Windows, les DLL de cette édition peuvent être bloquées par le marquage de sécurité hérité du ZIP téléchargé. Si cela arrive, utilisez plutôt l'édition Portable.

**Prérequis :** Windows, WebView2, connexion Internet et espace disque.

> **Important :** le fichier [`dist/All_Media_Download.exe`](./dist/All_Media_Download.exe) directement présent dans le dépôt est une **ancienne compilation**, et ne représente pas la version mise à jour. **SmartScreen peut toujours avertir** pour un EXE non signé : les corrections ne remplacent pas une signature de code reconnue.

## 🚀 Utilisation et dossiers

Collez une URL → ajoutez le média à la liste → choisissez **Vidéo**, **Audio** ou **GIF**, et sa qualité → cliquez sur **Télécharger**.

**Édition Portable :** les téléchargements sont rangés directement dans les six sous-dossiers placés à côté de `All_Media_Download.exe`, à condition que le dossier soit accessible en écriture. Si une destination est déjà enregistrée dans ta configuration, elle reste prioritaire.

**Version exécutée depuis Python ou dossier non modifiable :** emplacement de repli :

```text
%USERPROFILE%\Downloads\MediaDownloader
```

Les anciens médias restent à leur emplacement : aucun fichier n'est supprimé ni déplacé vers le nouveau dossier portable.

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

Le dépôt conserve le programme `yt_app.py`, les logos `logo.jpg` et `logo.ico`, les deux configurations de compilation `All_Media_Download.spec` et `All_Media_Download-Portable.spec`, les tests `tests/test_download_folders.py` et le workflow GitHub Actions. Les six dossiers multimédias sont présents sur GitHub et dans les ZIP grâce aux fichiers `.gitkeep` (petits fichiers marqueurs, sans effet sur les téléchargements).

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

Les tests automatisés sont exécutés avant chaque compilation Windows, suivis d'une vérification de lancement de la véritable fenêtre sur les deux éditions. Les deux compilations sont effectuées **sans UPX**.

## 🔧 Problèmes courants

- **Lien non pris en charge :** vérifiez le site, l'URL et l'extracteur yt-dlp.
- **Accès refusé :** vérifiez vos droits et, si nécessaire, les cookies.
- **Conversion impossible :** vérifiez FFmpeg et l'espace disque.
- **Plantage au lancement :** consultez `%LOCALAPPDATA%\AllMediaDownload\crash_log.txt` et ouvrez un [signalement](https://github.com/anderson76389/All-Download/issues).
- **Alerte Windows :** l'exécutable téléchargé n'est pas signé numériquement. SmartScreen peut afficher un avertissement de réputation ; une **détection de menace Microsoft Defender** est différente. Ne désactivez pas votre antivirus et ne forcez pas l'exécution en cas de détection : notez le nom exact de la menace et signalez-la avant de lancer l'application.

**Utilisation responsable :** téléchargez uniquement les contenus pour lesquels vous disposez des autorisations nécessaires. Les protections DRM ne sont pas contournées.

---

<div align="center">

**All-Download** · Créé et maintenu par [anderson76389](https://github.com/anderson76389)

</div>
