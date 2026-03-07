---
title: Hotkey Activation
description: Windows hotkey access to ATLAS
tags:
  - hotkey
  - windows
  - autohotkey
created: 2024-02-10
---

# Hotkey Activation

Summon ATLAS from anywhere with a keyboard shortcut.

---

## Overview

Press a hotkey (default: backtick `) to:
- Open ATLAS if not running
- Focus ATLAS window if already open
- Works from any Windows application

---

## Option 1: AutoHotkey (Recommended)

### Install AutoHotkey

1. Download from [autohotkey.com](https://www.autohotkey.com/)
2. Install AutoHotkey v2

### Create Hotkey Script

Save as `atlas-hotkey.ahk`:

```ahk
; ATLAS Hotkey - Press backtick to summon
`::
{
    if WinExist("ATLAS") {
        WinActivate
    } else {
        Run 'wt.exe -w ATLAS wsl.exe -d Ubuntu ~/ai-workspace/atlas/scripts/atlas'
    }
}
```

### Run on Startup

1. Press `Win + R`
2. Type `shell:startup`
3. Copy `atlas-hotkey.ahk` to this folder

---

## Option 2: Windows Terminal Quake Mode

Windows Terminal has built-in quake-style dropdown.

### Enable Quake Mode

1. Open Windows Terminal Settings
2. Go to Actions
3. Add new action:

```json
{
    "command": {
        "action": "quakeMode"
    },
    "keys": "win+`"
}
```

### Configure ATLAS Profile

Add to Windows Terminal `settings.json`:

```json
{
    "profiles": {
        "list": [
            {
                "name": "ATLAS",
                "commandline": "wsl.exe -d Ubuntu ~/ai-workspace/atlas/scripts/atlas",
                "startingDirectory": "~",
                "icon": "🤖"
            }
        ]
    }
}
```

---

## Option 3: PowerToys

Microsoft PowerToys provides keyboard manager.

### Setup

1. Install PowerToys from Microsoft Store
2. Open PowerToys Settings
3. Go to Keyboard Manager
4. Add shortcut:
   - Shortcut: `` ` `` (backtick)
   - Action: Run program
   - Program: `wt.exe -w ATLAS wsl.exe ~/ai-workspace/atlas/scripts/atlas`

---

## Customizing the Hotkey

### Change to Different Key

In `atlas-hotkey.ahk`:

```ahk
; Use F12 instead of backtick
F12::
{
    ; ... same code
}

; Use Ctrl+Space
^Space::
{
    ; ... same code
}

; Use Win+A
#a::
{
    ; ... same code
}
```

### Key Modifiers

| Symbol | Modifier |
|--------|----------|
| `^` | Ctrl |
| `!` | Alt |
| `+` | Shift |
| `#` | Win |

---

## Advanced: Voice Activation

Combine with voice for hands-free:

```ahk
; Backtick opens ATLAS in voice mode
`::
{
    if WinExist("ATLAS") {
        WinActivate
    } else {
        Run 'wt.exe -w ATLAS wsl.exe ~/ai-workspace/atlas/scripts/atlas voice'
    }
}
```

---

## Troubleshooting

> [!warning] Hotkey Not Working
> 1. Ensure AutoHotkey is running (check system tray)
> 2. Run script as Administrator if needed
> 3. Check for conflicting hotkeys

> [!warning] Wrong WSL Distro
> Change `Ubuntu` to your distro name:
> ```ahk
> Run 'wt.exe wsl.exe -d YourDistroName ...'
> ```

> [!tip] Find Distro Name
> ```powershell
> wsl --list
> ```

---

## See Also

- [[Installation]] - Initial setup
- [[Voice Interface]] - Voice mode integration

---

#hotkey #windows #autohotkey
