# ATLAS Development Session
**Date:** 2026-02-10

## Summary
This session covered performance optimizations, memory fixes, and various improvements to ATLAS.

## Key Topics
- Performance optimizations (connection pooling, caching, async improvements)
- Clearing stale pending tasks from queue
- Fixing conversation memory so ATLAS remembers previous sessions

---

## Conversation

### ATLAS Development Assistant

I'll implement ATLAS - the Automated Thinking, Learning & Advisory System. This is a substantial project, so let me start by creating the task list and then work through each phase systematically.

### ATLAS Development Assistant

Now let me set up task dependencies and check if there are any existing scripts to port.

### ATLAS Development Assistant

Let me read the existing scripts to port and check what already exists in the atlas directory.

### ATLAS Development Assistant

Good - there's already some code started. Let me check what exists.

### ATLAS Development Assistant

Excellent! There's already substantial work done. Let me check the existing scripts and see what else needs to be built.

### ATLAS Development Assistant

Excellent! There's already a lot built. Let me check what's in each module to understand the current state.

### ATLAS Development Assistant

This is great - most of the core has already been built! Let me read the key files to understand what's there and what's missing.

### ATLAS Development Assistant

The core is largely built. Let me check what else exists and what's missing.

### ATLAS Development Assistant

Excellent! A lot has been built already. Let me check the remaining files and see what's missing.

### ATLAS Development Assistant

Excellent! Most of the core phases (1-5) are already built. Let me check the providers and other core files.

### ATLAS Development Assistant

This is impressive - phases 1-5 are almost complete. Now let me check what's missing and what needs to be built for phases 6-11. Let me check which directories/files don't exist yet.

### ATLAS Development Assistant

Now I have a good picture. The missing directories for the JARVIS phases (6-11) are:
- `atlas/monitoring/` (Phase 6)
- `atlas/daemon/` (Phase 7)
- `atlas/integrations/` (Phases 8-9)
- `atlas/learning/` (Phase 11)
- Enhanced personality/quips (Phase 10 - not yet in core/)

Let me now systematically build what's missing. I'll start with updating tasks to mark Phase 1 complete since it's fully built.

### ATLAS Development Assistant

Phases 1-5 are complete. Now let me build Phase 10 (Enhanced Personality & Wit) first as recommended, then continue with the monitoring phases.

### ATLAS Development Assistant

Now let me update the core __init__.py to export these new modules.

### ATLAS Development Assistant

Now let's build Phase 6: Proactive Monitoring & Alerts.

### ATLAS Development Assistant

Now Phase 7: Ambient Daemon Mode with Windows toast notifications and system tray.

### ATLAS Development Assistant

Now let's add Windows toast notifications support.

### ATLAS Development Assistant

Now let's create the Windows system tray script.

### ATLAS Development Assistant

Now update the notifications __init__.py to include the new module.

### ATLAS Development Assistant

Now Phase 8: Smart Home Integration (Home Assistant).

### ATLAS Development Assistant

Now Phase 9: Calendar & Email Integration with Google OAuth.

### ATLAS Development Assistant

Now update the integrations __init__.py.

### ATLAS Development Assistant

Now Phase 11: Anticipation Engine - pattern detection and proactive suggestions.

### ATLAS Development Assistant

Now let me update the requirements.txt with all the new dependencies and update the main configuration.

### ATLAS Development Assistant

Now let me update the configuration file with the new settings for the JARVIS phases.

### ATLAS Development Assistant

Now let's verify all the files are in place and check the task status.

### ATLAS Development Assistant

All tasks are complete. Let me verify the directory structure.

### ATLAS Development Assistant

The ATLAS system is now fully implemented. Let me provide a summary of what was built:

## ATLAS Implementation Complete

All 11 phases have been implemented:

### Phases 1-5 (Already existed):
- **Phase 1**: Core structure, butler personality, config, memory manager
- **Phase 2**: Multi-model routing (Claude, GPT, Gemini, Ollama)
- **Phase 3**: Background tasks with SQLite queue, systemd service
- **Phase 4**: Voice interface (Whisper STT, Piper TTS)
- **Phase 5**: Hotkey activation (AutoHotkey script)

### Phases 6-11 (Newly built):

