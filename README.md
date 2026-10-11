<div align="center">

<img src="./logo.jpg" alt="All-Download — logo" width="160" />

# ALL-DOWNLOAD

**⚡ Tous vos médias, un seul endroit. La puissance du téléchargement, sans complexité.**

**Vidéos haute définition, musique, GIF, playlists et chaînes :** collez votre lien, choisissez la qualité et récupérez les contenus compatibles depuis une interface en français. Propulsé par **yt-dlp** et **FFmpeg**, pour **Windows**.

[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/anderson76389/All-Download)
[![Python](https://img.shields.io/badge/Python-Application-3776AB?style=for-the-badge&logo=python&logoColor=white)](./yt_app.py)
[![yt--dlp](https://img.shields.io/badge/Moteur-yt--dlp-FF5A5F?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp)
[![FFmpeg](https://img.shields.io/badge/Média-FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)

**[⬇ Version Windows recompilée](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml)** · **[📖 Installation](#-installation)** · **[✨ Fonctionnalités](#-fonctionnalités)**

</div>

---

## 🎯 Présentation

**All-Download** rassemble la récupération et le traitement des contenus multimédias dans une application de bureau. Collez une URL, choisissez le type de média et la qualité souhaitée, puis lancez le téléchargement.

L'application s'appuie sur les extracteurs de [yt-dlp](https://github.com/yt-dlp/yt-dlp), avec une gestion supplémentaire de certains liens, notamment **Pinterest** et **X / Twitter**. Elle peut traiter des vidéos individuelles, des playlists et des chaînes lorsque la plateforme et l'extracteur le permettent.

> **À savoir :** « multimédia » ne signifie pas « tous les sites sans exception ». La prise en charge dépend de la source, de ses restrictions, des extracteurs disponibles et des droits d'accès au contenu.

## ✨ Fonctionnalités

| Fonction | Détails |
| --- | --- |
| 🎬 **Vidéos** | Qualité automatique ou résolution sélectionnée, jusqu'à la 4K et au-delà lorsque la source le propose |
| 🎵 **Audio** | Extraction et conversion en **FLAC**, **M4A** ou **MP3** |
| 🎞️ **GIF** | Conversion de vidéos en GIF |
| 📚 **Playlists et chaînes** | Téléchargement d'ensembles et sélection d'une plage d'éléments |
| 🧩 **File d'attente** | Ajout de plusieurs liens, traitement en série et suivi de progression |
| 🖼️ **Miniatures et métadonnées** | Intégration ou sauvegarde des vignettes, ajout des informations disponibles |
| ✂️ **SponsorBlock** | Suppression ou marquage des segments pris en charge, notamment sur YouTube |
| 🔐 **Cookies** | Authentification par fichier cookies ou récupération des cookies du navigateur |
| 🌐 **Réseau avancé** | Proxy, choix d'agent utilisateur et arguments d'extracteur personnalisés |
| 🎨 **Interface** | Thèmes clair, sombre et sombre OLED, paramètres et journaux d'exécution |

### 🎚️ Qualité et formats

- **Vidéo :** conteneurs MP4 et MKV, sélection de résolution selon les formats proposés par la source.
- **Audio :** FLAC, M4A et MP3 ; prise en charge de la normalisation audio dans les paramètres.
- **Post-traitement :** remux vidéo, intégration des miniatures et métadonnées, options FFmpeg.
- **GIF :** conversion à partir d'un flux vidéo compatible.

> **Précision audio :** convertir une source avec pertes en FLAC ne restaure pas les informations perdues. La qualité finale dépend toujours du média d'origine.

## ⬇️ Installation

### Option 1 — Application Windows (simple)

1. Ouvrez les **[compilations Windows](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml)** et choisissez la dernière exécution **réussie** (coche verte).
2. Dans la section **Artifacts**, téléchargez `All-Download-Windows`, puis extrayez l'archive ZIP (une connexion GitHub peut être nécessaire).
3. Lancez `All_Media_Download.exe` sur Windows.
4. Au premier lancement, laissez l'application récupérer **yt-dlp** et **FFmpeg** si ces outils ne sont pas déjà présents dans son dossier de données.
5. Collez un lien et commencez à télécharger.

> Le fichier [dist/All_Media_Download.exe](./dist/All_Media_Download.exe) présent dans le dépôt est une ancienne compilation : il ne reçoit pas automatiquement les corrections du code source.

**Prérequis :** Windows, accès à Internet et espace disque adapté aux médias téléchargés. L'interface utilise **WebView2** via pywebview.

### Option 2 — Exécuter depuis les sources

Installez Python et le paquet requis, puis lancez l'application depuis la racine du dépôt :

```powershell
python -m pip install pywebview
python yt_app.py
```

Au lancement, l'application tente de télécharger les exécutables **yt-dlp** et **FFmpeg** dans le répertoire de données local s'ils sont absents.

### Compiler l'exécutable

Le dépôt contient également la configuration **PyInstaller** utilisée pour l'application :

```powershell
python -m pip install pywebview pyinstaller
python -m PyInstaller All_Media_Download.spec
```

Le résultat est généré dans `dist/`. La compilation et le fonctionnement effectif dépendent de l'environnement Windows et des dépendances installées.

## 🚀 Utilisation

1. **Collez une URL** de vidéo, playlist, chaîne ou média pris en charge dans le champ principal.
2. **Ajoutez le média** à la file d'attente afin de récupérer ses informations et les formats disponibles.
3. **Choisissez** Vidéo, Audio ou GIF ainsi que la qualité voulue.
4. Pour une playlist ou une chaîne, **définissez la plage** d'éléments à récupérer si nécessaire.
5. Cliquez sur **Télécharger**, puis suivez la progression ou consultez les journaux.

Le dossier de destination par défaut est :

```text
%USERPROFILE%\Downloads\MediaDownloader
```

Les téléchargements YouTube sont organisés suivant leur type dans des sous-dossiers tels que `VIDÉOS/`, `AUDIO/`, `PLAYLIST/` et `CHAÎNES/`. Les autres plateformes utilisent notamment `AUTRES/`. Le répertoire peut être adapté dans l'application.

## ⚙️ Réglages avancés

<details>
<summary><strong>📼 Vidéo et audio</strong></summary>

- Préférence de conteneur vidéo : MP4 ou MKV.
- Préférence de format audio : FLAC, M4A ou MP3.
- Conservation des flux d'origine et post-traitements disponibles.
- Miniatures intégrées ou conservées séparément ; métadonnées lorsqu'elles sont disponibles.

</details>

<details>
<summary><strong>🔐 Authentification et réseau</strong></summary>

- Import de `cookies.txt` ou extraction des cookies d'un navigateur pris en charge.
- Proxy et paramètres d'agent utilisateur.
- Arguments `yt-dlp` supplémentaires pour des extracteurs spécifiques.

Les cookies peuvent donner accès à une session personnelle : **ne publiez jamais vos fichiers de cookies**.

</details>

<details>
<summary><strong>✂️ SponsorBlock</strong></summary>

- Activation ou désactivation.
- Suppression de segments ou ajout de marqueurs de chapitres selon les options prises en charge.
- API SponsorBlock configurable et découpe précise via FFmpeg.

</details>

## 📂 Structure du projet

```text
All-Download/
├── yt_app.py                   # Code principal et interface
├── All_Media_Download.spec     # Configuration PyInstaller
├── logo.jpg                    # Visuel de l'application
├── logo.ico                    # Icône Windows
├── .gitignore                  # Fichiers locaux et temporaires à exclure
├── AUDIO/.gitkeep              # Dossier réservé aux fichiers audio
├── AUTRES/.gitkeep             # Médias d'autres plateformes
├── CHAÎNES/.gitkeep            # Vidéos regroupées par chaîne
├── PLAYLIST/.gitkeep           # Téléchargements des playlists
├── VIDÉOS/.gitkeep             # Vidéos individuelles
├── dist/
│   └── All_Media_Download.exe  # Exécutable historique conservé
└── .github/workflows/
    └── build-windows.yml       # Compilation Windows automatique
```

Les fichiers `.gitkeep` permettent à GitHub de conserver ces dossiers même sans aucun média. **Sur Windows, l'application recrée automatiquement les cinq catégories dans son dossier de téléchargement** (par défaut `%USERPROFILE%\\Downloads\\MediaDownloader`) sans effacer les contenus existants.

Les fichiers temporaires de compilation `build/` sont exclus de Git : ils seront recréés localement par PyInstaller si nécessaire. Les versions Windows recompilées sont disponibles dans les **[GitHub Actions](https://github.com/anderson76389/All-Download/actions/workflows/build-windows.yml)**.

## 🛠️ En cas de problème

| Situation | Vérification |
| --- | --- |
| L'URL ne fonctionne pas | Vérifier que la source est accessible et que son extracteur est pris en charge par yt-dlp |
| Accès refusé, 403 ou média privé | Vérifier les droits d'accès et, si nécessaire, les cookies de votre propre session |
| Conversion audio ou vidéo impossible | Vérifier la disponibilité de FFmpeg et l'espace disque |
| Une qualité n'est pas proposée | La résolution dépend des flux réellement fournis par la plateforme |
| Le téléchargement échoue | Consulter l'onglet **Journaux** pour identifier la cause |

Les services en ligne évoluent : certains extracteurs peuvent cesser de fonctionner temporairement après une modification de plateforme.

## 🧱 Technologies

- **[Python](https://www.python.org/)** — moteur de l'application.
- **[pywebview](https://pywebview.flowrl.com/)** — interface de bureau HTML/CSS/JavaScript.
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — extraction et téléchargement des médias.
- **[FFmpeg](https://ffmpeg.org/)** — assemblage, conversion et post-traitement.
- **[PyInstaller](https://pyinstaller.org/)** — génération de l'exécutable Windows.
- **[SponsorBlock](https://sponsor.ajay.app/)** — informations sur les segments communautaires compatibles.

## ⚖️ Utilisation responsable

All-Download est un outil de téléchargement et de traitement de médias. Utilisez-le uniquement pour des contenus que vous êtes autorisé à récupérer, dans le respect des droits d'auteur, des conditions des plateformes et des réglementations applicables. Le logiciel ne garantit ni l'accès aux contenus protégés ni le contournement des DRM.

---

<div align="center">

### ALL-DOWNLOAD

**Un lien. Plusieurs formats. Tous vos médias au même endroit.**

Développé et maintenu par **[anderson76389](https://github.com/anderson76389)**.

[↑ Revenir en haut](#all-download)

</div>
