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

**Configuration requise :** Windows 10/11 **x64 (64 bits)** et WebView2. La compilation utilise Python et un EXE x64 ; **x86 (32 bits) n'est pas pris en charge**. Une connexion Internet est nécessaire pour récupérer les contenus et, au besoin, yt-dlp et FFmpeg au premier lancement. **Pour YouTube**, All-Download installe automatiquement le moteur JavaScript Deno x64 à la première analyse d'un lien YouTube, dans `Donnees/bin/`, sans l'ajouter au PATH de Windows.

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
    ├── bin/          yt-dlp, FFmpeg, ffprobe et Deno (pour YouTube)
    ├── cache/
    │   ├── yt-dlp/   Cache du moteur de téléchargement
    │   └── deno/     Cache du moteur JavaScript YouTube
    ├── startup_log.txt
    └── crash_log.txt
```

**Même rangement dans les deux éditions :** les six catégories sont créées à côté de l'EXE, même si elles n'existaient pas à l'extraction. Les réglages, outils, journaux **et les caches yt-dlp/Deno** restent dans `Donnees/` de chaque édition. Les commandes du moteur ignorent les fichiers de configuration yt-dlp globaux, afin de ne pas dépendre de chemins ou réglages extérieurs. **Exception technique :** les profils de cache WebView2 restent dans `%LOCALAPPDATA%\\AllMediaDownload` (séparés entre Portable et Classique) pour la stabilité au démarrage, et PyInstaller peut employer des fichiers temporaires système. Aucun de ces caches ne contient vos médias.

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
- **YouTube (vidéos, Shorts, chaînes, playlists, musique) :** le moteur JavaScript **Deno 2.3+** est téléchargé automatiquement depuis sa Release officielle à la première analyse d'un lien YouTube et utilisé via `--js-runtimes deno:<chemin local>`. L'EXE officiel `yt-dlp.exe` intègre déjà `yt-dlp-ejs`. L'installation vérifie la structure PE x64 et l'exécution de `deno --version`, puis ne remplace l'exécutable qu'après validation. Si Deno ne peut pas être récupéré, yt-dlp conserve son comportement habituel, mais certains formats YouTube peuvent manquer. En cas de difficulté, vérifiez l'accès à GitHub et utilisez le bouton **Vérifier et mettre à jour yt-dlp** dans **Paramètres → Réseau**. Aucun moteur JavaScript n'est ajouté aux commandes Twitch et autres plateformes.
- **VOD Twitch impossible à télécharger :** dans **Paramètres → Réseau**, utilisez **Vérifier et mettre à jour yt-dlp**. Essayez ensuite une VOD publique accessible dans votre navigateur. Pour une VOD réservée, configurez les cookies dans **Authentification** avec un navigateur autorisé à lire la vidéo. Si le téléchargement échoue, ouvrez **Journaux** : la dernière erreur de yt-dlp reste visible, même lorsque la file s'arrête. Une erreur 403 peut venir d'un jeton de lecture refusé, d'une restriction Twitch ou d'un extracteur yt-dlp défaillant ; elle ne signifie pas automatiquement que les cookies manquent. Les autres applications peuvent utiliser d'autres mécanismes d'accès à Twitch. **Les corrections ne garantissent pas l'accès à une VOD particulière sans test réel de son URL.**
- **VOD Twitch réservée aux abonnés, extension Chrome :** si yt-dlp renvoie `subscriber-only content`, All-Download identifie précisément l'erreur et propose **Ouvrir dans Chrome** et **Importer une vidéo**. Cette fonction ne contourne pas les droits d'accès de Twitch et ne télécharge pas directement la VOD protégée : elle aide à récupérer un fichier **déjà téléchargé et légalement accessible** avec une autre application. Le fichier est copié dans `AUTRES/` ; l'original et les noms existants ne sont jamais écrasés. Les liens YouTube et les autres sites conservent leur fonctionnement habituel.
- **Archives publiques Twitch (nouveau, facultatif) :** lorsque yt-dlp refuse l'accès à une VOD, All-Download recherche automatiquement auprès de l'**API officielle d'Internet Archive** un élément qui cite **exactement** l'identifiant numérique de la VOD. Une copie n'est proposée que si l'archive indique explicitement une licence Creative Commons ou domaine public et contient un vrai fichier vidéo téléchargeable. Le fichier est téléchargé en flux dans `AUTRES/`, avec contrôle de taille, espace libre, annulation et protection contre l'écrasement. Avant de télécharger, confirmez disposer des droits nécessaires sur cette copie. Si aucune archive publique licite ne correspond, l'application **n'invente pas de résultat** : le recours à Chrome et l'import manuel restent disponibles. **L'Internet Archive et la base de l'extension Chrome sont deux services distincts** ; une VOD trouvée par l'extension n'est pas nécessairement trouvable sur Internet Archive. Aucun accès aux flux Twitch réservés aux abonnés n'est contourné.
- **Deux moteurs Twitch : yt-dlp + Streamlink** : chaque VOD Twitch possède maintenant un bouton **Streamlink Twitch** distinct du téléchargement yt-dlp. Le bouton existe également sur les fiches où yt-dlp échoue. Streamlink 8.6.3 est embarqué dans l'EXE Portable et utilise son propre extracteur Twitch, sans installation Python ou Node sur le PC. Les flux accessibles sont enregistrés dans `AUTRES/` (TS et, si FFmpeg est disponible, remux MP4 sans réencodage) ; pas d'écrasement de fichier, annulation et pause prises en charge. **Streamlink ne contourne pas les abonnements : une VOD réservée aux abonnés peut rester inaccessible aux deux moteurs.** Ce moteur ne remplace ni le système d'archives publiques, ni l'extension Chrome et son service privé. Seules les URL de VOD Twitch sont acceptées.
- **Pont avec l'extension Chrome (Andre Bradshaw)** : sur une VOD Twitch, utiliser **Chrome + import auto** pour ouvrir Chrome et commencer à surveiller le dossier de téléchargements de Chrome. **Dans Chrome, il faut encore cliquer sur Télécharger dans votre extension** ; celle-ci reste responsable de trouver les sources qu'elle autorise. Après la fin du téléchargement Chrome, All-Download détecte les nouveaux fichiers MP4, MKV, M4V, TS, WEBM ou MOV, puis les copie automatiquement dans `AUTRES/` sans écraser ni déplacer l'original. Les fichiers `.crdownload` ne sont jamais importés. Cliquez sur **Arrêter import** pour arrêter la surveillance. Si votre Chrome utilise un dossier personnalisé, cliquez sur **Dossier Chrome** puis choisissez le même dossier dans l'explorateur. Pendant une surveillance, toute nouvelle vidéo téléchargée dans ce dossier peut être importée : utilisez un dossier Chrome dédié si vous souhaitez éviter l'importation d'autres vidéos. **Ce pont n'utilise pas le service privé de l'extension, ne copie pas vos identifiants et ne contourne pas les restrictions d'abonnement.**
- **Extension Twitch dans All-Download (mode natif WebView2, expérimental)** : Microsoft WebView2 accepte les extensions Chromium décompressées. Une VOD Twitch affiche maintenant **Extension intégrée**. Au premier clic, All-Download recherche l'extension **Twitch VOD Downloader** d'Andre Bradshaw dans les profils Chrome locaux (identifiant `gaabmdjigfcnkgeommfpnoinpdmpfhaj`) et **copie seulement ses fichiers d'extension** dans `Donnees/Extensions/TwitchVODDownloader` : pas de cookies, de mots de passe, ni de données Chrome copiés, et aucune copie de l'extension n'est incluse dans l'EXE distribué. **Fermez puis relancez All-Download** : un profil WebView2 distinct et persistant est créé, l'extension est chargée et un second clic ouvre une fenêtre Twitch intégrée à All-Download. **Le test Windows valide l'installation réelle d'une extension de démonstration dans WebView2, pas la compatibilité de toutes les fonctionnalités de la version propriétaire 3.26.** Notamment, une API Chrome ou la connexion à un service tiers peut ne pas fonctionner dans WebView2 ; l'accès à une VOD réservée aux abonnés n'est pas garanti. **Paramètres → Réseau → Désactiver l’extension intégrée** permet de revenir au mode normal après redémarrage. Sans activation, le fonctionnement habituel et privé de yt-dlp/Streamlink n'est pas modifié. Le profil technique WebView2 persiste sous `LocalAppData` pour la stabilité Windows ; les fichiers d'extension restent dans `Donnees`.
- **Mises à jour du moteur :** elles sont volontaires et séparées de la mise à jour d'All-Download. Le binaire officiel est téléchargé dans un fichier temporaire et exécuté avec `--version` avant de remplacer l'ancien. En cas d'échec, l'ancien est conservé. Aucune mise à jour n'est lancée pendant un téléchargement en cours.
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
