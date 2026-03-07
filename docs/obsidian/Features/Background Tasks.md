---
title: Background Tasks
description: Queue and daemon for async processing
tags:
  - tasks
  - queue
  - daemon
created: 2024-02-10
---

# Background Tasks

Queue research and processing tasks for ATLAS to handle in the background.

---

## Overview

Background tasks let you:
- Queue research for overnight processing
- Run time-consuming analysis without waiting
- Process multiple tasks while you work

---

## Queuing Tasks

### Add a Task

```
You: /queue add Research best practices for microservices architecture

[ATLAS] Very good, sir. I've queued that for background processing.
Task ID: task_abc123
```

### Check Queue Status

```
You: /queue status

[ATLAS] Background queue status:

Status     │ Count
───────────┼───────
Pending    │ 2
Processing │ 1
Completed  │ 5
Failed     │ 0
```

### View Completed Tasks

```
You: /queue completed

[ATLAS] Completed tasks:

1. Research microservices best practices
   Completed: 2 hours ago

2. Analyze Python async patterns
   Completed: Yesterday
```

### Get Task Result

```
You: /queue result task_abc123

[ATLAS] Results for "Research microservices best practices":

## Summary
Microservices architecture involves...

## Key Findings
1. Service boundaries...
2. Communication patterns...
```

---

## Daemon Installation

The ATLAS daemon processes background tasks continuously.

### Install systemd Service

```bash
# Copy service file
cp services/atlas.service ~/.config/systemd/user/

# Reload systemd
systemctl --user daemon-reload

# Enable auto-start
systemctl --user enable atlas

# Start the daemon
systemctl --user start atlas
```

### Check Daemon Status

```bash
systemctl --user status atlas
```

Expected output:
```
● atlas.service - ATLAS Background Daemon
   Loaded: loaded
   Active: active (running)
```

### Stop/Restart Daemon

```bash
# Stop
systemctl --user stop atlas

# Restart
systemctl --user restart atlas

# View logs
journalctl --user -u atlas -f
```

---

## Task Priority

Tasks are processed in priority order:

| Priority | Description |
|----------|-------------|
| High | Urgent tasks, user-flagged |
| Normal | Standard queued tasks |
| Low | Background optimization, learning |

Set priority when queuing:
```
You: /queue add --priority high Critical security audit needed
```

---

## Task Types

ATLAS handles various background task types:

**Research:**
```
/queue add Research quantum computing basics
```

**Analysis:**
```
/queue add Analyze our API response times for the past week
```

**Summarization:**
```
/queue add Summarize the latest Python 3.12 release notes
```

**Code Review:**
```
/queue add Review the authentication module for security issues
```

---

## Briefing Integration

Completed background tasks appear in your briefings:

```
You: /morning

[ATLAS] Good morning, sir.

📋 Overnight Tasks:
  ✓ Research microservices best practices
  ✓ Analyze API performance data

  Use /queue result <id> for details.
```

---

## Configuration

```yaml
# config/atlas.yaml
daemon:
  ambient_mode: true
  task_check_interval: 60  # seconds
```

---

## Troubleshooting

> [!warning] Daemon Not Running
> If tasks aren't processing, check the daemon:
> ```bash
> systemctl --user status atlas
> ```

> [!tip] View Logs
> For debugging:
> ```bash
> journalctl --user -u atlas --since "1 hour ago"
> ```

---

## See Also

- [[Briefings]] - Task results in briefings
- [[Configuration]] - Daemon settings

---

#tasks #queue #daemon