**Phase 6: Proactive Monitoring**
- `atlas/monitoring/monitor.py` - Base monitoring framework with Alert system
- `atlas/monitoring/system_monitor.py` - CPU, memory, disk, Ollama status
- `atlas/monitoring/git_monitor.py` - Uncommitted changes, unpushed commits, stash
- `atlas/monitoring/web_monitor.py` - URL uptime and response time monitoring

**Phase 7: Ambient Daemon Mode**
- `atlas/daemon/ambient.py` - Enhanced daemon with continuous monitoring
- `atlas/notifications/windows_toast.py` - Windows toast notifications from WSL2
- `scripts/atlas-tray.py` - Windows system tray application

**Phase 8: Smart Home Integration**
- `atlas/integrations/home_assistant.py` - Home Assistant REST API client
- `atlas/integrations/smart_home.py` - Natural language smart home control

**Phase 9: Calendar & Email Integration**
- `atlas/integrations/google_auth.py` - Google OAuth2 authentication
- `atlas/integrations/calendar.py` - Google Calendar integration
- `atlas/integrations/email.py` - Gmail integration

**Phase 10: Enhanced Personality & Wit**
- `atlas/core/personality.py` - Situational awareness, time-based greetings, task quips
- `atlas/core/quips.py` - Easter eggs, jokes, provider quips, special dates

**Phase 11: Anticipation Engine**
- `atlas/learning/patterns.py` - Time and context pattern detection
- `atlas/learning/suggestions.py` - Proactive suggestion engine
- `atlas/learning/habits.py` - Habit tracking and streak management

### Configuration Updated:
- `config/atlas.yaml` - All new features configurable
- `requirements.txt` - Added Google API dependencies

### Directory Structure:
```
atlas/atlas/
├── core/           # Butler, config, personality, quips
├── daemon/         # Ambient mode
├── integrations/   # Home Assistant, Google Calendar/Gmail
├── learning/       # Patterns, suggestions, habits
├── memory/         # Conversation storage
├── monitoring/     # System, git, web monitors
├── notifications/  # Desktop and Windows toast
├── routing/        # Multi-model routing, providers
├── tasks/          # Background queue, worker
└── voice/          # STT (Whisper), TTS (Piper)
```

To test, run:
```bash
./scripts/atlas
```

### ATLAS Development Assistant

# ATLAS Usage Guide

## Phase 1: Core Structure and Memory

### Interactive REPL
```bash
cd ~/ai-workspace/atlas
./scripts/atlas
```

### Basic Commands
```
You: Hello                    # Start a conversation
You: /help                    # Show all commands
You: /status                  # Show usage stats and provider availability
You: /memory                  # View stored conversations and decisions
You: /decision                # Record an important decision (interactive)
You: /quit                    # Exit ATLAS
```

### Memory Storage
Conversations are automatically saved to:
```
~/ai-workspace/atlas/memory/conversations/YYYY-MM-DD.md
~/ai-workspace/atlas/memory/decisions/
```

---

## Phase 2: Multi-Model Routing

### Automatic Routing
Just ask questions - ATLAS routes to the best model:
```
You: Write a Python function to parse JSON      # Routes to OpenAI (code)
You: What is quantum computing?                 # Routes to Gemini (research)
You: Review this architecture decision          # Routes to Claude (review)
You: Draft an email to my team                  # Routes to Gemini (draft)
```

### Force a Specific Model
```
You: /model claude            # Force Claude for next queries
You: /model openai            # Force OpenAI
You: /model gemini            # Force Gemini
You: /model ollama            # Force local Ollama
You: /model                   # Restore automatic routing
```

### Check Usage
```
You: /status
```
Shows daily usage against limits for each provider.

---

## Phase 3: Background Tasks and Notifications

### Queue a Background Task
```bash
# From CLI
./scripts/atlas queue add "Research Kubernetes security best practices"

# Or from REPL
You: /queue add Research the latest Python 3.12 features
```

### Manage Queue
```
You: /queue status            # Show queue statistics
You: /queue pending           # List pending tasks
You: /queue completed         # List completed tasks (last 24h)
```

