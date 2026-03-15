# ATLAS 3.0 Build Plan

**Project:** ATLAS Rebuild - "Sellable Products, Not Code"
**Started:** 2026-03-13
**Status:** Planning Phase

---

## The Mission

> **ATLAS is a product studio that combines human creativity with ethical AI to build transformative solutions for our clients and the public.**

This mission is the foundation. Every agent, every decision, every product ties back to this.

| Word | Meaning |
|------|---------|
| **Product studio** | We make finished, sellable products. Not demos. Not prototypes. |
| **Human creativity** | You bring the ideas and vision. AI doesn't replace you. |
| **Ethical AI** | We build responsibly. Quality matters. No shortcuts. |
| **Transformative solutions** | Products that solve real problems. That matter. |
| **Clients and the public** | For paying customers AND broader impact. |

---

## Executive Summary

ATLAS 2.x produced functional code but not sellable products. The output looked like developer prototypes, not market-ready goods. This rebuild fundamentally changes how ATLAS approaches product creation.

**The Core Problem:** Agents executed prompts without understanding the mission. No business analysis, no design thinking, no mockups before building, no quality gates, no learning from feedback.

**The Solution:** Transform ATLAS from a "prompt executor" into a "product studio" where:
- Every agent knows the mission
- Ideas are discussed, not just submitted
- Business analysis happens before building
- You see polished mockups before building starts
- Specialized builders create quality products
- QC is both system AND human
- Agents learn and improve after every project

---

## What We're Building

### New Architecture Overview

```
                         ┌─────────────────────────────────┐
                         │           THE MISSION            │
                         │  "ATLAS is a product studio      │
                         │   that combines human creativity │
                         │   with ethical AI to build       │
                         │   transformative solutions"      │
                         └─────────────────────────────────┘
                                        │
                    Every agent, every step ties back to this
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRODUCT CREATION FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

1. IDEA CHAT
   ┌─────────────────────────────────────────────────────────┐
   │ You + ATLAS discuss the idea                            │
   │ - Conversation, not submission                          │
   │ - Flush it out, explore options                         │
   │ - Come up with a game plan                              │
   └─────────────────────────────────────────────────────────┘
                              ↓
2. BUSINESS ANALYSIS
   ┌─────────────────────────────────────────────────────────┐
   │ Is this a good idea?                                    │
   │ - Market analysis                                       │
   │ - Competition                                           │
   │ - Viability                                             │
   │ → GO / NO-GO DECISION                                   │
   └─────────────────────────────────────────────────────────┘
                              ↓ (if Go)
3. ROUND TABLE
   ┌─────────────────────────────────────────────────────────┐
   │ Assign the work                                         │
   │ - Who builds this? (which specialized builder)          │
   │ - What are they going to do?                            │
   │ - What does success mean?                               │
   └─────────────────────────────────────────────────────────┘
                              ↓
4. MOCKUP (Polished)
   ┌─────────────────────────────────────────────────────────┐
   │ See the product BEFORE building                         │
   │ - Polished visual preview                               │
   │ - Close to final appearance                             │
   │ → YOU APPROVE / REVISE                                  │
   └─────────────────────────────────────────────────────────┘
                              ↓ (if Approved)
5. BUILD
   ┌─────────────────────────────────────────────────────────┐
   │ SPECIALIZED BUILDERS                                    │
   │                                                         │
   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
   │  │ Printable    │ │ Document     │ │ Web          │    │
   │  │ Builder      │ │ Builder      │ │ Builder      │    │
   │  │ - Planners   │ │ - Books      │ │ - Landing    │    │
   │  │ - Cards      │ │ - Guides     │ │ - SPAs       │    │
   │  │ - Worksheets │ │ - Manuals    │ │ - Dashboards │    │
   │  └──────────────┘ └──────────────┘ └──────────────┘    │
   │                                                         │
   │  ┌──────────────┐                                       │
   │  │ App Builder  │  ← React Native (cross-platform)      │
   │  │ - iOS apps   │                                       │
   │  │ - Android    │                                       │
   │  └──────────────┘                                       │
   │                                                         │
   │ Builds based on approved mockup                         │
   └─────────────────────────────────────────────────────────┘
                              ↓
6. QC (Two Layers)
   ┌─────────────────────────────────────────────────────────┐
   │ System Tests: Does it work technically?                 │
   │ You Test: Is it sellable? Does it feel right?          │
   │ → PASS / FAIL                                           │
   └─────────────────────────────────────────────────────────┘
                              ↓ (if Pass)
7. DEPLOY
   ┌─────────────────────────────────────────────────────────┐
   │ Push to marketplace                                     │
   │ - Etsy, Amazon KDP, App Store, etc.                    │
   │ - You decide when and where                            │
   └─────────────────────────────────────────────────────────┘
                              ↓
8. AMP - ADVERTISE
   ┌─────────────────────────────────────────────────────────┐
   │ Social media promotion                                  │
   │ - Create content to sell the product                   │
   │ - Platform-optimized posts                             │
   └─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          AFTER EVERY PROJECT                                 │
└─────────────────────────────────────────────────────────────────────────────┘

9. PULSE - AGENT REVIEW
   ┌─────────────────────────────────────────────────────────┐
   │ HR for the agents                                       │
   │ - How did each agent perform?                          │
   │ - What gaps showed up?                                 │
   │ - What needs updating?                                 │
   │ → Recommends prompt updates                            │
   └─────────────────────────────────────────────────────────┘
                              ↓
10. CONTINUOUS TRAINING
   ┌─────────────────────────────────────────────────────────┐
   │ Two methods:                                            │
   │ 1. Prompt Updates - Pulse recommends, we update agents │
   │ 2. Knowledge Base - Lessons, tech, patterns grow       │
   │                                                         │
   │ Agents get smarter with every project                  │
   └─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              ONGOING                                         │
└─────────────────────────────────────────────────────────────────────────────┘

AMP - JOURNEY DOCUMENTATION
   ┌─────────────────────────────────────────────────────────┐
   │ Documents the ATLAS story                               │
   │ - What we're building                                  │
   │ - Challenges and successes                             │
   │ - Public blog posts and social content                 │
   └─────────────────────────────────────────────────────────┘
```

