"""Pytest configuration and shared fixtures for ATLAS tests."""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# --- Mock Providers ---

@pytest.fixture
def mock_openai_provider():
    """Mock OpenAI provider for testing without API calls."""
    provider = MagicMock()
    provider.name = "openai"
    provider.is_available.return_value = True
    provider.generate = AsyncMock(return_value="Mock OpenAI response")
    return provider


@pytest.fixture
def mock_claude_provider():
    """Mock Claude provider for testing without API calls."""
    provider = MagicMock()
    provider.name = "claude"
    provider.is_available.return_value = True
    provider.generate = AsyncMock(return_value="Mock Claude response")
    return provider


@pytest.fixture
def mock_ollama_provider():
    """Mock Ollama provider for testing without API calls."""
    provider = MagicMock()
    provider.name = "ollama"
    provider.is_available.return_value = True
    provider.generate = AsyncMock(return_value="Mock Ollama response")
    return provider


@pytest.fixture
def mock_providers(mock_openai_provider, mock_claude_provider, mock_ollama_provider):
    """Dictionary of all mock providers."""
    return {
        "openai": mock_openai_provider,
        "claude": mock_claude_provider,
        "ollama": mock_ollama_provider,
    }


# --- Mock Router ---

@pytest.fixture
def mock_router():
    """Mock router for testing agents without real routing."""
    router = MagicMock()
    router.route.return_value = {
        "provider": "openai",
        "task_type": "code",
        "reason": "Mock routing",
        "usage_before": 0,
    }
    return router


# --- Mock Memory ---

@pytest.fixture
def mock_memory():
    """Mock memory manager for testing without file I/O."""
    memory = MagicMock()
    memory.save_conversation = MagicMock()
    memory.get_recent_conversations.return_value = []
    memory.get_user_facts.return_value = []
    return memory


# --- Test Data ---

@pytest.fixture
def sample_task():
    """Sample task description for testing agents."""
    return "Create a Python function that calculates fibonacci numbers"


@pytest.fixture
def sample_context():
    """Sample context dictionary for testing."""
    return {
        "codebase": "Python project using FastAPI",
        "constraints": "Must be async-compatible",
    }
