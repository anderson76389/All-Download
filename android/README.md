# All-Download Android — bêta isolée

Nouvelle application Android **indépendante de Windows**, dans le dossier `android/`. Les éditions Portable/Classique Windows, `yt_app.py`, `twitch_hls.py` et `build-windows.yml` ne sont pas modifiés.

## Contenu de la bêta

- Application native Android (Android 7.0+, API 24), APK multi-architecture ARM 32/64 et x86 32/64.
- Moteur yt-dlp, QuickJS et FFmpeg intégrés via `youtubedl-android` 0.18.1 ; pas de PC, de Termux, ni de serveur personnel.
- Modes vidéo, audio MP3/M4A/FLAC, GIF (conversion), playlists et chaînes ; URL partagée depuis d'autres applis, annulation, progression et notification de téléchargement.
- Téléchargement **dans l'espace privé temporaire** de l'appli, puis export (streaming) dans `Téléchargements/All-Download/<catégorie>/` via MediaStore sur Android 10+, et accès direct sur Android 7-9 (permission de stockage).
- Répertoires catégorisés : `VIDÉOS`, `AUDIOS`, `TWITCH`, `GIFS`, `CHAÎNES`, `PLAYLIST`, `AUTRES`.
- Pour une **VOD Twitch en mode vidéo**, le format yt-dlp est limité aux flux dont la résolution source est **exactement 1080**, sinon **exactement 720** ; pas d'upscaling, de 480p automatique ni de réencodage vidéo. 720p et 480p restent sélectionnables manuellement.

## Liens sociaux et comptes (bêta 0.1.2)

- Reddit, Instagram, X/Twitter, Pinterest, TikTok, Facebook (notamment Reels), Vimeo, Bluesky et Dailymotion sont traités par les extracteurs **yt-dlp** ; leur disponibilité varie selon la vidéo, les protections du site et l'adresse IP.
- Le moteur yt-dlp tente une **actualisation officielle** en début de téléchargement social (puis une fois par semaine si elle aboutit). Si le réseau échoue, un nouvel essai est possible 12 heures plus tard et l'ancienne version continue de fonctionner. **Aucun service distant All-Download** n'est nécessaire.
- Les vidéos publiques ne nécessitent pas de connexion si le site les autorise. Quand un site exige une session, **l'utilisateur peut importer volontairement un fichier Netscape `cookies.txt` issu de son propre compte autorisé** via le sélecteur de documents. Il est copié dans l'espace privé de l'appli (limite 4 Mo), utilisé par yt-dlp et peut être supprimé à tout moment. **Ne jamais envoyer ses cookies ni son fichier à une autre personne.**
- Il n'y a **pas de contournement** des restrictions d'accès et pas de garantie universelle : certaines URL Reddit nécessitent des cookies, certaines anciennes vidéos Facebook ne sont pas interprétables par yt-dlp, et certains services bloquent les adresses IP automatisées. Les liens connus en échec restent suivis par les tests et sont signalés `SKIP` avec motif lorsqu'une limitation du service est identifiée.
- La suite Android de base teste les téléchargements locaux et le stockage privé, la suite réseau teste MP4/WebM/HLS/Twitch et la suite sociale teste séparément les plateformes. Une réussite sur un lien ne garantit pas tous les liens du site.

## Limites réelles

Il s'agit d'une **première bêta**, pas de la parité fonctionnelle avec l'édition Windows. Le secours HLS Twitch indépendant de `TwitchDownloaderCLI.exe`, l'authentification Twitch et les sous-titres/cookies, les paramètres avancés, les historiques, la file d'attente persistante, les thèmes et tous les outils Windows restent à porter et à valider. TwitchDownloaderCLI Windows ne peut pas être exécuté tel quel sur Android. Une VOD Twitch inaccessible à yt-dlp peut donc échouer sur cette bêta.

Les flux protégés/DRM, les contenus privés sans autorisation et les vidéos supprimées ne sont pas garantis. La résolution choisie correspond aux formats source, pas à une promesse de compatibilité de chaque plateforme. Le stockage Android impose un espace de travail temporaire privé avant l'export public ; aucun accès au système de fichiers racine ou permission « tous les fichiers » n'est demandé.

## Compilation

Via GitHub Actions : workflow `Build Android (beta)`, puis récupérer l'artefact `All-Download-Android-beta` après succès de la compilation.

En local : Android SDK plateforme 35, JDK 17 et Gradle 8.9, puis `gradle -p android :app:assembleDebug`.

**Important :** APK non testé sur appareil réel à cette étape ; ne pas considérer cette branche comme une version stable et ne pas fusionner sans validation Android (YouTube, Twitch, GIF, playlists, MediaStore, annulation, orientation, arrière-plan).
