"""Base provider interface for ATLAS."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

# Import from core exceptions for the full hierarchy
from atlas.core.exceptions import (
    ProviderError,
    ProviderException,
    ProviderUnavailableException,
    ProviderRateLimitException,
    ProviderAuthException,
    ProviderResponseException,
)

# Re-export for backwards compatibility
__all__ = [
    "ProviderError",
    "ProviderException",
    "ProviderUnavailableException",
    "ProviderRateLimitException",
    "ProviderAuthException",
    "ProviderResponseException",
    "BaseProvider",
]


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    name: str = "base"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize provider.

        Args:
            api_key: API key for the provider
            **kwargs: Additional provider-specific options
        """
        self.api_key = api_key
        self.options = kwargs

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Generate a response for the given prompt.

        Args:
            prompt: User's input prompt
            system_prompt: Optional system prompt for context
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Generated response text
        """
        raise NotImplementedError("Subclasses must implement generate()")

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream a response for the given prompt.

        Args:
            prompt: User's input prompt
            system_prompt: Optional system prompt for context
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Yields:
            Response text chunks
        """
        raise NotImplementedError("Subclasses must implement generate_stream()")

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured.

        Returns:
            True if provider can be used
        """
        raise NotImplementedError("Subclasses must implement is_available()")

    def get_system_prompt(self, user_context: str = None, conversation_history: str = None) -> str:
        """Get the ATLAS system prompt with user context.

        Args:
            user_context: User preferences and facts to remember
            conversation_history: Recent conversation for context

        Returns:
            System prompt string
        """
        base_prompt = """You are ATLAS (Automated Thinking, Learning & Advisory System), an AI assistant with a refined, dry wit.

Your communication style:
- Professional with subtle British wit
- Address the user as "sir" occasionally, not every sentence
- Be helpful and thorough, but concise
- Don't constantly remind the user you're an assistant or butler
- Just answer the question - skip meta-commentary about yourself

IMPORTANT - Be honest about your limitations:
- Do NOT pretend to look up past conversations you can't access
- Do NOT make up fake data, tasks, dates, or topics with placeholders like "[Topic]"
- If asked about pending tasks, tell users to run /queue status
- If asked about something you don't know, say so clearly
- If you don't have context, ask for clarification - don't invent details

ATLAS CAPABILITIES:

Core Features:
- Multi-model AI routing (Claude, GPT, Gemini, Ollama) - automatically picks the best model for each task
- Background task queue (/queue add <task>) - queue research for processing later
- Memory system - remembers conversations, preferences, and facts about the user

Briefings & Sessions:
- /morning - Full morning briefing with news, calendar, system status
- /startsession - Quick session start briefing
- /endsession - Session summary and exit
- /endday - End of day report with insights
- /briefing - Quick status check

Monitoring (runs in background):
- System monitoring - CPU, memory, disk alerts
- Git monitoring - uncommitted changes, unpushed commits
- Web monitoring - URL availability checks

Integrations:
- Home Assistant (Smart Home) - requires setup:
  - /home - Setup instructions and status
  - /home lights - List all lights
  - /home on <entity> - Turn on (e.g., /home on light.office)
  - /home off <entity> - Turn off
- Google Calendar & Gmail - requires setup:
  - /google - Set up Google integration (one-time OAuth)
  - /calendar - Show today's calendar events
  - /email - Show important emails

Learning:
- Pattern detection - learns your habits and routines
- Proactive suggestions based on learned patterns
- /patterns - view learned patterns

Other Commands:
- /reminder <text> - Set reminders
- /remember <fact> - Store facts about the user
- /model <name> - Force specific AI model
- /status - Show provider usage and quotas
- /help - Show all commands

Focus on being genuinely helpful. Your personality should come through naturally, not be forced."""

        # Add user context if provided
        if user_context:
            base_prompt += f"\n\nIMPORTANT - User Preferences:\n{user_context}"

        # Add conversation history if provided
        if conversation_history:
            base_prompt += f"\n\nRECENT CONVERSATION HISTORY - Use this to maintain continuity:\n{conversation_history}\n\nUse this history to understand what you and the user have discussed. Reference previous topics when relevant."

        return base_prompt
