# ATLAS Replication Guide

**How to rebuild ATLAS from scratch**

This document provides complete instructions for replicating the ATLAS system on a new machine or environment.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Directory Structure](#directory-structure)
3. [Step-by-Step Build](#step-by-step-build)
4. [Core Components](#core-components)
5. [Module Reference](#module-reference)
6. [Configuration](#configuration)
7. [Service Setup](#service-setup)
8. [Verification](#verification)

---

## System Requirements

### Required

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12+ | Core runtime |
| pip | Latest | Package management |
| Linux/WSL2 | Any | Operating system |

### Optional

| Component | Version | Purpose |
|-----------|---------|---------|
| Ollama | Latest | Local LLM inference |
| AutoHotkey | v2.0+ | Windows hotkey (Windows only) |
| PulseAudio | Any | Voice audio (Linux) |
| systemd | Any | Daemon management |

### API Keys (at least one recommended)

- `OPENAI_API_KEY` - OpenAI GPT models
- `GEMINI_API_KEY` - Google Gemini models
- `ANTHROPIC_API_KEY` - Claude models

---

## Directory Structure

```
~/ai-workspace/atlas/
├── atlas/                      # Python package
│   ├── __init__.py
│   ├── core/                   # Core components
│   │   ├── __init__.py
│   │   ├── butler.py           # Butler personality
│   │   └── config.py           # Configuration loader
│   ├── memory/                 # Persistent memory
│   │   ├── __init__.py
│   │   └── manager.py          # Memory manager
│   ├── routing/                # Multi-model routing
│   │   ├── __init__.py
│   │   ├── router.py           # Task router
│   │   ├── usage.py            # Usage tracker
│   │   └── providers/          # AI providers
│   │       ├── __init__.py
│   │       ├── base.py         # Base provider class
│   │       ├── claude.py       # Anthropic Claude
│   │       ├── openai.py       # OpenAI GPT
│   │       ├── gemini.py       # Google Gemini
│   │       └── ollama.py       # Local Ollama
│   ├── tasks/                  # Background tasks
│   │   ├── __init__.py
│   │   ├── queue.py            # SQLite task queue
│   │   └── worker.py           # Async worker
│   ├── notifications/          # Notifications
│   │   ├── __init__.py
│   │   └── notifier.py         # Desktop notifications
│   └── voice/                  # Voice interface
│       ├── __init__.py
│       ├── stt.py              # Speech-to-text (Whisper)
│       └── tts.py              # Text-to-speech (Piper)
├── memory/                     # Data storage
│   ├── conversations/          # Daily conversation logs
│   ├── decisions/              # Recorded decisions
│   ├── projects/               # Project notes
│   └── briefings/              # Session briefings
├── data/                       # Runtime data
│   ├── tasks.db                # SQLite queue database
│   └── daemon.log              # Daemon logs
├── config/
│   └── atlas.yaml              # Configuration file
├── scripts/
│   ├── atlas                   # Main CLI
│   ├── atlas-daemon            # Background daemon
│   ├── atlas-voice             # Voice interface
│   ├── atlas-hotkey.ahk        # Windows hotkey
│   └── setup.sh                # Setup script
├── services/
│   └── atlas.service           # systemd service
├── models/
│   └── piper/                  # Voice models
├── .venv/                      # Python virtual environment
├── requirements.txt            # Python dependencies
├── USAGE.md                    # User guide
└── REPLICATION.md              # This file
```

---

## Step-by-Step Build

### Step 1: Create Directory Structure

```bash
# Create base directory
mkdir -p ~/ai-workspace/atlas
cd ~/ai-workspace/atlas

# Create Python package structure
mkdir -p atlas/{core,memory,routing/providers,tasks,notifications,voice}

# Create data directories
mkdir -p memory/{conversations,decisions,projects,briefings}
mkdir -p data config scripts services models/piper

# Create __init__.py files
touch atlas/__init__.py
touch atlas/{core,memory,routing,tasks,notifications,voice}/__init__.py
touch atlas/routing/providers/__init__.py
```

### Step 2: Create Virtual Environment

```bash
cd ~/ai-workspace/atlas
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Create requirements.txt

```bash
cat > requirements.txt << 'EOF'
# Core
pyyaml>=6.0
python-dateutil>=2.8

# Routing & Providers
aiohttp>=3.9
openai>=1.0
anthropic>=0.18
google-generativeai>=0.3

# Background Tasks
aiosqlite>=0.19

# Voice (optional)
# openai-whisper>=20231117
# piper-tts>=1.2
# sounddevice>=0.4
# numpy>=1.24
EOF
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Create Core Modules

See [Module Reference](#module-reference) below for complete source code.

### Step 6: Create Scripts

```bash
# Make scripts executable
chmod +x scripts/atlas
chmod +x scripts/atlas-daemon
chmod +x scripts/atlas-voice
chmod +x scripts/setup.sh
```

### Step 7: Create Configuration

```bash
cat > config/atlas.yaml << 'EOF'
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
      fast: "llama3.2:3b"

memory:
  conversation_retention_days: 30

notifications:
  urgent_sound: true
  desktop_notifications: true

voice:
  enabled: false
  whisper_model: "base.en"
  piper_voice: "en_GB-alan-medium"
EOF
```

### Step 8: Install systemd Service

```bash
mkdir -p ~/.config/systemd/user
cp services/atlas.service ~/.config/systemd/user/
systemctl --user daemon-reload
```

---

## Core Components

### Component Overview

| Component | File | Purpose |
|-----------|------|---------|
| Butler | `core/butler.py` | British butler personality, response formatting |
| Config | `core/config.py` | YAML config loader, API key management |
| MemoryManager | `memory/manager.py` | Markdown-based persistent storage |
| Router | `routing/router.py` | Task classification and provider selection |
| UsageTracker | `routing/usage.py` | API quota tracking |
| Providers | `routing/providers/*.py` | AI provider implementations |
| TaskQueue | `tasks/queue.py` | SQLite-based task queue |
| TaskWorker | `tasks/worker.py` | Async background processor |
| Notifier | `notifications/notifier.py` | Desktop notifications |
| WhisperSTT | `voice/stt.py` | Speech-to-text |
| PiperTTS | `voice/tts.py` | Text-to-speech |

### Data Flow

```
User Input
    │
    ▼
┌─────────────────┐
│   AtlasCLI      │ ◄── Butler personality
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Router      │ ◄── Task classification
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ UsageTracker    │ ◄── Quota checking
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Provider     │ ◄── Claude/OpenAI/Gemini/Ollama
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MemoryManager  │ ◄── Save conversation
└────────┬────────┘
         │
         ▼
    Response
```

---

## Module Reference

### atlas/__init__.py

```python
"""ATLAS - Automated Thinking, Learning & Advisory System"""

__version__ = "0.1.0"
__author__ = "ATLAS Development"
```

### atlas/core/__init__.py

```python
"""Core ATLAS components."""

from .butler import Butler
from .config import Config

__all__ = ["Butler", "Config"]
```

### atlas/core/config.py

```python
"""Configuration management for ATLAS."""

import os
from pathlib import Path
from typing import Any, Optional
import yaml


class Config:
    """YAML-based configuration manager."""

    DEFAULT_CONFIG = {
        "atlas": {"name": "ATLAS", "personality": "butler"},
        "providers": {
            "claude": {"enabled": True, "daily_limit": 45},
            "openai": {"enabled": True, "daily_limit": 40, "api_key_env": "OPENAI_API_KEY"},
            "gemini": {"enabled": True, "daily_limit": 100, "api_key_env": "GEMINI_API_KEY"},
            "ollama": {"enabled": True, "base_url": "http://localhost:11434",
                      "models": {"default": "llama3", "code": "codellama:13b"}},
        },
        "memory": {"conversation_retention_days": 30},
        "notifications": {"urgent_sound": True, "desktop_notifications": True},
        "voice": {"enabled": False, "whisper_model": "base.en", "piper_voice": "en_GB-alan-medium"},
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.base_dir = Path.home() / "ai-workspace" / "atlas"
        self.config_path = config_path or self.base_dir / "config" / "atlas.yaml"
        self._config = self._load_config()

    def _load_config(self) -> dict:
        config = self.DEFAULT_CONFIG.copy()
        if self.config_path.exists():
            with open(self.config_path) as f:
                user_config = yaml.safe_load(f) or {}
                config = self._deep_merge(config, user_config)
        return config

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, *keys: str, default: Any = None) -> Any:
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_api_key(self, provider: str) -> Optional[str]:
        provider_config = self.get("providers", provider, default={})
        env_var = provider_config.get("api_key_env")
        if env_var:
            key = os.environ.get(env_var)
            if key:
                return key
        key_file = provider_config.get("api_key_file")
        if key_file:
            key_path = Path(key_file).expanduser()
            if key_path.exists():
                return key_path.read_text().strip()
        return None

    @property
    def memory_dir(self) -> Path:
        return self.base_dir / "memory"

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def name(self) -> str:
        return self.get("atlas", "name", default="ATLAS")
```

### atlas/core/butler.py

```python
"""British butler personality for ATLAS."""

import random
from datetime import datetime


class Butler:
    """Implements the refined British butler personality."""

    GREETINGS = {
        "morning": [
            "Good morning, sir. I trust you slept well. How may I be of service today?",
            "A fine morning to you, sir. I've prepared myself for whatever tasks you might require.",
        ],
        "afternoon": [
            "Good afternoon, sir. I hope the day finds you well. How may I assist?",
            "Afternoon, sir. I remain at your complete disposal.",
        ],
        "evening": [
            "Good evening, sir. I trust the day has treated you kindly. How may I help?",
            "A pleasant evening to you, sir. What may I assist you with?",
        ],
        "night": [
            "Good evening, sir. Burning the midnight oil, I see. How may I assist?",
            "The quiet hours, sir. An excellent time for focused work. What shall we tackle?",
        ],
    }

    ACKNOWLEDGMENTS = ["Very good, sir.", "Certainly, sir.", "At once, sir.", "Consider it done, sir."]
    THINKING_PHRASES = ["Allow me a moment to consider this, sir...", "Permit me to investigate, sir..."]
    COMPLETION_PHRASES = ["I trust this meets your requirements, sir.", "The task is complete, sir."]
    ERROR_PHRASES = ["I regret to inform you, sir, that we've encountered a difficulty."]
    FAREWELLS = ["Very good, sir. I shall be here when you need me.", "Until next time, sir. Do take care."]

    def __init__(self, name: str = "ATLAS"):
        self.name = name
        self._session_start = datetime.now()

    def _get_time_period(self) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12: return "morning"
        elif 12 <= hour < 17: return "afternoon"
        elif 17 <= hour < 22: return "evening"
        else: return "night"

    def greet(self) -> str:
        period = self._get_time_period()
        return f"[{self.name}] {random.choice(self.GREETINGS[period])}"

    def acknowledge(self) -> str:
        return f"[{self.name}] {random.choice(self.ACKNOWLEDGMENTS)}"

    def thinking(self) -> str:
        return f"[{self.name}] {random.choice(self.THINKING_PHRASES)}"

    def complete(self, response: str, include_closing: bool = True) -> str:
        lines = [f"[{self.name}]", "", response]
        if include_closing:
            lines.extend(["", random.choice(self.COMPLETION_PHRASES)])
        return "\n".join(lines)

    def error(self, message: str) -> str:
        return f"[{self.name}] {random.choice(self.ERROR_PHRASES)}\n\n{message}"

    def farewell(self) -> str:
        return f"[{self.name}] {random.choice(self.FAREWELLS)}"

    def format_status(self, status_dict: dict) -> str:
        lines = [f"[{self.name}] Your current status, sir:", ""]
        for key, value in status_dict.items():
            lines.append(f"  {key.replace('_', ' ').title()}: {value}")
        return "\n".join(lines)

    def format_briefing(self, briefing: dict) -> str:
        lines = [f"[{self.name}] Your briefing, sir:", "", "=" * 50]
        if "pending_tasks" in briefing:
            lines.append(f"\nPending Tasks: {briefing['pending_tasks']}")
        if "usage" in briefing:
            lines.append("\nAPI Usage:")
            for provider, count in briefing["usage"].items():
                lines.append(f"  {provider.title()}: {count}")
        lines.extend(["=" * 50, "\nHow may I assist you today, sir?"])
        return "\n".join(lines)
```

### atlas/routing/router.py

```python
"""Intelligent task routing between AI providers."""

import re
from typing import Optional
from .usage import UsageTracker


class Router:
    """Route tasks to the most appropriate AI provider."""

    TASK_PATTERNS = {
        "code": [r"\b(code|function|class|debug|fix|implement|python|javascript|error|bug)\b"],
        "research": [r"\b(research|find|search|what is|explain|compare)\b"],
        "review": [r"\b(review|critique|analyze|evaluate|feedback)\b"],
        "draft": [r"\b(write|draft|compose|email|document|article)\b"],
    }

    ROUTING_TABLE = {
        "research": ["gemini", "claude", "ollama"],
        "code": ["openai", "claude", "ollama"],
        "review": ["claude", "gemini", "openai"],
        "draft": ["gemini", "claude", "ollama"],
        "default": ["ollama", "gemini", "claude"],
    }

    def __init__(self, usage_tracker: Optional[UsageTracker] = None):
        self.usage = usage_tracker or UsageTracker()

    def classify_task(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        scores = {task_type: 0 for task_type in self.TASK_PATTERNS}
        for task_type, patterns in self.TASK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    scores[task_type] += 1
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "default"

    def select_provider(self, task_type: str, preferred: Optional[str] = None) -> tuple[str, str]:
        if preferred and self.usage.is_available(preferred):
            return preferred, f"User requested {preferred}"
        providers = self.ROUTING_TABLE.get(task_type, self.ROUTING_TABLE["default"])
        for provider in providers:
            if self.usage.is_available(provider):
                return provider, f"Best for {task_type} tasks"
        return "ollama", "All API providers exhausted"

    def route(self, prompt: str, preferred: Optional[str] = None) -> dict:
        task_type = self.classify_task(prompt)
        provider, reason = self.select_provider(task_type, preferred)
        return {"provider": provider, "task_type": task_type, "reason": reason}

    def log_completion(self, provider: str, task_type: str) -> int:
        return self.usage.log_usage(provider, task_type)
```

### atlas/routing/usage.py

```python
"""Usage tracking for LLM APIs."""

from datetime import datetime
from pathlib import Path
from typing import Optional


class UsageTracker:
    """Track and manage LLM API usage."""

    LIMITS = {"claude": 45, "openai": 40, "gemini": 100, "ollama": float("inf")}

    def __init__(self, usage_file: Optional[Path] = None):
        self.usage_file = usage_file or Path.home() / "ai-workspace" / ".usage-log"
        if not self.usage_file.exists():
            self.usage_file.parent.mkdir(parents=True, exist_ok=True)
            self.usage_file.write_text("# LLM Usage Tracker\n# Format: DATE|LLM|COUNT|NOTES\n")

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def get_usage(self, provider: str) -> int:
        today = self._today()
        max_count = 0
        for line in self.usage_file.read_text().splitlines():
            if line.startswith(f"{today}|{provider}|"):
                parts = line.split("|")
                if len(parts) >= 3:
                    try: max_count = max(max_count, int(parts[2]))
                    except ValueError: continue
        return max_count

    def log_usage(self, provider: str, task_type: str = "general") -> int:
        new_count = self.get_usage(provider) + 1
        with open(self.usage_file, "a") as f:
            f.write(f"{self._today()}|{provider}|{new_count}|{task_type}\n")
        return new_count

    def get_remaining(self, provider: str) -> float:
        limit = self.LIMITS.get(provider, 0)
        return float("inf") if limit == float("inf") else max(0, limit - self.get_usage(provider))

    def is_available(self, provider: str) -> bool:
        return self.get_remaining(provider) > 0

    def get_status_indicator(self, provider: str) -> str:
        limit = self.LIMITS.get(provider, 0)
        if limit == float("inf"): return "🟢"
        ratio = self.get_usage(provider) / limit
        return "🟢" if ratio < 0.6 else "🟡" if ratio < 0.9 else "🔴"

    def format_status(self) -> str:
        lines = ["═" * 45, f"  LLM Usage Status - {self._today()}", "═" * 45]
        for provider in ["claude", "openai", "gemini", "ollama"]:
            usage = self.get_usage(provider)
            limit = self.LIMITS.get(provider, 0)
            indicator = self.get_status_indicator(provider)
            limit_str = "∞" if limit == float("inf") else str(int(limit))
            lines.append(f"  {provider.title():8} {usage:3} / {limit_str:<3}  {indicator}")
        lines.append("═" * 45)
        return "\n".join(lines)
```

### Provider Base Class (atlas/routing/providers/base.py)

```python
"""Base provider interface for ATLAS."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class ProviderError(Exception):
    def __init__(self, message: str, provider: str, recoverable: bool = True):
        self.message = message
        self.provider = provider
        self.recoverable = recoverable
        super().__init__(f"[{provider}] {message}")


class BaseProvider(ABC):
    name: str = "base"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.options = kwargs

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                       max_tokens: int = 4096, temperature: float = 0.7) -> str:
        pass

    @abstractmethod
    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None,
                              max_tokens: int = 4096, temperature: float = 0.7) -> AsyncIterator[str]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    def get_system_prompt(self) -> str:
        return """You are ATLAS, a refined British butler assistant.
Address the user as "sir" or "madam". Be helpful, thorough, and precise."""
```

---

## Configuration

### atlas.yaml Reference

```yaml
atlas:
  name: "ATLAS"              # Assistant name
  personality: "butler"       # Personality type

providers:
  claude:
    enabled: true             # Enable/disable provider
    daily_limit: 45           # Daily request limit
  openai:
    enabled: true
    daily_limit: 40
    api_key_env: "OPENAI_API_KEY"    # Environment variable name
  gemini:
    enabled: true
    daily_limit: 100
    api_key_env: "GEMINI_API_KEY"
    api_key_file: "~/.gemini/api_key" # Alternative: file path
  ollama:
    enabled: true
    base_url: "http://localhost:11434"
    models:
      default: "llama3"
      code: "codellama:13b"
      fast: "llama3.2:3b"

memory:
  conversation_retention_days: 30    # Auto-cleanup after N days

notifications:
  urgent_sound: true          # Play sound for urgent notifications
  desktop_notifications: true # Show desktop notifications

voice:
  enabled: false              # Enable voice interface
  whisper_model: "base.en"    # Whisper model size
  piper_voice: "en_GB-alan-medium"  # Piper voice model
```

---

## Service Setup

### systemd User Service

Create `~/.config/systemd/user/atlas.service`:

```ini
[Unit]
Description=ATLAS Daemon
After=network.target

[Service]
Type=simple
ExecStart=/home/USER/ai-workspace/atlas/scripts/atlas-daemon
WorkingDirectory=/home/USER/ai-workspace/atlas
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

### Service Commands

```bash
# Reload service files
systemctl --user daemon-reload

# Enable on boot
systemctl --user enable atlas

# Start/stop/restart
systemctl --user start atlas
systemctl --user stop atlas
systemctl --user restart atlas

# Check status
systemctl --user status atlas

# View logs
journalctl --user -u atlas -f
```

---

## Verification

### Test Checklist

Run these commands to verify your installation:

```bash
# 1. Test CLI starts
~/ai-workspace/atlas/scripts/atlas --help

# 2. Test interactive mode
echo "/status" | ~/ai-workspace/atlas/scripts/atlas

# 3. Test queue commands
~/ai-workspace/atlas/scripts/atlas queue status

# 4. Test briefing
~/ai-workspace/atlas/scripts/atlas briefing

# 5. Test provider routing (requires API key or Ollama)
echo "What is 2+2?" | ~/ai-workspace/atlas/scripts/atlas

# 6. Test daemon (optional)
systemctl --user status atlas
```

### Expected Results

| Test | Expected Output |
|------|-----------------|
| CLI starts | Help text or greeting |
| /status | Usage table with provider availability |
| queue status | Pending/Running/Completed counts |
| briefing | Task summary |
| Question | Butler-styled response via provider |
| daemon | Active (running) status |

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Activate venv: `source .venv/bin/activate` |
| Provider not available | Set API key environment variable |
| Ollama connection failed | Start Ollama: `ollama serve` |
| Permission denied on scripts | Run: `chmod +x scripts/*` |
| systemd service not found | Run: `systemctl --user daemon-reload` |

---

## Quick Replication Script

For fast replication, run this complete setup script:

```bash
#!/bin/bash
set -e

ATLAS_DIR=~/ai-workspace/atlas

# Create structure
mkdir -p $ATLAS_DIR/{atlas/{core,memory,routing/providers,tasks,notifications,voice},memory/{conversations,decisions,projects,briefings},data,config,scripts,services,models/piper}

# Create venv
cd $ATLAS_DIR
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install pyyaml python-dateutil aiohttp openai anthropic google-generativeai aiosqlite

# Create __init__.py files
touch atlas/__init__.py
touch atlas/{core,memory,routing,tasks,notifications,voice}/__init__.py
touch atlas/routing/providers/__init__.py

echo "Structure created. Now copy the Python modules from REPLICATION.md"
```

---

## Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `atlas/__init__.py` | 4 | Package init |
| `atlas/core/config.py` | 80 | Configuration |
| `atlas/core/butler.py` | 120 | Personality |
| `atlas/memory/manager.py` | 180 | Memory storage |
| `atlas/routing/router.py` | 80 | Task routing |
| `atlas/routing/usage.py` | 90 | Usage tracking |
| `atlas/routing/providers/base.py` | 50 | Provider interface |
| `atlas/routing/providers/claude.py` | 80 | Claude provider |
| `atlas/routing/providers/openai.py` | 80 | OpenAI provider |
| `atlas/routing/providers/gemini.py` | 100 | Gemini provider |
| `atlas/routing/providers/ollama.py` | 120 | Ollama provider |
| `atlas/tasks/queue.py` | 150 | Task queue |
| `atlas/tasks/worker.py` | 150 | Background worker |
| `atlas/notifications/notifier.py` | 100 | Notifications |
| `atlas/voice/stt.py` | 120 | Speech-to-text |
| `atlas/voice/tts.py` | 150 | Text-to-speech |
| `scripts/atlas` | 350 | Main CLI |
| `scripts/atlas-daemon` | 100 | Daemon |
| **Total** | **~2900** | |

---

*ATLAS - Replication Guide v0.1.0*
