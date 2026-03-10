"""
ATLAS Team Conversation

A multi-agent conversation where all agents with concerns participate
in a single discussion. Users can address all feedback at once rather
than talking to each agent separately.
"""

import asyncio
import aiohttp
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class AgentConcern:
    """A concern raised by an agent."""
    agent: str
    category: str
    severity: str
    question: str
    context: str
    status: str = "open"  # open, addressed, resolved
    resolution: str = ""


@dataclass
class TeamMessage:
    """A message in the team conversation."""
    role: str  # "user" or agent name (tinker, oracle, etc.)
    content: str
    timestamp: str = ""
    concern_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "concern_ids": self.concern_ids,
        }


class TeamConversation:
    """
    Multi-agent conversation where the whole team participates.

    Agents take turns raising concerns, the user responds,
    and agents can follow up or move on.
    """

    AGENTS = {
        "sketch": {
            "name": "Sketch",
            "icon": "📐",
            "role": "Strategic Planning",
            "focus": ["requirements clarity", "scope definition", "user stories"],
        },
        "architect": {
            "name": "Architect",
            "icon": "🏗️",
            "role": "Technical Design",
            "focus": ["technical feasibility", "architecture", "scalability"],
        },
        "tinker": {
            "name": "Tinker",
            "icon": "🔧",
            "role": "Implementation",
            "focus": ["implementation details", "edge cases", "error handling"],
        },
        "oracle": {
            "name": "Oracle",
            "icon": "🔮",
            "role": "Quality & Risk",
            "focus": ["risks", "dependencies", "quality concerns"],
        },
        "launch": {
            "name": "Launch",
            "icon": "🚀",
            "role": "Deployment",
            "focus": ["deployment", "distribution", "go-to-market"],
        },
    }

    TEAM_ANALYSIS_PROMPT = """You are analyzing a project specification as a team of experts.

PROJECT SPECIFICATION:
{spec_content}

PREVIOUS AGENT REVIEWS (from sprint meeting):
{previous_reviews}

Analyze this spec from multiple perspectives and identify concerns that need discussion.

For EACH agent that has concerns, list them. Only include agents that actually have concerns.
Focus on the most important issues - don't nitpick.

Agents and their focus areas:
- Tinker (🔧 Implementation): implementation details, edge cases, error handling, testing
- Oracle (🔮 Quality & Risk): risks, dependencies, security, quality concerns
- Architect (🏗️ Technical Design): architecture, scalability, technical feasibility
- Launch (🚀 Deployment): deployment, distribution, platform requirements

Respond with a JSON object:
{{
    "team_assessment": "Brief 1-2 sentence overall assessment",
    "agents_with_concerns": [
        {{
            "agent": "tinker|oracle|architect|launch",
            "concerns": [
                {{
                    "category": "implementation|risk|architecture|deployment|etc",
                    "severity": "critical|important|minor",
                    "question": "The specific question or concern",
                    "context": "Why this matters (1 sentence)"
                }}
            ]
        }}
    ],
    "ready_to_proceed": true/false
}}

If no agents have significant concerns, return an empty agents_with_concerns array.

RESPOND ONLY WITH THE JSON OBJECT."""

    TEAM_FOLLOWUP_PROMPT = """Continue the team review conversation.

PROJECT CONTEXT:
{spec_summary}

CONVERSATION SO FAR:
{conversation}

OUTSTANDING CONCERNS:
{outstanding_concerns}

USER'S LATEST MESSAGE:
{user_message}

You are facilitating a team discussion. Based on the user's response:

1. Have the relevant agent(s) acknowledge what was addressed
2. If the answer resolves concerns, mark them as addressed
3. If clarification is needed, have the agent ask a follow-up
4. If moving to a new topic, have the next agent with concerns speak up
5. When all concerns are addressed, summarize and wrap up

IMPORTANT RULES:
- Each agent should speak in character with their icon
- Keep responses concise (2-3 sentences per agent)
- Multiple agents can respond in one turn if relevant
- Be collaborative, not interrogating
- When done, clearly indicate the review is complete

Respond with a JSON object:
{{
    "messages": [
        {{
            "agent": "tinker|oracle|architect|launch",
            "content": "What this agent says"
        }}
    ],
    "concerns_addressed": ["concern_id_1", "concern_id_2"],
    "is_complete": true/false,
    "summary": "If complete, brief summary of what was decided (or empty)"
}}

RESPOND ONLY WITH THE JSON OBJECT."""

    ROUND_TABLE_FOLLOWUP_PROMPT = """Continue the round-table review. Focus ONLY on {current_agent}'s concerns.

PROJECT CONTEXT:
{spec_summary}

{current_agent_upper}'S OPEN CONCERNS:
{agent_concerns}

CONVERSATION SO FAR:
{conversation}

USER'S LATEST MESSAGE:
{user_message}

You are {current_agent}. Review the user's response and:
1. Acknowledge what was addressed
2. If your concerns are resolved, say so clearly
3. If you need clarification, ask ONE follow-up question
4. Be concise (2-3 sentences max)

{other_agents_context}

Respond with a JSON object:
{{
    "messages": [
        {{
            "agent": "{current_agent}",
            "content": "Your response as {current_agent}"
        }}
    ],
    "concerns_addressed": ["concern_id_1", "concern_id_2"],
    "all_my_concerns_resolved": true/false
}}

RESPOND ONLY WITH THE JSON OBJECT."""

    # Agent speaking order for round-table mode
    AGENT_ORDER = ["tinker", "oracle", "architect", "launch", "finisher"]

    def __init__(
        self,
        openai_api_key: str = None,
        openai_model: str = "gpt-4o-mini",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3",
        mode: str = "free_form",  # "free_form" or "round_table"
    ):
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self._using_openai = bool(openai_api_key)
        self.mode = mode

        # Conversation state
        self.messages: List[TeamMessage] = []
        self.concerns: Dict[str, AgentConcern] = {}  # id -> concern
        self.is_complete: bool = False
        self.summary: str = ""

        # Round-table mode state
        self.current_agent_index: int = 0
        self.agents_with_concerns: List[str] = []  # Agents that have concerns, in order
        self.agent_concerns_map: Dict[str, List[str]] = {}  # agent -> list of concern_ids

        # Project context
        self.project_name: str = ""
        self.spec_content: str = ""

    @property
    def current_agent(self) -> Optional[str]:
        """Get the current agent in round-table mode."""
        if not self.agents_with_concerns:
            return None
        if self.current_agent_index >= len(self.agents_with_concerns):
            return None
        return self.agents_with_concerns[self.current_agent_index]

    def get_agent_open_concerns(self, agent: str) -> List[AgentConcern]:
        """Get open concerns for a specific agent."""
        concern_ids = self.agent_concerns_map.get(agent, [])
        return [self.concerns[cid] for cid in concern_ids if self.concerns[cid].status == "open"]

    def advance_to_next_agent(self) -> Optional[str]:
        """Move to the next agent with open concerns. Returns new agent or None if done."""
        while self.current_agent_index < len(self.agents_with_concerns):
            current = self.agents_with_concerns[self.current_agent_index]
            if self.get_agent_open_concerns(current):
                return current
            self.current_agent_index += 1
        return None

    async def start(self, project_name: str, spec_content: str, previous_reviews: List[Dict] = None) -> List[Dict]:
        """Start the team conversation by gathering all concerns."""
        self.project_name = project_name
        self.spec_content = spec_content

        # Format previous reviews
        reviews_text = ""
        if previous_reviews:
            for review in previous_reviews:
                reviews_text += f"\n{review.get('agent_name', 'Unknown')} ({review.get('verdict', 'pending')}):\n"
                reviews_text += f"  {review.get('summary', '')}\n"
                if review.get('concerns'):
                    reviews_text += f"  Concerns: {', '.join(review.get('concerns', []))}\n"

        # Analyze with the team
        analysis = await self._analyze_with_team(reviews_text)

        if not analysis.get("agents_with_concerns"):
            # No concerns from the team
            self.is_complete = True
            self.summary = analysis.get("team_assessment", "The team has no major concerns.")

            return [{
                "agent": "team",
                "icon": "👥",
                "content": f"**Team Assessment:** {self.summary}\n\nNo major concerns from the team. You're ready to proceed!"
            }]

        # Build concerns list and track by agent
        opening_messages = []
        concern_id = 0

        # Add team assessment first
        opening_messages.append({
            "agent": "team",
            "icon": "👥",
            "content": f"**Team Assessment:** {analysis.get('team_assessment', 'Let us review this together.')}"
        })

        # Process agents in the defined order for round-table mode
        agents_in_analysis = {d.get("agent"): d for d in analysis.get("agents_with_concerns", [])}

        # Build ordered list of agents with concerns
        for agent in self.AGENT_ORDER:
            if agent in agents_in_analysis:
                self.agents_with_concerns.append(agent)
                self.agent_concerns_map[agent] = []

        # Also add any agents not in AGENT_ORDER (shouldn't happen but be safe)
        for agent_data in analysis.get("agents_with_concerns", []):
            agent = agent_data.get("agent", "unknown")
            if agent not in self.agents_with_concerns:
                self.agents_with_concerns.append(agent)
                self.agent_concerns_map[agent] = []

        # Now process concerns for each agent
        for agent_data in analysis.get("agents_with_concerns", []):
            agent = agent_data.get("agent", "unknown")
            agent_info = self.AGENTS.get(agent, {"name": agent.title(), "icon": "💬"})

            concerns_text = []
            for concern in agent_data.get("concerns", []):
                concern_id += 1
                cid = f"{agent}_{concern_id}"

                self.concerns[cid] = AgentConcern(
                    agent=agent,
                    category=concern.get("category", "general"),
                    severity=concern.get("severity", "important"),
                    question=concern.get("question", ""),
                    context=concern.get("context", ""),
                )

                # Track concern by agent
                if agent in self.agent_concerns_map:
                    self.agent_concerns_map[agent].append(cid)

                severity_icon = {"critical": "🔴", "important": "🟡", "minor": "🟢"}.get(
                    concern.get("severity", "important"), "🟡"
                )
                concerns_text.append(f"{severity_icon} {concern.get('question', '')}")

            # In round-table mode, only show first agent's concerns now
            # Other agents will present when it's their turn
            if self.mode == "round_table":
                # Store for later but don't add to opening messages yet
                continue

            # Free-form mode: show all agents' concerns at once
            if concerns_text:
                message_content = "\n".join(concerns_text)
                if len(concerns_text) > 1:
                    message_content = "I have a few items:\n" + message_content

                opening_messages.append({
                    "agent": agent,
                    "icon": agent_info["icon"],
                    "content": message_content
                })

        # In round-table mode, show roster and first agent presents
        if self.mode == "round_table" and self.agents_with_concerns:
            # Show the roster of agents present
            roster = []
            for i, agent in enumerate(self.agents_with_concerns):
                info = self.AGENTS.get(agent, {"name": agent.title(), "icon": "💬"})
                concern_count = len(self.agent_concerns_map.get(agent, []))
                if i == 0:
                    roster.append(f"  → {info['icon']} **{info['name']}** (speaking) - {concern_count} concern(s)")
                else:
                    roster.append(f"    {info['icon']} {info['name']} - {concern_count} concern(s)")

            opening_messages.append({
                "agent": "system",
                "icon": "📋",
                "content": f"**Round-Table Review**\n\nAgents present:\n" + "\n".join(roster)
            })

            # First agent presents their concerns
            first_agent = self.agents_with_concerns[0]
            first_info = self.AGENTS.get(first_agent, {"name": first_agent.title(), "icon": "💬"})
            first_concerns = self.get_agent_open_concerns(first_agent)

            severity_icons = {"critical": "🔴", "important": "🟡", "minor": "🟢"}
            concerns_text = [
                f"{severity_icons.get(c.severity, '🟡')} {c.question}"
                for c in first_concerns
            ]

            message_content = "\n".join(concerns_text)
            if len(concerns_text) > 1:
                message_content = "I have a few items to discuss:\n" + message_content

            opening_messages.append({
                "agent": first_agent,
                "icon": first_info["icon"],
                "content": message_content
            })

        # Store messages
        for msg in opening_messages:
            self.messages.append(TeamMessage(
                role=msg["agent"],
                content=msg["content"],
                timestamp=datetime.now().isoformat(),
            ))

        return opening_messages

    async def respond(self, user_message: str) -> List[Dict]:
        """Process user's response and continue the conversation."""
        # Add user message
        self.messages.append(TeamMessage(
            role="user",
            content=user_message,
            timestamp=datetime.now().isoformat(),
        ))

        # Route to appropriate mode
        if self.mode == "round_table":
            return await self._respond_round_table(user_message)
        else:
            return await self._respond_free_form(user_message)

    async def _respond_free_form(self, user_message: str) -> List[Dict]:
        """Free-form mode: all agents can respond."""
        # Get outstanding concerns
        outstanding = [
            f"- {c.agent.title()}: {c.question}"
            for cid, c in self.concerns.items()
            if c.status == "open"
        ]

        if not outstanding:
            self.is_complete = True
            return [{
                "agent": "team",
                "icon": "👥",
                "content": "All concerns have been addressed. Great discussion!"
            }]

        # Generate team response
        followup = await self._generate_followup(user_message, outstanding)

        response_messages = []

        for msg in followup.get("messages", []):
            agent = msg.get("agent", "team")
            agent_info = self.AGENTS.get(agent, {"name": agent.title(), "icon": "💬"})

            response_messages.append({
                "agent": agent,
                "icon": agent_info.get("icon", "💬"),
                "content": msg.get("content", "")
            })

            self.messages.append(TeamMessage(
                role=agent,
                content=msg.get("content", ""),
                timestamp=datetime.now().isoformat(),
            ))

        # Mark addressed concerns
        for cid in followup.get("concerns_addressed", []):
            if cid in self.concerns:
                self.concerns[cid].status = "addressed"
            else:
                # Try to match by agent name
                for concern_id, concern in self.concerns.items():
                    if concern.agent == cid and concern.status == "open":
                        concern.status = "addressed"
                        break

        # Check if complete
        if followup.get("is_complete"):
            self.is_complete = True
            self.summary = followup.get("summary", "")

            if self.summary and not any(m.get("content", "").startswith("**Summary**") for m in response_messages):
                response_messages.append({
                    "agent": "team",
                    "icon": "👥",
                    "content": f"**Summary:** {self.summary}"
                })

        return response_messages

    async def _respond_round_table(self, user_message: str) -> List[Dict]:
        """Round-table mode: focus on one agent at a time."""
        response_messages = []

        # Get current agent
        current = self.current_agent
        if not current:
            # No more agents with concerns
            self.is_complete = True
            return [{
                "agent": "team",
                "icon": "👥",
                "content": "**Review Complete!** All agents' concerns have been addressed. Great discussion!"
            }]

        agent_info = self.AGENTS.get(current, {"name": current.title(), "icon": "💬"})

        # Get this agent's open concerns
        open_concerns = self.get_agent_open_concerns(current)
        if not open_concerns:
            # This agent has no more concerns, advance
            next_agent = self.advance_to_next_agent()
            return await self._handle_agent_transition(next_agent)

        # Format concerns for the prompt
        agent_concerns_text = "\n".join([
            f"- [{c.severity.upper()}] {c.question}"
            for c in open_concerns
        ])

        # Build context about other agents waiting
        other_agents = [a for a in self.agents_with_concerns[self.current_agent_index + 1:]
                       if self.get_agent_open_concerns(a)]
        if other_agents:
            other_context = f"(Note: {', '.join([self.AGENTS.get(a, {}).get('name', a.title()) for a in other_agents])} are waiting to discuss their concerns after you.)"
        else:
            other_context = "(You are the last agent with concerns.)"

        # Generate round-table response
        followup = await self._generate_round_table_followup(
            user_message,
            current,
            agent_concerns_text,
            other_context,
        )

        # Process response messages
        for msg in followup.get("messages", []):
            agent = msg.get("agent", current)
            msg_agent_info = self.AGENTS.get(agent, {"name": agent.title(), "icon": "💬"})

            response_messages.append({
                "agent": agent,
                "icon": msg_agent_info.get("icon", "💬"),
                "content": msg.get("content", "")
            })

            self.messages.append(TeamMessage(
                role=agent,
                content=msg.get("content", ""),
                timestamp=datetime.now().isoformat(),
            ))

        # Mark addressed concerns
        for cid in followup.get("concerns_addressed", []):
            if cid in self.concerns:
                self.concerns[cid].status = "addressed"
            else:
                # Try to match by agent name prefix
                for concern_id, concern in self.concerns.items():
                    if concern_id.startswith(current) and concern.status == "open":
                        concern.status = "addressed"
                        break

        # Check if current agent's concerns are all resolved
        if followup.get("all_my_concerns_resolved", False):
            # Mark all remaining concerns for this agent as addressed
            for cid in self.agent_concerns_map.get(current, []):
                if cid in self.concerns and self.concerns[cid].status == "open":
                    self.concerns[cid].status = "addressed"

            # Advance to next agent
            self.current_agent_index += 1
            next_agent = self.advance_to_next_agent()
            transition_messages = await self._handle_agent_transition(next_agent)
            response_messages.extend(transition_messages)

        return response_messages

    async def _handle_agent_transition(self, next_agent: Optional[str]) -> List[Dict]:
        """Handle transition between agents in round-table mode."""
        if not next_agent:
            # All done!
            self.is_complete = True
            self.summary = "All agents' concerns have been addressed through round-table discussion."
            return [{
                "agent": "team",
                "icon": "👥",
                "content": "**Review Complete!** All agents' concerns have been addressed. Ready to proceed."
            }]

        # Transition to next agent
        next_info = self.AGENTS.get(next_agent, {"name": next_agent.title(), "icon": "💬"})
        open_concerns = self.get_agent_open_concerns(next_agent)

        # Severity icons map
        severity_icons = {"critical": "🔴", "important": "🟡", "minor": "🟢"}

        # Format the next agent's concerns
        concerns_preview = "\n".join([
            f"  {severity_icons.get(c.severity, '🟡')} {c.question}"
            for c in open_concerns[:3]  # Show first 3
        ])

        remaining = len(open_concerns) - 3
        if remaining > 0:
            concerns_preview += f"\n  ...and {remaining} more"

        transition_message = {
            "agent": "system",
            "icon": "📋",
            "content": f"**Moving to {next_info['name']}** {next_info['icon']}\n\n"
                      f"{next_info['name']}'s concerns:\n{concerns_preview}\n\n"
                      f"Please address {next_info['name']}'s concerns."
        }

        # Store the transition message
        self.messages.append(TeamMessage(
            role="system",
            content=transition_message["content"],
            timestamp=datetime.now().isoformat(),
        ))

        return [transition_message]

    async def _generate_round_table_followup(
        self,
        user_message: str,
        current_agent: str,
        agent_concerns: str,
        other_agents_context: str,
    ) -> Dict:
        """Generate response for round-table mode focusing on one agent."""
        conversation_text = "\n".join([
            f"{'USER' if m.role == 'user' else m.role.upper()}: {m.content}"
            for m in self.messages[-10:]
        ])

        prompt = self.ROUND_TABLE_FOLLOWUP_PROMPT.format(
            current_agent=current_agent,
            current_agent_upper=current_agent.upper(),
            spec_summary=self.spec_content[:1500],
            agent_concerns=agent_concerns,
            conversation=conversation_text,
            user_message=user_message,
            other_agents_context=other_agents_context,
        )

        response = await self._call_llm(
            prompt,
            system=f"You are {current_agent}, part of a review team. Stay in character. Respond only with valid JSON."
        )

        return self._parse_round_table_json(response, current_agent)

    def _parse_round_table_json(self, response: str, current_agent: str) -> Dict:
        """Parse JSON from round-table LLM response."""
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            # Default response
            return {
                "messages": [{"agent": current_agent, "content": "I understand. Let me consider that."}],
                "concerns_addressed": [],
                "all_my_concerns_resolved": False,
            }

    async def _analyze_with_team(self, previous_reviews: str) -> Dict:
        """Have the team analyze the spec."""
        prompt = self.TEAM_ANALYSIS_PROMPT.format(
            spec_content=self.spec_content[:4000],
            previous_reviews=previous_reviews or "None",
        )

        response = await self._call_llm(
            prompt,
            system="You are a team of expert reviewers. Respond only with valid JSON."
        )

        return self._parse_json(response)

    async def _generate_followup(self, user_message: str, outstanding: List[str]) -> Dict:
        """Generate team follow-up response."""
        conversation_text = "\n".join([
            f"{'USER' if m.role == 'user' else m.role.upper()}: {m.content}"
            for m in self.messages[-10:]
        ])

        prompt = self.TEAM_FOLLOWUP_PROMPT.format(
            spec_summary=self.spec_content[:1500],
            conversation=conversation_text,
            outstanding_concerns="\n".join(outstanding) if outstanding else "None remaining",
            user_message=user_message,
        )

        response = await self._call_llm(
            prompt,
            system="You are facilitating a team review. Keep responses concise. Respond only with valid JSON."
        )

        return self._parse_json(response)

    def _parse_json(self, response: str) -> Dict:
        """Parse JSON from LLM response."""
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {
                "messages": [{"agent": "team", "content": "Let's continue discussing."}],
                "concerns_addressed": [],
                "is_complete": False,
            }

    async def _call_llm(self, prompt: str, system: str = None, timeout: int = 60) -> str:
        """Call LLM - tries OpenAI first, falls back to Ollama."""
        if self._using_openai and self.openai_api_key:
            try:
                return await self._call_openai(prompt, system, timeout)
            except Exception as e:
                print(f"[TeamConversation] OpenAI failed, falling back to Ollama: {e}")

        return await self._call_ollama(prompt, system, timeout)

    async def _call_openai(self, prompt: str, system: str = None, timeout: int = 60) -> str:
        """Call OpenAI API."""
        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }

        messages = [
            {"role": "system", "content": system or "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": self.openai_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1500,
        }

        try:
            client_timeout = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=client_timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error = await response.text()
                        raise Exception(f"OpenAI error ({response.status}): {error}")
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
        except asyncio.TimeoutError:
            raise Exception("OpenAI timeout")

    async def _call_ollama(self, prompt: str, system: str = None, timeout: int = 60) -> str:
        """Call Ollama API (fallback)."""
        url = f"{self.ollama_url}/api/generate"

        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "system": system or "You are a helpful assistant.",
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 1500,
            }
        }

        try:
            client_timeout = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=client_timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error = await response.text()
                        raise Exception(f"Ollama error: {error}")
                    result = await response.json()
                    return result.get("response", "")
        except Exception as e:
            return json.dumps({
                "messages": [{"agent": "team", "content": f"Connection issue: {str(e)[:50]}"}],
                "is_complete": False,
            })

    def get_state(self) -> Dict[str, Any]:
        """Get current conversation state."""
        open_concerns = [c for c in self.concerns.values() if c.status == "open"]
        addressed_concerns = [c for c in self.concerns.values() if c.status in ["addressed", "resolved"]]

        # Group by agent
        concerns_by_agent = {}
        for cid, concern in self.concerns.items():
            if concern.agent not in concerns_by_agent:
                concerns_by_agent[concern.agent] = {"open": 0, "addressed": 0}
            if concern.status == "open":
                concerns_by_agent[concern.agent]["open"] += 1
            else:
                concerns_by_agent[concern.agent]["addressed"] += 1

        state = {
            "is_complete": self.is_complete,
            "total_concerns": len(self.concerns),
            "open_concerns": len(open_concerns),
            "addressed_concerns": len(addressed_concerns),
            "concerns_by_agent": concerns_by_agent,
            "summary": self.summary,
            "mode": self.mode,
        }

        # Add round-table specific state
        if self.mode == "round_table":
            current = self.current_agent
            if current:
                agent_info = self.AGENTS.get(current, {"name": current.title(), "icon": "💬"})
                state["current_speaker"] = {
                    "agent": current,
                    "name": agent_info.get("name", current.title()),
                    "icon": agent_info.get("icon", "💬"),
                    "open_concerns": len(self.get_agent_open_concerns(current)),
                }
            state["agents_order"] = [
                {
                    "agent": a,
                    "name": self.AGENTS.get(a, {}).get("name", a.title()),
                    "icon": self.AGENTS.get(a, {}).get("icon", "💬"),
                    "is_current": a == current,
                    "is_done": not self.get_agent_open_concerns(a),
                }
                for a in self.agents_with_concerns
            ]

        return state

    def get_messages(self) -> List[Dict]:
        """Get all messages."""
        return [m.to_dict() for m in self.messages]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize conversation state."""
        data = {
            "messages": self.get_messages(),
            "concerns": {
                cid: {
                    "agent": c.agent,
                    "category": c.category,
                    "severity": c.severity,
                    "question": c.question,
                    "context": c.context,
                    "status": c.status,
                    "resolution": c.resolution,
                }
                for cid, c in self.concerns.items()
            },
            "is_complete": self.is_complete,
            "summary": self.summary,
            "project_name": self.project_name,
            "mode": self.mode,
        }

        # Include round-table state
        if self.mode == "round_table":
            data["round_table"] = {
                "current_agent_index": self.current_agent_index,
                "agents_with_concerns": self.agents_with_concerns,
                "agent_concerns_map": self.agent_concerns_map,
            }

        return data

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        openai_api_key: str = None,
        openai_model: str = "gpt-4o-mini",
    ) -> "TeamConversation":
        """Deserialize conversation state."""
        conv = cls(
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            mode=data.get("mode", "free_form"),
        )

        # Restore messages
        for msg_data in data.get("messages", []):
            conv.messages.append(TeamMessage(
                role=msg_data.get("role", "user"),
                content=msg_data.get("content", ""),
                timestamp=msg_data.get("timestamp", ""),
                concern_ids=msg_data.get("concern_ids", []),
            ))

        # Restore concerns
        for cid, c_data in data.get("concerns", {}).items():
            conv.concerns[cid] = AgentConcern(
                agent=c_data["agent"],
                category=c_data["category"],
                severity=c_data["severity"],
                question=c_data["question"],
                context=c_data.get("context", ""),
                status=c_data.get("status", "open"),
                resolution=c_data.get("resolution", ""),
            )

        conv.is_complete = data.get("is_complete", False)
        conv.summary = data.get("summary", "")
        conv.project_name = data.get("project_name", "")

        # Restore round-table state
        if conv.mode == "round_table" and "round_table" in data:
            rt = data["round_table"]
            conv.current_agent_index = rt.get("current_agent_index", 0)
            conv.agents_with_concerns = rt.get("agents_with_concerns", [])
            conv.agent_concerns_map = rt.get("agent_concerns_map", {})

        return conv
