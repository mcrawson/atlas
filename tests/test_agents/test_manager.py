"""Integration tests for AgentManager workflow orchestration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from atlas.agents.manager import AgentManager, WorkflowMode, WorkflowEvent
from atlas.agents.base import AgentOutput, AgentStatus


class TestAgentManager:
    """Test suite for AgentManager class."""

    @pytest.fixture
    def mock_router(self):
        """Create a mock router."""
        router = MagicMock()
        router.route.return_value = {
            "provider": "openai",
            "task_type": "code",
            "reason": "Test routing",
        }
        return router

    @pytest.fixture
    def mock_memory(self):
        """Create a mock memory manager."""
        memory = MagicMock()
        memory.save_conversation = MagicMock()
        return memory

    @pytest.fixture
    def mock_providers(self):
        """Create mock providers."""
        provider = MagicMock()
        provider.is_available.return_value = True
        provider.generate = AsyncMock(return_value="Mock response")
        return {"openai": provider}

    @pytest.fixture
    def manager(self, mock_router, mock_memory, mock_providers):
        """Create an AgentManager with mocked dependencies."""
        return AgentManager(mock_router, mock_memory, mock_providers)

    def test_initialization(self, manager):
        """Test that manager initializes with all agents."""
        assert manager.architect is not None
        assert manager.mason is not None
        assert manager.oracle is not None

    def test_get_all_status(self, manager):
        """Test getting status of all agents."""
        status = manager.get_all_status()

        assert "architect" in status
        assert "mason" in status
        assert "oracle" in status

        for agent_name, agent_status in status.items():
            assert "name" in agent_status
            assert "status" in agent_status

    def test_event_callback_registration(self, manager):
        """Test registering and unregistering event callbacks."""
        events = []

        def callback(event):
            events.append(event)

        manager.register_event_callback(callback)
        assert callback in manager._event_callbacks

        manager.unregister_event_callback(callback)
        assert callback not in manager._event_callbacks

    def test_workflow_modes_exist(self):
        """Test that all workflow modes are defined."""
        assert WorkflowMode.SEQUENTIAL
        assert WorkflowMode.DIRECT_BUILD
        assert WorkflowMode.VERIFY_ONLY
        assert WorkflowMode.SPEC_DRIVEN

    def test_max_revisions_constant(self, manager):
        """Test that MAX_REVISIONS is set."""
        assert manager.MAX_REVISIONS == 3


class TestWorkflowExecution:
    """Test workflow execution methods."""

    @pytest.fixture
    def manager_with_mock_agents(self, mock_router, mock_memory, mock_providers):
        """Create manager with mocked agent process methods."""
        manager = AgentManager(mock_router, mock_memory, mock_providers)

        # Mock architect output
        architect_output = AgentOutput(
            content="Plan: Build a fibonacci function",
            status=AgentStatus.COMPLETED,
            next_agent="mason",
            metadata={"agent": "architect"},
        )
        manager.architect.process = AsyncMock(return_value=architect_output)

        # Mock mason output
        mason_output = AgentOutput(
            content="def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
            status=AgentStatus.COMPLETED,
            next_agent="oracle",
            artifacts={"code": "fibonacci.py"},
            metadata={"agent": "mason"},
        )
        manager.mason.process = AsyncMock(return_value=mason_output)

        # Mock oracle output (approval)
        oracle_output = AgentOutput(
            content="Code review passed. Implementation is correct.",
            status=AgentStatus.COMPLETED,
            metadata={"agent": "oracle", "verdict": "APPROVED", "needs_revision": False},
        )
        manager.oracle.process = AsyncMock(return_value=oracle_output)

        return manager

    @pytest.fixture
    def mock_router(self):
        router = MagicMock()
        router.route.return_value = {"provider": "openai", "task_type": "code", "reason": "Test"}
        return router

    @pytest.fixture
    def mock_memory(self):
        return MagicMock()

    @pytest.fixture
    def mock_providers(self):
        provider = MagicMock()
        provider.is_available.return_value = True
        provider.generate = AsyncMock(return_value="Mock response")
        return {"openai": provider}

    @pytest.mark.asyncio
    async def test_sequential_workflow(self, manager_with_mock_agents):
        """Test full sequential workflow execution."""
        manager = manager_with_mock_agents

        outputs = await manager.execute_workflow(
            task="Create a fibonacci function",
            mode=WorkflowMode.SEQUENTIAL,
        )

        # Should have called all three agents
        manager.architect.process.assert_called_once()
        manager.mason.process.assert_called()
        manager.oracle.process.assert_called()

        # Should have outputs for all agents
        assert "architect" in outputs
        assert "mason" in outputs
        assert "oracle" in outputs

    @pytest.mark.asyncio
    async def test_direct_build_workflow(self, manager_with_mock_agents):
        """Test direct build workflow (skips architect)."""
        manager = manager_with_mock_agents

        outputs = await manager.execute_workflow(
            task="Create a simple function",
            mode=WorkflowMode.DIRECT_BUILD,
        )

        # Should NOT have called architect
        manager.architect.process.assert_not_called()

        # Should have called mason and oracle
        manager.mason.process.assert_called_once()
        manager.oracle.process.assert_called_once()

        assert "mason" in outputs
        assert "oracle" in outputs

    @pytest.mark.asyncio
    async def test_verify_only_workflow(self, manager_with_mock_agents):
        """Test verify-only workflow (oracle only)."""
        manager = manager_with_mock_agents

        outputs = await manager.execute_workflow(
            task="Review this code",
            mode=WorkflowMode.VERIFY_ONLY,
        )

        # Should only have called oracle
        manager.architect.process.assert_not_called()
        manager.mason.process.assert_not_called()
        manager.oracle.process.assert_called_once()

        assert "oracle" in outputs

    @pytest.mark.asyncio
    async def test_workflow_emits_events(self, manager_with_mock_agents):
        """Test that workflow emits proper events."""
        manager = manager_with_mock_agents
        events = []

        def collect_events(event):
            events.append(event)

        manager.register_event_callback(collect_events)

        await manager.execute_workflow(
            task="Test task",
            mode=WorkflowMode.SEQUENTIAL,
        )

        # Should have workflow_start and workflow_complete events
        event_types = [e.event_type for e in events]
        assert "workflow_start" in event_types
        assert "workflow_complete" in event_types

        # Should have agent events
        assert any("agent_start" in et for et in event_types)
        assert any("agent_complete" in et for et in event_types)


class TestRevisionLoop:
    """Test the revision loop when Oracle rejects."""

    @pytest.fixture
    def mock_router(self):
        router = MagicMock()
        router.route.return_value = {"provider": "openai", "task_type": "code", "reason": "Test"}
        return router

    @pytest.fixture
    def mock_memory(self):
        return MagicMock()

    @pytest.fixture
    def mock_providers(self):
        provider = MagicMock()
        provider.is_available.return_value = True
        provider.generate = AsyncMock(return_value="Mock response")
        return {"openai": provider}

    @pytest.mark.asyncio
    async def test_revision_loop_on_rejection(self, mock_router, mock_memory, mock_providers):
        """Test that mason revises when oracle rejects."""
        manager = AgentManager(mock_router, mock_memory, mock_providers)

        # Architect output
        architect_output = AgentOutput(
            content="Plan",
            status=AgentStatus.COMPLETED,
            next_agent="mason",
        )
        manager.architect.process = AsyncMock(return_value=architect_output)

        # Mason outputs
        mason_output = AgentOutput(
            content="First attempt",
            status=AgentStatus.COMPLETED,
            next_agent="oracle",
        )
        manager.mason.process = AsyncMock(return_value=mason_output)

        # Oracle: reject first, then approve
        oracle_reject = AgentOutput(
            content="Needs work",
            status=AgentStatus.COMPLETED,
            metadata={"verdict": "NEEDS_REVISION", "needs_revision": True},
        )
        oracle_approve = AgentOutput(
            content="Approved",
            status=AgentStatus.COMPLETED,
            metadata={"verdict": "APPROVED", "needs_revision": False},
        )
        manager.oracle.process = AsyncMock(side_effect=[oracle_reject, oracle_approve])

        outputs = await manager.execute_workflow(
            task="Test task",
            mode=WorkflowMode.SEQUENTIAL,
        )

        # Mason should have been called twice (original + revision)
        assert manager.mason.process.call_count == 2

        # Oracle should have been called twice
        assert manager.oracle.process.call_count == 2

    @pytest.mark.asyncio
    async def test_max_revisions_limit(self, mock_router, mock_memory, mock_providers):
        """Test that revision loop stops at MAX_REVISIONS."""
        manager = AgentManager(mock_router, mock_memory, mock_providers)

        # Architect output
        architect_output = AgentOutput(
            content="Plan",
            status=AgentStatus.COMPLETED,
        )
        manager.architect.process = AsyncMock(return_value=architect_output)

        # Mason always produces output
        mason_output = AgentOutput(
            content="Attempt",
            status=AgentStatus.COMPLETED,
        )
        manager.mason.process = AsyncMock(return_value=mason_output)

        # Oracle always rejects
        oracle_reject = AgentOutput(
            content="Rejected",
            status=AgentStatus.COMPLETED,
            metadata={"verdict": "NEEDS_REVISION", "needs_revision": True},
        )
        manager.oracle.process = AsyncMock(return_value=oracle_reject)

        outputs = await manager.execute_workflow(
            task="Test task",
            mode=WorkflowMode.SEQUENTIAL,
        )

        # Should stop after MAX_REVISIONS + 1 attempts
        expected_calls = manager.MAX_REVISIONS + 1
        assert manager.mason.process.call_count == expected_calls
        assert manager.oracle.process.call_count == expected_calls


class TestWorkflowEvent:
    """Test WorkflowEvent dataclass."""

    def test_event_creation(self):
        """Test creating a workflow event."""
        event = WorkflowEvent(
            event_type="agent_start",
            agent_name="architect",
            data={"task": "Test"},
        )

        assert event.event_type == "agent_start"
        assert event.agent_name == "architect"
        assert event.data == {"task": "Test"}
        assert event.timestamp is not None

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = WorkflowEvent(
            event_type="workflow_complete",
            agent_name=None,
            data={"success": True},
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == "workflow_complete"
        assert event_dict["agent_name"] is None
        assert event_dict["data"] == {"success": True}
        assert "timestamp" in event_dict
