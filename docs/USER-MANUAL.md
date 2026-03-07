# ATLAS User Manual

**Automated Thinking, Learning & Advisory System**

Version: 2.0
Last Updated: 2026-03-07

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard](#dashboard)
3. [Projects](#projects)
4. [Agents](#agents)
5. [Knowledge Base](#knowledge-base)
6. [GitHub Integration](#github-integration)
7. [Platform Setup](#platform-setup)
8. [API Reference](#api-reference)

---

## Getting Started

### Starting ATLAS

```bash
cd ~/ai-workspace/atlas
source .venv/bin/activate
./scripts/atlas-web
```

ATLAS will start on **http://localhost:8080** and automatically open your browser.

### First-Time Setup

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Add your API keys to `.env` (at minimum, one AI provider):
   ```
   OPENAI_API_KEY=sk-your-key
   # or
   ANTHROPIC_API_KEY=sk-ant-your-key
   ```

3. Restart ATLAS to apply changes.

---

## Dashboard

**URL:** http://localhost:8080/

The dashboard shows:
- Active projects
- Recent activity
- Agent status
- Quick actions

### Example: Creating a New Project

1. Click **"New Project"** or go to `/projects`
2. Enter your idea (can be vague)
3. ATLAS will ask clarifying questions about:
   - What you want to build
   - Who it's for
   - Key features
   - **Design preferences** (style, colors, inspiration)
4. Once complete, Sketch creates the plan

---

## Projects

**URL:** http://localhost:8080/projects

### Project Lifecycle

```
Idea → Conversation → Plan (Sketch) → Build (Tinker) → Verify (Oracle) → Deploy (Launch)
```

### Example: Creating a Mobile App

**Step 1: Start the conversation**
```
You: "I want to make a fart machine app"
ATLAS: "That sounds fun! Who is the target audience?"
You: "Anyone who wants a laugh"
ATLAS: "What features do you envision?"
You: "Different fart sounds, fun UI, daily challenges"
ATLAS: "What style are you going for? Playful, minimal, cartoonish?"
You: "Playful and colorful, like the app Heads Up"
```

**Step 2: Review the brief**

ATLAS generates a project brief with:
- Core features
- Target users
- Design preferences (playful style, colorful, inspired by Heads Up)
- Technical requirements

**Step 3: Sketch creates the plan**

Click "Start Planning" and Sketch (the architect agent) creates:
- Screen-by-screen breakdown
- Technical architecture
- Asset checklist

**Step 4: Tinker builds it**

Click "Start Building" and Tinker (the builder agent) generates:
- Complete source code
- File structure
- Implementation details

**Step 5: Preview the result**

The **Preview** tab shows:
- **Live Preview**: Rendered HTML/CSS in an iframe (for web projects)
- **Code**: All generated code with syntax highlighting
- **Files**: List of files created

### Project Types Supported

| Type | Icon | Examples |
|------|------|----------|
| Mobile App | 📱 | iOS app, Android app, Cross-platform |
| Web App | 🌐 | SPA, Dashboard, Landing page |
| Website | 🖥️ | Portfolio, Blog, E-commerce |
| API | ⚡ | REST API, GraphQL |
| CLI Tool | 💻 | Command-line utility |
| Library | 📦 | npm package, Python library |
| Document | 📄 | Book, Guide, Manual |
| Process | 🔄 | Workflow, Procedure |

---

## Agents

**URL:** http://localhost:8080/agents

ATLAS uses specialized AI agents that work together:

### Sketch (Planning Agent)
**Role:** Strategic planning and architecture

**What it does:**
- Analyzes your requirements
- Creates detailed blueprints
- Identifies risks and dependencies
- Designs system architecture

**Example output:**
```markdown
## App Screens
- Home Screen: Sound board with fart buttons
- Settings: Volume, haptics toggle
- Daily Challenge: Today's challenge card

## Technical Architecture
- Platform: React Native (cross-platform)
- State: Redux for sound management
- Storage: AsyncStorage for preferences
```

### Tinker (Building Agent)
**Role:** Implementation and coding

**What it does:**
- Writes production-ready code
- Follows the plan from Sketch
- Creates all necessary files
- Implements features

**Example output:**
```javascript
// HomeScreen.js
export default function HomeScreen() {
  const playSound = (soundId) => {
    // Sound implementation
  };

  return (
    <View style={styles.container}>
      <SoundBoard onPlay={playSound} />
    </View>
  );
}
```

### Oracle (Verification Agent)
**Role:** Quality assurance and testing

**What it does:**
- Reviews code for issues
- Suggests improvements
- Validates against requirements
- Checks for best practices

### Launch (Deployment Agent)
**Role:** Publishing and deployment

**What it does:**
- Deploys to Vercel/Netlify
- Publishes to npm/PyPI
- Prepares app store submissions
- Handles release management

### Buzz (Communications Agent)
**Role:** Notifications and updates

**What it does:**
- Sends Slack notifications
- Posts GitHub comments
- Provides status updates

### Hype (Marketing Agent)
**Role:** Marketing and promotion

**What it does:**
- Writes app store descriptions
- Creates marketing copy
- Generates social media content

### Cortex (Training Agent)
**Role:** Learning and improvement

**What it does:**
- Collects training data
- Assesses model readiness
- Improves agent performance

---

## Knowledge Base

**URL:** http://localhost:8080/knowledge/

Store and retrieve information that agents can use.

### Example: Adding Knowledge

```
POST /api/knowledge
{
  "title": "Company Style Guide",
  "content": "Use blue (#0066CC) as primary color. Sans-serif fonts only.",
  "tags": ["design", "branding"]
}
```

Agents will reference this when building projects.

---

## GitHub Integration

**URL:** http://localhost:8080/github/status

Bidirectional sync between ATLAS tasks and GitHub Issues.

### Setup

1. Create a GitHub Personal Access Token:
   - Go to https://github.com/settings/tokens/new
   - Check: `repo`, `read:user`
   - Generate and copy the token

2. Add to `.env`:
   ```
   ATLAS_GITHUB_TOKEN=ghp_your-token
   ATLAS_GITHUB_DEFAULT_REPO=username/repo-name
   ```

3. Restart ATLAS

### Example: Syncing a Task to GitHub

**Via API:**
```bash
curl -X POST "http://localhost:8080/github/sync/task/1"
```

**Response:**
```json
{
  "success": true,
  "message": "Issue created",
  "issue_number": 1,
  "url": "https://github.com/username/repo/issues/1"
}
```

### Example: Syncing a GitHub Issue to ATLAS

```bash
curl -X POST "http://localhost:8080/github/sync/issue?repo=username/repo&issue_number=1&project_id=24"
```

### Webhook Setup (Real-time Sync)

For automatic sync when issues change:

1. Start ngrok: `ngrok http 8080`
2. Copy the HTTPS URL
3. Add webhook in GitHub repo settings:
   - URL: `https://your-ngrok-url/github/webhook`
   - Events: Issues, Issue comments
   - Secret: (set in `.env` as `ATLAS_GITHUB_WEBHOOK_SECRET`)

---

## Platform Setup

**URL:** http://localhost:8080/setup

See which integrations are configured.

### Required Environment Variables

| Platform | Variables | Get From |
|----------|-----------|----------|
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| Anthropic | `ANTHROPIC_API_KEY` | https://console.anthropic.com/ |
| GitHub | `ATLAS_GITHUB_TOKEN` | https://github.com/settings/tokens |
| Vercel | `VERCEL_TOKEN` | https://vercel.com/account/tokens |
| Canva | `CANVA_API_KEY` | https://www.canva.com/developers/ |

See `SETUP-GUIDE.md` for complete setup instructions.

---

## API Reference

### Projects

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects` | GET | List all projects |
| `/api/projects/{id}` | GET | Get project details |
| `/api/projects` | POST | Create project |
| `/api/projects/{id}/tasks` | POST | Create task |

### GitHub

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/github/status` | GET | Check sync status |
| `/github/sync/task/{id}` | POST | Sync task to GitHub |
| `/github/sync/issue` | POST | Sync issue to ATLAS |

### Example: Create a Project via API

```bash
curl -X POST http://localhost:8080/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My New App",
    "description": "A cool app that does things"
  }'
```

---

## Changelog

### 2026-03-07
- Added design preference questions to idea conversation
- Fixed live preview rendering (Tinker's code now shows in iframe)
- Fixed GitHub reverse sync (issue → task)
- Added auto-load .env to startup

### 2026-03-06
- Set up GitHub integration
- Created `mcrawson/atlas-tasks` repo
- Added webhooks for real-time sync

---

## Troubleshooting

### ATLAS won't start
- Check that `.venv` is activated
- Verify `.env` file exists
- Check for port 8080 conflicts

### Preview shows placeholders
- Restart ATLAS after the 2026-03-07 update
- Ensure the project has been built by Tinker

### GitHub sync fails
- Verify `ATLAS_GITHUB_TOKEN` is set (not just `GITHUB_TOKEN`)
- Check token has `repo` scope
- Restart ATLAS after adding token

---

*For detailed setup instructions, see `SETUP-GUIDE.md`*
