# All-Download Android — catalogue final des icônes

## Direction artistique

**Identité : All-Download Windows.** Utiliser le logo original de Windows, sans recadrage, et les couleurs du thème déjà disponibles. Les captures de YTDLnis servent de référence **ergonomique** : icônes simples, boutons compacts et information claire, sans réutiliser ses fichiers graphiques.

Toutes les icônes sont des **VectorDrawable natifs originaux** au format `24 × 24`, avec des formes pleines ou des contours nets monochromes et une couleur appliquée par le thème. Pas d'emoji, de police spéciale, de chargement réseau ou de filtres GPU. Le même glyphe est réutilisé partout où la fonction est identique.

## Navigation Liquid Glass

| Section | Vecteur Android | Symbole | Libellé |
| --- | --- | --- | --- |
| Accueil | `nav_home` | Maison pleine | Accueil |
| File | `nav_queue` | Liste avec tâches cochées | File |
| Dossiers | `nav_folders` | Dossier plein | Dossiers |
| Réglages | `nav_settings` | Engrenage plein | Réglages |

La barre mobile affiche l'icône au-dessus du texte, sans retour à la ligne. En tablette et pliable ouvert, l'icône passe à gauche du texte dans la colonne latérale. L'onglet actif est blanc sur fond violet ; les autres suivent le thème.

## Accueil, options et formats rapides

| Fonction | Vecteur Android | Symbolique |
| --- | --- | --- |
| Nouveau lien / Dans la file | `ic_queue_add` | Liste avec ajout |
| Options | `ic_sliders` | Curseurs de réglages |
| Télécharger | `ic_download` | Flèche de téléchargement |
| Coller | `ic_paste` | Presse-papiers |
| Vidéo | `ic_video` | Écran avec lecture |
| Audio | `ic_audio` | Casque |
| GIF | `ic_gif` | Séquence animée dans un cadre |
| Playlist | `ic_playlist` | Liste + lecture |
| Twitch | `ic_stream` | Bulle de diffusion |
| Arrêter | `ic_stop` | Carré stop |

## File de téléchargement

| Fonction / état | Vecteur Android |
| --- | --- |
| Liste complète | `nav_queue` |
| Reprendre | `ic_play` |
| Pause | `ic_pause` |
| Terminé / effacer les terminés | `ic_done` |
| Erreur / effacer les erreurs | `ic_error` |
| Attente / effacer l'attente | `ic_waiting` |
| Réessayer | `ic_retry` |
| Supprimer | `ic_trash` |
| Copier le lien | `ic_copy` |
| Voir plus / autres options | `ic_more` |

## Dossiers — sept icônes distinctes

| Dossier | Vecteur Android |
| --- | --- |
| VIDÉOS | `ic_folder_video` |
| AUDIOS | `ic_folder_audio` |
| TWITCH | `ic_folder_twitch` |
| GIFS | `ic_folder_gif` |
| CHAÎNES | `ic_folder_channel` |
| PLAYLIST | `ic_folder_playlist` |
| AUTRES | `ic_folder_other` |

Les sept dossiers utilisent des pictogrammes autonomes plus lisibles (lecture, casque, chat en direct, pellicule, chaîne, playlist et dossier). Les fichiers affichent `ic_video`, `ic_audio`, `ic_gif` ou `ic_file` selon leur extension, plus un chevron discret `ic_chevron`.

## Réglages

| Section | Vecteur Android |
| --- | --- |
| Onglet Médias / Téléchargements | `ic_video` / `ic_download` |
| Onglet Appli | `nav_settings` |
| Onglet Réseau | `ic_network` |
| Audio | `ic_audio` |
| Métadonnées et miniatures | `ic_metadata` |
| Sous-titres | `ic_subtitles` |
| SponsorBlock | `ic_security` |
| Réseau et connexions | `ic_network` |
| Application et notifications | `ic_notifications` |
| Mises à jour / rechercher | `ic_update` |

## Grille de proportions

- Source des pictogrammes : **viewport 24 × 24**.
- Barre Liquid Glass mobile : **21 dp** ; icône au-dessus du libellé.
- Barre latérale tablette : **21 dp** ; icône à gauche du libellé.
- En-têtes de sections : **19 dp**.
- Boutons principaux : **18 dp** ; formats rapides : **17 dp**.
- Icônes de dossiers : case **50 dp**, pictogramme de **32 dp** avec marge intérieure de **9 dp**. La silhouette n'est plus un double cadre avec symbole minuscule.
- Action secondaire : pictogramme **16 dp**, cible tactile **48 dp** minimum.
- Espacement icône-texte : généralement **5 à 9 dp**.
- Textes de navigation sur une ligne, labels de fichiers longs tronqués avec ellipse, sans casser l'appui tactile.
- Fond clair/sombre/OLED selon le thème. Le violet est réservé aux actions actives ou aux accents, sans animation permanente.

**Ne pas changer :** logo principal Windows, identifiants des commandes, moteurs yt-dlp/FFmpeg/Twitch, logique de file et téléchargements, structure des releases Windows. Les évolutions restent dans `android/`.

### Contrôle de visibilité

Les pictogrammes de dossiers sont **distincts, contrastés et assez grands** pour éviter les détails illisibles ; ils suivent la teinte du thème. Le test d'instrumentation `sevenFolderGlyphsRenderAsDistinctVisibleShapes` dessine réellement les sept vecteurs et vérifie qu'ils ont des pixels visibles et des silhouettes différentes.

## Correctifs d'alignement mobile (novembre 2026)

- Navigation quatre onglets à largeur égale dans un conteneur fixe sans défilement horizontal ; aucun libellé ne doit sortir du bord gauche/droit.
- En-tête de marque et bannière toujours épinglés ; changement d'onglet ramené en haut immédiatement pour ne pas cacher le titre.
- État de téléchargement épinglé **uniquement pendant un transfert actif** sur téléphone, masqué à l'arrêt et dans Dossiers/Réglages.
- Actions de la file : icône et texte alignés au début du bouton pour ne pas les séparer visuellement.
- Version Windows et moteurs Android inchangés.
