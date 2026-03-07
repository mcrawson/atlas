"""Tests for configuration management."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from atlas.core.config import Config
from atlas.core.exceptions import MissingConfigException


class TestConfig:
    """Test Config class."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create a config instance with temp directory."""
        config_path = tmp_path / "config" / "atlas.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        return Config(config_path=config_path)

    def test_default_config_values(self, config):
        """Test that default values are set."""
        assert config.name == "ATLAS"
        assert config.get("atlas", "personality") == "butler"

    def test_get_nested_value(self, config):
        """Test getting nested configuration values."""
        value = config.get("providers", "claude", "enabled")
        assert value is True

    def test_get_with_default(self, config):
        """Test getting value with default."""
        value = config.get("nonexistent", "key", default="default_value")
        assert value == "default_value"

    def test_data_dir_property(self, config):
        """Test data_dir property."""
        assert isinstance(config.data_dir, Path)
        assert "data" in str(config.data_dir)

    def test_memory_dir_property(self, config):
        """Test memory_dir property."""
        assert isinstance(config.memory_dir, Path)
        assert "memory" in str(config.memory_dir)


class TestConfigApiKey:
    """Test API key retrieval."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create a config instance."""
        config_path = tmp_path / "config" / "atlas.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        return Config(config_path=config_path)

    def test_get_api_key_from_env(self, config):
        """Test getting API key from environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
            key = config.get_api_key("openai")
            assert key == "test-key-123"

    def test_get_api_key_missing(self, config):
        """Test getting missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            key = config.get_api_key("openai")
            assert key is None

    def test_require_api_key_raises(self, config):
        """Test require_api_key raises when missing."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(MissingConfigException):
                config.require_api_key("openai")

    def test_require_api_key_returns(self, config):
        """Test require_api_key returns key when present."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            key = config.require_api_key("openai")
            assert key == "test-key"


class TestConfigValidation:
    """Test configuration validation."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create a config instance."""
        config_path = tmp_path / "config" / "atlas.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        return Config(config_path=config_path)

    def test_validate_returns_warnings(self, config):
        """Test that validate returns a list."""
        warnings = config.validate()
        assert isinstance(warnings, list)

    def test_validate_warns_no_providers(self, config):
        """Test warning when no providers configured."""
        # Mock get_api_key to return None for all providers
        with patch.object(config, 'get_api_key', return_value=None):
            # Disable ollama in config
            config._config["providers"]["ollama"]["enabled"] = False

            warnings = config.validate()
            assert any("No AI providers" in w for w in warnings)

    def test_get_available_providers_with_key(self, config):
        """Test getting available providers."""
        env_patch = {
            "OPENAI_API_KEY": "test-key",
            "ANTHROPIC_API_KEY": "",
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
        }
        with patch.dict(os.environ, env_patch, clear=False):
            # Enable ollama
            config._config["providers"]["ollama"]["enabled"] = True

            providers = config.get_available_providers()
            assert "openai" in providers
            assert "ollama" in providers  # Ollama doesn't need key

    def test_get_available_providers_without_key(self, config):
        """Test available providers without API keys."""
        env_patch = {
            "OPENAI_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
        }
        with patch.dict(os.environ, env_patch, clear=False):
            # Enable ollama
            config._config["providers"]["ollama"]["enabled"] = True

            providers = config.get_available_providers()
            assert "openai" not in providers
            assert "ollama" in providers  # Ollama enabled by default


class TestConfigDeepMerge:
    """Test deep merge functionality."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create a config instance."""
        config_path = tmp_path / "config" / "atlas.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        return Config(config_path=config_path)

    def test_deep_merge_basic(self, config):
        """Test basic deep merge."""
        base = {"a": 1, "b": {"c": 2}}
        override = {"b": {"d": 3}}

        result = config._deep_merge(base, override)

        assert result["a"] == 1
        assert result["b"]["c"] == 2
        assert result["b"]["d"] == 3

    def test_deep_merge_override(self, config):
        """Test deep merge with override."""
        base = {"a": {"b": 1}}
        override = {"a": {"b": 2}}

        result = config._deep_merge(base, override)

        assert result["a"]["b"] == 2