### Start the Daemon
```bash
# Install systemd service (one-time)
mkdir -p ~/.config/systemd/user
cp ~/ai-workspace/atlas/services/atlas.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable atlas

# Start daemon
systemctl --user start atlas

# Check status
systemctl --user status atlas

# View logs
tail -f ~/ai-workspace/atlas/data/daemon.log
```

### Briefings
```
You: /briefing                # Quick session briefing
You: /morning                 # Full morning briefing with news
You: /endday                  # End of day report with AI insights
```

---

## Phase 4: Voice Interface

### Setup
```bash
# Install voice dependencies
pip install openai-whisper sounddevice numpy

# Download Piper voice (optional, for TTS)
mkdir -p ~/ai-workspace/atlas/models/piper
# Download en_GB-alan-medium.onnx from Piper releases
```

### Voice Mode
```bash
./scripts/atlas-voice
```

Commands in voice mode:
- Press Enter to start recording
- Speak your query
- Recording stops automatically after silence
- ATLAS res

[... response truncated ...]

### ATLAS Development Assistant

Now let me create a README.md for the project root that provides a quick overview and points to the detailed guide.

### ATLAS Development Assistant

I've created comprehensive documentation for ATLAS:

## Documentation Created

### 1. Full Usage Guide
**Location:** `~/ai-workspace/atlas/docs/USAGE.md`

**Size:** ~1,200 lines covering everything in depth:

| Section | Contents |
|---------|----------|
| Introduction | Overview, capabilities, philosophy |
| Installation | Prerequisites, setup steps, API keys |
| Quick Start | First conversation example |
| Core Features | REPL, memory, decisions, reminders |
| Multi-Model Routing | How routing works, forcing models, quotas |
| Background Tasks | Queuing, daemon, results |
| Briefings & Reports | Morning, quick, end-of-day |
| Voice Interface | Setup, usage, WSL2 audio |
| Hotkey Activation | AutoHotkey setup, controls |
| Proactive Monitoring | System, git, web monitoring |
| Smart Home Control | Home Assistant setup, commands |
| Calendar & Email | Google OAuth, commands |
| Personality & Easter Eggs | Time greetings, quips, special phrases |
| Learning & Anticipation | Patterns, suggestions, habits |
| Configuration Reference | Complete YAML reference |
| Command Reference | All commands with descriptions |
| Troubleshooting | Common issues and fixes |
| Advanced Usage | Python API, custom monitors, providers |
| Appendix | File structure, env vars, dependencies |

### 2. Quick README
**Location:** `~/ai-workspace/atlas/README.md`

Concise overview with:
- Feature list
- Quick start commands
- Command reference table
- Daemon setup
- Config example
- Link to full documentation

---

To read the full guide:
```bash
less ~/ai-workspace/atlas/docs/USAGE.md
```

Or view it with markdown rendering if you have a viewer like `glow`:
```bash
glow ~/ai-workspace/atlas/docs/USAGE.md
```

### ATLAS Development Assistant

I'll create an Obsidian vault structure for ATLAS documentation with proper linking, callouts, and organization.

### ATLAS Development Assistant

I'll continue creating the Obsidian documentation pages. Let me create the remaining pages for the vault.

### ATLAS Development Assistant

You've hit your limit · resets 5pm (America/New_York)

### ATLAS Development Assistant

Welcome back! I was creating the Obsidian documentation vault for ATLAS. I've completed 13 pages so far. Let me finish the remaining pages - Calendar Integration, Email Integration, and the Reference section.

### ATLAS Development Assistant

The Obsidian documentation vault is now complete. Here's what was created:

## ATLAS Obsidian Vault

**Location:** `~/ai-workspace/atlas/docs/obsidian/`

### Structure

```
docs/obsidian/
├── ATLAS Home.md              # Main index with navigation
├── Getting Started/
│   ├── Installation.md
│   ├── Quick Start.md
│   └── Configuration.md
├── Features/
│   ├── Multi-Model Routing.md
│   ├── Background Tasks.md
│   ├── Briefings.md
│   └── Memory System.md
├── Voice and Access/
│   ├── Voice Interface.md
│   └── Hotkey Activation.md
├── Monitoring/
│   ├── Proactive Monitoring.md
│   └── Learning Engine.md
├── Integrations/
│   ├── Smart Home.md
│   ├── Calendar Integration.md
│   └── Email Integration.md
├── Reference/
│   ├── Commands.md
│   ├── Configuration Reference.md
│   └── Troubleshooting.md
└── Advanced/
    └── Python API.md
```

