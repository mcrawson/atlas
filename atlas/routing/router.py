"""Intelligent task routing between AI providers."""

import re
from typing import Optional
from .usage import UsageTracker


class Router:
    """Route tasks to the most appropriate AI provider."""

    # Task type patterns for classification
    TASK_PATTERNS = {
        "code": [
            r"\b(code|function|class|debug|fix|implement|refactor|program|script)\b",
            r"\b(python|javascript|typescript|rust|go|java|c\+\+|sql)\b",
            r"\b(error|bug|exception|traceback|syntax)\b",
            r"\b(api|endpoint|database|query)\b",
        ],
        "research": [
            r"\b(research|reaserch|reserch|find|search|look up|lookup|what is|who is|when did)\b",
            r"\b(explain|describe|define|summarize|summary|overview|tell me about)\b",
            r"\b(compare|difference|between|versus|vs)\b",
            r"\b(latest|recent|current|news|update)\b",
            r"\b(learn|understand|know|information|info|about)\b",
            r"\b(history|background|origin|meaning)\b",
        ],
        "review": [
            r"\b(review|critique|analyze|evaluate|assess)\b",
            r"\b(feedback|opinion|thoughts|consider)\b",
            r"\b(pros and cons|trade-?offs|advantages|disadvantages)\b",
            r"\b(should i|would you recommend|better option)\b",
        ],
        "draft": [
            r"\b(write|draft|compose|create|generate)\b",
            r"\b(email|letter|document|report|article|blog)\b",
            r"\b(message|response|reply|announcement)\b",
            r"\b(outline|template|structure)\b",
        ],
    }

    # Provider routing preferences by task type
    # Format: task_type -> [primary, fallback1, fallback2]
    ROUTING_TABLE = {
        "research": ["gemini", "claude", "ollama"],
        "code": ["openai", "claude", "ollama"],
        "review": ["claude", "gemini", "openai"],
        "draft": ["gemini", "claude", "ollama"],
        "default": ["ollama", "gemini", "claude"],
    }

    def __init__(self, usage_tracker: Optional[UsageTracker] = None):
        """Initialize router.

        Args:
            usage_tracker: UsageTracker instance. Creates one if not provided.
        """
        self.usage = usage_tracker or UsageTracker()

    def classify_task(self, prompt: str) -> str:
        """Classify the task type based on the prompt.

        Args:
            prompt: User's input prompt

        Returns:
            Task type string (code, research, review, draft, or default)
        """
        prompt_lower = prompt.lower()
        scores = {task_type: 0 for task_type in self.TASK_PATTERNS}

        for task_type, patterns in self.TASK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    scores[task_type] += 1

        # Return the highest scoring type, or "default" if no matches
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "default"

    def select_provider(
        self,
        task_type: str,
        preferred_provider: Optional[str] = None,
    ) -> tuple[str, str]:
        """Select the best available provider for a task.

        Args:
            task_type: The classified task type
            preferred_provider: Optional override for provider selection

        Returns:
            Tuple of (selected_provider, selection_reason)
        """
        # If user explicitly requested a provider, try to honor it
        if preferred_provider:
            if self.usage.is_available(preferred_provider):
                return preferred_provider, f"User requested {preferred_provider}"
            else:
                reason = f"{preferred_provider} exhausted, using fallback"
        else:
            reason = f"Best for {task_type} tasks"

        # Get routing preferences for this task type
        providers = self.ROUTING_TABLE.get(task_type, self.ROUTING_TABLE["default"])

        # Find first available provider
        for provider in providers:
            if self.usage.is_available(provider):
                return provider, reason

        # All providers exhausted - use ollama as last resort (unlimited)
        return "ollama", "All API providers exhausted, using local model"

    def route(
        self,
        prompt: str,
        preferred_provider: Optional[str] = None,
    ) -> dict:
        """Route a prompt to the appropriate provider.

        Args:
            prompt: User's input prompt
            preferred_provider: Optional override for provider selection

        Returns:
            Dictionary with routing decision:
            {
                "provider": str,
                "task_type": str,
                "reason": str,
                "usage_before": int,
            }
        """
        task_type = self.classify_task(prompt)
        provider, reason = self.select_provider(task_type, preferred_provider)
        usage_before = self.usage.get_usage(provider)

        return {
            "provider": provider,
            "task_type": task_type,
            "reason": reason,
            "usage_before": usage_before,
        }

    def log_completion(self, provider: str, task_type: str) -> int:
        """Log successful completion and return new usage count.

        Args:
            provider: The provider that was used
            task_type: The task type that was performed

        Returns:
            New usage count for the provider
        """
        return self.usage.log_usage(provider, task_type)

    def get_recommendation(self, task_type: str) -> str:
        """Get a human-readable recommendation for a task type.

        Args:
            task_type: The task type

        Returns:
            Recommendation string
        """
        provider, reason = self.select_provider(task_type)
        indicator = self.usage.get_status_indicator(provider)

        return f"{provider.title()} {indicator} - {reason}"
