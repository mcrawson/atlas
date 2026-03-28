"""
Configuration for the Overnight Autonomous Operator.
"""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ScheduleConfig:
    """Time window configuration."""
    start_hour: int = 23  # 11 PM
    end_hour: int = 6     # 6 AM
    timezone: str = "local"


@dataclass
class LimitsConfig:
    """Rate limiting and task limits."""
    max_tasks: int = 50
    max_runtime_minutes: int = 420  # 7 hours
    requests_per_minute: float = 2.0
    min_delay_seconds: float = 30.0
    max_consecutive_errors: int = 3


@dataclass
class SafetyConfig:
    """Safety guardrails."""
    require_tests: bool = True
    branch_prefix: str = "overnight-"
    allowed_commands: list[str] = field(default_factory=lambda: [
        "pytest",
        "python -m pytest",
        "ruff check",
        "ruff format --check",
        "mypy",
    ])
    blocked_patterns: list[str] = field(default_factory=lambda: [
        "rm -rf",
        "sudo",
        "chmod",
        "curl",
        "wget",
        "git push --force",
        "git reset --hard",
    ])


@dataclass
class AtlasConfig:
    """ATLAS-specific configuration."""
    root: Path = field(default_factory=lambda: Path.home() / "ai-workspace" / "atlas")
    projects_output: Path = field(default_factory=lambda: Path.home() / "atlas-projects")


@dataclass
class GeneralConfig:
    """General task configuration."""
    output_dir: Path = field(default_factory=lambda: Path.home() / ".claude" / "data" / "overnight-output")


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    dir: Path = field(default_factory=lambda: Path.home() / ".claude" / "data" / "overnight-logs")


@dataclass
class BriefingConfig:
    """Morning briefing configuration."""
    enabled: bool = True
    dir: Path = field(default_factory=lambda: Path.home() / ".claude" / "data" / "overnight-briefings")


@dataclass
class EmailConfig:
    """Email notification configuration."""
    enabled: bool = False
    to: str = ""  # Recipient email address


@dataclass
class OvernightConfig:
    """Main configuration container."""
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    atlas: AtlasConfig = field(default_factory=AtlasConfig)
    general: GeneralConfig = field(default_factory=GeneralConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    briefing: BriefingConfig = field(default_factory=BriefingConfig)
    email: EmailConfig = field(default_factory=EmailConfig)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "OvernightConfig":
        """Load configuration from YAML file."""
        if path is None:
            path = Path.home() / ".claude" / "config" / "overnight.yaml"

        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls(
            schedule=ScheduleConfig(**data.get("schedule", {})),
            limits=LimitsConfig(**data.get("limits", {})),
            safety=SafetyConfig(**data.get("safety", {})),
            atlas=AtlasConfig(
                root=Path(os.path.expanduser(data.get("atlas", {}).get("root", "~/ai-workspace/atlas"))),
                projects_output=Path(os.path.expanduser(data.get("atlas", {}).get("projects_output", "~/atlas-projects"))),
            ),
            general=GeneralConfig(
                output_dir=Path(os.path.expanduser(data.get("general", {}).get("output_dir", "~/.claude/data/overnight-output"))),
            ),
            logging=LoggingConfig(
                level=data.get("logging", {}).get("level", "INFO"),
                dir=Path(os.path.expanduser(data.get("logging", {}).get("dir", "~/.claude/data/overnight-logs"))),
            ),
            briefing=BriefingConfig(
                enabled=data.get("briefing", {}).get("enabled", True),
                dir=Path(os.path.expanduser(data.get("briefing", {}).get("dir", "~/.claude/data/overnight-briefings"))),
            ),
            email=EmailConfig(
                enabled=data.get("email", {}).get("enabled", False),
                to=data.get("email", {}).get("to", ""),
            ),
        )

    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to YAML file."""
        if path is None:
            path = Path.home() / ".claude" / "config" / "overnight.yaml"

        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "schedule": {
                "start_hour": self.schedule.start_hour,
                "end_hour": self.schedule.end_hour,
                "timezone": self.schedule.timezone,
            },
            "limits": {
                "max_tasks": self.limits.max_tasks,
                "max_runtime_minutes": self.limits.max_runtime_minutes,
                "requests_per_minute": self.limits.requests_per_minute,
                "min_delay_seconds": self.limits.min_delay_seconds,
                "max_consecutive_errors": self.limits.max_consecutive_errors,
            },
            "safety": {
                "require_tests": self.safety.require_tests,
                "branch_prefix": self.safety.branch_prefix,
                "allowed_commands": self.safety.allowed_commands,
            },
            "atlas": {
                "root": str(self.atlas.root),
                "projects_output": str(self.atlas.projects_output),
            },
            "general": {
                "output_dir": str(self.general.output_dir),
            },
            "logging": {
                "level": self.logging.level,
                "dir": str(self.logging.dir),
            },
            "briefing": {
                "enabled": self.briefing.enabled,
                "dir": str(self.briefing.dir),
            },
        }

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
