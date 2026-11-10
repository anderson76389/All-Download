<div align="center">

<img src="./logo.jpg" alt="Logo All-Download" width="132">

# ALL-DOWNLOAD

**Téléchargez vos vidéos, musiques, GIF et playlists dans une seule application.**

Windows 10/11 et Android 7+ · Interface en français · Thèmes clair, sombre et OLED

[![Windows](https://img.shields.io/badge/Windows-Portable%20%26%20Classique-2563EB?style=for-the-badge&logo=windows11&logoColor=white)](https://github.com/anderson76389/All-Download/releases/latest)
[![Android](https://img.shields.io/badge/Android-APK%20b%C3%AAta-16A34A?style=for-the-badge&logo=android&logoColor=white)](https://github.com/anderson76389/All-Download/releases/tag/android-v0.6.10-beta)

</div>

---

## 📥 Télécharger All-Download

| Plateforme | Édition | Téléchargement officiel |
|:--|:--|:--|
| 🖥️ **Windows 10/11 (x64)** | **Portable** · Sans installation | **[⬇️ Télécharger le ZIP Portable](https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Portable-Windows.zip)** |
| 🖥️ **Windows 10/11 (x64)** | **Classique** · Avec installateur | **[⬇️ Télécharger le ZIP Classique](https://github.com/anderson76389/All-Download/releases/latest/download/All-Download-Classique-Windows.zip)** |
| 📱 **Android 7+** | **APK officielle — 0.6.10-beta** | **[⬇️ Télécharger l’APK Android](https://github.com/anderson76389/All-Download/releases/download/android-v0.6.10-beta/All-Download-Android-0.6.10-beta.apk)** |

**[Release Android et notes de version](https://github.com/anderson76389/All-Download/releases/tag/android-v0.6.10-beta)** · [Empreinte SHA-256 de l’APK](https://github.com/anderson76389/All-Download/releases/download/android-v0.6.10-beta/All-Download-Android-0.6.10-beta.apk.sha256) · [Dernière Release stable Windows](https://github.com/anderson76389/All-Download/releases/latest)

> **Important :** Windows et Android sont deux applications distinctes. Les ZIP Windows ne sont pas des fichiers Android et l’APK ne s’installe pas sur Windows. Les fichiers officiels sont uniquement ceux publiés dans les [Releases du dépôt](https://github.com/anderson76389/All-Download/releases).

## ✨ Fonctionnalités

| Fonction | Windows | Android |
|:--|:--:|:--:|
| Vidéo MP4/WebM et extraction audio MP3/M4A/FLAC | ✅ | ✅ |
| GIF, playlists, chaînes et file d’attente | ✅ | ✅ |
| Choix de qualité, sous-titres, miniatures et métadonnées | ✅ | ✅ |
| Dossiers organisés, accès aux médias téléchargés | ✅ | ✅ |
| Thèmes clair, sombre et OLED | ✅ | ✅ |
| Twitch : clips et vidéos accessibles | ✅ | ✅ |
| Twitch VOD : moteur spécialisé TwitchDownloader + secours HLS | ✅ | — |
| Mises à jour de l’application sans ouvrir le navigateur | Selon l’édition | ✅¹ |

¹ Sur Android, All-Download télécharge et vérifie l’APK **dans l’application**, puis ouvre **l’installateur officiel Android** : l’autorisation et la confirmation de l’utilisateur restent nécessaires. Il n’y a pas d’installation silencieuse.

La disponibilité des formats et des plateformes dépend des sites, de leur authentification et de leurs éventuelles restrictions. Les vidéos protégées par DRM ne sont pas prises en charge.

---

## 📱 Android — même identité, interface adaptée

**Version Android 0.6.10 bêta :** navigation mobile non tronquée, libellés et boutons réalignés, sept pictogrammes de dossiers plus lisibles, panneau d'état compact et rafraîchissement de yt-dlp pour YouTube sur réseau non facturé. Les modifications Windows sont inchangées.

<sub>Code et instructions : [android/README.md](https://github.com/anderson76389/All-Download/blob/feature/android-app/android/README.md) · Icône Android : [android/branding](https://github.com/anderson76389/All-Download/tree/feature/android-app/android/branding)</sub>

- **Nom et logo fixes** : All-Download reste identifiable à l’écran, sur le lanceur et dans la fenêtre de mise à jour.
- **En-tête toujours visible**, même pendant le défilement. Navigation en capsule **Liquid Glass** sur téléphone ; barre latérale sur tablette et pliable ouvert.
- **Accueil, File d’attente, Dossiers, Paramètres**, boutons accessibles, icônes vectorielles et placement adapté à la taille de l’écran.
- **Moteur natif Android** avec yt-dlp et FFmpeg intégrés. Vidéo, audio, GIF, playlist, chaîne et clips Twitch.
- **Stockage organisé** dans `Téléchargements/All-Download/`, avec sept catégories. Cookies facultatifs et préférences dans le stockage privé de l’application.
- **Optimisations** : file persistante, interface actualisée seulement quand nécessaire, chargement progressif et réduction des animations configurable.

### 🔄 Mettre à jour Android depuis l’application

1. Ouvrir **All-Download** : l’application vérifie les nouvelles Releases Android, sans confondre avec Windows.
2. Une **bannière apparaît en haut**, à la manière de Kovelyx : numéro de version, nouveautés, **Installer**, **Détails** et **Plus tard**.
3. Appuyer sur **Installer** : l’APK est téléchargée dans le cache privé, avec progression, contrôle SHA-256 et vérification de la signature.
4. Confirmer l’installation dans **Android**. Le navigateur n’est pas ouvert.

La recherche manuelle et l’activation des alertes se trouvent dans **Paramètres → Appli → Mises à jour Android**. La version **0.6.10-beta** utilise une signature permanente : les futures APK signées avec cette même clé pourront être installées par-dessus. Une ancienne bêta signée avec une autre clé peut nécessiter une désinstallation préalable, susceptible d’effacer les données privées de l’application. **Sauvegardez vos réglages et cookies si nécessaire.**

**Compatibilité testée en CI :** Android 9, 14 et 15, avec un profil tablette Android 14. Les tests de liens vidéo publics et de certains réseaux sociaux réussissent ; l’accès à toutes les vidéos de chaque service n’est pas garanti.

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

## 🛡️ Vérification et sécurité

- **Android :** une APK signée est accompagnée de son fichier `.apk.sha256`. L’application valide également le nom de paquet, la version et la compatibilité de la signature avant de demander l’installation.
- **Windows :** les éditions officielles sont disponibles dans la dernière Release stable. Un avertissement SmartScreen peut apparaître en l’absence d’une signature d’éditeur reconnue ; ne désactivez pas les protections de Windows.
- **Mises à jour :** les téléchargements Android et Windows sont distincts. La suppression d’anciennes Releases ne doit pas supprimer la dernière version Windows ni l’APK Android courante.

**Dépannage :** [signaler un problème](https://github.com/anderson76389/All-Download/issues) · [documentation Android](https://github.com/anderson76389/All-Download/blob/feature/android-app/android/README.md) · [voir les Releases](https://github.com/anderson76389/All-Download/releases)

<details>
<summary><strong>Développeurs — exécution depuis les sources Windows</strong></summary>

```powershell
python -m pip install pywebview==6.2.1
python yt_app.py
```

Les sources Windows incluent `yt_app.py`, la configuration PyInstaller et l’installateur. La branche `feature/android-app` contient la version native Android. Les dépendances, les licences et les versions doivent être vérifiées avant toute distribution.

</details>

---

<div align="center">

**ALL-DOWNLOAD · Télécharger · Convertir · Organiser**

[Releases officielles](https://github.com/anderson76389/All-Download/releases) · [Code source](https://github.com/anderson76389/All-Download) · [Signaler un bug](https://github.com/anderson76389/All-Download/issues)

</div>
