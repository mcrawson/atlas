"""Tests for cost tracking functionality."""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from atlas.monitoring.cost_tracker import (
    CostTracker,
    TokenUsage,
    CostEntry,
    get_cost_tracker,
)


class TestTokenUsage:
    """Test TokenUsage dataclass."""

    def test_total_tokens(self):
        """Test total_tokens property."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150

    def test_with_cached(self):
        """Test with cached tokens."""
        usage = TokenUsage(input_tokens=100, output_tokens=50, cached_tokens=20)
        assert usage.total_tokens == 150
        assert usage.cached_tokens == 20


class TestCostTracker:
    """Test CostTracker class."""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create a cost tracker with temp file."""
        cost_file = tmp_path / "test-costs.jsonl"
        return CostTracker(
            cost_file=cost_file,
            daily_budget=10.0,
            monthly_budget=200.0,
        )

    def test_initialization(self, tracker):
        """Test tracker initializes correctly."""
        assert tracker.cost_file.exists()
        assert tracker.daily_budget == 10.0
        assert tracker.monthly_budget == 200.0

    def test_normalize_model_alias(self, tracker):
        """Test model alias normalization."""
        assert tracker._normalize_model("claude-sonnet") == "claude-3-5-sonnet-20241022"
        assert tracker._normalize_model("gpt4o") == "gpt-4o"
        assert tracker._normalize_model("gemini-pro") == "gemini-1.5-pro"

    def test_normalize_model_already_normalized(self, tracker):
        """Test already normalized model names."""
        assert tracker._normalize_model("gpt-4o") == "gpt-4o"
        assert (
            tracker._normalize_model("claude-3-5-sonnet-20241022")
            == "claude-3-5-sonnet-20241022"
        )

    def test_get_cost_rates_known_model(self, tracker):
        """Test getting rates for known models."""
        rates = tracker._get_cost_rates("gpt-4o")
        assert "input" in rates
        assert "output" in rates
        assert rates["input"] == 0.0025
        assert rates["output"] == 0.01

    def test_get_cost_rates_ollama_free(self, tracker):
        """Test Ollama models are free."""
        rates = tracker._get_cost_rates("llama3")
        assert rates["input"] == 0.0
        assert rates["output"] == 0.0

    def test_calculate_cost(self, tracker):
        """Test cost calculation."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        input_cost, output_cost, total = tracker.calculate_cost("gpt-4o", usage)

        # GPT-4o: $0.0025/1K input, $0.01/1K output
        assert input_cost == pytest.approx(0.0025, rel=0.01)
        assert output_cost == pytest.approx(0.005, rel=0.01)
        assert total == pytest.approx(0.0075, rel=0.01)

    def test_calculate_cost_with_cache(self, tracker):
        """Test cost calculation with cached tokens."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500, cached_tokens=500)
        input_cost, output_cost, total = tracker.calculate_cost("gpt-4o", usage)

        # Cached tokens reduce input cost
        assert input_cost < 0.0025

    def test_log_usage(self, tracker):
        """Test logging usage."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        entry = tracker.log_usage(
            provider="openai",
            model="gpt-4o",
            usage=usage,
            task_type="code_generation",
        )

        assert isinstance(entry, CostEntry)
        assert entry.provider == "openai"
        assert entry.model == "gpt-4o"
        assert entry.input_tokens == 1000
        assert entry.output_tokens == 500
        assert entry.total_cost > 0

        # Verify written to file
        content = tracker.cost_file.read_text()
        assert "gpt-4o" in content
        assert "openai" in content

    def test_log_usage_with_metadata(self, tracker):
        """Test logging with metadata."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        entry = tracker.log_usage(
            provider="openai",
            model="gpt-4o",
            usage=usage,
            metadata={"request_id": "abc123"},
        )

        content = tracker.cost_file.read_text()
        data = json.loads(content.strip())
        assert data["metadata"]["request_id"] == "abc123"

    def test_get_daily_cost_empty(self, tracker):
        """Test daily cost with no entries."""
        cost = tracker.get_daily_cost()
        assert cost == 0.0

    def test_get_daily_cost_with_entries(self, tracker):
        """Test daily cost with entries."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)

        # Log some usage
        tracker.log_usage("openai", "gpt-4o", usage)
        tracker.log_usage("openai", "gpt-4o", usage)

        cost = tracker.get_daily_cost()
        assert cost > 0

    def test_get_cost_breakdown(self, tracker):
        """Test cost breakdown."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)

        tracker.log_usage("openai", "gpt-4o", usage, task_type="coding")
        tracker.log_usage("claude", "claude-sonnet", usage, task_type="analysis")

        breakdown = tracker.get_cost_breakdown(days=7)

        assert "by_provider" in breakdown
        assert "by_model" in breakdown
        assert "by_task" in breakdown
        assert "totals" in breakdown

        assert "openai" in breakdown["by_provider"]
        assert breakdown["totals"]["total_requests"] == 2

    def test_budget_status_under_budget(self, tracker):
        """Test budget status when under budget."""
        status = tracker.get_budget_status()

        assert status["daily"]["spent"] == 0
        assert status["daily"]["remaining"] == 10.0
        assert status["daily"]["percentage"] == 0
        assert len(status["alerts"]) == 0

    def test_budget_status_over_daily(self, tracker):
        """Test budget status when over daily budget."""
        # Log enough to exceed budget
        usage = TokenUsage(input_tokens=10000, output_tokens=10000)
        for _ in range(50):  # Log many requests
            tracker.log_usage("openai", "gpt-4", usage)

        status = tracker.get_budget_status()

        assert status["daily"]["spent"] > tracker.daily_budget
        assert any(
            a["level"] == "critical" for a in status["alerts"]
        )

    def test_generate_daily_report(self, tracker):
        """Test daily report generation."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        tracker.log_usage("openai", "gpt-4o", usage)

        report = tracker.generate_daily_report()

        assert "date" in report
        assert "summary" in report
        assert "comparisons" in report
        assert "budget" in report

        assert report["summary"]["total_cost"] > 0
        assert report["summary"]["total_requests"] == 1

    def test_format_daily_report(self, tracker):
        """Test formatted daily report."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        tracker.log_usage("openai", "gpt-4o", usage)

        report = tracker.format_daily_report()

        assert "Pennsworth" in report
        assert "Total Cost" in report
        assert "Budget Status" in report


