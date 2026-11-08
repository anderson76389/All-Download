# All-Download Android — bêta 0.3.0

Nouvelle application Android **indépendante de Windows**, dans le dossier `android/`. Les éditions Portable/Classique Windows, `yt_app.py`, `twitch_hls.py` et `build-windows.yml` ne sont pas modifiés.

## Interface mobile fidèle à All-Download

- **Nom, icône et logo d'origine** : la compilation Android copie la ressource `logo.jpg` à la racine du dépôt, en lecture seule, vers les ressources Android générées. Les éditions Windows ne changent pas.
- **Splash screen natif**, identité visuelle de Windows : violet `#7C3AED`, thème sombre `#141414`, cartes `#212121`, ainsi que les modes clair et OLED enregistrés.
- **Quatre écrans Android natifs** : Accueil (URL, vidéo/audio/GIF, qualité), File d'attente (progression et reprise), Dossiers (navigation et ouverture des médias) et Paramètres (thèmes, actualisation yt-dlp, cookies privés).
- **File de téléchargement persistante** dans les préférences privées, avec exécution séquentielle, progression, relance d'une tâche échouée et suppression des tâches terminées. Pause/reprise best-effort via `yt-dlp --continue` et espace de travail privé par tâche : certains serveurs interdisent la reprise ; dans ce cas, la tâche peut repartir du début.
- **Android pliable/tablette** : interface centrée et limitée en largeur sur les grands écrans, recalcul au changement d'orientation ; contrôles tactiles natifs sur petit écran.
- **Fichiers accessibles** depuis les sept dossiers de l'app : MediaStore Android 10+ et FileProvider Android 7–9, sans permission « gérer tous les fichiers ».

## Mises à jour Android dans l'application

À partir de la **bêta 0.3.0**, All-Download interroge directement l'API des **GitHub Releases** à l'ouverture (vérification limitée à une fois toutes les 30 minutes). Seules les versions publiées avec un tag `android-vX.Y.Z-beta` et un vrai fichier `All-Download-Android-X.Y.Z-beta.apk` sont retenues : **les Releases Windows ne déclenchent jamais de proposition d'APK**.

Quand une version Android plus récente existe, l'application affiche une **fenêtre native animée** avec le logo, le numéro de version, les nouveautés, « Télécharger la mise à jour » et « Plus tard ». Elle ne réaffiche pas la même fenêtre à chaque retour dans l'application ; une nouvelle version entraîne une nouvelle notification. Un interrupteur et un bouton « Rechercher une mise à jour » se trouvent dans Paramètres. Le bouton ouvre le fichier officiel GitHub dans le navigateur ; **Android conserve seul l'autorisation d'installer l'APK**. Il n'y a aucune installation silencieuse, service d'auto-mise-à-jour tiers ou compte All-Download.

**Signature APK :** les builds de test des anciennes bêta 0.1.2 et 0.2.0 ont été signés avec des clés de débogage éphémères. Ils ne peuvent **pas** garantir une installation de mise à jour par-dessus l'ancienne version. Pour des mises à jour Android vraiment installables sans désinstallation, configurez une **clé de signature persistante et privée** via les secrets GitHub Actions `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD` ; le workflow Android les utilise lorsqu'ils sont présents. **Ne commitez jamais votre keystore ou vos mots de passe.** La première transition vers la clé persistante pourra demander une désinstallation, ce qui effacera les données privées de l'appli ; les médias déjà exportés dans Téléchargements ne sont pas supprimés.

## Réglages adaptés depuis Windows

Les trois thèmes Windows **Clair / Sombre / OLED** sont enregistrés et appliqués au téléphone et à la tablette. Les réglages **utilisables dans le moteur Android** incluent le conteneur MP4/MKV, le remux optionnel, le débit cible MP3, les métadonnées et miniatures, les sous-titres lorsque la source les propose, SponsorBlock YouTube, le proxy HTTP(S)/SOCKS, les en-têtes User-Agent, les arguments yt-dlp avancés, les tentatives/délais/fragments réseau, les notifications, les animations et les cookies personnels privés. Les choix sont conservés dans les préférences de l'application.

