# All-Download Android 1.0.0 — édition stable

**Partage Android → All-Download :** depuis YouTube, Twitch, Reddit, Instagram, TikTok, Pinterest ou un navigateur, utiliser **Partager → All-Download**. Pour un lien HTTPS/HTTP, l'écran d'accueil est ouvert et l'URL est préremplie sans téléchargement automatique. Plusieurs liens partagés sont mis en attente.

**Vidéos locales :** depuis Galerie ou Fichiers, partager une vidéo MP4, WebM, MKV, MOV et autres formats reconnus vers All-Download. L'application copie en flux jusqu'à 12 fichiers content:// dans Téléchargements/All-Download/VIDÉOS, sans supprimer les originaux et sans charger toute la vidéo en RAM. Une copie incomplète est supprimée en cas d'échec. Sur Android 7–9, l'autorisation de stockage peut être demandée.

**Mises à jour :** versionCode 30, versionName 1.0.0 et même clé privée que 0.6.22. Le détecteur accepte les versions stables/bêta et donne priorité à la stable à numéros égaux. L'APK est vérifiée (SHA-256, signature) et l'installation requiert la confirmation du système Android. Les réglages et téléchargements doivent rester présents lors d'une installation par-dessus.

**Limites :** certains sites peuvent exiger une authentification, imposer des DRM, bloquer les téléchargements ou ne transmettre aucun fichier à Android. Les tests CI ne remplacent pas les essais sur appareil physique.

---
## Android 0.6.22-beta — sécurité des mises à jour

**Limite Dailymotion :** certains flux HLS exigent l'émulation TLS Firefox/Chrome (curl_cffi), qui n'est pas intégrée à l'APK Android. Si ce blocage externe apparaît en CI, le test est marqué *non concluant (SKIP)* avec la raison exacte, jamais « téléchargement réussi ». Les autres erreurs Dailymotion restent des échecs. Les sites compatibles et leurs qualités natives restent inchangés.

- Vérification d'espace avant téléchargement de l'APK (réserve de 16 Mio), sans effacer de fichiers utilisateur.
- Rejet des réponses checksum trop longues ; aucun chargement non borné en mémoire.
- Seuls les anciens caches appartenant à All-Download sont éligibles au nettoyage ; les futures APK en attente sont préservées.
- Les tests de reprise de la file après expiration Android 15 passent désormais réellement sur les émulateurs téléphone et tablette.

## Correctifs 0.6.22-beta

- Android 15 : expiration des services de transfert gérée proprement, reprise manuelle après pause sans suppression des fichiers partiels.
- Réessais HTTP/fragment bornés et nettoyage prudent, plafonné à huit dossiers temporaires orphelins âgés de plus de sept jours.
- File et paramètres conservés à travers les mises à jour signées ; Android demande toujours confirmation pour installer l'APK.

# All-Download Android — bêta 0.6.20

## Partage et fermeture de l’application — 0.6.20

- **Partager → All-Download** depuis YouTube, Twitch ou une application envoyant un lien HTTP(S) : ouverture du téléchargeur avec l’URL préremplie ; démarrage uniquement après confirmation.
- Partages texte et vidéo contenant un lien pris en charge ; un fichier local `content://` sans URL ne peut pas être téléchargé et déclenche un message explicatif.
- Notification « All-Download ouverte » avec **Fermer** sans service permanent au repos. Pendant les transferts, boutons **Pause / Annuler / Fermer** ; fermeture du transfert en cours et conservation de la file d’attente.
- Rafraîchissement de l’interface désactivé en arrière-plan. Une absence absolue de fuite mémoire ou de consommation batterie exige encore des mesures sur un téléphone réel.



## Mises à jour : récupération de l'espace privé — 0.6.18

- Après installation d'une mise à jour dans l'application, les anciennes APK All-Download et les fichiers `.apk.part` devenus obsolètes sont supprimés du cache privé.
- Une APK plus récente encore en attente et les fichiers étrangers au système de mise à jour sont préservés. Les médias utilisateur, réglages, cookies et file d'attente ne sont jamais concernés.
- Un test instrumenté Android vérifie explicitement la suppression de l'ancien cache sans perte d'autres fichiers.

## Alignement final des icônes et textes — 0.6.17

