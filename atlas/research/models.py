"""Data models for research results."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ResearchCategory(Enum):
    """Categories of research queries."""

    BEST_PRACTICES = "best_practices"
    TECHNICAL_SPECS = "technical_specs"
    DESIGN_PATTERNS = "design_patterns"
    MARKET_RESEARCH = "market_research"
    TROUBLESHOOTING = "troubleshooting"
    GENERAL = "general"


@dataclass
class SearchResult:
    """A single search result from web search."""

    title: str
    url: str
    snippet: str
    source: str = ""
    relevance_score: float = 0.0

    def to_markdown(self) -> str:
        """Format as markdown for prompt inclusion."""
        source_info = f" ({self.source})" if self.source else ""
        return f"**{self.title}**{source_info}\n{self.snippet}\n[Source]({self.url})"


@dataclass
class ResearchResult:
    """Complete result from a research query."""

    query: str
    category: ResearchCategory
    results: list[SearchResult] = field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    provider: str = ""

    @property
    def success(self) -> bool:
        """Check if research was successful."""
        return self.error is None and len(self.results) > 0

    def to_markdown(self, max_results: int = 3) -> str:
        """Format as markdown for prompt inclusion."""
        if self.error:
            return f"*Research failed: {self.error}*"

        if not self.results:
            return f"*No results found for: {self.query}*"

        lines = [f"### Research: {self.query}"]

        if self.summary:
            lines.append(f"\n{self.summary}\n")

        lines.append("**Key Findings:**")
        for result in self.results[:max_results]:
            lines.append(f"\n- {result.to_markdown()}")

        return "\n".join(lines)
