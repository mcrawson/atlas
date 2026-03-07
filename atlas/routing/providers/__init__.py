"""AI provider implementations for ATLAS."""

import warnings

# Suppress deprecation warning from google.generativeai
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

from .base import BaseProvider, ProviderError
from .claude import ClaudeProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider

__all__ = [
    "BaseProvider",
    "ProviderError",
    "ClaudeProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "OllamaProvider",
]
