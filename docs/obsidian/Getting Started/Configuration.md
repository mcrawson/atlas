---
title: Configuration
description: Customize ATLAS behavior and settings
tags:
  - configuration
  - settings
  - setup
created: 2024-02-10
---

# Configuration

All ATLAS settings are in `config/atlas.yaml`.

---

## Configuration File Location

```
~/ai-workspace/atlas/config/atlas.yaml
```

---

## Basic Structure

```yaml
atlas:
  name: "ATLAS"
  personality: "butler"

providers:
  # AI model configuration

memory:
  # Conversation retention

notifications:
  # Alert settings

monitoring:
  # Proactive monitoring

integrations:
  # External services

anticipation:
  # Learning engine
```

---

## Provider Configuration

### Claude (Anthropic)

```yaml
providers:
  claude:
    enabled: true
    daily_limit: 45
```

> [!note] Claude Authentication
> Uses existing Claude Code authentication. No API key needed if you're running from Claude Code.

### OpenAI (GPT)

```yaml
providers:
  openai:
    enabled: true
    daily_limit: 40
    api_key_env: "OPENAI_API_KEY"
```

Set the environment variable:
```bash
export OPENAI_API_KEY="sk-..."
```

### Google Gemini

```yaml
providers:
  gemini:
    enabled: true
    daily_limit: 100
    api_key_env: "GEMINI_API_KEY"
    api_key_file: "~/.gemini/api_key"
```

> [!tip] Multiple Auth Methods
> Gemini checks `api_key_env` first, then falls back to `api_key_file`.

### Ollama (Local)

```yaml
providers:
  ollama:
    enabled: true
    base_url: "http://localhost:11434"
    models:
      default: "llama3"
      code: "codellama:13b"
      fast: "llama3.2:3b"
```

---

## Memory Settings

```yaml
memory:
  conversation_retention_days: 30
```

| Setting | Description | Default |
|---------|-------------|---------|
| `conversation_retention_days` | Days to keep conversations | 30 |

---

## Notification Settings

```yaml
notifications:
  urgent_sound: true
  desktop_notifications: true
  windows_toast: true
```

| Setting | Description | Default |
|---------|-------------|---------|
| `urgent_sound` | Play sound for urgent alerts | true |
| `desktop_notifications` | Show desktop notifications | true |
| `windows_toast` | Use Windows toast notifications | true |

---

## Voice Settings

```yaml
voice:
  enabled: false
  whisper_model: "base.en"
  piper_voice: "en_GB-alan-medium"
```

See [[Voice Interface]] for full voice setup.

---

## Monitoring Settings

```yaml
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

  web:
    enabled: false
    urls: []
```

See [[Proactive Monitoring]] for details.

---

## Integration Settings

### Home Assistant

```yaml
integrations:
  home_assistant:
    enabled: false
    url: "http://homeassistant.local:8123"
    token_env: "HA_TOKEN"
    entities:
      office_lights: "light.office"
      bedroom_lights: "light.bedroom"
      thermostat: "climate.main"
```

See [[Smart Home]] for setup.

### Google Calendar & Gmail

```yaml
integrations:
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
```

See [[Calendar Integration]] and [[Email Integration]] for OAuth setup.

---

## Anticipation Engine

```yaml
anticipation:
  enabled: true
  learning: true
  confidence_threshold: 0.70
  suggestion_frequency: "occasional"
```

| Setting | Options | Description |
|---------|---------|-------------|
| `enabled` | true/false | Enable anticipation |
| `learning` | true/false | Learn from patterns |
| `confidence_threshold` | 0.0-1.0 | Min confidence for suggestions |
| `suggestion_frequency` | never, occasional, proactive | How often to suggest |

See [[Learning Engine]] for details.

---

## Environment Variables

ATLAS reads these environment variables:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API authentication |
| `GEMINI_API_KEY` | Google Gemini authentication |
| `HA_TOKEN` | Home Assistant long-lived token |

---

## Next Steps

- [[Configuration Reference]] - Complete YAML reference
- [[Troubleshooting]] - Common configuration issues

---

#configuration #settings #setup
