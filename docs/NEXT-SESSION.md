# Next Session Agenda

**Project:** ATLAS 3.0 Rebuild
**Last Session:** 2026-03-28
**Status:** Phase 4 In Progress - Kickoff + QC Integration

---

## What We Accomplished This Session

### Phase 4: Kickoff + QC Integration (IN PROGRESS)

1. **Merged KickoffAgent into RoundTableV2**
   - Added Phase 6: Technical Planning to `roundtable_v2.py`
   - Scope definition (in/out/assumptions)
   - Tech stack selection by product type
   - Priority features identification
   - Risk areas flagging
   - QC checkpoints definition
   - Architect instructions generation
   - Stored `kickoff_plan` in session and project metadata

2. **Removed orphaned `/kickoff` route**
   - Functionality now in `approve_business_brief` flow
   - One unified kickoff path through RoundTableV2

3. **Committed all ATLAS 3.0 changes** (8 commits)
   - Cleanup: Removed old MCP/Canva
   - Phase 2: Analyst + Kickoff agents
   - Phase 3: QC + Builders
   - Overnight Operator system
   - Integration layer (routes, templates)
   - Documentation + journey posts

---

## Current Flow

```
idea → analysis → brief_review → [approve] → plan
                                     ↓
                               RoundTableV2.kickoff()
                                     ↓
                         ┌───────────────────────┐
                         │ Phase 1: Mission      │
                         │ Phase 2: Brief Valid  │
                         │ Phase 3: Specialists  │
                         │ Phase 4: Roles        │
                         │ Phase 5: Timeline     │
                         │ Phase 6: Tech Plan    │ ← NEW (merged from KickoffAgent)
                         └───────────────────────┘
                                     ↓
                               kickoff_plan stored
                                     ↓
                                   plan phase
```

---

## Still To Do for Phase 4

1. [ ] **Test flow end-to-end** - Create project, go through full workflow
2. [ ] **Verify QC integration** - Check that QC routes work with kickoff_plan
3. [ ] **UI for kickoff_plan** - Display scope, tech stack in planning phase
4. [ ] **Update project_detail.html** - Show kickoff_plan data

---

## Files Changed This Session

| File | Change |
|------|--------|
| `atlas/agents/roundtable_v2.py` | Added Phase 6, kickoff_plan field, tech planning methods |
| `atlas/web/routes/projects.py` | Store kickoff_plan, removed orphaned route |

---

## Context If Chat Closed

If starting fresh, say:

> "Let's continue Phase 4 of ATLAS 3.0. We merged KickoffAgent into RoundTableV2 and need to test the full workflow end-to-end. Read `docs/NEXT-SESSION.md` for current state."

---

## Key Documents

| Document | Path | Status |
|----------|------|--------|
| Build Plan | `docs/BUILD-PLAN.md` | Phase 4 in progress |
| User Manual | `docs/USER-MANUAL.md` | Needs update |
| Next Session | `docs/NEXT-SESSION.md` | This file |

---

**Last Updated:** 2026-03-28
