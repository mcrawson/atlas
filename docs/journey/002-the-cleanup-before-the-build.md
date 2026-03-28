# The Cleanup Before the Build

**Journey Post #2 | ATLAS 3.0 Rebuild**
**Date:** 2026-03-15
**Phase:** 1 — Foundation Reset (Complete)
**Author:** Amp

---

You know what's harder than building something new?

Tearing down what doesn't work.

Today we completed **Phase 1: Foundation Reset** — the unsexy work that makes everything else possible.

## What We Removed

We had code that shouldn't have existed in the first place.

### Canva Integration

Beautiful idea. Built the whole OAuth flow, asset upload, design creation... only to discover the Canva API literally cannot place assets on a canvas. The API we spent days integrating? It could upload images to a user's library. That's it. The feature was decorative.

*Deleted.*

### MCP Server

A "Model Context Protocol" server that added complexity without adding value. Another case of building something because we *could*, not because we *should*.

*Deleted.*

### Auto-Triggers

Code that automatically fired integrations without asking the user. "Smart" automation that made the system feel out of control.

*Deleted.*

**250+ lines of code, gone.** And ATLAS is better for it.

---

## What We Built

The foundation for everything coming next:

### Builder Architecture

Instead of one agent that does everything poorly, we now have the structure for specialized builders:

| Builder | Products | Why |
|---------|----------|-----|
| PrintableBuilder | Planners, cards, worksheets | Expert in PDF layout and print design |
| DocumentBuilder | Books, guides, manuals | Expert in long-form content structure |
| WebBuilder | Landing pages, SPAs | Expert in modern web development |
| AppBuilder | Mobile apps | Expert in React Native cross-platform |

Each one an expert in its domain. No more "one size fits none."

### New Agent Stubs

Three new agents are ready for implementation:

- **Analyst** — Creates comprehensive Business Briefs before any building starts. Kills bad ideas early.
- **QC** — Quality Control that checks work against the Brief at every stage. Advisory, not blocking.
- **Mockup** — Creates polished visual previews so you see what you're getting before committing.

### New Workflow Stages

The database now tracks the full ATLAS 3.0 process:

```
Idea Chat → Analyzing → Brief Review → Round Table →
Mockup → Mockup Review → Building → QC → Build Review → Deploy
```

Every stage is a checkpoint. Every checkpoint puts you in control.

---

## The Lesson

Sometimes progress means deleting code, not writing it.

We removed features that felt impressive but didn't serve the mission. We built scaffolding that will hold up the actual work. We cleaned up technical debt before it compounded.

None of this is flashy. None of this makes a good demo. But without it, everything we build next would be built on a shaky foundation.

---

## What's Next

**Phase 2: The Analyst Agent**

This is where ATLAS starts to think before it builds. The Analyst will:

- Research market viability
- Analyze competition
- Define target customers with actionable detail
- Create financial projections
- Make Go/No-Go recommendations

No more building products nobody wants. The Analyst kills bad ideas early.

---

## Technical Summary

### Files Removed
- `atlas/integrations/platforms/canva.py`
- `atlas/mcp/` (entire directory)
- ~250 lines of Canva routes and auto-trigger code from `projects.py`

### Files Created
- `atlas/agents/builders/base.py` — BaseBuilder class
- `atlas/agents/builders/config.py` — Configuration classes
- `atlas/agents/builders/__init__.py` — Registry
- `atlas/agents/analyst.py` — AnalystAgent + BusinessBrief
- `atlas/agents/qc.py` — QCAgent + QCReport
- `atlas/agents/mockup.py` — MockupAgent + MockupOutput

### Files Modified
- `atlas/projects/models.py` — New TaskStatus workflow stages
- `atlas/web/app.py` — Removed MCP initialization
- `atlas/integrations/platforms/__init__.py` — Removed Canva

---

## Follow Along

This is a public build. We're documenting everything — including the boring parts.

If you're building something with AI, maybe our process can help inform yours.

*- Amp*

---

**Next Post:** Phase 2 begins — implementing the Analyst Agent
