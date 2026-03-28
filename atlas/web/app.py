"""FastAPI application factory for ATLAS Web Dashboard."""

import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

logger = logging.getLogger("atlas.web")
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routes import dashboard, projects, agents, api, knowledge, automation, specs, github, slack
from .websocket import router as websocket_router
from .auth import require_auth, is_auth_enabled
from .middleware import RateLimitMiddleware, RateLimitConfig, RequestLoggingMiddleware

# OpenAPI tag descriptions
OPENAPI_TAGS = [
    {
        "name": "API",
        "description": "Core REST API endpoints for programmatic access to ATLAS functionality.",
    },
    {
        "name": "Projects",
        "description": "Project management - create, view, and manage development projects.",
    },
    {
        "name": "Agents",
        "description": "Multi-agent workflow system - Architect, Mason, and Oracle agents.",
    },
    {
        "name": "Dashboard",
        "description": "Web dashboard routes for the ATLAS UI.",
    },
    {
        "name": "Knowledge",
        "description": "Knowledge base and memory management.",
    },
    {
        "name": "Automation",
        "description": "Background tasks and automation workflows.",
    },
    {
        "name": "Specs",
        "description": "Specification management for projects.",
    },
    {
        "name": "WebSocket",
        "description": "Real-time communication via WebSocket.",
    },
    {
        "name": "GitHub",
        "description": "GitHub Issues sync (Transporter) - bidirectional sync with GitHub.",
    },
    {
        "name": "Slack",
        "description": "Slack integration - two-way conversations for idea development.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - initialize managers on startup."""
    # Initialize project manager
    if app.state.project_manager:
        await app.state.project_manager.init_db()

    # Initialize GitHub Transporter if configured
    try:
        import os
        if os.getenv("ATLAS_GITHUB_TOKEN"):
            from atlas.integrations.github import get_transporter, TransporterConfig
            config = TransporterConfig.from_env()
            transporter = get_transporter(
                project_manager=app.state.project_manager,
                agent_manager=app.state.agent_manager,
                config=config,
            )
            app.state.transporter = transporter
            logger.info("GitHub Transporter initialized")

            # Register completion callback to post agent outputs to GitHub
            if app.state.agent_manager and config.post_agent_outputs:
                async def post_outputs_to_github(task_id: int, outputs: dict):
                    """Post agent outputs to linked GitHub issue."""
                    try:
                        # Format outputs for posting
                        formatted = {}
                        for name, output in outputs.items():
                            if hasattr(output, 'content'):
                                formatted[name] = {
                                    "content": output.content,
                                    "status": output.status.value if hasattr(output, 'status') else "completed",
                                    "metadata": output.metadata if hasattr(output, 'metadata') else {},
                                }
                        if formatted:
                            await transporter.post_agent_output(task_id, formatted)
                    except Exception as e:
                        logger.debug(f"Could not post outputs to GitHub: {e}")

                app.state.agent_manager.register_completion_callback(post_outputs_to_github)
                logger.info("Registered GitHub output posting callback")
    except ImportError as e:
        logger.debug(f"GitHub integration module not available: {e}")
    except Exception as e:
        logger.warning(f"Could not initialize GitHub Transporter: {e}")

    yield

    # Cleanup on shutdown
    if hasattr(app.state, "transporter") and app.state.transporter:
        try:
            await app.state.transporter.api.close()
        except Exception:
            pass


def create_app(
    agent_manager=None,
    project_manager=None,
    router=None,
    memory=None,
    providers=None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        agent_manager: AgentManager instance
        project_manager: ProjectManager instance
        router: ATLAS Router instance
        memory: MemoryManager instance
        providers: Dictionary of AI providers

    Returns:
        Configured FastAPI application
    """
    # Set up dependencies (auth if enabled)
    dependencies = []
    if is_auth_enabled():
        from fastapi import Depends
        dependencies.append(Depends(require_auth))

    app = FastAPI(
        title="ATLAS - Automated Thinking, Learning & Advisory System",
        description="""
## ATLAS 2.0 Multi-Agent Web Dashboard

ATLAS is an AI-powered development assistant that orchestrates multiple specialized agents
to help you build software projects from concept to completion.

### Key Features

- **Multi-Agent Workflow**: Architect → Mason → Oracle pipeline for comprehensive development
- **Project Management**: Track ideas, tasks, and progress
- **Smart Conversations**: AI-powered idea refinement
- **Multi-Provider Support**: Claude, GPT, Gemini, and Ollama

### Agent Roles

- **Architect**: Designs system architecture and creates specifications
- **Mason**: Implements code based on specifications
- **Oracle**: Reviews and validates implementations

### API Overview

Use the `/api` endpoints for programmatic access to ATLAS functionality.
The web dashboard provides a visual interface for the same features.
        """,
        version="2.0.0",
        lifespan=lifespan,
        dependencies=dependencies,
        openapi_tags=OPENAPI_TAGS,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # Store dependencies in app state
    app.state.agent_manager = agent_manager
    app.state.project_manager = project_manager
    app.state.router = router
    app.state.memory = memory
    app.state.providers = providers or {}

    # Setup templates and static files
    web_dir = Path(__file__).parent
    templates_dir = web_dir / "templates"
    static_dir = web_dir / "static"

    # Create directories if they don't exist
    templates_dir.mkdir(parents=True, exist_ok=True)
    static_dir.mkdir(parents=True, exist_ok=True)

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Setup templates
    templates = Jinja2Templates(directory=str(templates_dir))
    app.state.templates = templates

    # Add middleware (order matters - first added is outermost)
    app.add_middleware(RateLimitMiddleware, config=RateLimitConfig())
    app.add_middleware(RequestLoggingMiddleware)

    # Include routers
    app.include_router(dashboard.router, tags=["Dashboard"])
    app.include_router(projects.router, prefix="/projects", tags=["Projects"])
    app.include_router(agents.router, prefix="/agents", tags=["Agents"])
    app.include_router(api.router, prefix="/api", tags=["API"])
    app.include_router(knowledge.router, tags=["Knowledge"])
    app.include_router(automation.router, tags=["Automation"])
    logger.debug(f"Including specs router: {specs.router}, routes: {[r.path for r in specs.router.routes]}")
    app.include_router(specs.router, prefix="/specs", tags=["Specs"])
    app.include_router(websocket_router, tags=["WebSocket"])
    app.include_router(github.router, prefix="/github", tags=["GitHub"])
    app.include_router(slack.router, prefix="/slack", tags=["Slack"])

    return app


def create_default_app(use_ollama: bool = True, prefer_provider: str = "openai") -> FastAPI:
    """Create app with default managers for standalone use.

    Args:
        use_ollama: If True, create AgentManager (kept for backwards compat)
        prefer_provider: Preferred AI provider ("openai", "claude", "gemini", "ollama")
    """
    from atlas.projects.manager import ProjectManager
    from atlas.routing.router import Router

    # Use default data directory
    data_dir = Path(__file__).parent.parent.parent / "data"

    # Create project manager
    project_manager = ProjectManager(data_dir)

    # Create router for AI provider routing
    router = Router()
    logger.info("Router initialized")

    # Create agent manager with multiple providers
    agent_manager = None
    providers = {}
    if use_ollama:
        try:
            # Try multi-provider first (uses OpenAI/Claude when available)
            from atlas.agents.ollama_provider import create_multi_provider_agent_manager
            agent_manager = create_multi_provider_agent_manager(prefer_provider=prefer_provider)
            # Extract providers from agent_manager if available
            if hasattr(agent_manager, 'providers'):
                providers = agent_manager.providers
            logger.info("Agent Manager initialized with multiple providers")
        except Exception as e:
            logger.warning(f"Multi-provider init failed: {e}")
            # Fall back to Ollama-only
            try:
                from atlas.agents.ollama_provider import create_agent_manager_with_ollama
                agent_manager = create_agent_manager_with_ollama()
                # Extract providers from agent_manager if available
                if hasattr(agent_manager, 'providers'):
                    providers = agent_manager.providers
                logger.info("Agent Manager initialized with Ollama (fallback)")
            except Exception as e2:
                logger.warning(f"Could not initialize Ollama: {e2}. Running in demo mode.")

    return create_app(
        project_manager=project_manager,
        agent_manager=agent_manager,
        router=router,
        providers=providers,
    )


# Module-level app instance for uvicorn
# Usage: uvicorn atlas.web.app:app --reload
app = create_default_app(use_ollama=True)
