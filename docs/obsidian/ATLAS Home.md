---
title: ATLAS Documentation
description: Automated Thinking, Learning & Advisory System
tags:
  - atlas
  - index
  - moc
aliases:
  - ATLAS
  - Home
created: 2024-02-10
---

# ATLAS

> *"Very good, sir. I remain at your service."*

**Automated Thinking, Learning & Advisory System** - A refined British butler AI assistant with multi-model intelligence, proactive monitoring, and JARVIS-like awareness.

---

## Quick Navigation

### Getting Started
- [[Installation]] - Set up ATLAS on your system
- [[Quick Start]] - Your first conversation
- [[Configuration]] - Customize ATLAS behavior

### Core Features
- [[Multi-Model Routing]] - Intelligent AI selection
- [[Background Tasks]] - Queue and daemon
- [[Briefings]] - Morning, daily, end-of-day reports
- [[Memory System]] - Conversations, decisions, reminders

### Voice & Access
- [[Voice Interface]] - Whisper + Piper setup
- [[Hotkey Activation]] - Windows hotkey access

### Monitoring & Awareness
- [[Proactive Monitoring]] - System, git, web alerts
- [[Learning Engine]] - Pattern detection and anticipation

### Integrations
- [[Smart Home]] - Home Assistant control
- [[Calendar Integration]] - Google Calendar
- [[Email Integration]] - Gmail awareness

### Reference
- [[Commands]] - Complete command reference
- [[Configuration Reference]] - Full YAML options
- [[Troubleshooting]] - Common issues and fixes
- [[Python API]] - Programmatic usage

---

## At a Glance

```
./scripts/atlas
```

| Command | Action |
|---------|--------|
| `/help` | Show all commands |
| `/status` | Provider usage |
| `/morning` | Morning briefing |
| `/queue add <task>` | Background task |
| `/quit` | Exit |

---

## Feature Overview

```mermaid
graph TB
    A[ATLAS] --> B[Multi-Model Routing]
    A --> C[Background Tasks]
    A --> D[Monitoring]
    A --> E[Integrations]
    A --> F[Learning]

    B --> B1[Claude]
    B --> B2[GPT]
    B --> B3[Gemini]
    B --> B4[Ollama]

    D --> D1[System]
    D --> D2[Git]
    D --> D3[Web]

    E --> E1[Home Assistant]
    E --> E2[Google Calendar]
    E --> E3[Gmail]
```

---

## Tags

#atlas #documentation #ai-assistant #butler

---

## Recent Changes

- Initial documentation created
- All 11 phases documented
- Obsidian vault structure established
