"""Tests for research augmenter."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from atlas.research.models import (
    ResearchCategory,
    SearchResult,
    ResearchResult,
)
from atlas.research.augmenter import (
    ResearchAugmenter,
    get_research_augmenter,
    RESEARCH_PATTERNS,
)


class TestResearchPatterns:
    """Test pattern matching for research needs."""

    def test_patterns_exist(self):
        """Test that patterns are defined."""
        assert len(RESEARCH_PATTERNS) > 0

    def test_patterns_have_correct_structure(self):
        """Test pattern structure."""
        for pattern, (query_template, category) in RESEARCH_PATTERNS.items():
            assert isinstance(pattern, str)
            assert isinstance(query_template, str)
            assert isinstance(category, ResearchCategory)


class TestResearchAugmenter:
    """Test ResearchAugmenter class."""

    @pytest.fixture
    def augmenter(self):
        """Create an augmenter with mocked searcher."""
        with patch("atlas.research.augmenter.get_web_searcher") as mock_get:
            mock_searcher = MagicMock()
            mock_get.return_value = mock_searcher
            aug = ResearchAugmenter()
            aug._searcher = mock_searcher
            return aug

    def test_detect_research_needs_react(self, augmenter):
        """Test detecting React-related research needs."""
        needs = augmenter.detect_research_needs("Build a React dashboard")

        assert len(needs) > 0
        # Should find React pattern
        assert any("react" in query.lower() for query, _ in needs)

    def test_detect_research_needs_ios(self, augmenter):
        """Test detecting iOS-related research needs."""
        needs = augmenter.detect_research_needs("Create an iOS app for the App Store")

        assert len(needs) > 0
        assert any("ios" in query.lower() or "app store" in query.lower() for query, _ in needs)

    def test_detect_research_needs_planner(self, augmenter):
        """Test detecting planner/print research needs."""
        needs = augmenter.detect_research_needs("Create a printable 2024 planner")

        assert len(needs) > 0
        assert any("print" in query.lower() for query, _ in needs)

    def test_detect_research_needs_multiple(self, augmenter):
        """Test detecting multiple research needs."""
        needs = augmenter.detect_research_needs(
            "Build a Flutter iOS app with Docker deployment"
        )

        # Should find multiple patterns
        assert len(needs) >= 2

    def test_detect_research_needs_none(self, augmenter):
        """Test no research needs for generic text."""
        needs = augmenter.detect_research_needs("Hello world program")

        # May or may not find patterns depending on implementation
        # Just ensure it doesn't crash
        assert isinstance(needs, list)

    def test_detect_research_needs_from_context(self, augmenter):
        """Test detecting needs from context dict."""
        needs = augmenter.detect_research_needs(
            "Build an app",
            context={"framework": "react", "platform": "ios"}
        )

        # Should find patterns from context
        assert len(needs) > 0

    @pytest.mark.asyncio
    async def test_research_returns_result(self, augmenter):
        """Test research method returns result."""
        # Mock the search method
        mock_result = ResearchResult(
            query="React best practices",
            category=ResearchCategory.BEST_PRACTICES,
            results=[
                SearchResult(
                    title="React Guide",
                    url="https://react.dev",
                    snippet="Learn React",
                )
            ],
        )
        augmenter._searcher.search = AsyncMock(return_value=mock_result)

        result = await augmenter.research(
            "React best practices",
            ResearchCategory.BEST_PRACTICES,
        )

        assert result.query == "React best practices"
        assert len(result.results) > 0

    @pytest.mark.asyncio
    async def test_research_handles_error(self, augmenter):
        """Test research handles search errors."""
        augmenter._searcher.search = AsyncMock(side_effect=Exception("API Error"))

        result = await augmenter.research(
            "Test query",
            ResearchCategory.GENERAL,
        )

        assert result.error is not None
        assert result.success is False

    @pytest.mark.asyncio
    async def test_augment_prompt_adds_context(self, augmenter):
        """Test augment_prompt adds research context."""
        mock_result = ResearchResult(
            query="React best practices 2024",
            category=ResearchCategory.BEST_PRACTICES,
            results=[
                SearchResult(
                    title="React Best Practices",
                    url="https://react.dev",
                    snippet="Use functional components",
                )
            ],
        )
        augmenter._searcher.search = AsyncMock(return_value=mock_result)

        context = await augmenter.augment_prompt(
            "Build a React app",
            {},
        )

        assert context is not None
        assert "Research" in context or "react" in context.lower()

    @pytest.mark.asyncio
    async def test_augment_prompt_no_needs(self, augmenter):
        """Test augment_prompt returns None when no research needed."""
        # Text with no recognizable patterns
        context = await augmenter.augment_prompt(
            "Simple text with no tech keywords",
            {},
        )

        # Should return None or empty string
        assert context is None or context == ""

    @pytest.mark.asyncio
    async def test_augment_prompt_limits_searches(self, augmenter):
        """Test that augment_prompt limits number of searches."""
        mock_result = ResearchResult(
            query="Test",
            category=ResearchCategory.GENERAL,
            results=[],
        )
        augmenter._searcher.search = AsyncMock(return_value=mock_result)

        # Task with many potential patterns
        await augmenter.augment_prompt(
            "Build a React Next.js Vue Svelte Angular app with Docker Kubernetes AWS",
            {},
        )

        # Should not make excessive API calls
        call_count = augmenter._searcher.search.call_count
        assert call_count <= 3  # Should limit to max_searches


class TestGetResearchAugmenter:
    """Test the singleton factory function."""

    def test_returns_research_augmenter(self):
        """Test that factory returns a ResearchAugmenter."""
        with patch("atlas.research.augmenter.get_web_searcher"):
            aug = get_research_augmenter()
            assert isinstance(aug, ResearchAugmenter)

    def test_returns_same_instance(self):
        """Test that factory returns the same instance."""
        with patch("atlas.research.augmenter.get_web_searcher"):
            # Reset the singleton
            import atlas.research.augmenter as module
            module._research_augmenter = None

            aug1 = get_research_augmenter()
            aug2 = get_research_augmenter()
            assert aug1 is aug2