- Sur téléphone, les pictogrammes et libellés des actions **Télécharger**, **Ajouter**, **Coller**, **Vidéo**, **Audio**, **GIF**, **Playlist** et **Twitch** sont centrés ensemble, sans icône isolée à gauche du texte.
- Les onglets de réglages **Médias / Appli / Réseau** sont alignés sur une seule ligne quand l'écran le permet et empilés sur les petits écrans ou avec des caractères agrandis.
- Les titres de sections sont alignés verticalement avec leur pictogramme ; les grandes commandes de file d'attente et de cookies gardent leur alignement à gauche.
- La correction conserve les mêmes boutons, gestes et écouteurs, et ne modifie pas les moteurs de téléchargement.
- Validation GitHub : compilation signée, **42 tests Android instrumentés** par profil (Android 9/14/15 et tablette Android 14), tests de téléchargements publics et réseaux sociaux. Les médias bloqués par leur plateforme sont notés **non vérifiés / ignorés**, jamais comptés comme téléchargements réussis.
- APK officielle : [Android 0.6.17-beta](https://github.com/anderson76389/All-Download/releases/tag/android-v0.6.17-beta) · [SHA-256](https://github.com/anderson76389/All-Download/releases/download/android-v0.6.17-beta/All-Download-Android-0.6.17-beta.apk.sha256).

# All-Download Android — bêta 0.6.15

## Finitions mobile et actions vérifiées — 0.6.15

- Les paires de boutons passent sur deux lignes lorsque leur conteneur est étroit ou que le texte système est agrandi. Les mêmes actions restent accessibles, avec des cibles d’au moins 52 dp.
- Les cartes d’accueil et de réglages partagent des marges intérieures de 16 dp. Les intitulés de nettoyage et les boutons des réglages peuvent revenir sur deux lignes.
- Les descriptions des interrupteurs restent lisibles et les champs avancés sont limités à 500 caractères, comme le moteur, pour éviter d’afficher une valeur trop longue qui ne serait pas enregistrée.
- Tests instrumentés des actions Télécharger/Ajouter (validation), Copier/Réessayer/Supprimer, des douze interrupteurs et de leurs préférences. Captures des six pages et catégories de réglages sur les émulateurs pour contrôle visuel.


## File d'attente : hiérarchie simplifiée — 0.6.14

- Les téléchargements remontent immédiatement après **Reprendre / Pause** ; les options de nettoyage sont déplacées en bas, pour que les commandes de suppression ne parasitent plus la liste.
- Nettoyage **replié par défaut** : un bouton de 52 dp permet d'afficher ou de masquer les actions Effacer les terminés / Erreurs / En attente. L'état est conservé lors d'une rotation.
- Marges verticales plus nettes entre le résumé (24 dp), les commandes (26 dp), le titre des téléchargements (18 dp) et le nettoyage (26 dp), cartes de tâches espacées de 20 dp.
- Suppression des sous-titres redondants sur la file pour une interface plus sobre ; noms et pictogrammes cohérents avec Android et la palette claire/sombre/OLED.
- Les actions réelles de Pause, Reprendre, Copier, Réessayer, Supprimer et nettoyage sont inchangées ; aucune modification Windows ni yt-dlp/FFmpeg.
- Tests Android instrumentés pour vérifier l'ordre des sections, l'ouverture/fermeture du nettoyage et les cibles tactiles.

---

## File d'attente : sections séparées et boutons lisibles — 0.6.13

- Section File d'attente reconstruite sur Android en **trois cartes distinctes** : récapitulatif, contrôles (Reprendre/Pause) et nettoyage (Terminés/Erreurs/En attente). Les éléments de téléchargement sont une quatrième zone avec son titre et ses cartes.
- Espacements verticaux **14 à 20 dp** entre groupes, marges internes d'au moins **15 dp**, boutons de **52 dp** et espace de **12 dp** entre boutons adjacents. Le bas des cartes ne touche plus le bloc suivant.
- Chaque téléchargement affiche clairement le statut, le type de média, le pourcentage, l'adresse et le message éventuel, avec des écarts adaptés.
- Actions de téléchargement en **boutons visibles de largeur égale** au lieu d'une ligne à défilement horizontal. « Réessayer » dispose de sa propre ligne si nécessaire.
- Les clics, les identifiants et la file persistante sont inchangés. Conserve les thèmes clair/sombre/OLED, la barre de navigation Liquid Glass et la suppression du bandeau haut.
- Tests instrumentés de non-chevauchement et d'espacement sur Android téléphone et tablette. Aucun fichier Windows modifié.

---

## Correction des mises à jour intégrées — 0.6.12

- Dans **Paramètres → Appli → Mises à jour Android**, le bouton **Rechercher une mise à jour** affiche directement la fenêtre d'installation dans l'application si une version Android plus récente est disponible. Cela fonctionne aussi après avoir fermé la notification avec « Plus tard ».
- Un message persistant sur la carte affiche le résultat de la recherche ou une erreur de connexion, au lieu de dépendre uniquement d'un toast éphémère.
- Un contrôle déjà en cours est signalé explicitement sans annoncer par erreur que l'application est à jour.
- Le bandeau automatique reste discret et conditionnel : aucune barre « ALL DOWNLOAD » fixe n'est réintroduite.
- La vérification SHA-256, la compatibilité de signature, la confirmation d'installation Android et les dossiers de téléchargement restent inchangés. Windows n'est pas modifié.
- La 0.6.11 et la 0.6.10 officielles ont la même empreinte de signature (vérifiée dans les jobs GitHub Actions). Une APK très ancienne signée avec une autre clé peut encore nécessiter une installation manuelle.

---

## Interface épurée et paramètres unifiés — bêta 0.6.11

- **Plus de bandeau ALL-DOWNLOAD permanent au-dessus de l'accueil** : supprimé du XML et du code de l'activité, sur téléphone, tablette et pliable. Le nom et le logo de l'application restent inchangés sur le lanceur et dans les écrans système.
- La **bannière de nouvelle mise à jour** n'apparaît que si une nouvelle APK Android est disponible ; elle est intégrée au contenu, défilable, et ne réserve aucun espace au repos. Son bouton Installer, sa validation SHA-256 et la signature Android sont conservés.
- Paramètres regroupés dans **Médias / Appli / Réseau** : les cartes d'origine et les nouvelles cartes ont désormais les mêmes tuiles d'icônes vectorielles, typographies, espacements et couleurs clair/sombre/OLED.
- Les interrupteurs sont **alignés à droite**, avec titre et description à gauche, et gardent leurs préférences actuelles. Les sélecteurs et boutons sont homogènes ; cookies sous Réseau, apparence, mises à jour et moteur sous Appli.
- Aucun téléchargement, cookie, moteur, fichier média, signature ou fonctionnalité Windows n'est modifié. La refonte est limitée à Android.

---

## Fiabilisation de YouTube — bêta 0.6.10

- Sur une connexion non facturée au volume et hors économie d'énergie, le moteur yt-dlp est actualisé pour les liens YouTube et les réseaux sociaux ; fréquence limitée à une tentative toutes les 12 h et un succès tous les 7 jours.
- Sans connexion adaptée ou en cas d'échec, le moteur embarqué est conservé. Aucune actualisation forcée en données mobiles.
- Le test vidéo YouTube télécharge un extrait réel en utilisant un yt-dlp récent ; les erreurs réseau ne sont pas considérées comme une réussite.
- Les téléchargements Twitch et Windows ne sont pas modifiés.

## Interface mobile corrigée — bêta 0.6.10

- Les quatre boutons de navigation partagent réellement l'espace disponible : plus d'onglet Accueil ou Réglages tronqué sur téléphone.
- Les titres de page sont ramenés au début du défilement instantanément ; aucun ancien en-tête ne les masque.
- Le bandeau d'état « Prêt » n'occupe plus inutilement l'écran ; la progression ne se fixe au-dessus de la navigation que durant un téléchargement sur Accueil/File.
- Les sept catégories de dossiers utilisent des pictogrammes simplifiés et agrandis, avec cartes espacées et texte lisible.
- Les icônes et intitulés des commandes de la file sont alignés au lieu d'être séparés.
- Les boutons, moteurs, données, sauvegardes, thème, identité et version Windows restent inchangés.

---

Nouvelle application Android **indépendante de Windows**, dans le dossier `android/`. Les éditions Portable/Classique Windows, `yt_app.py`, `twitch_hls.py` et `build-windows.yml` ne sont pas modifiés.

## Identité verrouillée et mises à jour intégrées — bêta 0.6.9

- **Nom permanent « All-Download »** sur le lanceur Android, sans nom de test et sans modification liée au thème.
- **Logo Android d'origine conservé** dans le lanceur, le splash et les fenêtres de mise à jour ; cadrage entier, sans recadrage.
- **Aucun en-tête permanent dans l'application depuis la 0.6.11** : le haut de l'écran est réservé à la page et, seulement si nécessaire, à un avis de mise à jour.
- **Bannière de mise à jour native, dans l'esprit Kovelyx** : visible dans le contenu uniquement lorsqu'une nouvelle Release Android existe, numéro de version, notes détaillées, Installer, progression et « Plus tard ».
- Téléchargement dans le cache privé de l'application, contrôle du SHA-256 et de la signature, puis installation par le **programme d'installation Android**, sans navigateur. Android doit toujours demander la confirmation de l'utilisateur, sauf gestion privilégiée hors de cette application.
- Vérifications automatiques au retour dans l'application, avec cache HTTP et limite de fréquence pour préserver la batterie ; aucun scrutage permanent.
- Tests de non-régression pour l'absence de bandeau permanent, les quatre pages, les paramètres et la fermeture de la bannière jusqu'à une nouvelle version.
- Windows, yt-dlp, FFmpeg et Twitch sont inchangés.

## Raccourcis visibles et textes cohérents — bêta 0.6.9

- Sur téléphone et pliable de largeur limitée, les cinq raccourcis du bloc « Accès rapide » apparaissent **ensemble** sur deux rangées (3 + 2) : aucun onglet Twitch ou Playlist caché derrière un défilement horizontal.
- Tous les raccourcis utilisent la même hauteur (48 dp), des colonnes équilibrées et un espacement de 7 dp ; leurs icônes, labels et actions originales sont conservés.
- Sur les grandes tablettes (à partir de 900 dp), le bandeau reste en une seule rangée fidèle à Windows.
- Un test Android vérifie le nombre de rangées, la largeur réelle des boutons, les débordements, leur libellé et les clics Playlist/Twitch.
- Aucun fichier de la version Windows n'est modifié ; la publication APK utilise la signature permanente configurée dans GitHub.

## Cohérence des textes et placements — bêta 0.6.9

- Sur téléphone : bouton « Coller » élargi à **88 dp**, raccourcis rapides d'au moins **48 dp**, action « Ajouter » comme sur Windows et en-têtes avec icône et deux lignes possibles.
- Sur les écrans étroits ou avec une police système agrandie : onglets « Médias / Appli / Réseau » en disposition **icône au-dessus du texte**. Le contraste de l'onglet actif est mis à jour dans les deux orientations d'icône.
- Sur tablette et pliable ouvert : barre latérale conservée, avec libellés raccourcis quand la largeur ne permet pas les noms complets.
- Depuis la 0.6.11 : interrupteurs natifs à droite du libellé et de sa description, sélecteurs sur une ligne avec chevron et couleurs adaptées au thème.
- Libellés plus courts et explicites, accessibilité complète conservée via les descriptions vocales Android. Une nouvelle suite de tests vérifie les tailles, titres, icônes et alignements réels.
- Aucune modification des versions Windows, ni des moteurs de téléchargement. La publication APK exige la signature permanente déjà configurée.

## Icônes harmonisées — bêta 0.6.9

- Une seule famille de vecteurs Android 24 × 24 (formes pleines, teinte appliquée par le thème) pour navigation, formats, téléchargements, dossiers et réglages. Aucun emoji utilisé comme icône.
- Les sept catégories de dossiers ont chacune une icône dédiée. Les fichiers vidéo, audio et GIF utilisent une vignette correspondant à leur extension.
- Actions de file : reprise, pause, terminé, erreur, attente, copier, réessayer et supprimer reconnaissables même sans lire tout le texte.
- Boutons et libellés alignés avec des cibles tactiles confortables ; barre Liquid Glass conservée, logo original Windows conservé.
- Voir [ICONOGRAPHY.md](ICONOGRAPHY.md) pour le catalogue final, les tailles et les règles de cohérence.
- La Release Android exige toujours une signature permanente : consulter [SIGNING.md](SIGNING.md). Aucune clé privée n'est incluse au dépôt.
- Aucun code Windows modifié.

## Identité Windows sur Android — bêta 0.6.9

- Les quatre pictogrammes Liquid Glass de navigation, les contrôles de téléchargement et les dossiers adoptent le langage visuel **Material plein** des SVG employés dans la version Windows.
- Nouveaux pictogrammes dédiés pour les titres Nouveau lien, Options, File, Dossiers et Réglages.
- Les trois sections des réglages, leurs cartes et les boutons de mise à jour ont désormais de vrais glyphes vectoriels homogènes, teintés selon le thème.
- Pas de capture d'écran ni de flou GPU permanent ; les mêmes comportements téléphone/tablette/pliable sont conservés.
- **Signature permanente obligatoire :** les Releases Android ne basculent plus sur une APK debug en l'absence des secrets de signature. Le propriétaire doit créer et configurer les secrets expliqués dans [SIGNING.md](SIGNING.md).
- Les composants et Releases Windows ne sont pas modifiés.

## Icônes vectorielles et textes réajustés — bêta 0.6.9

- Fin des emojis et des glyphes texte comme pictogrammes. Icônes vectorielles cohérentes pour la navigation, les raccourcis, les fichiers et les téléchargements.
- Barre Liquid Glass inchangée dans son principe, mais icônes Accueil / File / Dossiers / Réglages redessinées, textes centrés et uniformes.
- Logo All-Download préservé dans le lanceur et le splash ; plus de badge ou de carte de marque en haut des pages depuis la 0.6.11.
- Icônes natives pour Télécharger, Dans la file, Coller, Reprendre, Pause, dossiers et actions de file.
- Cartes de fichiers plus régulières, textes longs tronqués sur une ligne et réglages plus lisibles.
- Tests dédiés au chargement des ressources vectorielles et au placement des boutons. Aucun fichier Windows modifié.

## Design minimaliste Liquid Glass — bêta 0.6.9

- Barre de navigation flottante, translucide, à reflet discret et capsule violette active ; rendu natif sans flou GPU continu.
- Accueil réorganisé : URL puis actions Télécharger / Dans la file sur une ligne, options et raccourcis, aperçu de la file.
- Cartes de file, explorateur de dossiers et panneaux de paramètres plus compacts et aérés.
- Quatre onglets, réglages, moteur et fonctions de téléchargement inchangés ; écrans téléphone, tablette et pliable.
- Nouveaux tests d'interface intégrés aux émulateurs Android. Aucun fichier Windows modifié.

## Interface mobile fidèle à All-Download

- **Nom et interface Windows conservés, logo d'application Android inédit :** le nouveau visuel violet combinant flèche, vidéo et monogramme AD se trouve dans `android/branding/android-launcher.jpg`. L'icône, le splash et le bandeau Android l'utilisent. Le `logo.jpg` de Windows reste intact et présent dans les ressources Android pour la cohérence visuelle.
- **Splash screen natif**, identité visuelle de Windows : violet `#7C3AED`, thème sombre `#141414`, cartes `#212121`, ainsi que les modes clair et OLED enregistrés.
- **Quatre écrans Android natifs** : Accueil (URL, vidéo/audio/GIF, qualité), File d'attente (progression et reprise), Dossiers (navigation et ouverture des médias) et Paramètres (thèmes, actualisation yt-dlp, cookies privés).
- **File de téléchargement persistante** dans les préférences privées, avec exécution séquentielle, progression, relance d'une tâche échouée et suppression des tâches terminées. Pause/reprise best-effort via `yt-dlp --continue` et espace de travail privé par tâche : certains serveurs interdisent la reprise ; dans ce cas, la tâche peut repartir du début.
- **Android 15+** : marges sécurisées sous les barres système et autour des découpes d'écran, sans décaler les autres versions d'Android.
- **Android pliable/tablette** : interface centrée et limitée en largeur sur les grands écrans, recalcul au changement d'orientation ; contrôles tactiles natifs sur petit écran.
- **Fichiers accessibles** depuis les sept dossiers de l'app : MediaStore Android 10+ et FileProvider Android 7–9, sans permission « gérer tous les fichiers ».

## Refonte de l'interface Windows sur téléphone et tablette (bêta 0.6.9)

- **Écran réellement inactif :** aucune boucle d'actualisation quand l'activité est en arrière-plan. Quand elle est visible, le rafraîchissement s'adapte (1,8 s pendant le téléchargement, 3 s dans la file, 8 s au repos) et ne redessine pas les contrôles si leur état n'a pas changé.
- **File d'attente optimisée :** les tâches restent enregistrées de façon atomique et persistante, avec un cache en mémoire et une révision. Les écritures identiques sont ignorées, la progression sur disque est regroupée et seulement 24 cartes sont affichées au départ (« Afficher plus » pour la suite). Aucun téléchargement n'est perdu si une carte n'est pas affichée.
- **Explorateur de dossiers non bloquant :** les requêtes MediaStore et les dossiers Android 7–9 sont lus sur un fil dédié, pas pendant les interactions utilisateur. Les fichiers sont affichés par séries de 50, avec un bouton pour charger la suite ; on ne construit plus toutes les cartes en même temps.
- **Moteur et réseau :** yt-dlp/FFmpeg initialisés une seule fois par service ; progression de yt-dlp et notifications limitées en fréquence. Une actualisation facultative de yt-dlp pour les réseaux sociaux est automatiquement évitée sur une connexion facturée au volume ou en mode économie d'énergie (les téléchargements demandés par l'utilisateur restent possibles).
- **Logo Android compact :** l'image Android dédiée est produite en PNG 192 × 192 pour l'interface et en PNG adaptatif 288 × 288 avec marges de sécurité Android. Les éléments Windows ne sont ni renommés ni supprimés.
- **Accueil plus proche de Windows :** aperçu léger de la file (trois tâches au maximum), accès direct à la file complète, modes rapides vidéo/audio/GIF/playlist/Twitch, collage d’URL et nettoyage ciblé des tâches échouées ou en attente.
- **Identité visuelle et commandes :** onglets de réglages **Téléchargement, Application, Réseau** fidèles à la navigation Windows, et réorganisation en barre latérale sur tablette et pliable ouvert. Seuls les réglages réellement implémentés par yt-dlp/Android sont activables.
- **Twitch :** VODs et clips Twitch enregistrés dans le dossier **TWITCH** ; les exigences de résolution native 1080p/720p des VODs sont inchangées.

