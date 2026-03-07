"""Knowledge Base data models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class KnowledgeCategory(Enum):
    """Categories of knowledge entries."""
    PLATFORM = "platform"           # iOS, Android, Web, etc.
    DEPLOYMENT = "deployment"       # How to deploy to stores/servers
    FRAMEWORK = "framework"         # React, Flutter, Django, etc.
    TOOL = "tool"                   # CLI tools, build systems
    BEST_PRACTICE = "best_practice" # Security, performance, UX
    TROUBLESHOOTING = "troubleshooting"  # Common errors and fixes


@dataclass
class KnowledgeEntry:
    """A single knowledge entry."""
    id: str
    title: str
    category: KnowledgeCategory
    content: str
    tags: list[str] = field(default_factory=list)
    platform: Optional[str] = None  # ios, android, web, etc.
    prerequisites: list[str] = field(default_factory=list)
    related_entries: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)  # Executable commands
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None  # Where this knowledge came from

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category.value,
            "content": self.content,
            "tags": self.tags,
            "platform": self.platform,
            "prerequisites": self.prerequisites,
            "related_entries": self.related_entries,
            "commands": self.commands,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeEntry":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            category=KnowledgeCategory(data["category"]),
            content=data["content"],
            tags=data.get("tags", []),
            platform=data.get("platform"),
            prerequisites=data.get("prerequisites", []),
            related_entries=data.get("related_entries", []),
            commands=data.get("commands", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            source=data.get("source"),
        )


@dataclass
class SearchResult:
    """Result from a knowledge search."""
    entry: KnowledgeEntry
    relevance_score: float
    matched_on: list[str]  # Which fields matched

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "entry": self.entry.to_dict(),
            "relevance_score": self.relevance_score,
            "matched_on": self.matched_on,
        }
