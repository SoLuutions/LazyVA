; ==============================================================================
; LazyVA Windows Inno Setup Installer Script
; Compiles to: LazyVA_Setup_v1.0.0.exe
; ==============================================================================

#define MyAppName "LazyVA"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "LazyVA Software"
#define MyAppURL "https://lazyva.app"
#define MyAppExeName "LazyVA.exe"

[Setup]
; App Identity
AppId={{5D8B4E12-7F3A-4C91-92A1-F9D82E0B6471}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Non-admin install into local AppData so users without Administrator rights can install it
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output file settings
OutputDir=..\dist
OutputBaseFilename=LazyVA_Setup_v{#MyAppVersion}
SetupIconFile=..\assets\icon_night.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Silent upgrade support for auto-updater
CloseApplications=yes
RestartApplications=no
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Launch LazyVA automatically on Windows Startup"; GroupDescription: "Windows Integration:"

[Files]
; Copy all files produced by PyInstaller directory build
Source: "..\dist\LazyVA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\assets\icon.ico"

[Registry]
; Run on Windows startup if user selected the task
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
