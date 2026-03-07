# ATLAS User Guide

**Automated Thinking, Learning & Advisory System**

A multi-model AI assistant with a refined British butler personality.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Interactive Mode](#interactive-mode)
5. [Commands Reference](#commands-reference)
6. [Multi-Model Routing](#multi-model-routing)
7. [Background Tasks](#background-tasks)
8. [Voice Interface](#voice-interface)
9. [Windows Hotkey](#windows-hotkey)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# Run ATLAS interactively
~/ai-workspace/atlas/scripts/atlas

# Queue a background research task
~/ai-workspace/atlas/scripts/atlas queue add "Research Kubernetes security best practices"

# Check task status
~/ai-workspace/atlas/scripts/atlas queue status

# Get a briefing
~/ai-workspace/atlas/scripts/atlas briefing
```

---

## Installation

### Prerequisites

- Python 3.12+
- API keys for cloud providers (optional but recommended):
  - OpenAI API key
  - Google Gemini API key
  - Anthropic Claude API key (via Claude Code)
- Ollama for local models (optional fallback)

### Setup

```bash
# Navigate to ATLAS directory
cd ~/ai-workspace/atlas

# Run the setup script
./scripts/setup.sh

# Or manually set up:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### API Key Configuration

Set your API keys as environment variables:

```bash
# Add to ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY="your-openai-key"
export GEMINI_API_KEY="your-gemini-key"
```

Or create key files:

```bash
# Gemini key file
mkdir -p ~/.gemini
echo "your-gemini-key" > ~/.gemini/api_key
```

---

## Configuration

ATLAS configuration is stored in `config/atlas.yaml`:

```yaml
atlas:
  name: "ATLAS"
  personality: "butler"

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
  ollama:
    enabled: true
    base_url: "http://localhost:11434"
    models:
      default: "llama3"
      code: "codellama:13b"

memory:
  conversation_retention_days: 30

notifications:
  urgent_sound: true
  desktop_notifications: true

voice:
  enabled: false
  whisper_model: "base.en"
  piper_voice: "en_GB-alan-medium"
```

---

## Interactive Mode

Start ATLAS in interactive mode:

```bash
~/ai-workspace/atlas/scripts/atlas
```

You'll see a greeting like:

```
[ATLAS] Good morning, sir. I trust you slept well. How may I be of service today?

Type /help for available commands, or simply ask me anything.

You: _
```

### Asking Questions

Simply type your question or task:

```
You: Write a Python function to sort a list

[ATLAS] Allow me a moment to consider this, sir...
  Task type: code
  Routing to: Openai

[ATLAS]

Certainly, sir. Here is a Python function to sort a list...
```

### Exiting

Type `/exit` or `/quit`, or press `Ctrl+C`:

```
You: /exit

[ATLAS] Very good, sir. I shall be here when you need me.
```

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/status` | Show API usage and provider availability |
| `/briefing` | Get a session briefing with queue status |
| `/memory` | Show memory summary (conversations, decisions) |
| `/decision` | Record an important decision interactively |
| `/model <provider>` | Force all requests to a specific provider |
| `/model` | Restore automatic routing |
| `/queue` | Show queue command help |
| `/queue add <task>` | Add a background task |
| `/queue status` | Show queue statistics |
| `/queue pending` | List pending tasks |
| `/queue completed` | List recently completed tasks |
| `/exit` or `/quit` | Exit ATLAS |

### Examples

**Check status:**
```
You: /status

[ATLAS]

═════════════════════════════════════════════
  LLM Usage Status - 2026-02-09
═════════════════════════════════════════════
  Claude     5 / 45   🟢
  Openai     3 / 40   🟢
  Gemini    12 / 100  🟢
  Ollama     8 / ∞    🟢
═════════════════════════════════════════════

Provider Availability:
  Claude   ✓
  Openai   ✓
  Gemini   ✓
  Ollama   ✓
```

**Force a specific model:**
```
You: /model claude

[ATLAS] Very good, sir. All requests will now be directed to Claude.

You: /model

[ATLAS] Automatic routing restored, sir.
```

**Record a decision:**
```
You: /decision

[ATLAS] Certainly, sir.

Please provide the following details:

Decision title: Use PostgreSQL for the project
Context (what prompted this): Need a database for the new application
The decision: PostgreSQL over MySQL
Reasoning: Better JSON support and performance
Alternatives considered (comma-separated): MySQL, SQLite, MongoDB

[ATLAS] Decision recorded successfully.
```

---

## Multi-Model Routing

ATLAS automatically routes your requests to the most appropriate AI model:

| Task Type | Primary Provider | Fallback 1 | Fallback 2 |
|-----------|-----------------|------------|------------|
| Code/debugging | OpenAI GPT | Claude | Ollama CodeLlama |
| Research/search | Gemini | Claude | Ollama |
| Review/critique | Claude | Gemini | OpenAI |
| Writing/drafts | Gemini | Claude | Ollama |
| General/other | Ollama | Gemini | Claude |

### How Routing Works

1. ATLAS analyzes your prompt for keywords
2. Classifies the task type (code, research, review, draft, or general)
3. Selects the best available provider based on:
   - Task type preferences
   - Current quota usage
   - Provider availability
4. Falls back to alternatives if the primary fails

### Task Classification Keywords

**Code tasks:** function, class, debug, fix, implement, python, javascript, error, bug, API

**Research tasks:** research, find, search, explain, what is, compare, latest

**Review tasks:** review, critique, analyze, evaluate, feedback, pros and cons

**Draft tasks:** write, draft, compose, email, document, article

---

## Background Tasks

Queue long-running tasks for background processing:

### Command Line

```bash
# Add a task
~/ai-workspace/atlas/scripts/atlas queue add "Research best practices for microservices"

# Check status
~/ai-workspace/atlas/scripts/atlas queue status

# View completed tasks
~/ai-workspace/atlas/scripts/atlas queue completed
```

### Interactive Mode

```
You: /queue add Research the latest developments in quantum computing

[ATLAS] Task queued successfully, sir.

Task ID: 3
Type: research

The daemon will process this in the background.
```

### Starting the Daemon

The background daemon processes queued tasks:

```bash
# Start manually
~/ai-workspace/atlas/scripts/atlas-daemon

# Or use systemd (recommended)
systemctl --user enable atlas    # Enable on boot
systemctl --user start atlas     # Start now
systemctl --user status atlas    # Check status
systemctl --user stop atlas      # Stop daemon
```

### Viewing Results

```bash
# Get a briefing with completed tasks
~/ai-workspace/atlas/scripts/atlas briefing --save

# Results are saved to:
# ~/ai-workspace/atlas/memory/briefings/
```

---

## Voice Interface

ATLAS supports voice interaction using Whisper (speech-to-text) and Piper (text-to-speech with British voice).

### Installation

```bash
# Install voice dependencies
source ~/ai-workspace/atlas/.venv/bin/activate
pip install openai-whisper sounddevice numpy piper-tts

# Download British voice model (optional)
mkdir -p ~/ai-workspace/atlas/models/piper
# Download en_GB-alan-medium.onnx from Piper releases
```

### Usage

```bash
~/ai-workspace/atlas/scripts/atlas-voice
```

```
ATLAS Voice Mode
========================================
Whisper (STT): ✓
Piper (TTS):   ✓
Microphone:    ✓
========================================

Commands:
  'quit' or 'exit' - Exit voice mode
  Press Enter to start listening (or type a message)

[ATLAS] Good day, sir. ATLAS voice mode is active. How may I assist you?

[Press Enter to speak, or type message]: _
```

### Voice Commands

- Press **Enter** with empty input to start voice recording
- Speak your question (recording stops after silence)
- ATLAS will respond with text-to-speech
- Type text directly as an alternative to speaking

---

## Windows Hotkey

Summon ATLAS from anywhere in Windows using a hotkey.

### Installation

1. Install [AutoHotkey v2](https://www.autohotkey.com/)
2. Copy `scripts/atlas-hotkey.ahk` to your Windows machine
3. Double-click to run, or add to Windows Startup

### Hotkeys

| Hotkey | Action |
|--------|--------|
| `` ` `` (backtick) | Summon ATLAS |
| `Win + `` ` | Alternative summon |
| `Ctrl + Shift + A` | Another alternative |

### How It Works

- If ATLAS window exists: focuses it
- If not: opens Windows Terminal with ATLAS in WSL

### Configuration

Edit `atlas-hotkey.ahk` to customize:

```ahk
; Change WSL distribution name
global WSL_DISTRO := "Ubuntu"

; Change ATLAS path
global ATLAS_PATH := "~/ai-workspace/atlas/scripts/atlas"
```

---

## Memory System

ATLAS maintains persistent memory in Markdown files:

```
~/ai-workspace/atlas/memory/
├── conversations/     # Daily conversation logs
│   └── 2026-02-09.md
├── decisions/         # Recorded decisions
│   └── 2026-02-09_use_postgresql.md
├── projects/          # Project-specific notes
└── briefings/         # Session briefings
```

### Conversation Logs

Each day's conversations are saved automatically:

```markdown
# Conversations - 2026-02-09

## 14:32:15 [openai]
*Task: code*

**User:** Write a Python function to sort a list

**ATLAS:** Certainly, sir. Here is a function...

---
```

### Retention

Old conversations are automatically cleaned up based on `memory.conversation_retention_days` in config (default: 30 days).

---

## Troubleshooting

### Provider Not Available

```
Provider Availability:
  Claude   ✗
  Openai   ✓
```

**Solution:** Set the API key environment variable or check your configuration.

```bash
export ANTHROPIC_API_KEY="your-key"
# or
export OPENAI_API_KEY="your-key"
```

### Ollama Connection Failed

```
[ATLAS] Cannot connect to Ollama. Is it running?
```

**Solution:** Start Ollama:

```bash
ollama serve
```

### No Providers Available

```
[ATLAS] No providers are currently available, sir.
```

**Solution:**
1. Set at least one API key, OR
2. Start Ollama for local inference

### Voice Not Working

```
Whisper (STT): ✗
```

**Solution:** Install voice dependencies:

```bash
pip install openai-whisper sounddevice numpy
```

For microphone issues on WSL2, you may need PulseAudio bridge or WSLg (Windows 11).

### Daemon Not Processing Tasks

Check daemon status:

```bash
systemctl --user status atlas
```

View logs:

```bash
tail -f ~/ai-workspace/atlas/data/daemon.log
```

---

## File Reference

| File | Purpose |
|------|---------|
| `scripts/atlas` | Main CLI entry point |
| `scripts/atlas-daemon` | Background task processor |
| `scripts/atlas-voice` | Voice interface |
| `scripts/atlas-hotkey.ahk` | Windows hotkey script |
| `config/atlas.yaml` | Configuration file |
| `data/tasks.db` | SQLite task queue |
| `data/daemon.log` | Daemon logs |
| `memory/` | Persistent memory storage |

---

## Tips

1. **Use `/status` frequently** to monitor quota usage
2. **Queue overnight tasks** using `/queue add` before ending your session
3. **Record important decisions** with `/decision` for future reference
4. **Check `/briefing`** at the start of each session
5. **Force a model** with `/model <provider>` when you need specific capabilities
6. **Use Ollama** as a free, unlimited fallback for general queries

---

*ATLAS - At your service, sir.*
