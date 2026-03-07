"""Session management for ATLAS - tracks daily sessions and generates briefings."""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional

logger = logging.getLogger("atlas.core.session")


class SessionManager:
    """Manages ATLAS sessions and generates start/end of day briefings."""

    def __init__(self, data_dir: Path):
        """Initialize session manager.

        Args:
            data_dir: Directory for storing session data
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.data_dir / "session_state.json"
        self.daily_log_dir = self.data_dir / "daily_logs"
        self.daily_log_dir.mkdir(parents=True, exist_ok=True)

        self._session_start = datetime.now()
        self._tasks_completed = []
        self._queries_made = []

    def _load_state(self) -> dict:
        """Load session state from file."""
        if self.session_file.exists():
            try:
                return json.loads(self.session_file.read_text())
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load session state: {e}")
        return {}

    def _save_state(self, state: dict):
        """Save session state to file."""
        self.session_file.write_text(json.dumps(state, indent=2, default=str))

    def is_first_session_today(self) -> bool:
        """Check if this is the first ATLAS session today.

        Returns:
            True if first session of the day
        """
        state = self._load_state()
        last_session = state.get("last_session_date")
        today = date.today().isoformat()

        # Update the last session date
        state["last_session_date"] = today
        state["last_session_time"] = datetime.now().isoformat()
        state["session_count_today"] = state.get("session_count_today", 0) + 1 if last_session == today else 1
        self._save_state(state)

        return last_session != today

    def get_session_count_today(self) -> int:
        """Get number of sessions started today."""
        state = self._load_state()
        if state.get("last_session_date") == date.today().isoformat():
            return state.get("session_count_today", 1)
        return 1

    def log_query(self, query: str, provider: str, task_type: str):
        """Log a query made during this session.

        Args:
            query: The user's query
            provider: AI provider used
            task_type: Type of task
        """
        self._queries_made.append({
            "time": datetime.now().isoformat(),
            "query": query[:100],  # Truncate long queries
            "provider": provider,
            "task_type": task_type,
        })

    def log_task_completed(self, task_description: str):
        """Log a completed task.

        Args:
            task_description: Description of completed task
        """
        self._tasks_completed.append({
            "time": datetime.now().isoformat(),
            "description": task_description,
        })

    def generate_morning_briefing(
        self,
        pending_tasks: int = 0,
        completed_overnight: int = 0,
        usage_stats: Optional[dict] = None,
    ) -> dict:
        """Generate morning briefing data.

        Args:
            pending_tasks: Number of pending background tasks
            completed_overnight: Tasks completed overnight
            usage_stats: API usage statistics

        Returns:
            Briefing dictionary
        """
        now = datetime.now()

        briefing = {
            "type": "morning",
            "date": now.strftime("%A, %B %d, %Y"),
            "time": now.strftime("%I:%M %p"),
            "greeting": self._get_morning_greeting(),
            "pending_tasks": pending_tasks,
            "completed_overnight": completed_overnight,
            "usage_stats": usage_stats or {},
            "tips": self._get_daily_tip(),
        }

        return briefing

    def generate_end_of_day_report(
        self,
        usage_stats: Optional[dict] = None,
        queue_stats: Optional[dict] = None,
    ) -> dict:
        """Generate end of day report.

        Args:
            usage_stats: API usage statistics
            queue_stats: Background queue statistics

        Returns:
            End of day report dictionary
        """
        now = datetime.now()
        session_duration = now - self._session_start

        report = {
            "type": "end_of_day",
            "date": now.strftime("%A, %B %d, %Y"),
            "time": now.strftime("%I:%M %p"),
            "session_duration_minutes": int(session_duration.total_seconds() / 60),
            "queries_made": len(self._queries_made),
            "tasks_completed": len(self._tasks_completed),
            "query_breakdown": self._get_query_breakdown(),
            "usage_stats": usage_stats or {},
            "queue_stats": queue_stats or {},
            "summary": self._generate_day_summary(),
        }

        # Save daily log
        self._save_daily_log(report)

        return report

    def _get_morning_greeting(self) -> str:
        """Get appropriate morning greeting based on day of week."""
        day = datetime.now().strftime("%A")
        greetings = {
            "Monday": "I trust you had a restful weekend. Let us begin the week productively.",
            "Tuesday": "Another fine day awaits.",
            "Wednesday": "We find ourselves at the week's midpoint.",
            "Thursday": "The week progresses well.",
            "Friday": "The week draws to a close. Let us finish strong.",
            "Saturday": "Working on Saturday? Your dedication is admirable.",
            "Sunday": "A Sunday session? I shall ensure it is time well spent.",
        }
        return greetings.get(day, "A new day awaits.")

    def _get_daily_tip(self) -> str:
        """Get a random daily productivity tip."""
        tips = [
            "Consider using /queue for research tasks that can run in the background.",
            "The /status command shows your current API usage across all providers.",
            "Complex research queries route best to Gemini for comprehensive answers.",
            "Code-related questions are optimized for OpenAI's models.",
            "Use /provider to force a specific AI when you have a preference.",
            "Background tasks complete even when ATLAS isn't actively open.",
            "Your conversation history is saved in the memory directory.",
        ]
        import random
        return random.choice(tips)

    def _get_query_breakdown(self) -> dict:
        """Get breakdown of queries by type and provider."""
        breakdown = {
            "by_type": {},
            "by_provider": {},
        }

        for query in self._queries_made:
            task_type = query.get("task_type", "unknown")
            provider = query.get("provider", "unknown")

            breakdown["by_type"][task_type] = breakdown["by_type"].get(task_type, 0) + 1
            breakdown["by_provider"][provider] = breakdown["by_provider"].get(provider, 0) + 1

        return breakdown

    def _generate_day_summary(self) -> str:
        """Generate a natural language summary of the day's activity."""
        query_count = len(self._queries_made)
        task_count = len(self._tasks_completed)

        if query_count == 0:
            return "A brief session today. No queries were made."

        breakdown = self._get_query_breakdown()
        most_used_type = max(breakdown["by_type"].items(), key=lambda x: x[1])[0] if breakdown["by_type"] else "general"

        summaries = []
        summaries.append(f"You made {query_count} {'query' if query_count == 1 else 'queries'} today")

        if most_used_type != "unknown":
            summaries.append(f"with a focus on {most_used_type} tasks")

        if task_count > 0:
            summaries.append(f"and completed {task_count} {'task' if task_count == 1 else 'tasks'}")

        return ", ".join(summaries) + "."

    def _save_daily_log(self, report: dict):
        """Save daily log to markdown file.

        Args:
            report: End of day report dictionary
        """
        today = date.today().isoformat()
        log_path = self.daily_log_dir / f"{today}.md"

        lines = [
            f"# ATLAS Daily Log - {report['date']}",
            "",
            f"**Session ended:** {report['time']}",
            f"**Duration:** {report['session_duration_minutes']} minutes",
            f"**Queries:** {report['queries_made']}",
            "",
            "## Summary",
            "",
            report['summary'],
            "",
        ]

        if report['query_breakdown']['by_type']:
            lines.extend([
                "## Activity Breakdown",
                "",
                "### By Task Type",
                "",
            ])
            for task_type, count in report['query_breakdown']['by_type'].items():
                lines.append(f"- {task_type.title()}: {count}")
            lines.append("")

        if report['query_breakdown']['by_provider']:
            lines.extend([
                "### By Provider",
                "",
            ])
            for provider, count in report['query_breakdown']['by_provider'].items():
                lines.append(f"- {provider.title()}: {count}")
            lines.append("")

        if report['usage_stats']:
            lines.extend([
                "## API Usage",
                "",
            ])
            for provider, usage in report['usage_stats'].items():
                lines.append(f"- {provider.title()}: {usage}")
            lines.append("")

        # Append to existing log or create new
        if log_path.exists():
            existing = log_path.read_text()
            lines.insert(0, existing + "\n---\n\n")

        log_path.write_text("\n".join(lines))

    def get_yesterday_summary(self) -> Optional[str]:
        """Get summary from yesterday's log if it exists.

        Returns:
            Yesterday's summary or None
        """
        from datetime import timedelta
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        log_path = self.daily_log_dir / f"{yesterday}.md"

        if log_path.exists():
            content = log_path.read_text()
            # Extract summary section
            if "## Summary" in content:
                start = content.index("## Summary") + len("## Summary")
                end = content.find("##", start) if "##" in content[start:] else len(content)
                return content[start:end].strip()

        return None

    def generate_session_start(
        self,
        pending_tasks: int = 0,
        usage_stats: Optional[dict] = None,
        system_status: Optional[dict] = None,
    ) -> dict:
        """Generate session start briefing data.

        A lighter briefing for each session (vs full morning briefing).

        Args:
            pending_tasks: Number of pending background tasks
            usage_stats: API usage statistics
            system_status: System status info

        Returns:
            Session start briefing dictionary
        """
        now = datetime.now()
        state = self._load_state()
        session_num = self.get_session_count_today()
        last_session_time = state.get("last_session_time")

        # Calculate time since last session
        time_since_last = None
        if last_session_time:
            try:
                last_dt = datetime.fromisoformat(last_session_time)
                delta = now - last_dt
                hours = int(delta.total_seconds() / 3600)
                minutes = int((delta.total_seconds() % 3600) / 60)
                if hours > 0:
                    time_since_last = f"{hours}h {minutes}m"
                else:
                    time_since_last = f"{minutes}m"
            except (ValueError, TypeError) as e:
                logger.debug(f"Could not parse last session time: {e}")

        briefing = {
            "type": "session_start",
            "date": now.strftime("%A, %B %d"),
            "time": now.strftime("%I:%M %p"),
            "session_number": session_num,
            "is_first_today": session_num == 1,
            "time_since_last": time_since_last,
            "pending_tasks": pending_tasks,
            "usage_stats": usage_stats or {},
            "system_status": system_status or {},
        }

        return briefing

    def generate_session_end(self) -> dict:
        """Generate session end summary.

        A lighter summary for ending a session (vs full end of day report).

        Returns:
            Session end summary dictionary
        """
        now = datetime.now()
        session_duration = now - self._session_start
        minutes = int(session_duration.total_seconds() / 60)

        # Get breakdown for this session
        breakdown = self._get_query_breakdown()

        # Find most used provider this session
        most_used_provider = None
        if breakdown["by_provider"]:
            most_used_provider = max(breakdown["by_provider"].items(), key=lambda x: x[1])

        summary = {
            "type": "session_end",
            "date": now.strftime("%A, %B %d"),
            "time": now.strftime("%I:%M %p"),
            "duration_minutes": minutes,
            "queries_made": len(self._queries_made),
            "tasks_completed": len(self._tasks_completed),
            "query_breakdown": breakdown,
            "most_used_provider": most_used_provider,
            "session_number": self.get_session_count_today(),
        }

        return summary

    def get_last_session_queries(self) -> list:
        """Get queries from the current session.

        Returns:
            List of query records from this session
        """
        return self._queries_made.copy()
