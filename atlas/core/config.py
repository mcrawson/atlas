"""Configuration management for ATLAS.

Provides YAML-based configuration with environment variable support
and validation for startup checks.
"""

import logging
import os
from pathlib import Path
from typing import Any, List, Optional
import yaml

from atlas.core.exceptions import MissingConfigException, InvalidConfigException

logger = logging.getLogger("atlas.core.config")


class Config:
    """YAML-based configuration manager with environment variable support."""

    DEFAULT_CONFIG = {
        "atlas": {
            "name": "ATLAS",
            "personality": "butler",
        },
        "providers": {
            "claude": {
                "enabled": True,
                "daily_limit": 45,
            },
            "openai": {
                "enabled": True,
                "daily_limit": 40,
                "api_key_env": "OPENAI_API_KEY",
            },
            "gemini": {
                "enabled": True,
                "daily_limit": 100,
                "api_key_env": "GEMINI_API_KEY",
                "api_key_file": "~/.gemini/api_key",
            },
            "ollama": {
                "enabled": True,
                "base_url": "http://localhost:11434",
                "models": {
                    "default": "llama3",
                    "code": "codellama:13b",
                    "fast": "llama3.2:3b",
                },
            },
        },
        "memory": {
            "conversation_retention_days": 30,
        },
        "notifications": {
            "urgent_sound": True,
            "desktop_notifications": True,
        },
        "voice": {
            "enabled": False,
            "whisper_model": "base.en",
            "piper_voice": "en_GB-alan-medium",
        },
    }

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration.

        Args:
            config_path: Path to config file. If None, uses default location.
        """
        self.base_dir = Path.home() / "ai-workspace" / "atlas"
        self.config_path = config_path or self.base_dir / "config" / "atlas.yaml"
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from YAML file, merging with defaults."""
        config = self.DEFAULT_CONFIG.copy()

        if self.config_path.exists():
            with open(self.config_path) as f:
                user_config = yaml.safe_load(f) or {}
                config = self._deep_merge(config, user_config)

        return config

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notation path.

        Args:
            keys: Path segments (e.g., "providers", "claude", "daily_limit")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider from env or file.

        Args:
            provider: Provider name (claude, openai, gemini)

        Returns:
            API key string or None
        """
        provider_config = self.get("providers", provider, default={})

        # Try environment variable first
        env_var = provider_config.get("api_key_env")
        if env_var:
            key = os.environ.get(env_var)
            if key:
                return key

        # Try file
        key_file = provider_config.get("api_key_file")
        if key_file:
            key_path = Path(key_file).expanduser()
            if key_path.exists():
                return key_path.read_text().strip()

        return None

    def save(self) -> None:
        """Save current configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)

    @property
    def memory_dir(self) -> Path:
        """Path to memory storage directory."""
        return self.base_dir / "memory"

    @property
    def data_dir(self) -> Path:
        """Path to data directory (SQLite, logs)."""
        return self.base_dir / "data"

    @property
    def name(self) -> str:
        """Assistant name."""
        return self.get("atlas", "name", default="ATLAS")

    def validate(self) -> List[str]:
        """Validate configuration and return list of warnings.

        Returns:
            List of warning messages
        """
        warnings = []

        # Check if any providers are available
        available_providers = self.get_available_providers()
        if not available_providers:
            warnings.append(
                "No AI providers configured. Set at least one of: "
                "OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, "
                "or enable Ollama"
            )

        # Check data directory
        if not self.data_dir.exists():
            try:
                self.data_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                warnings.append(f"Cannot create data directory: {self.data_dir}")

        # Check memory directory
        if not self.memory_dir.exists():
            try:
                self.memory_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                warnings.append(f"Cannot create memory directory: {self.memory_dir}")

        return warnings

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names.

        Returns:
            List of provider names with valid configuration
        """
        available = []

        for provider in ["claude", "openai", "gemini"]:
            provider_config = self.get("providers", provider, default={})
            if not provider_config.get("enabled", True):
                continue

            api_key = self.get_api_key(provider)
            if api_key:
                available.append(provider)

        # Ollama doesn't need an API key
        ollama_config = self.get("providers", "ollama", default={})
        if ollama_config.get("enabled", True):
            available.append("ollama")

        return available

    def log_status(self) -> None:
        """Log configuration status."""
        logger.info("ATLAS Configuration:")
        logger.info(f"  Name: {self.name}")
        logger.info(f"  Config file: {self.config_path}")
        logger.info(f"  Data directory: {self.data_dir}")

        logger.info("  Providers:")
        for provider in ["claude", "openai", "gemini", "ollama"]:
            provider_config = self.get("providers", provider, default={})
            enabled = provider_config.get("enabled", True)

            if provider == "ollama":
                status = "enabled" if enabled else "disabled"
            else:
                api_key = self.get_api_key(provider)
                if not enabled:
                    status = "disabled"
                elif api_key:
                    status = "configured"
                else:
                    status = "no API key"

            logger.info(f"    {provider}: {status}")

        warnings = self.validate()
        for warning in warnings:
            logger.warning(f"  WARNING: {warning}")

    def require_api_key(self, provider: str) -> str:
        """Get API key or raise an exception.

        Args:
            provider: Provider name

        Returns:
            API key string

        Raises:
            MissingConfigException: If API key is not configured
        """
        api_key = self.get_api_key(provider)
        if not api_key:
            provider_config = self.get("providers", provider, default={})
            env_var = provider_config.get("api_key_env", f"{provider.upper()}_API_KEY")
            raise MissingConfigException(
                env_var,
                f"API key required for {provider} provider"
            )
        return api_key


def validate_startup() -> Config:
    """Validate configuration at startup.

    Returns:
        Config instance

    Raises:
        MissingConfigException: If required config is missing
        InvalidConfigException: If config values are invalid
    """
    config = Config()
    config.log_status()

    warnings = config.validate()
    if warnings:
        logger.warning(f"Configuration has {len(warnings)} warning(s)")

    return config
