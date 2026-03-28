"""Tests for atlas.agents.personalities module."""

import pytest
from atlas.agents.personalities import (
    AgentPersonality,
    DebateStyle,
    CommunicationStyle,
    get_personality,
    create_expert_personality,
    DIRECTOR_PERSONALITY,
    PLANNER_PERSONALITY,
    QC_PERSONALITY,
    EXPERT_PERSONALITY,
    BUILDER_PERSONALITY,
)


class TestDebateStyle:
    """Tests for DebateStyle enum."""

    def test_debate_style_values(self):
        """Test that all debate styles have expected values."""
        assert DebateStyle.BOLD.value == "bold"
        assert DebateStyle.CAUTIOUS.value == "cautious"
        assert DebateStyle.CONTRARIAN.value == "contrarian"
        assert DebateStyle.MEDIATOR.value == "mediator"
        assert DebateStyle.PASSIONATE.value == "passionate"

    def test_debate_style_is_string(self):
        """Test that DebateStyle inherits from str."""
        assert isinstance(DebateStyle.BOLD, str)
        assert DebateStyle.BOLD == "bold"


class TestCommunicationStyle:
    """Tests for CommunicationStyle enum."""

    def test_communication_style_values(self):
        """Test that all communication styles have expected values."""
        assert CommunicationStyle.DIRECT.value == "direct"
        assert CommunicationStyle.DIPLOMATIC.value == "diplomatic"
        assert CommunicationStyle.ANALYTICAL.value == "analytical"
        assert CommunicationStyle.NARRATIVE.value == "narrative"


class TestAgentPersonality:
    """Tests for AgentPersonality dataclass."""

    def test_create_basic_personality(self):
        """Test creating a basic personality."""
        personality = AgentPersonality(
            name="TestAgent",
            role="test role",
            debate_style=DebateStyle.BOLD,
            communication_style=CommunicationStyle.DIRECT,
        )
        assert personality.name == "TestAgent"
        assert personality.role == "test role"
        assert personality.debate_style == DebateStyle.BOLD
        assert personality.communication_style == CommunicationStyle.DIRECT

    def test_default_values(self):
        """Test that default values are set correctly."""
        personality = AgentPersonality(
            name="Test",
            role="test",
            debate_style=DebateStyle.MEDIATOR,
            communication_style=CommunicationStyle.DIPLOMATIC,
        )
        assert personality.disagreement_tendency == 0.5
        assert personality.interruption_tendency == 0.3
        assert personality.expertise_confidence == 0.7
        assert personality.position_flexibility == 0.5
        assert personality.verbosity == 0.5
        assert personality.traits == []

    def test_custom_values(self):
        """Test setting custom trait values."""
        personality = AgentPersonality(
            name="HighDisagreement",
            role="critic",
            debate_style=DebateStyle.CONTRARIAN,
            communication_style=CommunicationStyle.DIRECT,
            disagreement_tendency=0.9,
            interruption_tendency=0.8,
            expertise_confidence=0.95,
            position_flexibility=0.2,
            verbosity=0.3,
            traits=["skeptical", "thorough"],
        )
        assert personality.disagreement_tendency == 0.9
        assert personality.interruption_tendency == 0.8
        assert personality.traits == ["skeptical", "thorough"]

    def test_to_prompt_description(self):
        """Test generating prompt description."""
        personality = AgentPersonality(
            name="TestAgent",
            role="test role",
            debate_style=DebateStyle.BOLD,
            communication_style=CommunicationStyle.DIRECT,
            disagreement_tendency=0.7,
            traits=["analytical", "focused"],
        )
        desc = personality.to_prompt_description()
        
        assert "PERSONALITY PROFILE:" in desc
        assert "Bold" in desc
        assert "Direct" in desc
        assert "analytical, focused" in desc

    def test_prompt_description_low_disagreement(self):
        """Test prompt description for low disagreement tendency."""
        personality = AgentPersonality(
            name="Agreeable",
            role="helper",
            debate_style=DebateStyle.MEDIATOR,
            communication_style=CommunicationStyle.DIPLOMATIC,
            disagreement_tendency=0.2,
        )
        desc = personality.to_prompt_description()
        assert "rarely disagrees" in desc

    def test_prompt_description_high_disagreement(self):
        """Test prompt description for high disagreement tendency."""
        personality = AgentPersonality(
            name="Critic",
            role="reviewer",
            debate_style=DebateStyle.CONTRARIAN,
            communication_style=CommunicationStyle.DIRECT,
            disagreement_tendency=0.8,
        )
        desc = personality.to_prompt_description()
        assert "highly critical" in desc

    def test_get_debate_instructions(self):
        """Test generating debate instructions."""
        personality = AgentPersonality(
            name="TestAgent",
            role="test",
            debate_style=DebateStyle.BOLD,
            communication_style=CommunicationStyle.DIRECT,
            disagreement_tendency=0.7,
            interruption_tendency=0.6,
            position_flexibility=0.8,
        )
        instructions = personality.get_debate_instructions()
        
        assert "DEBATE BEHAVIOR:" in instructions
        assert "Jump in" in instructions  # High interruption
        assert "change position" in instructions.lower()  # High flexibility

    def test_debate_instructions_low_interruption(self):
        """Test debate instructions for low interruption tendency."""
        personality = AgentPersonality(
            name="Patient",
            role="listener",
            debate_style=DebateStyle.MEDIATOR,
            communication_style=CommunicationStyle.DIPLOMATIC,
            interruption_tendency=0.2,
        )
        instructions = personality.get_debate_instructions()
        assert "Let others finish" in instructions

    def test_debate_instructions_analytical_style(self):
        """Test debate instructions for analytical communication."""
        personality = AgentPersonality(
            name="Analyst",
            role="data person",
            debate_style=DebateStyle.CAUTIOUS,
            communication_style=CommunicationStyle.ANALYTICAL,
        )
        instructions = personality.get_debate_instructions()
        assert "reasoning" in instructions.lower() or "data" in instructions.lower()


