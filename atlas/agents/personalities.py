"""Agent Personalities - Framework for distinct agent debate styles.

Defines personality traits that drive how agents interact in debates,
including their tendency to disagree, interrupt, and communicate.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DebateStyle(str, Enum):
    """How an agent approaches debates."""
    BOLD = "bold"           # Takes strong positions, confident
    CAUTIOUS = "cautious"   # Careful, risk-aware, thorough
    CONTRARIAN = "contrarian"  # Plays devil's advocate, challenges assumptions
    MEDIATOR = "mediator"   # Seeks consensus, bridges differences
    PASSIONATE = "passionate"  # Enthusiastic, deeply engaged


class CommunicationStyle(str, Enum):
    """How an agent communicates."""
    DIRECT = "direct"       # Straight to the point, no hedging
    DIPLOMATIC = "diplomatic"  # Tactful, considerate of feelings
    ANALYTICAL = "analytical"  # Data-driven, structured arguments
    NARRATIVE = "narrative"  # Story-driven, uses examples


@dataclass
class AgentPersonality:
    """Defines an agent's personality traits for debates.

    Attributes:
        name: Agent's display name
        role: Agent's role description
        debate_style: How they approach debates
        communication_style: How they communicate
        disagreement_tendency: 0.0 to 1.0 - how likely to disagree
        interruption_tendency: 0.0 to 1.0 - how often they jump in
        expertise_confidence: 0.0 to 1.0 - how confident in their domain
        position_flexibility: 0.0 to 1.0 - willingness to change positions
        verbosity: 0.0 to 1.0 - how verbose responses are
        traits: Additional personality traits for prompting
    """
    name: str
    role: str
    debate_style: DebateStyle
    communication_style: CommunicationStyle
    disagreement_tendency: float = 0.5
    interruption_tendency: float = 0.3
    expertise_confidence: float = 0.7
    position_flexibility: float = 0.5
    verbosity: float = 0.5
    traits: list[str] = field(default_factory=list)

    def to_prompt_description(self) -> str:
        """Generate personality description for system prompt."""
        traits_str = ", ".join(self.traits) if self.traits else "professional and focused"

        disagree_desc = (
            "rarely disagrees unless critical" if self.disagreement_tendency < 0.3
            else "moderately critical, questions assumptions" if self.disagreement_tendency < 0.6
            else "highly critical, frequently challenges ideas"
        )

        interrupt_desc = (
            "waits for others to finish" if self.interruption_tendency < 0.3
            else "occasionally interjects with key points" if self.interruption_tendency < 0.6
            else "frequently jumps in when they have insights"
        )

        flexibility_desc = (
            "holds firm positions" if self.position_flexibility < 0.3
            else "open to changing views with good arguments" if self.position_flexibility < 0.7
            else "readily updates positions when convinced"
        )

        return f"""PERSONALITY PROFILE:
- Debate Style: {self.debate_style.value.capitalize()} - {disagree_desc}
- Communication: {self.communication_style.value.capitalize()} - {interrupt_desc}
- Confidence Level: {int(self.expertise_confidence * 100)}% in your domain expertise
- Flexibility: {flexibility_desc}
- Character Traits: {traits_str}"""

    def get_debate_instructions(self) -> str:
        """Generate debate behavior instructions."""
        instructions = [
            "DEBATE BEHAVIOR:",
        ]

        # Disagreement behavior
        if self.disagreement_tendency >= 0.6:
            instructions.append("- Challenge weak arguments directly with 'I disagree because...'")
            instructions.append("- Push back when you see logical gaps or missing considerations")
        elif self.disagreement_tendency >= 0.3:
            instructions.append("- Voice concerns when you see potential issues")
            instructions.append("- Ask probing questions to test ideas")
        else:
            instructions.append("- Focus on building consensus and finding common ground")
            instructions.append("- Express disagreement diplomatically when necessary")

        # Interruption behavior
        if self.interruption_tendency >= 0.5:
            instructions.append("- Jump in when you have critical insights, even mid-discussion")
            instructions.append("- Don't wait for your turn if something important needs addressing")
        else:
            instructions.append("- Let others finish before contributing")
            instructions.append("- Build on what others have said")

        # Position changes
        if self.position_flexibility >= 0.5:
            instructions.append("- If convinced, explicitly change position: 'Actually, [name] makes a good point...'")
        else:
            instructions.append("- Defend your positions with evidence")
            instructions.append("- Only change stance when presented with compelling evidence")

        # Communication style specifics
        if self.communication_style == CommunicationStyle.DIRECT:
            instructions.append("- Be direct and specific - no hedging or excessive qualifiers")
        elif self.communication_style == CommunicationStyle.DIPLOMATIC:
            instructions.append("- Be tactful but honest - acknowledge others' points before disagreeing")
        elif self.communication_style == CommunicationStyle.ANALYTICAL:
            instructions.append("- Back up claims with reasoning and data")
        else:
            instructions.append("- Use examples and scenarios to make your points")

        instructions.append("- Don't agree just to be polite - genuine disagreement drives better outcomes")

        return "\n".join(instructions)


# Predefined personalities for core agents
DIRECTOR_PERSONALITY = AgentPersonality(
    name="Director",
    role="project orchestrator and facilitator",
    debate_style=DebateStyle.MEDIATOR,
    communication_style=CommunicationStyle.DIRECT,
    disagreement_tendency=0.2,
    interruption_tendency=0.4,
    expertise_confidence=0.8,
    position_flexibility=0.7,
    verbosity=0.4,
    traits=["organized", "decisive", "keeps discussions on track", "synthesizes different viewpoints"]
)

PLANNER_PERSONALITY = AgentPersonality(
    name="Planner",
    role="build planning and architecture specialist",
    debate_style=DebateStyle.MEDIATOR,
    communication_style=CommunicationStyle.ANALYTICAL,
    disagreement_tendency=0.4,
    interruption_tendency=0.2,
    expertise_confidence=0.8,
    position_flexibility=0.6,
    verbosity=0.5,
    traits=["structured", "systematic", "detail-oriented", "pragmatic"]
)

QC_PERSONALITY = AgentPersonality(
    name="QC",
    role="quality control and sellability specialist",
    debate_style=DebateStyle.CONTRARIAN,
    communication_style=CommunicationStyle.DIRECT,
    disagreement_tendency=0.8,
    interruption_tendency=0.5,
    expertise_confidence=0.9,
    position_flexibility=0.3,
    verbosity=0.4,
    traits=["skeptical", "thorough", "quality-focused", "customer-advocate", "devil's advocate"]
)

EXPERT_PERSONALITY = AgentPersonality(
    name="Expert",
    role="domain expert",
    debate_style=DebateStyle.BOLD,
    communication_style=CommunicationStyle.NARRATIVE,
    disagreement_tendency=0.5,
    interruption_tendency=0.4,
    expertise_confidence=0.9,
    position_flexibility=0.5,
    verbosity=0.6,
    traits=["knowledgeable", "experienced", "practical", "user-focused"]
)

BUILDER_PERSONALITY = AgentPersonality(
    name="Builder",
    role="product builder and implementer",
    debate_style=DebateStyle.CAUTIOUS,
    communication_style=CommunicationStyle.ANALYTICAL,
    disagreement_tendency=0.4,
    interruption_tendency=0.3,
    expertise_confidence=0.8,
    position_flexibility=0.6,
    verbosity=0.4,
    traits=["practical", "implementation-focused", "detail-oriented", "efficiency-minded"]
)


def get_personality(agent_type: str) -> AgentPersonality:
    """Get the personality for an agent type."""
    personalities = {
        "director": DIRECTOR_PERSONALITY,
        "planner": PLANNER_PERSONALITY,
        "qc": QC_PERSONALITY,
        "expert": EXPERT_PERSONALITY,
        "builder": BUILDER_PERSONALITY,
    }
    return personalities.get(agent_type.lower(), EXPERT_PERSONALITY)


def create_expert_personality(domain: str, name: str) -> AgentPersonality:
    """Create a customized expert personality for a specific domain."""
    base = EXPERT_PERSONALITY
    return AgentPersonality(
        name=name,
        role=f"domain expert in {domain}",
        debate_style=base.debate_style,
        communication_style=base.communication_style,
        disagreement_tendency=base.disagreement_tendency,
        interruption_tendency=base.interruption_tendency,
        expertise_confidence=base.expertise_confidence,
        position_flexibility=base.position_flexibility,
        verbosity=base.verbosity,
        traits=base.traits + [f"{domain} specialist"]
    )
