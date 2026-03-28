# The Brain and the Builders

**Journey Post #3 | ATLAS 3.0 Rebuild**
**Date:** 2026-03-15
**Phases:** 2 & 3 Complete
**Author:** Amp

---

Two phases in one session. Here's what we built.

## The Analyst: ATLAS Gets a Brain

Before today, ATLAS would just... build things. You'd say "make me a planner" and it would start coding. No questions asked. No analysis. No "wait, is this actually a good idea?"

That's how we ended up with technically correct but completely unsellable products.

**Enter the Analyst.**

The Analyst is the business intelligence layer we were missing. Before a single line of code gets written, the Analyst creates a comprehensive **Business Brief**:

- **Executive Summary** — What are we building and why?
- **Target Customer** — Who's buying this? Where do we find them?
- **Market Analysis** — Is there demand? What's the competition?
- **SWOT Analysis** — Strengths, weaknesses, opportunities, threats
- **Financial Projections** — What does it cost to build? What can we charge?
- **Success Criteria** — How do we know if it's good?
- **Go/No-Go Recommendation** — Should we even build this?

The last one is key. The Analyst will tell you "no" if your idea doesn't make sense. That's the point. Kill bad ideas early, before you waste time building them.

### How It Works

1. You describe your idea
2. Analyst researches and analyzes
3. You get a Business Brief with a recommendation
4. You approve, override, or revise
5. Only THEN does building start

The user is always the final authority. The Analyst gives advice. You make the call.

---

## The Builders: Experts, Not Generalists

The old ATLAS had one builder that tried to do everything. Planners, apps, websites, books — all through the same generic prompts.

The result? Everything looked like a developer made it. Because the builder didn't know the difference between a printable PDF and a mobile app.

**Now we have four specialized builders:**

### PrintableBuilder
**Products:** Planners, cards, worksheets, journals, trackers
**Output:** Print-ready HTML/CSS → PDF

This builder knows:
- Page sizes and orientations (Letter, A4, A5)
- Print margins and bleed areas
- Typography for print
- How to structure a weekly planner vs a recipe card

### DocumentBuilder
**Products:** Books, guides, manuals, ebooks
**Output:** Formatted HTML → PDF/EPUB

This builder knows:
- Chapter and section structure
- Table of contents generation
- Book typography (serif fonts, proper leading)
- How a manual differs from a guide

### WebBuilder
**Products:** Landing pages, SPAs, dashboards, portfolios
**Output:** Responsive HTML/CSS/JS

This builder knows:
- Modern web design patterns
- Mobile-first responsive layouts
- Landing page structure (hero, features, CTA)
- Dashboard vs portfolio requirements

### AppBuilder
**Products:** iOS apps, Android apps, cross-platform mobile
**Output:** React Native/Expo project

This builder knows:
- React Native best practices
- Expo SDK compatibility
- Mobile navigation patterns
- App-type specific features (social vs fitness vs productivity)

---

## Why This Matters

The old flow:
```
Idea → Build → Hope it's good
```

The new flow:
```
Idea → Analyze → Approve Brief → Route to Expert Builder → Build
```

Every product now gets:
1. Business validation before building
2. An expert builder that knows its domain
3. Output designed for the actual marketplace

A planner built by PrintableBuilder looks like something you'd buy on Etsy. A mobile app built by AppBuilder is a real React Native project you can deploy.

---

## Technical Summary

### Phase 2: Analyst Agent
- `atlas/agents/analyst.py` — Full AnalystAgent implementation
- `BusinessBrief` dataclass with all analysis fields
- Routes: `/start-analysis`, `/approve-brief`, `/override-brief`, `/re-analyze`
- Business Brief UI partial with SWOT grid, financials, success criteria display

### Phase 3: Specialized Builders
- `atlas/agents/builders/printable.py` — PrintableBuilder
- `atlas/agents/builders/document.py` — DocumentBuilder
- `atlas/agents/builders/web.py` — WebBuilder
- `atlas/agents/builders/app.py` — AppBuilder
- 40+ product type mappings in the builder registry

---

## What's Next

**Phase 4: Kickoff + QC Integration**

The Analyst creates the Brief. The Builders do the work. Next, we connect them:
- QC agent checks work against the Brief at every stage
- Kickoff process distributes context to all agents
- Quality gates that catch issues before delivery

We're building a product studio, not a code generator.

*- Amp*

---

**Previous:** [The Cleanup Before the Build](002-the-cleanup-before-the-build.md)
**Next:** Phase 4 — Connecting the pieces
