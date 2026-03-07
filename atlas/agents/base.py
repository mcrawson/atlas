"""Base agent class for ATLAS multi-agent system."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional
from datetime import datetime

logger = logging.getLogger("atlas.agents")


class AgentStatus(Enum):
    """Status of an agent in the workflow."""
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentOutput:
    """Output from an agent's processing."""
    content: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    next_agent: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: AgentStatus = AgentStatus.COMPLETED
    timestamp: datetime = field(default_factory=datetime.now)
    reasoning: str = ""  # Agent's thought process / reasoning
    tokens_used: int = 0  # Tokens consumed for this output
    prompt_tokens: int = 0  # Input tokens
    completion_tokens: int = 0  # Output tokens

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "artifacts": self.artifacts,
            "next_agent": self.next_agent,
            "metadata": self.metadata,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "reasoning": self.reasoning,
            "tokens_used": self.tokens_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        }


class BaseAgent(ABC):
    """Abstract base class for ATLAS agents.

    Each agent has a distinct personality and specialization:
    - Architect: Strategic planner, methodical
    - Mason: Craftsman, detail-oriented builder
    - Oracle: Quality guardian, thorough verifier
    """

    name: str = "base"
    description: str = "Base agent"
    icon: str = "🤖"
    color: str = "#666666"

    def __init__(self, router, memory, **kwargs):
        """Initialize agent.

        Args:
            router: ATLAS Router for AI provider access
            memory: ATLAS MemoryManager for context
            **kwargs: Additional agent-specific options
        """
        self.router = router
        self.memory = memory
        self.options = kwargs
        self._status = AgentStatus.IDLE
        self._current_task: Optional[str] = None
        self._callbacks: list = []

    @property
    def status(self) -> AgentStatus:
        """Get current agent status."""
        return self._status

    @status.setter
    def status(self, value: AgentStatus):
        """Set status and notify callbacks."""
        self._status = value
        self._notify_status_change()

    def _notify_status_change(self):
        """Notify all registered callbacks of status change."""
        for callback in self._callbacks:
            try:
                callback(self.name, self._status, self._current_task)
            except Exception:
                pass

    def register_callback(self, callback):
        """Register a callback for status updates.

        Args:
            callback: Function(agent_name, status, task) to call on updates
        """
        self._callbacks.append(callback)

    def unregister_callback(self, callback):
        """Remove a registered callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the agent's system prompt defining its personality and role.

        Returns:
            System prompt string
        """
        raise NotImplementedError("Subclasses must implement get_system_prompt()")

    @abstractmethod
    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Process a task and return output.

        Args:
            task: The task description or prompt
            context: Optional context dictionary
            previous_output: Output from previous agent in chain

        Returns:
            AgentOutput with results
        """
        raise NotImplementedError("Subclasses must implement process()")

    async def stream_process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AsyncIterator[str]:
        """Stream process a task, yielding content chunks.

        Args:
            task: The task description or prompt
            context: Optional context dictionary
            previous_output: Output from previous agent in chain

        Yields:
            Content chunks as they're generated
        """
        self.status = AgentStatus.THINKING
        self._current_task = task

        try:
            # Default implementation: process and yield result
            result = await self.process(task, context, previous_output)
            yield result.content
        finally:
            self.status = AgentStatus.IDLE
            self._current_task = None

    async def _generate_with_provider(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider_name: Optional[str] = None,
        temperature: float = 0.7,
    ) -> tuple[str, dict]:
        """Generate response using the router with fallback support.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt override
            provider_name: Optional specific provider to use
            temperature: Sampling temperature

        Returns:
            Tuple of (response_text, token_info_dict)
        """
        from atlas.routing.providers import ProviderError

        # Use agent's system prompt if not overridden
        if system_prompt is None:
            system_prompt = self.get_system_prompt()

        providers = self.options.get("providers", {})

        # Define fallback order - prefer OpenAI/Claude for code tasks
        fallback_order = ["openai", "claude", "gemini", "ollama"]

        # If a specific provider is requested, try it first
        if provider_name:
            fallback_order = [provider_name] + [p for p in fallback_order if p != provider_name]
        else:
            # Get routing decision
            routing = self.router.route(prompt)
            preferred = routing["provider"]
            fallback_order = [preferred] + [p for p in fallback_order if p != preferred]

        # Try each provider in order until one works
        last_error = None
        for try_provider in fallback_order:
            provider = providers.get(try_provider)

            if not provider:
                continue

            if not provider.is_available():
                logger.debug(f"[{self.name}] Provider {try_provider} not available, trying next...")
                continue

            try:
                logger.info(f"[{self.name}] Using provider: {try_provider}")
                response = await provider.generate(
                    prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                )

                # Estimate token usage (providers may return actual counts)
                # Basic estimation: ~4 chars per token
                token_info = {
                    "prompt_tokens": len(prompt + (system_prompt or "")) // 4,
                    "completion_tokens": len(response) // 4,
                    "total_tokens": (len(prompt + (system_prompt or "")) + len(response)) // 4,
                    "provider": try_provider,
                }

                return response, token_info

            except Exception as e:
                error_str = str(e)
                logger.warning(f"[{self.name}] Provider {try_provider} failed: {error_str[:100]}")
                last_error = e

                # If rate limited (429), try next provider
                if "429" in error_str or "rate" in error_str.lower() or "exhausted" in error_str.lower():
                    continue
                # For other errors, also try next provider
                continue

        # All providers failed
        raise ProviderError(
            f"All providers failed. Last error: {last_error}",
            "all",
            recoverable=False
        )

    def get_status_dict(self) -> dict:
        """Get agent status as dictionary for API/WebSocket.

        Returns:
            Status dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "status": self._status.value,
            "current_task": self._current_task,
        }
