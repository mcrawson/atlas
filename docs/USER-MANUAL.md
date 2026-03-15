# ATLAS User Manual

**Automated Thinking, Learning & Advisory System**

Version: 3.0
Last Updated: 2026-03-15

---

## The Mission

> **ATLAS is a product studio that combines human creativity with ethical AI to build transformative solutions for our clients and the public.**

This is the foundation. Every agent, every decision, every product ties back to this.

---

## What is ATLAS?

ATLAS is a product studio that turns your ideas into sellable products.

- **You** bring the creativity, ideas, and final judgment
- **ATLAS** provides the AI agents that analyze, design, build, and promote
- **Together** you create products that matter

**Core Philosophy:** If a customer wouldn't pay for it, it's not done.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [How ATLAS Works](#how-atlas-works)
3. [The Workflow](#the-workflow)
4. [Agents](#agents)
5. [Quality Control](#quality-control)
6. [Reviewing & Approving](#reviewing--approving)
7. [Product Types](#product-types)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Starting ATLAS

```bash
cd ~/ai-workspace/atlas
source .venv/bin/activate
./scripts/atlas-web
```

ATLAS runs at **http://localhost:8080**

### Your First Project

1. Go to **New Project**
2. Describe your idea (be as detailed or vague as you want)
3. Review the **Business Brief** (market analysis, target customer, etc.)
4. Approve → Analyst hands off to Sketch
5. Review the **Plan** (what will be built, how)
6. Approve → Sketch hands off to Tinker
7. Review the **Product** (rendered output, not code)
8. Approve → Product is ready

You see the actual product at every stage, not code.

---

## How ATLAS Works

### The Old Way (v2.x)
```
Idea → Build → Validation → Done
         ↑
    (No mission, no mockups, no real QC, hope it's good)
```

### The New Way (v3.0)
```
Idea Chat → Business Analysis → Round Table → Mockup → Build → QC → Deploy → Advertise
    ↓              ↓                 ↓           ↓        ↓      ↓
 Discuss       Go/No-Go         Assign work   You see   Build  System
 options       decision         Define success it first  it     + You
```

**Key Differences:**
- Mission at the core - every agent knows it
- Idea Chat is a conversation, not just submission
- Business Analysis can kill bad ideas early
- Mockup BEFORE building - you see it first
- QC is system tests AND you testing
- Amp advertises finished products
- Pulse reviews agents, recommends improvements
- Continuous training - agents get smarter

---

## The Workflow

### Stage 1: Business Analysis

**Agent:** Analyst

**What Happens:**
Analyst researches your idea and produces a Business Brief containing:
- Executive Summary
- Target Customer Profile
- Market Analysis
- Competition Overview
- SWOT Analysis
- Financial Projections
- Success Criteria

**Your Action:** Review and approve the Business Brief

**Why This Matters:** Every agent will work from this brief. If the brief is wrong, everything downstream is wrong.

---

### Stage 2: Kickoff

**What Happens:**
All agents receive the Business Brief and understand:
- What the product is
- Who it's for
- What "success" looks like
- Their specific role

**Your Action:** Review the kickoff summary (optional)

**Why This Matters:** No more telephone game. Everyone knows the mission.

---

### Stage 3: Planning

**Agent:** Sketch

**What Happens:**
Sketch creates a detailed plan WITH business context:
- Technical architecture
- Visual design specifications
- Content requirements
- Quality criteria

**Quality Check:** QC reviews plan against Business Brief

**Your Action:** Review plan + QC assessment, then approve

**Why This Matters:** Catching issues in planning is cheaper than fixing them in building.

---

### Stage 4: Building

**Agent:** Tinker

**What Happens:**
Tinker builds the product following Sketch's plan:
- Generates all files
- Creates content
- Applies structure

**Quality Check:** QC reviews output against plan AND Business Brief

**Your Action:** Review rendered product + QC assessment, then approve

**Why This Matters:** You see the actual product, not code.

---

### Stage 5: Polish

**Agent:** Polish

**What Happens:**
Polish refines the visual design:
- Typography improvements
- Color consistency
- Spacing and layout
- Professional finishing

**Quality Check:** QC reviews polished product

**Your Action:** Final review and approval

**Why This Matters:** The difference between "works" and "sells" is polish.

---

### Stage 6: Ship

**What Happens:**
Product is ready for deployment/publishing to:
- Etsy (printables, templates)
- Gumroad (digital products)
- Amazon KDP (books, journals)
- App stores (mobile apps)
- Web hosting (websites)

**Your Action:** Choose where to publish

---

## Agents

### Analyst (NEW in v3.0)
**Role:** Business Intelligence

Creates the Business Brief that guides all other agents. Ensures the product has a market and clear success criteria.

### Sketch
**Role:** Planning & Architecture

Creates detailed plans that include both technical AND design specifications. Works from the Business Brief.

### Tinker
**Role:** Building & Implementation

Generates the actual product files. Focuses on sellable output, not just working code.

### Polish (NEW in v3.0)
**Role:** Design Refinement

Applies visual design improvements. Makes output look professional, not like a prototype.

### QC (NEW in v3.0)
**Role:** Quality Assurance

Checks output at every stage against the Business Brief. Produces reports you can review.

### Oracle
**Role:** Final Validation

Performs comprehensive sellability check before shipping.

### Buzz
**Role:** Notifications

Keeps you updated on progress. Sends Slack/email notifications.

---

## Quality Control

### How QC Works

After each stage, QC produces a report:

```
QC REPORT - Sketch Plan
========================

ALIGNMENT: 92%
Matches Business Brief requirements

CHECKS PASSED:
✓ Target customer defined
✓ Visual specifications included
✓ Content requirements listed
✓ Success criteria measurable

ISSUES FOUND:
⚠ Missing: Accessibility considerations

RECOMMENDATION: APPROVE with note to address accessibility in build phase

---
```

### QC Verdicts

| Verdict | Meaning | Your Action |
|---------|---------|-------------|
| **PASS** | Meets Business Brief | Review and approve |
| **PASS WITH NOTES** | Minor issues noted | Review notes, approve or request changes |
| **NEEDS REVISION** | Significant gaps | Request changes, review revision |
| **FAIL** | Does not meet criteria | Review failure report, redirect |

### What QC Checks

- **Alignment:** Does output match Business Brief?
- **Completeness:** Are all requirements addressed?
- **Quality:** Does it meet sellability standards?
- **Consistency:** Does it match previous stages?

---

## Reviewing & Approving

### What You See

At each stage, you see:

1. **The Product** - Rendered output (preview, PDF, etc.)
2. **QC Report** - Assessment against Business Brief
3. **Source** (optional) - Underlying files/code

### Your Options

| Action | When to Use |
|--------|-------------|
| **Approve** | QC passed, you're satisfied |
| **Request Changes** | Specific improvements needed |
| **Reject** | Fundamentally wrong direction |

### Request Changes Flow

1. You identify issues
2. Write feedback (what's wrong, what you want)
3. Agent receives feedback + original brief
4. Agent revises
5. QC re-checks
6. You review again

### The System Learns

Every approval, change request, and rejection is logged. Over time, ATLAS learns:
- What you consider "sellable"
- Your design preferences
- Your quality standards
- Common issues to avoid

---

## Product Types

| Type | Examples | Agents Used | Output Format |
|------|----------|-------------|---------------|
| **Printable** | Planners, cards, worksheets | Analyst → Sketch → Tinker → Polish | PDF |
| **Document** | Books, guides, manuals | Analyst → Sketch → Tinker → Polish | PDF/EPUB |
| **Web App** | SPA, dashboard | Analyst → Sketch → Tinker | HTML/CSS/JS |
| **Mobile App** | iOS, Android | Analyst → Sketch → Tinker | React Native/Flutter |
| **API** | REST, GraphQL | Analyst → Sketch → Tinker | Python/Node |

---

## Configuration

### Environment Variables

```bash
# Required - at least one AI provider
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key

# Optional - notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Optional - publishing
ETSY_API_KEY=your-key
GUMROAD_ACCESS_TOKEN=your-token
```

### Settings

Access settings at **http://localhost:8080/setup**

| Setting | Default | Description |
|---------|---------|-------------|
| Auto-approve QC pass | OFF | Automatically approve if QC passes |
| Show code view | OFF | Show source code alongside product |
| Notification level | All | Which events trigger notifications |

---

## Troubleshooting

### ATLAS won't start
```bash
# Check virtual environment
source .venv/bin/activate

# Check .env file exists
ls -la .env

# Check port 8080 is free
lsof -i :8080
```

### Agents aren't working
- Verify API key is set in `.env`
- Restart ATLAS after changing `.env`
- Check server logs: `cat /tmp/atlas_server.log`

### Product preview is blank
- Refresh the page
- Check that Tinker completed successfully
- Look for errors in QC report

### QC always fails
- Review the Business Brief - it may have unrealistic criteria
- Check if your feedback is being incorporated
- Lower quality thresholds in settings (not recommended)

---

## Changelog

### v3.0 (2026-03-13) - "Sellable Products" Release
- **NEW:** Analyst agent - Business Brief before building
- **NEW:** Kickoff process - All agents get full context
- **NEW:** QC at every stage - Quality gates, not just end validation
- **NEW:** Polish agent - Dedicated design refinement
- **NEW:** Learning system - ATLAS learns your preferences
- **CHANGED:** Show products, not code
- **CHANGED:** User approves at every stage
- **REMOVED:** Auto-triggers without consent
- **REMOVED:** Canva auto-integration (API limitations)

### v2.x
- Previous version - see archive for details

---

## Getting Help

- **Bug reports:** https://github.com/mcrawson/atlas/issues
- **Documentation:** `/docs/` folder
- **Build Plan:** `docs/BUILD-PLAN.md`
- **Lessons Learned:** `docs/LESSONS-LEARNED.md`

---

*This is a living document. Updated with every ATLAS change.*
