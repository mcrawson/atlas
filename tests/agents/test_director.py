"""Tests for atlas.agents.director module."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

from atlas.agents.director import (
    BuildPhase,
    ConversationState,
    AgentState,
    DirectorAgent,
    run_director,
)
from atlas.agents.message_broker import MessageBroker, get_broker, remove_broker
from atlas.agents.personalities import PLANNER_PERSONALITY, QC_PERSONALITY


@dataclass
class MockProject:
    """Mock project for testing."""
    id: int = 123
    name: str = "Test Project"
    description: str = "A test project"


@dataclass
class MockBrief:
    """Mock business brief for testing."""
    product_name: str = "Test Product"
    product_type: str = "printable"
    executive_summary: str = "A test product summary"
    target_customer: dict = None
    success_criteria: list = None

    def __post_init__(self):
        if self.target_customer is None:
            self.target_customer = {"description": "Test customer"}
        if self.success_criteria is None:
            self.success_criteria = [{"criterion": "Works well"}]

    def to_dict(self):
        return {
            "product_name": self.product_name,
            "product_type": self.product_type,
            "executive_summary": self.executive_summary,
        }


class TestBuildPhase:
    """Tests for BuildPhase enum."""

    def test_phase_values(self):
        """Test that all phases have expected values."""
        assert BuildPhase.KICKOFF.value == "kickoff"
        assert BuildPhase.DEBATE.value == "debate"
        assert BuildPhase.BUILD.value == "build"
        assert BuildPhase.REVIEW.value == "review"
        assert BuildPhase.COMPLETE.value == "complete"

    def test_phase_ordering(self):
        """Test that phases can be compared."""
        phases = [BuildPhase.KICKOFF, BuildPhase.DEBATE, BuildPhase.BUILD, 
                  BuildPhase.REVIEW, BuildPhase.COMPLETE]
        assert len(phases) == 5


class TestConversationState:
    """Tests for ConversationState dataclass."""

    def test_default_state(self):
        """Test default conversation state."""
        state = ConversationState()
        assert state.phase == BuildPhase.KICKOFF
        assert state.turns == 0
        assert state.consensus is False
        assert state.topics_discussed == []
        assert state.current_topic is None

    def test_state_mutation(self):
        """Test mutating state."""
        state = ConversationState()
        state.phase = BuildPhase.DEBATE
        state.turns = 5
        state.consensus = True
        state.topics_discussed.append("Topic 1")
        
        assert state.phase == BuildPhase.DEBATE
        assert state.turns == 5
        assert len(state.topics_discussed) == 1


class TestAgentState:
    """Tests for AgentState dataclass."""

    def test_create_agent_state(self):
        """Test creating agent state."""
        state = AgentState(
            agent_id="planner",
            name="Planner",
            personality=PLANNER_PERSONALITY,
        )
        assert state.agent_id == "planner"
        assert state.name == "Planner"
        assert state.turns_since_spoke == 0
        assert state.is_typing is False

    def test_agent_state_with_position(self):
        """Test agent state with current position."""
        state = AgentState(
            agent_id="qc",
            name="QC",
            personality=QC_PERSONALITY,
            current_position="Use tabs for navigation",
        )
        assert state.current_position == "Use tabs for navigation"


class TestDirectorAgent:
    """Tests for DirectorAgent class."""

    @pytest.fixture
    def mock_project(self):
        """Create a mock project."""
        return MockProject()

    @pytest.fixture
    def mock_brief(self):
        """Create a mock brief."""
        return MockBrief()

    @pytest.fixture
    def director(self, mock_project):
        """Create a director with mocked dependencies."""
        # Clean up any existing broker
        remove_broker(mock_project.id)
        return DirectorAgent(mock_project)

    def test_init(self, director, mock_project):
        """Test director initialization."""
        assert director.project_id == mock_project.id
        assert director.agent_id == "director"
        assert director.state.phase == BuildPhase.KICKOFF
        assert director.brief is None

    def test_init_creates_broker(self, director, mock_project):
        """Test that director creates message broker."""
        broker = get_broker(mock_project.id)
        assert broker is not None
        assert broker.project_id == mock_project.id

    def test_init_subscribes_to_broker(self, director, mock_project):
        """Test that director subscribes to broker."""
        broker = get_broker(mock_project.id)
        assert "director" in broker.subscribers

    @pytest.mark.asyncio
    async def test_say_broadcasts_message(self, director):
        """Test that _say broadcasts message."""
        received = []
        
        async def ui_callback(msg):
            received.append(msg)
        
        director.broker.subscribe_ui(ui_callback)
        
        await director._say("director", "Test message")
        
        # Should have received the message
        assert len(received) >= 1
        assert any(m.get("content") == "Test message" for m in received)

    @pytest.mark.asyncio
    async def test_say_updates_history(self, director):
        """Test that _say updates conversation history."""
        initial_len = len(director.conversation_history)
        await director._say("planner", "Test message")

        # History should have grown (may be added multiple times via callback)
        assert len(director.conversation_history) > initial_len
        # Should contain our message
        assert any(
            h["sender"] == "planner" and h["content"] == "Test message"
            for h in director.conversation_history
        )

    @pytest.mark.asyncio
    async def test_generate_without_llm(self, director):
        """Test _generate returns fallback without LLM."""
        # Mock _get_llm to return None (even if API key exists)
        director._get_llm = AsyncMock(return_value=None)
        director._llm = None

        result = await director._generate("Test Agent", "test role", "test prompt")

        assert "Test Agent" in result or "thoughts" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_with_mock_llm(self, director):
        """Test _generate with mocked LLM."""
        # Mock the LLM
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Mocked response"
        
        mock_llm = AsyncMock()
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)
        director._llm = mock_llm
        
        result = await director._generate(
            "Planner",
            "planning specialist",
            "What should we build?",
            stream=False
        )
        
        assert result == "Mocked response"

    @pytest.mark.asyncio
    async def test_handle_user_message(self, director, mock_brief):
        """Test handling user message."""
        director.brief = mock_brief
        
        # Mock _generate to avoid LLM call
        director._generate = AsyncMock(return_value="Agent response")
        
        received = []
        async def ui_callback(msg):
            received.append(msg)
        director.broker.subscribe_ui(ui_callback)
        
        await director.handle_user_message("I have a question")
        
        # Should broadcast user message
        user_msgs = [m for m in received if m.get("sender") == "user"]
        assert len(user_msgs) >= 1

    @pytest.mark.asyncio
    async def test_route_user_message_to_qc(self, director, mock_brief):
        """Test routing user message about quality to QC."""
        director.brief = mock_brief
        director._generate = AsyncMock(return_value="QC response")
        
        await director._route_user_message("I have concerns about quality")
        
        # Should have called generate with QC
        call_args = director._generate.call_args
        assert "QC" in str(call_args) or "quality" in str(call_args)

    @pytest.mark.asyncio
    async def test_route_user_message_to_planner(self, director, mock_brief):
        """Test routing user message about planning to Planner."""
        director.brief = mock_brief
        director._generate = AsyncMock(return_value="Planner response")
        
        await director._route_user_message("How should we structure the layout?")
        
        call_args = director._generate.call_args
        assert "Planner" in str(call_args) or "plan" in str(call_args)

    def test_get_role_description(self, director):
        """Test getting role descriptions."""
        assert "orchestrator" in director._get_role_description("director")
        assert "planning" in director._get_role_description("planner")
        assert "quality" in director._get_role_description("qc")

    @pytest.mark.asyncio
    async def test_check_consensus_too_early(self, director):
        """Test consensus check returns false early in debate."""
        director.state.topic_turn_count = 1
        
        result = await director._check_consensus("Test topic")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_consensus_with_agreement(self, director):
        """Test consensus detection with agreement markers."""
        director.state.topic_turn_count = 5
        director.conversation_history = [
            {"sender": "planner", "content": "I think we should use tabs"},
            {"sender": "qc", "content": "That sounds good to me"},
            {"sender": "expert", "content": "I agree, tabs make sense"},
            {"sender": "planner", "content": "Good point, let's go with tabs"},
            {"sender": "qc", "content": "Yes, exactly right"},
            {"sender": "director", "content": "We have agreement"},
        ]
        
        result = await director._check_consensus("Navigation")
        assert result is True

    @pytest.mark.asyncio
    async def test_generate_topics_fallback(self, director):
        """Test topic generation falls back without LLM."""
        director._llm = None
        
        topics = await director._generate_topics()
        
        assert len(topics) >= 3
        assert any("structure" in t.lower() for t in topics)

    @pytest.mark.asyncio
    async def test_summarize_debate(self, director):
        """Test debate summarization."""
        director.conversation_history = [
            {"sender": "planner", "content": "Use grid layout", "message_type": "discussion"},
            {"sender": "qc", "content": "Add validation", "message_type": "discussion"},
            {"sender": "director", "content": "Agreed on grid", "message_type": "decision"},
        ]
        
        summary = director._summarize_debate()
        
        assert "grid" in summary.lower()
        assert len(summary) > 0


class TestDirectorIntegration:
    """Integration tests for director flow."""

    @pytest.fixture
    def director_with_mocks(self):
        """Create director with all external calls mocked."""
        project = MockProject(id=999)
        remove_broker(project.id)
        
        director = DirectorAgent(project)
        
        # Mock LLM to return simple responses
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        
        mock_llm = AsyncMock()
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)
        director._llm = mock_llm
        
        return director

    @pytest.mark.asyncio
    async def test_kickoff_initializes_agents(self, director_with_mocks):
        """Test that kickoff initializes agent states."""
        director = director_with_mocks
        director.brief = MockBrief()
        
        await director._kickoff()
        
        assert director.state.phase == BuildPhase.KICKOFF
        assert len(director.agent_states) >= 3  # director, planner, qc, expert
        assert "planner" in director.agent_states
        assert "qc" in director.agent_states

    @pytest.mark.asyncio
    async def test_kickoff_creates_expert(self, director_with_mocks):
        """Test that kickoff creates domain expert."""
        director = director_with_mocks
        director.brief = MockBrief()
        
        await director._kickoff()
        
        assert director.expert is not None
        assert director.composition is not None

    @pytest.mark.asyncio
    async def test_full_run_completes(self, director_with_mocks):
        """Test that full run completes all phases."""
        director = director_with_mocks
        brief = MockBrief()
        
        # Mock the factory to avoid import issues
        director.factory.cleanup = Mock()
        
        result = await director.run(brief)
        
        assert result["success"] is True
        assert director.state.phase == BuildPhase.COMPLETE


class TestRunDirector:
    """Tests for run_director convenience function."""

    @pytest.mark.asyncio
    async def test_run_director_creates_and_runs(self):
        """Test that run_director creates director and runs it."""
        project = MockProject(id=888)
        remove_broker(project.id)
        
        with patch.object(DirectorAgent, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"success": True}
            
            result = await run_director(project, None)
            
            assert result["success"] is True
            mock_run.assert_called_once()
