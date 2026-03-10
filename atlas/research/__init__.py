"""Research module for live web search capabilities.

This module provides web search functionality that agents can use
to augment their prompts with up-to-date information.

Usage:
    from atlas.research import get_research_augmenter

    # In an agent's process() method:
    research_augmenter = get_research_augmenter()
    research_context = await research_augmenter.augment_prompt(task, context)
    if research_context:
        prompt += f"\\n\\n{research_context}"
"""

from .augmenter import ResearchAugmenter, get_research_augmenter
from .models import ResearchCategory, ResearchResult, SearchResult
from .searcher import WebSearcher, get_web_searcher

__all__ = [
    # Main interface
    "get_research_augmenter",
    "ResearchAugmenter",
    # Models
    "ResearchCategory",
    "ResearchResult",
    "SearchResult",
    # Lower-level access
    "WebSearcher",
    "get_web_searcher",
]
