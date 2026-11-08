<div align="center">

<img src="./logo.jpg" alt="All-Download" width="160">

# ⚡ ALL-DOWNLOAD

### Toutes vos vidéos, musiques, GIF et playlists. Un seul logiciel.

**Téléchargez, convertissez et organisez vos médias préférés depuis une interface Windows moderne, rapide et entièrement en français.**

Propulsé par **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**, **[FFmpeg](https://ffmpeg.org/)** et **[pywebview](https://pywebview.flowrl.com/)**.

<p>
  <img src="https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?style=flat-square&logo=windows11&logoColor=white" alt="Windows 10 et 11">
  <img src="https://img.shields.io/badge/Android-7%2B%20(b%C3%AAta)-3DDC84?style=flat-square&logo=android&logoColor=white" alt="Android 7 ou supérieur (bêta)">
  <img src="https://img.shields.io/badge/Langue-Fran%C3%A7ais-2563EB?style=flat-square" alt="Français">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.12">
  <a href="https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml"><img src="https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml/badge.svg" alt="Compilation Windows"></a>
</p>

---

### 📥 TÉLÉCHARGER ALL-DOWNLOAD

<a href="https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Portable-Windows.zip"><img src="https://img.shields.io/badge/T%C3%89L%C3%89CHARGER-WINDOWS%20PORTABLE-2563EB?style=for-the-badge&logo=windows11&logoColor=white" alt="Télécharger Windows Portable"></a>
&nbsp;
<a href="https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Classique-Windows.zip"><img src="https://img.shields.io/badge/T%C3%89L%C3%89CHARGER-WINDOWS%20CLASSIQUE-374151?style=for-the-badge&logo=windows11&logoColor=white" alt="Télécharger Windows Classique"></a>

<br><br>

<a href="https://github.com/anderson76389/All-Download/releases/download/android-v0.3.0-beta/All-Download-Android-0.3.0-beta.apk"><img src="https://img.shields.io/badge/T%C3%89L%C3%89CHARGER-ANDROID%20APK%20B%C3%8ATA-16A34A?style=for-the-badge&logo=android&logoColor=white" alt="Télécharger Android APK bêta"></a>

**Windows :** deux archives ZIP à jour. **Android :** un APK bêta distinct (0.3.0).

<sub>Les boutons Windows pointent vers la <a href="https://github.com/anderson76389/All-Download/releases/latest">dernière version stable Windows</a>. L'APK Android est publié séparément dans sa <a href="https://github.com/anderson76389/All-Download/releases/tag/android-v0.3.0-beta">Release bêta</a>.</sub>

</div>

---

## 📱 All-Download Android — bêta 0.3.0

**[⬇️ Télécharger directement l'APK Android](https://github.com/anderson76389/All-Download/releases/download/android-v0.3.0-beta/All-Download-Android-0.3.0-beta.apk)** · **[Page de la Release et empreinte SHA-256](https://github.com/anderson76389/All-Download/releases/tag/android-v0.3.0-beta)**

L'APK Android est **indépendant des deux versions Windows**, fonctionne à partir d'**Android 7.0** et ne nécessite ni PC, ni Termux, ni serveur personnel. Il comprend yt-dlp et FFmpeg, ainsi que les modes vidéo, audio MP3/M4A/FLAC, GIF, playlist et chaîne. Les médias sont enregistrés dans `Téléchargements/All-Download/`, avec des sous-dossiers par catégorie.

**Interface Android 0.3.0 :** le logo et l'icône All-Download, écran de lancement, palette violette Windows et thèmes **Sombre, Clair et OLED**. Quatre rubriques natives **Accueil, File d'attente, Dossiers et Paramètres** ; file persistante avec progression, pause, reprise (selon la prise en charge du serveur), nouvelle tentative et suppression des tâches terminées. Explorateur des sept catégories et **navigation latérale sur tablette et téléphone pliable ouvert**.

**Mises à jour intégrées :** à partir de cette bêta, l'application recherche les nouvelles **Releases Android sur GitHub** à l'ouverture. Lorsqu'une version Android plus récente est disponible, un **popup animé** affiche le logo, les nouveautés, « Télécharger la mise à jour » et « Plus tard ». La recherche manuelle et l'option de désactivation sont disponibles dans les paramètres ; **les Releases Windows ne déclenchent pas ce popup**. Le téléchargement ouvre le lien officiel de l'APK, puis l'installation reste sous le contrôle d'Android.

**Réglages adaptés depuis Windows :** format MP4/MKV et remux optionnel, qualité MP3, métadonnées, miniatures, sous-titres, SponsorBlock, proxy, User-Agent, tentatives/délais réseau, notifications et réduction des animations. Les options propres à Windows, impossibles à utiliser telles quelles sur Android, ne sont pas présentées comme des fonctions disponibles.

Les tests Android 14 ont réussi sur des liens vidéo publics **Instagram Reels, X/Twitter, Pinterest, TikTok, Facebook Reels, Reddit HLS direct, Bluesky et Dailymotion**, ainsi que sur les formats MP4, WebM, HLS et les clips Twitch. Les tests de base passent également sur Android 9. **Toutes les vidéos et tous les réseaux sociaux ne sont pas garantis** : une publication Reddit classique peut exiger une connexion, certaines anciennes vidéos Facebook ne sont pas reconnues, et YouTube ou les VOD Twitch protégées peuvent être bloqués.

L'application peut actualiser yt-dlp et permet d'importer **facultativement** un fichier `cookies.txt` provenant de votre propre session autorisée, stocké dans l'espace privé de l'application et supprimable dans l'interface. **Attention : la bêta peut encore être signée avec une clé de débogage éphémère si aucune clé de signature privée persistante n'a été configurée sur GitHub.** Le popup signale les nouvelles versions, mais Android peut refuser une installation par-dessus une ancienne bêta dont la signature diffère. Une désinstallation sera alors nécessaire et supprimera les données privées de l'application ; évitez d'y importer des sessions sensibles. Les médias exportés dans le dossier Téléchargements ne sont pas inclus dans ces données privées.

Pour les limitations, les instructions et les détails de la compilation : **[README Android](https://github.com/anderson76389/All-Download/blob/feature/android-app/android/README.md)**.

---

## ✨ Tout ce qu'il vous faut sur Windows

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

## 📺 VOD Twitch — moteur spécialisé

Pour les liens de VOD du type `https://www.twitch.tv/videos/1234567890`, **All-Download utilise [TwitchDownloaderCLI](https://github.com/lay295/TwitchDownloader)** en mode **Vidéo**, tout en conservant exactement la même interface et la même file d'attente (progression, pause, reprise et annulation).

- Le CLI **Windows x64 autonome** est téléchargé **au premier besoin** depuis la dernière release officielle, dans `Donnees/bin/TwitchDownloaderCLI.exe`. L'archive est contrôlée (taille, empreinte SHA-256 quand elle est fournie par GitHub, format PE x64) puis l'exécutable est installé atomiquement. Aucune interface TwitchDownloader séparée ou installation de .NET n'est requise.
- Les VOD Twitch en mode **Vidéo** sont rangées dans le dossier **TWITCH/**, à côté de VIDÉOS, AUDIOS et AUTRES. Les anciennes VOD stockées dans AUTRES ne sont **ni déplacées ni supprimées**. L’option **Rename** du CLI évite d’écraser un fichier du même nom.
- All-Download réutilise son propre FFmpeg. Le CLI télécharge les VOD vidéo en **MP4** ; il ne gère pas ici la sortie MKV, les options SponsorBlock, la conversion audio ni les réglages de proxy d'yt-dlp.
- Si yt-dlp ne peut pas obtenir les métadonnées Twitch, une carte **« VOD Twitch + identifiant »** est ajoutée avec un **menu de qualité**. **1080p natif est sélectionné par défaut ; si aucun flux 1080p natif n’est accessible, seul le 720p natif est essayé**. Aucun réencodage, conversion ni agrandissement : le moteur HLS conserve la vidéo et l’audio d’origine avec FFmpeg `-c copy` (remux MP4). La résolution du flux **source (« chunked »)** est contrôlée par FFprobe avant utilisation : une source de résolution inconnue ou inférieure n’est jamais renommée en « 1080p ». Si ni le 1080p ni le 720p ne sont disponibles, un message d’erreur est affiché au lieu de fabriquer une qualité artificielle. Le menu conserve les choix manuels et le mode **Auto** ; une résolution inférieure choisie explicitement est récupérée en natif, sans conversion. Cette règle ne concerne que les VOD Twitch : YouTube et les autres plateformes ne changent pas.
- Si TwitchDownloaderCLI **est absent, ne peut pas être téléchargé, ne démarre pas ou refuse une VOD**, All-Download essaie **automatiquement son secours HLS indépendant** : métadonnées publiques Twitch, recherche d’une playlist CDN accessible sans connexion, puis assemblage par le FFmpeg déjà installé. Cette méthode a été validée sur un extrait réel de la VOD `2919531847` (chaîne aminematue) sans cookie OAuth. Elle ne sollicite ni la base privée ni les serveurs de l’extension Chrome Twitch VOD Downloader. Elle peut toutefois échouer pour certaines VOD, dont les flux ne sont plus disponibles.
- Les vidéos HLS sont enregistrées en **MP4**, avec fichiers temporaires nettoyés, sans écrasement des médias existants, et avec progression, pause/reprise et annulation pilotées par la file d’attente actuelle.
- Les **clips Twitch**, les modes **Audio/GIF**, YouTube et tous les autres sites restent gérés par **yt-dlp**, sans changement de leur fonctionnement. L’accès HLS dépend des playlists encore accessibles sur le CDN Twitch ; il n’est pas garanti pour toutes les VOD, notamment celles supprimées ou expirées.
- Le CLI reste prioritaire quand il fonctionne et est téléchargé depuis GitHub au premier besoin. **Si GitHub ou TwitchDownloaderCLI est indisponible**, le secours HLS est utilisable directement, à condition que FFmpeg soit installé et que Twitch fournisse encore un flux accessible. Les flux protégés ou supprimés ne sont pas garantis.

**Crédits :** [TwitchDownloader de lay295](https://github.com/lay295/TwitchDownloader), distribué sous [licence MIT](https://github.com/lay295/TwitchDownloader/blob/master/LICENSE.txt). TwitchDownloader n'est pas affilié à Twitch.

---

### Compatibilité YouTube : Deno local et facultatif

Le moteur yt-dlp officiel embarque déjà les scripts EJS de YouTube. Lorsque l'application analyse ou télécharge une URL YouTube, elle peut installer **`deno.exe` Windows x64** dans `All-Download/Donnees/bin/`, en utilisant la release officielle `denoland/deno` (taille et empreinte SHA-256 GitHub vérifiées, version minimale validée). Deno est transmis explicitement à **yt-dlp pour YouTube uniquement** ; aucun compte, installation système ou PATH n'est nécessaire. Il ne modifie pas le téléchargement Twitch, Pinterest ou d'autres sites. **Si Deno ne peut pas être installé, yt-dlp conserve son comportement actuel** : certaines vidéos YouTube peuvent alors avoir moins de formats disponibles.

## 💻 Deux versions Windows, le même All-Download

| 🧳 **PORTABLE** | 🖥️ **CLASSIQUE** |
|---|---|
| **Sans installation**, à emporter partout. | **Installateur Windows**, avec intégration au système. |
| ① Téléchargez le ZIP Portable.<br>② Extrayez-le où vous voulez.<br>③ Lancez `All_Media_Download.exe`. | ① Téléchargez le ZIP Classique.<br>② Extrayez-le et lancez `All-Download-Setup.exe`.<br>③ Ouvrez l'application depuis le menu Démarrer. |
| ✅ Exécutable autonome<br>✅ Aucun dossier `_internal`<br>✅ Médias, paramètres, outils et journaux dans le dossier Portable (accessible en écriture) | ✅ Installation sans droits administrateur<br>✅ Raccourci Bureau facultatif<br>✅ Médias, paramètres et outils dans le dossier installé<br>✅ Désinstallation sans suppression des médias personnels |

**Important :** la version Classique actuelle utilise le même moteur autonome que la Portable. Elle **ne repose plus sur l'ancien dossier `_internal`** qui pouvait provoquer l'erreur `Python.Runtime.dll` sur certains PC.

**Configuration requise :** Windows 10/11 **x64 (64 bits)** et WebView2. La compilation utilise Python et un EXE x64 ; **x86 (32 bits) n'est pas pris en charge**. Une connexion Internet est nécessaire pour récupérer les contenus et, au besoin, yt-dlp et FFmpeg au premier lancement. Pour une compatibilité YouTube améliorée, **Deno x64** est récupéré automatiquement au premier téléchargement YouTube et conservé localement dans `Donnees/bin/deno.exe`, sans installation globale ni modification du PATH. En cas d'indisponibilité de Deno, yt-dlp continue avec les capacités disponibles.

---

## 🚀 Télécharger en quelques clics

1. **🔗 Collez** l'URL d'une vidéo, d'un morceau, d'un GIF ou d'une playlist.
2. **⚙️ Choisissez** le mode **Vidéo**, **Audio** ou **GIF**, puis la qualité.
3. **⬇️ Lancez** le téléchargement individuel ou celui de la file d'attente.
4. **📂 Retrouvez** votre média dans le dossier correspondant.

---

## 📁 Un rangement automatique et organisé

```text
📁 All-Download/ (dossier de l'EXE Portable ou dossier d'installation Classique)
├── All_Media_Download.exe
├── logo.ico et logo.jpg
├── 🎵 AUDIOS/        Musiques et fichiers audio individuels
├── 🎬 VIDÉOS/        Vidéos YouTube individuelles
├── 📺 TWITCH/        VOD Twitch (publiques et HLS accessibles)
├── 🎞️ GIFS/          GIF téléchargés et GIF convertis
├── 📺 CHAÎNES/       Sous-dossiers par chaîne YouTube
├── 📑 PLAYLIST/      Sous-dossiers par playlist YouTube
├── 📦 AUTRES/        Autres médias et plateformes
└── 📁 Donnees/       Données personnelles des deux éditions
    ├── config.json   Réglages du logiciel
    ├── bin/          yt-dlp, FFmpeg, ffprobe, Deno et TwitchDownloaderCLI (facultatifs)
    ├── cache/        Cache yt-dlp et fichiers Twitch temporaires
    ├── webview/         Profil WebView2 local (Portable)
    ├── webview-classique/  Profil WebView2 local (Classique)
    ├── startup_log.txt
    └── crash_log.txt
```

**Tout le stockage permanent est local dans les versions Windows :** les sept catégories sont créées à côté de l'EXE ; les réglages, outils, journaux, caches yt-dlp/Twitch et profils WebView2 sont dans `All-Download/Donnees/`. Les anciens profils techniques `%LOCALAPPDATA%\\AllMediaDownload` ne sont plus utilisés par les EXE à jour. **Exception Windows inévitable :** le Portable PyInstaller monofichier extrait temporairement ses composants dans le dossier système `%TEMP%` pendant l'exécution ; cela n'y sauvegarde jamais les médias ni les préférences.

Les **sept catégories sont créées automatiquement**, sans effacer vos médias existants. Le ZIP **Portable** contient un dossier racine unique `All-Download/` avec l'EXE, les sept catégories, les logos, le code source et les dossiers `Donnees/bin` vides (aucun fichier personnel). Vous pouvez l'extraire dans le dossier parent de votre choix : aucun dossier de catégorie n'est déposé à l'extérieur d'All-Download. Le ZIP **Classique** contient l'installateur, qui crée les catégories dans son dossier d'installation. Sur GitHub, les dossiers vides n'apparaissent pas : c'est normal.

L'ancien dossier `AUDIO/` est migré vers `AUDIOS/` lorsque c'est possible, sans écraser les fichiers homonymes.

| Édition | Emplacement initial des téléchargements |
|---|---|
| **Portable x64** | Dans `All-Download/`, directement à côté de l'EXE (dossier obligatoirement modifiable) |
| **Classique x64** | Directement à côté de l'EXE installé (par défaut `%LOCALAPPDATA%\Programs\All-Download`) |

---

### 📂 Un seul dossier All-Download, y compris après les mises à jour

Dans **Paramètres → Téléchargement**, vous pouvez conserver le dossier principal `All-Download/` (recommandé) ou choisir **un sous-dossier situé à l'intérieur d'All-Download**. Les sélections extérieures sont refusées, y compris si vous collez un ancien chemin. **Par défaut** rétablit le dossier de l'EXE. Les sept catégories restent à l'intérieur de l'arborescence All-Download.

**Chaque édition possède sa propre configuration** dans `Donnees/config.json` à côté de son EXE. Au premier démarrage, les anciens réglages d'AppData peuvent être copiés, mais **un ancien emplacement de téléchargement extérieur (y compris personnalisé) est automatiquement désactivé et remplacé par le dossier All-Download**, sans déplacer ni supprimer les anciens médias. Les préférences et les cookies enregistrés sont conservés.

**Aucune destination de secours extérieure :** si All-Download est protégé en écriture (par exemple `Program Files`, dossier ZIP non extrait ou partage non modifiable), l'application explique le problème plutôt que d'écrire silencieusement ailleurs. Déplacez la version Portable dans un dossier modifiable ou installez la version Classique dans un dossier modifiable.

**Mise à jour d'une ancienne Portable :** la nouvelle archive contient déjà `All-Download/`. Pour conserver les anciens téléchargements, remplacez uniquement l'EXE et les logos dans votre dossier actuel, ou transférez les dossiers `Donnees/` et les sept catégories vers le nouveau `All-Download/` après vérification. N'extrayez pas une seconde copie `All-Download/All-Download/` dans votre installation existante. **Aucun ancien média n'est supprimé ni déplacé automatiquement.**

**Sécurité des données Classique :** lors d'une mise à jour ou d'une désinstallation, l'installateur est configuré pour ne jamais supprimer les sept catégories personnelles ni `Donnees/`. La désinstallation enlève l'application, mais ces dossiers personnels peuvent rester dans l'ancien emplacement ; c'est volontaire pour éviter toute perte. Ne les supprimez manuellement qu'après vérification.

---

## 🔒 Versions officielles et mises à jour

Les deux boutons en haut de cette page renvoient vers les fichiers de la **dernière [GitHub Release](https://github.com/anderson76389/All-Download/releases/latest)** :

- `All-Download-Portable-Windows.zip` : application autonome et prête à ouvrir.
- `All-Download-Classique-Windows.zip` : installateur Windows `All-Download-Setup.exe`.

Chaque archive comprend les **logos** et une copie des **sources GitHub** dans `Code-source/`. Les sept dossiers vides sont inclus uniquement dans le ZIP Portable ; ils sont créés par l'installateur pour la version Classique.

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
- **Problème de démarrage :** ouvrez `Donnees/crash_log.txt` ou `Donnees/startup_log.txt` dans le dossier de l'application et partagez la dernière erreur dans une [issue](https://github.com/anderson76389/All-Download/issues), après avoir masqué les données personnelles. Si le dossier de l'application est protégé, déplacez la version Portable ou réinstallez la version Classique dans un dossier modifiable : les EXE ne stockent plus leurs données en dehors d'All-Download.
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