### Specialized Builder Architecture

Instead of one "Tinker" that does everything poorly, we have focused builders:

```
atlas/agents/builders/
├── __init__.py              # Builder registry (add new builders here)
├── base.py                  # Shared logic (change once, affects all)
├── config.py                # Settings that change often (not in code)
├── templates/               # Shared design assets
│   ├── color_palettes.py
│   └── typography.py
│
├── printable/               # Planners, cards, worksheets
│   ├── builder.py           # PrintableBuilder class
│   ├── prompts.py           # Printable-specific prompts
│   └── templates/           # Planner layouts, card templates
│
├── document/                # Books, guides, manuals
│   ├── builder.py           # DocumentBuilder class
│   ├── prompts.py           # Document-specific prompts
│   └── templates/           # Book layouts, chapter templates
│
├── web/                     # Landing pages, SPAs
│   ├── builder.py           # WebBuilder class
│   ├── prompts.py           # Web-specific prompts
│   └── templates/           # Component templates
│
└── app/                     # Mobile apps
    ├── builder.py           # AppBuilder class
    ├── prompts.py           # Mobile-specific prompts
    └── templates/
        └── react_native/    # React Native components
```

**Why this structure:**
- Each builder is an expert in its domain
- Shared logic in `base.py` - change once, affects all
- Config separated from code - tweak settings without touching builders
- Add new builders by creating a folder + one line in registry

