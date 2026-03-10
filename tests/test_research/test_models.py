"""Tests for research models."""

import pytest
from datetime import datetime

from atlas.research.models import (
    ResearchCategory,
    SearchResult,
    ResearchResult,
)


class TestResearchCategory:
    """Test ResearchCategory enum."""

    def test_category_values(self):
        """Test category enum values."""
        assert ResearchCategory.BEST_PRACTICES.value == "best_practices"
        assert ResearchCategory.TECHNICAL_SPECS.value == "technical_specs"
        assert ResearchCategory.DESIGN_PATTERNS.value == "design_patterns"
        assert ResearchCategory.MARKET_RESEARCH.value == "market_research"
        assert ResearchCategory.TROUBLESHOOTING.value == "troubleshooting"
        assert ResearchCategory.GENERAL.value == "general"


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_create_result(self):
        """Test creating a search result."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="This is a test snippet",
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "This is a test snippet"
        assert result.source == ""
        assert result.relevance_score == 0.0

    def test_create_result_with_source(self):
        """Test creating a search result with source."""
        result = SearchResult(
            title="Test Title",
            url="https://docs.example.com",
            snippet="Documentation snippet",
            source="Official Docs",
            relevance_score=0.95,
        )
        assert result.source == "Official Docs"
        assert result.relevance_score == 0.95

    def test_to_markdown(self):
        """Test formatting result as markdown."""
        result = SearchResult(
            title="React Best Practices",
            url="https://react.dev/learn",
            snippet="Learn React best practices",
        )
        md = result.to_markdown()

        assert "**React Best Practices**" in md
        assert "Learn React best practices" in md
        assert "[Source](https://react.dev/learn)" in md

    def test_to_markdown_with_source(self):
        """Test markdown includes source when present."""
        result = SearchResult(
            title="Flutter Guide",
            url="https://flutter.dev",
            snippet="Official guide",
            source="Flutter Docs",
        )
        md = result.to_markdown()

        assert "(Flutter Docs)" in md


class TestResearchResult:
    """Test ResearchResult dataclass."""

    def test_create_result(self):
        """Test creating a research result."""
        result = ResearchResult(
            query="React best practices",
            category=ResearchCategory.BEST_PRACTICES,
        )
        assert result.query == "React best practices"
        assert result.category == ResearchCategory.BEST_PRACTICES
        assert result.results == []
        assert result.error is None

    def test_create_result_with_search_results(self):
        """Test creating result with search results."""
        search_results = [
            SearchResult(
                title="Result 1",
                url="https://example.com/1",
                snippet="Snippet 1",
            ),
            SearchResult(
                title="Result 2",
                url="https://example.com/2",
                snippet="Snippet 2",
            ),
        ]
        result = ResearchResult(
            query="Test query",
            category=ResearchCategory.GENERAL,
            results=search_results,
        )
        assert len(result.results) == 2

    def test_success_property_true(self):
        """Test success property when results exist."""
        result = ResearchResult(
            query="Test",
            category=ResearchCategory.GENERAL,
            results=[
                SearchResult(
                    title="Test",
                    url="https://test.com",
                    snippet="Test",
                )
            ],
        )
        assert result.success is True

    def test_success_property_false_no_results(self):
        """Test success property when no results."""
        result = ResearchResult(
            query="Test",
            category=ResearchCategory.GENERAL,
            results=[],
        )
        assert result.success is False

    def test_success_property_false_with_error(self):
        """Test success property when error exists."""
        result = ResearchResult(
            query="Test",
            category=ResearchCategory.GENERAL,
            results=[
                SearchResult(
                    title="Test",
                    url="https://test.com",
                    snippet="Test",
                )
            ],
            error="API rate limited",
        )
        assert result.success is False

    def test_to_markdown_with_results(self):
        """Test formatting result with results as markdown."""
        result = ResearchResult(
            query="React hooks",
            category=ResearchCategory.BEST_PRACTICES,
            results=[
                SearchResult(
                    title="Using Hooks",
                    url="https://react.dev/hooks",
                    snippet="Learn about hooks",
                ),
            ],
            summary="Hooks are a powerful feature in React.",
        )
        md = result.to_markdown()

        assert "### Research: React hooks" in md
        assert "Hooks are a powerful feature" in md
        assert "**Key Findings:**" in md
        assert "Using Hooks" in md

    def test_to_markdown_with_error(self):
        """Test markdown when error present."""
        result = ResearchResult(
            query="Test",
            category=ResearchCategory.GENERAL,
            error="Network error",
        )
        md = result.to_markdown()

        assert "*Research failed: Network error*" in md

    def test_to_markdown_no_results(self):
        """Test markdown when no results."""
        result = ResearchResult(
            query="obscure query",
            category=ResearchCategory.GENERAL,
            results=[],
        )
        md = result.to_markdown()

        assert "*No results found for: obscure query*" in md

    def test_to_markdown_limits_results(self):
        """Test that markdown limits number of results."""
        results = [
            SearchResult(title=f"Result {i}", url=f"https://example.com/{i}", snippet=f"Snippet {i}")
            for i in range(10)
        ]
        research = ResearchResult(
            query="Many results",
            category=ResearchCategory.GENERAL,
            results=results,
        )

        # Default max is 3
        md = research.to_markdown(max_results=3)

        assert "Result 0" in md
        assert "Result 2" in md
        assert "Result 3" not in md

    def test_timestamp_auto_set(self):
        """Test that timestamp is auto-set."""
        result = ResearchResult(
            query="Test",
            category=ResearchCategory.GENERAL,
        )
        assert isinstance(result.timestamp, datetime)
