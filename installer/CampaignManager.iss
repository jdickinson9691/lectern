#define MyAppName "Lectern - D&D Campaign Manager"
#define MyAppVersion "2.9.4"
#define MyAppExeName "Lectern.exe"
[Setup]
AppId={{LecternDNDCampaignManager}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\LecternDNDCampaignManager
DefaultGroupName={#MyAppName}
OutputDir=..\release
OutputBaseFilename=Lectern_v2_9_4_Setup
Compression=lzma
SolidCompression=yes
[Files]
Source: "..\dist\Lectern\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
