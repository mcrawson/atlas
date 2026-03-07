---
title: Configuration Reference
description: Complete YAML configuration options
tags:
  - configuration
  - reference
  - yaml
created: 2024-02-10
---

# Configuration Reference

Complete reference for `config/atlas.yaml`.

---

## File Location

```
~/ai-workspace/atlas/config/atlas.yaml
```

---

## Complete Configuration

```yaml
# Core Settings
atlas:
  name: "ATLAS"
  personality: "butler"

# AI Providers
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

# Memory Settings
memory:
  conversation_retention_days: 30

# Notification Settings
notifications:
  urgent_sound: true
  desktop_notifications: true
  windows_toast: true

# Voice Settings
voice:
  enabled: false
  whisper_model: "base.en"
  piper_voice: "en_GB-alan-medium"
  silence_threshold: 0.03
  max_record_seconds: 30
  speak_responses: true

# Monitoring Settings
monitoring:
  enabled: true
  interval: 300

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

  web:
    enabled: false
    urls: []
    timeout: 10

# Daemon Settings
daemon:
  ambient_mode: true
  task_check_interval: 60
  tray:
    enabled: true
    show_status: true

# Integrations
integrations:
  home_assistant:
    enabled: false
    url: "http://homeassistant.local:8123"
    token_env: "HA_TOKEN"
    entities:
      office_lights: "light.office"
      bedroom_lights: "light.bedroom"
      thermostat: "climate.main"
      front_door: "lock.front_door"

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
      alert_on_important: true

# Learning Engine
anticipation:
  enabled: true
  learning: true
  confidence_threshold: 0.70
  suggestion_frequency: "occasional"
```

---

## Section Reference

### atlas

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | string | "ATLAS" | Assistant name |
| `personality` | string | "butler" | Personality type |

---

### providers.claude

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable Claude |
| `daily_limit` | int | 45 | Max queries per day |

---

### providers.openai

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable OpenAI |
| `daily_limit` | int | 40 | Max queries per day |
| `api_key_env` | string | "OPENAI_API_KEY" | Environment variable for API key |

---

### providers.gemini

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable Gemini |
| `daily_limit` | int | 100 | Max queries per day |
| `api_key_env` | string | "GEMINI_API_KEY" | Environment variable |
| `api_key_file` | string | null | File containing API key |

---

### providers.ollama

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable Ollama |
| `base_url` | string | "http://localhost:11434" | Ollama server URL |
| `models.default` | string | "llama3" | Default model |
| `models.code` | string | "codellama:13b" | Model for code tasks |
| `models.fast` | string | "llama3.2:3b" | Fast model for simple tasks |

---

### memory

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `conversation_retention_days` | int | 30 | Days to keep conversations |

---

### notifications

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `urgent_sound` | bool | true | Play sound for urgent alerts |
| `desktop_notifications` | bool | true | Show desktop notifications |
| `windows_toast` | bool | true | Use Windows toast notifications |

---

### voice

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | false | Enable voice mode |
| `whisper_model` | string | "base.en" | Whisper model size |
| `piper_voice` | string | "en_GB-alan-medium" | Piper voice model |
| `silence_threshold` | float | 0.03 | Microphone sensitivity |
| `max_record_seconds` | int | 30 | Max recording length |
| `speak_responses` | bool | true | Enable TTS responses |

---

### monitoring

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable monitoring |
| `interval` | int | 300 | Seconds between checks |

### monitoring.system

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable system monitoring |
| `cpu_threshold` | int | 80 | CPU warning threshold % |
| `memory_threshold` | int | 85 | Memory warning threshold % |
| `disk_threshold` | int | 90 | Disk warning threshold % |

### monitoring.git

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable git monitoring |
| `repos` | list | [] | Repository paths to monitor |
| `check_uncommitted` | bool | true | Check for uncommitted changes |
| `check_unpushed` | bool | true | Check for unpushed commits |

### monitoring.web

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | false | Enable web monitoring |
| `urls` | list | [] | URLs to monitor |
| `timeout` | int | 10 | Request timeout seconds |

---

### daemon

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ambient_mode` | bool | true | Enable ambient awareness |
| `task_check_interval` | int | 60 | Seconds between task checks |
| `tray.enabled` | bool | true | Enable system tray |
| `tray.show_status` | bool | true | Show status in tray |

---

### integrations.home_assistant

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | false | Enable Home Assistant |
| `url` | string | null | Home Assistant URL |
| `token_env` | string | "HA_TOKEN" | Token environment variable |
| `entities` | dict | {} | Entity ID mappings |

---

### integrations.google

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | false | Enable Google integration |
| `credentials_file` | string | null | OAuth credentials path |
| `scopes` | list | [] | API scopes to request |
| `calendar.reminder_minutes` | list | [15, 5] | Meeting reminder times |
| `email.important_senders` | list | [] | Priority email senders |
| `email.alert_on_important` | bool | true | Alert for important emails |

---

### anticipation

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | true | Enable anticipation engine |
| `learning` | bool | true | Learn new patterns |
| `confidence_threshold` | float | 0.70 | Min confidence for suggestions |
| `suggestion_frequency` | string | "occasional" | never, occasional, proactive |

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `HA_TOKEN` | Home Assistant token |

---

## See Also

- [[Configuration]] - Basic setup
- [[Troubleshooting]] - Common issues

---

#configuration #reference #yaml
