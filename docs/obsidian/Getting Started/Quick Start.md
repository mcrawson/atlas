---
title: Quick Start
description: Your first conversation with ATLAS
tags:
  - getting-started
  - tutorial
created: 2024-02-10
---

# Quick Start

Your first conversation with ATLAS.

---

## Starting ATLAS

```bash
cd ~/ai-workspace/atlas
source .venv/bin/activate
./scripts/atlas
```

You'll see:
```
[ATLAS] Good morning, sir. How may I be of service?
```

---

## Basic Conversation

Simply type your question or request:

```
You: Write a Python function to check if a number is prime

[ATLAS] Very good, sir. Here's a prime checking function:

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True

Shall I explain the algorithm, sir?
```

---

## Essential Commands

| Command | What It Does |
|---------|--------------|
| `/help` | Show all available commands |
| `/status` | View provider usage and quotas |
| `/morning` | Get your morning briefing |
| `/quit` | Exit ATLAS |

> [!tip] Command Shortcut
> All commands start with `/`. Type `/help` anytime to see the full list.

---

## Check Provider Status

```
You: /status

[ATLAS] Current provider status, sir:

Provider    │ Used Today │ Limit │ Available
────────────┼────────────┼───────┼──────────
Claude      │ 5          │ 45    │ ✓
GPT-4       │ 12         │ 40    │ ✓
Gemini      │ 3          │ 100   │ ✓
Ollama      │ Local      │ ∞     │ ✓
```

---

## Get a Briefing

```
You: /morning

[ATLAS] Good morning, sir. Here's your briefing:

📅 Schedule:
  • 10:00 AM - Team standup
  • 2:00 PM - Client call

📧 Email:
  • 5 unread (2 important)

🖥️ System:
  • All systems nominal
  • Disk: 45% used

📋 Tasks:
  • 2 background tasks completed overnight
```

---

## Queue Background Research

```
You: /queue add Research best practices for Python async patterns

[ATLAS] Very good, sir. I've queued that for background processing.
Task ID: task_abc123
```

Check status later:
```
You: /queue status

[ATLAS] Background queue status:
  • Pending: 1
  • Processing: 0
  • Completed: 3
```

---

## Force a Specific Model

```
You: /model claude
You: Analyze this code review...

[ATLAS] Using Claude for this query, sir.
```

Reset to automatic routing:
```
You: /model auto
```

---

## Save Information

**Remember a fact about yourself:**
```
You: /remember I prefer tabs over spaces

[ATLAS] Noted, sir. I'll remember that preference.
```

**Set a reminder:**
```
You: /reminder Check deployment status at 3pm

[ATLAS] Very good, sir. I'll remind you at 3:00 PM.
```

---

## Exiting

```
You: /quit

[ATLAS] Very good, sir. Until next time.
```

---

## Next Steps

- [[Configuration]] - Customize ATLAS behavior
- [[Multi-Model Routing]] - Understand how queries are routed
- [[Commands]] - Full command reference

---

#quick-start #tutorial #getting-started
