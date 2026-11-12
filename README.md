<div align="center">

<img src="./logo.jpg" alt="Logo All-Download" width="132">

# ALL-DOWNLOAD

**Téléchargez vos vidéos, musiques, GIF et playlists dans une seule application.**

Windows 10/11 · Android 7+ · Linux x86_64 (bêta) · Interface en français · Thèmes clair, sombre et OLED

[![Windows](https://img.shields.io/badge/Windows-Portable%20%26%20Classique-2563EB?style=for-the-badge&logo=windows11&logoColor=white)](https://github.com/anderson76389/All-Download/releases/latest)
[![Android](https://img.shields.io/badge/Android-APK%20b%C3%AAta-16A34A?style=for-the-badge&logo=android&logoColor=white)](https://github.com/anderson76389/All-Download/releases/tag/android-v0.6.21-beta)
[![Linux](https://img.shields.io/badge/Linux-x86__64%20b%C3%AAta-6D28D9?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/anderson76389/All-Download/releases/tag/linux-v0.1.5-beta)

</div>

---

## 📥 Télécharger All-Download

| Plateforme | Édition | Téléchargement officiel |
|:--|:--|:--|
| 🖥️ **Windows 10/11 (x64)** | **Portable** · Sans installation | **[⬇️ Télécharger le ZIP Portable](https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Portable-Windows.zip)** |
| 🖥️ **Windows 10/11 (x64)** | **Classique** · Avec installateur | **[⬇️ Télécharger le ZIP Classique](https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Classique-Windows.zip)** |
| 📱 **Android 7+** | **APK officielle — 0.6.21-beta** | **[⬇️ Télécharger l’APK Android](https://github.com/anderson76389/All-Download/releases/download/android-v0.6.21-beta/All-Download-Android-0.6.21-beta.apk)** |
| 🐧 **Linux x86_64 (glibc)** | **Portable — 0.1.5-beta** | **[⬇️ Télécharger Linux (archive .tar.xz)](https://github.com/anderson76389/All-Download/releases/download/linux-v0.1.5-beta/All-Download-Linux-x86_64.tar.xz)** |

**[Release Android et notes de version](https://github.com/anderson76389/All-Download/releases/tag/android-v0.6.21-beta)** · [Empreinte SHA-256 de l’APK](https://github.com/anderson76389/All-Download/releases/download/android-v0.6.21-beta/All-Download-Android-0.6.21-beta.apk.sha256) · [Dernière Release stable Windows](https://github.com/anderson76389/All-Download/releases/latest)

> **Important :** Windows, Android et Linux sont trois éditions distinctes. Installez uniquement le format correspondant à votre appareil (ZIP Windows, APK Android, archive Linux). Les fichiers officiels sont ceux des [Releases GitHub](https://github.com/anderson76389/All-Download/releases). La première version Linux est une bêta portable, non un .deb/.rpm.

## ✨ Fonctionnalités

| Fonction | Windows | Android | Linux (bêta) |
|:--|:--:|:--:|:--:|
| Vidéo MP4/WebM et audio MP3/M4A/FLAC | ✅ | ✅ | ✅ |
| GIF, playlists, chaînes et file d'attente | ✅ | ✅ | ✅ |
| Qualités, miniatures et métadonnées | ✅ | ✅ | ✅² |
| Dossiers organisés et ouverture des fichiers | ✅ | ✅ | ✅ |
| Thèmes clair, sombre et OLED | ✅ | ✅ | ✅ |
| Clips Twitch et VOD publiques accessibles | ✅ | ✅ | ✅² |
| TwitchDownloader spécialisé et secours HLS | ✅ | — | — |
| Mise à jour depuis l'application | Selon édition | ✅¹ | Vérification manuelle³ |

¹ Sur Android, All-Download télécharge et vérifie l’APK **dans l’application**, puis ouvre **l’installateur officiel Android** : l’autorisation et la confirmation de l’utilisateur restent nécessaires. Il n’y a pas d’installation silencieuse.

² La version Linux réutilise l'interface Windows mais possède un moteur natif séparé. Les sous-titres et quelques traitements particuliers restent à valider sur une distribution réelle.

³ Sous Linux, **Paramètres → Appli → Linux** vérifie les nouvelles Releases officielles sur demande et ouvre leur page. Le téléchargement, la décompression et le remplacement restent manuels : aucune mise à jour silencieuse.

La disponibilité des formats et des plateformes dépend des sites, de leur authentification et de leurs éventuelles restrictions. Les vidéos protégées par DRM ne sont pas prises en charge.

---

## 📱 Android — même identité, interface adaptée

**Version Android 0.6.21 bêta :** Android 15 interrompt proprement les téléchargements en arrière-plan à expiration de la durée système : tâches sauvegardées et reprise manuelle possible sans effacer les fichiers partiels. Réessais réseau limités, nettoyage prudent des anciens dossiers temporaires orphelins et notifications « Fermer ». L’interface et les formats de téléchargement existants restent inchangés.

<sub>Code et instructions : [android/README.md](https://github.com/anderson76389/All-Download/blob/main/android/README.md) · Icône Android : [android/branding](https://github.com/anderson76389/All-Download/tree/main/android/branding)</sub>

- **Nom et logo conservés** dans le lanceur Android, le splash et la fenêtre de mise à jour ; aucun bandeau de marque permanent dans les pages.
- **Aucun en-tête ALL-DOWNLOAD permanent.** Navigation en capsule **Liquid Glass** sur téléphone ; barre latérale sur tablette et pliable ouvert.
- **Accueil, File d’attente, Dossiers, Paramètres**, boutons accessibles, icônes vectorielles et placement adapté à la taille de l’écran.
- **Moteur natif Android** avec yt-dlp et FFmpeg intégrés. Vidéo, audio, GIF, playlist, chaîne et clips Twitch.
- **Stockage organisé** dans `Téléchargements/All-Download/`, avec sept catégories. Cookies facultatifs et préférences dans le stockage privé de l’application.
- **Optimisations** : file persistante, interface actualisée seulement quand nécessaire, chargement progressif et réduction des animations configurable.

### 🔄 Mettre à jour Android depuis l’application

1. Ouvrir **All-Download** : l’application vérifie les nouvelles Releases Android, sans confondre avec Windows.
2. Une **bannière apparaît dans le contenu seulement si une nouvelle version est disponible**, à la manière de Kovelyx : nouveautés, **Installer**, **Détails** et **Plus tard**.
3. Appuyer sur **Installer** : l’APK est téléchargée dans le cache privé, avec progression, contrôle SHA-256 et vérification de la signature.
4. Confirmer l’installation dans **Android**. Le navigateur n’est pas ouvert.

La recherche manuelle et l’activation des alertes se trouvent dans **Paramètres → Appli → Mises à jour Android**. La version **0.6.21-beta** utilise une signature permanente et supprime les anciennes APK du cache privé après installation : les futures APK signées avec cette même clé pourront être installées par-dessus. Une ancienne bêta signée avec une autre clé peut nécessiter une désinstallation préalable, susceptible d’effacer les données privées de l’application. **Sauvegardez vos réglages et cookies si nécessaire.**

**Compatibilité testée en CI :** Android 9, 14 et 15, avec un profil tablette Android 14. Les tests de liens vidéo publics et de certains réseaux sociaux réussissent ; l’accès à toutes les vidéos de chaque service n’est pas garanti.

**Mesurer la RAM, le CPU et la batterie sur un appareil réel :** connecter un téléphone Android avec ADB autorisé, puis exécuter depuis la racine du dépôt (PowerShell Windows) :

```powershell
.\\scripts\\audit-android-performance.ps1 -Samples 18 -IntervalSeconds 10
```

Le rapport CSV est enregistré dans `Donnees/diagnostics/`. Comparer une session au repos et une session en téléchargement. **Les résultats CI n’équivalent pas à une mesure prolongée sur un HONOR Magic V6.**

---

## 💻 Windows — Portable ou Classique

| Portable | Classique |
|:--|:--|
| Décompressez `All-Download-Portable-Windows.zip` et lancez `All_Media_Download.exe`. | Décompressez `All-Download-Classique-Windows.zip` et lancez `All-Download-Setup.exe`. |
| Sans installation ; emplacement déplaçable. | Installateur Windows et raccourcis selon les options sélectionnées. |
| Médias, réglages et outils conservés dans son dossier `All-Download/`. | Médias et données conservés dans le dossier de l’édition Classique. |

**Prérequis :** Windows 10/11 x64, WebView2 et connexion Internet. Le lancement peut récupérer les outils nécessaires dans le dossier local de l’application. Aucun dossier personnel n’est censé être déplacé automatiquement en dehors de `All-Download/`.

### 📂 Organisation Windows

```text
All-Download/
├── All_Media_Download.exe
├── AUDIOS/
├── VIDÉOS/
├── TWITCH/
├── GIFS/
├── CHAÎNES/
├── PLAYLIST/
├── AUTRES/
└── Donnees/
    ├── config.json
    ├── bin/
    ├── cache/
    └── journaux et profils locaux
```

Les **sept catégories de médias** sont créées automatiquement. `Donnees/` regroupe configuration, outils, fichiers temporaires et journaux. La version Portable monofichier peut utiliser temporairement `%TEMP%` pour son extraction technique, sans y déplacer vos téléchargements.

**Twitch Windows :** les VOD publiques compatibles passent prioritairement par [TwitchDownloaderCLI](https://github.com/lay295/TwitchDownloader), avec un secours HLS indépendant lorsque possible. La qualité native 1080p est privilégiée, sinon 720p natif si disponible : aucune résolution artificiellement agrandie. Les clips Twitch et les autres plateformes restent traités par yt-dlp. YouTube peut utiliser Deno local pour certains formats, sans installation globale.

### ⚙️ Utilisation

1. **Collez** une URL publique ou un lien que vous êtes autorisé à récupérer.
2. Choisissez **Vidéo, Audio ou GIF**, puis le format et la qualité.
3. Lancez directement le téléchargement ou ajoutez-le à la **file d’attente**.
4. Retrouvez le fichier dans son **dossier de catégorie**.

---

## 🐧 Linux — portable x86_64 (bêta)

**0.1.5 bêta :** fermeture Qt et sous-processus yt-dlp/FFmpeg arrêtés proprement, réessais réseau limités, qualité Twitch **1080p puis 720p natifs**, et archive `.tar.xz` optimisée de **321,1 Mo à 311,6 Mo** (mesure CI, sans suppression de bibliothèques). Mises à jour Linux vérifiées manuellement avec SHA-256 ; lancement testé sur **Ubuntu 22.04 et 24.04**.

**L'interface HTML/CSS/JavaScript reste basée sur Windows** (extraite de `yt_app.py`). Seuls les boutons Linux de mise à jour et de raccourci sont ajoutés à l'onglet Appli. Le moteur Qt WebEngine, yt-dlp et FFmpeg est natif Linux, sans WebView2 ni exécutable Windows.

1. Télécharger **[Linux x86_64 0.1.5-beta (.tar.xz)](https://github.com/anderson76389/All-Download/releases/download/linux-v0.1.5-beta/All-Download-Linux-x86_64.tar.xz)**, ou l'**[archive .tar.gz](https://github.com/anderson76389/All-Download/releases/download/linux-v0.1.5-beta/All-Download-Linux-x86_64.tar.gz)**.
2. Extraire le dossier **All-Download/** dans un emplacement modifiable, puis lancer **All-Download-Linux** (sans sudo).
3. Pour obtenir un raccourci de menu, ouvrir **Paramètres → Appli → Linux → Ajouter au menu des applications**. Il est possible de le retirer depuis l'application.
4. Pour vérifier une nouvelle version, choisir **Vérifier les mises à jour Linux**. Le navigateur n'ouvre la Release que sur demande ; l'installation reste manuelle.

Les téléchargements et les données restent dans le dossier All-Download/ (catégories et Donnees/), à l'exception du fichier `.desktop` facultatif placé dans le répertoire des applications utilisateur. Avant de remplacer une version, **fermer All-Download** et conserver `Donnees/` ainsi que vos sept dossiers de médias.

Les VOD Twitch sont gérées par yt-dlp, sans le moteur spécialisé TwitchDownloaderCLI de Windows. Debian, Fedora et les environnements Wayland variés nécessitent encore des validations réelles.

**[Documentation Linux détaillée](https://github.com/anderson76389/All-Download/blob/main/linux/README.md)** · [SHA-256 de l'archive .tar.xz](https://github.com/anderson76389/All-Download/releases/download/linux-v0.1.5-beta/All-Download-Linux-x86_64.tar.xz.sha256)

---

## 🛡️ Vérification et sécurité

- **Android :** une APK signée est accompagnée de son fichier `.apk.sha256`. L’application valide également le nom de paquet, la version et la compatibilité de la signature avant de demander l’installation.
- **Linux :** l'archive portable est publiée dans une Release bêta spécifique avec une empreinte SHA-256. Les exécutables Linux et leurs bibliothèques ne sont pas compatibles Windows/Android.
- **Windows :** les éditions officielles sont disponibles dans la dernière Release stable. Un avertissement SmartScreen peut apparaître en l’absence d’une signature d’éditeur reconnue ; ne désactivez pas les protections de Windows.
- **Mises à jour :** les téléchargements Android et Windows sont distincts. La suppression d’anciennes Releases ne doit pas supprimer la dernière version Windows ni l’APK Android courante.

**Dépannage :** [signaler un problème](https://github.com/anderson76389/All-Download/issues) · [documentation Android](https://github.com/anderson76389/All-Download/blob/main/android/README.md) · [voir les Releases](https://github.com/anderson76389/All-Download/releases)

<details>
<summary><strong>Développeurs — exécution depuis les sources Windows</strong></summary>

```powershell
python -m pip install pywebview==6.2.1
python yt_app.py
```

Les sources Windows incluent `yt_app.py`, la configuration PyInstaller et l’installateur. `android/` contient la version native Android ; `linux/` contient le port Linux et ses tests, qui réutilisent la page HTML Windows sans exécuter son code spécifique à Windows. Les dépendances, les licences et les versions doivent être vérifiées avant toute distribution.

</details>

---

<div align="center">

**ALL-DOWNLOAD · Télécharger · Convertir · Organiser**

[Releases officielles](https://github.com/anderson76389/All-Download/releases) · [Code source](https://github.com/anderson76389/All-Download) · [Signaler un bug](https://github.com/anderson76389/All-Download/issues)

</div>
