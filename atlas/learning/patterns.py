"""Pattern detection for ATLAS - learn from user behavior."""

import json
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("atlas.learning.patterns")


@dataclass
class TimePattern:
    """A time-based pattern in user behavior."""
    trigger_hour: int
    trigger_minute: int = 0
    action: str = ""
    description: str = ""
    occurrences: int = 0
    confidence: float = 0.0
    last_seen: datetime = field(default_factory=datetime.now)

    def matches_time(self, dt: datetime, tolerance_minutes: int = 15) -> bool:
        """Check if a datetime matches this pattern.

        Args:
            dt: Datetime to check
            tolerance_minutes: Minutes of tolerance

        Returns:
            True if matches
        """
        target = time(self.trigger_hour, self.trigger_minute)
        actual = dt.time()

        # Calculate minute difference
        target_mins = self.trigger_hour * 60 + self.trigger_minute
        actual_mins = actual.hour * 60 + actual.minute

        diff = abs(target_mins - actual_mins)
        # Handle midnight wrap
        if diff > 720:  # More than 12 hours
            diff = 1440 - diff

        return diff <= tolerance_minutes


@dataclass
class ContextPattern:
    """A context-based pattern in user behavior."""
    trigger: str  # What triggers this pattern (e.g., "git push")
    follow_up: str  # What typically follows (e.g., "run tests")
    occurrences: int = 0
    confidence: float = 0.0
    last_seen: datetime = field(default_factory=datetime.now)


