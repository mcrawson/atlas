"""Cost tracking for LLM API usage.

Meet Tally - ATLAS's bean counter. Watches every token, tracks every API call,
and knows exactly where your money is going. Alerts you before budgets blow
up and keeps the spending in check.

Provides:
- Real-time cost tracking per model
- Daily cost reports with WoW comparison
- Budget alerts and spending limits
- Cost breakdown by provider/model/task
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("atlas.monitoring.cost_tracker")


@dataclass
class TokenUsage:
    """Token usage for a single API call."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class CostEntry:
    """A single cost entry in the ledger."""

    timestamp: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    task_type: str = "general"
    metadata: dict = field(default_factory=dict)


class CostTracker:
    """Tally - ATLAS's bean counter.

    Tracks and reports LLM API costs across all providers:
    - Real-time cost tracking per model
    - Daily cost reports with WoW comparison
    - Budget alerts and spending limits
    - Cost breakdown by provider/model/task
    """

    NAME = "Tally"

    # Cost per 1K tokens (as of 2024)
    # Prices in USD
    COSTS_PER_1K_TOKENS = {
        # OpenAI
        "gpt-4o": {"input": 0.0025, "output": 0.01, "cached": 0.00125},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006, "cached": 0.000075},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03, "cached": 0.005},
        "gpt-4": {"input": 0.03, "output": 0.06, "cached": 0.015},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015, "cached": 0.00025},
        "o1": {"input": 0.015, "output": 0.06, "cached": 0.0075},
        "o1-mini": {"input": 0.003, "output": 0.012, "cached": 0.0015},
        # Claude (Anthropic)
        "claude-3-5-sonnet-20241022": {
            "input": 0.003,
            "output": 0.015,
            "cached": 0.0003,
        },
        "claude-3-5-haiku-20241022": {
            "input": 0.0008,
            "output": 0.004,
            "cached": 0.00008,
        },
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075, "cached": 0.0015},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015, "cached": 0.0003},
        "claude-3-haiku-20240307": {
            "input": 0.00025,
            "output": 0.00125,
            "cached": 0.000025,
        },
        # Gemini (Google)
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005, "cached": 0.000315},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003, "cached": 0.00001875},
        "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004, "cached": 0.000025},
        # Ollama (local - free)
        "ollama": {"input": 0.0, "output": 0.0, "cached": 0.0},
    }

    # Model aliases to canonical names
    MODEL_ALIASES = {
        "claude-sonnet": "claude-3-5-sonnet-20241022",
        "claude-haiku": "claude-3-5-haiku-20241022",
        "claude-opus": "claude-3-opus-20240229",
        "sonnet": "claude-3-5-sonnet-20241022",
        "haiku": "claude-3-5-haiku-20241022",
        "opus": "claude-3-opus-20240229",
        "gpt4o": "gpt-4o",
        "gpt4": "gpt-4",
        "gemini-pro": "gemini-1.5-pro",
        "gemini-flash": "gemini-1.5-flash",
    }

    def __init__(
        self,
        cost_file: Optional[Path] = None,
        daily_budget: float = 10.0,
        monthly_budget: float = 200.0,
    ):
        """Initialize cost tracker.

        Args:
            cost_file: Path to cost ledger file. Defaults to ~/.ai-workspace/.cost-ledger.jsonl
            daily_budget: Daily spending limit in USD
            monthly_budget: Monthly spending limit in USD
        """
        self.cost_file = (
            cost_file or Path.home() / "ai-workspace" / ".cost-ledger.jsonl"
        )
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Create cost file if it doesn't exist."""
        if not self.cost_file.exists():
            self.cost_file.parent.mkdir(parents=True, exist_ok=True)
            self.cost_file.write_text("")

    def _normalize_model(self, model: str) -> str:
        """Normalize model name to canonical form."""
        model_lower = model.lower()
        return self.MODEL_ALIASES.get(model_lower, model_lower)

    def _get_cost_rates(self, model: str) -> dict[str, float]:
        """Get cost rates for a model."""
        normalized = self._normalize_model(model)

        # Direct match
        if normalized in self.COSTS_PER_1K_TOKENS:
            return self.COSTS_PER_1K_TOKENS[normalized]

        # Prefix match for versioned models
        for key in self.COSTS_PER_1K_TOKENS:
            if normalized.startswith(key) or key.startswith(normalized):
                return self.COSTS_PER_1K_TOKENS[key]

        # Check if it's an Ollama model (free)
        if "ollama" in normalized or "llama" in normalized or "mistral" in normalized:
            return self.COSTS_PER_1K_TOKENS["ollama"]

        # Default to GPT-4o rates if unknown (conservative estimate)
        logger.warning(f"Unknown model '{model}', using gpt-4o rates as estimate")
        return self.COSTS_PER_1K_TOKENS["gpt-4o"]

    def calculate_cost(
        self, model: str, usage: TokenUsage
    ) -> tuple[float, float, float]:
        """Calculate cost for token usage.

        Args:
            model: Model name
            usage: Token usage

        Returns:
            Tuple of (input_cost, output_cost, total_cost)
        """
        rates = self._get_cost_rates(model)

        # Calculate costs (divide by 1000 since rates are per 1K tokens)
        input_cost = (usage.input_tokens * rates["input"]) / 1000
        output_cost = (usage.output_tokens * rates["output"]) / 1000

        # Cached tokens are typically billed at reduced rate
        cached_cost = (usage.cached_tokens * rates.get("cached", 0)) / 1000

        # Cached tokens reduce input cost
        adjusted_input = max(0, input_cost - cached_cost)

        total = adjusted_input + output_cost
        return adjusted_input, output_cost, total

    def log_usage(
        self,
        provider: str,
        model: str,
        usage: TokenUsage,
        task_type: str = "general",
        metadata: Optional[dict] = None,
    ) -> CostEntry:
        """Log a usage event with cost calculation.

        Args:
            provider: Provider name (openai, claude, gemini, ollama)
            model: Model name
            usage: Token usage
            task_type: Type of task
            metadata: Additional metadata

        Returns:
            Cost entry
        """
        input_cost, output_cost, total_cost = self.calculate_cost(model, usage)

        entry = CostEntry(
            timestamp=datetime.now().isoformat(),
            provider=provider,
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=usage.cached_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            task_type=task_type,
            metadata=metadata or {},
        )

        # Append to ledger
        with open(self.cost_file, "a") as f:
            f.write(json.dumps(entry.__dict__) + "\n")

        logger.debug(
            f"Logged cost: ${total_cost:.4f} for {model} "
            f"({usage.total_tokens} tokens)"
        )

        return entry

    def _load_entries(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> list[CostEntry]:
        """Load entries from ledger, optionally filtered by date range."""
        entries = []

        for line in self.cost_file.read_text().splitlines():
            if not line.strip():
                continue

            try:
                data = json.loads(line)
                entry_time = datetime.fromisoformat(data["timestamp"])

                if start_date and entry_time < start_date:
                    continue
                if end_date and entry_time > end_date:
                    continue

                entries.append(
                    CostEntry(
                        timestamp=data["timestamp"],
                        provider=data["provider"],
                        model=data["model"],
                        input_tokens=data["input_tokens"],
                        output_tokens=data["output_tokens"],
                        cached_tokens=data.get("cached_tokens", 0),
                        input_cost=data["input_cost"],
                        output_cost=data["output_cost"],
                        total_cost=data["total_cost"],
                        task_type=data.get("task_type", "general"),
                        metadata=data.get("metadata", {}),
                    )
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse cost entry: {e}")
                continue

        return entries

    def get_daily_cost(self, date: Optional[datetime] = None) -> float:
        """Get total cost for a specific day.

        Args:
            date: Date to check (defaults to today)

        Returns:
            Total cost in USD
        """
        if date is None:
            date = datetime.now()

        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        entries = self._load_entries(start, end)
        return sum(e.total_cost for e in entries)

    def get_weekly_cost(self) -> float:
        """Get total cost for the past 7 days."""
        end = datetime.now()
        start = end - timedelta(days=7)
        entries = self._load_entries(start, end)
        return sum(e.total_cost for e in entries)

    def get_monthly_cost(self) -> float:
        """Get total cost for the current month."""
        now = datetime.now()
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        entries = self._load_entries(start, now)
        return sum(e.total_cost for e in entries)

    def get_cost_breakdown(
        self, days: int = 7
    ) -> dict[str, dict[str, Any]]:
        """Get cost breakdown by provider and model.

        Args:
            days: Number of days to analyze

        Returns:
            Breakdown dict with costs per provider/model
        """
        end = datetime.now()
        start = end - timedelta(days=days)
        entries = self._load_entries(start, end)

        breakdown = {
            "by_provider": {},
            "by_model": {},
            "by_task": {},
            "by_day": {},
            "totals": {
                "total_cost": 0.0,
                "total_tokens": 0,
                "total_requests": 0,
            },
        }

        for entry in entries:
            # By provider
            if entry.provider not in breakdown["by_provider"]:
                breakdown["by_provider"][entry.provider] = {
                    "cost": 0.0,
                    "tokens": 0,
                    "requests": 0,
                }
            breakdown["by_provider"][entry.provider]["cost"] += entry.total_cost
            breakdown["by_provider"][entry.provider]["tokens"] += (
                entry.input_tokens + entry.output_tokens
            )
            breakdown["by_provider"][entry.provider]["requests"] += 1

            # By model
            if entry.model not in breakdown["by_model"]:
                breakdown["by_model"][entry.model] = {
                    "cost": 0.0,
                    "tokens": 0,
                    "requests": 0,
                }
            breakdown["by_model"][entry.model]["cost"] += entry.total_cost
            breakdown["by_model"][entry.model]["tokens"] += (
                entry.input_tokens + entry.output_tokens
            )
            breakdown["by_model"][entry.model]["requests"] += 1

            # By task type
            if entry.task_type not in breakdown["by_task"]:
                breakdown["by_task"][entry.task_type] = {
                    "cost": 0.0,
                    "tokens": 0,
                    "requests": 0,
                }
            breakdown["by_task"][entry.task_type]["cost"] += entry.total_cost
            breakdown["by_task"][entry.task_type]["tokens"] += (
                entry.input_tokens + entry.output_tokens
            )
            breakdown["by_task"][entry.task_type]["requests"] += 1

            # By day
            day = entry.timestamp.split("T")[0]
            if day not in breakdown["by_day"]:
                breakdown["by_day"][day] = {"cost": 0.0, "tokens": 0, "requests": 0}
            breakdown["by_day"][day]["cost"] += entry.total_cost
            breakdown["by_day"][day]["tokens"] += (
                entry.input_tokens + entry.output_tokens
            )
            breakdown["by_day"][day]["requests"] += 1

            # Totals
            breakdown["totals"]["total_cost"] += entry.total_cost
            breakdown["totals"]["total_tokens"] += (
                entry.input_tokens + entry.output_tokens
            )
            breakdown["totals"]["total_requests"] += 1

        return breakdown

    def get_budget_status(self) -> dict[str, Any]:
        """Get current budget status with alerts.

        Returns:
            Budget status dict with current spend, limits, and alerts
        """
        daily = self.get_daily_cost()
        monthly = self.get_monthly_cost()

        daily_pct = (daily / self.daily_budget * 100) if self.daily_budget > 0 else 0
        monthly_pct = (
            (monthly / self.monthly_budget * 100) if self.monthly_budget > 0 else 0
        )

        alerts = []
        if daily_pct >= 100:
            alerts.append(
                {
                    "level": "critical",
                    "message": f"Daily budget exceeded: ${daily:.2f} / ${self.daily_budget:.2f}",
                }
            )
        elif daily_pct >= 80:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"Daily budget at {daily_pct:.0f}%: ${daily:.2f} / ${self.daily_budget:.2f}",
                }
            )

        if monthly_pct >= 100:
            alerts.append(
                {
                    "level": "critical",
                    "message": f"Monthly budget exceeded: ${monthly:.2f} / ${self.monthly_budget:.2f}",
                }
            )
        elif monthly_pct >= 80:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"Monthly budget at {monthly_pct:.0f}%: ${monthly:.2f} / ${self.monthly_budget:.2f}",
                }
            )

        return {
            "daily": {
                "spent": daily,
                "budget": self.daily_budget,
                "remaining": max(0, self.daily_budget - daily),
                "percentage": daily_pct,
            },
            "monthly": {
                "spent": monthly,
                "budget": self.monthly_budget,
                "remaining": max(0, self.monthly_budget - monthly),
                "percentage": monthly_pct,
            },
            "alerts": alerts,
        }

    def generate_daily_report(self) -> dict[str, Any]:
        """Generate a daily cost report (like CREAM's daily reports).

        Returns:
            Report dict with costs, comparisons, and insights
        """
        today = self.get_daily_cost()
        yesterday = self.get_daily_cost(datetime.now() - timedelta(days=1))
        last_week_same_day = self.get_daily_cost(datetime.now() - timedelta(days=7))

        # Calculate changes
        day_change = ((today - yesterday) / yesterday * 100) if yesterday > 0 else 0
        week_change = (
            ((today - last_week_same_day) / last_week_same_day * 100)
            if last_week_same_day > 0
            else 0
        )

        breakdown = self.get_cost_breakdown(days=1)
        budget = self.get_budget_status()

        # Get top models by cost
        top_models = sorted(
            breakdown["by_model"].items(), key=lambda x: x[1]["cost"], reverse=True
        )[:5]

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": {
                "total_cost": today,
                "total_tokens": breakdown["totals"]["total_tokens"],
                "total_requests": breakdown["totals"]["total_requests"],
                "avg_cost_per_request": (
                    today / breakdown["totals"]["total_requests"]
                    if breakdown["totals"]["total_requests"] > 0
                    else 0
                ),
            },
            "comparisons": {
                "vs_yesterday": {
                    "cost": yesterday,
                    "change_pct": day_change,
                    "direction": "up" if day_change > 0 else "down",
                },
                "vs_last_week": {
                    "cost": last_week_same_day,
                    "change_pct": week_change,
                    "direction": "up" if week_change > 0 else "down",
                },
            },
            "top_models": [
                {"model": model, "cost": data["cost"], "requests": data["requests"]}
                for model, data in top_models
            ],
            "by_provider": breakdown["by_provider"],
            "budget": budget,
        }

    def format_daily_report(self) -> str:
        """Format daily report for display/notification.

        Returns:
            Formatted report string
        """
        report = self.generate_daily_report()

        lines = [
            "=" * 50,
            f"  Tally's Daily Ledger - {report['date']}",
            "=" * 50,
            "",
            f"  Total Cost:     ${report['summary']['total_cost']:.2f}",
            f"  Total Tokens:   {report['summary']['total_tokens']:,}",
            f"  Total Requests: {report['summary']['total_requests']}",
            "",
        ]

        # Comparisons
        vs_yest = report["comparisons"]["vs_yesterday"]
        vs_week = report["comparisons"]["vs_last_week"]

        arrow_yest = "+" if vs_yest["change_pct"] > 0 else ""
        arrow_week = "+" if vs_week["change_pct"] > 0 else ""

        lines.extend(
            [
                "  Comparisons:",
                f"    vs Yesterday:  {arrow_yest}{vs_yest['change_pct']:.1f}% (${vs_yest['cost']:.2f})",
                f"    vs Last Week:  {arrow_week}{vs_week['change_pct']:.1f}% (${vs_week['cost']:.2f})",
                "",
            ]
        )

        # Top models
        if report["top_models"]:
            lines.append("  Top Models:")
            for item in report["top_models"]:
                lines.append(
                    f"    {item['model'][:25]:<25} ${item['cost']:.3f} ({item['requests']} req)"
                )
            lines.append("")

        # Budget status
        budget = report["budget"]
        lines.extend(
            [
                "  Budget Status:",
                f"    Daily:   ${budget['daily']['spent']:.2f} / ${budget['daily']['budget']:.2f} ({budget['daily']['percentage']:.0f}%)",
                f"    Monthly: ${budget['monthly']['spent']:.2f} / ${budget['monthly']['budget']:.2f} ({budget['monthly']['percentage']:.0f}%)",
            ]
        )

        # Alerts
        if budget["alerts"]:
            lines.append("")
            lines.append("  Alerts:")
            for alert in budget["alerts"]:
                icon = "!" if alert["level"] == "critical" else "~"
                lines.append(f"    {icon} {alert['message']}")

        lines.append("=" * 50)

        return "\n".join(lines)


# Singleton instance for global access
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get or create the global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
