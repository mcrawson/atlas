# ATLAS Session Notes - March 3, 2026

## Overview
UI updates, agent icons, new agents (Hype & Cortex), and logo changes.

---

## Agent Icon Updates

All agent icons were updated across the codebase:

| Agent | Old Icon | New Icon |
|-------|----------|----------|
| Sketch | ✏️ | 💡 |
| Tinker | 🔧 | 🛠️ |
| Oracle | 👁️ | 🔮 |
| Launch | 🚀 | 📤 |
| Buzz | 📢 | 📡 |
| Tally | 🧮 | 💰 |
| Hype | 🎉 | 🎉 (new agent) |
| Sentry | 🛡️ | 🛡️ (unchanged) |
| Cortex | 🧠 | 🧠 (renamed from Forge → Coach → Cortex) |

### Files Updated for Icons
- `atlas/agents/architect.py`
- `atlas/agents/mason.py`
- `atlas/agents/oracle.py`
- `atlas/agents/launch.py`
- `atlas/agents/buzz.py`
- `atlas/agents/sprint_meeting.py`
- `atlas/web/templates/agents.html`
- `atlas/web/templates/dashboard.html`
- `atlas/web/templates/project_detail.html`
- `atlas/web/templates/training.html`
- `atlas/web/templates/task_detail.html`
- `atlas/web/templates/spec_new.html`
- `atlas/web/templates/spec_execute.html`
- `atlas/web/templates/knowledge.html`
- `atlas/web/templates/knowledge_chat.html`
- `atlas/web/templates/partials/agent_status.html`
- `atlas/web/templates/partials/agent_pipeline.html`
- `atlas/web/templates/partials/execution_results.html`
- `atlas/web/templates/partials/smart_conversation.html`
- `atlas/web/routes/projects.py`

---

## New Agent: Hype (Advertising & Promotion)

**File:** `atlas/agents/hype.py`

The hypeman. Takes what the team built and makes the world care.

### Capabilities
- 11 content types (landing pages, social posts, email campaigns, etc.)
- 8 tone presets (professional, casual, bold, etc.)
- Generates marketing content for any platform

### Integration
- Added to `atlas/agents/__init__.py`
- Added to `atlas/agents/manager.py`
- Added to agents.html and dashboard.html

### Image Prompt for Hype
```
Professional portrait photo of a charismatic Black man in his early 30s,
confident smile, wearing stylish modern business casual (blazer, no tie),
creative/marketing professional vibe, urban office background with mood
lighting, energetic and approachable expression, 8k professional photography
```

---

## New Agent: Cortex (Training Data Intelligence)

**File:** `atlas/agents/cortex.py`

The brain of your training system. Understands your data, tracks your progress, assesses readiness, and guides you to training your own local AI model.

### Capabilities
- Analyzes training data quality & readiness
- Provides data-driven insights and assessments
- Estimates cost savings from local models
- Helps with Ollama deployment
- Built-in fallback responses if no AI provider

### Files Created/Updated
- `atlas/agents/cortex.py` - Main agent class
- `atlas/agents/__init__.py` - Added exports
- `atlas/web/templates/training.html` - Added "Ask Cortex" button
- `atlas/web/templates/training_chat.html` - New chat page
- `atlas/web/templates/agents.html` - Added Cortex to team
- `atlas/web/routes/dashboard.py` - Added chat routes

### Image Prompt for Cortex
```
Professional portrait of an East Asian woman in her mid-30s,
sharp perceptive eyes, sleek black hair with subtle blue-tinted
highlights, calm and knowing expression, wearing a modern dark
tech-forward outfit with subtle geometric patterns, cool cyan
and blue accent lighting illuminating her face, minimalist
futuristic background with faint neural network patterns,
the person who understands the data, 8k professional photography
```

---

## Logo Update

Changed the favicon to a simple green orb (matching the dashboard orb style).

**File:** `atlas/web/static/images/logo.svg`

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <!-- Outer ring -->
  <circle cx="16" cy="16" r="14" fill="rgba(0, 255, 136, 0.15)" stroke="#00ff88" stroke-width="2"/>
  <!-- Inner solid orb -->
  <circle cx="16" cy="16" r="7" fill="#00ff88"/>
</svg>
```

**Files Updated:**
- `atlas/web/static/images/logo.svg` - Created SVG
- `atlas/web/templates/base.html` - Added SVG favicon link

---

## Agent Portraits (Agents Page)

Removed grayscale filter from agent portraits on the Agent Command Center page.

**File:** `atlas/web/static/css/atlas.css`

Changed `.agent-portrait` to display in full color (removed `filter: grayscale(100%)`).

---

## Agent Image Prompts (for reference)

### Sketch (Planning & Strategy)
```
Professional portrait of a thoughtful woman in her 30s, Scandinavian features,
blonde hair in professional style, intelligent and analytical expression,
wearing smart casual attire, soft studio lighting, architectural/planning
mood, 8k professional photography
```

### Tinker (Implementation)
```
Professional portrait of a white man in his late 20s/early 30s,
focused craftsman expression, wearing casual tech worker attire
(hoodie or flannel), workshop/maker space background, warm lighting,
hands-on builder vibe, 8k professional photography
```

### Oracle (Quality & Verification)
```
Professional portrait of a wise-looking person with penetrating gaze,
perhaps South Asian or Middle Eastern features, wearing glasses,
scholarly/reviewer appearance, dramatic lighting, deep thinker expression,
8k professional photography
```

### Launch (Deployment)
```
Professional portrait of a confident flight director type,
diverse background, wearing technical/mission control style attire,
determined expression, screens/tech in background, 8k professional photography
```

### Buzz (Communications)
```
Professional portrait of a friendly communications specialist,
approachable expression, modern office/broadcast setting,
headset or communication devices nearby, warm lighting,
8k professional photography
```

### Sentry (Webhook Gatekeeper)
```
Professional portrait of a British man, security professional appearance,
alert but calm expression, perhaps wearing a blazer,
protective/guardian demeanor, 8k professional photography
```

### Tally (Cost Tracking)
```
Professional portrait of a tall Scandinavian woman,
accountant/analyst appearance, precise and organized expression,
perhaps glasses, financial/analytical setting, 8k professional photography
```

---

## Bugs Fixed

1. **HypeAgent missing `get_system_prompt`** - Added the required abstract method implementation
2. **Syntax error in dashboard.py** - Fixed f-string with escaped quotes in Forge chat responses

---

## Files to Add Images For

The following agents need portrait images in `atlas/web/static/images/agents/`:
- `cortex.webp` - Added!

---

## Next Steps (if continuing)

1. ~~Generate and add Cortex portrait image~~ Done!
2. Consider adding Cortex to dashboard mini cards
3. Test Cortex chat functionality with AI providers
4. Review and test all agent chat interfaces
