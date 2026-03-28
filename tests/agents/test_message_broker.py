"""Tests for atlas.agents.message_broker module."""

import pytest
import asyncio
from datetime import datetime

from atlas.agents.message_broker import (
    MessageType,
    AgentMessage,
    BuildStatus,
    AgentPosition,
    MessageBroker,
    get_broker,
    remove_broker,
)


class TestMessageType:
    """Tests for MessageType enum."""

    def test_original_message_types(self):
        """Test that original message types exist."""
        assert MessageType.SYSTEM.value == "system"
        assert MessageType.DISCUSSION.value == "discussion"
        assert MessageType.DECISION.value == "decision"
        assert MessageType.QC_REPORT.value == "qc_report"

    def test_new_streaming_types(self):
        """Test new streaming message types."""
        assert MessageType.TYPING.value == "typing"
        assert MessageType.TYPING_STOP.value == "typing_stop"
        assert MessageType.TEXT_CHUNK.value == "text_chunk"

    def test_user_message_type(self):
        """Test user message type."""
        assert MessageType.USER.value == "user"

    def test_interruption_type(self):
        """Test interruption message type."""
        assert MessageType.INTERRUPTION.value == "interruption"

    def test_position_change_type(self):
        """Test position change message type."""
        assert MessageType.POSITION_CHANGE.value == "position_change"