Ces mesures évitent les opérations superflues et limitent les allocations pendant l'utilisation, mais **une consommation chiffrée, la stabilité sur plusieurs jours et le rendu spécifique HONOR Magic V6 exigent encore des essais sur cet appareil réel**. Des téléchargements très longs ou des conversions vidéo/audio utilisent nécessairement de la batterie et du stockage temporaire.

## Mises à jour Android dans l'application

À partir de la **bêta 0.5.0**, All-Download interroge directement l'API des **GitHub Releases** à l'ouverture (vérification limitée à une fois toutes les 30 minutes). Seules les versions publiées avec un tag `android-vX.Y.Z-beta` et un vrai fichier `All-Download-Android-X.Y.Z-beta.apk` sont retenues : **les Releases Windows ne déclenchent jamais de proposition d'APK**.

Quand une version Android plus récente existe, l'application affiche une **fenêtre native animée** avec le logo, le numéro de version, les nouveautés, « Télécharger la mise à jour » et « Plus tard ». Elle ne réaffiche pas la même fenêtre à chaque retour dans l'application ; une nouvelle version entraîne une nouvelle notification. Un interrupteur et un bouton « Rechercher une mise à jour » se trouvent dans Paramètres. Le bouton télécharge désormais directement l'APK officiel dans le cache privé de l'application, avec barre de progression et contrôle de l'empreinte SHA-256 fournie par la Release GitHub. Aucun navigateur ne s'ouvre. L'application vérifie le nom de paquet, la version et la signature avant de lancer le **programme d'installation sécurisé Android** via FileProvider. Android peut demander une autorisation « Installer des applications inconnues » pour All-Download puis une confirmation. « Plus tard » annule un téléchargement d'APK en cours ; un APK déjà vérifié reste accessible après une rotation de l'écran. Il n'y a ni installation forcée, ni contournement des protections Android, ni service tiers.

