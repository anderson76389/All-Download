# Run locally on your own Windows PC (with JDK keytool installed).
# This creates the signing key OUTSIDE the git repository.
# No passwords or private keys are printed, committed, or uploaded.
$ErrorActionPreference = "Stop"
$tool = Get-Command keytool -ErrorAction Stop
$folder = Join-Path $env:USERPROFILE "AllDownload-Android-Signing"
$key = Join-Path $folder "all-download-release.p12"
if (Test-Path -LiteralPath $key) {
    throw "Une clé existe déjà. Ne la remplacez pas : $key"
}
New-Item -ItemType Directory -Path $folder -Force | Out-Null
& $tool.Source -genkeypair -keystore $key -storetype PKCS12 `
    -alias "all-download-android" -keyalg RSA -keysize 3072 -validity 10000 `
    -dname "CN=All-Download Android, OU=Personal, O=All-Download, C=FR"
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $key)) {
    throw "Échec de création de la clé."
}
Write-Host "Clé privée créée : $key"
Write-Host "Sauvegardez le fichier et son mot de passe dans votre coffre personnel."
Write-Host "Lisez android/SIGNING.md avant de configurer les secrets GitHub."
