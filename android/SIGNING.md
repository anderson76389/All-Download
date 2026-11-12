# Signature permanente — All-Download Android

La branche Android publie désormais **uniquement** des APK signées avec une clé privée persistante.
Sans les quatre secrets GitHub Actions ci-dessous, la publication échoue : elle ne fabrique plus de Release utilisant une clé debug générée par un runner.

## 1. Créer la clé sur votre PC (Windows)

Un JDK 17+ avec `keytool` doit être installé. Depuis la racine du dépôt dans PowerShell :

```powershell
.\android\tools\create-release-keystore.ps1
```

Ce script utilise `keytool` pour créer un fichier privé à l'emplacement :
`%USERPROFILE%\AllDownload-Android-Signing\all-download-release.p12`.

L'alias est **all-download-android**. Choisissez un mot de passe fort lors de la demande interactive de `keytool`.
Le type PKCS12 utilise ce même mot de passe pour la clé et son magasin.

**À conserver :** fichier `.p12` original, mot de passe, alias. Sauvegardez-les dans un coffre personnel sécurisé, avec une copie de secours. **Ne mettez jamais la clé, sa version Base64 ni le mot de passe dans le dépôt, une issue ou un message de chat.**

## 2. Ajouter 4 secrets au dépôt GitHub

Ouvrez [Settings → Secrets and variables → Actions](https://github.com/anderson76389/All-Download/settings/secrets/actions) puis **New repository secret**.

| Secret | Valeur |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | Contenu Base64 complet du fichier `.p12` |
| `ANDROID_KEYSTORE_PASSWORD` | Mot de passe du magasin |
| `ANDROID_KEY_ALIAS` | `all-download-android` |
| `ANDROID_KEY_PASSWORD` | Même mot de passe que le magasin (PKCS12) |

Pour copier la valeur Base64 dans le presse-papiers Windows, exécutez localement :

```powershell
$p12 = Join-Path $env:USERPROFILE "AllDownload-Android-Signing\all-download-release.p12"
[Convert]::ToBase64String([IO.File]::ReadAllBytes($p12)) | Set-Clipboard
```

Collez-la directement dans le champ du secret `ANDROID_KEYSTORE_BASE64`, enregistrez puis videz le presse-papiers.

## 3. Publier

Après la configuration, exécutez à nouveau le workflow
`Publish All-Download Android beta` pour la branche `feature/android-app`.
L'APK final doit avoir la signature privée permanente ; GitHub Actions la vérifie via `apksigner`, puis publie l'APK et son SHA-256.

**Transition :** les anciennes bêta jusqu'à 0.6.4 étaient signées avec une clé debug non persistante ; un désinstall / réinstall de l'application pourra être nécessaire **une dernière fois**. Les données privées (cookies, paramètres, file d'attente) peuvent être perdues en désinstallant ; les médias exportés dans Téléchargements restent. Ensuite, réutilisez absolument la même clé pour chaque nouvelle version.

L'installation mise à jour reste soumise à la confirmation sécurisée d'Android ; aucune installation silencieuse ni contournement des protections.
