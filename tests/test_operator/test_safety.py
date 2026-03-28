"""Tests for the safety layer."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from pathlib import Path

from atlas.operator.safety import SafetyLayer, SafetyViolation
from atlas.operator.config import OvernightConfig, ScheduleConfig, LimitsConfig, SafetyConfig


class TestTimeWindow:
    """Test time window enforcement."""

    @pytest.fixture
    def config(self):
        """Config with 11 PM to 6 AM window."""
        config = OvernightConfig()
        config.schedule = ScheduleConfig(start_hour=23, end_hour=6)
        return config

    @pytest.fixture
    def safety(self, config):
        return SafetyLayer(config)

    def test_in_window_late_night(self, safety):
        """11 PM is in the window."""
        with patch("atlas.operator.safety.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 27, 23, 30)
            assert safety.is_in_window() is True

    def test_in_window_early_morning(self, safety):
        """3 AM is in the window."""
        with patch("atlas.operator.safety.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 27, 3, 0)
            assert safety.is_in_window() is True

    def test_out_of_window_daytime(self, safety):
        """12 PM (noon) is outside the window."""
        with patch("atlas.operator.safety.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 27, 12, 0)
            assert safety.is_in_window() is False

    def test_out_of_window_evening(self, safety):
        """8 PM is outside the window."""
        with patch("atlas.operator.safety.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 27, 20, 0)
            assert safety.is_in_window() is False

    def test_check_window_raises(self, safety):
        """check_window raises outside window."""
        with patch("atlas.operator.safety.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 27, 12, 0)
            with pytest.raises(SafetyViolation) as exc:
                safety.check_window()
            assert "Outside overnight window" in str(exc.value)


class TestRateLimiting:
    """Test rate limiting."""

    @pytest.fixture
    def config(self):
        config = OvernightConfig()
        config.limits = LimitsConfig(min_delay_seconds=1.0)
        return config

    @pytest.fixture
    def safety(self, config):
        return SafetyLayer(config)

    def test_first_request_no_wait(self, safety):
        """First request doesn't wait."""
        assert safety.check_rate_limit() is True

    @pytest.mark.asyncio
    async def test_rate_limit_waits(self, safety):
        """Subsequent requests wait."""
        await safety.wait_for_rate_limit()  # First request
        # Immediately check - should need to wait
        assert safety.check_rate_limit() is False


class TestErrorTracking:
    """Test consecutive error tracking."""

    @pytest.fixture
    def config(self):
        config = OvernightConfig()
        config.limits = LimitsConfig(max_consecutive_errors=3)
        return config

    @pytest.fixture
    def safety(self, config):
        return SafetyLayer(config)

    def test_error_count_increments(self, safety):
        """Error count increments."""
        assert safety._consecutive_errors == 0
        safety.record_error()
        assert safety._consecutive_errors == 1
        safety.record_error()
        assert safety._consecutive_errors == 2

    def test_success_resets_count(self, safety):
        """Success resets error count."""
        safety.record_error()
        safety.record_error()
        safety.record_success()
        assert safety._consecutive_errors == 0

    def test_threshold_violation(self, safety):
        """Exceeding threshold raises."""
        safety.record_error()
        safety.record_error()
        safety.record_error()
        with pytest.raises(SafetyViolation) as exc:
            safety.check_error_threshold()
        assert "max consecutive errors" in str(exc.value)


class TestTaskLimits:
    """Test task limit enforcement."""

    @pytest.fixture
    def config(self):
        config = OvernightConfig()
        config.limits = LimitsConfig(max_tasks=10)
        return config

    @pytest.fixture
    def safety(self, config):
        return SafetyLayer(config)

    def test_under_limit_ok(self, safety):
        """Under limit doesn't raise."""
        safety.check_task_limit(5)  # Should not raise

    def test_at_limit_raises(self, safety):
        """At limit raises."""
        with pytest.raises(SafetyViolation) as exc:
            safety.check_task_limit(10)
        assert "max tasks limit" in str(exc.value)


class TestCommandSafety:
    """Test command safety checks."""

    @pytest.fixture
    def config(self):
        config = OvernightConfig()
        config.safety = SafetyConfig(
            allowed_commands=["pytest", "python -m pytest", "ruff check"],
            blocked_patterns=["rm -rf", "sudo", "git push --force"],
        )
        return config

    @pytest.fixture
    def safety(self, config):
        return SafetyLayer(config)

    def test_allowed_command(self, safety):
        """Allowed commands pass."""
        assert safety.is_safe_command("pytest tests/") is True
        assert safety.is_safe_command("python -m pytest -v") is True
        assert safety.is_safe_command("ruff check atlas/") is True

    def test_blocked_command(self, safety):
        """Blocked commands fail."""
        assert safety.is_safe_command("rm -rf /") is False
        assert safety.is_safe_command("sudo apt install") is False
        assert safety.is_safe_command("git push --force") is False

    def test_safe_git_commands(self, safety):
        """Safe git read commands pass."""
        assert safety.is_safe_command("git status") is True
        assert safety.is_safe_command("git log --oneline") is True
        assert safety.is_safe_command("git diff") is True

    def test_python_execution(self, safety):
        """Python scripts allowed, but not -c."""
        assert safety.is_safe_command("python script.py") is True
        assert safety.is_safe_command("python -c 'import os'") is False


class TestPreflightCheck:
    """Test composite preflight check."""

    @pytest.fixture
    def config(self):
        config = OvernightConfig()
        config.limits = LimitsConfig(
            max_tasks=10,
            max_consecutive_errors=3,
            max_runtime_minutes=60,
        )
        return config

    @pytest.fixture
    def safety(self, config):
        s = SafetyLayer(config)
        s.start_session()
        return s

    def test_preflight_passes_normal(self, safety):
        """Normal conditions pass preflight."""
        with patch.object(safety, "is_in_window", return_value=True):
            safety.full_preflight_check(completed_tasks=5)  # Should not raise

    def test_preflight_fails_on_errors(self, safety):
        """Too many errors fails preflight."""
        safety.record_error()
        safety.record_error()
        safety.record_error()
        with pytest.raises(SafetyViolation):
            safety.full_preflight_check(completed_tasks=0, force=True)

    def test_preflight_force_skips_window(self, safety):
        """Force mode skips window check."""
        with patch.object(safety, "is_in_window", return_value=False):
            safety.full_preflight_check(completed_tasks=0, force=True)  # Should not raise
