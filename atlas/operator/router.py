"""
Task Router for Overnight Autonomous Operations.

Classifies incoming tasks and routes them to the appropriate handler:
- general: Research, drafts, reviews (Path C)
- atlas-fix: Bug fixes in ATLAS codebase (Path D)
- atlas-build: Product building with ATLAS agents (Path D)
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TaskMode(Enum):
    """Task processing modes."""
    GENERAL = "general"
    ATLAS_FIX = "atlas-fix"
    ATLAS_BUILD = "atlas-build"


@dataclass
class RoutingResult:
    """Result of task classification."""
    mode: TaskMode
    confidence: float  # 0.0 - 1.0
    reason: str
    suggested_role: Optional[str] = None  # For general mode


# Routing rules with weighted keywords
ROUTING_RULES = {
    TaskMode.ATLAS_FIX: {
        "keywords": {
            "fix": 3,
            "bug": 3,
            "error": 2,
            "broken": 3,
            "failing": 2,
            "crash": 3,
            "issue": 1,
            "debug": 2,
            "repair": 2,
            "patch": 2,
        },
        "targets": {
            "atlas": 5,
            "mason": 4,
            "qc": 4,
            "analyst": 4,
            "oracle": 3,
            "tinker": 3,
            "sketch": 3,
            "router": 2,
            "provider": 2,
            "agent": 2,
        },
        "file_patterns": [
            r"\.py$",
            r"atlas/",
        ],
    },
    TaskMode.ATLAS_BUILD: {
        "keywords": {
            "build": 3,
            "create": 3,
            "make": 2,
            "generate": 2,
            "design": 2,
            "develop": 2,
            "implement": 2,
        },
        "targets": {
            "app": 4,
            "site": 4,
            "website": 4,
            "page": 3,
            "landing": 4,
            "product": 4,
            "portfolio": 3,
            "store": 3,
            "dashboard": 3,
            "application": 3,
            "printable": 3,
            "document": 2,
            "ebook": 3,
        },
    },
    TaskMode.GENERAL: {
        "keywords": {
            "research": 5,  # High priority - research tasks are general
            "draft": 3,
            "write": 2,
            "review": 3,
            "analyze": 3,
            "summarize": 3,
            "find": 2,
            "explore": 2,
            "investigate": 3,
            "check": 1,
            "compare": 2,
            "evaluate": 2,
            "outline": 2,
            "plan": 1,
            "what are": 2,
            "what is": 2,
            "how to": 2,
            "best practices": 3,
            "top": 2,
        },
    },
}

# Role selection for general tasks
ROLE_KEYWORDS = {
    "researcher": ["research", "find", "explore", "investigate", "sources", "information"],
    "writer": ["write", "draft", "compose", "create content", "blog", "article"],
    "editor": ["edit", "proofread", "review writing", "grammar", "tone"],
    "reviewer": ["review", "code review", "feedback", "critique", "evaluate"],
    "factchecker": ["verify", "fact-check", "validate", "confirm", "accurate"],
    "analyst": ["analyze", "data", "trends", "insights", "compare", "metrics"],
}


class TaskRouter:
    """
    Routes tasks to appropriate handlers based on content analysis.
    """

    def classify(self, task: dict) -> RoutingResult:
        """
        Classify a task and determine the appropriate processing mode.

        Args:
            task: Task dict with 'prompt' and optional 'task_type', 'metadata'

        Returns:
            RoutingResult with mode, confidence, and reason
        """
        prompt = task.get("prompt", "").lower()
        task_type = (task.get("task_type") or "").lower()
        metadata = task.get("metadata", {}) or {}

        # Handle metadata as JSON string (from database)
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        # Check for explicit mode override in metadata
        if "mode" in metadata:
            mode_str = metadata["mode"]
            try:
                mode = TaskMode(mode_str)
                return RoutingResult(
                    mode=mode,
                    confidence=1.0,
                    reason="Explicit mode in metadata",
                    suggested_role=self._select_role(prompt) if mode == TaskMode.GENERAL else None,
                )
            except ValueError:
                pass

        # Check for explicit type override in task_type
        if task_type in ("atlas-fix", "atlas_fix"):
            return RoutingResult(
                mode=TaskMode.ATLAS_FIX,
                confidence=1.0,
                reason="Explicit task_type: atlas-fix",
            )
        if task_type in ("atlas-build", "atlas_build", "build"):
            return RoutingResult(
                mode=TaskMode.ATLAS_BUILD,
                confidence=1.0,
                reason="Explicit task_type: atlas-build",
            )

        # Score each mode
        scores = {}
        reasons = {}

        for mode, rules in ROUTING_RULES.items():
            score = 0
            matches = []

            # Score keywords
            for keyword, weight in rules.get("keywords", {}).items():
                if keyword in prompt:
                    score += weight
                    matches.append(f"keyword:{keyword}")

            # Score targets (for fix/build modes)
            for target, weight in rules.get("targets", {}).items():
                if target in prompt:
                    score += weight
                    matches.append(f"target:{target}")

            # Check file patterns (for fix mode)
            for pattern in rules.get("file_patterns", []):
                if re.search(pattern, prompt):
                    score += 2
                    matches.append(f"pattern:{pattern}")

            scores[mode] = score
            reasons[mode] = ", ".join(matches[:3])  # Top 3 matches

        # Find best match
        best_mode = max(scores, key=scores.get)
        best_score = scores[best_mode]

        # Calculate confidence (normalize by expected max score)
        max_possible = 15  # Reasonable max for strong matches
        confidence = min(1.0, best_score / max_possible)

        # Default to general if no strong match
        if best_score < 3:
            best_mode = TaskMode.GENERAL
            confidence = 0.5
            reasons[best_mode] = "No strong pattern match"

        # Select role for general tasks
        suggested_role = None
        if best_mode == TaskMode.GENERAL:
            suggested_role = self._select_role(prompt)

        return RoutingResult(
            mode=best_mode,
            confidence=confidence,
            reason=reasons.get(best_mode, "Pattern match"),
            suggested_role=suggested_role,
        )

    def _select_role(self, prompt: str) -> str:
        """Select the best role for a general task."""
        prompt_lower = prompt.lower()

        best_role = "researcher"  # Default
        best_score = 0

        for role, keywords in ROLE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > best_score:
                best_score = score
                best_role = role

        return best_role

    def get_mode_description(self, mode: TaskMode) -> str:
        """Get a human-readable description of a mode."""
        descriptions = {
            TaskMode.GENERAL: "General task (research, drafts, reviews)",
            TaskMode.ATLAS_FIX: "ATLAS bug fix (code changes on branch)",
            TaskMode.ATLAS_BUILD: "ATLAS product build (using agents)",
        }
        return descriptions.get(mode, "Unknown mode")
