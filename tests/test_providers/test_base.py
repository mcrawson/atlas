"""Tests for base provider interface."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from atlas.routing.providers.base import (
    BaseProvider,
    ProviderError,
    ProviderException,
)


class TestProviderError:
    """Test ProviderError exception."""

    def test_basic_error(self):
        """Test creating a basic provider error."""
        error = ProviderError("Connection failed", "openai")
        assert error.provider == "openai"
        assert "Connection failed" in str(error)
        assert error.recoverable is True

    def test_non_recoverable_error(self):
        """Test non-recoverable error."""
        error = ProviderError("Invalid API key", "claude", recoverable=False)
        assert error.recoverable is False

    def test_error_inheritance(self):
        """Test that ProviderError inherits from ProviderException."""
        error = ProviderError("Test", "test")
        assert isinstance(error, ProviderException)


class TestBaseProvider:
    """Test BaseProvider abstract class."""

    def test_cannot_instantiate_directly(self):
        """Test that BaseProvider cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseProvider()

    def test_concrete_implementation(self):
        """Test that concrete implementations can be created."""

        class ConcreteProvider(BaseProvider):
            name = "test"

            async def generate(self, prompt, **kwargs):
                return "test response"

            async def generate_stream(self, prompt, **kwargs):
                yield "test"

            def is_available(self):
                return True

        provider = ConcreteProvider()
        assert provider.name == "test"
        assert provider.is_available()

    def test_provider_with_api_key(self):
        """Test provider initialization with API key."""

        class ConcreteProvider(BaseProvider):
            name = "test"

            async def generate(self, prompt, **kwargs):
                return "test"

            async def generate_stream(self, prompt, **kwargs):
                yield "test"

            def is_available(self):
                return self.api_key is not None

        provider = ConcreteProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.is_available()

    def test_provider_without_api_key(self):
        """Test provider without API key."""

        class ConcreteProvider(BaseProvider):
            name = "test"

            async def generate(self, prompt, **kwargs):
                return "test"

            async def generate_stream(self, prompt, **kwargs):
                yield "test"

            def is_available(self):
                return self.api_key is not None

        provider = ConcreteProvider()
        assert provider.api_key is None
        assert not provider.is_available()

    def test_get_system_prompt(self):
        """Test getting system prompt."""

        class ConcreteProvider(BaseProvider):
            name = "test"

            async def generate(self, prompt, **kwargs):
                return "test"

            async def generate_stream(self, prompt, **kwargs):
                yield "test"

            def is_available(self):
                return True

        provider = ConcreteProvider()
        prompt = provider.get_system_prompt()

        assert isinstance(prompt, str)
        assert "ATLAS" in prompt

    def test_system_prompt_with_user_context(self):
        """Test system prompt with user context."""

        class ConcreteProvider(BaseProvider):
            name = "test"

            async def generate(self, prompt, **kwargs):
                return "test"

            async def generate_stream(self, prompt, **kwargs):
                yield "test"

            def is_available(self):
                return True

        provider = ConcreteProvider()
        prompt = provider.get_system_prompt(user_context="User prefers formal language")

        assert "User Preferences" in prompt
        assert "formal language" in prompt
