<div align="center">

<img src="./logo.jpg" alt="Logo All-Download" width="140">

# ALL-DOWNLOAD

**⚡ Vidéos, musiques, GIF, playlists et chaînes : tout au même endroit.**

Téléchargeur multimédia **Windows**, avec interface en français, propulsé par [yt-dlp](https://github.com/yt-dlp/yt-dlp) et [FFmpeg](https://ffmpeg.org/).

[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?style=flat-square)](https://github.com/anderson76389/All-Download)
[![Python](https://img.shields.io/badge/Python-3-3776AB?style=flat-square&logo=python&logoColor=white)](./yt_app.py)
[![Build Windows](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml/badge.svg)](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml)

### ⬇️ Téléchargements Windows

[![Télécharger Portable Windows](https://img.shields.io/badge/T%C3%89L%C3%89CHARGER-WINDOWS%20PORTABLE-2563EB?style=for-the-badge&logo=windows11&logoColor=white)](https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Portable-Windows.zip)

[![Télécharger Windows classique](https://img.shields.io/badge/T%C3%89L%C3%89CHARGER-WINDOWS%20CLASSIQUE-4B5563?style=for-the-badge&logo=windows11&logoColor=white)](https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Classique-Windows.zip)

**Liens permanents et fixes** : ils pointent automatiquement vers les fichiers ZIP de la dernière [version publiée](https://github.com/anderson76389/All-Download/releases/latest).

Chaque ZIP contient **l'application complète**, les logos, les six dossiers multimédias et **tous les fichiers suivis du dépôt** dans `Code-source/`.

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

## ⬇️ Installer All-Download

1. Cliquez sur le bouton **Windows Portable** ci-dessus (recommandé).
2. Décompressez le ZIP dans un nouveau dossier.
3. Lancez **`All_Media_Download.exe`**. Les logos et les six dossiers multimédias sont déjà fournis.

**Portable :** un seul exécutable, sans dossier `_internal/`. **Windows classique :** une distribution avec `_internal/`. Cette dernière a provoqué sur certains PC l'erreur `Python.Runtime.dll` : **choisissez Portable si vous rencontrez cette erreur**. Les deux archives comprennent le même code source complet dans `Code-source/`.

**Prérequis :** Windows, WebView2, connexion Internet et espace disque.

> **Important :** le fichier [`dist/All_Media_Download.exe`](./dist/All_Media_Download.exe) déjà suivi dans le dépôt est une **ancienne compilation**. Les ZIP des boutons ci-dessus sont mis à jour automatiquement lors des compilations validées. SmartScreen peut encore avertir pour un EXE non signé ; ne désactivez pas les protections de Windows.

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