class PatternTracker:
    """Track and learn patterns in user behavior."""

    MIN_OCCURRENCES = 3
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, data_dir: Path = None):
        """Initialize pattern tracker.

        Args:
            data_dir: Directory for pattern storage
        """
        self.data_dir = data_dir or Path.home() / ".config" / "atlas"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_file = self.data_dir / "patterns.json"

        self._time_patterns: Dict[str, TimePattern] = {}
        self._context_patterns: Dict[str, ContextPattern] = {}
        self._query_history: List[Dict[str, Any]] = []
        self._max_history = 1000

        self._load_patterns()

    def _load_patterns(self):
        """Load patterns from file."""
        if not self.patterns_file.exists():
            return

        try:
            data = json.loads(self.patterns_file.read_text())

            for key, pattern_data in data.get("time_patterns", {}).items():
                if "last_seen" in pattern_data:
                    pattern_data["last_seen"] = datetime.fromisoformat(pattern_data["last_seen"])
                self._time_patterns[key] = TimePattern(**pattern_data)

            for key, pattern_data in data.get("context_patterns", {}).items():
                if "last_seen" in pattern_data:
                    pattern_data["last_seen"] = datetime.fromisoformat(pattern_data["last_seen"])
                self._context_patterns[key] = ContextPattern(**pattern_data)

            self._query_history = data.get("query_history", [])

        except Exception as e:
            logger.error(f"Failed to load patterns: {e}")

    def _save_patterns(self):
        """Save patterns to file."""
        try:
            time_patterns = {}
            for key, pattern in self._time_patterns.items():
                p = asdict(pattern)
                p["last_seen"] = p["last_seen"].isoformat()
                time_patterns[key] = p

            context_patterns = {}
            for key, pattern in self._context_patterns.items():
                p = asdict(pattern)
                p["last_seen"] = p["last_seen"].isoformat()
                context_patterns[key] = p

            data = {
                "time_patterns": time_patterns,
                "context_patterns": context_patterns,
                "query_history": self._query_history[-500:],  # Keep last 500
            }

            self.patterns_file.write_text(json.dumps(data, indent=2))

        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")

    def track_query(
        self,
        query: str,
        task_type: str = "general",
        context: Dict[str, Any] = None,
    ):
        """Track a user query for pattern learning.

        Args:
            query: The user's query
            task_type: Type of task
            context: Additional context (e.g., current directory)
        """
        now = datetime.now()

        # Store in history
        entry = {
            "query": query,
            "task_type": task_type,
            "timestamp": now.isoformat(),
            "hour": now.hour,
            "minute": now.minute,
            "day_of_week": now.weekday(),
            "context": context or {},
        }

        self._query_history.append(entry)
        if len(self._query_history) > self._max_history:
            self._query_history.pop(0)

        # Analyze for time patterns
        self._analyze_time_pattern(entry)

        # Analyze for context patterns (using previous query)
        if len(self._query_history) >= 2:
            previous = self._query_history[-2]
            self._analyze_context_pattern(previous, entry)

        # Save periodically (every 10 queries)
        if len(self._query_history) % 10 == 0:
            self._save_patterns()

    def _analyze_time_pattern(self, entry: Dict[str, Any]):
        """Analyze a query for time-based patterns.

        Args:
            entry: Query history entry
        """
        # Create a key based on hour and task type
        hour = entry["hour"]
        task_type = entry["task_type"]
        key = f"{hour:02d}:{task_type}"

        if key not in self._time_patterns:
            self._time_patterns[key] = TimePattern(
                trigger_hour=hour,
                action=task_type,
                description=f"{task_type} queries around {hour:02d}:00",
            )

        pattern = self._time_patterns[key]
        pattern.occurrences += 1
        pattern.last_seen = datetime.now()

        # Calculate confidence based on frequency
        # Count how many queries were at this hour out of total
        same_hour_count = sum(
            1 for h in self._query_history
            if h["hour"] == hour
        )
        total_queries = len(self._query_history)

        if total_queries > 0:
            pattern.confidence = min(0.95, same_hour_count / total_queries * 3)

    def _analyze_context_pattern(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any],
    ):
        """Analyze for context-based patterns.

        Args:
            previous: Previous query entry
            current: Current query entry
        """
        # Check if queries are close in time (within 5 minutes)
        prev_time = datetime.fromisoformat(previous["timestamp"])
        curr_time = datetime.fromisoformat(current["timestamp"])

        if (curr_time - prev_time).total_seconds() > 300:
            return  # Too far apart

        # Create pattern key
        trigger = self._extract_action(previous["query"])
        follow_up = self._extract_action(current["query"])

        if not trigger or not follow_up:
            return

        key = f"{trigger}->{follow_up}"

        if key not in self._context_patterns:
            self._context_patterns[key] = ContextPattern(
                trigger=trigger,
                follow_up=follow_up,
            )

        pattern = self._context_patterns[key]
        pattern.occurrences += 1
        pattern.last_seen = datetime.now()

        # Calculate confidence
        # Count how often this follow_up occurs after this trigger
        trigger_count = 0
        sequence_count = 0

        for i in range(len(self._query_history) - 1):
            prev_action = self._extract_action(self._query_history[i]["query"])
            if prev_action == trigger:
                trigger_count += 1
                next_action = self._extract_action(self._query_history[i + 1]["query"])
                if next_action == follow_up:
                    sequence_count += 1

        if trigger_count > 0:
            pattern.confidence = min(0.95, sequence_count / trigger_count)

    def _extract_action(self, query: str) -> Optional[str]:
        """Extract a meaningful action from a query.

        Args:
            query: User query

        Returns:
            Action keyword or None
        """
        query = query.lower()

        # Common action keywords
        actions = [
            "git push", "git commit", "git pull",
            "run tests", "test", "debug",
            "deploy", "build", "compile",
            "research", "search", "find",
            "review", "check",
            "email", "calendar",
            "status", "morning", "endday",
        ]

        for action in actions:
            if action in query:
                return action

        return None

    def get_time_patterns(self) -> List[TimePattern]:
        """Get detected time-based patterns.

        Returns:
            List of time patterns above confidence threshold
        """
        return [
            p for p in self._time_patterns.values()
            if p.occurrences >= self.MIN_OCCURRENCES
            and p.confidence >= self.CONFIDENCE_THRESHOLD
        ]

    def get_context_patterns(self) -> List[ContextPattern]:
        """Get detected context-based patterns.

        Returns:
            List of context patterns above confidence threshold
        """
        return [
            p for p in self._context_patterns.values()
            if p.occurrences >= self.MIN_OCCURRENCES
            and p.confidence >= self.CONFIDENCE_THRESHOLD
        ]

    def get_current_suggestions(self) -> List[str]:
        """Get suggestions based on current time and context.

        Returns:
            List of suggestion strings
        """
        now = datetime.now()
        suggestions = []

        # Check time patterns
        for pattern in self.get_time_patterns():
            if pattern.matches_time(now, tolerance_minutes=30):
                suggestions.append(
                    f"You usually {pattern.action} around this time"
                )

        return suggestions

    def get_follow_up_suggestion(self, previous_query: str) -> Optional[str]:
        """Get suggestion based on what typically follows a query.

        Args:
            previous_query: The query just completed

        Returns:
            Suggestion string or None
        """
        action = self._extract_action(previous_query)
        if not action:
            return None

        for pattern in self.get_context_patterns():
            if pattern.trigger == action:
                return f"Shall I {pattern.follow_up}, sir?"

        return None

    def get_all_patterns(self) -> Dict[str, Any]:
        """Get all patterns for display.

        Returns:
            Dictionary with all patterns
        """
        return {
            "time_patterns": [
                {
                    "time": f"{p.trigger_hour:02d}:{p.trigger_minute:02d}",
                    "action": p.action,
                    "occurrences": p.occurrences,
                    "confidence": f"{p.confidence:.0%}",
                }
                for p in self.get_time_patterns()
            ],
            "context_patterns": [
                {
                    "trigger": p.trigger,
                    "follow_up": p.follow_up,
                    "occurrences": p.occurrences,
                    "confidence": f"{p.confidence:.0%}",
                }
                for p in self.get_context_patterns()
            ],
        }

    def clear_patterns(self):
        """Clear all learned patterns."""
        self._time_patterns = {}
        self._context_patterns = {}
        self._query_history = []
        self._save_patterns()
        logger.info("All patterns cleared")
