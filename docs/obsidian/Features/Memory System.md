---
title: Memory System
description: Persistent memory for conversations and preferences
tags:
  - memory
  - persistence
  - context
created: 2024-02-10
---

# Memory System

ATLAS remembers conversations, decisions, and your preferences.

---

## Memory Types

| Type | Purpose | Storage |
|------|---------|---------|
| Conversations | Chat history | SQLite |
| Decisions | Important choices | Markdown |
| Preferences | Your likes/dislikes | YAML |
| Reminders | Things to remember | SQLite |
| Projects | Project context | Markdown |

---

## Remember Command

Store facts about yourself:

```
You: /remember I prefer dark mode in all applications

[ATLAS] Noted, sir. I'll remember that preference.
```

```
You: /remember My main project is called Phoenix

[ATLAS] Understood, sir. I'll keep that in mind.
```

### View Remembered Facts

```
You: /memories

[ATLAS] Here's what I remember about you, sir:

Preferences:
  • Prefers dark mode in all applications
  • Uses tabs over spaces
  • Timezone: EST

Projects:
  • Main project: Phoenix
  • Secondary: Atlas development

Technical:
  • Primary language: Python
  • Editor: VS Code
```

---

## Reminders

### Set a Reminder

```
You: /reminder Check deployment status at 3pm

[ATLAS] Very good, sir. I'll remind you at 3:00 PM.
```

```
You: /reminder Review PR #123 tomorrow morning

[ATLAS] Reminder set for tomorrow morning, sir.
```

### View Pending Reminders

```
You: /reminders

[ATLAS] Your pending reminders:

Today:
  • 3:00 PM - Check deployment status

Tomorrow:
  • 9:00 AM - Review PR #123
```

### Reminder Delivery

When a reminder is due:
- Desktop notification appears
- ATLAS mentions it in next interaction
- Shows in briefings

---

## Conversation History

ATLAS maintains conversation context:

### Within a Session
- Full context of current conversation
- References previous questions/answers

### Across Sessions
- Remembers recent conversations (configurable retention)
- Can recall "what we discussed yesterday"

```
You: What did we talk about yesterday?

[ATLAS] Yesterday we discussed:
  • Python async patterns
  • Your Phoenix project deployment
  • Kubernetes networking issues
```

---

## Project Memory

Track project-specific context:

```
You: /project set Phoenix We're building a real-time analytics platform

[ATLAS] Project context saved for Phoenix, sir.
```

When you mention a project, ATLAS recalls its context:

```
You: Let's continue working on Phoenix

[ATLAS] Certainly, sir. Phoenix is your real-time analytics
platform. Last session we were working on the data pipeline.
Shall we continue from there?
```

---

## Memory Storage

```
~/ai-workspace/atlas/memory/
├── conversations/       # Conversation logs
│   └── 2024-02-11.md
├── decisions/          # Important decisions
│   └── architecture.md
├── projects/           # Project contexts
│   └── phoenix.md
└── briefings/          # Past briefings
    └── 2024-02-11.md
```

---

## Configuration

```yaml
# config/atlas.yaml
memory:
  conversation_retention_days: 30
```

| Setting | Description | Default |
|---------|-------------|---------|
| `conversation_retention_days` | Days to keep conversation history | 30 |

---

## Privacy

> [!info] Local Storage Only
> All memory is stored locally on your machine. Nothing is sent to external servers except API queries to AI providers.

### Clear Memory

```
You: /forget all reminders

[ATLAS] All reminders cleared, sir.
```

```
You: /forget preference dark mode

[ATLAS] I've forgotten that preference, sir.
```

---

## See Also

- [[Configuration]] - Memory settings
- [[Briefings]] - Memory in briefings

---

#memory #persistence #context
