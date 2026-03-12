"""Learning-based routing optimization for ATLAS.

Adapts provider selection based on:
- Historical success rates per task type
- User feedback (explicit ratings or implicit: retries, follow-ups)
- Provider performance (speed, cost, quality)
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("atlas.learning.routing")


@dataclass
class RoutingOutcome:
    """Record of a routing decision and its outcome."""
    provider: str
    task_type: str
    timestamp: str
    success: bool = True
    retried: bool = False
    user_rating: Optional[int] = None  # 1-5
    response_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RoutingLearner:
    """Learn from routing outcomes to improve provider selection.

    Tracks:
    - Success rates per provider/task_type combination
    - User satisfaction signals
    - Response times

    Uses this data to adjust routing preferences dynamically.
    """

    LEARNING_RATE = 0.1  # How quickly to adapt to new data
    MIN_SAMPLES = 5  # Minimum samples before adjusting
    DECAY_DAYS = 30  # How quickly old data loses relevance

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize routing learner.

        Args:
            data_dir: Directory for storing learning data
        """
        self.data_dir = data_dir or Path.home() / ".config" / "atlas"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "routing_history.json"

        # Outcome history
        self._outcomes: List[RoutingOutcome] = []
        self._max_history = 1000

        # Learned scores: provider -> task_type -> score (0.0 to 1.0)
        self._scores: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(lambda: 0.5))

        self._load_data()

    def _load_data(self):
        """Load historical data from file."""
        if not self.data_file.exists():
            return

        try:
            data = json.loads(self.data_file.read_text())

            for outcome_data in data.get("outcomes", []):
                self._outcomes.append(RoutingOutcome(**outcome_data))

            for provider, task_scores in data.get("scores", {}).items():
                for task_type, score in task_scores.items():
                    self._scores[provider][task_type] = score

            logger.info(f"Loaded {len(self._outcomes)} routing outcomes")

        except Exception as e:
            logger.error(f"Failed to load routing history: {e}")

    def _save_data(self):
        """Save data to file."""
        try:
            data = {
                "outcomes": [asdict(o) for o in self._outcomes[-500:]],
                "scores": {
                    provider: dict(tasks)
                    for provider, tasks in self._scores.items()
                },
            }
            self.data_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save routing history: {e}")

    def record_outcome(
        self,
        provider: str,
        task_type: str,
        success: bool = True,
        retried: bool = False,
        user_rating: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record the outcome of a routing decision.

        Args:
            provider: Provider that was used
            task_type: Type of task
            success: Whether the task succeeded
            retried: Whether user had to retry
            user_rating: Optional 1-5 rating from user
            response_time_ms: Response time in milliseconds
            metadata: Additional metadata
        """
        outcome = RoutingOutcome(
            provider=provider,
            task_type=task_type,
            timestamp=datetime.now().isoformat(),
            success=success,
            retried=retried,
            user_rating=user_rating,
            response_time_ms=response_time_ms,
            metadata=metadata or {},
        )

        self._outcomes.append(outcome)
        if len(self._outcomes) > self._max_history:
            self._outcomes.pop(0)

        # Update scores
        self._update_scores(outcome)

        # Periodic save
        if len(self._outcomes) % 10 == 0:
            self._save_data()

    def _update_scores(self, outcome: RoutingOutcome):
        """Update scores based on a new outcome.

        Args:
            outcome: The routing outcome to learn from
        """
        current = self._scores[outcome.provider][outcome.task_type]

        # Calculate outcome score (0.0 to 1.0)
        outcome_score = 1.0 if outcome.success else 0.0

        # Penalty for retry
        if outcome.retried:
            outcome_score *= 0.7

        # Use explicit rating if available
        if outcome.user_rating is not None:
            outcome_score = (outcome.user_rating - 1) / 4  # Convert 1-5 to 0-1

        # Apply learning rate
        new_score = current + self.LEARNING_RATE * (outcome_score - current)

        # Clamp to valid range
        self._scores[outcome.provider][outcome.task_type] = max(0.1, min(0.95, new_score))

        logger.debug(
            f"Updated {outcome.provider}/{outcome.task_type} score: "
            f"{current:.2f} -> {new_score:.2f}"
        )

    def get_provider_score(self, provider: str, task_type: str) -> float:
        """Get the learned score for a provider/task combination.

        Args:
            provider: Provider name
            task_type: Task type

        Returns:
            Score from 0.0 to 1.0 (higher is better)
        """
        return self._scores[provider][task_type]

    def get_best_providers(self, task_type: str, candidates: List[str]) -> List[str]:
        """Get providers sorted by learned preference for a task type.

        Args:
            task_type: The task type
            candidates: List of available provider names

        Returns:
            Sorted list of providers (best first)
        """
        # Get scores for each candidate
        scored = [
            (provider, self.get_provider_score(provider, task_type))
            for provider in candidates
        ]

        # Sort by score (highest first)
        scored.sort(key=lambda x: x[1], reverse=True)

        return [provider for provider, _ in scored]

    def get_adjustment(self, provider: str, task_type: str) -> float:
        """Get routing adjustment factor for a provider.

        Args:
            provider: Provider name
            task_type: Task type

        Returns:
            Adjustment factor (-0.5 to +0.5 for ranking adjustment)
        """
        score = self.get_provider_score(provider, task_type)
        # Convert 0.1-0.95 score to -0.5 to +0.5 adjustment
        return (score - 0.5)

    def get_recent_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get statistics for recent routing outcomes.

        Args:
            days: Number of days to look back

        Returns:
            Statistics dictionary
        """
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            o for o in self._outcomes
            if datetime.fromisoformat(o.timestamp) > cutoff
        ]

        stats = {
            "total_requests": len(recent),
            "success_rate": 0.0,
            "retry_rate": 0.0,
            "by_provider": {},
            "by_task_type": {},
        }

        if not recent:
            return stats

        stats["success_rate"] = sum(1 for o in recent if o.success) / len(recent)
        stats["retry_rate"] = sum(1 for o in recent if o.retried) / len(recent)

        # Group by provider
        by_provider = defaultdict(list)
        for o in recent:
            by_provider[o.provider].append(o)

        for provider, outcomes in by_provider.items():
            stats["by_provider"][provider] = {
                "requests": len(outcomes),
                "success_rate": sum(1 for o in outcomes if o.success) / len(outcomes),
            }

        # Group by task type
        by_task = defaultdict(list)
        for o in recent:
            by_task[o.task_type].append(o)

        for task_type, outcomes in by_task.items():
            stats["by_task_type"][task_type] = {
                "requests": len(outcomes),
                "success_rate": sum(1 for o in outcomes if o.success) / len(outcomes),
            }

        return stats

    def get_learned_preferences(self) -> Dict[str, List[str]]:
        """Get the learned routing preferences.

        Returns:
            Dictionary of task_type -> ordered list of preferred providers
        """
        # Collect all task types we've seen
        task_types = set()
        for provider_scores in self._scores.values():
            task_types.update(provider_scores.keys())

        preferences = {}
        for task_type in task_types:
            # Get all providers that have scores for this task type
            providers_with_scores = [
                (provider, self._scores[provider][task_type])
                for provider in self._scores
                if task_type in self._scores[provider]
            ]

            # Sort by score
            providers_with_scores.sort(key=lambda x: x[1], reverse=True)
            preferences[task_type] = [p for p, _ in providers_with_scores]

        return preferences


# Singleton instance
_routing_learner: Optional[RoutingLearner] = None


def get_routing_learner() -> RoutingLearner:
    """Get or create the global routing learner instance."""
    global _routing_learner
    if _routing_learner is None:
        _routing_learner = RoutingLearner()
    return _routing_learner
