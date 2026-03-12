"""Tests for Gemini (Google) provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
from pathlib import Path

from atlas.routing.providers.gemini import GeminiProvider
from atlas.routing.providers.base import ProviderError


class TestGeminiProvider:
    """Test GeminiProvider class."""

    def test_initialization_defaults(self):
        """Test default initialization."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            provider = GeminiProvider()
            assert provider.name == "gemini"
            assert "gemini" in provider.model.lower()

    def test_initialization_custom(self):
        """Test custom initialization."""
        provider = GeminiProvider(
            api_key="custom-key",
            model="gemini-1.5-pro",
        )
        assert provider.api_key == "custom-key"
        assert provider.model == "gemini-1.5-pro"

    def test_is_available_with_api_key(self):
        """Test is_available returns True when API key is set."""
        with patch("atlas.routing.providers.gemini.genai", create=True):
            provider = GeminiProvider(api_key="test-key")
            assert provider.is_available() is True

    def test_is_available_without_api_key(self):
        """Test is_available returns False without API key."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("GOOGLE_API_KEY", None)
            provider = GeminiProvider()
            # Mock Path.home() to return a path without api_key file
            with patch.object(Path, "exists", return_value=False):
                assert provider.is_available() is False


class TestGeminiProviderGetApiKey:
    """Test GeminiProvider _get_api_key method."""

    def test_get_api_key_from_instance(self):
        """Test getting API key from instance."""
        provider = GeminiProvider(api_key="instance-key")
        assert provider._get_api_key() == "instance-key"

    def test_get_api_key_from_gemini_env(self):
        """Test getting API key from GEMINI_API_KEY env var."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}, clear=True):
            provider = GeminiProvider()
            assert provider._get_api_key() == "env-key"

    def test_get_api_key_from_google_env(self):
        """Test getting API key from GOOGLE_API_KEY env var."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "google-key"}, clear=True):
            provider = GeminiProvider()
            assert provider._get_api_key() == "google-key"

    def test_get_api_key_none_when_not_found(self):
        """Test None returned when no API key found."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("GOOGLE_API_KEY", None)
            provider = GeminiProvider()

            with patch.object(Path, "exists", return_value=False):
                assert provider._get_api_key() is None


class TestGeminiProviderGenerate:
    """Test GeminiProvider generate method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return GeminiProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        mock_response = MagicMock()
        mock_response.text = "Hello, world!"

        mock_client = MagicMock()
        mock_client.models.generate_content = MagicMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.generate("Say hello")
            assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_generate_with_custom_system_prompt(self, provider):
        """Test generation with custom system prompt."""
        mock_response = MagicMock()
        mock_response.text = "Custom response"

        mock_client = MagicMock()
        mock_client.models.generate_content = MagicMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.generate(
                "Test prompt",
                system_prompt="You are a test assistant"
            )
            assert result == "Custom response"

    @pytest.mark.asyncio
    async def test_generate_api_error(self, provider):
        """Test handling of API errors."""
        mock_client = MagicMock()
        mock_client.models.generate_content = MagicMock(
            side_effect=Exception("API quota exceeded")
        )

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(ProviderError) as exc_info:
                await provider.generate("Test")

            assert provider.name in str(exc_info.value)


class TestGeminiProviderStream:
    """Test GeminiProvider generate_stream method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return GeminiProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_generate_stream_success(self, provider):
        """Test successful streaming."""
        # Create mock chunks
        chunks = []
        for text in ["Hello", ", ", "world", "!"]:
            mock_chunk = MagicMock()
            mock_chunk.text = text
            chunks.append(mock_chunk)

        mock_client = MagicMock()
        mock_client.models.generate_content_stream = MagicMock(return_value=iter(chunks))

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = []
            async for text in provider.generate_stream("Say hello"):
                result.append(text)

            assert "".join(result) == "Hello, world!"


class TestGeminiProviderGetClient:
    """Test GeminiProvider _get_client method."""

    def test_get_client_missing_api_key(self):
        """Test error when API key not provided."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("GOOGLE_API_KEY", None)
            provider = GeminiProvider()

            with patch.object(Path, "exists", return_value=False):
                with pytest.raises(ProviderError) as exc_info:
                    provider._get_client()
                assert "API key" in str(exc_info.value)
