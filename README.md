<div align="center">

<img src="./logo.jpg" width="132" alt="Logo All-Download">

# All-Download

**Vidéos, musiques, GIF, playlists et chaînes : un seul logiciel pour vos téléchargements.**

Application Windows en français, basée sur [yt-dlp](https://github.com/yt-dlp/yt-dlp), [FFmpeg](https://ffmpeg.org/) et [pywebview](https://pywebview.flowrl.com/).

[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?style=flat-square&logo=windows11&logoColor=white)](https://github.com/anderson76389/All-Download)
[![Code source](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](./yt_app.py)
[![Tests Windows](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml/badge.svg)](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml)

## Télécharger All-Download

[![Windows Portable](https://img.shields.io/badge/T%C3%89L%C3%89CHARGER-WINDOWS%20PORTABLE-2563EB?style=for-the-badge&logo=windows11&logoColor=white)](https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Portable-Windows.zip)

[![Windows Classique](https://img.shields.io/badge/T%C3%89L%C3%89CHARGER-WINDOWS%20CLASSIQUE-374151?style=for-the-badge&logo=windows11&logoColor=white)](https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Classique-Windows.zip)

**Deux liens fixes, automatiquement mis à jour** avec la dernière [Release validée](https://github.com/anderson76389/All-Download/releases/latest).

</div>

---

## Choisir sa version

| | **Portable** | **Classique (installable)** |
|---|---|---|
| Lancement | EXE directement après extraction du ZIP | Installation via `All-Download-Setup.exe` |
| Installation nécessaire | Non | Oui, sans droits administrateur |
| Raccourcis Windows | À créer manuellement | Menu Démarrer ; Bureau en option |
| Désinstallation Windows | Supprimer le dossier portable | Paramètres Windows → Applications |
| Destination initiale des médias | Six dossiers à côté de l'EXE si accessibles en écriture | `Téléchargements\MediaDownloader` |
| Moteur de téléchargement | Identique | Identique |

**La version classique a été revue :** elle utilise désormais un véritable installateur Windows qui installe l'exécutable autonome de la version Portable. Elle **ne distribue plus le dossier `_internal`** responsable de l'erreur `Python.Runtime.dll` sur certaines installations Windows.

### Installation

**Portable :** téléchargez le ZIP Portable, extrayez tout son contenu dans un nouveau dossier, puis ouvrez `All_Media_Download.exe`.

**Classique :** téléchargez le ZIP Classique, extrayez-le et exécutez `All-Download-Setup.exe`. Suivez l'assistant pour installer l'application, créer éventuellement un raccourci sur le Bureau et la lancer depuis le menu Démarrer.

Les deux ZIP contiennent les **logos**, les **six dossiers** et la copie des **fichiers du dépôt** dans `Code-source/`. La version installable place le programme dans le profil Windows de l'utilisateur et conserve les téléchargements en dehors du dossier installé, pour éviter de les perdre à la désinstallation.

**Prérequis :** Windows 10/11 (64 bits), Microsoft Edge WebView2, connexion Internet pour les médias et de l'espace disque. yt-dlp et FFmpeg sont récupérés au premier lancement si nécessaire.

## Fonctionnalités

- **Vidéos :** choix de la qualité et de la résolution (jusqu'à 4K si la source le propose), formats MP4 et MKV.
- **Audio :** extraction et conversion en FLAC, M4A ou MP3.
- **GIF :** téléchargement direct et conversion de vidéos lorsque la source est compatible.
- **Playlists et chaînes :** téléchargement groupé et sélection d'une plage d'éléments.
- **File d'attente :** plusieurs liens, progression, journaux d'erreur, annulation et pause **entre les éléments**.
- **Options :** miniatures, métadonnées, normalisation audio, SponsorBlock, proxy, cookies et thèmes clair/sombre/OLED.

La prise en charge varie selon les sites, les droits d'accès, les formats disponibles et les changements apportés par les plateformes. La conversion vers FLAC ne restaure pas la qualité d'un audio compressé.

## Comment télécharger ?

1. Collez l'adresse du média dans All-Download et cliquez sur **Ajouter**.
2. Choisissez **Vidéo**, **Audio** ou **GIF**, ainsi que la qualité souhaitée.
3. Téléchargez un élément ou la file entière. Suivez l'avancement dans le logiciel.
4. Ouvrez le dossier de destination avec le bouton dédié.

### Organisation des médias

| Dossier | Fichiers |
|---|---|
| `VIDÉOS/` | Vidéos YouTube individuelles |
| `AUDIOS/` | Fichiers audio individuels |
| `GIFS/` | GIF téléchargés ou convertis |
| `CHAÎNES/` | Sous-dossiers par chaîne YouTube |
| `PLAYLIST/` | Sous-dossiers par playlist YouTube |
| `AUTRES/` | Autres médias et plateformes |

L'application crée les six catégories si elles n'existent pas. L'ancien dossier `AUDIO/` est migré vers `AUDIOS/` **sans écraser les fichiers homonymes**.

**Choix du dossier :** si une destination est déjà enregistrée dans la configuration, elle reste prioritaire. Sinon, la version Portable choisit ses dossiers voisins si elle peut y écrire, tandis que la version Classique installée utilise par défaut :

```text
%USERPROFILE%\Downloads\MediaDownloader
```

Une mise à jour ou une désinstallation de la version Classique ne doit pas nécessiter la suppression de vos médias.

## Code source et vérifications

Le dépôt comprend `yt_app.py` (application), les logos, les spécifications PyInstaller, `installer/All-Download.iss` (installateur Windows), `tests/` et la publication automatisée des [Releases](https://github.com/anderson76389/All-Download/releases).

Les compilations publiées sont soumises à des tests Python, des tests d'interaction de l'interface, à des essais de démarrage Windows et à une vérification des archives. Les téléchargements réels dépendent néanmoins des sites : **les tests automatisés ne garantissent pas tous les contenus ni toutes les plateformes**.

Pour lancer les sources avec Python 3.12 sous Windows :

```powershell
python -m pip install pywebview==6.2.1
python yt_app.py
```

Pour fabriquer l'EXE autonome :

```powershell
python -m pip install pyinstaller==6.22.3 pywebview==6.2.1 pythonnet==3.2.1
python -m PyInstaller --clean --noconfirm All_Media_Download-Portable.spec
```

> Le fichier `dist/All_Media_Download.exe` suivi historiquement dans le dépôt n'est **pas** la version actuelle. Utilisez les boutons de téléchargement en haut du README.

## Dépannage et sécurité

- **Application qui ne démarre pas :** consultez `%LOCALAPPDATA%\AllMediaDownload\crash_log.txt` et créez une [issue](https://github.com/anderson76389/All-Download/issues) avec la dernière erreur (sans données personnelles).
- **Téléchargement impossible :** vérifiez le lien, les cookies éventuels, la compatibilité de la source et les dépendances yt-dlp/FFmpeg.
- **Alerte Microsoft SmartScreen :** les exécutables ne sont pas encore signés avec un certificat d'éditeur reconnu. Une alerte de réputation est distincte d'une détection de menace ; ne désactivez pas votre antivirus et vérifiez toute détection.

Téléchargez uniquement les contenus pour lesquels vous disposez des droits nécessaires. All-Download ne contourne pas les protections DRM.

---

<div align="center">

Conçu et maintenu par [anderson76389](https://github.com/anderson76389) · [Versions Windows](https://github.com/anderson76389/All-Download/releases/latest) · [Signaler un problème](https://github.com/anderson76389/All-Download/issues)

</div>