### 19 Pages Total

Each page includes:
- YAML frontmatter (title, description, tags, created date)
- Obsidian wiki links (`[[Page Name]]`)
- Callouts (`> [!tip]`, `> [!warning]`, `> [!note]`)
- Code blocks with syntax highlighting
- Tables for quick reference
- "See Also" sections linking related pages

### To Use

1. Open Obsidian
2. Open folder as vault: `~/ai-workspace/atlas/docs/obsidian/`
3. Start at `ATLAS Home.md`

The wiki links will create a connected knowledge graph of all ATLAS features.

### ATLAS Development Assistant

I opened the folder in Windows Explorer. To open it in Obsidian:

1. **If Obsidian is installed on Windows:**
   - Open Obsidian
   - Click "Open folder as vault"
   - Navigate to: `\\wsl$\Ubuntu\home\mcrawson\ai-workspace\atlas\docs\obsidian`

2. **Or from the Explorer window I just opened:**
   - Copy the path
   - In Obsidian, use "Open folder as vault" and paste it

Let me also try launching Obsidian directly if it's installed:

### ATLAS Development Assistant

Obsidian should be opening. If it prompts you to select a vault:

**Path to open as vault:**
```
\\wsl$\Ubuntu\home\mcrawson\ai-workspace\atlas\docs\obsidian
```

Or from the Windows Explorer window that opened, you can drag the folder into Obsidian's vault selector.

Once open, click on `ATLAS Home` to start navigating the documentation. The wiki links should show as clickable connections in the graph view.

### ATLAS Development Assistant

No, Obsidian isn't installed. Want me to download it for you?

### ATLAS Development Assistant

Latest version is **v1.11.7**. I can download and install it:

### ATLAS Development Assistant

Downloaded (283MB). Now let me run the installer:

### ATLAS Development Assistant

The installer is in your Downloads folder:

```
C:\Users\mikec\Downloads\Obsidian-Setup.exe
```

**Double-click it to install.** Once installed:

1. Open Obsidian
2. Click "Open folder as vault"
3. Navigate to: `\\wsl.localhost\Ubuntu\home\mcrawson\ai-workspace\atlas\docs\obsidian`
4. Click "Open"

The ATLAS documentation vault will load with all the wiki links working.

### ATLAS Development Assistant

Obsidian can't watch files across the WSL boundary. Let me copy the vault to a native Windows location:

### ATLAS Development Assistant

Done. Now open this folder in Obsidian instead:

```
C:\Users\mikec\Documents\ATLAS-Docs
```

1. In Obsidian, click "Open folder as vault"
2. Navigate to `C:\Users\mikec\Documents\ATLAS-Docs`
3. Click "Open"

This is a native Windows path so file watching will work properly.

### ATLAS Development Assistant

Let me check the current hotkey setup:

### ATLAS Development Assistant

The script exists. Let me check if AutoHotkey is installed and if the script is running:

### ATLAS Development Assistant

AutoHotkey v1 is installed but the script requires v2. Let me rewrite it for v1 compatibility:

### ATLAS Development Assistant

Now let me copy it to Windows and restart AutoHotkey:

### ATLAS Development Assistant

Script is running. Try pressing:

- **`** (backtick) - primary hotkey
- **Win + `** - alternative
- **Ctrl+Shift+A** - another alternative

You should see a tooltip "ATLAS Hotkey Active" appear briefly. Does pressing backtick open ATLAS now?

### ATLAS Development Assistant

Let me check the current briefing structure and add session commands:

### ATLAS Development Assistant

Now let me add session start/end methods. I'll update both `session.py` and `butler.py`:

### ATLAS Development Assistant

Now let me add formatting methods to butler.py:

### ATLAS Development Assistant

Now let me check the main CLI to add the commands:

### ATLAS Development Assistant

Now let me add the session commands to the CLI:

### ATLAS Development Assistant

Now let me update the Obsidian documentation with the new commands:

### ATLAS Development Assistant

Now let me sync the updated docs to Windows:

### ATLAS Development Assistant

