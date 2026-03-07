---
title: Commands
description: Complete command reference
tags:
  - commands
  - reference
created: 2024-02-10
---

# Commands

Complete reference for all ATLAS commands.

---

## Command Syntax

All commands start with `/`:
```
/command [arguments]
```

---

## General Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/quit` | Exit ATLAS |
| `/status` | Show provider usage and system status |
| `/version` | Show ATLAS version |

---

## Briefings

| Command | Description |
|---------|-------------|
| `/morning` | Full morning briefing (first session of day) |
| `/briefing` | Quick status briefing |
| `/startsession` | Session start briefing (shown automatically) |
| `/endsession` | Session end summary and exit |
| `/endday` | End of day report and wrap-up |

---

## Memory & Reminders

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/remember` | `<fact>` | Remember a fact about you |
| `/reminder` | `<text>` | Set a reminder |
| `/reminders` | | View pending reminders |
| `/memories` | | View remembered facts |
| `/forget` | `<type> [item]` | Forget something |

### Examples

```
/remember I prefer Python over JavaScript
/reminder Review PR at 3pm
/reminders
/forget reminder 3
/forget all reminders
```

---

## Background Tasks

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/queue add` | `<task>` | Add task to queue |
| `/queue status` | | Show queue status |
| `/queue completed` | | List completed tasks |
| `/queue result` | `<task_id>` | Get task result |
| `/queue cancel` | `<task_id>` | Cancel pending task |

### Examples

```
/queue add Research Kubernetes security best practices
/queue add --priority high Urgent security audit
/queue status
/queue result task_abc123
```

---

## Model Control

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/model` | `<name>` | Force specific model |
| `/model` | `auto` | Return to automatic routing |
| `/models` | | List available models |

### Model Names

| Name | Provider |
|------|----------|
| `claude` | Anthropic Claude |
| `gpt` | OpenAI GPT-4 |
| `gemini` | Google Gemini |
| `ollama` | Local Ollama |
| `auto` | Automatic routing |

### Examples

```
/model claude
/model gpt
/model auto
```

---

## Voice

| Command | Description |
|---------|-------------|
| `/voice` | Enter voice mode |
| `/voice off` | Exit voice mode |

---

## Monitoring & System

| Command | Description |
|---------|-------------|
| `/system` | Show system status |
| `/git` | Show git status for monitored repos |
| `/alerts` | Show recent alerts |

---

## Learning & Patterns

| Command | Description |
|---------|-------------|
| `/patterns` | View learned patterns |
| `/patterns clear` | Clear all patterns |
| `/habits` | View habit streaks |
| `/learning on` | Enable learning |
| `/learning off` | Disable learning |

---

## Smart Home

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/lights` | `on/off [room]` | Control lights |
| `/temp` | `<degrees>` | Set thermostat |
| `/home` | | Home status overview |

### Examples

```
/lights on office
/lights off
/temp 72
/home
```

---

## Project Context

| Command | Arguments | Description |
|---------|-----------|-------------|
| `/project set` | `<name> <context>` | Set project context |
| `/project` | `<name>` | Switch to project |
| `/projects` | | List projects |

### Examples

```
/project set Phoenix Real-time analytics platform
/project Phoenix
```

---

## Configuration

| Command | Description |
|---------|-------------|
| `/config` | Show current configuration |
| `/config reload` | Reload configuration file |

---

## Google Integration

| Command | Description |
|---------|-------------|
| `/calendar` | Show today's calendar |
| `/email` | Show email summary |

---

## Debug Commands

| Command | Description |
|---------|-------------|
| `/debug on` | Enable debug output |
| `/debug off` | Disable debug output |
| `/logs` | Show recent logs |

---

## Command Shortcuts

Some commands have shortcuts:

| Shortcut | Full Command |
|----------|--------------|
| `/q` | `/quit` |
| `/m` | `/morning` |
| `/s` | `/status` |
| `/h` | `/help` |

---

## See Also

- [[Quick Start]] - Getting started
- [[Configuration]] - Settings reference

---

#commands #reference
