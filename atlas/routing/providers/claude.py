"""Claude (Anthropic) provider for ATLAS."""

import logging
import os
from typing import AsyncIterator, Optional

from .base import BaseProvider, ProviderError

logger = logging.getLogger("atlas.routing.providers.claude")


class ClaudeProvider(BaseProvider):
    """Anthropic Claude API provider."""

    name = "claude"

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514", **kwargs):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            model: Model to use (default: claude-sonnet-4-20250514)
            **kwargs: Additional options
        """
        super().__init__(api_key, **kwargs)
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise ProviderError(
                    "anthropic package not installed. Run: pip install anthropic",
                    self.name,
                    recoverable=False,
                )

            api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ProviderError(
                    "No API key found. Set ANTHROPIC_API_KEY environment variable.",
                    self.name,
                    recoverable=False,
                )

            self._client = AsyncAnthropic(api_key=api_key)

        return self._client

    def is_available(self) -> bool:
        """Check if Claude is available."""
        try:
            from anthropic import AsyncAnthropic
            api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
            return api_key is not None
        except ImportError:
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Generate a response using Claude."""
        client = self._get_client()
        system = system_prompt or self.get_system_prompt()

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude generate error: {e}", exc_info=True)
            raise ProviderError(str(e), self.name)

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream a response from Claude."""
        client = self._get_client()
        system = system_prompt or self.get_system_prompt()

        try:
            async with client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Claude stream error: {e}", exc_info=True)
            raise ProviderError(str(e), self.name)
