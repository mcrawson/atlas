---
title: Briefings
description: Morning, daily, and end-of-day reports
tags:
  - briefings
  - reports
  - productivity
created: 2024-02-10
---

# Briefings

Structured reports to keep you informed throughout the day.

---

## Briefing Types

| Command | When to Use |
|---------|-------------|
| `/morning` | Start of day - full overview |
| `/startsession` | Start of each session - quick status |
| `/briefing` | Mid-day check-in - quick status |
| `/endsession` | End of session - summary and exit |
| `/endday` | End of day - full report and tomorrow prep |

---

## Session vs Day Briefings

**Session** = Each time you open ATLAS
**Day** = Your entire workday

| Session Briefings | Day Briefings |
|-------------------|---------------|
| `/startsession` | `/morning` |
| `/endsession` | `/endday` |
| Quick, lightweight | Comprehensive |
| Shown automatically | On request |

---

## Session Start

Shown automatically when you open ATLAS (after the first session of the day):

```
[ATLAS]

┌──────────────────────────────────────────────────────┐
│                   SESSION START                       │
└──────────────────────────────────────────────────────┘

  Tuesday, February 11 • 2:30 PM
  Welcome back, sir. It's been 2h 15m since our last session.

  📋 3 pending tasks  •  ⚠️ Claude: 40/45

  What shall we work on, sir?
```

---

## Session End

End your session with a summary:

```
You: /endsession

[ATLAS]

┌──────────────────────────────────────────────────────┐
│                  SESSION COMPLETE                     │
└──────────────────────────────────────────────────────┘

  Tuesday, February 11 • 4:45 PM

  ┌─ This Session ─────────────────────────────────────┐
  │ Duration: 2h 15m
  │ Queries: 12
  │ Tasks completed: 2
  │ Primary AI: Claude (8 queries)
  └─────────────────────────────────────────────────────┘

  ┌─ Activity ──────────────────────────────────────────┐
  │ Code         ████████████ 8
  │ Research     ███ 3
  │ Review       █ 1
  └─────────────────────────────────────────────────────┘

  Have a productive day ahead, sir.
  I shall be here when you return.
```

---

## Morning Briefing

```
You: /morning

[ATLAS] Good morning, sir. Here's your briefing for Tuesday, February 11th:

📅 Today's Schedule:
  • 9:00 AM - Team standup (30 min)
  • 2:00 PM - Client call with Acme Corp (1 hour)
  • 4:30 PM - Code review session

📧 Email Summary:
  • 12 unread (3 important)
  • John Smith: "Project update needed"
  • GitHub: "PR #123 approved"

🖥️ System Status:
  • All systems nominal
  • Disk usage: 45%
  • Ollama: Running

📋 Background Tasks:
  • 2 tasks completed overnight
  • Use /queue completed for details

💡 Reminders:
  • Deploy staging environment
  • Review Q4 budget

🔄 Git Status:
  • atlas: 3 uncommitted changes
```

---

## Quick Briefing

For a faster mid-day check:

```
You: /briefing

[ATLAS] Quick status, sir:

📅 Next: Client call in 2 hours
📧 Email: 5 new since morning
🖥️ System: All clear
📋 Tasks: 1 completed, 2 pending
```

---

## End of Day Report

```
You: /endday

[ATLAS] End of day summary, sir:

✅ Completed Today:
  • 15 AI queries processed
  • 3 background tasks completed
  • Code review for PR #456

📊 Provider Usage:
  • Claude: 12/45
  • GPT: 8/40
  • Gemini: 5/100

📋 Pending for Tomorrow:
  • Research task: Kubernetes networking
  • Reminder: Team retrospective at 10 AM

💾 Session saved to memory.

Is there anything else before you go, sir?
```

---

## Briefing Content

### What's Included

| Section | Source |
|---------|--------|
| Schedule | Google Calendar |
| Email | Gmail integration |
| System | System monitoring |
| Tasks | Background queue |
| Git | Repository monitoring |
| Reminders | Memory system |

> [!note] Integrations Required
> Calendar and email require [[Calendar Integration]] and [[Email Integration]] setup.

### Customizing Content

Some sections only appear when relevant integrations are enabled:

```yaml
# config/atlas.yaml
integrations:
  google:
    enabled: true  # Enables calendar/email in briefings
  home_assistant:
    enabled: true  # Adds home status

monitoring:
  enabled: true    # Adds system status
  git:
    enabled: true  # Adds git status
```

---

## Proactive Briefings

ATLAS can deliver briefings automatically:

**Morning (if daemon running):**
- Notification at configured wake time
- "Good morning, sir. Shall I deliver your briefing?"

**Meeting Reminders:**
- 15 minutes before: "Sir, you have a meeting in 15 minutes"
- 5 minutes before: Final reminder

**End of Day:**
- Optionally triggered at configured time
- Or manually with `/endday`

---

## Briefing in Notifications

When running in ambient mode, briefing highlights appear as notifications:

> [!example] Windows Toast Example
> **ATLAS - Morning Briefing**
> 3 meetings today, 5 unread emails
> Click to open full briefing

---

## See Also

- [[Calendar Integration]] - Add calendar to briefings
- [[Email Integration]] - Add email summaries
- [[Proactive Monitoring]] - System status in briefings

---

#briefings #reports #productivity
