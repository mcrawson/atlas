"""Dashboard routes for ATLAS Web."""

import logging
import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pathlib import Path
from pydantic import BaseModel

from atlas.agents.training_collector import get_collector
from atlas.agents.cortex import get_cortex

logger = logging.getLogger("atlas.web.dashboard")


class CortexChatMessage(BaseModel):
    """Chat message for Cortex."""
    message: str
    history: list[dict] = []

router = APIRouter()


@router.get("/offline", response_class=HTMLResponse)
async def offline(request: Request):
    """Offline page for PWA."""
    templates = request.app.state.templates
    return templates.TemplateResponse("offline.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    templates = request.app.state.templates
    agent_manager = request.app.state.agent_manager
    project_manager = request.app.state.project_manager

    # Get agent status
    agent_status = {}
    if agent_manager:
        agent_status = agent_manager.get_all_status()

    # Get recent projects
    recent_projects = []
    project_stats = {}
    if project_manager:
        try:
            recent_projects = await project_manager.get_projects(limit=5, include_tasks=True)
            project_stats = await project_manager.get_stats()
        except Exception as e:
            logger.error(f"Failed to load dashboard projects: {e}")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "agent_status": agent_status,
            "recent_projects": recent_projects,
            "project_stats": project_stats,
        }
    )


@router.get("/partials/agent-status", response_class=HTMLResponse)
async def agent_status_partial(request: Request):
    """Partial for agent status cards (HTMX)."""
    templates = request.app.state.templates
    agent_manager = request.app.state.agent_manager

    agent_status = {}
    if agent_manager:
        agent_status = agent_manager.get_all_status()

    return templates.TemplateResponse(
        "partials/agent_status.html",
        {
            "request": request,
            "agents": agent_status,
        }
    )


@router.get("/partials/recent-projects", response_class=HTMLResponse)
async def recent_projects_partial(request: Request):
    """Partial for recent projects list (HTMX)."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    projects = []
    if project_manager:
        try:
            projects = await project_manager.get_projects(limit=5, include_tasks=True)
        except Exception as e:
            logger.error(f"Failed to load recent projects: {e}")

    return templates.TemplateResponse(
        "partials/project_list.html",
        {
            "request": request,
            "projects": projects,
        }
    )


@router.get("/partials/activity-feed", response_class=HTMLResponse)
async def activity_feed_partial(request: Request):
    """Partial for activity feed (HTMX)."""
    templates = request.app.state.templates

    # Activity feed is populated via WebSocket
    return templates.TemplateResponse(
        "partials/activity_feed.html",
        {
            "request": request,
            "activities": [],
        }
    )


@router.get("/training", response_class=HTMLResponse)
async def training_dashboard(request: Request):
    """Training data dashboard for local LLM development."""
    templates = request.app.state.templates

    collector = get_collector()
    stats = collector.get_stats()
    savings = collector.get_cost_savings_potential()

    return templates.TemplateResponse(
        "training.html",
        {
            "request": request,
            "stats": stats.to_dict(),
            "savings": savings,
        }
    )


@router.post("/training/export", response_class=HTMLResponse)
async def export_training_data(request: Request):
    """Export training data as JSONL file."""
    collector = get_collector()

    # Export to temp file
    export_path = Path("/tmp/atlas_training_data.jsonl")
    count = collector.export_training_set(
        str(export_path),
        min_quality="all"  # Export all for now
    )

    if export_path.exists():
        return FileResponse(
            export_path,
            media_type="application/jsonl",
            filename="atlas_training_data.jsonl"
        )

    # Fallback
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "training.html",
        {
            "request": request,
            "stats": collector.get_stats().to_dict(),
            "savings": collector.get_cost_savings_potential(),
            "message": f"Exported {count} examples",
        }
    )


@router.post("/training/export-ollama")
async def export_for_ollama(request: Request):
    """Export Modelfile for creating Ollama custom model."""
    collector = get_collector()

    # Export Modelfile
    export_path = Path("/tmp/atlas_Modelfile")
    count = collector.export_for_ollama(str(export_path))

    if export_path.exists():
        return FileResponse(
            export_path,
            media_type="text/plain",
            filename="Modelfile"
        )

    return {"error": "Failed to export", "examples": count}


@router.get("/training/chat", response_class=HTMLResponse)
async def training_chat_page(request: Request):
    """Chat with Cortex agent about training."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "training_chat.html",
        {"request": request}
    )


