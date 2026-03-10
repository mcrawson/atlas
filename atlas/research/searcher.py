"""Web search providers with automatic fallback."""

import os
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from .models import ResearchCategory, ResearchResult, SearchResult


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    name: str = "base"
    requires_api_key: bool = True

    @abstractmethod
    async def search(
        self,
        query: str,
        category: ResearchCategory = ResearchCategory.GENERAL,
        max_results: int = 5,
    ) -> ResearchResult:
        """Execute a search query."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        pass


class TavilyProvider(SearchProvider):
    """Tavily search provider - optimized for AI agents."""

    name = "tavily"
    requires_api_key = True

    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY", "")
        self.base_url = "https://api.tavily.com"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        category: ResearchCategory = ResearchCategory.GENERAL,
        max_results: int = 5,
    ) -> ResearchResult:
        if not self.is_available():
            return ResearchResult(
                query=query,
                category=category,
                error="Tavily API key not configured",
                provider=self.name,
            )

        # Map category to Tavily search depth
        search_depth = "advanced" if category in [
            ResearchCategory.TECHNICAL_SPECS,
            ResearchCategory.BEST_PRACTICES,
        ] else "basic"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "search_depth": search_depth,
                        "max_results": max_results,
                        "include_answer": True,
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", "")[:500],
                    source=self._extract_domain(item.get("url", "")),
                    relevance_score=item.get("score", 0.0),
                ))

            return ResearchResult(
                query=query,
                category=category,
                results=results,
                summary=data.get("answer", ""),
                provider=self.name,
            )

        except httpx.HTTPStatusError as e:
            return ResearchResult(
                query=query,
                category=category,
                error=f"Tavily API error: {e.response.status_code}",
                provider=self.name,
            )
        except Exception as e:
            return ResearchResult(
                query=query,
                category=category,
                error=f"Tavily search failed: {str(e)}",
                provider=self.name,
            )

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except Exception:
            return ""


class SerperProvider(SearchProvider):
    """Serper search provider - Google search results."""

    name = "serper"
    requires_api_key = True

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY", "")
        self.base_url = "https://google.serper.dev"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        category: ResearchCategory = ResearchCategory.GENERAL,
        max_results: int = 5,
    ) -> ResearchResult:
        if not self.is_available():
            return ResearchResult(
                query=query,
                category=category,
                error="Serper API key not configured",
                provider=self.name,
            )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers={"X-API-KEY": self.api_key},
                    json={
                        "q": query,
                        "num": max_results,
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("organic", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source=self._extract_domain(item.get("link", "")),
                    relevance_score=1.0 / (item.get("position", 10) + 1),
                ))

            # Use answer box if available
            summary = ""
            if "answerBox" in data:
                answer_box = data["answerBox"]
                summary = answer_box.get("answer", "") or answer_box.get("snippet", "")

            return ResearchResult(
                query=query,
                category=category,
                results=results,
                summary=summary,
                provider=self.name,
            )

        except httpx.HTTPStatusError as e:
            return ResearchResult(
                query=query,
                category=category,
                error=f"Serper API error: {e.response.status_code}",
                provider=self.name,
            )
        except Exception as e:
            return ResearchResult(
                query=query,
                category=category,
                error=f"Serper search failed: {str(e)}",
                provider=self.name,
            )

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except Exception:
            return ""


class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo search provider - free fallback."""

    name = "duckduckgo"
    requires_api_key = False

    def is_available(self) -> bool:
        return True  # Always available (no API key needed)

    async def search(
        self,
        query: str,
        category: ResearchCategory = ResearchCategory.GENERAL,
        max_results: int = 5,
    ) -> ResearchResult:
        try:
            # Use duckduckgo-search library
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", ""),
                        source=self._extract_domain(r.get("href", "")),
                        relevance_score=0.5,  # DDG doesn't provide scores
                    ))

            return ResearchResult(
                query=query,
                category=category,
                results=results,
                provider=self.name,
            )

        except ImportError:
            return ResearchResult(
                query=query,
                category=category,
                error="duckduckgo-search package not installed",
                provider=self.name,
            )
        except Exception as e:
            return ResearchResult(
                query=query,
                category=category,
                error=f"DuckDuckGo search failed: {str(e)}",
                provider=self.name,
            )

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except Exception:
            return ""


class WebSearcher:
    """Web searcher with automatic provider fallback."""

    def __init__(self):
        # Initialize providers in priority order
        self.providers: list[SearchProvider] = [
            TavilyProvider(),
            SerperProvider(),
            DuckDuckGoProvider(),
        ]

    def get_available_providers(self) -> list[str]:
        """Get list of available provider names."""
        return [p.name for p in self.providers if p.is_available()]

    async def search(
        self,
        query: str,
        category: ResearchCategory = ResearchCategory.GENERAL,
        max_results: int = 5,
        preferred_provider: Optional[str] = None,
    ) -> ResearchResult:
        """
        Execute a search with automatic provider fallback.

        Tries providers in order: Tavily -> Serper -> DuckDuckGo
        Returns the first successful result.
        """
        providers_to_try = self.providers.copy()

        # Move preferred provider to front if specified
        if preferred_provider:
            for i, p in enumerate(providers_to_try):
                if p.name == preferred_provider and p.is_available():
                    providers_to_try.insert(0, providers_to_try.pop(i))
                    break

        last_error = None
        for provider in providers_to_try:
            if not provider.is_available():
                continue

            result = await provider.search(query, category, max_results)

            if result.success:
                return result

            # Store error but try next provider
            last_error = result.error

        # All providers failed
        return ResearchResult(
            query=query,
            category=category,
            error=last_error or "No search providers available",
            provider="none",
        )


# Singleton instance
_searcher: Optional[WebSearcher] = None


def get_web_searcher() -> WebSearcher:
    """Get or create the global WebSearcher instance."""
    global _searcher
    if _searcher is None:
        _searcher = WebSearcher()
    return _searcher
