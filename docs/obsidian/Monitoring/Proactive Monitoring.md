---
title: Proactive Monitoring
description: System, git, and web alerts
tags:
  - monitoring
  - alerts
  - system
created: 2024-02-10
---

# Proactive Monitoring

ATLAS watches your systems and speaks up when something needs attention.

---

## Overview

ATLAS monitors:
- **System** - CPU, memory, disk, services
- **Git** - Uncommitted changes, unpushed commits
- **Web** - Website/API uptime

When issues are detected:
> "Sir, I noticed your disk is at 92% capacity. Shall I help identify large files?"

---

## System Monitoring

### What's Monitored

| Metric | Default Threshold | Alert |
|--------|------------------|-------|
| CPU | 80% | Warning when sustained |
| Memory | 85% | Warning when exceeded |
| Disk | 90% | Urgent when exceeded |
| Ollama | Service status | Info if not running |

### Configuration

```yaml
monitoring:
  enabled: true
  interval: 300  # Check every 5 minutes

  system:
    enabled: true
    cpu_threshold: 80
    memory_threshold: 85
    disk_threshold: 90
```

### Example Alerts

```
[ATLAS] Sir, I noticed the following:
  ⚠️ Disk usage is at 92% on /home
  Would you like me to help identify large files?
```

```
[ATLAS] Sir, memory usage is quite high at 87%.
  Top processes: Chrome (2.1GB), VS Code (1.8GB)
  Shall I suggest some cleanup options?
```

---

## Git Monitoring

### What's Monitored

| Check | Description |
|-------|-------------|
| Uncommitted changes | Files modified but not committed |
| Unpushed commits | Local commits not pushed to remote |
| Stash entries | Items in git stash |

### Configuration

```yaml
monitoring:
  git:
    enabled: true
    repos:
      - "~/ai-workspace/atlas"
      - "~/projects/myapp"
    check_uncommitted: true
    check_unpushed: true
```

### Example Alerts

```
[ATLAS] Sir, repository status:
  📁 atlas: 3 uncommitted changes, 2 unpushed commits

  Would you like me to show the changes?
```

```
[ATLAS] Sir, you have uncommitted work in atlas:
  • Modified: atlas/core/butler.py
  • Modified: config/atlas.yaml
  • New: atlas/monitoring/system_monitor.py
```

---

## Web Monitoring

### What's Monitored

| Check | Description |
|-------|-------------|
| Availability | Is the URL responding? |
| Response time | How fast is the response? |
| Status code | HTTP status (200, 500, etc.) |

### Configuration

```yaml
monitoring:
  web:
    enabled: true
    urls:
      - "https://myapp.example.com/health"
      - "https://api.example.com/status"
    timeout: 10  # seconds
```

### Example Alerts

```
[ATLAS] Sir, I noticed a service issue:
  🔴 https://api.example.com is not responding
  Last successful check: 10 minutes ago

  Shall I investigate further?
```

```
[ATLAS] Sir, response time alert:
  ⚠️ https://myapp.example.com is slow (3.2s response)
  Normal response time: ~200ms
```

---

## Alert Severity Levels

| Level | Icon | Notification |
|-------|------|--------------|
| Info | ℹ️ | Shown in briefing |
| Warning | ⚠️ | Desktop notification |
| Urgent | 🔴 | Toast + sound |

### Configuration

```yaml
notifications:
  urgent_sound: true
  desktop_notifications: true
  windows_toast: true
```

---

## Viewing Alerts

### In Briefings

Alerts appear in morning/daily briefings:

```
You: /morning

[ATLAS] Good morning, sir.

🔔 Alerts:
  ⚠️ Disk at 92% capacity
  ℹ️ 5 uncommitted changes in atlas
```

### Check Current Status

```
You: /system

[ATLAS] Current system status:

CPU:    45% ✓
Memory: 72% ✓
Disk:   92% ⚠️
Ollama: Running ✓
```

---

## Custom Monitoring

Add monitoring for specific services:

```python
# atlas/monitoring/custom_monitor.py
from atlas.monitoring.monitor import Monitor, Alert, AlertSeverity

class CustomMonitor(Monitor):
    name = "custom"
    check_interval = 600  # 10 minutes

    async def check(self) -> List[Alert]:
        # Your monitoring logic
        if something_wrong:
            return [Alert(
                monitor_name=self.name,
                severity=AlertSeverity.WARNING,
                message="Something needs attention",
                action_suggestion="Shall I investigate?"
            )]
        return []
```

---

## See Also

- [[Configuration]] - Monitoring settings
- [[Briefings]] - Alerts in briefings
- [[Background Tasks#Daemon Installation]] - Daemon for continuous monitoring

---

#monitoring #alerts #system
