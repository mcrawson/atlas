"""Ollama local model provider for ATLAS."""

import logging
from typing import AsyncIterator, Optional

from .base import BaseProvider, ProviderError

logger = logging.getLogger("atlas.routing.providers.ollama")


class OllamaProvider(BaseProvider):
    """Ollama local model provider."""

    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        **kwargs
    ):
        """Initialize Ollama provider.

        Args:
            base_url: Ollama server URL
            model: Default model to use
            **kwargs: Additional options (may include code_model, fast_model)
        """
        super().__init__(None, **kwargs)  # No API key needed
        self.base_url = base_url
        self.model = model
        self.code_model = kwargs.get("code_model", "codellama:13b")
        self.fast_model = kwargs.get("fast_model", "llama3.2:3b")
        self._session = None

    async def _get_session(self):
        """Get an aiohttp session, creating a new one if needed."""
        try:
            import aiohttp
        except ImportError:
            raise ProviderError(
                "aiohttp package not installed. Run: pip install aiohttp",
                self.name,
                recoverable=False,
            )

        # Always create a fresh session to avoid event loop issues
        # The overhead is minimal compared to the API call itself
        return aiohttp.ClientSession()

    def is_available(self) -> bool:
        """Check if Ollama is available (always returns True, actual check at runtime)."""
        try:
            import aiohttp
            return True
        except ImportError:
            return False

    async def check_connection(self) -> bool:
        """Actually check if Ollama server is running.

        Returns:
            True if Ollama is accessible
        """
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"Ollama connection check failed: {e}")
            return False

    def select_model(self, task_type: Optional[str] = None) -> str:
        """Select the best model for a task type.

        Args:
            task_type: Type of task (code, fast, or None for default)

        Returns:
            Model name to use
        """
        if task_type == "code":
            return self.code_model
        elif task_type == "fast":
            return self.fast_model
        return self.model

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        task_type: Optional[str] = None,
    ) -> str:
        """Generate a response using Ollama."""
        import json
        import aiohttp

        model = self.select_model(task_type)
        system = system_prompt or self.get_system_prompt()

        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise ProviderError(f"Ollama error: {text}", self.name)

                    data = await response.json()
                    return data.get("response", "")
        except ProviderError:
            raise
        except Exception as e:
            if "ClientConnectorError" in str(type(e).__name__):
                raise ProviderError(
                    "Cannot connect to Ollama. Is it running? Try: ollama serve",
                    self.name,
                )
            raise ProviderError(str(e), self.name)

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        task_type: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream a response from Ollama."""
        import json
        import aiohttp

        model = self.select_model(task_type)
        system = system_prompt or self.get_system_prompt()

        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise ProviderError(f"Ollama error: {text}", self.name)

                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                continue
        except ProviderError:
            raise
        except Exception as e:
            if "ClientConnectorError" in str(type(e).__name__):
                raise ProviderError(
                    "Cannot connect to Ollama. Is it running? Try: ollama serve",
                    self.name,
                )
            raise ProviderError(str(e), self.name)

    async def close(self):
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
