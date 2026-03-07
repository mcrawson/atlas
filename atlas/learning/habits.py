"""Habit tracking for ATLAS - learn and support user routines."""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("atlas.learning.habits")


@dataclass
class Habit:
    """A detected user habit."""
    name: str
    description: str
    schedule_type: str  # daily, weekday, weekly
    trigger_time: Optional[time] = None
    trigger_day: Optional[int] = None  # Day of week (0=Monday)
    streak: int = 0
    last_performed: Optional[date] = None
    total_occurrences: int = 0
    missed_days: int = 0
    enabled: bool = True


class HabitTracker:
    """Track user habits and routines."""

    def __init__(self, data_dir: Path = None):
        """Initialize habit tracker.

        Args:
            data_dir: Directory for habit storage
        """
        self.data_dir = data_dir or Path.home() / ".config" / "atlas"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.habits_file = self.data_dir / "habits.json"

        self._habits: Dict[str, Habit] = {}
        self._activity_log: List[Dict[str, Any]] = []
        self._load_habits()

    def _load_habits(self):
        """Load habits from file."""
        if not self.habits_file.exists():
            # Initialize with default habits
            self._init_default_habits()
            return

        try:
            data = json.loads(self.habits_file.read_text())

            for name, habit_data in data.get("habits", {}).items():
                if "trigger_time" in habit_data and habit_data["trigger_time"]:
                    h, m = map(int, habit_data["trigger_time"].split(":"))
                    habit_data["trigger_time"] = time(h, m)
                if "last_performed" in habit_data and habit_data["last_performed"]:
                    habit_data["last_performed"] = date.fromisoformat(habit_data["last_performed"])
                self._habits[name] = Habit(**habit_data)

            self._activity_log = data.get("activity_log", [])[-500:]

        except Exception as e:
            logger.error(f"Failed to load habits: {e}")
            self._init_default_habits()

    def _init_default_habits(self):
        """Initialize default trackable habits."""
        self._habits = {
            "morning_briefing": Habit(
                name="morning_briefing",
                description="Check morning briefing",
                schedule_type="weekday",
                trigger_time=time(9, 0),
            ),
            "email_check": Habit(
                name="email_check",
                description="Check emails",
                schedule_type="daily",
                trigger_time=time(9, 30),
            ),
            "end_of_day": Habit(
                name="end_of_day",
                description="End of day report",
                schedule_type="weekday",
                trigger_time=time(17, 30),
            ),
        }

    def _save_habits(self):
        """Save habits to file."""
        try:
            habits_data = {}
            for name, habit in self._habits.items():
                h = {
                    "name": habit.name,
                    "description": habit.description,
                    "schedule_type": habit.schedule_type,
                    "trigger_time": habit.trigger_time.strftime("%H:%M") if habit.trigger_time else None,
                    "trigger_day": habit.trigger_day,
                    "streak": habit.streak,
                    "last_performed": habit.last_performed.isoformat() if habit.last_performed else None,
                    "total_occurrences": habit.total_occurrences,
                    "missed_days": habit.missed_days,
                    "enabled": habit.enabled,
                }
                habits_data[name] = h

            data = {
                "habits": habits_data,
                "activity_log": self._activity_log[-500:],
            }

            self.habits_file.write_text(json.dumps(data, indent=2))

        except Exception as e:
            logger.error(f"Failed to save habits: {e}")

    def log_activity(self, activity_type: str, details: str = ""):
        """Log an activity that may relate to a habit.

        Args:
            activity_type: Type of activity (e.g., "morning_briefing")
            details: Optional details
        """
        now = datetime.now()

        # Log the activity
        self._activity_log.append({
            "type": activity_type,
            "details": details,
            "timestamp": now.isoformat(),
        })

        # Check if this matches a habit
        if activity_type in self._habits:
            habit = self._habits[activity_type]
            today = date.today()

            # Update streak
            if habit.last_performed:
                days_since = (today - habit.last_performed).days
                if days_since == 1:
                    habit.streak += 1
                elif days_since > 1:
                    habit.streak = 1
                    habit.missed_days += days_since - 1
            else:
                habit.streak = 1

            habit.last_performed = today
            habit.total_occurrences += 1

            self._save_habits()
            logger.info(f"Habit '{activity_type}' performed. Streak: {habit.streak}")

    def get_due_habits(self) -> List[Habit]:
        """Get habits that are due now.

        Returns:
            List of due habits
        """
        now = datetime.now()
        today = date.today()
        current_time = now.time()
        due = []

        for habit in self._habits.values():
            if not habit.enabled:
                continue

            # Check if already done today
            if habit.last_performed == today:
                continue

            # Check schedule type
            if habit.schedule_type == "weekday" and today.weekday() >= 5:
                continue

            if habit.schedule_type == "weekly":
                if habit.trigger_day is not None and today.weekday() != habit.trigger_day:
                    continue

            # Check if it's time
            if habit.trigger_time:
                # Within 30 minutes of trigger time
                trigger_mins = habit.trigger_time.hour * 60 + habit.trigger_time.minute
                current_mins = current_time.hour * 60 + current_time.minute

                if -15 <= (current_mins - trigger_mins) <= 60:
                    due.append(habit)

        return due

    def get_habit_summary(self) -> Dict[str, Any]:
        """Get summary of habit status.

        Returns:
            Summary dictionary
        """
        today = date.today()
        summary = {
            "total_habits": len([h for h in self._habits.values() if h.enabled]),
            "completed_today": 0,
            "pending_today": 0,
            "habits": [],
        }

        for habit in self._habits.values():
            if not habit.enabled:
                continue

            completed = habit.last_performed == today
            if completed:
                summary["completed_today"] += 1
            else:
                summary["pending_today"] += 1

            summary["habits"].append({
                "name": habit.name,
                "description": habit.description,
                "completed_today": completed,
                "streak": habit.streak,
                "trigger_time": habit.trigger_time.strftime("%H:%M") if habit.trigger_time else None,
            })

        return summary

    def get_streak_celebration(self) -> Optional[str]:
        """Get a celebration message for notable streaks.

        Returns:
            Celebration message or None
        """
        for habit in self._habits.values():
            if habit.streak in [7, 14, 21, 30, 60, 90, 100, 365]:
                return f"Congratulations, sir! You've maintained your {habit.description} habit for {habit.streak} days!"
        return None

    def add_habit(
        self,
        name: str,
        description: str,
        schedule_type: str = "daily",
        trigger_time: time = None,
        trigger_day: int = None,
    ) -> Habit:
        """Add a new habit to track.

        Args:
            name: Habit identifier
            description: Human-readable description
            schedule_type: daily, weekday, or weekly
            trigger_time: Time to trigger reminder
            trigger_day: Day of week for weekly habits

        Returns:
            Created Habit
        """
        habit = Habit(
            name=name,
            description=description,
            schedule_type=schedule_type,
            trigger_time=trigger_time,
            trigger_day=trigger_day,
        )

        self._habits[name] = habit
        self._save_habits()
        return habit

    def remove_habit(self, name: str) -> bool:
        """Remove a habit.

        Args:
            name: Habit to remove

        Returns:
            True if removed
        """
        if name in self._habits:
            del self._habits[name]
            self._save_habits()
            return True
        return False

    def get_productivity_insights(self) -> Dict[str, Any]:
        """Get insights about productivity patterns.

        Returns:
            Insights dictionary
        """
        insights = {
            "most_consistent_habit": None,
            "longest_streak": 0,
            "total_activities_this_week": 0,
            "busiest_hour": None,
        }

        # Find most consistent habit
        max_streak = 0
        for habit in self._habits.values():
            if habit.streak > max_streak:
                max_streak = habit.streak
                insights["most_consistent_habit"] = habit.name
                insights["longest_streak"] = habit.streak

        # Count activities this week
        week_ago = datetime.now() - timedelta(days=7)
        week_activities = [
            a for a in self._activity_log
            if datetime.fromisoformat(a["timestamp"]) > week_ago
        ]
        insights["total_activities_this_week"] = len(week_activities)

        # Find busiest hour
        hour_counts = defaultdict(int)
        for activity in week_activities:
            hour = datetime.fromisoformat(activity["timestamp"]).hour
            hour_counts[hour] += 1

        if hour_counts:
            busiest = max(hour_counts.items(), key=lambda x: x[1])
            insights["busiest_hour"] = f"{busiest[0]:02d}:00"

        return insights
