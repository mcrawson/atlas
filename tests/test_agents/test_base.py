"""Tests for the base agent class."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from atlas.agents.base import BaseAgent, AgentOutput, AgentStatus


class TestAgentStatus:
    """Test AgentStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all expected statuses are defined."""
        assert AgentStatus.IDLE
        assert AgentStatus.THINKING
        assert AgentStatus.WORKING
        assert AgentStatus.WAITING
        assert AgentStatus.COMPLETED
        assert AgentStatus.ERROR

    def test_status_values(self):
        """Test status string values."""
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.THINKING.value == "thinking"
        assert AgentStatus.WORKING.value == "working"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.ERROR.value == "error"


class TestAgentOutput:
    """Test AgentOutput dataclass."""

    def test_output_creation(self):
        """Test creating an agent output."""
        output = AgentOutput(
            content="Test output",
            artifacts={"file": "test.py"},
            next_agent="oracle",
            metadata={"key": "value"},
        )

        assert output.content == "Test output"
        assert output.artifacts == {"file": "test.py"}
        assert output.next_agent == "oracle"
        assert output.metadata == {"key": "value"}
        assert output.status == AgentStatus.COMPLETED  # default

    def test_output_defaults(self):
        """Test default values for AgentOutput."""
        output = AgentOutput(content="Minimal output")

        assert output.content == "Minimal output"
        assert output.artifacts == {}
        assert output.next_agent is None
        assert output.metadata == {}
        assert output.status == AgentStatus.COMPLETED
        assert output.reasoning == ""
        assert output.tokens_used == 0

    def test_output_to_dict(self):
        """Test converting output to dictionary."""
        output = AgentOutput(
            content="Test",
            artifacts={"code": "print('hello')"},
            metadata={"agent": "test"},
            reasoning="I did this because...",
            tokens_used=100,
        )

        output_dict = output.to_dict()

        assert output_dict["content"] == "Test"
        assert output_dict["artifacts"] == {"code": "print('hello')"}
        assert output_dict["metadata"] == {"agent": "test"}
        assert output_dict["reasoning"] == "I did this because..."
        assert output_dict["tokens_used"] == 100
        assert output_dict["status"] == "completed"
        assert "timestamp" in output_dict

    def test_output_with_error_status(self):
        """Test output with error status."""
        output = AgentOutput(
            content="Error occurred",
            status=AgentStatus.ERROR,
            metadata={"error": "Connection failed"},
        )

        assert output.status == AgentStatus.ERROR
        assert output.metadata["error"] == "Connection failed"


class TestBaseAgentInterface:
    """Test BaseAgent interface and common functionality."""

    def test_cannot_instantiate_base_agent(self):
        """Test that BaseAgent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseAgent(MagicMock(), MagicMock())

    def test_abstract_methods_raise_not_implemented(self):
        """Test that abstract methods would raise NotImplementedError."""
        # Create a minimal concrete implementation for testing
        class MinimalAgent(BaseAgent):
            name = "minimal"

            def get_system_prompt(self):
                # Call parent to test NotImplementedError
                super().get_system_prompt()

            async def process(self, task, context=None, previous_output=None):
                super().process(task, context, previous_output)

        router = MagicMock()
        memory = MagicMock()
        agent = MinimalAgent(router, memory)

        # These should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            agent.get_system_prompt()


class TestAgentCallbacks:
    """Test agent callback functionality."""

    @pytest.fixture
    def concrete_agent(self):
        """Create a concrete agent implementation for testing."""
        class TestAgent(BaseAgent):
            name = "test"

            def get_system_prompt(self):
                return "Test prompt"

            async def process(self, task, context=None, previous_output=None):
                return AgentOutput(content="Test output")

        return TestAgent(MagicMock(), MagicMock())

    def test_register_callback(self, concrete_agent):
        """Test registering a status callback."""
        callback = MagicMock()
        concrete_agent.register_callback(callback)

        assert callback in concrete_agent._callbacks

    def test_unregister_callback(self, concrete_agent):
        """Test unregistering a status callback."""
        callback = MagicMock()
        concrete_agent.register_callback(callback)
        concrete_agent.unregister_callback(callback)

        assert callback not in concrete_agent._callbacks

    def test_status_change_notifies_callbacks(self, concrete_agent):
        """Test that status changes notify callbacks."""
        callback = MagicMock()
        concrete_agent.register_callback(callback)

        concrete_agent.status = AgentStatus.WORKING

        callback.assert_called_once()

    def test_get_status_dict(self, concrete_agent):
        """Test getting agent status as dictionary."""
        status = concrete_agent.get_status_dict()

        assert status["name"] == "test"
        assert status["status"] == "idle"
        assert "description" in status
        assert "icon" in status
        assert "color" in status
