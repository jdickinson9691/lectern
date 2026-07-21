#define MyAppName "Lectern - D&D Campaign Manager"
#define MyAppVersion "3.0.0"
#define MyAppExeName "Lectern.exe"
[Setup]
AppId={{LecternDNDCampaignManager}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\LecternDNDCampaignManager
DefaultGroupName={#MyAppName}
OutputDir=..\release
OutputBaseFilename=Lectern_v3_0_0_Setup
Compression=lzma
SolidCompression=yes
[Files]
Source: "..\dist\Lectern\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\Lectern\FantasyGrounds\LecternSync.ext"; DestDir: "{code:GetFantasyGroundsExtensionsDir}"; Flags: ignoreversion
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  FantasyGroundsExtensionsPage: TInputDirWizardPage;

procedure InitializeWizard;
begin
  FantasyGroundsExtensionsPage := CreateInputDirPage(
    wpSelectDir,
    'Fantasy Grounds Extension Folder',
    'Choose where Lectern Sync should be installed.',
    'Select the Fantasy Grounds extensions folder. In the Fantasy Grounds launcher, use the folder button to find the data folder, then choose its extensions subfolder.',
    False,
    ''
  );
  FantasyGroundsExtensionsPage.Add('Fantasy Grounds extensions folder:');
  FantasyGroundsExtensionsPage.Values[0] := ExpandConstant('{userappdata}\SmiteWorks\Fantasy Grounds\extensions');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  SelectedFolder: String;
begin
  Result := True;
  if CurPageID <> FantasyGroundsExtensionsPage.ID then
    Exit;

  SelectedFolder := Trim(FantasyGroundsExtensionsPage.Values[0]);
  if SelectedFolder = '' then
  begin
    MsgBox('Choose the Fantasy Grounds extensions folder before continuing.', mbError, MB_OK);
    Result := False;
    Exit;
  end;

  if not DirExists(SelectedFolder) then
  begin
    MsgBox(
      'The selected folder does not exist. Open Fantasy Grounds, use the launcher folder button to locate its data folder, and select the extensions subfolder.',
      mbError,
      MB_OK
    );
    Result := False;
  end;
end;

function GetFantasyGroundsExtensionsDir(Param: String): String;
begin
  Result := FantasyGroundsExtensionsPage.Values[0];
end;
