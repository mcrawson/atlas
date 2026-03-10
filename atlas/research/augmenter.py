"""Research augmenter for injecting web research into agent prompts."""

import re
from typing import Optional

from .models import ResearchCategory, ResearchResult
from .searcher import WebSearcher, get_web_searcher


# Pattern matching for research needs
# Maps patterns to (search_query_template, category)
RESEARCH_PATTERNS: dict[str, tuple[str, ResearchCategory]] = {
    # Print/Planner projects
    r"\b(planner|printable|print)\b": (
        "standard print dimensions margins DPI for {context}",
        ResearchCategory.TECHNICAL_SPECS,
    ),
    r"\b(calendar|agenda|schedule)\b": (
        "calendar layout design best practices {year}",
        ResearchCategory.DESIGN_PATTERNS,
    ),
    # Mobile platforms
    r"\b(ios|iphone|ipad|app\s*store)\b": (
        "iOS App Store guidelines requirements {year}",
        ResearchCategory.TECHNICAL_SPECS,
    ),
    r"\b(android|play\s*store|google\s*play)\b": (
        "Google Play Store app requirements {year}",
        ResearchCategory.TECHNICAL_SPECS,
    ),
    r"\b(flutter)\b": (
        "Flutter best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    # Web frameworks
    r"\b(react|reactjs)\b": (
        "React best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    r"\b(next\.?js|nextjs)\b": (
        "Next.js best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    r"\b(vue|vuejs)\b": (
        "Vue.js best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    r"\b(svelte|sveltekit)\b": (
        "SvelteKit best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    # Backend
    r"\b(django)\b": (
        "Django best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    r"\b(fastapi)\b": (
        "FastAPI best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    r"\b(express|expressjs)\b": (
        "Express.js Node.js best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    # Deployment
    r"\b(docker|container)\b": (
        "Docker containerization best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    r"\b(kubernetes|k8s)\b": (
        "Kubernetes deployment best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    r"\b(aws|amazon\s*web\s*services)\b": (
        "AWS deployment best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    r"\b(vercel)\b": (
        "Vercel deployment configuration {year}",
        ResearchCategory.TECHNICAL_SPECS,
    ),
    r"\b(netlify)\b": (
        "Netlify deployment configuration {year}",
        ResearchCategory.TECHNICAL_SPECS,
    ),
    # Databases
    r"\b(postgresql|postgres)\b": (
        "PostgreSQL optimization best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    r"\b(mongodb)\b": (
        "MongoDB schema design best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    # Security
    r"\b(oauth|authentication|auth)\b": (
        "OAuth authentication best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    r"\b(jwt|json\s*web\s*token)\b": (
        "JWT security best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
    # Design
    r"\b(accessibility|a11y|wcag)\b": (
        "WCAG accessibility guidelines {year}",
        ResearchCategory.TECHNICAL_SPECS,
    ),
    r"\b(seo|search\s*engine)\b": (
        "SEO best practices {year}",
        ResearchCategory.BEST_PRACTICES,
    ),
}


class ResearchAugmenter:
    """Augments agent prompts with relevant web research."""

    def __init__(self, searcher: Optional[WebSearcher] = None):
        """Initialize with optional WebSearcher."""
        self._searcher = searcher

    @property
    def searcher(self) -> WebSearcher:
        """Lazy-load web searcher if needed."""
        if self._searcher is None:
            self._searcher = get_web_searcher()
        return self._searcher

    def detect_research_needs(
        self,
        text: str,
        context: Optional[dict] = None,
    ) -> list[tuple[str, ResearchCategory]]:
        """
        Detect what research would be helpful based on text patterns.

        Returns list of (query, category) tuples.
        """
        text_lower = text.lower()
        context = context or {}

        # Get current year for query templates
        from datetime import datetime
        current_year = datetime.now().year

        # Extract context hints for query customization
        context_hint = ""
        if "project_type" in context:
            context_hint = context["project_type"]
        elif "category" in context:
            context_hint = str(context["category"])

        detected: list[tuple[str, ResearchCategory]] = []
        matched_patterns: set[str] = set()

        for pattern, (query_template, category) in RESEARCH_PATTERNS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                # Avoid duplicate queries for similar patterns
                pattern_key = category.value + pattern[:10]
                if pattern_key in matched_patterns:
                    continue
                matched_patterns.add(pattern_key)

                # Format query with context
                query = query_template.format(
                    year=current_year,
                    context=context_hint or "general",
                )
                detected.append((query, category))

        # Limit to avoid excessive API calls
        return detected[:3]

    async def research(
        self,
        query: str,
        category: ResearchCategory = ResearchCategory.GENERAL,
        max_results: int = 3,
    ) -> ResearchResult:
        """Execute a single research query."""
        return await self.searcher.search(query, category, max_results)

    async def research_multiple(
        self,
        queries: list[tuple[str, ResearchCategory]],
        max_results_per_query: int = 2,
    ) -> list[ResearchResult]:
        """Execute multiple research queries."""
        import asyncio

        tasks = [
            self.research(query, category, max_results_per_query)
            for query, category in queries
        ]
        return await asyncio.gather(*tasks)

    def format_research_context(
        self,
        results: list[ResearchResult],
        max_results_per_query: int = 2,
        max_total_length: int = 2000,
    ) -> str:
        """Format research results as markdown for prompt inclusion."""
        if not results:
            return ""

        successful_results = [r for r in results if r.success]
        if not successful_results:
            return ""

        lines = ["## Live Research Context"]
        lines.append("*The following information was retrieved from web search:*\n")

        total_length = len("\n".join(lines))

        for result in successful_results:
            result_text = result.to_markdown(max_results=max_results_per_query)

            # Check length limit
            if total_length + len(result_text) > max_total_length:
                break

            lines.append(result_text)
            lines.append("")  # Blank line between results
            total_length += len(result_text) + 1

        if len(lines) <= 2:  # Only header added
            return ""

        return "\n".join(lines)

    async def augment_prompt(
        self,
        task: str,
        context: Optional[dict] = None,
        max_queries: int = 2,
        max_results_per_query: int = 2,
    ) -> str:
        """
        Main method for agents to call.

        Detects research needs, executes searches, and returns formatted context.
        Returns empty string if no research is needed or available.
        """
        # Check if research is available
        available_providers = self.searcher.get_available_providers()
        if not available_providers:
            return ""

        # Detect what research would help
        combined_text = task
        if context:
            # Add context values to detection
            for key, value in context.items():
                if isinstance(value, str):
                    combined_text += f" {value}"

        research_needs = self.detect_research_needs(combined_text, context)

        if not research_needs:
            return ""

        # Limit queries
        research_needs = research_needs[:max_queries]

        # Execute research
        results = await self.research_multiple(
            research_needs,
            max_results_per_query=max_results_per_query,
        )

        # Format and return
        return self.format_research_context(
            results,
            max_results_per_query=max_results_per_query,
        )


# Singleton instance
_augmenter: Optional[ResearchAugmenter] = None


def get_research_augmenter() -> ResearchAugmenter:
    """Get or create the global ResearchAugmenter instance."""
    global _augmenter
    if _augmenter is None:
        _augmenter = ResearchAugmenter()
    return _augmenter
