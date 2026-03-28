"""Tests for the overnight configuration."""

import pytest
import tempfile
from pathlib import Path

from atlas.operator.config import (
    OvernightConfig,
    ScheduleConfig,
    LimitsConfig,
    SafetyConfig,
    AtlasConfig,
    GeneralConfig,
    LoggingConfig,
    BriefingConfig,
)


class TestOvernightConfig:
    """Test configuration loading and saving."""

    def test_default_config(self):
        """Default config has sensible values."""
        config = OvernightConfig()

        # Schedule
        assert config.schedule.start_hour == 23
        assert config.schedule.end_hour == 6

        # Limits
        assert config.limits.max_tasks == 50
        assert config.limits.max_runtime_minutes == 420
        assert config.limits.min_delay_seconds == 30.0
        assert config.limits.max_consecutive_errors == 3

        # Safety
        assert config.safety.require_tests is True
        assert "pytest" in config.safety.allowed_commands
        assert "rm -rf" in config.safety.blocked_patterns

        # Briefing
        assert config.briefing.enabled is True

    def test_save_and_load(self):
        """Config can be saved and loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "overnight.yaml"

            # Create custom config
            config = OvernightConfig()
            config.schedule.start_hour = 22
            config.limits.max_tasks = 100

            # Save
            config.save(config_path)
            assert config_path.exists()

            # Load
            loaded = OvernightConfig.load(config_path)
            assert loaded.schedule.start_hour == 22
            assert loaded.limits.max_tasks == 100

    def test_load_nonexistent_returns_default(self):
        """Loading nonexistent file returns defaults."""
        config = OvernightConfig.load(Path("/nonexistent/path.yaml"))
        assert config.schedule.start_hour == 23  # Default value


class TestScheduleConfig:
    """Test schedule configuration."""

    def test_schedule_defaults(self):
        """Schedule has correct defaults."""
        schedule = ScheduleConfig()
        assert schedule.start_hour == 23
        assert schedule.end_hour == 6
        assert schedule.timezone == "local"

    def test_schedule_custom(self):
        """Schedule accepts custom values."""
        schedule = ScheduleConfig(start_hour=22, end_hour=7, timezone="UTC")
        assert schedule.start_hour == 22
        assert schedule.end_hour == 7
        assert schedule.timezone == "UTC"


class TestLimitsConfig:
    """Test limits configuration."""

    def test_limits_defaults(self):
        """Limits have correct defaults."""
        limits = LimitsConfig()
        assert limits.max_tasks == 50
        assert limits.max_runtime_minutes == 420
        assert limits.requests_per_minute == 2.0
        assert limits.min_delay_seconds == 30.0
        assert limits.max_consecutive_errors == 3


class TestSafetyConfig:
    """Test safety configuration."""

    def test_safety_defaults(self):
        """Safety has correct defaults."""
        safety = SafetyConfig()
        assert safety.require_tests is True
        assert safety.branch_prefix == "overnight-"
        assert len(safety.allowed_commands) > 0
        assert len(safety.blocked_patterns) > 0

    def test_blocked_patterns_include_dangerous(self):
        """Blocked patterns include dangerous commands."""
        safety = SafetyConfig()
        dangerous = ["rm -rf", "sudo", "git push --force"]
        for cmd in dangerous:
            assert cmd in safety.blocked_patterns


class TestAtlasConfig:
    """Test ATLAS configuration."""

    def test_atlas_defaults(self):
        """ATLAS config has path defaults."""
        config = AtlasConfig()
        assert "atlas" in str(config.root)
        assert "atlas-projects" in str(config.projects_output)


class TestBriefingConfig:
    """Test briefing configuration."""

    def test_briefing_defaults(self):
        """Briefing config has correct defaults."""
        config = BriefingConfig()
        assert config.enabled is True
        assert "overnight-briefings" in str(config.dir)