**Builder Registry:**
```python
BUILDERS = {
    "physical_planner": PrintableBuilder,
    "physical_cards": PrintableBuilder,
    "doc_book": DocumentBuilder,
    "doc_guide": DocumentBuilder,
    "web_spa": WebBuilder,
    "web_landing": WebBuilder,
    "mobile_ios": AppBuilder,         # React Native
    "mobile_android": AppBuilder,     # React Native
    "mobile_cross_platform": AppBuilder,
}
```

### Key Principles

1. **Mission First**: Every agent knows the mission. Every decision ties back to it.
2. **Human Creativity + Ethical AI**: You bring ideas and judgment. AI builds responsibly.
3. **Mockup Before Build**: See polished visuals before committing to build.
4. **Show Product, Not Code**: Users see rendered output AND code (for learning).
5. **QC is System + Human**: Automated tests AND you test it yourself.
6. **User is Final Authority**: Nothing ships without your explicit approval.
7. **Specialized Builders**: Expert builders for each product type.
8. **Continuous Improvement**: Agents learn from every project via prompts and knowledge base.

---

## What We Keep

### Keep - Core Infrastructure
| Component | Location | Why Keep |
|-----------|----------|----------|
| FastAPI web framework | `atlas/web/` | Solid foundation, works well |
| SQLite database | `atlas.db` | Simple, reliable, sufficient |
| Project model | `atlas/projects/` | Good data structure |
| Multi-provider agents | `atlas/agents/ollama_provider.py` | OpenAI/Ollama flexibility |
| Web templates | `atlas/web/templates/` | Good UI foundation |
| Logging middleware | `atlas/web/middleware/` | Useful for debugging |

### Keep - Modified
| Component | Location | Changes Needed |
|-----------|----------|----------------|
| Sketch agent | `atlas/agents/sketch.py` | Add business context consumption |
| Tinker agent | `atlas/agents/tinker.py` | Focus on sellable output |
| Oracle agent | `atlas/agents/oracle.py` | Become QC at each stage |
| Project routes | `atlas/web/routes/projects.py` | Add new workflow stages |
| Standards | `atlas/standards.py` | Update sellability criteria |

---

## What We Remove

### Remove - Complexity That Didn't Work
| Component | Location | Why Remove |
|-----------|----------|------------|
| Canva auto-integration | `atlas/integrations/platforms/canva.py` | API can't place assets on canvas - fundamental limitation |
| Auto-deploy logic | Various | Premature - focus on quality first |
| Complex routing | `atlas/agents/governor.py` | Over-engineered for current needs |
| MCP server | `atlas/mcp/` | Adds complexity without value yet |

### Remove - Misleading Features
| Component | Why Remove |
|-----------|------------|
| "Sellability" checks that don't work | Oracle was just another LLM guessing |
| Automatic "passed validation" | Gave false confidence |
| Silent retries | Hid problems from user |

---

## Build Phases

### Phase 0: Kickoff Meeting (Before We Start)

**Goal:** Align on the plan before writing any code

**Participants:** You + Claude

**Agenda:**
1. [ ] Review this Build Plan together
2. [ ] Confirm architecture decisions make sense
3. [ ] Confirm builder priority order (Printable → Document → App → Web)
4. [ ] Answer any open questions
5. [ ] Identify any missing pieces
6. [ ] Set expectations for Phase 1
7. [ ] Go / No-Go decision

**Questions to Answer:**
- [ ] How detailed should the Business Brief be?
- [ ] Should QC have veto power or just advisory?
- [ ] Any product types missing from the builders?
- [ ] What does "done" look like for Phase 1?

**Outcome Options:**
| Decision | What Happens |
|----------|--------------|
| **GO** | Proceed to Phase 1: Foundation Reset |
| **UPDATE** | Revise the plan based on discussion, then re-review |
| **PAUSE** | More research needed before proceeding |

**Status:** IN PROGRESS

**Session Notes:**
- 2026-03-13: Reviewed architecture, confirmed specialized builders, confirmed React Native for mobile. Open questions remain. Resume next session to complete kickoff.

