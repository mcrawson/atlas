# ATLAS Complete Task List

**Goal:** Get ATLAS fully up and running correctly.

**Current Status:** 583 tests passing, 5 minor failures (non-critical)

---

## PHASE 1: CRITICAL FIXES (Must Do)

### Task 1.1: Fix Failing Tests
**Files to fix:**
- `tests/test_research/test_augmenter.py` — 2 failures (API error handling)
- `tests/test_versioning/test_changelog.py` — 2 failures (duplicate entries, bold formatting)
- `tests/test_web/test_rate_limit.py` — 1 failure (default config mismatch)

**Command to verify:**
```bash
pytest tests/test_research/test_augmenter.py tests/test_versioning/test_changelog.py tests/test_web/test_rate_limit.py -v
```

### Task 1.2: Verify Project 100 End-to-End
- Start server: `./scripts/atlas-web --port 5002 --no-browser`
- Rebuild project 100 with `build_type: static_html`
- Run QC and verify it passes
- Open in browser and verify UI works

---

## PHASE 2: INTEGRATION (Connect Everything)

### Task 2.1: Wire Up build_type in UI
**Files:**
- `atlas/web/templates/project_detail.html` or similar
- Add dropdown or toggle for users to select build_type (static_html vs react_spa)
- Pass selection to Mason via context

### Task 2.2: QC Report UI Improvements
**Files:**
- `atlas/web/templates/partials/qc_report.html`
- Show when QC is evaluating React source files vs HTML preview
- Add indicator: "Evaluating React components" or "Evaluating static HTML"

### Task 2.3: Business Brief → Builder Pipeline
**Files:**
- `atlas/web/routes/projects.py`
- `atlas/agents/director.py`
- Ensure approved Business Brief automatically routes to correct builder
- Verify Go/No-Go decision blocks or allows progression

---

## PHASE 3: LAYLA-STYLE CONVERSATION (Polish)

### Task 3.1: Verify Typing Indicators Work
**Files:**
- `atlas/agents/message_broker.py` — has TYPING message type ✅
- `atlas/agents/director.py` — needs to call `push_typing()` before generation
- `atlas/web/templates/partials/live_conversation.html` — needs CSS animation

**Test:** Start a conversation and verify typing dots appear before agent speaks.

### Task 3.2: Verify User Intervention Works
**Files:**
- `atlas/web/websocket.py` — has `handle_user_message()` ✅
- `atlas/web/templates/partials/live_conversation.html` — has textarea ✅

**Test:** Join a live conversation and send a message. Verify agents respond.

### Task 3.3: Dynamic Topic Generation
**Files:**
- `atlas/agents/director.py`
- Currently uses hardcoded debate topics
- Should generate topics from Business Brief

**Change:** In `_debate()`, call LLM to generate 3-5 relevant debate topics from the brief.

### Task 3.4: Genuine Disagreement
**Files:**
- `atlas/agents/personalities.py` — exists ✅
- `atlas/agents/director.py`
- Agents should take different positions and challenge each other

**Test:** Start a debate and verify agents don't just agree with each other.

---

## PHASE 4: QUALITY & POLISH

### Task 4.1: Add build_type Tests to QC
**File:** `tests/test_agents/test_qc.py` (create if needed)
- Test QC evaluates React source files when present
- Test QC uses HTML preview for static HTML builds
- Test QC verdict is accurate for both build types

### Task 4.2: Error Handling
**Files:** Various
- Ensure graceful failures when LLM API is down
- Show user-friendly error messages
- Log errors for debugging

### Task 4.3: Mobile Responsive Check
- Test all pages on mobile viewport
- Fix any layout issues in templates

---

## PHASE 5: DOCUMENTATION & CLEANUP

### Task 5.1: Update User Manual
**File:** `docs/USER-MANUAL.md`
- Document build_type option
- Document QC behavior for React vs static HTML
- Add troubleshooting section

### Task 5.2: Clean Up Handoff Files
- Delete `HANDOFF-OPENCLAW.md` (no longer needed)
- Delete `TASKS-OPENCLAW.md` (no longer needed)
- Update `MEMORY.md` with completed tasks

### Task 5.3: Run Full Test Suite
```bash
pytest tests/ -v
```
**Goal:** All tests passing (588+)

---

## VERIFICATION CHECKLIST

After completing all tasks, verify:

- [ ] Server starts without errors: `./scripts/atlas-web --port 5002`
- [ ] Create new project works
- [ ] Business Brief generation works
- [ ] Go/No-Go decision works
- [ ] Build with `static_html` produces HTML/CSS/JS
- [ ] Build with `react_spa` produces React/TypeScript
- [ ] QC evaluates both build types correctly
- [ ] QC passes for complete builds
- [ ] Auto-fix loop works
- [ ] Live conversation shows typing indicators
- [ ] User can join conversation
- [ ] All tests pass: `pytest tests/ -v`

---

## PRIORITY ORDER

1. **Task 1.1** — Fix failing tests (5 tests)
2. **Task 1.2** — Verify project 100 works
3. **Task 2.1** — Add build_type UI
4. **Task 3.1** — Verify typing indicators
5. **Task 3.2** — Verify user intervention
6. Everything else in order

---

## HOW TO RUN

```bash
cd /home/mcrawson/ai-workspace/atlas
source .venv/bin/activate
./scripts/atlas-web --port 5002 --no-browser
```

Then open: http://localhost:5002
