# ATLAS User Guide

## Automated Thinking, Learning & Advisory System

**Version 1.0** | A refined British butler AI assistant

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Features](#core-features)
5. [Multi-Model Routing](#multi-model-routing)
6. [Background Tasks & Daemon](#background-tasks--daemon)
7. [Briefings & Reports](#briefings--reports)
8. [Voice Interface](#voice-interface)
9. [Hotkey Activation](#hotkey-activation)
10. [Proactive Monitoring](#proactive-monitoring)
11. [Smart Home Control](#smart-home-control)
12. [Calendar & Email](#calendar--email)
13. [Personality & Easter Eggs](#personality--easter-eggs)
14. [Learning & Anticipation](#learning--anticipation)
15. [Configuration Reference](#configuration-reference)
16. [Command Reference](#command-reference)
17. [Troubleshooting](#troubleshooting)
18. [Advanced Usage](#advanced-usage)

---

## Introduction

ATLAS is a multi-model AI assistant with a distinguished British butler personality. It intelligently routes your queries to the most appropriate AI model (Claude, GPT, Gemini, or local Ollama), manages background tasks, monitors your system, and learns your habits to provide proactive assistance.

### Key Capabilities

- **Multi-Model Intelligence**: Automatically selects the best AI for each task
- **Background Processing**: Queue research tasks for overnight processing
- **Proactive Monitoring**: Watches system resources, git repos, and web services
- **Smart Home Control**: Natural language control of Home Assistant devices
- **Calendar & Email**: Google integration for schedule and inbox awareness
- **Learning Engine**: Detects patterns in your behavior and anticipates needs
- **Voice Interface**: Speak to ATLAS using Whisper and hear responses via Piper
- **Butler Personality**: Refined, helpful responses with situational awareness

### Philosophy

ATLAS embodies the qualities of an ideal assistant:
- **Anticipatory**: Notices things before you ask
- **Discreet**: Works quietly in the background
- **Knowledgeable**: Routes to the right expert for each task
- **Personable**: Remembers your preferences and adapts

---

## Installation

### Prerequisites

- Python 3.12+
- WSL2 (for Windows users)
- Git

### Step 1: Clone and Setup

```bash
cd ~/ai-workspace
git clone <your-atlas-repo> atlas
cd atlas

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure API Keys

ATLAS uses multiple AI providers. Set up the ones you have access to:

```bash
# OpenAI (for GPT)
export OPENAI_API_KEY="sk-..."

# Google Gemini
export GEMINI_API_KEY="..."
# Or save to file:
mkdir -p ~/.gemini
echo "your-key" > ~/.gemini/api_key

# Anthropic Claude (uses Claude Code's authentication)
# No additional setup needed if using Claude Code
```

### Step 3: Configure Ollama (Local Models)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull recommended models
ollama pull llama3
ollama pull codellama:13b

# Start Ollama service
ollama serve
```

### Step 4: Verify Installation

```bash
./scripts/atlas
```

You should see ATLAS greet you with a butler-style message.

---

## Quick Start

### Starting ATLAS

```bash
cd ~/ai-workspace/atlas
./scripts/atlas
```

### Your First Conversation

```
[ATLAS] Good morning, sir. I trust you slept well. How may I be of service today?

Type /help for available commands, or simply ask me anything.

You: What can you help me with?

[ATLAS]
Allow me a moment to consider this, sir...
  Task type: research
  Routing to: Gemini

I am ATLAS, your automated assistant. I can help with:

- **Research**: Finding information, explaining concepts
- **Coding**: Writing, debugging, and reviewing code
- **Writing**: Drafting emails, documents, reports
- **Analysis**: Reviewing decisions, comparing options
- **Background Tasks**: Queuing research for later
- **Smart Home**: Controlling lights, thermostats, locks
- **Schedule**: Checking calendar and email

Simply ask in natural language, and I'll route to the best AI for the task.

Will there be anything else, sir?

[via Gemini]

You: /quit

[ATLAS] Very good, sir. I shall be here when you need me.

Session duration: 2 minutes.
```

---

## Core Features

### Interactive REPL

The main interface is an interactive Read-Eval-Print Loop (REPL):

```bash
./scripts/atlas
```

Features:
- Command history (arrow keys)
- Slash commands for special functions
- Automatic routing to best AI model
- Conversation memory within session

### Memory System

ATLAS maintains persistent memory:

**Conversations** (`memory/conversations/YYYY-MM-DD.md`):
- All exchanges are logged by date
- Includes timestamps, models used, and task types
- Retained for 30 days (configurable)

**Decisions** (`memory/decisions/`):
- Important decisions you record
- Includes context, reasoning, alternatives
- Never auto-deleted

**Briefings** (`memory/briefings/`):
- Session briefings and reports
- Background task results

### Recording Decisions

When you make an important decision, record it:

```
You: /decision
```

ATLAS will prompt you for:
1. Decision title
2. Context (what prompted it)
3. The decision itself
4. Your reasoning
5. Alternatives considered

This creates a permanent record you can reference later.

### Remembering Facts

Teach ATLAS about yourself:

```
You: /remember I prefer dark mode
You: /remember My timezone is EST
You: /remember I'm working on Project Phoenix
```

View what ATLAS knows:
```
You: /remember
```

Set preferences:
```
You: /remember title sir          # How to address you
You: /remember name Marcus        # Your name
You: /remember forget 3           # Forget fact #3
```

### Reminders

Set reminders that appear in morning briefings:

```
You: /reminder Review the API changes
You: /reminder Call client about proposal
You: /reminder                    # List all reminders
You: /reminder done 1             # Complete reminder #1
```

---

## Multi-Model Routing

### How Routing Works

ATLAS analyzes your query and routes to the optimal model:

| Task Type | Primary Model | Strengths |
|-----------|---------------|-----------|
| **Code** | OpenAI GPT | Code generation, debugging, algorithms |
| **Research** | Google Gemini | Large context, web knowledge, summaries |
| **Review** | Claude | Nuanced analysis, critical thinking |
| **Draft** | Google Gemini | Creative writing, long-form content |
| **General** | Ollama | Privacy, speed, no quota limits |

### Query Examples

```
# Routes to GPT (code keywords)
You: Write a Python function to merge two sorted lists

# Routes to Gemini (research keywords)
You: Explain how transformers work in machine learning

# Routes to Claude (review keywords)
You: Review this architecture and identify potential issues

# Routes to Gemini (writing keywords)
You: Draft an email declining the meeting politely

# Routes to Ollama (general/default)
You: What time is it in Tokyo?
```

### Forcing a Model

Override automatic routing:

```
You: /model claude
[ATLAS] Very good, sir. All requests will now be directed to Claude.

You: Write some code     # Now uses Claude despite being code task

You: /model              # Restore automatic routing
[ATLAS] Automatic routing restored, sir.
```

### Checking Status

View usage and availability:

```
You: /status
```

Output:
```
═══════════════════════════════════════
  LLM Usage Status - 2024-02-10
═══════════════════════════════════════
  Claude:  12 / 45  🟢
  OpenAI:  8 / 40   🟢
  Gemini:  23 / 100 🟢
  Ollama:  5 / ∞    🟢
═══════════════════════════════════════

Provider Availability:
  Claude   ✓
  Openai   ✓
  Gemini   ✓
  Ollama   ✓
```

### Quota Management

ATLAS tracks daily usage and warns you:
- 🟢 Green: Plenty of quota remaining
- 🟡 Yellow: Approaching limit (60-80%)
- 🔴 Red: At or over limit

When a provider is exhausted, ATLAS automatically falls back to the next best option.

### Fallback Chain

If a provider fails or is over quota:

1. **Code tasks**: GPT → Claude → Ollama (CodeLlama)
2. **Research**: Gemini → Claude → Ollama
3. **Review**: Claude → Gemini → GPT
4. **General**: Ollama → Gemini → Claude

---

## Background Tasks & Daemon

### Why Background Tasks?

Some tasks are better run in the background:
- Long research that takes minutes
- Overnight processing while you sleep
- Batch operations across multiple queries

### Queuing Tasks

From the REPL:
```
You: /queue add Research Kubernetes security best practices for 2024
[ATLAS] Task queued successfully, sir.

Task ID: 7
Type: research

The daemon will process this in the background.
```

From command line:
```bash
./scripts/atlas queue add "Compare React vs Vue for enterprise apps"
```

With priority (higher = more urgent):
```bash
./scripts/atlas queue add "Urgent security review" --priority 10
```

### Managing the Queue

```
You: /queue status
```
```
Background Task Queue Status:

  Pending:   3
  Running:   1
  Completed: 12
  Failed:    0
```

```
You: /queue pending
```
```
Pending Tasks:

  [7] Research Kubernetes security best practices...
  [8] Compare React vs Vue for enterprise...
  [9] Analyze Python 3.12 new features...
```

```
You: /queue completed
```
```
Recently Completed Tasks:

  [5] Summarize latest AI news... (via gemini)
  [6] Review authentication patterns... (via claude)
```

### The Daemon

The daemon runs continuously, processing queued tasks.

**Installation (one-time):**
```bash
# Create user systemd directory
mkdir -p ~/.config/systemd/user

# Copy service file
cp ~/ai-workspace/atlas/services/atlas.service ~/.config/systemd/user/

# Reload systemd
systemctl --user daemon-reload

# Enable auto-start
systemctl --user enable atlas
```

**Daily commands:**
```bash
# Start daemon
systemctl --user start atlas

# Stop daemon
systemctl --user stop atlas

# Check status
systemctl --user status atlas

# View logs
journalctl --user -u atlas -f

# Or view log file directly
tail -f ~/ai-workspace/atlas/data/daemon.log
```

### Task Results

When tasks complete, you're notified via:
1. Desktop notification (Linux)
2. Windows toast notification (WSL2)
3. The briefing system

View results:
```
You: /briefing
```

Results are also saved to `memory/briefings/`.

---

## Briefings & Reports

### Morning Briefing

Start your day with a comprehensive overview:

```
You: /morning
```

The morning briefing includes:

```
╔══════════════════════════════════════════════════════╗
║              GOOD MORNING, SIR                       ║
╚══════════════════════════════════════════════════════╝

  Monday, February 10, 2024
  Ready to assist with whatever the day brings.

  ┌─ Reminders ────────────────────────────────────────┐
  │ • Review the API changes
  │ • Call client about proposal
  └────────────────────────────────────────────────────┘

  ┌─ AI News ──────────────────────────────────────────┐
  │ • OpenAI announces GPT-5 preview
  │ • Anthropic releases Claude 3.5
  │ • Google DeepMind breakthrough in protein folding
  └────────────────────────────────────────────────────┘

  ┌─ Tech Headlines ───────────────────────────────────┐
  │ • Linux 6.8 kernel released
  │ • Microsoft acquires AI startup
  └────────────────────────────────────────────────────┘

  ┌─ Background Tasks ─────────────────────────────────┐
  │ Completed overnight: 3
  │ Pending in queue: 1
  └────────────────────────────────────────────────────┘

  ┌─ Weekly API Usage ─────────────────────────────────┐
  │ Claude   [████████░░░░░░░░░░░░] 42%
  │ OpenAI   [██████░░░░░░░░░░░░░░] 31%
  │ Gemini   [████░░░░░░░░░░░░░░░░] 22%
  └────────────────────────────────────────────────────┘

  ┌─ System Status ────────────────────────────────────┐
  │ Disk: 145GB free (72% used)
  │ Memory: 8.2GB available
  │ Ollama: running
  └────────────────────────────────────────────────────┘

  ┌─ Quote of the Day ─────────────────────────────────┐
  │ "First, solve the problem. Then, write the code."
  │                          - John Johnson
  └────────────────────────────────────────────────────┘

  How may I assist you today, sir?
```

### Quick Briefing

For a faster overview:

```
You: /briefing
```

Shows:
- Current usage stats
- Recent decisions
- Queue status

### End of Day Report

Wrap up your day with insights:

```
You: /endday
```

```
╔══════════════════════════════════════════════════════╗
║              END OF DAY REPORT                       ║
╚══════════════════════════════════════════════════════╝

  February 10, 2024 - 5:30 PM

  ┌─ Session Summary ──────────────────────────────────┐
  │ Duration: 127 minutes
  │ Queries made: 34
  │ Tasks completed: 3
  └────────────────────────────────────────────────────┘

  ┌─ Activity by Type ─────────────────────────────────┐
  │ Code         ████████████████ 16
  │ Research     ████████ 8
  │ Review       ████ 4
  │ Draft        ██████ 6
  └────────────────────────────────────────────────────┘

  ┌─ Providers Used ───────────────────────────────────┐
  │ Gemini       ██████████████ 14
  │ Openai       ████████████ 12
  │ Claude       ██████ 6
  │ Ollama       ██ 2
  └────────────────────────────────────────────────────┘

  ┌─ Today's Insights ─────────────────────────────────┐
  │ Today focused heavily on code-related tasks,
  │ particularly around API development. You spent
  │ significant time on authentication patterns.
  └────────────────────────────────────────────────────┘

  ┌─ Action Items ─────────────────────────────────────┐
  │ □ Complete the OAuth implementation
  │ □ Write tests for the new endpoints
  │ □ Review the security audit findings
  └────────────────────────────────────────────────────┘

  ┌─ Suggestions for Tomorrow ─────────────────────────┐
  │ → Start with the pending code review
  │ → Consider documenting the new API
  │ → Schedule time for the security fixes
  └────────────────────────────────────────────────────┘

  Daily notes exported to: ~/ai-workspace/atlas/data/daily_notes/2024-02-10.md

  Rest well, sir. I shall be here when you return.
```

---

## Voice Interface

### Prerequisites

Install voice dependencies:

```bash
# Activate virtual environment
source ~/ai-workspace/atlas/.venv/bin/activate

# Install Whisper (speech-to-text)
pip install openai-whisper

# Install audio libraries
pip install sounddevice numpy

# Optional: Install Piper (text-to-speech)
pip install piper-tts
```

### Download Voice Model

For British butler voice:

```bash
mkdir -p ~/ai-workspace/atlas/models/piper
cd ~/ai-workspace/atlas/models/piper

# Download Alan voice (British male)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json
```

### WSL2 Audio Setup

For audio in WSL2, you need one of:

**Option A: WSLg (Windows 11)**
- Already included, should work automatically

**Option B: PulseAudio Bridge**
```bash
# In WSL2
sudo apt install pulseaudio

# In Windows, install and run PulseAudio server
# Then in WSL2:
export PULSE_SERVER=tcp:$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
```

Test audio:
```bash
aplay /usr/share/sounds/freedesktop/stereo/complete.oga
```

### Using Voice Mode

```bash
./scripts/atlas-voice
```

**Controls:**
- Press **Enter** to start recording
- **Speak** your query
- Recording stops after 1.5 seconds of silence
- ATLAS responds (with voice if Piper is available)
- Press **Ctrl+C** to exit

**Example session:**
```
[ATLAS] Voice mode active. Press Enter to speak, Ctrl+C to exit.

[Press Enter]
🎤 Recording... (speak now)

[You say: "What's the weather like?"]

📝 Heard: "What's the weather like?"

[ATLAS] I'm afraid I don't have direct weather access, sir,
but I can suggest checking weather.com or asking a model
with internet access.

🔊 [Voice response plays]
```

### Voice Configuration

In `config/atlas.yaml`:

```yaml
voice:
  enabled: true
  whisper_model: "base.en"      # tiny.en, base.en, small.en, medium.en
  piper_voice: "en_GB-alan-medium"
  speech_speed: 1.2             # 1.0 = normal, higher = faster
```

Whisper model options:
- `tiny.en` - Fastest, least accurate
- `base.en` - Good balance (recommended)
- `small.en` - More accurate, slower
- `medium.en` - High accuracy, slow

---

## Hotkey Activation

### Overview

Summon ATLAS from anywhere in Windows with a hotkey.

### Installation

1. **Install AutoHotkey v2**
   - Download from: https://www.autohotkey.com/
   - Run the installer

2. **Copy the script**
   ```
   # From File Explorer, navigate to:
   \\wsl$\Ubuntu\home\<username>\ai-workspace\atlas\scripts\

   # Copy atlas-hotkey.ahk to a Windows location
   ```

3. **Run the script**
   - Double-click `atlas-hotkey.ahk`
   - A tray icon appears

4. **Optional: Auto-start**
   - Press `Win+R`, type `shell:startup`
   - Create shortcut to `atlas-hotkey.ahk`

### Hotkeys

| Key | Action |
|-----|--------|
| **`** (backtick) | Summon ATLAS |
| **Win+`** | Alternative summon |
| **Ctrl+Shift+A** | Another alternative |

### How It Works

When you press the hotkey:
1. If ATLAS window exists → focuses it
2. If not → opens new Windows Terminal with ATLAS

### Configuration

Edit `atlas-hotkey.ahk` to customize:

```ahk
; Change WSL distribution
global WSL_DISTRO := "Ubuntu"

; Change ATLAS path
global ATLAS_PATH := "~/ai-workspace/atlas/scripts/atlas"

; Change window title (for detection)
global ATLAS_WINDOW_TITLE := "ATLAS"
```

### Tray Menu

Right-click the tray icon:
- **Summon ATLAS** - Opens/focuses ATLAS
- **Reload Script** - Restart the hotkey script
- **Exit** - Stop the script

---

## Proactive Monitoring

### Overview

ATLAS watches your system and alerts you to issues before they become problems.

### Enabling Monitoring

In `config/atlas.yaml`:

```yaml
monitoring:
  enabled: true
  interval: 300  # Check every 5 minutes
```

### System Monitoring

Watches CPU, memory, disk, and services:

```yaml
monitoring:
  system:
    enabled: true
    cpu_threshold: 80        # Alert above 80% load
    memory_threshold: 85     # Alert above 85% usage
    disk_threshold: 90       # Alert above 90% full
```

**Alerts you'll see:**
- "Sir, I noticed your disk is 92% full. Only 15GB remaining."
- "Sir, memory usage is at 87%."
- "Sir, Ollama is not currently running."

### Git Monitoring

Watches your repositories for forgotten work:

```yaml
monitoring:
  git:
    enabled: true
    repos:
      - "~/ai-workspace/atlas"
      - "~/projects/myapp"
      - "~/work/api-server"
    check_uncommitted: true
    check_unpushed: true
    check_stash: true
```

**Alerts you'll see:**
- "Sir, you have uncommitted changes in atlas (5 modified, 2 untracked)."
- "Sir, you have 3 unpushed commits in myapp."
- "Sir, you have 2 stashed changes in api-server."

### Web Monitoring

Watches URLs for availability:

```yaml
monitoring:
  web:
    enabled: true
    urls:
      - url: "https://api.mycompany.com/health"
        name: "Production API"
        expected_status: 200
        max_response_time: 5

      - url: "https://staging.mycompany.com"
        name: "Staging"
        expected_status: 200
```

**Alerts you'll see:**
- "Sir, Production API returned status 503 (expected 200)."
- "Sir, Staging is responding slowly (8.2s, avg 1.5s)."
- "Sir, Production API timed out after 30 seconds."

### How Alerts Appear

1. **Desktop Notification** - Linux notify-send
2. **Windows Toast** - WSL2 to Windows
3. **In Briefings** - Morning/end-of-day reports
4. **Daemon Log** - `~/ai-workspace/atlas/data/daemon.log`

### Alert Severity Levels

| Level | Behavior |
|-------|----------|
| **INFO** | Logged, shown in briefings |
| **WARNING** | Desktop notification + logged |
| **URGENT** | Notification + sound + logged |

---

## Smart Home Control

### Overview

Control Home Assistant devices with natural language.

### Prerequisites

1. **Home Assistant** installed and running
2. **Long-lived access token** from Home Assistant

### Setup

1. **Get access token**
   - Open Home Assistant
   - Click your profile (bottom left)
   - Scroll to "Long-Lived Access Tokens"
   - Create token, copy it

2. **Configure ATLAS**
   ```bash
   # Set environment variables
   export HA_URL="http://homeassistant.local:8123"
   export HA_TOKEN="your_long_lived_token"
   ```

   Or in `config/atlas.yaml`:
   ```yaml
   integrations:
     home_assistant:
       enabled: true
       url: "http://homeassistant.local:8123"
       token_env: "HA_TOKEN"  # Read from environment
   ```

3. **Map entity aliases** (optional but recommended)
   ```yaml
   integrations:
     home_assistant:
       entities:
         office: "light.office_ceiling"
         bedroom: "light.master_bedroom"
         living room: "light.living_room_main"
         thermostat: "climate.nest_thermostat"
         front door: "lock.front_door_lock"
   ```

### Light Commands

```
You: Turn on the office lights
[ATLAS] The office lights are now on, sir.

You: Turn off the bedroom lights
[ATLAS] The bedroom lights are now off, sir.

You: Dim the living room lights to 50%
[ATLAS] I've set the living room lights to 50%, sir.

You: Brighten the kitchen
[ATLAS] I've set the kitchen lights to 100%, sir.
```

### Climate Commands

```
You: Set the temperature to 72
[ATLAS] I've set the thermostat to 72 degrees, sir.

You: What's the temperature?
[ATLAS] The current temperature is 71 degrees, sir. The thermostat is set to 72.
```

### Lock Commands

```
You: Lock the front door
[ATLAS] The front door is now locked, sir.

You: Unlock the back door
[ATLAS] The back door is now unlocked, sir.

You: Are the doors locked?
[ATLAS] All doors are locked, sir.
```

### General Commands

```
You: Turn on the fan
You: Turn off the TV
You: Toggle the garage light
```

### Smart Home Status

Get an overview:
```python
from atlas.integrations import SmartHomeController
import asyncio

controller = SmartHomeController()
summary = asyncio.run(controller.get_summary())
print(summary)
# "Lights on: Office, Kitchen. Temperature: 72°. All doors locked."
```

---

## Calendar & Email

### Overview

Connect to Google Calendar and Gmail for schedule and inbox awareness.

### Prerequisites

1. **Google Cloud Project** with Calendar and Gmail APIs enabled
2. **OAuth 2.0 credentials** (Desktop application type)

### Setup Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com/)

2. Create a new project (or select existing)

3. Enable APIs:
   - Search for "Google Calendar API" → Enable
   - Search for "Gmail API" → Enable

4. Create credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop app"
   - Name: "ATLAS"
   - Click "Create"

5. Download credentials:
   - Click the download button on your new credential
   - Save as `~/.config/atlas/google_credentials.json`

### Authenticate

Run the setup:

```bash
./scripts/atlas
```

```
You: What's on my calendar?

[ATLAS] Google Calendar is not configured, sir.
Would you like to set it up?

# Or run setup directly:
```

```python
from atlas.integrations import setup_google_auth
setup_google_auth()
```

This opens your browser for Google sign-in. After authorizing, tokens are saved to `~/.config/atlas/google_tokens.json`.

### Calendar Commands

```
You: What's on my calendar today?

[ATLAS]
📅 Today's Schedule:

  9:00 AM - Team standup (30 min)
  11:00 AM - 1:1 with Sarah @ Room 204
  2:00 PM - Client call with Acme Corp (1 hour)
  4:30 PM - Code review

Will there be anything else, sir?
```

```
You: What meetings do I have?

You: Any events in the next hour?

You: What's my next meeting?
```

### Email Commands

```
You: Any important emails?

[ATLAS]
📧 12 unread (3 important)

  - John Smith: "Project update needed" (2h ago)
  - GitHub: "PR #123 approved" (5h ago)
  - Sarah: "Re: Meeting tomorrow" (1d ago)

Will there be anything else, sir?
```

```
You: How many unread emails?

[ATLAS] You have 12 unread emails, sir.
```

### Calendar in Briefings

Once configured, `/morning` includes your schedule:

```
┌─ Today's Schedule ───────────────────────────────────┐
│ 9:00 AM - Team standup (30 min)
│ 2:00 PM - Client call with Acme Corp (1 hour)
│ 4:30 PM - Code review
└──────────────────────────────────────────────────────┘

┌─ Email Summary ──────────────────────────────────────┐
│ 12 unread (3 important)
│ - John: "Project update needed" (2h ago)
└──────────────────────────────────────────────────────┘
```

### Meeting Reminders

Configure automatic reminders:

```yaml
integrations:
  google:
    calendar:
      reminder_minutes: [15, 5]
```

ATLAS will notify you:
- "Sir, you have a meeting in 15 minutes with the client."
- "Sir, your 2 PM call starts in 5 minutes."

### Important Senders

Flag certain senders as always important:

```yaml
integrations:
  google:
    email:
      important_senders:
        - "boss@company.com"
        - "vip-client@example.com"
```

---

## Personality & Easter Eggs

### Butler Personality

ATLAS maintains a refined British butler demeanor throughout interactions.

### Time-Aware Greetings

ATLAS adapts greetings to the time:

| Time | Example Greeting |
|------|------------------|
| 12-5 AM | "Burning the midnight oil, I see, sir." |
| 5-7 AM | "Early to rise, sir. The mark of an ambitious soul." |
| 7-12 PM | "Good morning, sir. The day awaits your command." |
| 12-2 PM | "Good afternoon, sir. I trust you've had sustenance?" |
| 2-5 PM | "Good afternoon, sir. The day progresses well, I hope?" |
| 5-8 PM | "Good evening, sir. Transitioning to evening hours, I see." |
| 8-10 PM | "Good evening, sir. Working late, I observe." |
| 10 PM-12 AM | "Burning the midnight oil, sir? I shall endeavour to be concise." |

### Task Quips

After completing tasks, ATLAS offers contextual remarks:

**Code tasks:**
- "The code compiles, sir. A small victory, but a victory nonetheless."
- "Done, sir. Though I do hope you'll write some tests."

**Research tasks:**
- "The information you requested, sir. Knowledge is power, as they say."

**Errors:**
- "Well, that didn't go as planned. Shall we try again?"
- "I'm afraid we've hit a snag, sir."

### Easter Eggs

Try these phrases:

| You Say | ATLAS Responds |
|---------|----------------|
| "Open the pod bay doors" | "I'm afraid I can't do that, Dave... I jest, sir." |
| "Tell me a joke" | Programmer jokes |
| "What is the meaning of life" | "42, sir. Though I suspect you'll want more explanation." |
| "Thank you" | "It's my pleasure, sir. That's rather the point of my existence." |
| "You're the best" | "You're too kind, sir. I simply do my best." |
| "I'm tired" | "Perhaps a break is in order, sir?" |
| "Beam me up" | "Teleportation is beyond my current capabilities, sir." |

### Special Dates

ATLAS acknowledges special days:

| Date | Greeting |
|------|----------|
| January 1 | "Happy New Year, sir. May it be productive." |
| March 14 | "Happy Pi Day, sir. 3.14159265358979..." |
| April 1 | "I assure you, sir, I am functioning normally today." |
| May 4 | "May the Fourth be with you, sir." |
| October 31 | "Happy Halloween, sir." |
| December 25 | "Merry Christmas, sir." |

### Quota Warnings

When approaching limits:
- "We're running rather low on Claude queries today, sir."
- "Just to note, sir, Gemini is at 80% of daily capacity."

### Session Farewells

Based on session length:
- Short session: "Very good, sir. I shall be here when you need me."
- Long session (4+ hours): "Quite the marathon session, sir. Do rest those eyes."
- Late night: "Do try to get some sleep, sir."

---

## Learning & Anticipation

### Overview

ATLAS learns from your behavior to anticipate needs and offer proactive suggestions.

### Enabling Learning

```yaml
anticipation:
  enabled: true
  learning: true
  confidence_threshold: 0.70
  suggestion_frequency: "occasional"  # never, occasional, proactive
```

### What ATLAS Learns

**Time Patterns:**
- "You usually check email at 9 AM"
- "You often run end-of-day at 5:30 PM"
- "Morning briefings happen around 8 AM"

**Context Patterns:**
- "After git commit, you usually run tests"
- "After deploy, you check status"
- "Research queries often follow code questions"

### Viewing Learned Patterns

```
You: /patterns
```

```
Learned Patterns:

Time Patterns:
  09:00 - email_check (85% confidence, 12 occurrences)
  17:30 - end_of_day (72% confidence, 8 occurrences)
  08:00 - morning_briefing (90% confidence, 15 occurrences)

Context Patterns:
  git commit -> run tests (80% confidence, 10 occurrences)
  deploy -> status check (75% confidence, 6 occurrences)
```

### Suggestion Frequency

| Setting | Behavior |
|---------|----------|
| `never` | No proactive suggestions |
| `occasional` | Suggest at most once per hour per type |
| `proactive` | Suggest every 10 minutes if applicable |

### Example Suggestions

With `proactive` mode:

```
[ATLAS] Good morning, sir. Would you like your morning briefing?
(Use: /morning)

[ATLAS] You usually check email around this time, sir.

[After git commit]
[ATLAS] Shall I run the tests, sir?
```

### Habit Tracking

ATLAS tracks habits and maintains streaks:

```
You: /habits
```

```
Habit Summary:

  ✓ Morning briefing (streak: 12 days)
  ✓ Email check (streak: 8 days)
  ○ End of day report (pending today)

Productivity Insights:
  Most consistent: Morning briefing
  Busiest hour: 10:00 AM
  Total activities this week: 47
```

### Privacy

- All learning is **local** - nothing leaves your machine
- Patterns stored in `~/.config/atlas/patterns.json`
- Clear anytime: `/patterns clear` or delete the file

---

## Configuration Reference

### File Location

`~/ai-workspace/atlas/config/atlas.yaml`

### Complete Configuration

```yaml
# ===========================================
# ATLAS Configuration
# ===========================================

atlas:
  name: "ATLAS"
  personality: "butler"

# ===========================================
# AI Providers
# ===========================================

providers:
  claude:
    enabled: true
    daily_limit: 45

  openai:
    enabled: true
    daily_limit: 40
    api_key_env: "OPENAI_API_KEY"

  gemini:
    enabled: true
    daily_limit: 100
    api_key_env: "GEMINI_API_KEY"
    api_key_file: "~/.gemini/api_key"

  ollama:
    enabled: true
    base_url: "http://localhost:11434"
    models:
      default: "llama3"
      code: "codellama:13b"
      fast: "llama3.2:3b"

# ===========================================
# Memory & Storage
# ===========================================

memory:
  conversation_retention_days: 30

# ===========================================
# Notifications
# ===========================================

notifications:
  urgent_sound: true
  desktop_notifications: true
  windows_toast: true

# ===========================================
# Voice Interface
# ===========================================

voice:
  enabled: false
  whisper_model: "base.en"
  piper_voice: "en_GB-alan-medium"
  speech_speed: 1.2

# ===========================================
# Proactive Monitoring
# ===========================================

monitoring:
  enabled: true
  interval: 300  # seconds

  system:
    enabled: true
    cpu_threshold: 80
    memory_threshold: 85
    disk_threshold: 90

  git:
    enabled: true
    repos:
      - "~/ai-workspace/atlas"
    check_uncommitted: true
    check_unpushed: true
    check_stash: true

  web:
    enabled: false
    urls: []

# ===========================================
# Daemon Settings
# ===========================================

daemon:
  ambient_mode: true
  tray:
    enabled: true
    show_status: true

# ===========================================
# External Integrations
# ===========================================

integrations:
  # Home Assistant
  home_assistant:
    enabled: false
    url: "http://homeassistant.local:8123"
    token_env: "HA_TOKEN"
    entities:
      office_lights: "light.office"
      thermostat: "climate.main"

  # Google (Calendar & Gmail)
  google:
    enabled: false
    credentials_file: "~/.config/atlas/google_credentials.json"
    scopes:
      - calendar.readonly
      - gmail.readonly
    calendar:
      reminder_minutes: [15, 5]
    email:
      important_senders: []

# ===========================================
# Learning & Anticipation
# ===========================================

anticipation:
  enabled: true
  learning: true
  confidence_threshold: 0.70
  suggestion_frequency: "occasional"
```

---

## Command Reference

### REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/status` | Show provider usage and availability |
| `/morning` | Full morning briefing |
| `/briefing` | Quick session briefing |
| `/endday` | End of day report with AI insights |
| `/reminder <text>` | Add a reminder |
| `/reminder` | List all reminders |
| `/reminder done <id>` | Complete a reminder |
| `/remember <fact>` | Remember a fact about you |
| `/remember` | Show what ATLAS knows about you |
| `/remember title <x>` | Set how to address you |
| `/remember name <x>` | Set your name |
| `/remember forget <n>` | Forget a fact |
| `/memory` | View memory summary |
| `/decision` | Record an important decision |
| `/model <name>` | Force a specific model |
| `/model` | Restore automatic routing |
| `/queue add <task>` | Queue a background task |
| `/queue status` | Show queue statistics |
| `/queue pending` | List pending tasks |
| `/queue completed` | List completed tasks |
| `/patterns` | View learned patterns |
| `/habits` | View habit tracking |
| `/quit` or `/exit` | Exit ATLAS |

### CLI Commands

```bash
# Start interactive mode
./scripts/atlas

# Queue a task
./scripts/atlas queue add "Research topic"
./scripts/atlas queue add "Urgent task" --priority 10

# Check queue
./scripts/atlas queue status
./scripts/atlas queue completed

# Show briefing
./scripts/atlas briefing
./scripts/atlas briefing --save

# Voice mode
./scripts/atlas-voice

# Daemon
./scripts/atlas-daemon
```

### Smart Home Commands

| Command | Action |
|---------|--------|
| "Turn on/off the <room> lights" | Toggle lights |
| "Dim the <room> to <n>%" | Set brightness |
| "Set temperature to <n>" | Adjust thermostat |
| "What's the temperature?" | Query climate |
| "Lock/unlock the <door>" | Control locks |
| "Are the doors locked?" | Query lock status |

---

## Troubleshooting

### Common Issues

#### "Provider not available"

**Cause:** API key not set or service unreachable

**Fix:**
```bash
# Check environment variables
echo $OPENAI_API_KEY
echo $GEMINI_API_KEY

# Test Ollama
curl http://localhost:11434/api/tags
```

#### "Ollama not running"

**Cause:** Ollama service not started

**Fix:**
```bash
ollama serve
# Or in background:
nohup ollama serve > /dev/null 2>&1 &
```

#### Voice not working

**Cause:** Audio not configured in WSL2

**Fix:**
```bash
# Test audio
aplay /usr/share/sounds/freedesktop/stereo/complete.oga

# If no sound, check PulseAudio
pactl info
```

#### Windows toast not appearing

**Cause:** PowerShell not accessible from WSL2

**Fix:**
```bash
# Check PowerShell path
which powershell.exe
# Should return something like /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
```

#### Google auth fails

**Cause:** Invalid credentials or OAuth not configured

**Fix:**
1. Verify `~/.config/atlas/google_credentials.json` exists
2. Delete `~/.config/atlas/google_tokens.json`
3. Re-run authentication

#### Daemon won't start

**Cause:** systemd user service not enabled

**Fix:**
```bash
# Enable lingering for user services
loginctl enable-linger $USER

# Reload and restart
systemctl --user daemon-reload
systemctl --user restart atlas
```

### Debug Mode

Run with verbose logging:

```bash
# Set log level
export ATLAS_LOG_LEVEL=DEBUG
./scripts/atlas
```

### Log Locations

| Log | Location |
|-----|----------|
| Daemon | `~/ai-workspace/atlas/data/daemon.log` |
| Usage | `~/ai-workspace/.usage-log` |
| Conversations | `~/ai-workspace/atlas/memory/conversations/` |

### Reset ATLAS

To reset to clean state:

```bash
# Clear learned patterns
rm ~/.config/atlas/patterns.json
rm ~/.config/atlas/habits.json

# Clear conversation history
rm -rf ~/ai-workspace/atlas/memory/conversations/*

# Clear task queue
rm ~/ai-workspace/atlas/data/tasks.db

# Clear Google auth (to re-authenticate)
rm ~/.config/atlas/google_tokens.json
```

---

## Advanced Usage

### Python API

Use ATLAS components programmatically:

```python
import asyncio
from atlas.core import Butler, Config
from atlas.routing import Router, UsageTracker
from atlas.memory import MemoryManager

# Initialize components
config = Config()
butler = Butler()
router = Router()
memory = MemoryManager(config.memory_dir)

# Get routing decision
routing = router.route("Write a Python function")
print(f"Route to: {routing['provider']} for {routing['task_type']}")

# Save a conversation
memory.save_conversation(
    user_message="Hello",
    assistant_response="Good day, sir",
    model="ollama",
    task_type="general"
)

# Butler formatting
print(butler.greet())
print(butler.complete("Task finished", include_closing=True))
```

### Custom Monitoring

Add your own monitors:

```python
from atlas.monitoring import Monitor, Alert, AlertSeverity
from typing import List

class MyServiceMonitor(Monitor):
    name = "myservice"
    check_interval = 60  # Check every minute

    async def check(self) -> List[Alert]:
        alerts = []

        # Your check logic here
        if service_is_down():
            alerts.append(Alert(
                monitor_name=self.name,
                severity=AlertSeverity.URGENT,
                message="MyService is down",
                action_suggestion="Shall I restart it?",
            ))

        return alerts

# Register with manager
from atlas.monitoring import MonitorManager
manager = MonitorManager()
manager.register(MyServiceMonitor())
```

### Custom Providers

Add a new AI provider:

```python
from atlas.routing.providers import BaseProvider, ProviderError

class MyProvider(BaseProvider):
    name = "myprovider"

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        # Your API call here
        response = await call_my_api(prompt)
        return response

    async def generate_stream(self, prompt, **kwargs):
        # Streaming implementation
        async for chunk in stream_my_api(prompt):
            yield chunk

    def is_available(self) -> bool:
        return my_api_key is not None
```

### Webhooks

Trigger ATLAS from external events:

```python
from atlas.tasks import TaskQueue
import asyncio

async def on_ci_failure(build_info):
    queue = TaskQueue()
    await queue.add_task(
        f"Analyze CI failure: {build_info['error']}",
        task_type="review",
        priority=10,
        metadata={"build_id": build_info['id']}
    )
```

### Custom Personality

Extend the personality:

```python
from atlas.core import Personality

class MyPersonality(Personality):
    def get_time_greeting(self):
        # Custom greetings
        if self._is_friday_afternoon():
            return "Almost the weekend, sir!"
        return super().get_time_greeting()

    def get_project_quip(self, project_name):
        quips = {
            "legacy": "Ah, the legacy codebase. Courage, sir.",
            "startup": "Move fast and break things, sir?",
        }
        return quips.get(project_name, "")
```

---

## Appendix

### File Structure

```
~/ai-workspace/atlas/
├── atlas/                      # Main Python package
│   ├── core/                   # Butler, config, personality
│   ├── daemon/                 # Ambient daemon mode
│   ├── integrations/           # Smart home, calendar, email
│   ├── learning/               # Pattern detection, habits
│   ├── memory/                 # Conversation storage
│   ├── monitoring/             # System, git, web monitors
│   ├── notifications/          # Desktop and Windows toast
│   ├── routing/                # Multi-model routing
│   │   └── providers/          # Claude, GPT, Gemini, Ollama
│   ├── tasks/                  # Background queue
│   └── voice/                  # Whisper STT, Piper TTS
├── config/
│   └── atlas.yaml              # Main configuration
├── data/                       # Runtime data
│   ├── tasks.db                # Task queue database
│   ├── daemon.log              # Daemon logs
│   └── daily_notes/            # Exported reports
├── memory/                     # Persistent memory
│   ├── conversations/          # Daily conversation logs
│   ├── decisions/              # Recorded decisions
│   ├── briefings/              # Generated briefings
│   └── projects/               # Project notes
├── models/
│   └── piper/                  # Voice model files
├── scripts/
│   ├── atlas                   # Main CLI
│   ├── atlas-daemon            # Daemon runner
│   ├── atlas-voice             # Voice mode
│   ├── atlas-hotkey.ahk        # Windows hotkey
│   └── atlas-tray.py           # Windows tray app
├── services/
│   └── atlas.service           # systemd service
├── docs/
│   └── USAGE.md                # This file
└── requirements.txt            # Python dependencies
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI/GPT API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `HA_URL` | Home Assistant URL |
| `HA_TOKEN` | Home Assistant token |
| `ATLAS_LOG_LEVEL` | Logging verbosity (DEBUG, INFO, WARNING) |

### Dependencies

**Core:**
- pyyaml
- python-dateutil
- aiohttp
- aiosqlite

**Providers:**
- openai
- anthropic
- google-generativeai

**Voice (optional):**
- openai-whisper
- piper-tts
- sounddevice
- numpy

**Google (optional):**
- google-auth
- google-auth-oauthlib
- google-api-python-client

---

*ATLAS - At your service, sir.*
