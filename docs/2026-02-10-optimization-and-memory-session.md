# ATLAS Optimization & Memory Fix Session
**Date:** 2026-02-10

---

## Session Overview

This session focused on performance optimizations and fixing the conversation memory system so ATLAS can remember previous discussions.

---

## Issues Addressed

### 1. Performance - ATLAS Felt "Clunky"

**Problem:** ATLAS was slow due to inefficient resource usage.

**Root Causes Identified:**
- Ollama provider created new HTTP connections for every request
- Gemini provider recreated the model instance on every call
- UsageTracker read from disk on every `get_usage()` call
- Multiple `asyncio.run()` calls nested inside async functions
- Sequential async operations that could run in parallel

### 2. Stale Pending Tasks

**Problem:** ATLAS showed "2 pending tasks" that didn't exist.

**Root Cause:** Old test tasks from 2026-02-09 were left in the SQLite queue database.

### 3. Conversation Memory Not Working

**Problem:** ATLAS couldn't remember previous sessions or conversations.

**Root Cause:** The code tried to access `conv.get("user_message")` from file-level data that only contained raw markdown content. The AI never received actual conversation history.

---

## Fixes Applied

### Performance Optimizations

#### 1. Ollama Connection Pooling (`atlas/routing/providers/ollama.py`)
```python
# Before: Created new session every request
async with aiohttp.ClientSession() as session:
    async with session.post(...) as response:

# After: Reuses existing session
session = await self._get_session()
async with session.post(...) as response:
```

#### 2. Gemini Model Caching (`atlas/routing/providers/gemini.py`)
```python
# Before: Created new model every request
model = genai.GenerativeModel(self.model, system_instruction=system)

# After: Reuses cached model
model = self._get_model()
```

#### 3. UsageTracker In-Memory Cache (`atlas/routing/usage.py`)
```python
# Added cache with 30-second TTL
CACHE_TTL = 30
self._cache = {}  # {provider: count}
self._cache_date = None
self._cache_time = 0

def get_usage(self, provider: str) -> int:
    if not self._is_cache_valid():
        self._refresh_cache()
    return self._cache.get(provider, 0)
```

#### 4. Async Consolidation (`scripts/atlas`)
- Converted `_get_system_context()` to async `_get_system_context_async()`
- Used `asyncio.gather()` for parallel fetching in morning briefing
- Used `asyncio.gather()` for parallel AI insight generation in end-of-day report

### Queue Cleanup
```python
# Cleared stale pending tasks
async with aiosqlite.connect(queue.db_path) as db:
    await db.execute('DELETE FROM tasks WHERE status = ?', (TaskStatus.PENDING.value,))
    await db.commit()
```

### Memory Fix

#### Added `get_recent_exchanges()` method (`atlas/memory/manager.py`)
```python
def get_recent_exchanges(self, limit: int = 10) -> list[dict]:
    """Parse markdown files to extract actual User/ATLAS exchanges."""
    import re
    exchanges = []

    for days_ago in range(2):
        date = datetime.now() - timedelta(days=days_ago)
        path = self._get_conversation_path(date)
        if not path.exists():
            continue

        content = path.read_text()
        pattern = r'\*\*User:\*\*\s*(.*?)\n\n\*\*ATLAS:\*\*\s*(.*?)(?=\n---|\Z)'
        matches = re.findall(pattern, content, re.DOTALL)

        for user_msg, assistant_msg in matches:
            exchanges.append({
                'user': user_msg.strip()[:500],
                'assistant': assistant_msg.strip()[:500],
            })

    return exchanges[-limit:]
```

#### Fixed conversation history building (`scripts/atlas`)
```python
# Before: Broken - tried to access keys that didn't exist
for conv in recent_convos[-5:]:
    user_msg = conv.get("user_message", "")[:100]  # Always empty!

# After: Uses properly parsed exchanges
recent_exchanges = self.memory.get_recent_exchanges(limit=15)
for exchange in recent_exchanges:
    user_msg = exchange.get("user", "")[:300]
    assistant_msg = exchange.get("assistant", "")[:400]
    history_lines.append(f"User: {user_msg}")
    history_lines.append(f"ATLAS: {assistant_msg}")
```

#### Updated system prompt (`atlas/routing/providers/base.py`)
```python
# Made instructions clearer for AI to use the history
base_prompt += f"\n\nRECENT CONVERSATION HISTORY - Use this to maintain continuity:\n{conversation_history}\n\nUse this history to understand what you and the user have discussed. Reference previous topics when relevant."
```

---

## Files Modified

| File | Changes |
|------|---------|
| `atlas/routing/providers/ollama.py` | Connection pooling - reuse `_get_session()` |
| `atlas/routing/providers/gemini.py` | Model caching - reuse `_get_model()` in generate() |
| `atlas/routing/usage.py` | Added in-memory cache with 30s TTL |
| `atlas/memory/manager.py` | Added `get_recent_exchanges()` method |
| `atlas/routing/providers/base.py` | Updated system prompt for conversation history |
| `scripts/atlas` | Fixed history building, async optimizations |

---

## Results

- **Performance:** Reduced connection overhead, faster responses
- **Memory:** ATLAS now receives 15 recent exchanges (~8,400 chars of context) with each request
- **Queue:** Cleared stale test tasks, shows accurate pending count

---

## Notes

- Old conversations before this fix didn't have proper memory, so the AI may reference confused exchanges from before the fix
- Going forward, new conversations will be properly remembered across sessions
- The UsageTracker cache refreshes every 30 seconds to stay in sync with disk
