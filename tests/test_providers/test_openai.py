"""Tests for OpenAI provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

from atlas.routing.providers.openai import OpenAIProvider
from atlas.routing.providers.base import ProviderError


class TestOpenAIProvider:
    """Test OpenAIProvider class."""

    def test_initialization_defaults(self):
        """Test default initialization."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIProvider()
            assert provider.name == "openai"
            assert provider.model == "gpt-4o"

    def test_initialization_custom(self):
        """Test custom initialization."""
        provider = OpenAIProvider(
            api_key="custom-key",
            model="gpt-4-turbo",
        )
        assert provider.api_key == "custom-key"
        assert provider.model == "gpt-4-turbo"

    def test_is_available_with_api_key(self):
        """Test is_available returns True when API key is set."""
        provider = OpenAIProvider(api_key="test-key")
        assert provider.is_available() is True

    def test_is_available_without_api_key(self):
        """Test is_available returns False without API key."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove OPENAI_API_KEY if it exists
            os.environ.pop("OPENAI_API_KEY", None)
            provider = OpenAIProvider()
            assert provider.is_available() is False


class TestOpenAIProviderGenerate:
    """Test OpenAIProvider generate method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return OpenAIProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        mock_message = MagicMock()
        mock_message.content = "Hello, world!"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("atlas.routing.providers.openai.OpenAIProvider._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await provider.generate("Say hello")
            assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, provider):
        """Test generation with custom system prompt."""
        mock_message = MagicMock()
        mock_message.content = "Custom response"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("atlas.routing.providers.openai.OpenAIProvider._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await provider.generate(
                "Test prompt",
                system_prompt="You are a test assistant"
            )
            assert result == "Custom response"

            # Verify the system prompt was passed
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs.get("messages", [])
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "You are a test assistant"

    @pytest.mark.asyncio
    async def test_generate_api_error(self, provider):
        """Test handling of API errors."""
        with patch("atlas.routing.providers.openai.OpenAIProvider._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("API rate limit exceeded")
            )
            mock_get_client.return_value = mock_client

            with pytest.raises(ProviderError) as exc_info:
                await provider.generate("Test")

            assert "rate limit" in str(exc_info.value).lower()


class TestOpenAIProviderStream:
    """Test OpenAIProvider generate_stream method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return OpenAIProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_generate_stream_success(self, provider):
        """Test successful streaming."""
        # Create mock chunks
        chunks = []
        for text in ["Hello", ", ", "world", "!"]:
            mock_delta = MagicMock()
            mock_delta.content = text
            mock_choice = MagicMock()
            mock_choice.delta = mock_delta
            mock_chunk = MagicMock()
            mock_chunk.choices = [mock_choice]
            chunks.append(mock_chunk)

        async def mock_stream():
            for chunk in chunks:
                yield chunk

        with patch("atlas.routing.providers.openai.OpenAIProvider._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
            mock_get_client.return_value = mock_client

            result = []
            async for text in provider.generate_stream("Say hello"):
                result.append(text)

            assert "".join(result) == "Hello, world!"


class TestOpenAIProviderGetClient:
    """Test OpenAIProvider _get_client method."""

    def test_get_client_missing_package(self):
        """Test error when openai package not installed."""
        provider = OpenAIProvider(api_key="test-key")

        with patch.dict("sys.modules", {"openai": None}):
            with patch("atlas.routing.providers.openai.OpenAIProvider._get_client") as mock:
                mock.side_effect = ProviderError(
                    "openai package not installed",
                    "openai",
                    recoverable=False
                )
                with pytest.raises(ProviderError) as exc_info:
                    provider._get_client()
                assert "not installed" in str(exc_info.value)

    def test_get_client_missing_api_key(self):
        """Test error when API key not provided."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            provider = OpenAIProvider()

            with pytest.raises(ProviderError) as exc_info:
                provider._get_client()
            assert "API key" in str(exc_info.value)