class TestCostTrackerDateFiltering:
    """Test date filtering functionality."""

    @pytest.fixture
    def tracker_with_history(self, tmp_path):
        """Create tracker with historical data."""
        cost_file = tmp_path / "test-costs.jsonl"
        tracker = CostTracker(cost_file=cost_file)

        # Create entries for different days
        now = datetime.now()

        entries = [
            # Today
            {
                "timestamp": now.isoformat(),
                "provider": "openai",
                "model": "gpt-4o",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cached_tokens": 0,
                "input_cost": 0.0025,
                "output_cost": 0.005,
                "total_cost": 0.0075,
                "task_type": "general",
                "metadata": {},
            },
            # Yesterday
            {
                "timestamp": (now - timedelta(days=1)).isoformat(),
                "provider": "openai",
                "model": "gpt-4o",
                "input_tokens": 2000,
                "output_tokens": 1000,
                "cached_tokens": 0,
                "input_cost": 0.005,
                "output_cost": 0.01,
                "total_cost": 0.015,
                "task_type": "general",
                "metadata": {},
            },
            # Last week
            {
                "timestamp": (now - timedelta(days=7)).isoformat(),
                "provider": "claude",
                "model": "claude-sonnet",
                "input_tokens": 5000,
                "output_tokens": 2000,
                "cached_tokens": 0,
                "input_cost": 0.015,
                "output_cost": 0.03,
                "total_cost": 0.045,
                "task_type": "general",
                "metadata": {},
            },
        ]

        with open(cost_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        return tracker

    def test_get_daily_cost_today(self, tracker_with_history):
        """Test getting today's cost."""
        cost = tracker_with_history.get_daily_cost()
        assert cost == pytest.approx(0.0075, rel=0.01)

    def test_get_daily_cost_yesterday(self, tracker_with_history):
        """Test getting yesterday's cost."""
        yesterday = datetime.now() - timedelta(days=1)
        cost = tracker_with_history.get_daily_cost(yesterday)
        assert cost == pytest.approx(0.015, rel=0.01)

    def test_get_weekly_cost(self, tracker_with_history):
        """Test getting weekly cost."""
        # Includes today and yesterday
        cost = tracker_with_history.get_weekly_cost()
        assert cost >= 0.0225  # At least today + yesterday


class TestCostTrackerComparisons:
    """Test comparison calculations."""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create tracker."""
        return CostTracker(cost_file=tmp_path / "costs.jsonl")

    def test_wow_comparison_no_data(self, tracker):
        """Test WoW comparison with no previous data."""
        report = tracker.generate_daily_report()

        # Should handle zero gracefully
        assert report["comparisons"]["vs_yesterday"]["cost"] == 0
        assert report["comparisons"]["vs_last_week"]["cost"] == 0


class TestGlobalCostTracker:
    """Test global cost tracker instance."""

    def test_get_cost_tracker_singleton(self):
        """Test singleton behavior."""
        # Reset the global instance for testing
        import atlas.monitoring.cost_tracker as module

        module._cost_tracker = None

        tracker1 = get_cost_tracker()
        tracker2 = get_cost_tracker()

        assert tracker1 is tracker2


class TestCostEntry:
    """Test CostEntry dataclass."""

    def test_create_entry(self):
        """Test creating a cost entry."""
        entry = CostEntry(
            timestamp="2024-01-15T10:30:00",
            provider="openai",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=0,
            input_cost=0.0025,
            output_cost=0.005,
            total_cost=0.0075,
        )

        assert entry.provider == "openai"
        assert entry.total_cost == 0.0075

    def test_entry_with_metadata(self):
        """Test entry with metadata."""
        entry = CostEntry(
            timestamp="2024-01-15T10:30:00",
            provider="openai",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=0,
            input_cost=0.0025,
            output_cost=0.005,
            total_cost=0.0075,
            task_type="code_review",
            metadata={"pr_number": 123},
        )

        assert entry.task_type == "code_review"
        assert entry.metadata["pr_number"] == 123
