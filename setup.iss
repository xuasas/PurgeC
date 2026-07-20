; PurgeC 安装脚本 — Inno Setup 6
; 生成单文件安装程序，支持自定义安装目录

#define MyAppName "PurgeC"
#define MyAppVersion "1.0"
#define MyAppPublisher "PurgeC"
#define MyAppExeName "PurgeC.exe"
#define MySourceDir "dist\PurgeC"

[Setup]
AppId={{B8F4A3D2-7E1C-4A9F-8D5B-2C6E0F1A9D3E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName=D:\Program Files\PurgeC
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=PurgeC_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; 因为程序需要管理员权限做清理，安装也要求管理员
PrivilegesRequired=admin
; 64位安装
ArchitecturesInstallIn64BitMode=x64compatible

; 语言使用默认英文（该版本不含中文语言包）

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "额外快捷方式:"

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 PurgeC"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 PurgeC"; Flags: nowait postinstall skipifsilent
