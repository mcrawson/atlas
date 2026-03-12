"""Google Gemini provider for ATLAS."""

import logging
import os
from pathlib import Path
from typing import AsyncIterator, Optional

from .base import BaseProvider, ProviderError

logger = logging.getLogger("atlas.routing.providers.gemini")


class GeminiProvider(BaseProvider):
    """Google Gemini API provider using google-genai package."""

    name = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        **kwargs
    ):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key. Checks GEMINI_API_KEY env var and ~/.gemini/api_key
            model: Model to use (default: gemini-2.0-flash)
            **kwargs: Additional options
        """
        super().__init__(api_key, **kwargs)
        self.model = model
        self._client = None

    def _get_api_key(self) -> Optional[str]:
        """Get API key from various sources."""
        if self.api_key:
            return self.api_key

        # Try environment variable
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if key:
            return key

        # Try file
        key_file = Path.home() / ".gemini" / "api_key"
        if key_file.exists():
            return key_file.read_text().strip()

        return None

    def _get_client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            try:
                from google import genai
            except ImportError:
                raise ProviderError(
                    "google-genai package not installed. Run: pip install google-genai",
                    self.name,
                    recoverable=False,
                )

            api_key = self._get_api_key()
            if not api_key:
                raise ProviderError(
                    "No API key found. Set GEMINI_API_KEY or create ~/.gemini/api_key",
                    self.name,
                    recoverable=False,
                )

            self._client = genai.Client(api_key=api_key)

        return self._client

    def is_available(self) -> bool:
        """Check if Gemini is available."""
        try:
            from google import genai
            return self._get_api_key() is not None
        except ImportError:
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Generate a response using Gemini."""
        client = self._get_client()

        # Build the contents with optional system instruction
        system_instruction = system_prompt or self.get_system_prompt()

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                system_instruction=system_instruction,
            )

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generate error: {e}", exc_info=True)
            raise ProviderError(str(e), self.name)

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream a response from Gemini."""
        client = self._get_client()

        system_instruction = system_prompt or self.get_system_prompt()

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                system_instruction=system_instruction,
            )

            # Use streaming
            response = client.models.generate_content_stream(
                model=self.model,
                contents=prompt,
                config=config,
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini stream error: {e}", exc_info=True)
            raise ProviderError(str(e), self.name)
