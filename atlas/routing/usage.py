"""Usage tracking for LLM APIs - Python port of usage-tracker.sh."""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("atlas.routing.usage")


class UsageTracker:
    """Track and manage LLM API usage to avoid hitting limits."""

    # Default daily limits
    LIMITS = {
        "claude": 45,
        "openai": 40,
        "gemini": 100,
        "ollama": float("inf"),  # Local, no limit
    }

    # Cache TTL in seconds (refresh every 30 seconds)
    CACHE_TTL = 30

    def __init__(self, usage_file: Optional[Path] = None):
        """Initialize usage tracker.

        Args:
            usage_file: Path to usage log file. Defaults to ~/.ai-workspace/.usage-log
        """
        self.usage_file = usage_file or Path.home() / "ai-workspace" / ".usage-log"
        self.limits = self.LIMITS.copy()  # Expose limits as instance attribute
        self._cache = {}  # {provider: count}
        self._cache_date = None  # Date the cache is valid for
        self._cache_time = 0  # When cache was last refreshed
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Create usage file if it doesn't exist."""
        if not self.usage_file.exists():
            self.usage_file.parent.mkdir(parents=True, exist_ok=True)
            self.usage_file.write_text("# LLM Usage Tracker\n# Format: DATE|LLM|COUNT|NOTES\n")

    def _today(self) -> str:
        """Get today's date string."""
        return datetime.now().strftime("%Y-%m-%d")

    def _refresh_cache(self) -> None:
        """Refresh the in-memory cache from disk."""
        today = self._today()
        self._cache = {"claude": 0, "openai": 0, "gemini": 0, "ollama": 0}
        self._cache_date = today
        self._cache_time = time.time()

        for line in self.usage_file.read_text().splitlines():
            if line.startswith(today):
                parts = line.split("|")
                if len(parts) >= 3:
                    try:
                        provider = parts[1]
                        count = int(parts[2])
                        if provider in self._cache:
                            self._cache[provider] = max(self._cache[provider], count)
                    except (ValueError, IndexError):
                        continue

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache or self._cache_date != self._today():
            return False
        return (time.time() - self._cache_time) < self.CACHE_TTL

    def get_usage(self, provider: str) -> int:
        """Get today's usage count for a provider.

        Args:
            provider: Provider name (claude, openai, gemini, ollama)

        Returns:
            Current usage count
        """
        if not self._is_cache_valid():
            self._refresh_cache()
        return self._cache.get(provider, 0)

    def log_usage(self, provider: str, task_type: str = "general") -> int:
        """Log a usage event and return the new count.

        Args:
            provider: Provider name
            task_type: Type of task performed

        Returns:
            New usage count
        """
        current = self.get_usage(provider)
        new_count = current + 1

        with open(self.usage_file, "a") as f:
            f.write(f"{self._today()}|{provider}|{new_count}|{task_type}\n")

        # Update cache immediately
        if self._cache and provider in self._cache:
            self._cache[provider] = new_count

        return new_count

    def get_all_usage(self) -> dict[str, int]:
        """Get today's usage for all providers.

        Returns:
            Dictionary of provider -> count
        """
        return {
            "claude": self.get_usage("claude"),
            "openai": self.get_usage("openai"),
            "gemini": self.get_usage("gemini"),
            "ollama": self.get_usage("ollama"),
        }

    def get_remaining(self, provider: str) -> float:
        """Get remaining requests for a provider today.

        Args:
            provider: Provider name

        Returns:
            Remaining count (infinity for unlimited providers)
        """
        limit = self.LIMITS.get(provider, 0)
        if limit == float("inf"):
            return float("inf")
        return max(0, limit - self.get_usage(provider))

    def is_available(self, provider: str) -> bool:
        """Check if a provider has remaining capacity.

        Args:
            provider: Provider name

        Returns:
            True if provider can be used
        """
        return self.get_remaining(provider) > 0

    def get_status_indicator(self, provider: str) -> str:
        """Get a status indicator for a provider.

        Args:
            provider: Provider name

        Returns:
            Status emoji (🟢 good, 🟡 warning, 🔴 exhausted)
        """
        limit = self.LIMITS.get(provider, 0)
        if limit == float("inf"):
            return "🟢"

        usage = self.get_usage(provider)
        ratio = usage / limit

        if ratio < 0.6:
            return "🟢"
        elif ratio < 0.9:
            return "🟡"
        else:
            return "🔴"

    def format_status(self) -> str:
        """Get formatted status report.

        Returns:
            Multi-line status string
        """
        lines = [
            "═" * 45,
            f"  LLM Usage Status - {self._today()}",
            "═" * 45,
        ]

        for provider in ["claude", "openai", "gemini", "ollama"]:
            usage = self.get_usage(provider)
            limit = self.LIMITS.get(provider, 0)
            indicator = self.get_status_indicator(provider)

            if limit == float("inf"):
                lines.append(f"  {provider.title():8} {usage:3} / ∞    {indicator}")
            else:
                lines.append(f"  {provider.title():8} {usage:3} / {limit:<3}  {indicator}")

        lines.append("═" * 45)

        # Add warnings
        warnings = []
        for provider in ["claude", "openai", "gemini"]:
            if not self.is_available(provider):
                warnings.append(f"⚠️  {provider.upper()} LIMIT REACHED")
            elif self.get_status_indicator(provider) == "🟡":
                warnings.append(f"💡 {provider.title()} approaching limit")

        if warnings:
            lines.append("")
            lines.extend(warnings)

        return "\n".join(lines)

    def get_weekly_usage(self, provider: str) -> int:
        """Get usage count for a provider over the last 7 days.

        Args:
            provider: Provider name

        Returns:
            Total usage count for the week
        """
        total = 0
        today = datetime.now().date()

        for line in self.usage_file.read_text().splitlines():
            if f"|{provider}|" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    try:
                        line_date = datetime.strptime(parts[0], "%Y-%m-%d").date()
                        if (today - line_date).days < 7:
                            # Get the max count for each day
                            count = int(parts[2])
                            total = max(total, count)
                    except (ValueError, IndexError):
                        continue

        return total

    def get_weekly_breakdown(self) -> dict:
        """Get daily breakdown of usage for the past 7 days.

        Returns:
            Dict of date -> provider -> count
        """
        breakdown = {}
        today = datetime.now().date()

        # Initialize all days
        for i in range(7):
            day = (today - timedelta(days=i)).isoformat()
            breakdown[day] = {}

        # Parse usage file
        daily_max = {}  # Track max count per day per provider

        for line in self.usage_file.read_text().splitlines():
            if line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) >= 3:
                try:
                    line_date = parts[0]
                    provider = parts[1]
                    count = int(parts[2])

                    if line_date in breakdown:
                        key = f"{line_date}|{provider}"
                        if key not in daily_max or count > daily_max[key]:
                            daily_max[key] = count
                            breakdown[line_date][provider] = count
                except (ValueError, IndexError):
                    continue

        return breakdown

    def get_usage_for_date(self, provider: str, date_str: str) -> int:
        """Get usage count for a specific date.

        Args:
            provider: Provider name
            date_str: Date in YYYY-MM-DD format

        Returns:
            Usage count for that date
        """
        max_count = 0

        for line in self.usage_file.read_text().splitlines():
            if line.startswith(f"{date_str}|{provider}|"):
                parts = line.split("|")
                if len(parts) >= 3:
                    try:
                        count = int(parts[2])
                        max_count = max(max_count, count)
                    except ValueError:
                        continue

        return max_count
