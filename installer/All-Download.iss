#define MyAppName "All-Download"
#define MyAppExeName "All_Media_Download.exe"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

; Installe l'edition monofichier qui fonctionne sans charger Python.Runtime.dll
; depuis un dossier _internal copie ou extrait depuis Internet.
; Installation par utilisateur, sans demande de droits administrateur.

[Setup]
AppId={{6F1AA20A-8EA5-594E-9CED-32A458C29F67}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=anderson76389
AppPublisherURL=https://github.com/anderson76389/All-Download
AppSupportURL=https://github.com/anderson76389/All-Download/issues
AppUpdatesURL=https://github.com/anderson76389/All-Download/releases/latest
DefaultDirName={localappdata}\Programs\All-Download
DefaultGroupName=All-Download
PrivilegesRequired=lowest
UsePreviousAppDir=yes
OutputDir=..\dist\All-Download-Installer
OutputBaseFilename=All-Download-Setup
SetupIconFile=..\logo.ico
UninstallDisplayIcon={app}\All_Media_Download.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis"; Flags: unchecked

[Files]
Source: "..\dist\All-Download-Portable\All_Media_Download.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\logo.jpg"; DestDir: "{app}"; Flags: ignoreversion
Source: "installed.marker"; DestDir: "{app}"; DestName: ".all-download-installed"; Flags: ignoreversion
Source: "..\AUDIOS\.gitkeep"; DestDir: "{app}\AUDIOS"; Flags: ignoreversion
Source: "..\AUTRES\.gitkeep"; DestDir: "{app}\AUTRES"; Flags: ignoreversion
Source: "..\CHAÎNES\.gitkeep"; DestDir: "{app}\CHAÎNES"; Flags: ignoreversion
Source: "..\GIFS\.gitkeep"; DestDir: "{app}\GIFS"; Flags: ignoreversion
Source: "..\PLAYLIST\.gitkeep"; DestDir: "{app}\PLAYLIST"; Flags: ignoreversion
Source: "..\VIDÉOS\.gitkeep"; DestDir: "{app}\VIDÉOS"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\All-Download"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\All-Download"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer All-Download"; Flags: nowait postinstall skipifsilent