---

### Phase 1: Foundation Reset (Week 1)

**Goal:** Clean up codebase, establish new builder architecture

**Tasks:**
1. [ ] Remove Canva auto-integration code
2. [ ] Remove MCP server code
3. [ ] Simplify project routes (remove auto-triggers)
4. [ ] Create builder architecture:
   - `atlas/agents/builders/__init__.py` (registry)
   - `atlas/agents/builders/base.py` (shared logic)
   - `atlas/agents/builders/config.py` (settings)
5. [ ] Create `atlas/agents/analyst.py` (stub)
6. [ ] Create `atlas/agents/qc.py` (stub)
7. [ ] Update database schema for new workflow stages
8. [ ] Create Business Brief model

**Deliverable:** Clean codebase with builder architecture in place

### Phase 2: Analyst Agent (Week 2)

**Goal:** Business analysis before any building

**Tasks:**
1. [ ] Implement Analyst agent with prompts for:
   - Executive summary
   - Market analysis
   - Target customer profile
   - Competition analysis
   - SWOT analysis
   - Financial projections
2. [ ] Create Business Brief template
3. [ ] Add UI for business brief display
4. [ ] Add user approval step for brief

**Deliverable:** New project flow starts with Analyst producing business brief

### Phase 3: Specialized Builders (Week 2-3)

**Goal:** Expert builders for each product type

**Tasks:**
1. [ ] Create PrintableBuilder
   - Prompts for planners, cards, worksheets
   - Templates for common layouts
   - PDF rendering pipeline
2. [ ] Create DocumentBuilder
   - Prompts for books, guides, manuals
   - Chapter/section templates
   - PDF/EPUB output
3. [ ] Create WebBuilder
   - Prompts for landing pages, SPAs
   - Component templates
   - HTML/CSS/JS output
4. [ ] Create AppBuilder
   - React Native as default framework
   - Prompts for mobile apps
   - Screen/navigation templates
   - App store asset generation
5. [ ] Update builder registry with all product types
6. [ ] Add routing logic (project type → correct builder)

**Deliverable:** Four specialized builders, each expert in its domain

### Phase 4: Kickoff + QC Integration (Week 3-4)

**Goal:** Shared context and quality gates

**Tasks:**
1. [ ] Create Kickoff process that distributes Business Brief
2. [ ] Each builder receives:
   - Business Brief
   - Plan from Sketch
   - Quality criteria for its product type
3. [ ] Implement QC agent that checks against Business Brief
4. [ ] Add QC checkpoint after Sketch
5. [ ] Add QC checkpoint after each Builder
6. [ ] Create QC report format:
   - Pass/Fail status
   - Issues found
   - Recommendations
   - Alignment with brief score
7. [ ] Add UI for QC reports

**Deliverable:** Builders work with full context, QC runs at each stage

### Phase 5: User Review Flow (Week 4-5)

**Goal:** User is final authority at every stage

**Tasks:**
1. [ ] Create staged approval UI
2. [ ] Show PRODUCT not code:
   - Printables: PDF preview
   - Documents: PDF/rendered preview
   - Web: Live iframe preview
   - Apps: Screenshots + video mockup
3. [ ] Show QC assessment alongside product
4. [ ] User options: Approve / Request Changes / Reject
5. [ ] On "Request Changes": Generate revision guidance
6. [ ] On "Reject": Log reason for learning

**Deliverable:** User reviews rendered product at each stage

### Phase 6: Learning System (Week 5-6)

**Goal:** ATLAS learns what "sellable" means to THIS user

**Tasks:**
1. [ ] Create feedback logging (approvals, rejections, reasons)
2. [ ] Build user preference profile over time
3. [ ] Analyst incorporates user history
4. [ ] QC calibrates to user standards
5. [ ] Surface patterns in Lessons Learned doc

**Deliverable:** System improves based on user feedback