Sur tablette et sur pliable ouvert (largeur Android d'au moins 720 dp), l'interface passe à une **barre latérale** et à une colonne de contenu large. Sur téléphone, elle garde des onglets tactiles horizontaux. Les fichiers personnels restent dans les sept dossiers **Téléchargements/All-Download/**, sans déplacement arbitraire vers le stockage racine. Certains réglages Windows propres au PC (WebView2, CLI TwitchDownloader, runtime Deno Windows, sélection de dossiers Windows et normalisation avancée) ne sont pas équivalents sur Android et ne sont pas affichés comme de faux boutons.

## Contenu de la bêta

- Application native Android (Android 7.0+, API 24), APK multi-architecture ARM 32/64 et x86 32/64.
- Moteur yt-dlp, QuickJS et FFmpeg intégrés via `youtubedl-android` 0.18.1 ; pas de PC, de Termux, ni de serveur personnel.
- Modes vidéo, audio MP3/M4A/FLAC, GIF (conversion), playlists et chaînes ; URL partagée depuis d'autres applis, annulation, progression et notification de téléchargement.
- Téléchargement **dans l'espace privé temporaire** de l'appli, puis export (streaming) dans `Téléchargements/All-Download/<catégorie>/` via MediaStore sur Android 10+, et accès direct sur Android 7-9 (permission de stockage).
- Répertoires catégorisés : `VIDÉOS`, `AUDIOS`, `TWITCH`, `GIFS`, `CHAÎNES`, `PLAYLIST`, `AUTRES`.
- Pour une **VOD Twitch en mode vidéo**, le format yt-dlp est limité aux flux dont la résolution source est **exactement 1080**, sinon **exactement 720** ; pas d'upscaling, de 480p automatique ni de réencodage vidéo. 720p et 480p restent sélectionnables manuellement.

## Liens sociaux et comptes (bêta 0.3.0)

- Reddit, Instagram, X/Twitter, Pinterest, TikTok, Facebook (notamment Reels), Vimeo, Bluesky et Dailymotion sont traités par les extracteurs **yt-dlp** ; leur disponibilité varie selon la vidéo, les protections du site et l'adresse IP.
- Le moteur yt-dlp tente une **actualisation officielle** en début de téléchargement social (puis une fois par semaine si elle aboutit). Si le réseau échoue, un nouvel essai est possible 12 heures plus tard et l'ancienne version continue de fonctionner. **Aucun service distant All-Download** n'est nécessaire.
- Les vidéos publiques ne nécessitent pas de connexion si le site les autorise. Quand un site exige une session, **l'utilisateur peut importer volontairement un fichier Netscape `cookies.txt` issu de son propre compte autorisé** via le sélecteur de documents. Il est copié dans l'espace privé de l'appli (limite 4 Mo), utilisé par yt-dlp et peut être supprimé à tout moment. **Ne jamais envoyer ses cookies ni son fichier à une autre personne.**
- Il n'y a **pas de contournement** des restrictions d'accès et pas de garantie universelle : certaines URL Reddit nécessitent des cookies, certaines anciennes vidéos Facebook ne sont pas interprétables par yt-dlp, et certains services bloquent les adresses IP automatisées. Les liens connus en échec restent suivis par les tests et sont signalés `SKIP` avec motif lorsqu'une limitation du service est identifiée.
- La suite Android de base teste les téléchargements locaux et le stockage privé, la suite réseau teste MP4/WebM/HLS/Twitch et la suite sociale teste séparément les plateformes. Une réussite sur un lien ne garantit pas tous les liens du site.

## Limites réelles

Il s'agit d'une **bêta mobile**, pas encore de la parité fonctionnelle avec Windows. Le secours HLS Twitch indépendant de `TwitchDownloaderCLI.exe`, l'authentification Twitch avancée, les sous-titres non fournis par les plateformes, les outils Windows spécialisés, les journaux et historiques détaillés et certains réglages sont encore à porter. Les boutons de pause/reprise de la file Android utilisent les mécanismes disponibles de yt-dlp ; la reprise n'est pas garantie pour les serveurs non compatibles. TwitchDownloaderCLI Windows ne peut pas être exécuté tel quel sur Android. Certaines VOD Twitch peuvent encore échouer.

Les flux protégés/DRM, les contenus privés sans autorisation et les vidéos supprimées ne sont pas garantis. La résolution choisie correspond aux formats source, pas à une promesse de compatibilité de chaque plateforme. Le stockage Android impose un espace de travail temporaire privé avant l'export public ; aucun accès au système de fichiers racine ou permission « tous les fichiers » n'est demandé.

## Compilation

Via GitHub Actions : workflow `Build Android (beta)`, puis récupérer l'artefact `All-Download-Android-beta` après succès. La préversion `android-v0.3.0-beta` est distribuée séparément des Releases stables Windows.

En local : Android SDK plateforme 35, JDK 17 et Gradle 8.9, puis `gradle -p android :app:assembleDebug`.

**Important :** APK non testé sur appareil réel à cette étape ; ne pas considérer cette branche comme une version stable et ne pas fusionner sans validation Android (YouTube, Twitch, GIF, playlists, MediaStore, annulation, orientation, arrière-plan).