@router.post("/training/chat")
async def training_chat(request: Request, chat: CortexChatMessage):
    """Process a chat message with Cortex agent."""
    agent_manager = request.app.state.agent_manager

    # Get training stats for context
    collector = get_collector()
    stats = collector.get_stats()
    cortex = get_cortex()

    # Analyze readiness
    readiness = cortex.analyze_readiness(stats.to_dict())
    savings = collector.get_cost_savings_potential()

    # If no AI provider available, use Cortex's built-in responses
    if not agent_manager or not hasattr(agent_manager, 'router'):
        # Generate contextual response based on the question
        response = _generate_cortex_response(chat.message, stats.to_dict(), readiness, savings)
        return JSONResponse({
            "response": response,
            "stats": stats.to_dict(),
        })

    try:
        # Build context with training stats
        context = {
            "conversation_history": chat.history,
            "chat_mode": True,
            "training_stats": stats.to_dict(),
            "readiness": readiness,
            "savings": savings,
        }

        # Build prompt with Cortex's system prompt and context
        system_prompt = cortex.get_system_prompt()
        stats_context = f"""
CURRENT TRAINING STATS:
- Total Examples: {stats.total_examples}
- Approval Rate: {stats.approval_rate:.1%}
- By Agent: Sketch={stats.by_agent.get('architect', 0)}, Tinker={stats.by_agent.get('mason', 0)}, Oracle={stats.by_agent.get('oracle', 0)}

READINESS ASSESSMENT:
- Score: {readiness['score']}/100
- Status: {readiness['status_text']}
- Blockers: {', '.join(readiness['blockers']) if readiness['blockers'] else 'None'}
- Recommendations: {', '.join(readiness['recommendations']) if readiness['recommendations'] else 'Looking good!'}

POTENTIAL SAVINGS:
- Monthly Cloud Cost: ${savings.get('monthly_cost', 0):.2f}
- Estimated Savings: ${savings.get('potential_savings', 0):.2f}/month
"""

        full_prompt = f"{system_prompt}\n\n{stats_context}\n\nUser Question: {chat.message}"

        # Use the router to get a response
        response_text, token_info = await agent_manager.router.generate(
            prompt=full_prompt,
            temperature=0.7,
        )

        return JSONResponse({
            "response": response_text,
            "stats": stats.to_dict(),
            "tokens_used": token_info.get("total_tokens", 0),
        })

    except Exception as e:
        logger.error(f"Cortex chat error: {e}")
        # Fallback to built-in responses
        response = _generate_cortex_response(chat.message, stats.to_dict(), readiness, savings)
        return JSONResponse({
            "response": response,
            "stats": stats.to_dict(),
        })


def _generate_cortex_response(message: str, stats: dict, readiness: dict, savings: dict) -> str:
    """Generate a contextual response from Cortex without AI."""
    message_lower = message.lower()

    total = stats.get("total_examples", 0)
    approval = stats.get("approval_rate", 0)
    score = readiness.get("score", 0)
    status = readiness.get("status_text", "Unknown")

    # Check for common questions
    if any(word in message_lower for word in ["ready", "start", "begin", "fine-tune", "finetune"]):
        if score >= 80:
            return f"""Great news! You're **ready for training**! 🎉

**Your Stats:**
- {total} training examples collected
- {approval:.0%} approval rate
- Readiness score: {score}/100

**Next Steps:**
1. Export your training data using the "Export Data" button
2. Install Ollama if you haven't: `curl -fsSL https://ollama.com/install.sh | sh`
3. Create your custom model with the exported Modelfile
4. Test your local model

You've put in the work - you've earned this! 🎯"""
        else:
            blockers = readiness.get("blockers", [])
            recs = readiness.get("recommendations", [])
            response = f"""You're making progress, but not quite ready yet.

**Current Status:** {status}
**Readiness Score:** {score}/100

"""
            if blockers:
                response += "**What's Blocking You:**\n"
                for b in blockers:
                    response += f"- {b}\n"
            if recs:
                response += "\n**Recommendations:**\n"
                for r in recs:
                    response += f"- {r}\n"

            response += "\nKeep using ATLAS and I'll let you know when you're ready!"
            return response

    elif any(word in message_lower for word in ["how", "look", "status", "progress", "stat"]):
        by_agent = stats.get("by_agent", {})
        return f"""Here's how your training data is looking:

**Overall Progress:**
- 📊 Total Examples: **{total}**
- ✅ Approval Rate: **{approval:.0%}**
- 🎯 Readiness Score: **{score}/100** ({status})

**By Agent:**
- 💡 Sketch: {by_agent.get('architect', 0)} examples
- 🛠️ Tinker: {by_agent.get('mason', 0)} examples
- 🔮 Oracle: {by_agent.get('oracle', 0)} examples

**Goal:** ~500 examples with >70% approval rate for best results.

{"Keep it up! You're doing great." if score >= 50 else "Use ATLAS more to collect training examples."}"""

    elif any(word in message_lower for word in ["save", "cost", "money", "worth"]):
        monthly_cost = savings.get("monthly_cost", 0)
        potential = savings.get("potential_savings", 0)
        return f"""Let's talk about potential savings with a local model:

**Current Cloud Costs (estimated):**
- Monthly API spend: ~${monthly_cost:.2f}

**With a Local Model:**
- Potential monthly savings: **${potential:.2f}**
- Yearly savings: **${potential * 12:.2f}**

**The Math:**
- Cloud APIs: ~$0.01 per 1K tokens
- Local inference: ~$0.001 per 1K tokens (electricity)
- That's roughly **90% savings** on inference costs!

**Note:** You'll need a GPU with 8GB+ VRAM for good performance. Most consumer GPUs (RTX 3060+) work great."""

    elif any(word in message_lower for word in ["export", "download", "get data"]):
        return """To export your training data:

**Option 1: JSONL Format**
Click the "Export Data" button on the Training page to download your examples in JSONL format. This works with most fine-tuning tools.

**Option 2: Ollama Modelfile**
Click "Export for Ollama" to get a Modelfile you can use directly with Ollama to create your custom model.

**Using the Export:**
```bash
# With Ollama
ollama create atlas-local -f Modelfile
ollama run atlas-local

# With other tools (MLX, llama.cpp, etc.)
# Use the JSONL file with your preferred training framework
```"""

    elif any(word in message_lower for word in ["ollama", "local", "deploy", "run"]):
        return """Here's how to deploy your local ATLAS model with Ollama:

**1. Install Ollama**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**2. Export Your Modelfile**
Use the "Export for Ollama" button on the Training page.

**3. Create Your Model**
```bash
ollama create atlas-local -f Modelfile
```

**4. Run Your Model**
```bash
ollama run atlas-local
```

**Hardware Recommendations:**
- Minimum: 8GB VRAM (RTX 3060, M1 Mac)
- Recommended: 16GB+ VRAM (RTX 4080, M2 Pro+)
- CPU-only: Possible but slower

Your model will run entirely on your hardware - no cloud costs! 🧠"""

    else:
        return f"""I'm Cortex, your training data intelligence. 🧠

I can help you understand:
- **Training readiness** - Am I ready to fine-tune?
- **Data quality** - How's my training data looking?
- **Cost savings** - How much could I save with a local model?
- **Exporting data** - How do I export for Ollama?
- **Local deployment** - How do I run my own model?

**Your Current Stats:**
- {total} examples collected
- {approval:.0%} approval rate
- Readiness: {status}

What would you like to know?"""


