---
title: Python API
description: Programmatic usage of ATLAS
tags:
  - api
  - python
  - development
created: 2024-02-10
---

# Python API

Use ATLAS programmatically in your Python projects.

---

## Basic Usage

```python
from atlas.core.butler import Butler
from atlas.core.config import Config

# Load configuration
config = Config.load("config/atlas.yaml")

# Create butler instance
butler = Butler(config)

# Send a query
response = await butler.query("What's the weather like?")
print(response)
```

---

## Configuration

### Load Config

```python
from atlas.core.config import Config

# From default location
config = Config.load()

# From custom path
config = Config.load("/path/to/atlas.yaml")

# Access settings
print(config.providers.claude.enabled)
print(config.monitoring.interval)
```

### Modify Config

```python
config = Config.load()
config.providers.openai.daily_limit = 50
config.save()
```

---

## Multi-Model Routing

### Use Router Directly

```python
from atlas.routing.router import Router
from atlas.routing.usage import UsageTracker

tracker = UsageTracker()
router = Router(config, tracker)

# Route a query
provider, model = await router.route("Write a Python function")
print(f"Selected: {provider} / {model}")
```

### Query Specific Provider

```python
from atlas.routing.providers import OpenAIProvider, ClaudeProvider

# OpenAI
openai = OpenAIProvider(config.providers.openai)
response = await openai.query("Hello!")

# Claude
claude = ClaudeProvider(config.providers.claude)
response = await claude.query("Hello!")
```

---

## Background Tasks

### Queue Tasks

```python
from atlas.tasks.queue import TaskQueue

queue = TaskQueue("data/tasks.db")

# Add task
task_id = await queue.add(
    task="Research Python async patterns",
    priority="normal"
)

# Check status
status = await queue.get_status(task_id)

# Get result
result = await queue.get_result(task_id)
```

### Process Tasks

```python
from atlas.tasks.worker import Worker

worker = Worker(queue, router)

# Process one task
await worker.process_next()

# Process all pending
await worker.process_all()
```

---

## Memory System

### Conversations

```python
from atlas.memory.manager import MemoryManager

memory = MemoryManager("memory/")

# Save conversation
await memory.save_conversation(
    messages=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Good day, sir"}
    ]
)

# Load recent
recent = await memory.get_recent_conversations(days=7)
```

### Preferences

```python
# Remember something
await memory.remember("user prefers dark mode")

# Recall
facts = await memory.get_memories()
```

### Reminders

```python
from datetime import datetime, timedelta

# Set reminder
await memory.add_reminder(
    text="Check deployment",
    when=datetime.now() + timedelta(hours=2)
)

# Get pending
reminders = await memory.get_pending_reminders()
```

---

## Monitoring

### System Monitor

```python
from atlas.monitoring.system_monitor import SystemMonitor

monitor = SystemMonitor(config.monitoring.system)

# Run check
alerts = await monitor.check()

for alert in alerts:
    print(f"{alert.severity}: {alert.message}")
```

### Git Monitor

```python
from atlas.monitoring.git_monitor import GitMonitor

monitor = GitMonitor(config.monitoring.git)
alerts = await monitor.check()
```

### Custom Monitor

```python
from atlas.monitoring.monitor import Monitor, Alert, AlertSeverity

class CustomMonitor(Monitor):
    name = "custom"
    check_interval = 300

    async def check(self) -> List[Alert]:
        # Your logic here
        if issue_detected:
            return [Alert(
                monitor_name=self.name,
                severity=AlertSeverity.WARNING,
                message="Issue detected",
                action_suggestion="Shall I investigate?"
            )]
        return []
```

---

## Integrations

### Home Assistant

```python
from atlas.integrations.home_assistant import HomeAssistantClient

ha = HomeAssistantClient(
    url="http://homeassistant.local:8123",
    token=os.environ["HA_TOKEN"]
)

# Control devices
await ha.turn_on("light.office")
await ha.set_brightness("light.office", 50)
await ha.set_temperature("climate.main", 72)

# Get state
state = await ha.get_state("climate.main")
print(f"Temperature: {state['attributes']['current_temperature']}")
```

### Google Calendar

```python
from atlas.integrations.calendar import CalendarClient

calendar = CalendarClient(credentials_file)

# Get events
events = await calendar.get_today_events()

for event in events:
    print(f"{event.start}: {event.title}")

# Get next meeting
next_meeting = await calendar.get_next_meeting()
```

### Gmail

```python
from atlas.integrations.email import EmailClient

email = EmailClient(credentials_file)

# Unread count
count = await email.get_unread_count()

# Important emails
important = await email.get_important_unread(limit=5)

# Summary
summary = await email.get_summary()
```

---

## Learning Engine

### Pattern Tracking

```python
from atlas.learning.patterns import PatternTracker

tracker = PatternTracker()

# Track a query
tracker.track_query(
    query="Check email",
    time=datetime.now(),
    context={"previous_action": "login"}
)

# Get patterns
time_patterns = tracker.get_time_patterns()
context_patterns = tracker.get_context_patterns()
```

### Suggestions

```python
from atlas.learning.suggestions import SuggestionEngine

engine = SuggestionEngine(tracker)

# Get suggestions
suggestions = await engine.get_suggestions(
    time=datetime.now(),
    context={"current_action": "git push"}
)

for suggestion in suggestions:
    print(f"Suggest: {suggestion.action} ({suggestion.confidence})")
```

---

## Notifications

### Windows Toast

```python
from atlas.notifications.windows_toast import WindowsToast

toast = WindowsToast()

# Simple notification
toast.send("ATLAS", "Task completed successfully")

# With buttons
toast.send_with_buttons(
    title="Meeting in 15 minutes",
    message="Client call with Acme Corp",
    buttons=["Open Link", "Dismiss"]
)
```

---

## Voice

### Speech to Text

```python
from atlas.voice.stt import SpeechToText

stt = SpeechToText(model="base.en")

# Transcribe file
text = stt.transcribe("audio.wav")

# Real-time (blocking)
text = stt.listen()
```

### Text to Speech

```python
from atlas.voice.tts import TextToSpeech

tts = TextToSpeech(voice="en_GB-alan-medium")

# Speak
tts.speak("Good morning, sir.")

# Save to file
tts.save("Good morning, sir.", "greeting.wav")
```

---

## Full Example

```python
import asyncio
from atlas.core.butler import Butler
from atlas.core.config import Config

async def main():
    # Initialize
    config = Config.load()
    butler = Butler(config)

    # Interactive loop
    while True:
        user_input = input("You: ")

        if user_input.lower() in ["/quit", "exit"]:
            print(butler.farewell())
            break

        response = await butler.query(user_input)
        print(f"[ATLAS] {response}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## See Also

- [[Configuration Reference]] - Config options
- [[Commands]] - CLI commands

---

#api #python #development
