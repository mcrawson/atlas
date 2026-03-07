"""Google Gemini provider for ATLAS."""

import logging
import os
from pathlib import Path
from typing import AsyncIterator, Optional

from .base import BaseProvider, ProviderError

logger = logging.getLogger("atlas.routing.providers.gemini")


class GeminiProvider(BaseProvider):
    """Google Gemini API provider."""

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
            model: Model to use (default: gemini-1.5-flash)
            **kwargs: Additional options
        """
        super().__init__(api_key, **kwargs)
        self.model = model
        self._model_instance = None

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

    def _get_model(self):
        """Lazy initialization of Gemini model."""
        if self._model_instance is None:
            try:
                import warnings
                warnings.filterwarnings("ignore", category=FutureWarning, module="google")
                import google.generativeai as genai
            except ImportError:
                raise ProviderError(
                    "google-generativeai package not installed. Run: pip install google-generativeai",
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

            genai.configure(api_key=api_key)
            self._model_instance = genai.GenerativeModel(
                self.model,
                system_instruction=self.get_system_prompt(),
            )

        return self._model_instance

    def is_available(self) -> bool:
        """Check if Gemini is available."""
        try:
            import warnings
            warnings.filterwarnings("ignore", category=FutureWarning, module="google")
            import google.generativeai
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
        model = self._get_model()

        # If custom system prompt, create new model instance
        if system_prompt:
            try:
                import warnings
                warnings.filterwarnings("ignore", category=FutureWarning, module="google")
                import google.generativeai as genai
                model = genai.GenerativeModel(
                    self.model,
                    system_instruction=system_prompt,
                )
            except Exception as e:
                logger.error(f"Gemini model init error: {e}", exc_info=True)
                raise ProviderError(str(e), self.name)

        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                },
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
        model = self._get_model()

        # If custom system prompt, create new model instance
        if system_prompt:
            try:
                import google.generativeai as genai
                model = genai.GenerativeModel(
                    self.model,
                    system_instruction=system_prompt,
                )
            except Exception as e:
                logger.error(f"Gemini stream model init error: {e}", exc_info=True)
                raise ProviderError(str(e), self.name)

        try:
            response = await model.generate_content_async(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                },
                stream=True,
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini stream error: {e}", exc_info=True)
            raise ProviderError(str(e), self.name)
