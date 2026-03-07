"""Tests for Ollama provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from atlas.routing.providers.ollama import OllamaProvider
from atlas.routing.providers.base import ProviderError


class TestOllamaProvider:
    """Test OllamaProvider class."""

    def test_initialization_defaults(self):
        """Test default initialization."""
        provider = OllamaProvider()
        assert provider.name == "ollama"
        assert provider.base_url == "http://localhost:11434"
        assert provider.model == "llama3"
        assert provider.api_key is None

    def test_initialization_custom(self):
        """Test custom initialization."""
        provider = OllamaProvider(
            base_url="http://custom:1234",
            model="mistral",
            code_model="codellama:7b",
            fast_model="phi3",
        )
        assert provider.base_url == "http://custom:1234"
        assert provider.model == "mistral"
        assert provider.code_model == "codellama:7b"
        assert provider.fast_model == "phi3"

    def test_is_available_with_aiohttp(self):
        """Test is_available returns True when aiohttp is installed."""
        provider = OllamaProvider()
        # aiohttp is installed in the test environment
        assert provider.is_available() is True

    def test_select_model_default(self):
        """Test model selection for default task."""
        provider = OllamaProvider(model="llama3")
        assert provider.select_model() == "llama3"
        assert provider.select_model(None) == "llama3"

    def test_select_model_code(self):
        """Test model selection for code task."""
        provider = OllamaProvider(code_model="codellama:13b")
        assert provider.select_model("code") == "codellama:13b"

    def test_select_model_fast(self):
        """Test model selection for fast task."""
        provider = OllamaProvider(fast_model="llama3.2:3b")
        assert provider.select_model("fast") == "llama3.2:3b"


class TestOllamaProviderGenerate:
    """Test OllamaProvider generate method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return OllamaProvider()

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "Hello, world!"})

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_post = MagicMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock()
            mock_session.post.return_value = mock_post

            mock_session_class.return_value = mock_session

            result = await provider.generate("Say hello")
            assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, provider):
        """Test generation with custom system prompt."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "Custom response"})

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_post = MagicMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock()
            mock_session.post.return_value = mock_post

            mock_session_class.return_value = mock_session

            result = await provider.generate(
                "Test prompt",
                system_prompt="You are a test assistant"
            )
            assert result == "Custom response"

            # Verify the payload was correct
            call_args = mock_session.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload["system"] == "You are a test assistant"

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, provider):
        """Test handling of connection error."""
        # Test connection error handling
        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a mock that raises connection error
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
            mock_session_class.return_value = mock_session

            with pytest.raises(ProviderError) as exc_info:
                await provider.generate("Test")

            assert provider.name in str(exc_info.value)


class TestOllamaProviderCheckConnection:
    """Test OllamaProvider check_connection method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return OllamaProvider()

    @pytest.mark.asyncio
    async def test_check_connection_success(self, provider):
        """Test successful connection check."""
        mock_response = MagicMock()
        mock_response.status = 200

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_get = MagicMock()
            mock_get.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get.__aexit__ = AsyncMock()
            mock_session.get.return_value = mock_get

            mock_session_class.return_value = mock_session

            result = await provider.check_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, provider):
        """Test failed connection check."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
            mock_session_class.return_value = mock_session

            result = await provider.check_connection()
            assert result is False
