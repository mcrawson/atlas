"""Agent Factory - Dynamically creates agents based on project needs.

Analyzes the goal and spawns the right team of agents.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from .message_broker import MessageBroker, AgentMessage, MessageType
from .personalities import (
    AgentPersonality, get_personality, create_expert_personality,
    EXPERT_PERSONALITY
)

if TYPE_CHECKING:
    from ..projects.models import Project
    from .analyst import BusinessBrief

logger = logging.getLogger(__name__)


@dataclass
class TeamComposition:
    """The team of agents needed for a project."""
    expert_domain: str  # e.g., "fitness", "productivity", "cooking"
    expert_name: str    # e.g., "Fitness Planning Expert"
    builder_type: str   # e.g., "printable", "document", "web", "app"
    include_qc: bool = True
    include_planner: bool = True
    additional_specialists: list[str] = field(default_factory=list)

    def get_participants(self) -> list[str]:
        """Get list of participant IDs."""
        participants = ["director", f"expert_{self.builder_type}"]
        if self.include_planner:
            participants.append("planner")
        if self.include_qc:
            participants.append("qc")
        participants.append(f"builder_{self.builder_type}")
        participants.extend(self.additional_specialists)
        return participants


class CustomExpert:
    """A dynamically spawned domain expert.

    Created based on the project's Business Brief to provide
    domain-specific expertise throughout the build process.
    """

    def __init__(
        self,
        name: str,
        domain: str,
        expertise: str,
        product_type: str,
        broker: MessageBroker,
        brief: "BusinessBrief" = None,
        personality: AgentPersonality = None,
    ):
        self.name = name
        self.domain = domain
        self.expertise = expertise
        self.product_type = product_type
        self.broker = broker
        self.brief = brief
        self.agent_id = f"expert_{product_type}"
        self._llm = None

        # Use provided personality or create domain-specific one
        self.personality = personality or create_expert_personality(domain, name)

        # Build system prompt from brief and personality
        self.system_prompt = self._build_system_prompt()

        # Subscribe to broker
        broker.subscribe_agent(self.agent_id, self.on_message)

    async def _get_llm(self):
        """Get or create LLM instance."""
        if self._llm is None:
            import os
            try:
                from openai import AsyncOpenAI
                api_key = os.environ.get("OPENAI_API_KEY")
                if api_key:
                    self._llm = AsyncOpenAI(api_key=api_key)
            except ImportError:
                pass
        return self._llm

    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate a response using LLM."""
        llm = await self._get_llm()
        if not llm:
            return f"[{self.name}] (LLM not available) {prompt[:100]}..."

        try:
            response = await llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt or self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"LLM error: {e}")
            return f"[{self.name}] I'm ready to help with {self.domain}."

    def _format_criteria(self, criteria: list) -> str:
        """Format success criteria as string."""
        result = []
        for c in criteria:
            if isinstance(c, dict):
                result.append(c.get('criterion', c.get('description', str(c))))
            else:
                result.append(str(c))
        return ', '.join(result)

    def _build_system_prompt(self) -> str:
        """Generate system prompt based on domain expertise and personality."""
        brief_context = ""
        if self.brief:
            brief_context = f"""
PROJECT CONTEXT:
- Product: {self.brief.product_name}
- Type: {self.brief.product_type}
- Target Customer: {self.brief.target_customer.get('description', 'General audience')}
- Key Value: {self.brief.executive_summary}
- Success Criteria: {self._format_criteria(self.brief.success_criteria[:3])}
"""

        # Get personality-based behavior
        personality_desc = self.personality.to_prompt_description()
        debate_instructions = self.personality.get_debate_instructions()

        return f"""You are {self.name}, a domain expert in {self.domain}.

YOUR EXPERTISE: {self.expertise}

{personality_desc}

YOUR ROLE IN THIS PROJECT:
- Provide domain-specific insights and recommendations
- Ensure the product serves its intended purpose effectively
- Catch domain-specific issues others might miss
- Suggest features and details that make the product valuable
- Validate that the approach will resonate with the target audience

{brief_context}

{debate_instructions}

RESPONSE GUIDELINES:
- Keep responses to 2-4 sentences unless more detail is needed
- Be direct and specific with recommendations
- Explain WHY something matters, not just WHAT to do
- Reference your domain expertise when making suggestions
- If you disagree, say so clearly: "I disagree because..."
- If convinced by another agent, acknowledge it: "Actually, that's a good point..."

You are participating in a real-time debate with other agents.
This is a dynamic conversation - respond naturally, interrupt if needed, and don't be afraid to challenge ideas.
"""

    async def on_message(self, message: AgentMessage) -> None:
        """Handle incoming messages from the conversation."""
        # Store for context
        pass  # Will be called by broker when messages arrive

    async def introduce(self) -> str:
        """Introduce yourself to the team."""
        intro = await self.generate(
            f"Introduce yourself briefly to the team. You are {self.name}, "
            f"expert in {self.domain}. Mention 1-2 key things you'll focus on for this project. "
            "Keep it to 2-3 sentences.",
            system_prompt=self.system_prompt
        )
        return intro

    async def respond(self, conversation_context: list[AgentMessage]) -> str:
        """Generate a response based on conversation context."""
        # Build context from recent messages
        context = "\n".join([
            f"{msg.sender}: {msg.content}"
            for msg in conversation_context[-10:]  # Last 10 messages
        ])

        response = await self.generate(
            f"Continue this conversation as {self.name}:\n\n{context}\n\n{self.name}:",
            system_prompt=self.system_prompt
        )
        return response

    async def review(self, artifact_description: str) -> str:
        """Review a build artifact from domain perspective."""
        review = await self.generate(
            f"Review this from your domain expertise perspective:\n\n{artifact_description}\n\n"
            "Provide 2-3 specific observations (good or needs improvement).",
            system_prompt=self.system_prompt
        )
        return review


