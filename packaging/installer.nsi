; =============================================================
;  朝鲜族音乐 ChaoxianzuMusic — NSIS installer script
;  Build:  makensis installer.nsi   (from this directory)
; =============================================================
Unicode true
SetCompressor /SOLID lzma

!define APPNAME "朝鲜族音乐"
!define APPFILE "ChaoxianzuMusic"
!define COMPANY  "EthnosMusic"
!define UNINSTKEY "ChaoxianzuMusic"

!include "MUI2.nsh"

!define MUI_ICON "..\assets\app.ico"
!define MUI_UNICON "..\assets\app.ico"
!define MUI_ABORTWARNING

; ------------------------------------------------------- pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APPFILE}.exe"
!define MUI_FINISHPAGE_RUN_TEXT "立即运行 ${APPNAME}"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "SimpChinese"

; ------------------------------------------------------- basic info
Name "${APPNAME}"
OutFile "..\${APPFILE}_Setup.exe"
InstallDir "$PROGRAMFILES64\${APPNAME}"
InstallDirRegKey HKLM "Software\${COMPANY}\${UNINSTKEY}" "InstallDir"
RequestExecutionLevel admin
ShowInstDetails show
ShowUnInstDetails show

Icon "..\assets\app.ico"
UninstallIcon "..\assets\app.ico"

; ------------------------------------------------------- install
Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  File /r "..\dist\${APPFILE}\*.*"

  ; user drops local audio files here
  CreateDirectory "$INSTDIR\music"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortcut  "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\${APPFILE}.exe"
  CreateShortcut  "$SMPROGRAMS\${APPNAME}\卸载 ${APPNAME}.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut  "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${APPFILE}.exe"

  WriteRegStr HKLM "Software\${COMPANY}\${UNINSTKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UNINSTKEY}" "DisplayName" "${APPNAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UNINSTKEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UNINSTKEY}" "DisplayIcon" "$INSTDIR\${APPFILE}.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UNINSTKEY}" "Publisher" "${COMPANY}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UNINSTKEY}" "NoRepair" 1
SectionEnd

; ------------------------------------------------------- uninstall
; NOTE: keeps the user's local "music" folder on disk.
Section Uninstall
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\${APPFILE}.exe"
  Delete "$INSTDIR\Uninstall.exe"

  Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
  Delete "$SMPROGRAMS\${APPNAME}\卸载 ${APPNAME}.lnk"
  RMDir  "$SMPROGRAMS\${APPNAME}"
  Delete "$DESKTOP\${APPNAME}.lnk"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UNINSTKEY}"
  DeleteRegKey HKLM "Software\${COMPANY}\${UNINSTKEY}"
  RMDir  "$INSTDIR"   ; removed only when empty -> music/ files survive
SectionEnd
