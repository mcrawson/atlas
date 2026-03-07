; ATLAS Voice Mode Hotkey (AutoHotkey v1.1)
; Press Ctrl+` to launch or focus ATLAS Voice Mode
#SingleInstance Force
#NoEnv

^`::
    IfWinExist, ATLAS Voice
        WinActivate
    else
        Run, wt.exe -w "ATLAS Voice" wsl.exe -d Ubuntu ~/ai-workspace/atlas/scripts/atlas-voice
    return
