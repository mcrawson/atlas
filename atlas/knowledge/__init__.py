"""ATLAS Knowledge Base System.

Stores and retrieves platform guides, deployment knowledge, and best practices.
"""

from .models import KnowledgeEntry, KnowledgeCategory, SearchResult
from .manager import KnowledgeManager
from .augmenter import KnowledgeAugmenter, get_knowledge_augmenter

__all__ = [
    "KnowledgeEntry",
    "KnowledgeCategory",
    "SearchResult",
    "KnowledgeManager",
    "KnowledgeAugmenter",
    "get_knowledge_augmenter",
]
