---
title: Learning Engine
description: Pattern detection and anticipation
tags:
  - learning
  - patterns
  - anticipation
created: 2024-02-10
---

# Learning Engine

ATLAS learns your patterns and anticipates your needs.

---

## Overview

The learning engine:
- Tracks your usage patterns
- Identifies recurring behaviors
- Makes proactive suggestions
- All learning is local and private

---

## How It Works

### Pattern Detection

ATLAS observes:
- **Time patterns** - When you do certain things
- **Context patterns** - What follows what
- **Preference patterns** - How you like things done

### Confidence Building

Patterns need multiple observations before ATLAS acts:
1. First occurrence: Noted
2. 3+ occurrences: Pattern recognized
3. 70%+ confidence: Suggestions offered

---

## Time-Based Patterns

ATLAS learns your schedule:

| Pattern Detected | Suggestion |
|------------------|------------|
| Check email at 9 AM daily | "Good morning, sir. You have 5 new emails." |
| Run tests at 5 PM | "Shall I run the test suite, sir?" |
| Review PRs on Monday | "There are 3 PRs awaiting review, sir." |

### Example

After a week of checking email at 9 AM:
```
[ATLAS] Good morning, sir. I've noticed you typically
check your email around this time. You have 8 unread
messages, 2 of which appear important.
```

---

## Context-Based Patterns

ATLAS notices sequences:

| After This | You Usually | Suggestion |
|------------|-------------|------------|
| `git push` | Run tests | "Shall I run the tests, sir?" |
| Writing code | Need docs | Offers relevant documentation |
| Starting work | Check calendar | Shows today's schedule |

### Example

After you push code several times, ATLAS learns:
```
[ATLAS] Push complete, sir. Based on your usual workflow,
shall I run the test suite?
```

---

## View Learned Patterns

```
You: /patterns

[ATLAS] Here are the patterns I've learned, sir:

Time Patterns:
  ✓ Email check at 9:00 AM (85% confidence, 12 observations)
  ✓ End-of-day commit at 5:30 PM (72% confidence, 8 observations)

Context Patterns:
  ✓ After git push → run tests (78% confidence, 15 observations)
  ✓ After meeting → check email (71% confidence, 10 observations)

Learning:
  • Started monitoring for afternoon patterns
  • Tracking code review preferences
```

---

## Habit Tracking

ATLAS tracks productive habits:

```
You: /habits

[ATLAS] Your habit streaks, sir:

🔥 Active Streaks:
  • Morning briefing: 5 days
  • Daily commit: 12 days
  • Code review: 3 days

📊 Statistics:
  • Most productive hour: 10 AM
  • Preferred AI: Claude for reviews
  • Average session length: 45 min
```

---

## Configuration

```yaml
anticipation:
  enabled: true
  learning: true
  confidence_threshold: 0.70
  suggestion_frequency: "occasional"
```

| Setting | Options | Description |
|---------|---------|-------------|
| `enabled` | true/false | Master switch |
| `learning` | true/false | Learn new patterns |
| `confidence_threshold` | 0.0-1.0 | Min confidence for suggestions |
| `suggestion_frequency` | never, occasional, proactive | How often to suggest |

### Frequency Levels

| Level | Behavior |
|-------|----------|
| never | No unsolicited suggestions |
| occasional | Only high-confidence suggestions |
| proactive | Actively suggest based on patterns |

---

## Privacy & Control

> [!info] Local Only
> All pattern data is stored locally. Nothing is sent to external servers.

### Delete Patterns

```
You: /patterns clear

[ATLAS] All learned patterns have been cleared, sir.
```

### Disable Learning

```yaml
anticipation:
  learning: false  # Stop learning new patterns
```

Or in conversation:
```
You: /learning off

[ATLAS] Learning disabled, sir. I'll use existing
patterns but won't learn new ones.
```

### View Raw Data

Pattern data is stored in:
```
~/.config/atlas/patterns.yaml
```

---

## Examples in Action

### Morning Routine

```
[9:00 AM]
[ATLAS] Good morning, sir. Based on your usual routine:

📧 Email: 12 unread (3 important)
📅 First meeting: 10:00 AM standup
☕ Shall I start with your briefing?
```

### Post-Push Workflow

```
You: git push origin main

[ATLAS] Push complete, sir. I notice you typically
run tests after pushing. Shall I:
  1. Run the test suite
  2. Check CI status
  3. Neither

[1]

[ATLAS] Running tests, sir...
```

### End of Day

```
[5:30 PM]
[ATLAS] Sir, it's about the time you usually wrap up.

Today's summary:
  • 23 queries processed
  • 2 background tasks completed

You have 2 uncommitted changes. Shall I help
with an end-of-day commit?
```

---

## See Also

- [[Configuration]] - Anticipation settings
- [[Memory System]] - Related persistence
- [[Proactive Monitoring]] - Alert system

---

#learning #patterns #anticipation
