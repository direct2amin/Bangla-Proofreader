; Inno Setup Script for Bangla Proofreader
; Generates standalone setup installer with custom installation directory choice and logo branding.

#define MyAppName "Bangla Proofreader"
#define MyAppVersion "1.7.0"
#define MyAppPublisher "Amin"
#define MyAppURL "https://direct2amin.github.io/aminsweb"
#define MyAppExeName "BanglaProofreader.exe"

[Setup]
AppId={{5C1D829F-A62E-4D7A-93B4-29E7BC852891}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Allow user to select custom installation directory
DisableDirPage=no
; Allow user to select start menu folder
DisableProgramGroupPage=no
OutputDir=dist_installer
OutputBaseFilename=BanglaProofreader_Setup
SetupIconFile=assets\logo.ico
UninstallDisplayIcon={app}\assets\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
CloseApplicationsFilter=BanglaProofreader.exe,*.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\BanglaProofreader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\*"; DestDir: "{app}\app\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\logo.ico"; AppUserModelID: "amin.banglaproofreader.desktop.1.7.0"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\logo.ico"; Tasks: desktopicon; AppUserModelID: "amin.banglaproofreader.desktop.1.7.0"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Terminate any running instance of BanglaProofreader before install or uninstall
function KillRunningApp(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/f /im BanglaProofreader.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

function InitializeSetup(): Boolean;
begin
  KillRunningApp();
  Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  KillRunningApp();
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    // Clean up any stale legacy 32-bit uninstall registry entries so Control Panel displays current version accurately
    RegDeleteKeyIncludingSubkeys(HKLM, 'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{5C1D829F-A62E-4D7A-93B4-29E7BC852891}_is1');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDataDir := ExpandConstant('{userappdata}\BanglaProofreader');
    if DirExists(AppDataDir) and (not UninstallSilent()) then
    begin
      if MsgBox(
        'Do you want to KEEP your saved preferences and Gemini API Key for future installations?' + #13#10 + #13#10 +
        '• Click "Yes" to KEEP your saved API Key and settings.' + #13#10 +
        '• Click "No" to REMOVE all saved preferences and API Key permanently.',
        mbConfirmation, MB_YESNO or MB_DEFBUTTON1
      ) = IDNO then
      begin
        DelTree(AppDataDir, True, True, True);
        RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'BanglaProofreader');
      end;
    end;
  end;
end;
