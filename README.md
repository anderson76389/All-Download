<div align="center">

<img src="./logo.jpg" alt="All-Download" width="160">

# ⚡ ALL-DOWNLOAD

### Toutes vos vidéos, musiques, GIF et playlists. Un seul logiciel.

**Téléchargez, convertissez et organisez vos médias préférés depuis une interface Windows moderne, rapide et entièrement en français.**

Propulsé par **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**, **[FFmpeg](https://ffmpeg.org/)** et **[pywebview](https://pywebview.flowrl.com/)**.

<p>
  <img src="https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?style=flat-square&logo=windows11&logoColor=white" alt="Windows 10 et 11">
  <img src="https://img.shields.io/badge/Langue-Fran%C3%A7ais-2563EB?style=flat-square" alt="Français">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.12">
  <a href="https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml"><img src="https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml/badge.svg" alt="Compilation Windows"></a>
</p>

---

### 📥 TÉLÉCHARGER ALL-DOWNLOAD

<a href="https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Portable-Windows.zip"><img src="https://img.shields.io/badge/T%C3%89L%C3%89CHARGER-WINDOWS%20PORTABLE-2563EB?style=for-the-badge&logo=windows11&logoColor=white" alt="Télécharger Windows Portable"></a>
&nbsp;
<a href="https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Classique-Windows.zip"><img src="https://img.shields.io/badge/T%C3%89L%C3%89CHARGER-WINDOWS%20CLASSIQUE-374151?style=for-the-badge&logo=windows11&logoColor=white" alt="Télécharger Windows Classique"></a>

**Deux téléchargements directs en ZIP, toujours à jour.**

<sub>Les liens restent identiques et pointent vers la dernière <a href="https://github.com/anderson76389/All-Download/releases/latest">version publiée</a>.</sub>

</div>

---

## ✨ Tout ce qu'il vous faut

| | Fonctionnalité | Ce que vous pouvez faire |
|:--:|---|---|
| 🎬 | **Vidéos haute qualité** | Télécharger en MP4 ou MKV, choisir la résolution (jusqu'à 4K si disponible). |
| 🎧 | **Audio & musique** | Extraire ou convertir en MP3, M4A et FLAC. |
| 🎞️ | **GIF** | Récupérer des GIF directs ou convertir des vidéos en GIF. |
| 📺 | **Playlists & chaînes** | Télécharger plusieurs éléments et sélectionner une plage précise. |
| 📋 | **File d'attente** | Ajouter plusieurs liens, suivre la progression, annuler et consulter les journaux. |
| 🎨 | **Interface personnalisable** | Thèmes clair, sombre et OLED, réglages et accès rapide aux dossiers. |
| 🛠️ | **Outils avancés** | Miniatures, métadonnées, normalisation audio, SponsorBlock, cookies et proxy. |

> Les formats, résolutions et sites pris en charge dépendent de la disponibilité des sources et des extracteurs yt-dlp. Aucune application ne peut garantir le téléchargement de tous les contenus.

---

## 💻 Deux versions Windows, le même All-Download

| 🧳 **PORTABLE** | 🖥️ **CLASSIQUE** |
|---|---|
| **Sans installation**, à emporter partout. | **Installateur Windows**, avec intégration au système. |
| ① Téléchargez le ZIP Portable.<br>② Extrayez-le où vous voulez.<br>③ Lancez `All_Media_Download.exe`. | ① Téléchargez le ZIP Classique.<br>② Extrayez-le et lancez `All-Download-Setup.exe`.<br>③ Ouvrez l'application depuis le menu Démarrer. |
| ✅ Exécutable autonome<br>✅ Aucun dossier `_internal`<br>✅ Médias, paramètres, outils et journaux dans le dossier Portable (accessible en écriture) | ✅ Installation sans droits administrateur<br>✅ Raccourci Bureau facultatif<br>✅ Médias, paramètres et outils dans le dossier installé<br>✅ Désinstallation sans suppression des médias personnels |

**Important :** la version Classique actuelle utilise le même moteur autonome que la Portable. Elle **ne repose plus sur l'ancien dossier `_internal`** qui pouvait provoquer l'erreur `Python.Runtime.dll` sur certains PC.

**Configuration requise :** Windows 10/11 **x64 (64 bits)** et WebView2. La compilation utilise Python et un EXE x64 ; **x86 (32 bits) n'est pas pris en charge**. Une connexion Internet est nécessaire pour récupérer les contenus et, au besoin, yt-dlp et FFmpeg au premier lancement.

---

## 🚀 Télécharger en quelques clics

1. **🔗 Collez** l'URL d'une vidéo, d'un morceau, d'un GIF ou d'une playlist.
2. **⚙️ Choisissez** le mode **Vidéo**, **Audio** ou **GIF**, puis la qualité.
3. **⬇️ Lancez** le téléchargement individuel ou celui de la file d'attente.
4. **📂 Retrouvez** votre média dans le dossier correspondant.

---

## 📁 Un rangement automatique et organisé

```text
📁 All-Download-Portable/ (ou dossier d'installation Classique/)
├── All_Media_Download.exe
├── logo.ico et logo.jpg
├── 🎵 AUDIOS/        Musiques et fichiers audio individuels
├── 🎬 VIDÉOS/        Vidéos YouTube individuelles
├── 🎞️ GIFS/          GIF téléchargés et GIF convertis
├── 📺 CHAÎNES/       Sous-dossiers par chaîne YouTube
├── 📑 PLAYLIST/      Sous-dossiers par playlist YouTube
├── 📦 AUTRES/        Autres médias et plateformes
└── 📁 Donnees/       Données personnelles des deux éditions
    ├── config.json   Réglages du logiciel
    ├── bin/          yt-dlp, FFmpeg et ffprobe
    ├── startup_log.txt
    └── crash_log.txt
```

**Même rangement dans les deux éditions :** les six catégories sont créées à côté de l'EXE, même si elles n'existaient pas à l'extraction. Les réglages, outils et journaux restent dans `Donnees/` de chaque édition. **Exception technique :** les profils de cache WebView2 restent dans `%LOCALAPPDATA%\\AllMediaDownload` (séparés entre Portable et Classique) pour la stabilité au démarrage, et PyInstaller peut employer des fichiers temporaires système. Aucun de ces caches ne contient vos médias.

Les **six catégories sont créées automatiquement**, sans effacer vos médias existants. Le ZIP **Portable** les contient comme véritables dossiers vides, sans `.gitkeep`. Le ZIP **Classique** n'ajoute aucun dossier parasite lors de l'extraction : l'installateur crée les catégories directement dans son dossier d'installation. Sur GitHub, les dossiers vides n'apparaissent pas : c'est le fonctionnement normal de Git.

L'ancien dossier `AUDIO/` est migré vers `AUDIOS/` lorsque c'est possible, sans écraser les fichiers homonymes.

| Édition | Emplacement initial des téléchargements |
|---|---|
| **Portable x64** | Dans le dossier contenant l'EXE, sans dossier `All-Download-Medias` supplémentaire (si l'emplacement est modifiable) |
| **Classique x64** | Directement à côté de l'EXE installé (par défaut `%LOCALAPPDATA%\Programs\All-Download`) |

---

### 📂 Choisir librement son dossier

Dans **Paramètres → Téléchargement → Dossier des téléchargements**, cliquez sur **Parcourir…** pour sélectionner un dossier Windows, y compris sur un autre disque (D:, E:, etc.), ou collez son chemin complet. Cliquez sur **Enregistrer** pour appliquer le changement. **Par défaut** rétablit l'emplacement automatique correspondant à l'édition utilisée.

Les six catégories sont créées dans le dossier choisi. L'application vérifie l'accès en écriture et conserve l'ancien emplacement en cas d'erreur. **Les fichiers existants ne sont pas déplacés ni supprimés.**

**Chaque édition possède sa propre configuration** dans `Donnees/config.json` à côté de son EXE. Au premier démarrage, les anciens réglages de `%LOCALAPPDATA%\\AllMediaDownload` sont copiés s'ils existent, sans effacer leur origine. Un dossier personnalisé expressément choisi reste prioritaire. Si le dossier du programme est exceptionnellement protégé contre l'écriture, le logiciel utilise une destination de repli modifiable.

**Dans les deux éditions**, les anciens emplacements automatiques `Téléchargements/MediaDownloader` et `Téléchargements/All-Download-Medias` ne sont plus utilisés pour les nouveaux téléchargements : ils vont dans les catégories du dossier contenant l'EXE. **Les anciens fichiers ne sont ni déplacés ni effacés automatiquement** ; vérifiez leur contenu avant de supprimer un ancien dossier. Vous pouvez toujours choisir une destination personnalisée dans les paramètres.

**Sécurité des données Classique :** lors d'une mise à jour ou d'une désinstallation, l'installateur est configuré pour ne jamais supprimer les six catégories personnelles ni `Donnees/`. La désinstallation enlève l'application, mais ces dossiers personnels peuvent rester dans l'ancien emplacement ; c'est volontaire pour éviter toute perte. Ne les supprimez manuellement qu'après vérification.

---

## 🔒 Versions officielles et mises à jour

Les deux boutons en haut de cette page renvoient vers les fichiers de la **dernière [GitHub Release](https://github.com/anderson76389/All-Download/releases/latest)** :

- `All-Download-Portable-Windows.zip` : application autonome et prête à ouvrir.
- `All-Download-Classique-Windows.zip` : installateur Windows `All-Download-Setup.exe`.

Chaque archive comprend les **logos** et une copie des **sources GitHub** dans `Code-source/`. Les six dossiers vides sont inclus uniquement dans le ZIP Portable ; ils sont créés par l'installateur pour la version Classique.

Les versions sont construites automatiquement et soumises à des tests Python, des tests d'interface et des vérifications du démarrage sur Windows. **Cela ne remplace pas un essai réel de chaque site ou de chaque format.**

<details>
<summary><strong>🧑‍💻 Développeurs — Code source et compilation</strong></summary>

Le projet comprend notamment `yt_app.py`, `All_Media_Download-Portable.spec`, `installer/All-Download.iss`, `tests/` et les workflows GitHub Actions.

**Lancer depuis Python 3.12 sur Windows :**

```powershell
python -m pip install pywebview==6.2.1
python yt_app.py
```

**Compiler l'EXE autonome :**

```powershell
python -m pip install pyinstaller==6.22.3 pywebview==6.2.1 pythonnet==3.2.1
python scripts/patch_webview_startup.py
python -m PyInstaller --clean --noconfirm All_Media_Download-Portable.spec
```

Le fichier `dist/All_Media_Download.exe` déjà présent dans le dépôt est une **ancienne compilation**, à ne pas confondre avec les versions proposées dans les Releases.

</details>

<details>
<summary><strong>🩺 Dépannage, SmartScreen et sécurité</strong></summary>

- **Premier démarrage Windows / WebView2 :** la compilation officielle applique une correction ciblée au cycle de vie WinForms : WebView2 commence son initialisation après l'affichage de la fenêtre. Un test Windows exige un premier chargement HTML réactif **sans relance automatique**, pour chaque édition. Le diagnostic de lancements répétés demeure disponible et peut toujours relever un blocage intermittent sur certaines configurations.
- **Crash CLR / pythonnet au démarrage :** All-Download tente automatiquement **une seule relance propre** lors de l'erreur connue `Python.Runtime.Loader.Initialize`. Si celle-ci échoue aussi, la boîte d'erreur et le journal restent disponibles.
- **Problème de démarrage :** ouvrez `Donnees/crash_log.txt` ou `Donnees/startup_log.txt` dans le dossier de l'application et partagez la dernière erreur dans une [issue](https://github.com/anderson76389/All-Download/issues), après avoir masqué les données personnelles. Si le dossier de l'application n'est pas modifiable, les journaux peuvent se trouver dans `%LOCALAPPDATA%\AllMediaDownload`.
- **Média non disponible :** contrôlez l'URL, les autorisations, les cookies éventuels et la compatibilité yt-dlp.
- **Conversion impossible :** vérifiez FFmpeg, l'espace disque et le format source.
- **Avertissement SmartScreen :** les exécutables ne disposent pas encore d'une signature d'éditeur reconnue. Un avertissement de réputation ne constitue pas à lui seul une détection de malware. Ne désactivez pas vos protections et ne contournez pas une détection de menace.

Téléchargez uniquement les contenus pour lesquels vous disposez des droits nécessaires. All-Download ne contourne pas les protections DRM.

</details>

---

<div align="center">

**⚡ ALL-DOWNLOAD — Téléchargez. Convertissez. Organisez.**

Créé et maintenu par **[anderson76389](https://github.com/anderson76389)**

[📥 Dernière version](https://github.com/anderson76389/All-Download/releases/latest) · [📖 Code source](./yt_app.py) · [🐛 Signaler un problème](https://github.com/anderson76389/All-Download/issues)

</div>
