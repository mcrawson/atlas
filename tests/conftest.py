"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
import tempfile
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory that's cleaned up after test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton caches between tests."""
    # Clear broker cache
    from atlas.agents.message_broker import _brokers
    _brokers.clear()
    
    # Clear memory cache
    from atlas.agents.memory import _memories
    _memories.clear()
    
    yield
    
    # Clean up after test
    _brokers.clear()
    _memories.clear()