class TestPredefinedPersonalities:
    """Tests for predefined personality constants."""

    def test_director_personality(self):
        """Test Director personality configuration."""
        assert DIRECTOR_PERSONALITY.name == "Director"
        assert DIRECTOR_PERSONALITY.debate_style == DebateStyle.MEDIATOR
        assert DIRECTOR_PERSONALITY.communication_style == CommunicationStyle.DIRECT
        assert DIRECTOR_PERSONALITY.disagreement_tendency < 0.5  # Directors are mediators

    def test_qc_personality(self):
        """Test QC personality configuration."""
        assert QC_PERSONALITY.name == "QC"
        assert QC_PERSONALITY.debate_style == DebateStyle.CONTRARIAN
        assert QC_PERSONALITY.disagreement_tendency >= 0.7  # QC should challenge
        assert "skeptical" in QC_PERSONALITY.traits

    def test_planner_personality(self):
        """Test Planner personality configuration."""
        assert PLANNER_PERSONALITY.name == "Planner"
        assert PLANNER_PERSONALITY.communication_style == CommunicationStyle.ANALYTICAL
        assert "structured" in PLANNER_PERSONALITY.traits

    def test_expert_personality(self):
        """Test Expert personality configuration."""
        assert EXPERT_PERSONALITY.name == "Expert"
        assert EXPERT_PERSONALITY.debate_style == DebateStyle.BOLD
        assert EXPERT_PERSONALITY.expertise_confidence >= 0.8

    def test_builder_personality(self):
        """Test Builder personality configuration."""
        assert BUILDER_PERSONALITY.name == "Builder"
        assert BUILDER_PERSONALITY.debate_style == DebateStyle.CAUTIOUS
        assert "practical" in BUILDER_PERSONALITY.traits


class TestGetPersonality:
    """Tests for get_personality function."""

    def test_get_director(self):
        """Test getting director personality."""
        personality = get_personality("director")
        assert personality.name == "Director"

    def test_get_qc(self):
        """Test getting QC personality."""
        personality = get_personality("qc")
        assert personality.name == "QC"

    def test_get_planner(self):
        """Test getting planner personality."""
        personality = get_personality("planner")
        assert personality.name == "Planner"

    def test_get_unknown_returns_expert(self):
        """Test that unknown agent type returns expert personality."""
        personality = get_personality("unknown_agent")
        assert personality.name == "Expert"

    def test_case_insensitive(self):
        """Test that lookup is case-insensitive."""
        assert get_personality("DIRECTOR").name == "Director"
        assert get_personality("Director").name == "Director"
        assert get_personality("QC").name == "QC"


class TestCreateExpertPersonality:
    """Tests for create_expert_personality function."""

    def test_create_fitness_expert(self):
        """Test creating a fitness expert personality."""
        personality = create_expert_personality("fitness", "Fitness Coach")
        assert personality.name == "Fitness Coach"
        assert "fitness" in personality.role
        assert "fitness specialist" in personality.traits

    def test_create_nutrition_expert(self):
        """Test creating a nutrition expert personality."""
        personality = create_expert_personality("nutrition", "Nutrition Expert")
        assert personality.name == "Nutrition Expert"
        assert "nutrition" in personality.role

    def test_inherits_expert_base_traits(self):
        """Test that created expert inherits base expert traits."""
        personality = create_expert_personality("tech", "Tech Expert")
        # Should inherit from EXPERT_PERSONALITY
        assert personality.debate_style == EXPERT_PERSONALITY.debate_style
        assert personality.communication_style == EXPERT_PERSONALITY.communication_style
        assert personality.expertise_confidence == EXPERT_PERSONALITY.expertise_confidence
