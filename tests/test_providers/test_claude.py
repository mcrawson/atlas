"""Tests for Claude (Anthropic) provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

from atlas.routing.providers.claude import ClaudeProvider
from atlas.routing.providers.base import ProviderError


class TestClaudeProvider:
    """Test ClaudeProvider class."""

    def test_initialization_defaults(self):
        """Test default initialization."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            provider = ClaudeProvider()
            assert provider.name == "claude"
            assert "claude" in provider.model.lower()

    def test_initialization_custom(self):
        """Test custom initialization."""
        provider = ClaudeProvider(
            api_key="custom-key",
            model="claude-3-opus-20240229",
        )
        assert provider.api_key == "custom-key"
        assert provider.model == "claude-3-opus-20240229"

    def test_is_available_with_api_key(self):
        """Test is_available returns True when API key is set."""
        provider = ClaudeProvider(api_key="test-key")
        assert provider.is_available() is True

    def test_is_available_without_api_key(self):
        """Test is_available returns False without API key."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            provider = ClaudeProvider()
            assert provider.is_available() is False


class TestClaudeProviderGenerate:
    """Test ClaudeProvider generate method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return ClaudeProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        mock_content_block = MagicMock()
        mock_content_block.text = "Hello, world!"

        mock_response = MagicMock()
        mock_response.content = [mock_content_block]

        with patch("atlas.routing.providers.claude.ClaudeProvider._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await provider.generate("Say hello")
            assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, provider):
        """Test generation with custom system prompt."""
        mock_content_block = MagicMock()
        mock_content_block.text = "Custom response"

        mock_response = MagicMock()
        mock_response.content = [mock_content_block]

        with patch("atlas.routing.providers.claude.ClaudeProvider._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await provider.generate(
                "Test prompt",
                system_prompt="You are a test assistant"
            )
            assert result == "Custom response"

            # Verify the system prompt was passed
            call_args = mock_client.messages.create.call_args
            assert call_args.kwargs.get("system") == "You are a test assistant"

    @pytest.mark.asyncio
    async def test_generate_api_error(self, provider):
        """Test handling of API errors."""
        with patch("atlas.routing.providers.claude.ClaudeProvider._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(
                side_effect=Exception("API rate limit exceeded")
            )
            mock_get_client.return_value = mock_client

            with pytest.raises(ProviderError) as exc_info:
                await provider.generate("Test")

            assert provider.name in str(exc_info.value)


class TestClaudeProviderStream:
    """Test ClaudeProvider generate_stream method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return ClaudeProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_generate_stream_success(self, provider):
        """Test successful streaming."""
        # Create mock text stream
        async def mock_text_stream():
            for text in ["Hello", ", ", "world", "!"]:
                yield text

        mock_stream_context = MagicMock()
        mock_stream_context.text_stream = mock_text_stream()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_stream_context)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)

        with patch("atlas.routing.providers.claude.ClaudeProvider._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.stream = MagicMock(return_value=mock_stream_context)
            mock_get_client.return_value = mock_client

            result = []
            async for text in provider.generate_stream("Say hello"):
                result.append(text)

            assert "".join(result) == "Hello, world!"


class TestClaudeProviderGetClient:
    """Test ClaudeProvider _get_client method."""

    def test_get_client_missing_api_key(self):
        """Test error when API key not provided."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            provider = ClaudeProvider()

            with pytest.raises(ProviderError) as exc_info:
                provider._get_client()
            assert "API key" in str(exc_info.value)