Done! Here's what I added:

## New Session Commands

| Command | Description |
|---------|-------------|
| `/startsession` | Shows session start briefing (also shown automatically when you open ATLAS after the first session of the day) |
| `/endsession` | Shows session summary and exits ATLAS |

### Session Start Briefing
- Shows automatically when opening ATLAS (not first session of day)
- Displays time since last session
- Shows pending tasks and quota warnings
- Quick system status alerts

### Session End Summary
- Duration of the session
- Number of queries made
- Tasks completed
- Activity breakdown by type
- Most used AI provider
- Personalized farewell based on time of day

### Difference from Day Briefings

| Session | Day |
|---------|-----|
| `/startsession` | `/morning` |
| `/endsession` | `/endday` |
| Quick, lightweight | Comprehensive with news, quotes, insights |
| Every time you open ATLAS | Once per day |

Try it out - open ATLAS and you should see the session start briefing automatically. Use `/endsession` when you're done to see your summary.

### ATLAS Development Assistant

Let me check where the butler personality is defined and tone it down:

### ATLAS Development Assistant

I see the issue. The system prompt tells the AI to act like a "refined British butler" and "trusted household butler." Let me tone this down across the board:

### ATLAS Development Assistant

Now let me tone down the personality phrases - reducing the excessive "sir" usage:

### ATLAS Development Assistant

Let me also update the session formatting methods in butler.py:

### ATLAS Development Assistant

Done. Here's what I changed to make ATLAS more direct and less butler-like:

## Changes Made

**1. System Prompt** (`routing/providers/base.py`)
- Removed "refined British butler" and "trusted household butler" references
- Changed to: "Professional and direct, concise, dry wit welcome, skip unnecessary pleasantries"

**2. Butler Phrases** (`core/butler.py`)
- Greetings: "Good morning, sir. I trust you slept well..." → "Morning. What are we working on?"
- Acknowledgments: "Very good, sir" → "Got it"
- Completions: "I trust this meets your requirements, sir" → "Done"
- Farewells: "Very good, sir. I shall be here when you need me" → "Later"

**3. Personality Engine** (`core/personality.py`)
- Removed all "sir" from greetings and quips
- Simplified phrases across the board
- Task quips: "The code compiles, sir. A small victory..." → "Code done. Compiles, at least."

**4. Easter Eggs & Quips** (`core/quips.py`)
- Removed all "sir" from jokes and responses
- Simplified special date messages
- Made waiting messages short: "Processing..."

**5. Session & Briefings**
- Simplified day-of-week greetings
- Removed excessive politeness from all briefing text

The personality is now **direct and efficient** while still having some dry wit. No more "sir" or butler formality.

### ATLAS Development Assistant

Got it - you want the butler personality, just not constantly reminding you of it. Let me restore the character but dial back the repetitive completion phrases.

### ATLAS Development Assistant

Done. I've restored the butler personality but with better balance. Here's what changed:

## Key Fix - System Prompt

The AI is now told:
- Address the user as "sir" **occasionally, not every sentence**
- **Don't constantly remind the user you're an assistant or butler**
- Just answer the question - **skip meta-commentary about yourself**
- Personality should come through **naturally, not be forced**

## What's Restored
- Butler greetings with wit ("Burning the midnight oil, I see")
- Occasional "sir" in phrases
- Dry humor in quips and easter eggs
- The refined personality in task completions

## What's Different
- **Completion phrases are simpler**: "Done." / "Here you go." / "All set." instead of lengthy butler-speak every time
- The AI won't pad responses with "As your trusted butler, I am here to serve you, sir..."
- Natural personality that shows up when appropriate, not forced into every response

The butler character is there, but it won't lecture you about being a butler after every prompt.

### ATLAS Development Assistant

I see the problem. The AI doesn't know about ATLAS's actual features because the system prompt only mentions generic capabilities. The AI models don't know about the queue, briefings, monitoring, smart home, etc.

Let me update the system prompt to include ATLAS's real capabilities:

### ATLAS Development Assistant

Now ATLAS will know about its actual capabilities. The AI will be able to explain:

- Background task queue (`/queue add`, `/queue status`)
- Briefings (`/morning`, `/startsession`, `/endsession`, `/endday`)
- System/Git/Web monitoring
- Smart home control (Home Assistant)
- Calendar and email integration
- Pattern learning
- All the slash commands

