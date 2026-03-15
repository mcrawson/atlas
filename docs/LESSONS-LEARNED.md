# ATLAS Lessons Learned

**Purpose:** Track issues, root causes, and preventive measures.
**Started:** 2026-03-13

---

## The Core Lesson

> **We built ATLAS 2.x without a mission. Agents executed prompts but didn't know WHY.**

The fix: Everything now ties back to the mission.

> **ATLAS is a product studio that combines human creativity with ethical AI to build transformative solutions for our clients and the public.**

Every issue below traces back to this missing foundation.

---

## How to Use This Document

When an issue is discovered:
1. Add it to the appropriate category
2. Document what happened
3. Identify the root cause (ask "why" 5 times)
4. Document the fix or preventive measure
5. Tag with severity (Critical/Major/Minor)

---

## Issue Categories

- [Architecture Issues](#architecture-issues)
- [Agent Behavior Issues](#agent-behavior-issues)
- [Integration Issues](#integration-issues)
- [User Experience Issues](#user-experience-issues)
- [Code Quality Issues](#code-quality-issues)

---

## Architecture Issues

### ARCH-001: Agents Don't Understand the Mission
**Severity:** Critical
**Date Discovered:** 2026-03-13

**What Happened:**
Agents executed prompts without understanding WHY they were doing it. Each agent worked in isolation, like a telephone game. Output was "correct" code but not sellable products.

**Root Cause Analysis:**
- Why did agents not understand the mission? → There was no mission defined
- Why no mission? → We skipped the foundation and went straight to building
- Why skip the foundation? → Developer mindset - ship features, not products
- **Root Cause:** No mission. No north star. Agents had nothing to align to.

**Fix/Prevention:**
1. Define the mission: "ATLAS is a product studio that combines human creativity with ethical AI to build transformative solutions for our clients and the public."
2. Mission appears in EVERY agent's prompt - first thing they see
3. Mission stored in MISSION.md at project root
4. Every decision filters through: "Does this serve the mission?"
5. Round Table ensures all agents understand before building starts

**Status:** FIXED - Mission defined 2026-03-15

---

### ARCH-002: No Quality Gates Between Stages
**Severity:** Critical
**Date Discovered:** 2026-03-13

**What Happened:**
Work flowed from Sketch → Tinker → Oracle without checkpoints. Oracle at the end was too late - problems compounded. Oracle was just another LLM guessing if work was "sellable."

**Root Cause Analysis:**
- Why was QC only at the end? → Modeled after traditional development pipelines
- Why didn't Oracle catch issues? → Oracle had no objective criteria, just prompts
- Why no objective criteria? → No Business Brief to check against
- **Root Cause:** QC was decorative, not functional. No clear criteria = no real validation.

**Fix/Prevention:**
1. QC checkpoint after EVERY stage
2. QC checks against Business Brief (objective criteria)
3. QC produces report, not just pass/fail
4. User reviews QC report + output at each stage

**Status:** Planned for Phase 4

---

### ARCH-003: User Saw Code, Not Products
**Severity:** Major
**Date Discovered:** 2026-03-13

**What Happened:**
Project detail page showed source code, JSON, and file listings. Users had to imagine what the product would look like. No visual preview for physical products (planners, cards, etc.).

**Root Cause Analysis:**
- Why show code? → Developer-focused design
- Why no visual preview? → Assumed user would compile/render themselves
- Why assume that? → Built by developers, for developers
- **Root Cause:** Interface designed around implementation, not product.

**Fix/Prevention:**
1. Always render product preview (HTML, PDF, images)
2. Code is secondary, accessed via "View Source" button
3. Physical products show PDF preview
4. Web products show live iframe

**Status:** Planned for Phase 5

---

## Agent Behavior Issues

### AGENT-001: Tinker Produces "Working" Not "Sellable"
**Severity:** Critical
**Date Discovered:** 2026-03-13

**What Happened:**
Tinker generated functional code that worked but looked like a developer prototype. Recipe cards were "just text on paper." Planners had no design, no style, no visual appeal.

**Root Cause Analysis:**
- Why did output look like code? → Prompt asked for implementation
- Why just implementation? → No design requirements in plan
- Why no design requirements? → Sketch didn't include them
- Why didn't Sketch include them? → Sketch didn't receive design context
- **Root Cause:** Pipeline focused on code generation, not product creation. No design phase.

**Fix/Prevention:**
1. Business Brief includes design requirements
2. Sketch plan includes visual specifications
3. Add Polish agent for design refinement
4. Tinker prompt emphasizes "sellable" not just "working"

**Status:** Planned for Phase 7

---

### AGENT-002: Oracle Gave False Confidence
**Severity:** Major
**Date Discovered:** 2026-03-13

**What Happened:**
Oracle said "Passed validation on attempt 1" but products were clearly not sellable. Logs showed validation passing immediately without meaningful checks.

**Root Cause Analysis:**
- Why did Oracle pass bad work? → No clear rejection criteria
- Why no criteria? → Oracle was prompt-based, not rule-based
- Why prompt-based? → Assumed LLM could judge "sellable"
- **Root Cause:** LLMs cannot objectively assess quality without explicit criteria.

**Fix/Prevention:**
1. Replace vague "sellability" prompts with explicit checklist
2. QC checks against Business Brief requirements
3. Require specific evidence for pass/fail
4. Log actual checks performed, not just result

**Status:** Planned for Phase 4

---

## Integration Issues

### INT-001: Canva API Cannot Place Assets on Canvas
**Severity:** Critical
**Date Discovered:** 2026-03-13

**What Happened:**
Implemented full Canva OAuth + asset upload flow. Designs were created but were empty. Assets uploaded to user's library but could not be placed on canvas programmatically.

**Root Cause Analysis:**
- Why were designs empty? → Canva Connect API has no endpoint for placing assets
- Why implement if API couldn't do it? → Didn't read API limitations first
- Why not read limitations? → Rushed to implement "cool feature"
- **Root Cause:** Feature added without verifying API capabilities. Assumed API could do what we needed.

**Fix/Prevention:**
1. **Always read API documentation completely before implementing**
2. Create POC (proof of concept) for critical features before full implementation
3. Document API limitations in integration notes
4. Remove Canva auto-integration (too limited)

**Status:** Removed

---

### INT-002: OAuth Redirect URI Confusion (localhost vs 127.0.0.1)
**Severity:** Minor
**Date Discovered:** 2026-03-13

**What Happened:**
Canva OAuth failed with "Localhost URLs must use IP address '127.0.0.1'". Used `localhost:8000` initially, Canva requires `127.0.0.1`.

**Root Cause Analysis:**
- Why wrong URL? → Common developer assumption
- Why not documented? → It was documented, didn't read carefully
- **Root Cause:** Skipped documentation details.

**Fix/Prevention:**
1. Read OAuth documentation completely
2. Test OAuth flow immediately after setup
3. Document platform-specific requirements

**Status:** Fixed (but feature removed)

---

## User Experience Issues

### UX-001: No Visibility Into What Agents Are Doing
**Severity:** Major
**Date Discovered:** 2026-03-13

**What Happened:**
User submitted idea, waited, got output. No insight into Analyst thinking, Sketch planning, Tinker building. Felt like a black box.

**Root Cause Analysis:**
- Why no visibility? → Agents run async, return only final output
- Why only final output? → Original design focused on end result
- Why focus on end? → Assumed user only cared about deliverable
- **Root Cause:** No intermediate status, no streaming updates, no progress indicators.

**Fix/Prevention:**
1. Show each stage as it happens
2. Display intermediate outputs (Brief, Plan, Draft)
3. User approves at each stage, not just the end
4. Streaming updates for long operations

**Status:** Planned for Phase 5

---

### UX-002: Failures Happened Silently
**Severity:** Major
**Date Discovered:** 2026-03-13

**What Happened:**
When Canva design creation failed, logs showed error but UI showed nothing. User had to check server logs to understand what happened.

**Root Cause Analysis:**
- Why silent? → Error handling returned None, not error message
- Why return None? → Defensive coding pattern
- Why defensive? → Didn't want to crash
- **Root Cause:** Errors swallowed instead of surfaced. User-facing error display missing.

**Fix/Prevention:**
1. All errors surface to UI with clear message
2. Create error report format
3. Log errors AND show them
4. Never swallow exceptions silently

**Status:** Planned for Phase 4

---

## Code Quality Issues

### CODE-001: Auto-Triggers Without User Consent
**Severity:** Minor
**Date Discovered:** 2026-03-13

**What Happened:**
After Tinker completed, system auto-triggered Canva design creation without asking user. User had no control over when integrations fired.

**Root Cause Analysis:**
- Why auto-trigger? → Wanted to feel "smart" and "automated"
- Why no consent? → Assumed user would always want it
- **Root Cause:** Over-automation. User should control when actions happen.

**Fix/Prevention:**
1. No auto-triggers without explicit user consent
2. Default to manual triggers
3. Add "auto-approve" setting that user must enable
4. Always show what will happen before doing it

**Status:** Removed (Canva integration removed)

---

## Patterns to Watch

### Pattern: "Just Make It Work"
**Symptom:** Shipping code that runs but doesn't serve the mission.
**Fix:** Always ask "Would someone pay for this?"

### Pattern: "The API Can Probably Do That"
**Symptom:** Implementing features without verifying API capabilities.
**Fix:** POC first, implement second.

### Pattern: "Users Will Figure It Out"
**Symptom:** Showing raw output (code, JSON) instead of rendered product.
**Fix:** Always show the product, hide the implementation.

### Pattern: "Errors Can Fail Silently"
**Symptom:** Returning None or empty results instead of error messages.
**Fix:** Every error surfaces to the user with context.

---

## Root Cause Categories

For each issue, identify which category applies:

| Category | Description | Common Fixes |
|----------|-------------|--------------|
| **Missing Context** | Agent didn't have info it needed | Add to Business Brief, share more context |
| **Wrong Abstraction** | Solved wrong problem | Step back, understand actual need |
| **Skipped Documentation** | Didn't read the docs | Read first, implement second |
| **Over-Automation** | Did things user didn't ask for | Default to manual, add opt-in automation |
| **Developer Mindset** | Built for devs, not users | Show products, not code |
| **Wishful API** | Assumed API could do something | POC first, verify capabilities |

---

## Document Maintenance

Update this document when:
- A new issue is discovered
- A root cause is identified
- A fix is implemented
- A pattern emerges

**Format for new issues:**
```markdown
### [CATEGORY]-[NUMBER]: Short Title
**Severity:** Critical/Major/Minor
**Date Discovered:** YYYY-MM-DD

**What Happened:**
Description

**Root Cause Analysis:**
- Why X? → Because Y
- Why Y? → Because Z
- **Root Cause:** The fundamental issue

**Fix/Prevention:**
1. Action item
2. Action item

**Status:** Fixed/Planned/In Progress
```

---

**Last Updated:** 2026-03-13
