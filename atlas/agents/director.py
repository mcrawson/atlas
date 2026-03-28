"""Director Agent - Layla-style real-time agent debate.

Agents actually discuss, disagree, and reach consensus.
User watches it happen live via WebSocket.
Supports dynamic topics, interruptions, streaming, and user intervention.
"""

import asyncio
import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from .message_broker import (
    MessageBroker, AgentMessage, MessageType, BuildStatus, get_broker
)
from .factory import AgentFactory, TeamComposition, CustomExpert
from .personalities import (
    AgentPersonality, get_personality, PLANNER_PERSONALITY,
    QC_PERSONALITY, DIRECTOR_PERSONALITY
)
from .memory import AgentMemory, get_memory

if TYPE_CHECKING:
    from ..projects.models import Project
    from .analyst import BusinessBrief

logger = logging.getLogger(__name__)


class BuildPhase(str, Enum):
    KICKOFF = "kickoff"
    DEBATE = "debate"
    BUILD = "build"
    REVIEW = "review"
    COMPLETE = "complete"


@dataclass
class AgentState:
    """State of an agent in the debate."""
    agent_id: str
    name: str
    personality: AgentPersonality
    current_position: Optional[str] = None
    turns_since_spoke: int = 0
    is_typing: bool = False


@dataclass
class ConversationState:
    phase: BuildPhase = BuildPhase.KICKOFF
    turns: int = 0
    consensus: bool = False
    topics_discussed: List[str] = field(default_factory=list)
    current_topic: Optional[str] = None
    topic_turn_count: int = 0
    user_messages: List[str] = field(default_factory=list)


