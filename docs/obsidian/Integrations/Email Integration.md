---
title: Email Integration
description: Gmail awareness and summaries
tags:
  - email
  - gmail
  - google
created: 2024-02-10
---

# Email Integration

Stay on top of important emails without context switching.

---

## Overview

ATLAS integrates with Gmail to:
- Show unread count in briefings
- Highlight important emails
- Summarize email content
- Alert on urgent messages

> [!note] Read-Only
> ATLAS only reads emails. It cannot send, delete, or modify messages.

---

## Setup

### 1. Google Cloud Project

If you completed [[Calendar Integration]], use the same project. Otherwise:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create/select project: "ATLAS"
3. Enable Gmail API
4. Use existing OAuth credentials

### 2. Add Gmail Scope

```yaml
# config/atlas.yaml
integrations:
  google:
    enabled: true
    credentials_file: "~/.config/atlas/google_credentials.json"
    scopes:
      - calendar.readonly
      - gmail.readonly  # Add this
    email:
      important_senders:
        - "boss@company.com"
        - "client@important.com"
```

### 3. Re-authenticate

If adding Gmail after Calendar:
```bash
rm ~/.config/atlas/google_tokens.json
./scripts/atlas setup-google
```

---

## Usage

### Check Email Status

```
You: Any important emails?

[ATLAS] Email summary, sir:

📧 12 unread messages (3 important)

Important:
  • John Smith (2 hours ago)
    "Project deadline update"

  • GitHub (5 hours ago)
    "PR #456 approved"

  • AWS (Yesterday)
    "Billing alert - unusual activity"

Shall I summarize any of these, sir?
```

### Unread Count

```
You: How many emails do I have?

[ATLAS] You have 12 unread emails, sir.
3 are marked important or from priority senders.
```

### Email Summary

```
You: Summarize the email from John

[ATLAS] Summary of John Smith's email, sir:

Subject: Project deadline update
Received: 2 hours ago

Key points:
  • Deadline moved from Friday to next Monday
  • Client requested additional features
  • Needs your input on scope changes by tomorrow

This appears to require action, sir.
```

---

## Important Senders

Configure priority senders for highlighting:

```yaml
email:
  important_senders:
    - "ceo@company.com"
    - "hr@company.com"
    - "*@important-client.com"  # Wildcard
```

Emails from these senders:
- Always shown in briefings
- Trigger notifications
- Appear first in summaries

---

## In Briefings

```
You: /morning

[ATLAS] Good morning, sir.

📧 Email Summary:
  • 15 unread (4 important)

  Important messages:
    • CEO: "Q1 Strategy meeting" (1 hour ago)
    • GitHub: "Security alert" (3 hours ago)
    • Client: "Contract renewal" (Yesterday)

  Use "summarize email from [sender]" for details.
```

---

## Alerts

ATLAS can notify you of urgent emails:

```
[ATLAS notification]
📧 Urgent email from CEO
Subject: "Immediate attention needed"
Received just now
```

### Configure Alerts

```yaml
email:
  important_senders:
    - "ceo@company.com"
  alert_on_important: true
```

---

## Privacy

> [!info] Data Handling
> - Emails are read in real-time, not stored locally
> - Only metadata (sender, subject, snippet) is cached briefly
> - Full content only fetched when you request summaries
> - AI summaries use your configured provider

---

## Troubleshooting

> [!warning] Permission Denied
> Ensure Gmail API is enabled:
> 1. Google Cloud Console → APIs & Services
> 2. Enable "Gmail API"
> 3. Re-authenticate

> [!warning] No Emails Showing
> Check scopes include `gmail.readonly`:
> ```bash
> rm ~/.config/atlas/google_tokens.json
> ./scripts/atlas setup-google
> ```

> [!tip] Rate Limits
> Gmail API has quotas. ATLAS caches results to minimize API calls.
> Heavy usage may hit limits temporarily.

---

## See Also

- [[Calendar Integration]] - Same OAuth setup
- [[Briefings]] - Email in briefings
- [[Configuration]] - Google settings

---

#email #gmail #google