### Phase 7: Polish Agent (Week 6)

**Goal:** Design refinement as a dedicated step

**Tasks:**
1. [ ] Create Polish agent focused on visual quality
2. [ ] Style guides and consistency checking
3. [ ] Typography, spacing, color application
4. [ ] Professional finishing touches
5. [ ] Before/after comparison UI

**Deliverable:** Dedicated design polish step

---

## Success Criteria

### Minimum Viable Success
- [ ] User can submit an idea and see a Business Brief before building starts
- [ ] User approves plan before Tinker builds
- [ ] User sees rendered PRODUCT, not code
- [ ] QC report accompanies each deliverable
- [ ] Failed QC generates actionable report

### Full Success
- [ ] System learns from user feedback
- [ ] Products look professional, not like prototypes
- [ ] Zero "just text on paper" outputs
- [ ] User says: "This looks like something I could sell"

---

## Risk Mitigation

### Risk 1: LLMs Still Can't Design
**Mitigation:** Focus on templates, style guides, design systems. Don't ask LLM to invent design - ask it to apply established patterns.

### Risk 2: Business Analysis Adds Too Much Overhead
**Mitigation:** Make Analyst fast. Default templates for common product types. Skip for simple projects.

### Risk 3: Too Many Approval Steps Slow Everything Down
**Mitigation:** Add "auto-approve if QC passes with high confidence" option. But default to user review.

---

## Timeline

| Week | Focus | Key Deliverable |
|------|-------|-----------------|
| 1 | Foundation Reset | Clean codebase, builder architecture |
| 2 | Analyst + Builders Start | Business brief flow, PrintableBuilder |
| 3 | Builders Complete | DocumentBuilder, WebBuilder, AppBuilder |
| 4 | Kickoff + QC | Shared context, quality gates |
| 5 | User Review | Staged approval UI, product previews |
| 6 | Learning + Polish | Feedback system, design refinement |

**Total:** 6 weeks to functional ATLAS 3.0

### Builder Priority Order

Build the specialized builders in this order based on your priorities:

| Priority | Builder | Products | Why This Order |
|----------|---------|----------|----------------|
| 1 | PrintableBuilder | Planners, cards, worksheets | Etsy products, quickest to sell |
| 2 | DocumentBuilder | Books, guides | KDP products, similar to printables |
| 3 | AppBuilder | Mobile apps (React Native) | Higher value, more complex |
| 4 | WebBuilder | Landing pages, SPAs | Support for app marketing sites |

---

## Open Questions

1. How detailed should the Business Brief be? (MVP vs comprehensive)
2. Should QC have veto power or just advisory?
3. What constitutes "high confidence" for auto-approve?
4. ~~How do we show rendered products for all product types?~~ **ANSWERED:**
   - Printables/Documents: PDF preview
   - Web: Live iframe
   - Apps: Screenshots + video mockup (Expo preview link if possible)

## Decisions Made

| Decision | Choice | Date |
|----------|--------|------|
| Mobile framework | React Native (cross-platform) | 2026-03-13 |
| Builder architecture | Specialized builders, not one Tinker | 2026-03-13 |
| Builder priority | Printable → Document → App → Web | 2026-03-13 |

---

## Living Documents

These documents must be updated as we proceed:

| Document | Purpose | Update When |
|----------|---------|-------------|
| **MISSION.md** | The foundation - why ATLAS exists | Rarely (only if mission evolves) |
| **BUILD-PLAN.md** | What we're building, how, and status | Decisions made, phases complete, scope changes |
| **USER-MANUAL.md** | How to use ATLAS | Features added, workflows change |
| **LESSONS-LEARNED.md** | Issues and root causes | Bugs found, mistakes made, patterns discovered |
| **docs/journey/** | Amp's public content about building ATLAS | After every session |

This is non-negotiable. Every session should check if these need updates.

**Last Updated:** 2026-03-13
