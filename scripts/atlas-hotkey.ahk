; ATLAS Hotkey Script for Windows (AutoHotkey v1)
; Summons ATLAS with the backtick (`) key
;
; Installation:
; 1. Install AutoHotkey from https://www.autohotkey.com/
; 2. Copy this file to your Windows machine
; 3. Run the script (double-click or add to startup)
;
; Usage:
; - Press ` (backtick) to summon ATLAS
; - If ATLAS window exists, it will be focused
; - If not, a new Windows Terminal window will open with ATLAS

#SingleInstance Force
#NoEnv
SetWorkingDir %A_ScriptDir%

; Configuration
ATLAS_WINDOW_TITLE := "ATLAS"
WSL_DISTRO := "Ubuntu"
ATLAS_PATH := "~/ai-workspace/atlas/scripts/atlas"

; Show startup tooltip
ToolTip, ATLAS Hotkey Active`nPress `` to summon, % A_ScreenWidth - 200, 50
SetTimer, RemoveToolTip, -3000
return

RemoveToolTip:
    ToolTip
return

; Backtick hotkey
`::
    GoSub, SummonATLAS
return

; Alternative: Win+` combo
#`::
    GoSub, SummonATLAS
return

; Ctrl+Shift+A as another alternative
^+a::
    GoSub, SummonATLAS
return

SummonATLAS:
    ; Check if ATLAS window already exists
    IfWinExist, %ATLAS_WINDOW_TITLE%
    {
        WinActivate
        WinWaitActive, %ATLAS_WINDOW_TITLE%, , 2
    }
    else
    {
        GoSub, LaunchATLAS
    }
return

LaunchATLAS:
    ; Use Windows Terminal with named window
    cmd := "wt.exe -w " . ATLAS_WINDOW_TITLE . " wsl.exe -d " . WSL_DISTRO . " " . ATLAS_PATH
    Run, %cmd%, , , pid
    if ErrorLevel
    {
        ; Fallback to cmd with wsl
        cmd := "cmd.exe /c wsl.exe -d " . WSL_DISTRO . " " . ATLAS_PATH
        Run, %cmd%
    }
return

; Tray menu
Menu, Tray, NoStandard
Menu, Tray, Add, Summon ATLAS, SummonATLAS
Menu, Tray, Add
Menu, Tray, Add, Reload Script, ReloadScript
Menu, Tray, Add, Exit, ExitScript
Menu, Tray, Default, Summon ATLAS
return

ReloadScript:
    Reload
return

ExitScript:
    ExitApp
return
