# ATLAS

**Automated Thinking, Learning & Advisory System**

A refined British butler AI assistant with multi-model intelligence, proactive monitoring, and JARVIS-like awareness.

---

## Features

- **Multi-Model Routing** - Automatically routes queries to Claude, GPT, Gemini, or Ollama
- **Background Tasks** - Queue research for overnight processing
- **Proactive Monitoring** - System, git, and web service alerts
- **Smart Home Control** - Natural language Home Assistant integration
- **Calendar & Email** - Google Calendar and Gmail awareness
- **Voice Interface** - Whisper STT + Piper TTS with British voice
- **Learning Engine** - Detects patterns and anticipates needs
- **Butler Personality** - Refined, contextual responses with wit

---

## Quick Start

```bash
# Activate environment
source .venv/bin/activate

# Start ATLAS
./scripts/atlas
```

```
[ATLAS] Good morning, sir. How may I be of service?

You: Write a Python function to merge sorted lists
You: /status
You: /morning
You: /quit
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/status` | Provider usage and availability |
| `/morning` | Full morning briefing |
| `/briefing` | Quick session briefing |
| `/endday` | End of day report |
| `/reminder <text>` | Add a reminder |
| `/remember <fact>` | Remember something about you |
| `/queue add <task>` | Queue background task |
| `/model <name>` | Force specific model |
| `/quit` | Exit ATLAS |

---

## Background Daemon

```bash
# Install service (one-time)
cp services/atlas.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable atlas

# Start/stop
systemctl --user start atlas
systemctl --user stop atlas
```

---

## Configuration

Edit `config/atlas.yaml`:

```yaml
providers:
  claude:
    enabled: true
    daily_limit: 45
  openai:
    enabled: true
    api_key_env: "OPENAI_API_KEY"
  gemini:
    enabled: true
    api_key_file: "~/.gemini/api_key"
  ollama:
    enabled: true
    base_url: "http://localhost:11434"

monitoring:
  enabled: true
  git:
    repos: ["~/projects/myapp"]

integrations:
  home_assistant:
    enabled: true
    url: "http://homeassistant.local:8123"
```

---

## Documentation

**[Full Usage Guide](docs/USAGE.md)** - Comprehensive documentation covering:

- Installation & Setup
- Multi-Model Routing
- Background Tasks & Daemon
- Briefings & Reports
- Voice Interface
- Hotkey Activation
- Proactive Monitoring
- Smart Home Control
- Calendar & Email Integration
- Personality & Easter Eggs
- Learning & Anticipation
- Configuration Reference
- Troubleshooting
- Advanced Usage

---

## Project Structure

```
atlas/
├── atlas/                  # Main Python package
│   ├── core/               # Butler, config, personality
│   ├── daemon/             # Ambient daemon mode
│   ├── integrations/       # Home Assistant, Google
│   ├── learning/           # Pattern detection
│   ├── memory/             # Conversation storage
│   ├── monitoring/         # System, git, web monitors
│   ├── notifications/      # Desktop & Windows toast
│   ├── routing/            # Multi-model routing
│   ├── tasks/              # Background queue
│   └── voice/              # Whisper + Piper
├── config/atlas.yaml       # Configuration
├── scripts/                # CLI tools
├── services/               # systemd service
├── memory/                 # Persistent storage
└── docs/                   # Documentation
```

---

## Requirements

- Python 3.12+
- WSL2 (for Windows)

**Core:**
```
pyyaml python-dateutil aiohttp aiosqlite
openai anthropic google-generativeai
```

**Voice (optional):**
```
openai-whisper piper-tts sounddevice numpy
```

**Google (optional):**
```
google-auth google-auth-oauthlib google-api-python-client
```

---

## License

MIT

---

*"Very good, sir. I remain at your service."*
