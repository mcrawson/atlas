"""Ollama Provider for ATLAS agents."""

import aiohttp
from dataclasses import dataclass
from typing import Optional


@dataclass
class OllamaConfig:
    """Ollama configuration."""
    base_url: str = "http://localhost:11434"
    default_model: str = "llama3"
    code_model: str = "codellama:13b"
    fast_model: str = "llama3.2:3b"


class OllamaProvider:
    """Ollama LLM provider for ATLAS agents."""

    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.name = "ollama"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a response using Ollama.

        Args:
            prompt: User prompt
            system_prompt: System prompt for the model
            model: Model to use (defaults to config.default_model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text
        """
        model = model or self.config.default_model
        url = f"{self.config.base_url}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama error: {error_text}")

                result = await response.json()
                return result.get("response", "")

    async def generate_chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a response using chat format.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text
        """
        model = model or self.config.default_model
        url = f"{self.config.base_url}/api/chat"

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama error: {error_text}")

                result = await response.json()
                return result.get("message", {}).get("content", "")

    def is_available(self) -> bool:
        """Check if provider is available (for agent interface compatibility)."""
        return True  # Actual availability checked at runtime

    async def check_health(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config.base_url}/api/tags") as response:
                    return response.status == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available models."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []


class SimpleRouter:
    """Simple router that always routes to a specific provider."""

    def __init__(self, default_provider: str = "ollama"):
        self.default_provider = default_provider

    def route(self, prompt: str) -> dict:
        """Route a prompt to a provider."""
        return {
            "provider": self.default_provider,
            "task_type": "general",
        }


class SimpleMemory:
    """Simple memory stub for agents (can be replaced with real memory)."""

    def __init__(self):
        self.conversations = []

    def save_conversation(self, **kwargs):
        """Save a conversation entry."""
        self.conversations.append(kwargs)

    def get_recent(self, limit: int = 10) -> list:
        """Get recent conversations."""
        return self.conversations[-limit:]


def create_agent_manager_with_ollama(config: Optional[OllamaConfig] = None):
    """Create an AgentManager configured to use Ollama.

    Args:
        config: Optional Ollama configuration

    Returns:
        Configured AgentManager
    """
    from .manager import AgentManager

    config = config or OllamaConfig()
    provider = OllamaProvider(config)
    router = SimpleRouter("ollama")
    memory = SimpleMemory()

    providers = {"ollama": provider}

    return AgentManager(router, memory, providers)