@router.get("/setup", response_class=HTMLResponse)
async def setup_status(request: Request):
    """Setup status page showing platform configuration."""
    templates = request.app.state.templates

    # Define all platforms and their required env vars
    platforms = [
        {
            "id": "ai_providers",
            "name": "AI Providers",
            "icon": "🤖",
            "description": "Core AI providers for ATLAS agents",
            "category": "core",
            "env_vars": [
                {"name": "OPENAI_API_KEY", "description": "OpenAI API key", "required": False, "url": "https://platform.openai.com/api-keys"},
                {"name": "ANTHROPIC_API_KEY", "description": "Anthropic API key", "required": False, "url": "https://console.anthropic.com/"},
                {"name": "GEMINI_API_KEY", "description": "Google Gemini API key", "required": False, "url": "https://aistudio.google.com/apikey"},
            ],
            "note": "At least one AI provider is required",
        },
        {
            "id": "github",
            "name": "GitHub",
            "icon": "🐙",
            "description": "Code repository and version control",
            "category": "core",
            "env_vars": [
                {"name": "GITHUB_TOKEN", "description": "Personal access token", "required": True, "url": "https://github.com/settings/tokens"},
            ],
            "scopes": "repo, read:user",
        },
        {
            "id": "slack",
            "name": "Slack",
            "icon": "💬",
            "description": "Notifications and two-way integration",
            "category": "communication",
            "env_vars": [
                {"name": "SLACK_BOT_TOKEN", "description": "Bot token (xoxb-...)", "required": True, "url": "https://api.slack.com/apps"},
                {"name": "SLACK_SIGNING_SECRET", "description": "Signing secret for webhooks", "required": False, "url": "https://api.slack.com/apps"},
            ],
        },
        {
            "id": "canva",
            "name": "Canva",
            "icon": "🎨",
            "description": "Design assets - app icons, book covers, graphics",
            "category": "design",
            "env_vars": [
                {"name": "CANVA_API_KEY", "description": "Canva API key", "required": True, "url": "https://www.canva.com/developers/"},
                {"name": "CANVA_BRAND_ID", "description": "Brand kit ID (optional)", "required": False},
            ],
        },
        {
            "id": "figma",
            "name": "Figma",
            "icon": "🖼️",
            "description": "UI design and prototyping",
            "category": "design",
            "env_vars": [
                {"name": "FIGMA_API_TOKEN", "description": "Personal access token", "required": True, "url": "https://www.figma.com/developers/api"},
            ],
        },
        {
            "id": "google_docs",
            "name": "Google Docs",
            "icon": "📝",
            "description": "Document creation and formatting",
            "category": "documents",
            "env_vars": [
                {"name": "GOOGLE_CREDENTIALS_PATH", "description": "Path to OAuth credentials JSON", "required": True, "url": "https://console.cloud.google.com/"},
                {"name": "GOOGLE_ACCESS_TOKEN", "description": "OAuth access token", "required": True},
            ],
            "note": "Requires OAuth 2.0 flow setup",
        },
        {
            "id": "app_store",
            "name": "Apple App Store",
            "icon": "🍎",
            "description": "iOS app publishing",
            "category": "app_stores",
            "env_vars": [
                {"name": "APP_STORE_ISSUER_ID", "description": "Issuer ID (UUID)", "required": True, "url": "https://appstoreconnect.apple.com/access/api"},
                {"name": "APP_STORE_KEY_ID", "description": "Key ID", "required": True},
                {"name": "APP_STORE_PRIVATE_KEY_PATH", "description": "Path to .p8 key file", "required": True},
            ],
            "note": "Requires Apple Developer Program membership ($99/year)",
        },
        {
            "id": "play_store",
            "name": "Google Play Store",
            "icon": "🤖",
            "description": "Android app publishing",
            "category": "app_stores",
            "env_vars": [
                {"name": "GOOGLE_PLAY_SERVICE_ACCOUNT", "description": "Service account JSON path", "required": True, "url": "https://play.google.com/console/developers"},
                {"name": "ANDROID_PACKAGE_NAME", "description": "App package name", "required": True},
            ],
            "note": "Requires Google Play Developer account ($25 one-time)",
        },
        {
            "id": "vercel",
            "name": "Vercel",
            "icon": "▲",
            "description": "Web deployment and hosting",
            "category": "hosting",
            "env_vars": [
                {"name": "VERCEL_TOKEN", "description": "API token", "required": True, "url": "https://vercel.com/account/tokens"},
                {"name": "VERCEL_TEAM_ID", "description": "Team ID (for team deployments)", "required": False},
            ],
        },
        {
            "id": "npm",
            "name": "npm",
            "icon": "📦",
            "description": "JavaScript package registry",
            "category": "packages",
            "env_vars": [
                {"name": "NPM_TOKEN", "description": "npm access token", "required": True, "url": "https://www.npmjs.com/settings/~/tokens"},
            ],
        },
        {
            "id": "pypi",
            "name": "PyPI",
            "icon": "🐍",
            "description": "Python package registry",
            "category": "packages",
            "env_vars": [
                {"name": "PYPI_TOKEN", "description": "PyPI API token", "required": True, "url": "https://pypi.org/manage/account/token/"},
                {"name": "USE_TEST_PYPI", "description": "Use TestPyPI instead", "required": False},
            ],
        },
    ]

    # Check configuration status for each platform
    for platform in platforms:
        configured_count = 0
        required_count = 0

        for env_var in platform["env_vars"]:
            value = os.getenv(env_var["name"])
            env_var["configured"] = bool(value)
            env_var["masked_value"] = _mask_value(value) if value else None

            if env_var.get("required", True):
                required_count += 1
                if value:
                    configured_count += 1

        # Determine overall platform status
        if required_count == 0:
            platform["status"] = "optional"
        elif configured_count == required_count:
            platform["status"] = "ready"
        elif configured_count > 0:
            platform["status"] = "partial"
        else:
            platform["status"] = "missing"

        platform["configured_count"] = configured_count
        platform["required_count"] = required_count

    # Group by category
    categories = {
        "core": {"name": "Core Services", "platforms": []},
        "communication": {"name": "Communication", "platforms": []},
        "design": {"name": "Design Tools", "platforms": []},
        "documents": {"name": "Documents", "platforms": []},
        "app_stores": {"name": "App Stores", "platforms": []},
        "hosting": {"name": "Hosting", "platforms": []},
        "packages": {"name": "Package Registries", "platforms": []},
    }

    for platform in platforms:
        cat = platform.get("category", "other")
        if cat in categories:
            categories[cat]["platforms"].append(platform)

    # Calculate overall stats
    total_platforms = len(platforms)
    ready_platforms = sum(1 for p in platforms if p["status"] == "ready")
    partial_platforms = sum(1 for p in platforms if p["status"] == "partial")

    return templates.TemplateResponse(
        "setup.html",
        {
            "request": request,
            "categories": categories,
            "platforms": platforms,
            "stats": {
                "total": total_platforms,
                "ready": ready_platforms,
                "partial": partial_platforms,
                "missing": total_platforms - ready_platforms - partial_platforms,
            },
        }
    )


def _mask_value(value: str) -> str:
    """Mask a sensitive value for display."""
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return value[:4] + "..." + value[-4:]