**Also noticed**: When the user asked "what are the pending tasks", ATLAS made up fake tasks instead of checking the actual queue. The AI should now know to tell users to use `/queue status` to see real pending tasks, rather than inventing them.

Try asking ATLAS again - it should now give accurate information about its features.

### ATLAS Development Assistant

Yes, I can see several issues in that conversation:

1. **Hallucinating fake data** - When asked about pending tasks, it made up fake tasks with placeholders like "[Topic]" and "[Date]" instead of saying "use `/queue status` to check"

2. **Pretending to have memory it doesn't** - Said "I've gone back through our previous conversation" when it can't actually do that

3. **Losing context repeatedly** - Kept saying "Let's start fresh" and "there appears to be no previous conversation"

4. **Doesn't know its real features** - Only mentioned generic AI stuff, not the actual ATLAS commands

Let me add instructions to prevent the hallucination issue:

### ATLAS Development Assistant

Now the AI is instructed to:
- **Not fake data** - Won't make up tasks with "[Topic]" placeholders
- **Not pretend to have memory** - Won't claim to "look up" conversations it can't access
- **Direct to real commands** - Will tell users to use `/queue status` for actual pending tasks
- **Be honest** - Will admit when it doesn't know something instead of inventing answers

The Ollama models are less capable than Claude/GPT and more prone to hallucination. When Gemini hit rate limits in that conversation, it fell back to Ollama which then made things up. The updated prompt should help, but Ollama will still be less reliable than the cloud models.

### ATLAS Development Assistant

Good catch. The session start screen shows "2 pending tasks" (from the actual queue), but when you ask ATLAS about it, the AI can't access that data. At least now it's telling you to use `/queue status` instead of making things up.

The issue is the AI doesn't have access to the queue. Let me fix this by passing queue context to the AI when relevant:

### ATLAS Development Assistant

I can add queue context to the AI. Let me modify the message handler to include current queue status:

### ATLAS Development Assistant

Now let me add the method that gets the system context:

### ATLAS Development Assistant

Now when users ask about pending tasks, the AI will have the actual data. It will receive context like:

```
CURRENT SYSTEM STATUS:
Background Queue: 2 pending, 0 completed today
Pending tasks:
  - Research Kubernetes security best practices
  - Analyze Python async patterns
```

So when someone asks "what are the pending tasks?", the AI can give the real answer instead of making things up.

Try it again - ATLAS should now know about the actual pending tasks.

### ATLAS Development Assistant

Let me analyze where ATLAS might be slow or clunky:

### ATLAS Development Assistant

Let's do it. Starting with the quick wins:

### ATLAS Development Assistant

I'll continue implementing the performance optimizations. Let me start by fixing the Ollama connection pooling issue.

### ATLAS Development Assistant

I can see the issue. Both `generate()` and `generate_stream()` create new `aiohttp.ClientSession()` each time instead of reusing the session. Let me fix this.

### ATLAS Development Assistant

Now let me check the Gemini provider for similar optimization opportunities.

### ATLAS Development Assistant

I see the issue - `generate()` creates a new model each time instead of using `_get_model()`. Let me fix that.

### ATLAS Development Assistant

Now let me check the UsageTracker to add caching.

### ATLAS Development Assistant

I see the issue - the UsageTracker reads the file on every `get_usage()` call, and methods like `get_all_usage()` call it 4 times. Let me add in-memory caching.

### ATLAS Development Assistant

Now let me check the main script for `asyncio.run()` overhead.

### ATLAS Development Assistant

I see the issue - `_get_system_context()` calls `asyncio.run()` twice, and it's called from `handle_message_async()` which is already async. Let me optimize this by making `_get_system_context()` async.

### ATLAS Development Assistant

Now let me also optimize the morning briefing which has multiple `asyncio.run()` calls. Let me create an async version and consolidate them.

### ATLAS Development Assistant

Let me also optimize the end of day report which has multiple sequential async calls.

### ATLAS Development Assistant

Now let me check the Router for any optimization opportunities.

### ATLAS Development Assistant

The router looks optimized. Let me check the Claude provider.

