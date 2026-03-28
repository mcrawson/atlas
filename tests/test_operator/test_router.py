"""Tests for the task router."""

import pytest
from atlas.operator.router import TaskRouter, TaskMode, RoutingResult


class TestTaskRouter:
    """Test TaskRouter classification."""

    @pytest.fixture
    def router(self):
        return TaskRouter()

    # General task tests
    def test_research_task(self, router):
        """Research tasks route to general mode."""
        result = router.classify({"prompt": "Research best practices for API design"})
        assert result.mode == TaskMode.GENERAL
        assert result.suggested_role == "researcher"

    def test_draft_task(self, router):
        """Draft tasks route to general mode with writer role."""
        result = router.classify({"prompt": "Draft an email announcing the new feature"})
        assert result.mode == TaskMode.GENERAL
        assert result.suggested_role == "writer"

    def test_review_task(self, router):
        """Review tasks route to general mode with reviewer role."""
        result = router.classify({"prompt": "Review this document for clarity"})
        assert result.mode == TaskMode.GENERAL
        assert result.suggested_role == "reviewer"

    def test_analyze_task(self, router):
        """Analysis tasks route to general mode with analyst role."""
        result = router.classify({"prompt": "Analyze the competitor pricing data"})
        assert result.mode == TaskMode.GENERAL
        assert result.suggested_role == "analyst"

    # ATLAS fix task tests
    def test_atlas_fix_explicit(self, router):
        """Explicit atlas-fix type routes correctly."""
        result = router.classify({
            "prompt": "There's a problem with the mason module",
            "task_type": "atlas-fix",
        })
        assert result.mode == TaskMode.ATLAS_FIX
        assert result.confidence == 1.0

    def test_atlas_fix_keywords(self, router):
        """Fix keywords with ATLAS targets route to atlas-fix."""
        result = router.classify({
            "prompt": "Fix the bug in atlas mason.py where tech_stack is wrong"
        })
        assert result.mode == TaskMode.ATLAS_FIX
        assert result.confidence > 0.5

    def test_atlas_fix_broken(self, router):
        """Broken/error keywords with ATLAS targets route to atlas-fix."""
        result = router.classify({
            "prompt": "The QC agent is broken and returns errors"
        })
        assert result.mode == TaskMode.ATLAS_FIX

    # ATLAS build task tests
    def test_atlas_build_explicit(self, router):
        """Explicit atlas-build type routes correctly."""
        result = router.classify({
            "prompt": "Create something",
            "task_type": "atlas-build",
        })
        assert result.mode == TaskMode.ATLAS_BUILD
        assert result.confidence == 1.0

    def test_atlas_build_app(self, router):
        """Build app requests route to atlas-build."""
        result = router.classify({
            "prompt": "Build a recipe sharing app for home cooks"
        })
        assert result.mode == TaskMode.ATLAS_BUILD

    def test_atlas_build_website(self, router):
        """Build website requests route to atlas-build."""
        result = router.classify({
            "prompt": "Create a portfolio website for a photographer"
        })
        assert result.mode == TaskMode.ATLAS_BUILD

    def test_atlas_build_landing(self, router):
        """Build landing page requests route to atlas-build."""
        result = router.classify({
            "prompt": "Make a landing page for a SaaS product"
        })
        assert result.mode == TaskMode.ATLAS_BUILD

    # Metadata override tests
    def test_metadata_mode_override(self, router):
        """Metadata mode takes precedence."""
        result = router.classify({
            "prompt": "Research something",
            "metadata": {"mode": "atlas-build"},
        })
        assert result.mode == TaskMode.ATLAS_BUILD
        assert result.confidence == 1.0

    def test_metadata_json_string(self, router):
        """Metadata as JSON string is parsed correctly."""
        result = router.classify({
            "prompt": "Do something",
            "metadata": '{"mode": "atlas-fix"}',
        })
        assert result.mode == TaskMode.ATLAS_FIX

    # Edge cases
    def test_empty_prompt(self, router):
        """Empty prompt defaults to general."""
        result = router.classify({"prompt": ""})
        assert result.mode == TaskMode.GENERAL

    def test_none_values(self, router):
        """None values don't crash."""
        result = router.classify({
            "prompt": "Test",
            "task_type": None,
            "metadata": None,
        })
        assert result.mode == TaskMode.GENERAL

    def test_ambiguous_prompt(self, router):
        """Ambiguous prompts with low confidence."""
        result = router.classify({"prompt": "Do the thing"})
        assert result.mode == TaskMode.GENERAL
        assert result.confidence <= 0.5


class TestRoutingResult:
    """Test RoutingResult dataclass."""

    def test_routing_result_attributes(self):
        """RoutingResult has all expected attributes."""
        result = RoutingResult(
            mode=TaskMode.GENERAL,
            confidence=0.8,
            reason="keyword match",
            suggested_role="researcher",
        )
        assert result.mode == TaskMode.GENERAL
        assert result.confidence == 0.8
        assert result.reason == "keyword match"
        assert result.suggested_role == "researcher"
