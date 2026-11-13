# All-Download — plan de durabilité et de récupération

## Sauvegarde à conserver en dehors de GitHub

Garder deux copies indépendantes (disque débranché et stockage chiffré) du code
Git complet, des dernières archives Windows, Android et Linux, de leurs SHA-256
et des données de chaque appareil. GitHub ne garantit pas la conservation éternelle
des Releases ; les anciens dépôts, runners et dépendances peuvent disparaître.

**Important : une sauvegarde ZIP créée par ce script n'est PAS chiffrée.**
Ne pas la publier, l'envoyer sur GitHub ou la partager si elle contient des
paramètres personnels, des cookies ou des médias privés.

Créer une sauvegarde de tout l'historique réellement présent en local :

    git fetch --all --tags
    python scripts/offline_backup.py create --repository . --output ../all-download-source.zip
    python scripts/offline_backup.py verify ../all-download-source.zip

Le fichier .sha256 adjacent permet de détecter les altérations. Le Git bundle
contient les références Git locales réellement récupérées, pas les branches
distantes qui n'ont jamais été fetch. Il faudra toujours sauvegarder séparément
les archives binaires publiées si les outils de compilation deviennent introuvables.

En option, depuis une installation portable Windows/Linux, inclure les sept
dossiers médias et Donnees/config.json (ainsi que les éventuels cookies) :

    python scripts/offline_backup.py create --repository . --output ../all-download-prive.zip --data-root "D:/All-Download" --accept-unencrypted

Le script exclut les caches, espaces temporaires et les extensions de clés
cryptographiques courantes. Les clés de signature Android (.p12), alias,
mots de passe GitHub Actions et secrets doivent être sauvegardés **séparément
dans un coffre chiffré**, avec une procédure documentée pour leur restauration.

Restauration dans un dossier qui **n'existe pas encore**, sans réseau ni
remplacement destructeur de fichiers :

    python scripts/offline_backup.py verify ../all-download-prive.zip
    python scripts/offline_backup.py restore ../all-download-prive.zip --destination ../All-Download-Restaure

Faire un essai de restauration complet sur une autre machine au moins une fois.
Le script clone les sources localement depuis le Git bundle et restaure les
données privées exportées ; il n'installe pas les logiciels sur ton appareil.

## Vérifications avant mise à jour (3 versions)

1. Sauvegarder une installation et ses paramètres, de préférence avec plusieurs
   téléchargements de test terminés et interrompus.
2. Vérifier les fichiers .sha256 et l'origine GitHub ; sur Android vérifier la
   signature identique et le versionCode croissant.
3. Tester la transition depuis la version N-1, puis interruption du réseau,
   manque d'espace, annulation, reprise et ouverture après redémarrage.
4. Android : le système demande toujours une confirmation ; vérifier la file,
   les préférences et Téléchargements/All-Download après mise à jour.
5. Windows : vérifier les éditions Portable et Classique, conserver le dossier
   précédent jusqu'à confirmation que toutes les données sont accessibles.
6. Linux : extraire la nouvelle version à côté de l'ancienne, contrôler SHA-256,
   sauvegarder Donnees/ puis ne remplacer que les fichiers applicatifs. Les
   mises à jour Linux restent manuelles.
7. Vérifier RAM/CPU/stockage et disparition des processus après fermeture avec
   les scripts de diagnostic existants. Comparer repos, activité et fermeture.

## Maintenir sans casser

- Les contrôles de dépendances sont manuels avant chaque Release et les PR doivent être validées,
  **jamais une fusion automatique** des nouvelles bibliothèques.
- Après changement de yt-dlp/FFmpeg, exécuter les tests des sites, des formats
  Twitch 1080p/720p natifs et de conversion, avec rollback prévu.
- N'exécuter les suites coûteuses d'émulateurs Android que sur modification
  pertinente, pas en boucle sans besoin.
- Conserver tes quatre premières et quatre dernières Releases comme demandé,
  et archiver les versions de secours hors de GitHub avant une suppression.
- Les empreintes SHA-256 détectent les altérations ; elles ne remplacent pas
  une signature d'éditeur ni ne protègent d'une compromission de GitHub.
- Les protections contre les changements de YouTube/Twitch nécessitent de la
  maintenance future ; aucune application n'a de compatibilité garantie à vie.

## Vérifications complémentaires après la sortie stable 1.0

La 1.0 peut être publiée après les suites automatisées Windows/Android/Linux et les
vérifications de signature/intégrité. **Stable ne veut pas dire vérifiée sur chaque
appareil ni sur chaque site distant.** La validation N-1 → N sur un HONOR Magic V6,
les tests d'endurance RAM/CPU/batterie et une restauration complète sur machine
physique doivent être documentés séparément dans l'issue #60 ; ils ne sont pas
attestés par les émulateurs.

Avant toute mise à jour risquée, conserver une version de secours, les données
portables et la clé Android dans un coffre chiffré. Les sites tiers évoluent :
leur compatibilité ne peut pas être garantie à vie.

## Vérifier une archive téléchargée sans réseau

Conserver l'archive de Release et son fichier .sha256 au même endroit.

    python scripts/verify_release_asset.py All-Download-Portable-Windows.zip
    python scripts/verify_release_asset.py All-Download-Android-1.0.0.apk
    python scripts/verify_release_asset.py All-Download-Linux-x86_64.tar.xz

Le contrôle refuse les fichiers altérés, les checksums associés à un autre nom et
les lignes de checksum anormalement volumineuses. Une empreinte fournie par le
même serveur compromis que le binaire ne garantit pas à elle seule l'identité
de l'éditeur : vérifier aussi les signatures Android et la provenance des builds.

## Surveillance légère des dépendances

Un seul workflow GitHub Actions hebdomadaire lit les métadonnées des trois
projets amont officiels : yt-dlp, FFmpeg-Builds, TwitchDownloader.
Aucun téléchargement de média, aucune compilation, aucune PR automatique et
aucune mise à jour silencieuse. Les versions sont affichées dans le résumé
GitHub Actions et doivent être examinées humainement. La surveillance est
conditionnée à la disponibilité de GitHub Actions.
