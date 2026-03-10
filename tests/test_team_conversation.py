"""Tests for team conversation module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from atlas.agents.team_conversation import (
    TeamConversation,
    TeamMessage,
    AgentConcern,
)


class TestTeamConversationModes:
    """Test conversation mode initialization."""

    def test_default_mode_is_free_form(self):
        """Test that default mode is free_form."""
        conv = TeamConversation()
        assert conv.mode == "free_form"

    def test_round_table_mode_initialization(self):
        """Test round_table mode initialization."""
        conv = TeamConversation(mode="round_table")
        assert conv.mode == "round_table"
        assert conv.current_agent_index == 0
        assert conv.agents_with_concerns == []
        assert conv.agent_concerns_map == {}


class TestRoundTableState:
    """Test round-table state management."""

    @pytest.fixture
    def round_table_conv(self):
        """Create a round-table conversation with concerns."""
        conv = TeamConversation(mode="round_table")

        # Set up agents with concerns
        conv.agents_with_concerns = ["tinker", "oracle", "architect"]
        conv.agent_concerns_map = {
            "tinker": ["tinker_1", "tinker_2"],
            "oracle": ["oracle_1"],
            "architect": ["architect_1", "architect_2"],
        }

        # Create concerns
        conv.concerns = {
            "tinker_1": AgentConcern(
                agent="tinker",
                category="implementation",
                severity="important",
                question="How will error handling work?",
                context="Need to define error flows",
            ),
            "tinker_2": AgentConcern(
                agent="tinker",
                category="testing",
                severity="minor",
                question="What test framework?",
                context="Need to pick testing tools",
            ),
            "oracle_1": AgentConcern(
                agent="oracle",
                category="risk",
                severity="critical",
                question="What about security?",
                context="Security is critical",
            ),
            "architect_1": AgentConcern(
                agent="architect",
                category="architecture",
                severity="important",
                question="Monolith or microservices?",
                context="Architecture decision needed",
            ),
            "architect_2": AgentConcern(
                agent="architect",
                category="scalability",
                severity="minor",
                question="Expected load?",
                context="For capacity planning",
            ),
        }

        return conv

    def test_current_agent(self, round_table_conv):
        """Test current_agent property."""
        assert round_table_conv.current_agent == "tinker"

    def test_current_agent_after_advance(self, round_table_conv):
        """Test current_agent after advancing."""
        # Mark tinker's concerns as addressed
        round_table_conv.concerns["tinker_1"].status = "addressed"
        round_table_conv.concerns["tinker_2"].status = "addressed"

        # Advance
        next_agent = round_table_conv.advance_to_next_agent()
        assert next_agent == "oracle"

    def test_get_agent_open_concerns(self, round_table_conv):
        """Test getting open concerns for an agent."""
        concerns = round_table_conv.get_agent_open_concerns("tinker")
        assert len(concerns) == 2

        # Address one
        round_table_conv.concerns["tinker_1"].status = "addressed"
        concerns = round_table_conv.get_agent_open_concerns("tinker")
        assert len(concerns) == 1

    def test_advance_skips_resolved_agents(self, round_table_conv):
        """Test that advance skips agents with no open concerns."""
        # Mark all tinker and oracle concerns as addressed
        round_table_conv.concerns["tinker_1"].status = "addressed"
        round_table_conv.concerns["tinker_2"].status = "addressed"
        round_table_conv.concerns["oracle_1"].status = "addressed"

        # Should skip to architect
        next_agent = round_table_conv.advance_to_next_agent()
        assert next_agent == "architect"

    def test_advance_returns_none_when_done(self, round_table_conv):
        """Test advance returns None when all agents done."""
        # Mark all concerns as addressed
        for concern in round_table_conv.concerns.values():
            concern.status = "addressed"

        next_agent = round_table_conv.advance_to_next_agent()
        assert next_agent is None


class TestGetState:
    """Test get_state method."""

    def test_get_state_free_form(self):
        """Test get_state for free_form mode."""
        conv = TeamConversation(mode="free_form")
        conv.concerns = {
            "test_1": AgentConcern(
                agent="tinker",
                category="test",
                severity="important",
                question="Test?",
                context="",
            ),
        }

        state = conv.get_state()
        assert state["mode"] == "free_form"
        assert "current_speaker" not in state
        assert "agents_order" not in state

    def test_get_state_round_table(self):
        """Test get_state includes round-table info."""
        conv = TeamConversation(mode="round_table")
        conv.agents_with_concerns = ["tinker", "oracle"]
        conv.agent_concerns_map = {
            "tinker": ["t1"],
            "oracle": ["o1"],
        }
        conv.concerns = {
            "t1": AgentConcern(
                agent="tinker",
                category="test",
                severity="important",
                question="Test?",
                context="",
            ),
            "o1": AgentConcern(
                agent="oracle",
                category="risk",
                severity="critical",
                question="Risk?",
                context="",
            ),
        }

        state = conv.get_state()
        assert state["mode"] == "round_table"
        assert "current_speaker" in state
        assert state["current_speaker"]["agent"] == "tinker"
        assert "agents_order" in state
        assert len(state["agents_order"]) == 2


class TestSerialization:
    """Test serialization and deserialization."""

    def test_to_dict_includes_mode(self):
        """Test that to_dict includes mode."""
        conv = TeamConversation(mode="round_table")
        data = conv.to_dict()
        assert data["mode"] == "round_table"

    def test_to_dict_includes_round_table_state(self):
        """Test that to_dict includes round-table state."""
        conv = TeamConversation(mode="round_table")
        conv.agents_with_concerns = ["tinker", "oracle"]
        conv.current_agent_index = 1
        conv.agent_concerns_map = {"tinker": ["t1"], "oracle": ["o1"]}

        data = conv.to_dict()
        assert "round_table" in data
        assert data["round_table"]["current_agent_index"] == 1
        assert data["round_table"]["agents_with_concerns"] == ["tinker", "oracle"]

    def test_from_dict_restores_mode(self):
        """Test that from_dict restores mode."""
        data = {
            "messages": [],
            "concerns": {},
            "is_complete": False,
            "summary": "",
            "project_name": "test",
            "mode": "round_table",
            "round_table": {
                "current_agent_index": 1,
                "agents_with_concerns": ["tinker", "oracle"],
                "agent_concerns_map": {"tinker": ["t1"], "oracle": ["o1"]},
            },
        }

        conv = TeamConversation.from_dict(data)
        assert conv.mode == "round_table"
        assert conv.current_agent_index == 1
        assert conv.agents_with_concerns == ["tinker", "oracle"]

    def test_from_dict_defaults_to_free_form(self):
        """Test that from_dict defaults to free_form mode."""
        data = {
            "messages": [],
            "concerns": {},
            "is_complete": False,
            "summary": "",
            "project_name": "test",
        }

        conv = TeamConversation.from_dict(data)
        assert conv.mode == "free_form"


class TestAgentOrder:
    """Test agent ordering."""

    def test_agent_order_defined(self):
        """Test that AGENT_ORDER is defined."""
        assert TeamConversation.AGENT_ORDER == ["tinker", "oracle", "architect", "launch", "finisher"]

    def test_agents_info_defined(self):
        """Test that AGENTS info is defined."""
        agents = TeamConversation.AGENTS
        assert "tinker" in agents
        assert "oracle" in agents
        assert "architect" in agents
        assert "launch" in agents

        # Check structure
        for agent, info in agents.items():
            assert "name" in info
            assert "icon" in info
            assert "role" in info
            assert "focus" in info


class TestTeamMessage:
    """Test TeamMessage dataclass."""

    def test_create_message(self):
        """Test creating a team message."""
        msg = TeamMessage(
            role="tinker",
            content="Test message",
        )
        assert msg.role == "tinker"
        assert msg.content == "Test message"
        assert msg.timestamp == ""
        assert msg.concern_ids == []

    def test_message_to_dict(self):
        """Test message serialization."""
        msg = TeamMessage(
            role="user",
            content="Hello",
            timestamp="2024-01-01T00:00:00",
            concern_ids=["t1", "t2"],
        )
        data = msg.to_dict()
        assert data["role"] == "user"
        assert data["content"] == "Hello"
        assert data["timestamp"] == "2024-01-01T00:00:00"
        assert data["concern_ids"] == ["t1", "t2"]


class TestAgentConcern:
    """Test AgentConcern dataclass."""

    def test_create_concern(self):
        """Test creating an agent concern."""
        concern = AgentConcern(
            agent="oracle",
            category="risk",
            severity="critical",
            question="What about security?",
            context="Need to address security early",
        )
        assert concern.agent == "oracle"
        assert concern.category == "risk"
        assert concern.severity == "critical"
        assert concern.status == "open"
        assert concern.resolution == ""

    def test_concern_status_changes(self):
        """Test concern status can change."""
        concern = AgentConcern(
            agent="tinker",
            category="test",
            severity="minor",
            question="Test?",
            context="",
        )
        assert concern.status == "open"

        concern.status = "addressed"
        assert concern.status == "addressed"

        concern.status = "resolved"
        assert concern.status == "resolved"
