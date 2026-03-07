"""British butler personality for ATLAS."""

import random
from datetime import datetime
from typing import Optional


class Butler:
    """Implements the refined British butler personality for ATLAS."""

    GREETINGS = {
        "morning": [
            "Good morning, sir. How may I assist?",
            "Good morning. What shall we tackle today?",
            "Morning, sir. Ready when you are.",
        ],
        "afternoon": [
            "Good afternoon, sir. How may I assist you?",
            "Afternoon. How can I help?",
            "Good afternoon. What's on the agenda?",
        ],
        "evening": [
            "Good evening, sir. How may I assist?",
            "Evening. What can I do for you?",
            "Good evening. What are we working on?",
        ],
        "night": [
            "Burning the midnight oil, I see. How can I help?",
            "Late night session. How may I assist you?",
            "Working late, sir? Let's make it count.",
        ],
    }

    ACKNOWLEDGMENTS = [
        "Very good, sir.",
        "Certainly.",
        "On it.",
        "Right away.",
        "Understood.",
    ]

    THINKING_PHRASES = [
        "One moment...",
        "Let me look into that...",
        "Checking...",
        "Working on it...",
    ]

    COMPLETION_PHRASES = [
        "Done.",
        "Here you go.",
        "All set.",
    ]

    ERROR_PHRASES = [
        "I'm afraid we've hit a snag.",
        "Something went wrong.",
        "That didn't work as expected.",
        "An error occurred.",
    ]

    FAREWELLS = [
        "Until next time, sir.",
        "Take care.",
        "I'll be here when you need me.",
        "Farewell for now.",
    ]

    def __init__(self, name: str = "ATLAS"):
        """Initialize the butler.

        Args:
            name: The butler's name
        """
        self.name = name
        self._session_start = datetime.now()

    def _get_time_period(self) -> str:
        """Determine the current time period for appropriate greetings."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"

    def greet(self) -> str:
        """Generate an appropriate greeting based on time of day."""
        period = self._get_time_period()
        greeting = random.choice(self.GREETINGS[period])
        return f"[{self.name}] {greeting}"

    def acknowledge(self) -> str:
        """Generate an acknowledgment phrase."""
        return f"[{self.name}] {random.choice(self.ACKNOWLEDGMENTS)}"

    def thinking(self) -> str:
        """Generate a thinking/processing phrase."""
        return f"[{self.name}] {random.choice(self.THINKING_PHRASES)}"

    def complete(self, response: str, include_closing: bool = True) -> str:
        """Format a complete response with butler styling.

        Args:
            response: The main content of the response
            include_closing: Whether to include a closing phrase

        Returns:
            Formatted response with butler personality
        """
        lines = [f"[{self.name}]", "", response]
        if include_closing:
            lines.extend(["", random.choice(self.COMPLETION_PHRASES)])
        return "\n".join(lines)

    def error(self, message: str) -> str:
        """Format an error message with butler styling.

        Args:
            message: The error details

        Returns:
            Formatted error message
        """
        return f"[{self.name}] {random.choice(self.ERROR_PHRASES)}\n\n{message}"

    def farewell(self) -> str:
        """Generate a farewell message."""
        duration = datetime.now() - self._session_start
        minutes = int(duration.total_seconds() / 60)

        farewell = random.choice(self.FAREWELLS)

        if minutes > 0:
            return f"[{self.name}] {farewell}\n\nSession duration: {minutes} minutes."
        return f"[{self.name}] {farewell}"

    def format_status(self, status_dict: dict) -> str:
        """Format a status report in butler style.

        Args:
            status_dict: Dictionary of status information

        Returns:
            Formatted status report
        """
        lines = [f"[{self.name}] Your current status:", ""]

        for key, value in status_dict.items():
            formatted_key = key.replace("_", " ").title()
            lines.append(f"  {formatted_key}: {value}")

        return "\n".join(lines)

    def format_briefing(self, briefing: dict) -> str:
        """Format a session briefing.

        Args:
            briefing: Dictionary with briefing information

        Returns:
            Formatted briefing text
        """
        period = self._get_time_period()
        time_greeting = {
            "morning": "Good morning. Your briefing for today:",
            "afternoon": "Good afternoon. Here is your current status:",
            "evening": "Good evening. A summary of today's matters:",
            "night": "Good evening. Your late-night briefing:",
        }[period]

        lines = [f"[{self.name}] {time_greeting}", ""]
        lines.append("=" * 50)

        if "pending_tasks" in briefing:
            lines.append(f"\nPending Tasks: {briefing['pending_tasks']}")

        if "completed_tasks" in briefing:
            lines.append(f"Completed Today: {briefing['completed_tasks']}")

        if "usage" in briefing:
            lines.append("\nAPI Usage:")
            for provider, count in briefing["usage"].items():
                lines.append(f"  {provider.title()}: {count}")

        if "recent_decisions" in briefing and briefing["recent_decisions"]:
            lines.append("\nRecent Decisions:")
            for decision in briefing["recent_decisions"][:3]:
                lines.append(f"  - {decision}")

        lines.append("=" * 50)
        lines.append("\nHow may I assist you?")

        return "\n".join(lines)

    def format_morning_briefing(self, briefing: dict, yesterday_summary: str = None) -> str:
        """Format a morning/start-of-day briefing.

        Args:
            briefing: Morning briefing dictionary
            yesterday_summary: Optional summary from yesterday

        Returns:
            Formatted morning briefing
        """
        lines = [
            f"[{self.name}]",
            "",
            "╔" + "═" * 56 + "╗",
            "║" + "  GOOD MORNING, SIR  ".center(56) + "║",
            "╚" + "═" * 56 + "╝",
            "",
            f"  {briefing.get('date', '')}",
            f"  {briefing.get('greeting', '')}",
            "",
        ]

        # Yesterday's summary if available
        if yesterday_summary:
            lines.extend([
                "  ┌─ Yesterday ─────────────────────────────────────┐",
                f"  │ {yesterday_summary[:50]}{'...' if len(yesterday_summary) > 50 else ''}",
                "  └─────────────────────────────────────────────────┘",
                "",
            ])

        # Reminders
        reminders = briefing.get('reminders', [])
        if reminders:
            lines.append("  ┌─ Reminders ────────────────────────────────────────┐")
            for r in reminders[:3]:
                lines.append(f"  │ • {r.get('text', '')[:48]}")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        # AI News
        news = briefing.get('news', {})
        ai_news = news.get('ai_news', []) if isinstance(news, dict) else []
        if ai_news:
            lines.append("  ┌─ AI News ──────────────────────────────────────────┐")
            for h in ai_news[:5]:
                title = h.get('title', '')[:46]
                source = h.get('source', '')[:10]
                lines.append(f"  │ • {title}")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        # Tech Headlines
        tech_news = news.get('tech_news', []) if isinstance(news, dict) else news if isinstance(news, list) else []
        if tech_news:
            lines.append("  ┌─ Tech Headlines ───────────────────────────────────┐")
            for h in tech_news[:4]:
                title = h.get('title', '')[:48]
                lines.append(f"  │ • {title}")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        # Overnight activity
        overnight = briefing.get('completed_overnight', 0)
        pending = briefing.get('pending_tasks', 0)

        if overnight > 0 or pending > 0:
            lines.append("  ┌─ Background Tasks ────────────────────────────────┐")
            if overnight > 0:
                lines.append(f"  │ Completed overnight: {overnight}")
            if pending > 0:
                lines.append(f"  │ Pending in queue: {pending}")
            lines.append("  └─────────────────────────────────────────────────┘")
            lines.append("")

        # Weekly usage stats
        weekly_usage = briefing.get('weekly_usage', {})
        if weekly_usage:
            lines.append("  ┌─ Weekly API Usage ─────────────────────────────────┐")
            for provider, stats in weekly_usage.items():
                pct = stats.get('weekly_percent', 0)
                bar_len = int(pct / 5)  # 20 chars max
                bar = "█" * bar_len + "░" * (20 - bar_len)
                lines.append(f"  │ {provider.title():8} [{bar}] {pct:.0f}%")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        # System status
        system = briefing.get('system_status', {})
        if system:
            lines.append("  ┌─ System Status ────────────────────────────────────┐")
            disk = system.get('disk', {})
            if 'free_gb' in disk:
                lines.append(f"  │ Disk: {disk['free_gb']}GB free ({disk['percent_used']}% used)")
            mem = system.get('memory', {})
            if 'available_gb' in mem:
                lines.append(f"  │ Memory: {mem['available_gb']}GB available")
            if system.get('ollama_running') is not None:
                status = "running" if system['ollama_running'] else "not running"
                lines.append(f"  │ Ollama: {status}")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        # Quote of the day
        quote = briefing.get('quote', {})
        if quote:
            lines.append("  ┌─ Quote of the Day ────────────────────────────────┐")
            q_text = quote.get('quote', '')
            # Wrap quote if too long
            if len(q_text) > 50:
                lines.append(f"  │ \"{q_text[:50]}\"")
                lines.append(f"  │ \"{q_text[50:100]}\"")
            else:
                lines.append(f"  │ \"{q_text}\"")
            lines.append(f"  │                          - {quote.get('author', '')}")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        lines.append("  How may I assist you?")
        lines.append("")

        return "\n".join(lines)

    def format_end_of_day_report(self, report: dict) -> str:
        """Format an end-of-day report.

        Args:
            report: End of day report dictionary

        Returns:
            Formatted end of day report
        """
        lines = [
            f"[{self.name}]",
            "",
            "╔" + "═" * 56 + "╗",
            "║" + "  END OF DAY REPORT  ".center(56) + "║",
            "╚" + "═" * 56 + "╝",
            "",
            f"  {report.get('date', '')} - {report.get('time', '')}",
            "",
        ]

        # Session stats
        lines.extend([
            "  ┌─ Session Summary ──────────────────────────────────┐",
            f"  │ Duration: {report.get('session_duration_minutes', 0)} minutes",
            f"  │ Queries made: {report.get('queries_made', 0)}",
            f"  │ Tasks completed: {report.get('tasks_completed', 0)}",
            "  └─────────────────────────────────────────────────────┘",
            "",
        ])

        # Query breakdown
        breakdown = report.get('query_breakdown', {})
        by_type = breakdown.get('by_type', {})
        by_provider = breakdown.get('by_provider', {})

        if by_type:
            lines.append("  ┌─ Activity by Type ─────────────────────────────────┐")
            for task_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
                bar = "█" * min(count, 20)
                lines.append(f"  │ {task_type.title():12} {bar} {count}")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        if by_provider:
            lines.append("  ┌─ Providers Used ───────────────────────────────────┐")
            for provider, count in sorted(by_provider.items(), key=lambda x: -x[1]):
                bar = "█" * min(count, 20)
                lines.append(f"  │ {provider.title():12} {bar} {count}")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        # AI-generated insights
        insights = report.get('insights', '')
        if insights:
            lines.append("  ┌─ Today's Insights ─────────────────────────────────┐")
            # Wrap long insights
            for i in range(0, len(insights), 52):
                lines.append(f"  │ {insights[i:i+52]}")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        # Action items
        action_items = report.get('action_items', [])
        if action_items:
            lines.append("  ┌─ Action Items ─────────────────────────────────────┐")
            for item in action_items[:5]:
                lines.append(f"  │ □ {item[:50]}")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        # Tomorrow suggestions
        suggestions = report.get('tomorrow_suggestions', [])
        if suggestions:
            lines.append("  ┌─ Suggestions for Tomorrow ────────────────────────┐")
            for s in suggestions[:3]:
                lines.append(f"  │ → {s[:50]}")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        # Weekly trends
        trends = report.get('weekly_trends', {})
        if trends and trends.get('total_queries_this_week'):
            lines.append("  ┌─ Weekly Trends ────────────────────────────────────┐")
            lines.append(f"  │ Total queries this week: {trends['total_queries_this_week']}")
            if trends.get('most_used_provider'):
                provider, count = trends['most_used_provider']
                lines.append(f"  │ Most used: {provider.title()} ({count} queries)")
            if trends.get('busiest_day'):
                day, count = trends['busiest_day']
                lines.append(f"  │ Busiest day: {day} ({count} queries)")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        # Summary
        summary = report.get('summary', '')
        if summary:
            lines.extend([
                "  ┌─ Summary ───────────────────────────────────────────┐",
                f"  │ {summary[:52]}",
                "  └─────────────────────────────────────────────────────┘",
                "",
            ])

        # Export info
        export_path = report.get('export_path', '')
        if export_path:
            lines.append(f"  Daily notes exported to: {export_path}")
            lines.append("")

        # Farewell
        lines.extend([
            "  Rest well. I shall be here when you return.",
            "",
        ])

        return "\n".join(lines)

    def format_session_start(self, briefing: dict) -> str:
        """Format a session start briefing.

        A lighter briefing shown when starting each session.

        Args:
            briefing: Session start briefing dictionary

        Returns:
            Formatted session start briefing
        """
        period = self._get_time_period()
        session_num = briefing.get('session_number', 1)

        # Different greeting based on session number
        if briefing.get('is_first_today'):
            greeting = {
                "morning": "Good morning. Let's begin today's work.",
                "afternoon": "Good afternoon. Ready when you are.",
                "evening": "Good evening. How may I assist?",
                "night": "Working late? Let's make it count.",
            }[period]
        else:
            time_since = briefing.get('time_since_last', '')
            if time_since:
                greeting = f"Welcome back. It's been {time_since} since our last session."
            else:
                greeting = f"Welcome back. This is session #{session_num} today."

        lines = [
            f"[{self.name}]",
            "",
            "┌" + "─" * 54 + "┐",
            f"│{'  SESSION START  '.center(54)}│",
            "└" + "─" * 54 + "┘",
            "",
            f"  {briefing.get('date', '')} • {briefing.get('time', '')}",
            f"  {greeting}",
            "",
        ]

        # Quick status row
        pending = briefing.get('pending_tasks', 0)
        usage = briefing.get('usage_stats', {})
        system = briefing.get('system_status', {})

        status_items = []
        if pending > 0:
            status_items.append(f"📋 {pending} pending task{'s' if pending != 1 else ''}")

        # Show any low quotas
        for provider, stats in usage.items():
            if isinstance(stats, dict):
                used = stats.get('used', 0)
                limit = stats.get('limit', 100)
                if limit > 0 and (used / limit) > 0.8:
                    status_items.append(f"⚠️ {provider}: {used}/{limit}")

        # System alerts
        if system.get('disk_warning'):
            status_items.append(f"💾 Disk: {system.get('disk_percent', 0)}%")
        if system.get('ollama_running') is False:
            status_items.append("🔴 Ollama offline")

        if status_items:
            lines.append("  " + "  •  ".join(status_items[:3]))
            lines.append("")

        lines.append("  What shall we work on?")
        lines.append("")

        return "\n".join(lines)

    def format_session_end(self, summary: dict) -> str:
        """Format a session end summary.

        A lighter summary shown when ending each session.

        Args:
            summary: Session end summary dictionary

        Returns:
            Formatted session end summary
        """
        duration = summary.get('duration_minutes', 0)
        queries = summary.get('queries_made', 0)
        tasks = summary.get('tasks_completed', 0)

        lines = [
            f"[{self.name}]",
            "",
            "┌" + "─" * 54 + "┐",
            f"│{'  SESSION COMPLETE  '.center(54)}│",
            "└" + "─" * 54 + "┘",
            "",
            f"  {summary.get('date', '')} • {summary.get('time', '')}",
            "",
        ]

        # Session stats
        lines.append("  ┌─ This Session ─────────────────────────────────────┐")

        if duration >= 60:
            hours = duration // 60
            mins = duration % 60
            duration_str = f"{hours}h {mins}m"
        else:
            duration_str = f"{duration} minute{'s' if duration != 1 else ''}"

        lines.append(f"  │ Duration: {duration_str}")
        lines.append(f"  │ Queries: {queries}")

        if tasks > 0:
            lines.append(f"  │ Tasks completed: {tasks}")

        # Most used provider
        most_used = summary.get('most_used_provider')
        if most_used:
            provider, count = most_used
            lines.append(f"  │ Primary AI: {provider.title()} ({count} queries)")

        lines.append("  └─────────────────────────────────────────────────────┘")
        lines.append("")

        # Query breakdown if multiple types
        breakdown = summary.get('query_breakdown', {})
        by_type = breakdown.get('by_type', {})

        if len(by_type) > 1:
            lines.append("  ┌─ Activity ──────────────────────────────────────────┐")
            for task_type, count in sorted(by_type.items(), key=lambda x: -x[1])[:4]:
                bar = "█" * min(count, 15)
                lines.append(f"  │ {task_type.title():12} {bar} {count}")
            lines.append("  └─────────────────────────────────────────────────────┘")
            lines.append("")

        # Farewell based on time
        period = self._get_time_period()
        farewells = {
            "morning": "Have a productive day ahead.",
            "afternoon": "Good luck with the rest of your day.",
            "evening": "Enjoy your evening.",
            "night": "Do get some rest.",
        }

        lines.append(f"  {farewells[period]}")
        lines.append("  I shall be here when you return.")
        lines.append("")

        return "\n".join(lines)