**Signature APK :** les builds de test des anciennes bêta 0.1.2 et 0.2.0 ont été signés avec des clés de débogage éphémères. Ils ne peuvent **pas** garantir une installation de mise à jour par-dessus l'ancienne version. Pour des mises à jour Android vraiment installables sans désinstallation, configurez une **clé de signature persistante et privée** via les secrets GitHub Actions `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD` ; la publication échoue volontairement s'ils sont absents, et aucune APK debug n'est publiée. **Ne commitez jamais votre keystore ou vos mots de passe.** La première transition vers la clé persistante pourra demander une désinstallation, ce qui effacera les données privées de l'appli ; les médias déjà exportés dans Téléchargements ne sont pas supprimés.

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

## Liens sociaux et comptes (bêta 0.4.0)

- Reddit, Instagram, X/Twitter, Pinterest, TikTok, Facebook (notamment Reels), Vimeo, Bluesky et Dailymotion sont traités par les extracteurs **yt-dlp** ; leur disponibilité varie selon la vidéo, les protections du site et l'adresse IP.
- Le moteur yt-dlp tente une **actualisation officielle** en début de téléchargement social (puis une fois par semaine si elle aboutit). Si le réseau échoue, un nouvel essai est possible 12 heures plus tard et l'ancienne version continue de fonctionner. **Aucun service distant All-Download** n'est nécessaire.
- Les vidéos publiques ne nécessitent pas de connexion si le site les autorise. Quand un site exige une session, **l'utilisateur peut importer volontairement un fichier Netscape `cookies.txt` issu de son propre compte autorisé** via le sélecteur de documents. Il est copié dans l'espace privé de l'appli (limite 4 Mo), utilisé par yt-dlp et peut être supprimé à tout moment. **Ne jamais envoyer ses cookies ni son fichier à une autre personne.**
- Il n'y a **pas de contournement** des restrictions d'accès et pas de garantie universelle : certaines URL Reddit nécessitent des cookies, certaines anciennes vidéos Facebook ne sont pas interprétables par yt-dlp, et certains services bloquent les adresses IP automatisées. Les liens connus en échec restent suivis par les tests et sont signalés `SKIP` avec motif lorsqu'une limitation du service est identifiée.
- La suite Android de base teste les téléchargements locaux et le stockage privé, la suite réseau teste MP4/WebM/HLS/Twitch et la suite sociale teste séparément les plateformes. Une réussite sur un lien ne garantit pas tous les liens du site.