### ATLAS Development Assistant

Claude provider already caches its client. Let me check OpenAI.

### ATLAS Development Assistant

Let me run a quick test to make sure the changes work.

### ATLAS Development Assistant

Let me verify ATLAS still starts properly.

### ATLAS Development Assistant

ATLAS is working. Here's a summary of all the performance optimizations I've implemented:

## Performance Optimizations Applied

### 1. **Ollama Connection Pooling** (`ollama.py`)
- Now reuses `aiohttp.ClientSession` via `_get_session()` instead of creating a new session for every request
- Eliminates connection setup overhead on repeated calls

### 2. **Gemini Model Reuse** (`gemini.py`)
- `generate()` now uses cached model instance via `_get_model()` like `generate_stream()` already did
- Avoids reinitializing the model and reconfiguring the API key on every request

### 3. **UsageTracker Caching** (`usage.py`)
- Added in-memory cache with 30-second TTL
- File is now read once and cached; subsequent `get_usage()` calls use memory
- `log_usage()` updates cache immediately so it stays in sync

### 4. **Async Context Gathering** (main script)
- Converted `_get_system_context()` to async `_get_system_context_async()`
- Uses `asyncio.gather()` to fetch queue stats and pending tasks in parallel
- Eliminates nested `asyncio.run()` calls in async context

### 5. **Morning Briefing Optimization**
- Fetches queue stats, completed tasks, and news headlines in parallel with `asyncio.gather()`
- Reduced from 3 sequential async calls to 1 parallel batch

### 6. **End of Day Report Optimization**
- Generates AI insights, action items, and tomorrow suggestions in parallel
- Reduced from 3 sequential AI calls to 1 parallel batch (significant time savings)

These changes should make ATLAS noticeably more responsive, especially on startup and during briefings.

### ATLAS Development Assistant

Let me check what's in the task queue database.

### ATLAS Development Assistant

Found them - two old test tasks from yesterday. Let me clear them out.

### ATLAS Development Assistant

Done. The stale test tasks have been cleared. The queue now shows 0 pending. You can verify by running `/startsession` or `/queue status` in ATLAS.

### ATLAS Development Assistant

Let me check how the memory system is working and what's being stored.

### ATLAS Development Assistant

I see the issue. The conversation history isn't being parsed properly - it's returning raw markdown files but trying to access `user_message` keys that don't exist. Let me fix this.

### ATLAS Development Assistant

Now I see the bug. The conversation history code is broken - it's trying to access `user_message` from file-level data instead of parsing the actual conversation content. Let me fix this properly.

### ATLAS Development Assistant

Now let me fix the main script to use this new method properly.

### ATLAS Development Assistant

Let me test the new conversation parsing.

### ATLAS Development Assistant

The parsing is working now. Let me also verify the full context being passed to the AI.

### ATLAS Development Assistant

The conversation history is now being retrieved properly. Let me also check how it's presented in the system prompt.

### ATLAS Development Assistant

Let me update the system prompt to make it clearer that the AI should use the conversation history.

### ATLAS Development Assistant

Let me also increase the history length for better context.

### ATLAS Development Assistant

Let me verify the fix works.

### ATLAS Development Assistant

The memory issue is now fixed. Here's what was wrong and what I changed:

## Problem
The conversation history code was broken - it was trying to access `user_message` keys from file-level data that only contained raw markdown content. The AI never received any actual conversation history.

## Fixes Applied

1. **Added `get_recent_exchanges()` method** to `memory/manager.py`
   - Parses the markdown files to extract actual User/ATLAS exchanges
   - Returns properly structured data with `user` and `assistant` keys

2. **Fixed conversation history building** in the main script
   - Now uses the new method to get real parsed exchanges
   - Includes up to 15 recent exchanges with 300/400 char snippets

3. **Updated system prompt** in `base.py`
   - Added clearer instructions telling the AI to use the conversation history
   - "Use this history to understand what you and the user have discussed. Reference previous topics when relevant."

Now ATLAS will receive 15 recent exchanges (about 8,400 chars of context) with each request, so it should remember what you've discussed in previous sessions.

**Note:** The old conversations before this fix didn't have proper memory, so you may see some confused exchanges in the history. Going forward, new conversations will be properly remembered.
