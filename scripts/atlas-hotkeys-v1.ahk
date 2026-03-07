; ATLAS Hotkeys (AutoHotkey v1.1)
; ` (backtick) = Regular ATLAS text mode
; Ctrl+Shift+V = ATLAS Voice mode
#SingleInstance Force
#NoEnv

; Backtick - Regular ATLAS
`::
    IfWinExist, ATLAS
    {
        WinActivate
    }
    else
    {
        Run, wt.exe -w ATLAS wsl.exe ~/ai-workspace/atlas/scripts/atlas
    }
    return

; Ctrl+Shift+V - ATLAS Voice Mode
^+v::
    IfWinExist, ATLAS Voice
    {
        WinActivate
    }
    else
    {
        Run, wt.exe -w "ATLAS Voice" wsl.exe ~/ai-workspace/atlas/scripts/atlas-voice
    }
    return