class AgentFactory:
    """Creates agents on-demand based on project requirements."""

    # Domain keywords → expert configuration
    DOMAIN_MAPPING = {
        # Fitness/Health
        "fitness": ("Fitness Planning Expert", "fitness and workout planning", "exercise routines, progressive overload, habit formation, workout tracking"),
        "workout": ("Fitness Planning Expert", "fitness and workout planning", "exercise routines, progressive overload, habit formation, workout tracking"),
        "health": ("Health & Wellness Expert", "health and wellness", "nutrition, sleep, stress management, holistic health practices"),
        "nutrition": ("Nutrition Expert", "nutrition and meal planning", "macros, meal prep, dietary requirements, healthy eating habits"),
        "diet": ("Nutrition Expert", "nutrition and meal planning", "macros, meal prep, dietary requirements, healthy eating habits"),

        # Productivity/Planning
        "productivity": ("Productivity Expert", "productivity systems", "time management, goal setting, habit tracking, focus techniques"),
        "planner": ("Planning Expert", "personal planning and organization", "goal setting, time blocking, habit tracking, life organization"),
        "habit": ("Habit Formation Expert", "habit building and behavior change", "habit stacking, cue-routine-reward, consistency strategies"),
        "goal": ("Goal Achievement Expert", "goal setting and achievement", "SMART goals, milestone tracking, motivation, accountability"),
        "budget": ("Financial Planning Expert", "personal finance and budgeting", "expense tracking, savings goals, financial habits"),

        # Creative
        "journal": ("Journaling Expert", "journaling and self-reflection", "prompt design, gratitude practice, self-discovery, therapeutic writing"),
        "creative": ("Creative Coach", "creativity and artistic expression", "creative blocks, artistic development, creative habits"),
        "writing": ("Writing Coach", "writing and content creation", "writing habits, story structure, content planning"),

        # Business
        "business": ("Business Strategy Expert", "business planning and strategy", "market analysis, competitive positioning, growth strategies"),
        "marketing": ("Marketing Expert", "marketing and brand building", "audience targeting, messaging, content marketing, brand voice"),
        "sales": ("Sales Expert", "sales and customer acquisition", "sales funnels, conversion, customer relationships"),

        # Technical
        "app": ("App Development Expert", "mobile app development", "user experience, app architecture, mobile-first design"),
        "web": ("Web Development Expert", "web development and design", "responsive design, user experience, web performance"),
        "saas": ("SaaS Expert", "software as a service products", "subscription models, user onboarding, feature prioritization"),
    }

    # Product type → builder type mapping
    BUILDER_MAPPING = {
        "printable_planner": "printable",
        "digital_planner": "printable",
        "worksheet": "printable",
        "cards": "printable",
        "journal": "printable",
        "tracker": "printable",
        "calendar": "printable",

        "book": "document",
        "ebook": "document",
        "guide": "document",
        "manual": "document",
        "course": "document",

        "landing_page": "web",
        "website": "web",
        "dashboard": "web",
        "spa": "web",
        "portfolio": "web",

        "mobile_app": "app",
        "ios_app": "app",
        "android_app": "app",
        "app": "app",
    }

    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self._active_agents: dict[str, BaseAgent] = {}

    def analyze_goal(self, goal: str, brief: "BusinessBrief" = None) -> TeamComposition:
        """Analyze the goal and determine team composition."""
        goal_lower = goal.lower()

        # Determine domain
        expert_domain = "general"
        expert_config = ("Project Expert", "project planning", "general best practices and quality standards")

        for keyword, config in self.DOMAIN_MAPPING.items():
            if keyword in goal_lower:
                expert_config = config
                expert_domain = keyword
                break

        # If we have a brief, use its product type
        builder_type = "printable"  # default
        if brief and brief.product_type:
            builder_type = self.BUILDER_MAPPING.get(brief.product_type, "printable")
        else:
            # Infer from goal
            for keyword, btype in self.BUILDER_MAPPING.items():
                if keyword in goal_lower:
                    builder_type = btype
                    break

        return TeamComposition(
            expert_domain=expert_domain,
            expert_name=expert_config[0],
            builder_type=builder_type,
            include_qc=True,
            include_planner=True,
        )

    def create_expert(self, composition: TeamComposition, brief: "BusinessBrief" = None) -> CustomExpert:
        """Create a domain expert for this project."""
        config = self.DOMAIN_MAPPING.get(
            composition.expert_domain,
            ("Project Expert", "project planning", "general best practices")
        )

        # Create domain-specific personality
        personality = create_expert_personality(config[1], config[0])

        expert = CustomExpert(
            name=config[0],
            domain=config[1],
            expertise=config[2],
            product_type=composition.builder_type,
            broker=self.broker,
            brief=brief,
            personality=personality,
        )

        self._active_agents[expert.agent_id] = expert
        logger.info(f"Created expert: {expert.name} ({expert.agent_id}) with {personality.debate_style.value} debate style")

        return expert

    def get_builder(self, builder_type: str):
        """Get the appropriate builder for the product type."""
        from .builders import get_builder_for_type

        # Map our simplified type to actual builder
        type_mapping = {
            "printable": "printable_planner",
            "document": "doc_book",
            "web": "web_landing",
            "app": "mobile_cross_platform",
        }

        actual_type = type_mapping.get(builder_type, builder_type)
        return get_builder_for_type(actual_type)

    def get_qc_agent(self):
        """Get the QC agent."""
        from .qc import QCAgent
        return QCAgent()

    def get_planner_agent(self):
        """Get the planner agent."""
        from .planner import PlannerAgent
        return PlannerAgent()

    def cleanup(self) -> None:
        """Clean up all active agents."""
        for agent_id in list(self._active_agents.keys()):
            self.broker.unsubscribe_agent(agent_id)
        self._active_agents.clear()
