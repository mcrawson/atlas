; ATLAS Hotkey Script for Windows (AutoHotkey v1.1)
; Summons ATLAS with the backtick (`) key
;
; Press ` (backtick) to summon ATLAS

#SingleInstance Force
#NoEnv
SetWorkingDir %A_ScriptDir%

; Configuration
WSL_DISTRO := "Ubuntu"
ATLAS_PATH := "~/ai-workspace/atlas/scripts/atlas"
ATLAS_WINDOW_TITLE := "ATLAS"

; Backtick hotkey
`::
    SummonATLAS()
    return

; Win+` alternative
#`::
    SummonATLAS()
    return

; Ctrl+Shift+A alternative
^+a::
    SummonATLAS()
    return

SummonATLAS() {
    global ATLAS_WINDOW_TITLE, WSL_DISTRO, ATLAS_PATH

    ; Check if ATLAS window exists
    IfWinExist, %ATLAS_WINDOW_TITLE%
    {
        WinActivate
    }
    else
    {
        ; Launch Windows Terminal with ATLAS
        Run, wt.exe -w %ATLAS_WINDOW_TITLE% wsl.exe -d %WSL_DISTRO% %ATLAS_PATH%
    }
}

; Show tooltip on startup
ToolTip, ATLAS Hotkey Active`nPress ` to summon, % A_ScreenWidth - 250, 50
SetTimer, RemoveToolTip, -3000
return

RemoveToolTip:
    ToolTip
    return
