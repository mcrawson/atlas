"""Proactive suggestion engine for ATLAS - anticipate user needs."""

from datetime import datetime, time, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

from .patterns import PatternTracker

logger = logging.getLogger("atlas.learning.suggestions")


class SuggestionEngine:
    """Generate proactive suggestions based on learned patterns and context."""

    def __init__(
        self,
        pattern_tracker: PatternTracker = None,
        enabled: bool = True,
        confidence_threshold: float = 0.7,
        suggestion_frequency: str = "occasional",
    ):
        """Initialize suggestion engine.

        Args:
            pattern_tracker: PatternTracker for learned patterns
            enabled: Whether suggestions are enabled
            confidence_threshold: Minimum confidence for suggestions
            suggestion_frequency: How often to suggest (never, occasional, proactive)
        """
        self.patterns = pattern_tracker or PatternTracker()
        self.enabled = enabled
        self.confidence_threshold = confidence_threshold
        self.frequency = suggestion_frequency

        self._last_suggestions = {}  # Track when suggestions were made
        self._suggestion_cooldown = {
            "never": float("inf"),
            "occasional": 3600,  # 1 hour
            "proactive": 600,  # 10 minutes
        }

    def should_suggest(self, suggestion_type: str) -> bool:
        """Check if we should make a suggestion of this type.

        Args:
            suggestion_type: Type of suggestion

        Returns:
            True if should suggest
        """
        if not self.enabled or self.frequency == "never":
            return False

        cooldown = self._suggestion_cooldown.get(self.frequency, 3600)
        last_time = self._last_suggestions.get(suggestion_type)

        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < cooldown:
                return False

        return True

    def mark_suggested(self, suggestion_type: str):
        """Mark that a suggestion was made.

        Args:
            suggestion_type: Type of suggestion
        """
        self._last_suggestions[suggestion_type] = datetime.now()

    def get_time_based_suggestions(self) -> List[Dict[str, Any]]:
        """Get suggestions based on current time.

        Returns:
            List of suggestion dictionaries
        """
        if not self.should_suggest("time"):
            return []

        suggestions = []
        now = datetime.now()

        # Check time patterns
        for pattern in self.patterns.get_time_patterns():
            if pattern.matches_time(now, tolerance_minutes=15):
                if pattern.confidence >= self.confidence_threshold:
                    suggestions.append({
                        "type": "time_pattern",
                        "message": f"You usually {pattern.action} around this time, sir.",
                        "action": pattern.action,
                        "confidence": pattern.confidence,
                    })

        # Built-in time suggestions
        hour = now.hour

        # Morning suggestions
        if 6 <= hour < 9:
            if self.should_suggest("morning_briefing"):
                suggestions.append({
                    "type": "routine",
                    "message": "Good morning, sir. Would you like your morning briefing?",
                    "action": "morning_briefing",
                    "command": "/morning",
                })

        # End of day
        if 17 <= hour < 19:
            if self.should_suggest("end_of_day"):
                suggestions.append({
                    "type": "routine",
                    "message": "The day winds down, sir. Shall I prepare an end-of-day report?",
                    "action": "end_of_day",
                    "command": "/endday",
                })

        if suggestions:
            self.mark_suggested("time")

        return suggestions[:2]  # Limit to 2 time-based suggestions

    def get_context_suggestions(self, last_query: str) -> List[Dict[str, Any]]:
        """Get suggestions based on what the user just did.

        Args:
            last_query: The user's last query

        Returns:
            List of suggestion dictionaries
        """
        if not self.should_suggest("context"):
            return []

        suggestions = []

        # Check context patterns
        follow_up = self.patterns.get_follow_up_suggestion(last_query)
        if follow_up:
            suggestions.append({
                "type": "follow_up",
                "message": follow_up,
                "based_on": last_query,
            })

        # Built-in context suggestions
        last_lower = last_query.lower()

        if "commit" in last_lower and "push" not in last_lower:
            suggestions.append({
                "type": "follow_up",
                "message": "Shall I push those changes, sir?",
                "action": "git_push",
            })

        if "deploy" in last_lower or "production" in last_lower:
            suggestions.append({
                "type": "caution",
                "message": "I trust you've tested thoroughly, sir?",
                "action": "reminder",
            })

        if suggestions:
            self.mark_suggested("context")

        return suggestions[:1]  # Limit to 1 context suggestion

    def get_all_suggestions(
        self,
        last_query: str = None,
    ) -> List[Dict[str, Any]]:
        """Get all applicable suggestions.

        Args:
            last_query: The user's last query

        Returns:
            List of all relevant suggestions
        """
        suggestions = []

        # Time-based
        suggestions.extend(self.get_time_based_suggestions())

        # Context-based
        if last_query:
            suggestions.extend(self.get_context_suggestions(last_query))

        return suggestions

    def format_suggestion(self, suggestion: Dict[str, Any]) -> str:
        """Format a suggestion for display.

        Args:
            suggestion: Suggestion dictionary

        Returns:
            Formatted string
        """
        message = suggestion.get("message", "")
        command = suggestion.get("command")

        if command:
            return f"{message} (Use: {command})"
        return message

    def get_greeting_suggestion(self) -> Optional[str]:
        """Get a suggestion for the greeting.

        Returns:
            Suggestion string or None
        """
        now = datetime.now()
        suggestions = self.get_time_based_suggestions()

        if suggestions:
            return suggestions[0].get("message")

        return None


class AnticipationContext:
    """Track context for better anticipation."""

    def __init__(self):
        """Initialize context tracking."""
        self.current_project = None
        self.current_task = None
        self.session_start = datetime.now()
        self.query_count = 0
        self.last_queries = []

    def update(self, query: str, task_type: str = None, context: dict = None):
        """Update context with new query.

        Args:
            query: The query
            task_type: Type of task
            context: Additional context
        """
        self.query_count += 1
        self.last_queries.append({
            "query": query,
            "task_type": task_type,
            "time": datetime.now(),
        })

        # Keep last 10
        self.last_queries = self.last_queries[-10:]

        # Try to detect project from context
        if context and "cwd" in context:
            cwd = context["cwd"]
            # Extract project name from path
            parts = cwd.split("/")
            if "projects" in parts:
                idx = parts.index("projects")
                if idx + 1 < len(parts):
                    self.current_project = parts[idx + 1]

    def get_session_duration_minutes(self) -> int:
        """Get session duration in minutes.

        Returns:
            Minutes since session start
        """
        return int((datetime.now() - self.session_start).total_seconds() / 60)

    def get_recent_focus(self) -> Optional[str]:
        """Get the recent focus area based on queries.

        Returns:
            Most common task type recently
        """
        if not self.last_queries:
            return None

        task_types = [q.get("task_type") for q in self.last_queries if q.get("task_type")]
        if not task_types:
            return None

        # Get most common
        from collections import Counter
        counter = Counter(task_types)
        return counter.most_common(1)[0][0]
