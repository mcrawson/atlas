"""OpenAI GPT provider for ATLAS."""

import logging
import os
from typing import AsyncIterator, Optional

from .base import BaseProvider, ProviderError

logger = logging.getLogger("atlas.routing.providers.openai")


class OpenAIProvider(BaseProvider):
    """OpenAI GPT API provider."""

    name = "openai"

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o", **kwargs):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: Model to use (default: gpt-4o)
            **kwargs: Additional options
        """
        super().__init__(api_key, **kwargs)
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ProviderError(
                    "openai package not installed. Run: pip install openai",
                    self.name,
                    recoverable=False,
                )

            api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ProviderError(
                    "No API key found. Set OPENAI_API_KEY environment variable.",
                    self.name,
                    recoverable=False,
                )

            self._client = AsyncOpenAI(api_key=api_key)

        return self._client

    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        try:
            from openai import AsyncOpenAI
            api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
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
        """Generate a response using GPT."""
        client = self._get_client()
        system = system_prompt or self.get_system_prompt()

        try:
            response = await client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generate error: {e}", exc_info=True)
            raise ProviderError(str(e), self.name)

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream a response from GPT."""
        client = self._get_client()
        system = system_prompt or self.get_system_prompt()

        try:
            stream = await client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}", exc_info=True)
            raise ProviderError(str(e), self.name)
