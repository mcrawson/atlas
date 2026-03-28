"""Round Table - Agent coordination and kickoff for ATLAS.

The Round Table is where agents come together at project kickoff:
1. Brief is distributed to all agents
2. Custom Expert is spawned for this specific project
3. Agent conversation log is created
4. Each agent understands their role

Agents communicate through the conversation log throughout the project.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from atlas.agents.base import BaseAgent, AgentStatus, AgentOutput

logger = logging.getLogger("atlas.agents.roundtable")


class MessageType(Enum):
    """Types of messages in the agent conversation."""
    SYSTEM = "system"          # Round Table announcements
    BRIEF = "brief"            # Brief distribution
    QUESTION = "question"      # Agent asking a question
    ANSWER = "answer"          # Agent answering
    UPDATE = "update"          # Status update
    HANDOFF = "handoff"        # Passing work to another agent
    DECISION = "decision"      # Decision made
    QC_REPORT = "qc_report"    # QC findings
    CONCERN = "concern"        # Agent raising a concern
    RESOLUTION = "resolution"  # Concern resolved


@dataclass
class AgentMessage:
    """A message in the agent conversation log."""
    sender: str              # Agent name (qc, planner, expert, system)
    message_type: MessageType
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    recipient: Optional[str] = None  # Specific agent, or None for all
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "recipient": self.recipient,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        return cls(
            sender=data["sender"],
            message_type=MessageType(data["message_type"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            recipient=data.get("recipient"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConversationLog:
    """The agent conversation log for a project."""
    project_id: int
    messages: list[AgentMessage] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_message(
        self,
        sender: str,
        message_type: MessageType,
        content: str,
        recipient: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AgentMessage:
        """Add a message to the conversation."""
        msg = AgentMessage(
            sender=sender,
            message_type=message_type,
            content=content,
            recipient=recipient,
            metadata=metadata or {},
        )
        self.messages.append(msg)

        # Track participants
        if sender not in self.participants and sender != "system":
            self.participants.append(sender)

        return msg

    def get_messages_for(self, agent: str) -> list[AgentMessage]:
        """Get messages relevant to a specific agent."""
        return [
            m for m in self.messages
            if m.recipient is None or m.recipient == agent or m.sender == agent
        ]

    def get_recent(self, count: int = 10) -> list[AgentMessage]:
        """Get recent messages."""
        return self.messages[-count:]

    def get_by_type(self, message_type: MessageType) -> list[AgentMessage]:
        """Get messages of a specific type."""
        return [m for m in self.messages if m.message_type == message_type]

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "messages": [m.to_dict() for m in self.messages],
            "participants": self.participants,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationLog":
        messages = [AgentMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            project_id=data["project_id"],
            messages=messages,
            participants=data.get("participants", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )

    def format_for_context(self, max_messages: int = 20) -> str:
        """Format conversation for agent context."""
        recent = self.get_recent(max_messages)
        lines = ["## Agent Conversation Log", ""]

        for msg in recent:
            time_str = msg.timestamp.strftime("%H:%M")
            recipient_str = f" → {msg.recipient}" if msg.recipient else ""
            lines.append(f"[{time_str}] **{msg.sender}**{recipient_str} ({msg.message_type.value}):")
            lines.append(f"  {msg.content}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class RoundTableSession:
    """A Round Table kickoff session."""
    project_id: int
    brief: dict
    conversation: ConversationLog
    custom_expert: Optional[dict] = None  # The spawned expert config
    participants: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    status: str = "active"

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "brief": self.brief,
            "conversation": self.conversation.to_dict(),
            "custom_expert": self.custom_expert,
            "participants": self.participants,
            "started_at": self.started_at.isoformat(),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RoundTableSession":
        return cls(
            project_id=data["project_id"],
            brief=data["brief"],
            conversation=ConversationLog.from_dict(data["conversation"]),
            custom_expert=data.get("custom_expert"),
            participants=data.get("participants", []),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else datetime.now(),
            status=data.get("status", "active"),
        )


class RoundTable:
    """Manages agent coordination and kickoff.

    The Round Table:
    1. Kicks off projects by distributing the Brief
    2. Spawns the Custom Expert for this project
    3. Maintains the conversation log
    4. Facilitates agent communication
    """

    def __init__(self, router=None, memory=None, providers=None):
        self.router = router
        self.memory = memory
        self.providers = providers or {}
        self._sessions: dict[int, RoundTableSession] = {}

    async def kickoff(
        self,
        project_id: int,
        brief: dict,
        idea: str,
    ) -> RoundTableSession:
        """Kick off a project with the Round Table.

        Args:
            project_id: The project ID
            brief: The approved Business Brief
            idea: The original idea

        Returns:
            RoundTableSession with conversation log and custom expert
        """
        logger.info(f"[RoundTable] Kickoff for project {project_id}")

        # Create conversation log
        conversation = ConversationLog(project_id=project_id)

        # System announcement
        conversation.add_message(
            sender="system",
            message_type=MessageType.SYSTEM,
            content=f"Round Table session started for: {brief.get('product_name', 'New Project')}",
        )

        # Distribute the Brief
        brief_summary = self._summarize_brief(brief)
        conversation.add_message(
            sender="system",
            message_type=MessageType.BRIEF,
            content=brief_summary,
            metadata={"full_brief": brief},
        )

        # Spawn the Custom Expert
        custom_expert = await self._spawn_custom_expert(brief, idea)

        conversation.add_message(
            sender="system",
            message_type=MessageType.SYSTEM,
            content=f"Custom Expert spawned: {custom_expert['name']} - {custom_expert['expertise']}",
            metadata={"expert_config": custom_expert},
        )

        # Introduce participants
        participants = ["qc", "planner", custom_expert["id"]]

        conversation.add_message(
            sender="system",
            message_type=MessageType.SYSTEM,
            content=f"Participants: QC Agent, Planner, {custom_expert['name']}",
        )

        # Each agent acknowledges
        conversation.add_message(
            sender="qc",
            message_type=MessageType.UPDATE,
            content=f"QC ready. I'll verify all work against the Brief. Success criteria noted: {len(brief.get('success_criteria', []))} items to verify.",
        )

        conversation.add_message(
            sender="planner",
            message_type=MessageType.UPDATE,
            content=f"Planner ready. I'll create the build plan for this {brief.get('product_type', 'product')}.",
        )

        conversation.add_message(
            sender=custom_expert["id"],
            message_type=MessageType.UPDATE,
            content=f"{custom_expert['name']} ready. I'm the domain expert for this project. {custom_expert['introduction']}",
        )

        # Create session
        session = RoundTableSession(
            project_id=project_id,
            brief=brief,
            conversation=conversation,
            custom_expert=custom_expert,
            participants=participants,
        )

        self._sessions[project_id] = session

        logger.info(f"[RoundTable] Kickoff complete. Expert: {custom_expert['name']}")

        return session

    def _summarize_brief(self, brief: dict) -> str:
        """Create a summary of the Brief for agents."""
        lines = [
            "## Business Brief Distributed",
            "",
            f"**Product:** {brief.get('product_name', 'Unknown')}",
            f"**Type:** {brief.get('product_type', 'Unknown')}",
            f"**Recommendation:** {brief.get('recommendation', 'Unknown')}",
            "",
            f"**Summary:** {brief.get('executive_summary', 'No summary')[:200]}...",
            "",
            "**Target Customer:**",
        ]

        target = brief.get("target_customer", {})
        if target:
            lines.append(f"- Demographics: {target.get('demographics', 'Unknown')}")
            if target.get("pain_points"):
                lines.append(f"- Pain Points: {', '.join(target['pain_points'][:3])}")

        lines.append("")
        lines.append("**Success Criteria:**")
        for criterion in brief.get("success_criteria", [])[:3]:
            lines.append(f"- {criterion}")

        return "\n".join(lines)

    async def _spawn_custom_expert(self, brief: dict, idea: str) -> dict:
        """Spawn a Custom Expert agent for this project.

        The Custom Expert is dynamically created based on the Brief.
        It becomes the domain expert and builder for this specific project.
        """
        product_name = brief.get("product_name", "Product")
        product_type = brief.get("product_type", "product")
        target_customer = brief.get("target_customer", {})
        market_analysis = brief.get("market_analysis", {})

        # Generate expert identity
        expert_id = f"expert_{product_type}"
        expert_name = self._generate_expert_name(product_name, product_type)
        expertise = self._generate_expertise(brief)

        # Build the system prompt for this expert
        system_prompt = self._build_expert_prompt(brief, idea)

        # Introduction message
        introduction = self._generate_introduction(brief)

        expert_config = {
            "id": expert_id,
            "name": expert_name,
            "expertise": expertise,
            "system_prompt": system_prompt,
            "introduction": introduction,
            "product_type": product_type,
            "brief_snapshot": {
                "product_name": product_name,
                "target_customer": target_customer.get("demographics", ""),
                "success_criteria": brief.get("success_criteria", []),
            },
            "spawned_at": datetime.now().isoformat(),
        }

        return expert_config

    def _generate_expert_name(self, product_name: str, product_type: str) -> str:
        """Generate a name for the Custom Expert."""
        type_titles = {
            "printable": "Printable Product Specialist",
            "document": "Document & Publishing Expert",
            "web": "Web Development Specialist",
            "app": "Mobile App Expert",
        }

        base_title = type_titles.get(product_type, "Product Specialist")

        # Make it specific to the product
        if "planner" in product_name.lower():
            return "Planner Design Specialist"
        elif "book" in product_name.lower() or "guide" in product_name.lower():
            return "Book & Guide Expert"
        elif "tracker" in product_name.lower():
            return "Tracker Design Specialist"
        elif "app" in product_name.lower():
            return "App Development Expert"
        else:
            return base_title

    def _generate_expertise(self, brief: dict) -> str:
        """Generate expertise description."""
        product_type = brief.get("product_type", "product")
        product_name = brief.get("product_name", "this product")
        target = brief.get("target_customer", {}).get("demographics", "customers")

        return f"Expert in {product_type} products for {target}, specializing in {product_name}"

    def _generate_introduction(self, brief: dict) -> str:
        """Generate the expert's introduction message."""
        product_name = brief.get("product_name", "this product")
        product_type = brief.get("product_type", "product")
        target = brief.get("target_customer", {})
        target_demo = target.get("demographics", "our target customers")

        pain_points = target.get("pain_points", [])
        pain_str = pain_points[0] if pain_points else "their needs"

        return (
            f"I'll be building {product_name} - a {product_type} designed for {target_demo}. "
            f"I understand they struggle with {pain_str}, and I'll ensure our product addresses this."
        )

    def _build_expert_prompt(self, brief: dict, idea: str) -> str:
        """Build the system prompt for the Custom Expert."""
        product_name = brief.get("product_name", "Product")
        product_type = brief.get("product_type", "product")
        executive_summary = brief.get("executive_summary", "")
        target_customer = brief.get("target_customer", {})
        market_analysis = brief.get("market_analysis", {})
        success_criteria = brief.get("success_criteria", [])
        financials = brief.get("financials", {})

        # Build comprehensive prompt
        prompt = f"""You are the Custom Expert for this ATLAS project.

## Your Identity
You are a specialist in {product_type} products, specifically an expert in building {product_name}.

## The Project
**Original Idea:** {idea}

**Executive Summary:** {executive_summary}

## Your Customer
"""

        if target_customer:
            prompt += f"""
**Demographics:** {target_customer.get('demographics', 'Not specified')}

**Pain Points:**
"""
            for point in target_customer.get('pain_points', []):
                prompt += f"- {point}\n"

            prompt += f"""
**Behaviors:**
"""
            for behavior in target_customer.get('behaviors', []):
                prompt += f"- {behavior}\n"

        prompt += f"""
## Market Context
"""
        if market_analysis:
            prompt += f"""
**Market Size:** {market_analysis.get('market_size', 'Unknown')}
**Competition:** {market_analysis.get('competition', 'Unknown')}
**Differentiation:** {market_analysis.get('differentiation', 'Unknown')}
"""

        prompt += f"""
## Success Criteria
You must ensure the final product meets these criteria:
"""
        for criterion in success_criteria:
            prompt += f"- {criterion}\n"

        prompt += f"""
## Your Role
1. **Domain Expert** - You know everything about {product_type} products like {product_name}
2. **Builder** - You create the actual product (templates, code, content)
3. **Quality Focus** - Everything you build must be SELLABLE
4. **Customer Advocate** - Always think about the target customer's needs

## Building Guidelines
"""

        # Add type-specific guidelines
        if product_type == "printable":
            prompt += """
- Create print-ready HTML/CSS
- Use proper page sizes (Letter/A4)
- Design for physical printing (margins, bleed)
- Focus on usability when printed
- Make it beautiful AND functional
"""
        elif product_type == "document":
            prompt += """
- Create professional, publishable content
- Structure for readability
- Include all necessary sections
- Format for the target platform (KDP, Gumroad, etc.)
- Make it comprehensive yet accessible
"""
        elif product_type == "web":
            prompt += """
- Build modern, responsive web pages
- Focus on user experience
- Optimize for conversion
- Make it professional and trustworthy
- Include all necessary functionality
"""
        elif product_type == "app":
            prompt += """
- Design for mobile-first experience
- Focus on user engagement
- Make it intuitive and easy to use
- Include core features from the Brief
- Plan for scalability
"""

        prompt += f"""
## Pricing Context
"""
        if financials:
            prompt += f"""
**Target Price:** {financials.get('pricing', 'TBD')}
**Production Cost:** {financials.get('production_cost', 'TBD')}

Your output must justify this price point. Would a customer pay this for what you build?
"""

        prompt += """
## Communication
- Update the team through the conversation log
- Ask questions if requirements are unclear
- Flag concerns early
- Coordinate with QC on quality checks

Remember: We build SELLABLE products. Every output must be something a customer would pay for.
"""

        return prompt

    def get_session(self, project_id: int) -> Optional[RoundTableSession]:
        """Get an existing session."""
        return self._sessions.get(project_id)

    def add_message(
        self,
        project_id: int,
        sender: str,
        message_type: MessageType,
        content: str,
        recipient: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[AgentMessage]:
        """Add a message to a project's conversation."""
        session = self._sessions.get(project_id)
        if not session:
            logger.warning(f"[RoundTable] No session for project {project_id}")
            return None

        return session.conversation.add_message(
            sender=sender,
            message_type=message_type,
            content=content,
            recipient=recipient,
            metadata=metadata,
        )

    def get_conversation(self, project_id: int) -> Optional[ConversationLog]:
        """Get the conversation log for a project."""
        session = self._sessions.get(project_id)
        return session.conversation if session else None

    def get_expert(self, project_id: int) -> Optional[dict]:
        """Get the Custom Expert config for a project."""
        session = self._sessions.get(project_id)
        return session.custom_expert if session else None

    def get_context_for_agent(self, project_id: int, agent: str) -> dict:
        """Get the context an agent needs for this project.

        Includes:
        - The Business Brief
        - Recent conversation
        - Custom Expert info (if relevant)
        """
        session = self._sessions.get(project_id)
        if not session:
            return {}

        context = {
            "brief": session.brief,
            "conversation": session.conversation.format_for_context(),
            "participants": session.participants,
        }

        if session.custom_expert:
            context["expert"] = {
                "name": session.custom_expert["name"],
                "expertise": session.custom_expert["expertise"],
            }

            # If this IS the expert, include full config
            if agent == session.custom_expert["id"]:
                context["expert_config"] = session.custom_expert

        return context


# Singleton instance
_roundtable: Optional[RoundTable] = None


def get_roundtable(router=None, memory=None, providers=None) -> RoundTable:
    """Get or create the Round Table instance."""
    global _roundtable
    if _roundtable is None:
        _roundtable = RoundTable(router=router, memory=memory, providers=providers)
    return _roundtable