class DirectorAgent:
    """Orchestrates Layla-style agent debate.

    Agents don't just respond once - they debate, disagree, build on ideas.
    Features:
    - Dynamic topic generation from Business Brief
    - Interruptions based on personality
    - Consensus detection
    - User participation
    - Streaming responses
    - Persistent memory
    """

    def __init__(self, project: "Project"):
        self.project = project
        self.project_id = project.id
        self.broker = get_broker(project.id)
        self.factory = AgentFactory(self.broker)
        self.memory = get_memory(project.id)
        self.state = ConversationState()
        self.brief: Optional["BusinessBrief"] = None
        self.expert: Optional[CustomExpert] = None
        self.composition: Optional[TeamComposition] = None
        self.conversation_history: List[dict] = []
        self.build_output = None

        # Agent states for dynamic turn-taking
        self.agent_states: dict[str, AgentState] = {}

        self._llm = None
        self.agent_id = "director"
        self.personality = DIRECTOR_PERSONALITY
        self.broker.subscribe_agent(self.agent_id, self._on_message)

        # User message queue
        self._user_message_queue: asyncio.Queue = asyncio.Queue()

    async def _get_llm(self):
        if self._llm is None:
            try:
                from openai import AsyncOpenAI
                api_key = os.environ.get("OPENAI_API_KEY")
                if api_key:
                    self._llm = AsyncOpenAI(api_key=api_key)
            except ImportError:
                pass
        return self._llm

    async def _on_message(self, message: AgentMessage):
        """Handle incoming messages."""
        self.state.turns += 1
        self.conversation_history.append(message.to_dict())

        # Track user messages for response
        if message.message_type == MessageType.USER:
            await self._user_message_queue.put(message)

    async def handle_user_message(self, content: str) -> None:
        """Handle a message from the user joining the conversation."""
        # Create and broadcast user message
        msg = AgentMessage(
            sender="user",
            content=content,
            message_type=MessageType.USER,
        )
        await self.broker.broadcast(msg)
        self.conversation_history.append(msg.to_dict())

        # Director acknowledges
        await self._say(
            "director",
            "Good point. Let me get the team's thoughts on that.",
            MessageType.SYSTEM
        )

        # Route to most relevant agent
        await self._route_user_message(content)

    async def _route_user_message(self, content: str) -> None:
        """Determine which agent should respond to user and get response."""
        # Analyze content to find best responder
        content_lower = content.lower()

        # Simple keyword matching for routing
        if any(word in content_lower for word in ["quality", "sellable", "issue", "problem", "concern"]):
            responder_id = "qc"
            responder_name = "QC"
            responder_role = "quality control specialist"
        elif any(word in content_lower for word in ["plan", "structure", "organize", "layout", "design"]):
            responder_id = "planner"
            responder_name = "Planner"
            responder_role = "build planning specialist"
        elif self.expert:
            responder_id = self.expert.agent_id
            responder_name = self.expert.name
            responder_role = f"domain expert in {self.expert.domain}"
        else:
            responder_id = "planner"
            responder_name = "Planner"
            responder_role = "build planning specialist"

        response = await self._generate(
            responder_name,
            responder_role,
            f"The user said: '{content}'. Respond directly to them, addressing their point."
        )
        await self._say(responder_id, response)

    async def _say(
        self,
        sender: str,
        content: str,
        msg_type: MessageType = MessageType.DISCUSSION
    ):
        """Send a message and stream to UI."""
        msg = AgentMessage(
            sender=sender,
            content=content,
            message_type=msg_type,
        )
        await self.broker.broadcast(msg)
        self.conversation_history.append(msg.to_dict())

        # Update turn tracking
        for agent_id, state in self.agent_states.items():
            if agent_id == sender:
                state.turns_since_spoke = 0
            else:
                state.turns_since_spoke += 1

        # Small delay so UI can show messages appearing
        await asyncio.sleep(0.3)

    async def _generate(
        self,
        agent_name: str,
        role: str,
        prompt: str,
        personality: AgentPersonality = None,
        stream: bool = True
    ) -> str:
        """Generate agent response with personality and optional streaming."""
        llm = await self._get_llm()
        if not llm:
            return f"[{agent_name}] I have thoughts on this..."

        # Get personality
        if personality is None:
            personality = get_personality(agent_name.lower().split()[0])

        # Build system prompt with personality
        personality_section = personality.to_prompt_description()
        debate_instructions = personality.get_debate_instructions()

        system = f"""You are {agent_name}, {role}.

{personality_section}

You're in a live debate with other agents about building a product.
{debate_instructions}

RESPONSE GUIDELINES:
- Keep responses to 2-4 sentences
- Be direct and specific
- Sound natural, like a real conversation
- If disagreeing, be clear: "I disagree because..."
- If convinced, acknowledge it: "Actually, that's a good point..."

Current project: {self.brief.product_name if self.brief else self.project.name}
"""

        # Include recent conversation for context
        recent = self.conversation_history[-8:] if self.conversation_history else []
        context = "\n".join([f"{m['sender']}: {m['content']}" for m in recent])

        # Include relevant memories
        memory_context = self.memory.format_memories_for_prompt(prompt)

        full_prompt = f"Recent conversation:\n{context}\n{memory_context}\n\nNow respond to: {prompt}"

        agent_id = agent_name.lower().replace(" ", "_")

        try:
            if stream:
                return await self._generate_streaming(agent_id, system, full_prompt)
            else:
                response = await llm.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": full_prompt},
                    ],
                    max_tokens=200,
                    temperature=0.8,
                )
                return response.choices[0].message.content

        except Exception as e:
            logger.warning(f"LLM error: {e}")
            return f"I think we should focus on the core functionality first."

    async def _generate_streaming(
        self,
        agent_id: str,
        system: str,
        prompt: str
    ) -> str:
        """Generate with word-by-word streaming to UI."""
        llm = await self._get_llm()
        if not llm:
            return "I have thoughts on this..."

        # Show typing indicator
        await self.broker.push_typing(agent_id, True)

        try:
            stream = await llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=200,
                temperature=0.8,
                stream=True
            )

            full_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_response += text
                    # Push chunk to UI
                    await self.broker.push_text_chunk(agent_id, text)

            return full_response

        finally:
            # Hide typing indicator
            await self.broker.push_typing(agent_id, False)

    async def run(self, brief: "BusinessBrief" = None) -> dict:
        """Run the full agent debate."""
        self.brief = brief
        logger.info(f"Director starting debate for project {self.project_id}")

        try:
            # Phase 1: Kickoff - Introduce the team
            await self._kickoff()

            # Phase 2: Debate - Agents discuss approach (dynamic rounds)
            await self._dynamic_debate()

            # Phase 3: Build decision and execution
            await self._build_decision()

            # Phase 4: Review
            await self._review()

            # Store conversation in memory
            self.memory.store_conversation(
                self.conversation_history,
                summary=f"Debate for {self.brief.product_name if self.brief else self.project.name}"
            )

            # Generate debrief summary
            debrief = await self._generate_debrief()
            await self._say("director", debrief, MessageType.DECISION)

            self.state.phase = BuildPhase.COMPLETE
            await self._say(
                "director",
                "Debate complete. Ready for your review.",
                MessageType.DECISION
            )

            return {
                "success": True,
                "phase": self.state.phase.value,
                "turns": self.state.turns,
            }

        except Exception as e:
            logger.exception(f"Director error: {e}")
            await self._say("director", f"Error: {str(e)}", MessageType.SYSTEM)
            return {"success": False, "error": str(e), "phase": self.state.phase.value}

        finally:
            self.factory.cleanup()

    async def _kickoff(self):
        """Phase 1: Introduce the team and goal."""
        self.state.phase = BuildPhase.KICKOFF

        await self.broker.push_status(BuildStatus(
            phase="kickoff", progress=5, current_action="Assembling team...", agent="director"
        ))

        # Analyze goal
        goal = ""
        if self.brief:
            goal = f"{self.brief.product_name}: {self.brief.executive_summary}"
        else:
            goal = self.project.description or self.project.name

        self.composition = self.factory.analyze_goal(goal, self.brief)

        await self._say(
            "director",
            f"Alright team, we're building: **{self.brief.product_name if self.brief else self.project.name}**",
            MessageType.SYSTEM
        )
        await asyncio.sleep(0.5)

        # Spawn expert and initialize agent states
        self.expert = self.factory.create_expert(self.composition, self.brief)

        # Initialize agent states
        self.agent_states = {
            "director": AgentState(
                agent_id="director",
                name="Director",
                personality=DIRECTOR_PERSONALITY
            ),
            "planner": AgentState(
                agent_id="planner",
                name="Planner",
                personality=PLANNER_PERSONALITY
            ),
            "qc": AgentState(
                agent_id="qc",
                name="QC",
                personality=QC_PERSONALITY
            ),
            self.expert.agent_id: AgentState(
                agent_id=self.expert.agent_id,
                name=self.expert.name,
                personality=self.expert.personality
            ),
        }

        # Expert introduces
        intro = await self._generate(
            self.expert.name,
            f"domain expert in {self.expert.domain}",
            "Introduce yourself briefly and share your first impression of this project. What excites you? What concerns you?",
            personality=self.expert.personality
        )
        await self._say(self.expert.agent_id, intro)

        # Planner introduces
        planner_intro = await self._generate(
            "Planner",
            "build planning specialist",
            "Introduce yourself and share your initial thoughts on how to approach this build.",
            personality=PLANNER_PERSONALITY
        )
        await self._say("planner", planner_intro)

        # QC introduces
        qc_intro = await self._generate(
            "QC",
            "quality control specialist focused on sellability",
            "Introduce yourself briefly. What will you be watching for to make sure this product is sellable?",
            personality=QC_PERSONALITY
        )
        await self._say("qc", qc_intro)

        await self._say(
            "director",
            "Great, team's assembled. Let's discuss the approach.",
            MessageType.SYSTEM
        )

    async def _generate_topics(self) -> list[str]:
        """Generate 3-5 debate topics from Business Brief."""
        llm = await self._get_llm()
        if not llm or not self.brief:
            # Fallback to default topics
            return [
                "What should be the core structure of this product?",
                "What features are essential vs nice-to-have?",
                "What could go wrong and how do we prevent it?",
            ]

        brief_context = f"""
Product: {self.brief.product_name}
Type: {self.brief.product_type}
Target Customer: {self.brief.target_customer.get('description', 'Unknown')}
Core Value: {self.brief.executive_summary}
Success Criteria: {', '.join(str(c) for c in self.brief.success_criteria[:3])}
"""

        try:
            response = await llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You generate debate topics for a product design team. Return 3-5 specific, actionable topics as a JSON array of strings."},
                    {"role": "user", "content": f"Generate debate topics for:\n{brief_context}\n\nReturn ONLY a JSON array of topic strings."},
                ],
                max_tokens=300,
                temperature=0.7,
            )

            import json
            content = response.choices[0].message.content
            # Extract JSON from response
            if "[" in content:
                start = content.index("[")
                end = content.rindex("]") + 1
                topics = json.loads(content[start:end])
                return topics[:5]

        except Exception as e:
            logger.warning(f"Failed to generate topics: {e}")

        return [
            "What should be the core structure of this product?",
            "What features are essential vs nice-to-have?",
            "What could go wrong and how do we prevent it?",
        ]

    async def _dynamic_debate(self):
        """Phase 2: Dynamic agent debate with interruptions and consensus detection."""
        self.state.phase = BuildPhase.DEBATE

        await self.broker.push_status(BuildStatus(
            phase="debate", progress=20, current_action="Generating topics...", agent="director"
        ))

        # Generate dynamic topics from brief
        topics = await self._generate_topics()

        for i, topic in enumerate(topics):
            self.state.current_topic = topic
            self.state.topic_turn_count = 0

            await self._say("director", f"**Topic {i+1}:** {topic}", MessageType.SYSTEM)
            await asyncio.sleep(0.3)

            # Assign initial positions to create debate tension
            await self._assign_positions(topic)

            # Dynamic turn-taking until consensus or max turns
            max_topic_turns = 8
            while self.state.topic_turn_count < max_topic_turns:
                # Determine who should speak next
                speaker = await self._get_next_speaker(topic)
                if not speaker:
                    break

                # Generate response
                response = await self._generate(
                    speaker.name,
                    self._get_role_description(speaker.agent_id),
                    f"Respond to the current discussion about: {topic}",
                    personality=speaker.personality
                )
                await self._say(speaker.agent_id, response)
                self.state.topic_turn_count += 1

                # Check for interruptions
                interrupter = await self._check_interruptions(speaker.agent_id, response)
                if interrupter:
                    interrupt_response = await self._generate(
                        interrupter.name,
                        self._get_role_description(interrupter.agent_id),
                        f"You feel strongly about {topic} and need to jump in. Interrupt with your point.",
                        personality=interrupter.personality
                    )
                    await self._say(
                        interrupter.agent_id,
                        interrupt_response,
                        MessageType.INTERRUPTION
                    )
                    self.state.topic_turn_count += 1

                # Check for consensus
                if await self._check_consensus(topic):
                    self.state.consensus = True
                    break

            await self.broker.push_status(BuildStatus(
                phase="debate",
                progress=20 + (i + 1) * (60 // len(topics)),
                current_action=f"Discussed: {topic[:30]}...",
                agent="director"
            ))

            self.state.topics_discussed.append(topic)

            # Remember decisions made
            if self.state.consensus:
                await self._record_topic_decision(topic)

        await self._say(
            "director",
            "Good discussion. I think we have alignment on the approach.",
            MessageType.DECISION
        )

    async def _assign_positions(self, topic: str) -> None:
        """Assign initial positions to agents to create debate tension."""
        llm = await self._get_llm()
        if not llm:
            return

        try:
            agents = list(self.agent_states.keys())
            agent_list = ", ".join([s.name for s in self.agent_states.values()])

            response = await llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You assign different perspectives to agents for a debate. Agents: {agent_list}. Return JSON with agent_id -> position mapping."},
                    {"role": "user", "content": f"Topic: {topic}\n\nAssign different but reasonable positions to create healthy debate. Return ONLY a JSON object."},
                ],
                max_tokens=200,
                temperature=0.8,
            )

            import json
            content = response.choices[0].message.content
            if "{" in content:
                start = content.index("{")
                end = content.rindex("}") + 1
                positions = json.loads(content[start:end])

                for agent_id, position in positions.items():
                    if agent_id in self.agent_states:
                        self.agent_states[agent_id].current_position = position
                        self.broker.update_position(agent_id, topic, position)

        except Exception as e:
            logger.debug(f"Position assignment skipped: {e}")

    async def _get_next_speaker(self, topic: str) -> Optional[AgentState]:
        """Determine which agent should speak next based on dynamics."""
        candidates = [
            s for s in self.agent_states.values()
            if s.agent_id != "director"
        ]

        if not candidates:
            return None

        # Weight by personality traits and turns since spoke
        weights = []
        for agent in candidates:
            weight = 1.0

            # Higher interruption tendency = more likely to speak
            weight += agent.personality.interruption_tendency * 0.5

            # More turns since spoke = more likely
            weight += min(agent.turns_since_spoke * 0.3, 1.5)

            # QC is more likely to speak if others have been talking
            if agent.agent_id == "qc" and agent.turns_since_spoke >= 2:
                weight += 0.5

            weights.append(weight)

        # Weighted random selection
        total = sum(weights)
        weights = [w / total for w in weights]

        return random.choices(candidates, weights=weights, k=1)[0]

    async def _check_interruptions(
        self,
        current_speaker: str,
        message: str
    ) -> Optional[AgentState]:
        """Check if any agent wants to interrupt based on personality."""
        for agent_id, agent in self.agent_states.items():
            if agent_id == current_speaker or agent_id == "director":
                continue

            # Roll against interruption tendency
            if random.random() < agent.personality.interruption_tendency * 0.3:
                # QC more likely to interrupt if they spot an issue
                if agent_id == "qc":
                    issue_words = ["might", "could", "maybe", "probably", "assume"]
                    if any(word in message.lower() for word in issue_words):
                        return agent

                # Expert interrupts on domain expertise
                if "expert" in agent_id and self.expert:
                    domain_words = self.expert.domain.lower().split()
                    if any(word in message.lower() for word in domain_words):
                        return agent

        return None

    async def _check_consensus(self, topic: str) -> bool:
        """Detect when agents have reached agreement."""
        if self.state.topic_turn_count < 3:
            return False

        recent = self.conversation_history[-6:]
        if len(recent) < 3:
            return False

        # Look for agreement markers
        agreement_markers = [
            "agree", "good point", "that works", "makes sense",
            "let's go with", "sounds good", "I'm on board",
            "yes", "exactly", "right"
        ]

        agreement_count = sum(
            1 for msg in recent
            if any(marker in msg.get("content", "").lower() for marker in agreement_markers)
        )

        # If 2+ recent messages show agreement, we have consensus
        return agreement_count >= 2

    async def _record_topic_decision(self, topic: str) -> None:
        """Record the decision made on a topic to memory."""
        recent = self.conversation_history[-5:]
        decision_summary = " ".join(m.get("content", "")[:100] for m in recent)

        self.memory.remember_decision(
            topic=topic,
            decision=decision_summary[:300],
            context={"phase": "debate", "product": self.brief.product_name if self.brief else ""},
            participants=[s.name for s in self.agent_states.values()],
        )

    def _get_role_description(self, agent_id: str) -> str:
        """Get role description for an agent."""
        roles = {
            "director": "project orchestrator",
            "planner": "build planning specialist",
            "qc": "quality control specialist focused on sellability",
        }
        if "expert" in agent_id and self.expert:
            return f"domain expert in {self.expert.domain}"
        if "builder" in agent_id:
            return f"{self.composition.builder_type} product builder"
        return roles.get(agent_id, "team member")

    async def _parallel_responses(
        self,
        agents: list[AgentState],
        prompt: str
    ) -> list[tuple[str, str]]:
        """Get responses from multiple agents concurrently."""
        # Show all agents typing
        for agent in agents:
            await self.broker.push_typing(agent.agent_id, True)

        # Generate in parallel
        tasks = [
            self._generate(
                agent.name,
                self._get_role_description(agent.agent_id),
                prompt,
                personality=agent.personality,
                stream=False  # Don't stream parallel responses
            )
            for agent in agents
        ]
        responses = await asyncio.gather(*tasks)

        # Stop all typing
        for agent in agents:
            await self.broker.push_typing(agent.agent_id, False)

        # Return with small delays so they don't all appear at once
        results = []
        for i, (agent, response) in enumerate(zip(agents, responses)):
            await asyncio.sleep(0.3 * i)
            results.append((agent.agent_id, response))
            await self._say(agent.agent_id, response)

        return results

    async def _build_decision(self):
        """Phase 3: Decide on build approach and execute."""
        self.state.phase = BuildPhase.BUILD

        await self.broker.push_status(BuildStatus(
            phase="build", progress=80, current_action="Finalizing build plan...", agent="director"
        ))

        # Summarize decision
        summary = await self._generate(
            "Director",
            "project orchestrator",
            "Summarize what the team decided. What are we building and how?",
            personality=DIRECTOR_PERSONALITY
        )
        await self._say("director", summary, MessageType.DECISION)

        # Builder confirms
        builder_confirm = await self._generate(
            "Builder",
            f"{self.composition.builder_type} product builder",
            "Confirm you understand the plan and are ready to build"
        )
        await self._say(f"builder_{self.composition.builder_type}", builder_confirm)

        # Execute actual build if builder available
        await self._execute_build()

    async def _execute_build(self):
        """Execute the actual build using the appropriate builder."""
        try:
            builder = self.factory.get_builder(self.composition.builder_type)
            if not builder:
                logger.info("No builder available for execution")
                return

            await self._say(
                f"builder_{self.composition.builder_type}",
                "Building based on our decisions...",
                MessageType.PROGRESS
            )

            await self.broker.push_status(BuildStatus(
                phase="building",
                progress=85,
                current_action=f"Generating {self.composition.builder_type}...",
                agent=f"builder_{self.composition.builder_type}"
            ))

            # Create build context
            from .builders.base import BuildContext
            build_context = BuildContext(
                project_name=self.project.name,
                project_description=self.project.description or "",
                business_brief=self.brief.to_dict() if self.brief else {},
                debate_summary=self._summarize_debate(),
            )

            # Execute build
            output = await builder.build(build_context)
            self.build_output = output

            # Announce completion
            if output and output.preview_url:
                await self.broker.push_deliverable(
                    name=f"{self.project.name} - {self.composition.builder_type}",
                    preview_url=output.preview_url,
                    download_url=output.files.get("index.html", "") if output.files else ""
                )

        except Exception as e:
            logger.warning(f"Build execution skipped: {e}")

    def _summarize_debate(self) -> str:
        """Create a summary of the debate for the builder."""
        if not self.conversation_history:
            return ""

        # Get last 10 messages
        recent = self.conversation_history[-10:]
        summary_parts = []
        for msg in recent:
            if msg.get("message_type") in ["decision", "discussion"]:
                summary_parts.append(f"{msg['sender']}: {msg['content'][:100]}")

        return "\n".join(summary_parts)

    async def _generate_debrief(self) -> str:
        """Generate a debrief summary of the debate."""
        # Collect key decisions from memory
        decisions = self.memory.get_relevant_memories("decision", limit=10)
        decisions_text = "\n".join([
            f"- {d.get('topic', 'Topic')}: {d.get('decision', '')[:100]}"
            for d in decisions
        ]) if decisions else "No decisions recorded."

        # Get topics discussed
        topics = [msg.get("content", "")[:80] for msg in self.conversation_history
                  if "Topic" in msg.get("content", "")][:5]
        topics_text = "\n".join([f"- {t}" for t in topics]) if topics else "General discussion"

        # Count participants
        participants = set(msg.get("sender", "") for msg in self.conversation_history
                          if msg.get("sender") not in ["director", "system", ""])

        debrief = f"""📋 **DEBRIEF SUMMARY**

**Product:** {self.brief.product_name if self.brief else self.project.name}

**Participants:** {', '.join(p.replace('_', ' ').title() for p in participants)}

**Topics Discussed:**
{topics_text}

**Key Decisions:**
{decisions_text}

**Next Steps:**
- Review the build plan
- Approve to start building
- QC will validate the final output"""

        return debrief

    async def _review(self):
        """Phase 4: Final review with QC validation."""
        self.state.phase = BuildPhase.REVIEW

        await self.broker.push_status(BuildStatus(
            phase="review", progress=95, current_action="Final review...", agent="qc"
        ))

        # If we have build output, QC validates it
        if self.build_output:
            try:
                from .qc import QCAgent, QCVerdict
                from .ollama_provider import create_multi_provider_agent_manager

                # QC needs router/providers to use LLM evaluation
                # Create a fresh agent manager for QC
                try:
                    agent_manager = create_multi_provider_agent_manager()
                    qc = QCAgent(
                        router=agent_manager.router,
                        providers=agent_manager.providers
                    )
                except Exception as e:
                    logger.warning(f"Could not initialize QC with providers: {e}")
                    qc = QCAgent()  # Will use basic evaluation

                # Convert build_output to dict if needed
                build_dict = self.build_output.to_dict() if hasattr(self.build_output, 'to_dict') else self.build_output
                brief_dict = self.brief.to_dict() if hasattr(self.brief, 'to_dict') else (self.brief or {})

                qc_report = await qc.check_build(
                    output=build_dict,
                    brief=brief_dict,
                    mockup=None,  # Could add mockup support later
                    attempt=1
                )

                if qc_report.verdict in [QCVerdict.PASS, QCVerdict.PASS_WITH_NOTES]:
                    # Format strengths from checks_passed
                    strengths = qc_report.checks_passed[:3] if qc_report.checks_passed else ["Quality verified"]
                    await self._say(
                        "qc",
                        f"Build passes QC! Sellability: {qc_report.sellability_score}/100\n"
                        f"Strengths: {', '.join(strengths)}",
                        MessageType.QC_REPORT
                    )
                else:
                    # Format issues from QCIssue objects
                    issue_strs = [issue.description for issue in qc_report.issues[:3]]
                    await self._say(
                        "qc",
                        f"Build needs revision.\nIssues: {', '.join(issue_strs)}\n"
                        f"Fix: {qc_report.fix_instructions}",
                        MessageType.CONCERN
                    )

                    # Record lesson learned
                    first_issue = qc_report.issues[0].description if qc_report.issues else 'various'
                    self.memory.add_lesson(
                        lesson=f"QC found issues: {first_issue}",
                        context=f"During review of {self.composition.builder_type}"
                    )

            except Exception as e:
                logger.debug(f"QC validation skipped: {e}")
                # Fallback to generated review
                qc_final = await self._generate(
                    "QC",
                    "quality control specialist",
                    "Give your final approval or any last concerns before we proceed",
                    personality=QC_PERSONALITY
                )
                await self._say("qc", qc_final, MessageType.QC_REPORT)
        else:
            # No build output - just get verbal review
            qc_final = await self._generate(
                "QC",
                "quality control specialist",
                "Give your final approval or any last concerns before we proceed",
                personality=QC_PERSONALITY
            )
            await self._say("qc", qc_final, MessageType.QC_REPORT)

        # Expert final blessing
        expert_final = await self._generate(
            self.expert.name,
            f"domain expert in {self.expert.domain}",
            "Any final advice before we start building?",
            personality=self.expert.personality
        )
        await self._say(self.expert.agent_id, expert_final)

        await self.broker.push_status(BuildStatus(
            phase="complete", progress=100, current_action="Ready for build", agent="director"
        ))


async def run_director(project: "Project", brief: "BusinessBrief" = None) -> dict:
    """Convenience function to run the director."""
    director = DirectorAgent(project)
    return await director.run(brief)