class TestAgentMessage:
    """Tests for AgentMessage dataclass."""

    def test_create_basic_message(self):
        """Test creating a basic message."""
        msg = AgentMessage(
            sender="planner",
            content="Let's discuss the layout",
        )
        assert msg.sender == "planner"
        assert msg.content == "Let's discuss the layout"
        assert msg.message_type == MessageType.DISCUSSION  # default
        assert msg.recipient is None  # broadcast by default

    def test_create_typed_message(self):
        """Test creating a message with specific type."""
        msg = AgentMessage(
            sender="qc",
            content="I have concerns",
            message_type=MessageType.CONCERN,
        )
        assert msg.message_type == MessageType.CONCERN

    def test_create_directed_message(self):
        """Test creating a message to specific recipient."""
        msg = AgentMessage(
            sender="director",
            content="What do you think?",
            recipient="expert_fitness",
        )
        assert msg.recipient == "expert_fitness"

    def test_to_dict(self):
        """Test converting message to dict."""
        msg = AgentMessage(
            sender="planner",
            content="Test content",
            message_type=MessageType.DECISION,
            metadata={"key": "value"},
        )
        d = msg.to_dict()
        
        assert d["sender"] == "planner"
        assert d["content"] == "Test content"
        assert d["message_type"] == "decision"
        assert d["metadata"]["key"] == "value"
        assert "timestamp" in d

    def test_to_json(self):
        """Test converting message to JSON."""
        msg = AgentMessage(sender="test", content="Hello")
        json_str = msg.to_json()
        
        import json
        parsed = json.loads(json_str)
        assert parsed["sender"] == "test"
        assert parsed["content"] == "Hello"

    def test_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated."""
        msg = AgentMessage(sender="test", content="test")
        assert msg.timestamp is not None
        assert isinstance(msg.timestamp, datetime)


class TestBuildStatus:
    """Tests for BuildStatus dataclass."""

    def test_create_status(self):
        """Test creating a build status."""
        status = BuildStatus(
            phase="debate",
            progress=45,
            current_action="Discussing layout",
            agent="planner",
        )
        assert status.phase == "debate"
        assert status.progress == 45
        assert status.current_action == "Discussing layout"

    def test_to_dict(self):
        """Test converting status to dict."""
        status = BuildStatus(
            phase="build",
            progress=80,
            current_action="Building",
            agent="builder",
        )
        d = status.to_dict()
        
        assert d["type"] == "status_update"
        assert d["phase"] == "build"
        assert d["progress"] == 80


class TestAgentPosition:
    """Tests for AgentPosition dataclass."""

    def test_create_position(self):
        """Test creating a position."""
        pos = AgentPosition(
            agent_id="planner",
            topic="Database choice",
            position="Use PostgreSQL",
            confidence=0.9,
        )
        assert pos.agent_id == "planner"
        assert pos.topic == "Database choice"
        assert pos.confidence == 0.9

    def test_position_with_change(self):
        """Test position that tracks a change."""
        pos = AgentPosition(
            agent_id="qc",
            topic="Framework",
            position="React",
            changed_from="Vue",
        )
        assert pos.changed_from == "Vue"

    def test_to_dict(self):
        """Test converting position to dict."""
        pos = AgentPosition(
            agent_id="expert",
            topic="API design",
            position="REST",
        )
        d = pos.to_dict()
        
        assert d["agent_id"] == "expert"
        assert d["topic"] == "API design"
        assert "timestamp" in d


class TestMessageBroker:
    """Tests for MessageBroker class."""

    @pytest.fixture
    def broker(self):
        """Create a fresh broker."""
        return MessageBroker(project_id=999)

    @pytest.mark.asyncio
    async def test_send_broadcast(self, broker):
        """Test broadcasting a message."""
        received = []
        
        async def callback(msg):
            received.append(msg)
        
        broker.subscribe_agent("agent1", callback)
        broker.subscribe_agent("agent2", callback)
        
        msg = AgentMessage(sender="director", content="Hello all")
        await broker.send(msg)
        
        # Both agents should receive (except sender if subscribed)
        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_send_directed(self, broker):
        """Test sending to specific agent."""
        received_1 = []
        received_2 = []
        
        async def callback1(msg):
            received_1.append(msg)
        
        async def callback2(msg):
            received_2.append(msg)
        
        broker.subscribe_agent("agent1", callback1)
        broker.subscribe_agent("agent2", callback2)
        
        msg = AgentMessage(
            sender="director",
            content="Just for you",
            recipient="agent1",
        )
        await broker.send(msg)
        
        assert len(received_1) == 1
        assert len(received_2) == 0

    @pytest.mark.asyncio
    async def test_history_tracking(self, broker):
        """Test that messages are tracked in history."""
        await broker.send(AgentMessage(sender="a", content="First"))
        await broker.send(AgentMessage(sender="b", content="Second"))
        
        history = broker.get_history()
        assert len(history) == 2
        assert history[0].content == "First"
        assert history[1].content == "Second"

    def test_get_recent(self, broker):
        """Test getting recent messages."""
        # Manually add to history for sync test
        for i in range(10):
            broker.messages.append(
                AgentMessage(sender="test", content=f"Message {i}")
            )
        
        recent = broker.get_recent(5)
        assert len(recent) == 5
        assert recent[-1].content == "Message 9"

    @pytest.mark.asyncio
    async def test_push_typing(self, broker):
        """Test pushing typing indicator."""
        received = []
        
        async def ui_callback(msg):
            received.append(msg)
        
        broker.subscribe_ui(ui_callback)
        
        await broker.push_typing("planner", True)
        assert "planner" in broker.typing_agents
        assert len(received) == 1
        assert received[0]["type"] == "typing"
        
        await broker.push_typing("planner", False)
        assert "planner" not in broker.typing_agents
        assert received[1]["type"] == "typing_stop"

    @pytest.mark.asyncio
    async def test_push_text_chunk(self, broker):
        """Test pushing text chunk for streaming."""
        received = []
        
        async def ui_callback(msg):
            received.append(msg)
        
        broker.subscribe_ui(ui_callback)
        
        await broker.push_text_chunk("planner", "Hello ")
        await broker.push_text_chunk("planner", "world!")
        
        assert len(received) == 2
        assert received[0]["type"] == "text_chunk"
        assert received[0]["text"] == "Hello "
        assert received[1]["text"] == "world!"

    def test_update_position(self, broker):
        """Test updating agent position."""
        pos = broker.update_position(
            agent_id="planner",
            topic="Layout",
            position="Use grid",
            confidence=0.8,
        )
        
        assert pos.agent_id == "planner"
        assert pos.topic == "Layout"
        
        positions = broker.get_positions_for_topic("Layout")
        assert len(positions) == 1

    def test_update_position_replaces_old(self, broker):
        """Test that updating position replaces old one."""
        broker.update_position("planner", "Topic", "Position 1")
        broker.update_position("planner", "Topic", "Position 2")
        
        positions = broker.get_positions_for_topic("Topic")
        assert len(positions) == 1
        assert positions[0].position == "Position 2"

    def test_get_agent_position(self, broker):
        """Test getting specific agent's position."""
        broker.update_position("planner", "Topic", "Planner's view")
        broker.update_position("qc", "Topic", "QC's view")
        
        pos = broker.get_agent_position("qc", "Topic")
        assert pos.position == "QC's view"

    def test_check_consensus_no_positions(self, broker):
        """Test consensus check with no positions."""
        has_consensus, position = broker.check_consensus("Unknown topic")
        assert has_consensus is False
        assert position is None

    def test_check_consensus_single_position(self, broker):
        """Test consensus check with only one position."""
        broker.update_position("planner", "Topic", "Only view")
        
        has_consensus, _ = broker.check_consensus("Topic")
        assert has_consensus is False  # Need at least 2 for consensus

    def test_subscribe_unsubscribe_agent(self, broker):
        """Test agent subscription management."""
        callback = lambda msg: None
        
        broker.subscribe_agent("test_agent", callback)
        assert "test_agent" in broker.subscribers
        
        broker.unsubscribe_agent("test_agent")
        assert "test_agent" not in broker.subscribers

    def test_subscribe_unsubscribe_ui(self, broker):
        """Test UI subscription management."""
        callback = lambda msg: None
        
        broker.subscribe_ui(callback)
        assert callback in broker.ui_callbacks
        
        broker.unsubscribe_ui(callback)
        assert callback not in broker.ui_callbacks

    def test_clear_history(self, broker):
        """Test clearing message history."""
        broker.messages.append(AgentMessage(sender="test", content="test"))
        assert len(broker.messages) > 0
        
        broker.clear()
        assert len(broker.messages) == 0


class TestGetBroker:
    """Tests for get_broker function."""

    def test_get_broker_returns_same_instance(self):
        """Test that get_broker returns cached instance."""
        broker1 = get_broker(12345)
        broker2 = get_broker(12345)
        
        assert broker1 is broker2

    def test_get_broker_different_projects(self):
        """Test that different projects get different brokers."""
        broker1 = get_broker(11111)
        broker2 = get_broker(22222)
        
        assert broker1 is not broker2
        assert broker1.project_id == 11111
        assert broker2.project_id == 22222


class TestRemoveBroker:
    """Tests for remove_broker function."""

    def test_remove_broker(self):
        """Test removing a broker from cache."""
        broker1 = get_broker(99999)
        remove_broker(99999)
        broker2 = get_broker(99999)
        
        assert broker1 is not broker2
