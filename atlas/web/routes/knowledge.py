"""Knowledge Base web routes."""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from ...knowledge import KnowledgeManager, KnowledgeCategory

logger = logging.getLogger("atlas.web.knowledge")
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class ChatMessage(BaseModel):
    """Chat message from the user."""
    message: str
    history: list[dict] = []


@router.get("/", response_class=HTMLResponse)
async def knowledge_index(request: Request):
    """Knowledge base index page."""
    km = KnowledgeManager()
    entries = km.get_all()

    # Group by category
    by_category = {}
    platforms = set()
    for entry in entries:
        cat = entry.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(entry)
        if entry.platform:
            platforms.add(entry.platform)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "knowledge.html",
        {
            "request": request,
            "by_category": by_category,
            "platforms": sorted(platforms),
            "total": len(entries),
        }
    )


@router.get("/{entry_id}", response_class=HTMLResponse)
async def knowledge_entry(request: Request, entry_id: str):
    """View a knowledge entry."""
    km = KnowledgeManager()
    entry = km.get(entry_id)

    if not entry:
        return HTMLResponse("<h1>Entry not found</h1>", status_code=404)

    # Get related entries
    related = []
    for related_id in entry.related_entries:
        related_entry = km.get(related_id)
        if related_entry:
            related.append(related_entry)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "knowledge_entry.html",
        {
            "request": request,
            "entry": entry,
            "related": related,
        }
    )


@router.get("/search/{query}", response_class=HTMLResponse)
async def search_knowledge(request: Request, query: str):
    """Search knowledge base."""
    km = KnowledgeManager()
    results = km.search(query, limit=20)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "knowledge_search.html",
        {
            "request": request,
            "query": query,
            "results": results,
        }
    )


@router.get("/platform/{platform}", response_class=HTMLResponse)
async def knowledge_by_platform(request: Request, platform: str):
    """Get knowledge entries for a platform."""
    km = KnowledgeManager()
    entries = km.get_by_platform(platform)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "knowledge_platform.html",
        {
            "request": request,
            "platform": platform,
            "entries": entries,
        }
    )


@router.get("/chat", response_class=HTMLResponse)
async def knowledge_chat_page(request: Request):
    """Chat with Launch agent about deployment."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "knowledge_chat.html",
        {"request": request}
    )


@router.post("/chat")
async def knowledge_chat(request: Request, chat: ChatMessage):
    """Process a chat message with Launch agent."""
    agent_manager = request.app.state.agent_manager

    if not agent_manager or not hasattr(agent_manager, 'launch'):
        return JSONResponse({
            "error": "Launch agent not available. Configure AI providers to enable chat.",
            "response": None
        })

    try:
        # Build context from conversation history
        context = {
            "conversation_history": chat.history,
            "chat_mode": True,  # Indicates this is a chat, not a project deployment
        }

        # Process with Launch agent
        output = await agent_manager.launch.process(
            task=chat.message,
            context=context,
            previous_output=None
        )

        return JSONResponse({
            "response": output.content,
            "platforms": output.artifacts.get("platforms", []),
            "tokens_used": output.tokens_used,
        })

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JSONResponse({
            "error": str(e),
            "response": None
        })
