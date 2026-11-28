# All-Download pour Android

L’APK fonctionne sur téléphone, tablette et pliable à partir d’Android 7. Le lien de téléchargement et l’empreinte SHA-256 figurent dans le [guide principal](../README.md).

## Télécharger ou partager une vidéo

Collez un lien dans Accueil ou utilisez **Partager → All-Download** depuis une autre application. Un lien partagé remplit le champ URL. Plusieurs liens rejoignent la file. Depuis Galerie ou Fichiers, le partage de vidéos locales copie les fichiers dans le dossier VIDÉOS et conserve les originaux.

Choisissez Vidéo, Audio (MP3, M4A ou FLAC), GIF, Playlist ou Chaîne. Le raccourci Twitch accepte les VOD et les clips. Par défaut, la vidéo utilise la meilleure qualité native disponible jusqu’à 1080p. En cas d’échec de l’extracteur Twitch, l’application peut essayer le flux HLS public.

Les médias terminés se trouvent sous `Téléchargements/All-Download/`, classés par catégorie. L’application utilise temporairement son stockage privé pendant le transfert. Sur Android 7 à 9, Android peut demander une autorisation de stockage.

## Accès aux sites et mises à jour

Si un site comme Instagram exige une session, importez vos propres cookies au format Netscape dans les paramètres réseau. L’application les conserve dans son espace privé. Un lien supprimé, protégé ou inaccessible à votre compte peut échouer.

Dans **Paramètres → Appli**, vous pouvez rechercher une mise à jour. All-Download télécharge l’APK, vérifie son empreinte, son identité et sa signature, puis ouvre l’installateur Android pour confirmation.

## Compiler et tester

Avec le JDK 17, le SDK Android 35 et Gradle 8.9, lancez depuis la racine du dépôt :

```sh
gradle -p android :app:testDebugUnitTest :app:assembleDebug
```

Les tests sur émulateur et les essais de téléchargement réseau sont distincts. Pour publier une APK installable par-dessus la version distribuée, utilisez la clé permanente décrite dans le [guide de signature](SIGNING.md).
