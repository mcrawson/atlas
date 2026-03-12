"""Cost monitoring for ATLAS - budget alerts and spending notifications."""

from typing import List
import logging

from .monitor import Monitor, Alert, AlertSeverity
from .cost_tracker import get_cost_tracker

logger = logging.getLogger("atlas.monitoring.cost")


class CostMonitor(Monitor):
    """Monitor for API spending and budget alerts.

    Integrates with CostTracker to generate proactive alerts when:
    - Daily budget reaches 80% (warning)
    - Daily budget is exceeded (urgent)
    - Monthly budget reaches 80% (warning)
    - Monthly budget is exceeded (urgent)
    """

    name = "cost"
    check_interval = 300  # Check every 5 minutes

    def __init__(
        self,
        daily_budget: float = 10.0,
        monthly_budget: float = 200.0,
        warn_at_percent: float = 80.0,
        enabled: bool = True,
    ):
        """Initialize cost monitor.

        Args:
            daily_budget: Daily spending limit in USD
            monthly_budget: Monthly spending limit in USD
            warn_at_percent: Percentage at which to send warning
            enabled: Whether this monitor is active
        """
        super().__init__(enabled=enabled)
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        self.warn_at_percent = warn_at_percent

        # Track what we've already alerted on to avoid spam
        self._alerted_daily_warning = False
        self._alerted_daily_exceeded = False
        self._alerted_monthly_warning = False
        self._alerted_monthly_exceeded = False
        self._last_reset_day = None

    def _reset_daily_alerts_if_new_day(self, current_day: str) -> None:
        """Reset daily alert flags if it's a new day."""
        if self._last_reset_day != current_day:
            self._alerted_daily_warning = False
            self._alerted_daily_exceeded = False
            self._last_reset_day = current_day

    async def check(self) -> List[Alert]:
        """Check spending against budgets.

        Returns:
            List of alerts if thresholds are crossed
        """
        alerts = []
        tracker = get_cost_tracker()

        # Update tracker budgets in case they changed
        tracker.daily_budget = self.daily_budget
        tracker.monthly_budget = self.monthly_budget

        budget_status = tracker.get_budget_status()
        daily = budget_status["daily"]
        monthly = budget_status["monthly"]

        # Reset daily flags if new day
        from datetime import datetime
        current_day = datetime.now().strftime("%Y-%m-%d")
        self._reset_daily_alerts_if_new_day(current_day)

        # Daily budget checks
        if daily["percentage"] >= 100 and not self._alerted_daily_exceeded:
            alerts.append(Alert(
                monitor_name=self.name,
                severity=AlertSeverity.URGENT,
                message=f"daily API spending has exceeded the ${self.daily_budget:.2f} budget. Current spend: ${daily['spent']:.2f}.",
                action_suggestion="Consider pausing non-essential API calls or increasing the budget.",
                data={
                    "type": "daily_exceeded",
                    "spent": daily["spent"],
                    "budget": self.daily_budget,
                    "percentage": daily["percentage"],
                },
            ))
            self._alerted_daily_exceeded = True

        elif daily["percentage"] >= self.warn_at_percent and not self._alerted_daily_warning:
            alerts.append(Alert(
                monitor_name=self.name,
                severity=AlertSeverity.WARNING,
                message=f"daily API spending is at {daily['percentage']:.0f}% of the ${self.daily_budget:.2f} budget (${daily['spent']:.2f} spent).",
                action_suggestion=f"Remaining budget: ${daily['remaining']:.2f}",
                data={
                    "type": "daily_warning",
                    "spent": daily["spent"],
                    "budget": self.daily_budget,
                    "percentage": daily["percentage"],
                },
            ))
            self._alerted_daily_warning = True

        # Monthly budget checks
        if monthly["percentage"] >= 100 and not self._alerted_monthly_exceeded:
            alerts.append(Alert(
                monitor_name=self.name,
                severity=AlertSeverity.URGENT,
                message=f"monthly API spending has exceeded the ${self.monthly_budget:.2f} budget. Current spend: ${monthly['spent']:.2f}.",
                action_suggestion="This requires immediate attention. Consider increasing the monthly budget or reducing usage.",
                data={
                    "type": "monthly_exceeded",
                    "spent": monthly["spent"],
                    "budget": self.monthly_budget,
                    "percentage": monthly["percentage"],
                },
            ))
            self._alerted_monthly_exceeded = True

        elif monthly["percentage"] >= self.warn_at_percent and not self._alerted_monthly_warning:
            alerts.append(Alert(
                monitor_name=self.name,
                severity=AlertSeverity.WARNING,
                message=f"monthly API spending is at {monthly['percentage']:.0f}% of the ${self.monthly_budget:.2f} budget (${monthly['spent']:.2f} spent).",
                action_suggestion=f"Remaining budget: ${monthly['remaining']:.2f}",
                data={
                    "type": "monthly_warning",
                    "spent": monthly["spent"],
                    "budget": self.monthly_budget,
                    "percentage": monthly["percentage"],
                },
            ))
            self._alerted_monthly_warning = True

        return alerts

    def get_status(self) -> dict:
        """Get monitor status including current spend."""
        base_status = super().get_status()

        tracker = get_cost_tracker()
        budget_status = tracker.get_budget_status()

        base_status.update({
            "daily_spent": budget_status["daily"]["spent"],
            "daily_budget": self.daily_budget,
            "daily_percentage": budget_status["daily"]["percentage"],
            "monthly_spent": budget_status["monthly"]["spent"],
            "monthly_budget": self.monthly_budget,
            "monthly_percentage": budget_status["monthly"]["percentage"],
        })

        return base_status