## Limites réelles

Il s'agit d'une **bêta mobile**, pas encore de la parité fonctionnelle avec Windows. Le secours HLS Twitch indépendant de `TwitchDownloaderCLI.exe`, l'authentification Twitch avancée, les sous-titres non fournis par les plateformes, les outils Windows spécialisés, les journaux et historiques détaillés et certains réglages sont encore à porter. Les boutons de pause/reprise de la file Android utilisent les mécanismes disponibles de yt-dlp ; la reprise n'est pas garantie pour les serveurs non compatibles. TwitchDownloaderCLI Windows ne peut pas être exécuté tel quel sur Android. Certaines VOD Twitch peuvent encore échouer.

Les flux protégés/DRM, les contenus privés sans autorisation et les vidéos supprimées ne sont pas garantis. La résolution choisie correspond aux formats source, pas à une promesse de compatibilité de chaque plateforme. Le stockage Android impose un espace de travail temporaire privé avant l'export public ; aucun accès au système de fichiers racine ou permission « tous les fichiers » n'est demandé.

## Compilation

Le workflow `Build and test Android (beta)` compile et exécute les tests en mode debug **sans publier l'APK debug comme artefact téléchargeable**. Une APK utilisateur n'est distribuée que depuis les **Releases Android signées avec la clé permanente** (voir [SIGNING.md](SIGNING.md)), indépendamment des Releases Windows.

En local : Android SDK plateforme 35, JDK 17 et Gradle 8.9, puis `gradle -p android :app:assembleDebug`.

**Important :** la version 1.0 reste à valider sur des appareils physiques et différents réseaux ; les tests CI valident uniquement les parcours automatisés (YouTube, Twitch, GIF, playlists, MediaStore, annulation, orientation, arrière-plan).
