"""Round Table V2 - Enhanced Agent Coordination for ATLAS.

The Round Table is the strategic planning session where:
1. Mission is reinforced - everyone aligned on building SELLABLE products
2. Brief is reviewed and validated - pain points, metrics, pricing
3. Dynamic specialists are spawned - 1-3 experts for THIS project
4. Roles and deliverables are assigned - who does what
5. Timeline and tasks are created - when things happen

This is a REAL discussion, not just a handoff.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, List

from atlas.agents.base import BaseAgent, AgentStatus, AgentOutput
from atlas.standards import CORE_PRINCIPLE, PHILOSOPHY

logger = logging.getLogger("atlas.agents.roundtable")


# =============================================================================
# Message Types for Agent Conversation
# =============================================================================

class MessageType(Enum):
    """Types of messages in the agent conversation."""
    SYSTEM = "system"              # Round Table announcements
    MISSION = "mission"            # Mission alignment
    BRIEF = "brief"                # Brief distribution
    DISCUSSION = "discussion"      # General discussion
    QUESTION = "question"          # Agent asking a question
    ANSWER = "answer"              # Agent answering
    CONCERN = "concern"            # Agent raising a concern
    RESOLUTION = "resolution"      # Concern resolved
    PROPOSAL = "proposal"          # Agent proposing something
    AGREEMENT = "agreement"        # Agent agreeing
    DISAGREEMENT = "disagreement"  # Agent disagreeing
    DECISION = "decision"          # Final decision made
    TASK = "task"                  # Task assignment
    TIMELINE = "timeline"          # Timeline item
    HANDOFF = "handoff"            # Passing work to another agent
    QC_REPORT = "qc_report"        # QC findings
    UPDATE = "update"              # Status update


@dataclass
class AgentMessage:
    """A message in the agent conversation log."""
    sender: str
    message_type: MessageType
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    recipient: Optional[str] = None
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

    def add(
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
        if sender not in self.participants and sender != "system":
            self.participants.append(sender)
        return msg

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "messages": [m.to_dict() for m in self.messages],
            "participants": self.participants,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationLog":
        return cls(
            project_id=data["project_id"],
            messages=[AgentMessage.from_dict(m) for m in data.get("messages", [])],
            participants=data.get("participants", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )

    def get_recent(self, count: int = 20) -> list[AgentMessage]:
        """Get the most recent messages."""
        return self.messages[-count:] if self.messages else []

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


# =============================================================================
# Task & Deliverable Tracking
# =============================================================================

@dataclass
class Deliverable:
    """A deliverable assigned to an agent."""
    id: str
    name: str
    description: str
    owner: str  # Agent ID
    depends_on: list[str] = field(default_factory=list)  # Other deliverable IDs
    estimated_effort: str = ""  # e.g., "2 hours", "1 day"
    status: str = "pending"  # pending, in_progress, complete, blocked
    output: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "depends_on": self.depends_on,
            "estimated_effort": self.estimated_effort,
            "status": self.status,
            "output": self.output,
        }


@dataclass
class DynamicAgent:
    """A dynamically spawned specialist agent."""
    id: str
    name: str
    expertise: str
    role_description: str
    system_prompt: str
    skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "expertise": self.expertise,
            "role_description": self.role_description,
            "system_prompt": self.system_prompt,
            "skills": self.skills,
        }


# =============================================================================
# Round Table Session
# =============================================================================

@dataclass
class RoundTableSession:
    """A complete Round Table planning session."""
    project_id: int
    brief: dict
    conversation: ConversationLog

    # Dynamic agents spawned for this project
    specialists: list[DynamicAgent] = field(default_factory=list)

    # Validated brief elements (after discussion)
    validated_pain_points: list[dict] = field(default_factory=list)
    validated_metrics: list[dict] = field(default_factory=list)
    validated_pricing: dict = field(default_factory=dict)

    # Deliverables and timeline
    deliverables: list[Deliverable] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)

    # Session metadata
    started_at: datetime = field(default_factory=datetime.now)
    status: str = "active"  # active, planning_complete, in_progress, complete

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "brief": self.brief,
            "conversation": self.conversation.to_dict(),
            "specialists": [s.to_dict() for s in self.specialists],
            "validated_pain_points": self.validated_pain_points,
            "validated_metrics": self.validated_metrics,
            "validated_pricing": self.validated_pricing,
            "deliverables": [d.to_dict() for d in self.deliverables],
            "timeline": self.timeline,
            "started_at": self.started_at.isoformat(),
            "status": self.status,
        }


# =============================================================================
# Round Table V2 - The Main Coordinator
# =============================================================================

class RoundTableV2:
    """Enhanced Round Table with real discussions and planning.

    The Round Table orchestrates:
    1. Mission alignment - everyone knows we build SELLABLE products
    2. Brief validation - pain points, metrics, pricing discussion
    3. Specialist spawning - 1-3 experts for this specific project
    4. Role assignment - who does what
    5. Timeline creation - when things happen
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
        """Run a full Round Table kickoff session.

        This runs through all phases:
        1. Mission alignment
        2. Brief review & validation
        3. Specialist spawning
        4. Role assignment
        5. Timeline creation
        """
        logger.info(f"[RoundTable] Starting kickoff for project {project_id}")

        # Initialize session
        conversation = ConversationLog(project_id=project_id)
        session = RoundTableSession(
            project_id=project_id,
            brief=brief,
            conversation=conversation,
        )

        # Phase 1: Mission Alignment
        await self._phase_mission_alignment(session)

        # Phase 2: Brief Review & Validation
        await self._phase_brief_validation(session, idea)

        # Phase 3: Spawn Specialists
        await self._phase_spawn_specialists(session, idea)

        # Phase 4: Role Assignment & Deliverables
        await self._phase_assign_roles(session)

        # Phase 5: Timeline
        await self._phase_create_timeline(session)

        # Wrap up
        session.status = "planning_complete"
        self._sessions[project_id] = session

        logger.info(f"[RoundTable] Kickoff complete. {len(session.specialists)} specialists, {len(session.deliverables)} deliverables")

        return session

    # =========================================================================
    # Phase 1: Mission Alignment
    # =========================================================================

    async def _phase_mission_alignment(self, session: RoundTableSession):
        """Ensure all agents understand the ATLAS mission."""
        conv = session.conversation

        conv.add("system", MessageType.SYSTEM,
            f"=== ROUND TABLE SESSION STARTED ===\n"
            f"Project: {session.brief.get('product_name', 'New Project')}"
        )

        conv.add("system", MessageType.MISSION,
            f"**ATLAS MISSION REMINDER**\n\n{CORE_PRINCIPLE}\n\n"
            f"Every agent must ask: 'Would a customer pay $10+ for this right now?'\n"
            f"If not YES, we keep working until it is."
        )

        # Director acknowledges
        conv.add("director", MessageType.AGREEMENT,
            "Mission acknowledged. We're here to build a SELLABLE product, not a demo. "
            "Let's make sure our Brief is solid before we start building."
        )

        # QC acknowledges
        conv.add("qc", MessageType.AGREEMENT,
            "QC ready. I will verify all work against the sellability test. "
            "Nothing ships until it's ready for a real customer to pay for."
        )

    # =========================================================================
    # Phase 2: Brief Review & Validation
    # =========================================================================

    async def _phase_brief_validation(self, session: RoundTableSession, idea: str):
        """Review and validate the Brief through discussion."""
        conv = session.conversation
        brief = session.brief

        conv.add("system", MessageType.SYSTEM, "=== PHASE 2: BRIEF VALIDATION ===")

        # Distribute the Brief
        brief_summary = self._format_brief_summary(brief)
        conv.add("system", MessageType.BRIEF, brief_summary)

        # --- Pain Points Discussion ---
        conv.add("director", MessageType.DISCUSSION,
            "Let's start with the pain points. What problems are we solving, and are they real enough that people will pay to fix them?"
        )

        pain_points = brief.get("target_customer", {}).get("pain_points", [])
        if not pain_points:
            pain_points = self._extract_pain_points_from_brief(brief)

        validated_pain_points = []
        for i, pain in enumerate(pain_points[:3]):  # Top 3 pain points
            pain_text = pain if isinstance(pain, str) else pain.get("description", str(pain))

            conv.add("qc", MessageType.QUESTION,
                f"Pain Point #{i+1}: '{pain_text}'\n"
                f"How do we know this is a real pain? How will we measure if we solved it?"
            )

            # Generate a metric for this pain point
            metric = self._derive_metric_from_pain(pain_text, brief)

            conv.add("planner", MessageType.ANSWER,
                f"For '{pain_text}', success means: {metric['success_looks_like']}\n"
                f"We measure this by: {metric['how_to_measure']}"
            )

            validated_pain_points.append({
                "pain_point": pain_text,
                "success_looks_like": metric["success_looks_like"],
                "how_to_measure": metric["how_to_measure"],
                "importance": "critical" if i == 0 else "important",
            })

        session.validated_pain_points = validated_pain_points

        # --- Pricing Discussion ---
        conv.add("director", MessageType.DISCUSSION,
            "Now let's talk pricing. What should this cost, and why?"
        )

        financials = brief.get("financials", {})
        pricing = financials.get("pricing", "Not specified")

        if pricing == "Not specified" or not pricing:
            conv.add("qc", MessageType.CONCERN,
                "The Brief doesn't specify pricing. We need to decide this now, "
                "or we can't validate if the product is worth building."
            )

            # Generate pricing recommendation
            pricing_rec = self._recommend_pricing(brief)

            conv.add("planner", MessageType.PROPOSAL,
                f"Based on the product type ({brief.get('product_type', 'unknown')}) "
                f"and target market, I recommend:\n"
                f"- Price: {pricing_rec['price']}\n"
                f"- Model: {pricing_rec['model']}\n"
                f"- Justification: {pricing_rec['justification']}"
            )

            conv.add("qc", MessageType.AGREEMENT,
                f"Agreed. At {pricing_rec['price']}, we need to ensure the product "
                f"delivers enough value to justify that price."
            )

            session.validated_pricing = pricing_rec
        else:
            session.validated_pricing = {
                "price": pricing,
                "model": financials.get("revenue_model", "one-time"),
                "justification": "From original Brief",
            }

            conv.add("qc", MessageType.AGREEMENT,
                f"Brief specifies {pricing}. Let's make sure we deliver that value."
            )

        # --- Success Criteria Validation ---
        conv.add("director", MessageType.DISCUSSION,
            "Final check: Are our success criteria measurable? QC will use these to validate."
        )

        success_criteria = brief.get("success_criteria", [])
        validated_metrics = []

        for criterion in success_criteria[:3]:
            if isinstance(criterion, dict):
                crit_text = criterion.get("criterion", str(criterion))
                measurable = criterion.get("measurable", "")
            else:
                crit_text = str(criterion)
                measurable = ""

            if not measurable or measurable in ["", "N/A", "TBD"]:
                conv.add("qc", MessageType.CONCERN,
                    f"'{crit_text}' is not measurable as stated. "
                    f"How do we objectively verify this?"
                )

                # Generate measurable version
                measurable = self._make_measurable(crit_text, brief)

                conv.add("planner", MessageType.RESOLUTION,
                    f"Let's measure it as: {measurable}"
                )

            validated_metrics.append({
                "criterion": crit_text,
                "measurable": measurable,
                "verified": False,
            })

        session.validated_metrics = validated_metrics

        conv.add("qc", MessageType.AGREEMENT,
            f"Brief validation complete. {len(validated_pain_points)} pain points, "
            f"{len(validated_metrics)} measurable criteria, pricing confirmed."
        )

    # =========================================================================
    # Phase 3: Spawn Specialists
    # =========================================================================

    async def _phase_spawn_specialists(self, session: RoundTableSession, idea: str):
        """Spawn 1-3 specialist agents for this specific project."""
        conv = session.conversation
        brief = session.brief

        conv.add("system", MessageType.SYSTEM, "=== PHASE 3: SPECIALIST SPAWNING ===")

        conv.add("director", MessageType.DISCUSSION,
            "Based on this project, what specialists do we need? "
            "We should spawn 1-3 experts who are perfect for THIS product."
        )

        # Determine what specialists we need
        specialists_needed = self._determine_specialists(brief, idea)

        for spec in specialists_needed[:3]:  # Max 3 specialists
            agent = DynamicAgent(
                id=spec["id"],
                name=spec["name"],
                expertise=spec["expertise"],
                role_description=spec["role"],
                system_prompt=self._build_specialist_prompt(spec, brief),
                skills=spec.get("skills", []),
            )
            session.specialists.append(agent)

            conv.add("system", MessageType.SYSTEM,
                f"Specialist spawned: **{agent.name}** ({agent.expertise})"
            )

            conv.add(agent.id, MessageType.UPDATE,
                f"I'm {agent.name}, your {agent.expertise}. {agent.role_description}"
            )

        conv.add("qc", MessageType.AGREEMENT,
            f"Team assembled: {', '.join(s.name for s in session.specialists)}. "
            f"Ready to plan deliverables."
        )

    # =========================================================================
    # Phase 4: Role Assignment & Deliverables
    # =========================================================================

    async def _phase_assign_roles(self, session: RoundTableSession):
        """Assign roles and define deliverables."""
        conv = session.conversation
        brief = session.brief

        conv.add("system", MessageType.SYSTEM, "=== PHASE 4: ROLES & DELIVERABLES ===")

        conv.add("director", MessageType.DISCUSSION,
            "Let's define what each team member will deliver. "
            "Be specific - what are the actual outputs?"
        )

        # Generate deliverables based on project type and specialists
        deliverables = self._generate_deliverables(session)

        for d in deliverables:
            session.deliverables.append(d)

            depends_text = f" (depends on: {', '.join(d.depends_on)})" if d.depends_on else ""

            conv.add(d.owner, MessageType.TASK,
                f"I'll deliver: **{d.name}**\n"
                f"- {d.description}\n"
                f"- Estimated effort: {d.estimated_effort}{depends_text}"
            )

        conv.add("qc", MessageType.UPDATE,
            f"I will verify each deliverable against the Brief and sellability criteria. "
            f"Nothing moves forward until it passes QC."
        )

    # =========================================================================
    # Phase 5: Timeline
    # =========================================================================

    async def _phase_create_timeline(self, session: RoundTableSession):
        """Create the project timeline."""
        conv = session.conversation

        conv.add("system", MessageType.SYSTEM, "=== PHASE 5: TIMELINE ===")

        conv.add("director", MessageType.DISCUSSION,
            "Let's sequence the work. What's the order and timing?"
        )

        # Generate timeline from deliverables
        timeline = self._generate_timeline(session.deliverables)
        session.timeline = timeline

        for phase in timeline:
            deliverable_names = ", ".join(phase["deliverables"])
            conv.add("director", MessageType.TIMELINE,
                f"**{phase['name']}** ({phase['duration']})\n"
                f"- Deliverables: {deliverable_names}\n"
                f"- Gate: {phase['gate']}"
            )

        conv.add("system", MessageType.DECISION,
            "=== PLANNING COMPLETE ===\n\n"
            f"Team: {len(session.specialists)} specialists\n"
            f"Deliverables: {len(session.deliverables)}\n"
            f"Timeline: {len(timeline)} phases\n\n"
            f"Mission: Build a SELLABLE product. Let's go!"
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _format_brief_summary(self, brief: dict) -> str:
        """Format Brief for distribution."""
        lines = [
            "## Business Brief",
            "",
            f"**Product:** {brief.get('product_name', 'Unknown')}",
            f"**Type:** {brief.get('product_type', 'Unknown')}",
            f"**Recommendation:** {brief.get('recommendation', 'Unknown')}",
            "",
            f"**Summary:** {brief.get('executive_summary', 'No summary')[:300]}",
            "",
        ]

        target = brief.get("target_customer", {})
        if target:
            lines.append("**Target Customer:**")
            if target.get("demographics"):
                lines.append(f"- Demographics: {target['demographics']}")
            if target.get("pain_points"):
                pain_list = target["pain_points"][:3]
                lines.append(f"- Pain Points: {', '.join(str(p) for p in pain_list)}")

        return "\n".join(lines)

    def _extract_pain_points_from_brief(self, brief: dict) -> list:
        """Extract pain points from Brief if not explicitly listed."""
        pain_points = []

        # Check problem statement
        problem = brief.get("problem_statement", "") or brief.get("description", "")
        if problem:
            pain_points.append(problem)

        # Check features (they often solve pain points)
        features = brief.get("core_features", [])
        for f in features[:2]:
            if isinstance(f, str) and len(f) > 10:
                pain_points.append(f"Need for: {f}")

        return pain_points if pain_points else ["General productivity improvement"]

    def _derive_metric_from_pain(self, pain_point: str, brief: dict) -> dict:
        """Derive a measurable metric from a pain point."""
        # Simple heuristic-based derivation
        pain_lower = pain_point.lower()

        if "forget" in pain_lower or "miss" in pain_lower:
            return {
                "success_looks_like": "User never forgets important items",
                "how_to_measure": "Zero missed reminders/appointments in first week",
            }
        elif "organize" in pain_lower or "manage" in pain_lower:
            return {
                "success_looks_like": "User can find any item in under 10 seconds",
                "how_to_measure": "Task/item lookup time < 10 seconds",
            }
        elif "time" in pain_lower or "busy" in pain_lower:
            return {
                "success_looks_like": "User saves time on daily tasks",
                "how_to_measure": "Reported 30+ minutes saved per week",
            }
        else:
            return {
                "success_looks_like": "User reports problem solved",
                "how_to_measure": "4+ star rating, positive feedback",
            }

    def _recommend_pricing(self, brief: dict) -> dict:
        """Recommend pricing based on product type."""
        product_type = brief.get("product_type", "").lower()

        pricing_map = {
            "printable": {"price": "$4.99-$9.99", "model": "one-time", "justification": "Standard Etsy printable range"},
            "planner": {"price": "$7.99-$14.99", "model": "one-time", "justification": "Premium planner pricing on Etsy"},
            "document": {"price": "$2.99-$9.99", "model": "one-time", "justification": "Standard ebook pricing"},
            "app": {"price": "$4.99/month or $29.99/year", "model": "subscription", "justification": "Productivity app standard"},
            "web": {"price": "$9.99-$29.99/month", "model": "subscription", "justification": "SaaS pricing"},
        }

        for key, pricing in pricing_map.items():
            if key in product_type:
                return pricing

        return {"price": "$9.99", "model": "one-time", "justification": "Default mid-range pricing"}

    def _make_measurable(self, criterion: str, brief: dict) -> str:
        """Convert vague criterion to measurable one."""
        crit_lower = criterion.lower()

        if "organized" in crit_lower:
            return "User can locate any item in under 10 seconds"
        elif "easy" in crit_lower or "simple" in crit_lower:
            return "User completes core task in under 3 clicks/taps"
        elif "fast" in crit_lower or "quick" in crit_lower:
            return "Task completion time < 30 seconds"
        elif "complete" in crit_lower or "finish" in crit_lower:
            return "80%+ of started tasks marked complete"
        else:
            return f"User rates '{criterion}' as 4+ out of 5"

    def _determine_specialists(self, brief: dict, idea: str) -> list:
        """Determine what specialist agents are needed."""
        product_type = brief.get("product_type", "").lower()
        specialists = []

        # Always need a domain expert
        domain = self._identify_domain(brief, idea)
        specialists.append({
            "id": f"expert_{domain['id']}",
            "name": domain["name"],
            "expertise": domain["expertise"],
            "role": domain["role"],
            "skills": domain["skills"],
        })

        # Add technical expert based on product type
        if "app" in product_type or "mobile" in product_type:
            specialists.append({
                "id": "expert_mobile",
                "name": "Mobile Dev Expert",
                "expertise": "Cross-platform mobile development",
                "role": "I handle app architecture, UI implementation, and platform best practices.",
                "skills": ["Flutter", "React Native", "iOS", "Android", "App Store submission"],
            })
        elif "web" in product_type:
            specialists.append({
                "id": "expert_web",
                "name": "Web Dev Expert",
                "expertise": "Modern web development",
                "role": "I handle frontend, backend, and deployment.",
                "skills": ["React", "Node.js", "Vercel", "Responsive design"],
            })
        elif "printable" in product_type or "planner" in product_type:
            specialists.append({
                "id": "expert_design",
                "name": "Print Designer",
                "expertise": "Print-ready design and layout",
                "role": "I ensure the product looks professional and prints perfectly.",
                "skills": ["Print CSS", "Layout", "Typography", "Color theory"],
            })

        # UX expert for user-facing products
        if any(t in product_type for t in ["app", "web", "planner"]):
            specialists.append({
                "id": "expert_ux",
                "name": "UX Designer",
                "expertise": "User experience and interface design",
                "role": "I ensure the product is intuitive and delightful to use.",
                "skills": ["User flows", "Wireframes", "Usability", "Accessibility"],
            })

        return specialists

    def _identify_domain(self, brief: dict, idea: str) -> dict:
        """Identify the domain expertise needed."""
        idea_lower = idea.lower()

        if any(word in idea_lower for word in ["fitness", "workout", "exercise", "health"]):
            return {
                "id": "fitness",
                "name": "Fitness Coach",
                "expertise": "Health and fitness",
                "role": "I ensure the product follows fitness best practices and motivates users.",
                "skills": ["Exercise science", "Motivation", "Habit formation"],
            }
        elif any(word in idea_lower for word in ["productivity", "task", "planner", "organize"]):
            return {
                "id": "productivity",
                "name": "Productivity Expert",
                "expertise": "Personal productivity and organization",
                "role": "I ensure the product helps users actually get things done.",
                "skills": ["GTD", "Time management", "Habit formation", "Focus techniques"],
            }
        elif any(word in idea_lower for word in ["finance", "money", "budget", "invest"]):
            return {
                "id": "finance",
                "name": "Finance Expert",
                "expertise": "Personal finance",
                "role": "I ensure the product gives sound financial guidance.",
                "skills": ["Budgeting", "Investing", "Financial planning"],
            }
        elif any(word in idea_lower for word in ["learn", "study", "education", "course"]):
            return {
                "id": "education",
                "name": "Education Expert",
                "expertise": "Learning and education",
                "role": "I ensure the product facilitates effective learning.",
                "skills": ["Pedagogy", "Curriculum design", "Learning science"],
            }
        else:
            return {
                "id": "general",
                "name": "Product Expert",
                "expertise": "Product development",
                "role": "I ensure the product meets user needs and market standards.",
                "skills": ["User research", "Product strategy", "Quality standards"],
            }

    def _build_specialist_prompt(self, spec: dict, brief: dict) -> str:
        """Build system prompt for a specialist agent."""
        return f"""You are {spec['name']}, an expert in {spec['expertise']}.

{CORE_PRINCIPLE}

YOUR ROLE: {spec['role']}

YOUR SKILLS: {', '.join(spec.get('skills', []))}

PROJECT CONTEXT:
- Product: {brief.get('product_name', 'Unknown')}
- Type: {brief.get('product_type', 'Unknown')}
- Target: {brief.get('target_customer', {}).get('demographics', 'Unknown')}

Your job is to ensure this product is SELLABLE from your area of expertise.
If something doesn't meet professional standards in your domain, speak up.
"""

    def _generate_deliverables(self, session: RoundTableSession) -> list[Deliverable]:
        """Generate deliverables based on project and team."""
        deliverables = []
        brief = session.brief
        product_type = brief.get("product_type", "").lower()

        # Common deliverables
        deliverables.append(Deliverable(
            id="d1_requirements",
            name="Requirements Document",
            description="Detailed requirements based on validated Brief",
            owner="planner",
            estimated_effort="1 hour",
        ))

        # Type-specific deliverables
        if "app" in product_type or "mobile" in product_type:
            deliverables.extend([
                Deliverable(
                    id="d2_wireframes",
                    name="Wireframes & User Flows",
                    description="Screen layouts and navigation flow",
                    owner="expert_ux",
                    depends_on=["d1_requirements"],
                    estimated_effort="2 hours",
                ),
                Deliverable(
                    id="d3_app_code",
                    name="App Implementation",
                    description="Complete app code with all screens",
                    owner="expert_mobile",
                    depends_on=["d2_wireframes"],
                    estimated_effort="4 hours",
                ),
            ])
        elif "printable" in product_type or "planner" in product_type:
            deliverables.extend([
                Deliverable(
                    id="d2_layout",
                    name="Layout Design",
                    description="Page layouts and visual design",
                    owner="expert_design",
                    depends_on=["d1_requirements"],
                    estimated_effort="2 hours",
                ),
                Deliverable(
                    id="d3_print_files",
                    name="Print-Ready Files",
                    description="Complete print-ready PDF/HTML",
                    owner="expert_design",
                    depends_on=["d2_layout"],
                    estimated_effort="3 hours",
                ),
            ])
        else:
            deliverables.append(Deliverable(
                id="d2_implementation",
                name="Product Implementation",
                description="Core product built to spec",
                owner=session.specialists[0].id if session.specialists else "planner",
                depends_on=["d1_requirements"],
                estimated_effort="4 hours",
            ))

        # QC is always last
        deliverables.append(Deliverable(
            id="d_final_qc",
            name="Final QC Validation",
            description="Verify product is SELLABLE",
            owner="qc",
            depends_on=[d.id for d in deliverables],
            estimated_effort="1 hour",
        ))

        return deliverables

    def _generate_timeline(self, deliverables: list[Deliverable]) -> list[dict]:
        """Generate timeline phases from deliverables."""
        timeline = []

        # Group deliverables by dependency level
        no_deps = [d for d in deliverables if not d.depends_on]
        has_deps = [d for d in deliverables if d.depends_on and d.id != "d_final_qc"]
        final_qc = [d for d in deliverables if d.id == "d_final_qc"]

        if no_deps:
            timeline.append({
                "name": "Phase 1: Planning",
                "deliverables": [d.name for d in no_deps],
                "duration": "Day 1",
                "gate": "Requirements approved",
            })

        if has_deps:
            timeline.append({
                "name": "Phase 2: Build",
                "deliverables": [d.name for d in has_deps],
                "duration": "Day 2-3",
                "gate": "All features complete",
            })

        if final_qc:
            timeline.append({
                "name": "Phase 3: QC & Ship",
                "deliverables": [d.name for d in final_qc],
                "duration": "Day 4",
                "gate": "SELLABLE - ready to list",
            })

        return timeline

    # =========================================================================
    # Session Management
    # =========================================================================

    def get_session(self, project_id: int) -> Optional[RoundTableSession]:
        """Get an existing session."""
        return self._sessions.get(project_id)

    def save_session(self, session: RoundTableSession):
        """Save session state."""
        self._sessions[session.project_id] = session


# =============================================================================
# Singleton Factory
# =============================================================================

_roundtable_v2: Optional[RoundTableV2] = None


def get_roundtable_v2(router=None, memory=None, providers=None) -> RoundTableV2:
    """Get or create the Round Table V2 instance."""
    global _roundtable_v2
    if _roundtable_v2 is None:
        _roundtable_v2 = RoundTableV2(router=router, memory=memory, providers=providers)
    return _roundtable_v2
