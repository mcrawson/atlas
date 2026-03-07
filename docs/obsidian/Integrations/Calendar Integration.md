---
title: Calendar Integration
description: Google Calendar integration
tags:
  - calendar
  - google
  - schedule
created: 2024-02-10
---

# Calendar Integration

View your schedule and get meeting reminders.

---

## Overview

ATLAS integrates with Google Calendar to:
- Show today's schedule in briefings
- Remind you before meetings
- Answer schedule questions
- Help with meeting prep

---

## Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project: "ATLAS"
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials JSON

### 2. Save Credentials

```bash
mkdir -p ~/.config/atlas
mv ~/Downloads/credentials.json ~/.config/atlas/google_credentials.json
```

### 3. Configure ATLAS

```yaml
# config/atlas.yaml
integrations:
  google:
    enabled: true
    credentials_file: "~/.config/atlas/google_credentials.json"
    scopes:
      - calendar.readonly
    calendar:
      reminder_minutes: [15, 5]
```

### 4. Authenticate

```bash
./scripts/atlas setup-google
```

This opens a browser for OAuth consent. After approval, tokens are saved to `~/.config/atlas/google_tokens.json`.

---

## Usage

### View Today's Schedule

```
You: What's on my calendar today?

[ATLAS] Your schedule for today, sir:

📅 Tuesday, February 11th:

  9:00 AM - Team standup (30 min)
    Location: Zoom

  11:00 AM - 1:1 with Sarah (1 hour)
    Location: Conference Room B

  2:00 PM - Client call - Acme Corp (1 hour)
    Location: Google Meet

  4:30 PM - Code review session (30 min)
    No location specified
```

### Check Upcoming Events

```
You: What's my next meeting?

[ATLAS] Your next meeting is the Team standup
in 45 minutes, sir. It's a 30-minute Zoom call.

Shall I prepare anything for it?
```

```
You: What do I have tomorrow?

[ATLAS] Tomorrow's schedule, sir:

  10:00 AM - Sprint planning (2 hours)
  3:00 PM - Interview - Senior Developer (1 hour)
```

### Week Overview

```
You: What does my week look like?

[ATLAS] This week's overview, sir:

  Monday: 3 meetings (4 hours total)
  Tuesday: 4 meetings (3.5 hours) ← Today
  Wednesday: 2 meetings (2 hours)
  Thursday: 5 meetings (4.5 hours) - Busy day
  Friday: 1 meeting (1 hour)

Thursday appears quite packed, sir.
```

---

## Meeting Reminders

ATLAS reminds you before meetings:

### 15 Minutes Before
```
[ATLAS] Sir, you have a meeting in 15 minutes:
  📅 Client call - Acme Corp
  📍 Google Meet

Shall I open the meeting link?
```

### 5 Minutes Before
```
[ATLAS] Sir, the Acme Corp call starts in 5 minutes.
The Google Meet link is ready when you are.
```

### Configuration

```yaml
calendar:
  reminder_minutes: [15, 5]  # Remind at 15 and 5 minutes
```

---

## In Briefings

Calendar appears in morning briefings:

```
You: /morning

[ATLAS] Good morning, sir.

📅 Today's Schedule:
  • 9:00 AM - Team standup (30 min)
  • 11:00 AM - 1:1 with Sarah (1 hour)
  • 2:00 PM - Client call (1 hour)
  • 4:30 PM - Code review (30 min)

  Total: 4 meetings, 3 hours blocked
```

---

## Free Time

```
You: When am I free today?

[ATLAS] Your available slots today, sir:

  • 9:30 AM - 11:00 AM (1.5 hours)
  • 12:00 PM - 2:00 PM (2 hours)
  • 3:00 PM - 4:30 PM (1.5 hours)
  • After 5:00 PM

The longest block is around lunch, sir.
```

---

## Troubleshooting

> [!warning] Authentication Failed
> Re-run the OAuth flow:
> ```bash
> rm ~/.config/atlas/google_tokens.json
> ./scripts/atlas setup-google
> ```

> [!warning] No Events Showing
> Check calendar permissions:
> - Ensure the calendar is shared with your Google account
> - Verify `calendar.readonly` scope is enabled

> [!tip] Multiple Calendars
> ATLAS shows events from your primary calendar by default.
> Contact calendars and subscribed calendars are included.

---

## See Also

- [[Email Integration]] - Gmail setup (same OAuth)
- [[Briefings]] - Calendar in briefings
- [[Configuration]] - Google settings

---

#calendar #google #schedule
