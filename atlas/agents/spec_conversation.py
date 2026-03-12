"""
ATLAS Spec Refinement Conversation

A proactive AI conversation system for refining specs through discussion.
Unlike a passive Q&A, this system:
1. Analyzes the spec for gaps, risks, and unclear areas
2. Raises concerns and asks targeted questions
3. Digs deeper based on responses
4. Tracks what's been resolved vs. still open
5. Updates the spec based on the conversation
"""

import asyncio
import aiohttp
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class SpecConcern:
    """A concern or question about the spec."""
    id: str
    category: str  # "clarity", "feasibility", "scope", "risk", "missing", "conflict"
    severity: str  # "critical", "important", "minor"
    question: str  # The question to ask the user
    context: str  # Why this matters
    spec_section: str  # Which part of spec this relates to
    status: str = "open"  # "open", "discussed", "resolved"
    resolution: str = ""  # How it was resolved


@dataclass
class ConversationMessage:
    """A message in the conversation."""
    role: str  # "assistant" or "user"
    content: str
    timestamp: str = ""
    concern_id: str = ""  # Which concern this relates to

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "concern_id": self.concern_id,
        }


class SpecRefinementConversation:
    """
    AI-powered conversation to refine and improve specs.

    The agent proactively identifies issues and drives the discussion
    rather than passively waiting for user questions.
    """

    AGENT_PERSONAS = {
        "sketch": {
            "name": "Sketch",
            "role": "Strategic Planning",
            "icon": "📐",
            "focus": ["requirements clarity", "scope definition", "user stories", "acceptance criteria"],
            "style": "I focus on making sure requirements are clear and complete.",
        },
        "architect": {
            "name": "Architect",
            "role": "Technical Design",
            "icon": "🏗️",
            "focus": ["technical feasibility", "architecture", "integration points", "scalability"],
            "style": "I evaluate technical decisions and identify architectural concerns.",
        },
        "tinker": {
            "name": "Tinker",
            "role": "Implementation",
            "icon": "🔧",
            "focus": ["implementation details", "edge cases", "error handling", "testing"],
            "style": "I think about how this will actually be built and what could go wrong.",
        },
        "oracle": {
            "name": "Oracle",
            "role": "Quality & Risk",
            "icon": "🔮",
            "focus": ["risks", "dependencies", "quality concerns", "missing pieces"],
            "style": "I identify risks and ensure nothing important is overlooked.",
        },
    }

    ANALYSIS_PROMPT = """Analyze this specification and identify concerns that need discussion.

SPECIFICATION:
{spec_content}

SPEC METADATA:
- Name: {spec_name}
- Status: {spec_status}
- Tasks: {task_count} total

YOUR ROLE: {agent_role}
YOUR FOCUS AREAS: {focus_areas}

Already discussed topics (DO NOT ask about these again):
{discussed_topics}

Identify 3-5 concerns from YOUR perspective. For each concern, determine:
1. Category: clarity, feasibility, scope, risk, missing, or conflict
2. Severity: critical (blocks progress), important (should address), minor (nice to clarify)
3. A specific question to ask the user
4. Why this matters (1 sentence)
5. Which spec section this relates to

CRITICAL RULES:
- Focus on YOUR area of expertise ({focus_areas})
- Ask about things NOT in the "already discussed" list
- Be specific - reference actual parts of the spec
- Prioritize critical and important concerns first
- If the spec is solid in your area, say so with just 1-2 minor suggestions

Respond with a JSON object:
{{
    "overall_assessment": "Brief 1-2 sentence assessment from your perspective",
    "spec_quality": 0-100,
    "concerns": [
        {{
            "id": "concern_1",
            "category": "clarity|feasibility|scope|risk|missing|conflict",
            "severity": "critical|important|minor",
            "question": "The specific question to ask",
            "context": "Why this matters",
            "spec_section": "Which part of spec"
        }}
    ],
    "ready_to_proceed": true/false
}}

RESPOND ONLY WITH THE JSON OBJECT."""

    FOLLOWUP_PROMPT = """Continue the spec refinement conversation.

SPECIFICATION CONTEXT:
{spec_summary}

CONVERSATION SO FAR:
{conversation}

CURRENT CONCERN BEING DISCUSSED:
{current_concern}

USER'S RESPONSE:
{user_message}

YOUR ROLE: {agent_name} ({agent_role})

Based on the user's response, do ONE of these:
1. If their answer is clear and addresses the concern: Acknowledge it, summarize the resolution, and move to the next concern
2. If their answer is vague or raises new questions: Ask a specific follow-up to dig deeper
3. If their answer reveals a new issue: Acknowledge it and address the new issue
4. If they ask YOU a question: Answer it based on your expertise, then return to the concern

IMPORTANT:
- Be conversational and collaborative, not interrogating
- One question at a time
- Acknowledge what they said before asking more
- If they seem frustrated, offer to move on
- Reference specific parts of the spec when relevant

Respond with a JSON object:
{{
    "response": "Your conversational response (2-4 sentences max)",
    "concern_status": "resolved|needs_followup|new_issue",
    "resolution_summary": "If resolved, brief summary of the resolution (or empty)",
    "next_action": "followup|next_concern|complete",
    "spec_update": "If the conversation revealed something that should update the spec, describe it (or empty)"
}}

RESPOND ONLY WITH THE JSON OBJECT."""

    def __init__(
        self,
        agent_type: str = "sketch",
        openai_api_key: str = None,
        openai_model: str = "gpt-4o-mini",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3",
    ):
        self.agent_type = agent_type
        self.agent = self.AGENT_PERSONAS.get(agent_type, self.AGENT_PERSONAS["sketch"])

        # LLM config
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self._using_openai = bool(openai_api_key)

        # Conversation state
        self.messages: List[ConversationMessage] = []
        self.concerns: List[SpecConcern] = []
        self.current_concern_idx: int = 0
        self.is_complete: bool = False
        self.spec_updates: List[str] = []  # Suggested updates from conversation

        # Spec context
        self.spec_name: str = ""
        self.spec_content: str = ""
        self.spec_metadata: Dict = {}

    async def start(self, spec_name: str, spec_content: str, spec_metadata: Dict = None) -> str:
        """Start the conversation by analyzing the spec and raising initial concerns."""
        self.spec_name = spec_name
        self.spec_content = spec_content
        self.spec_metadata = spec_metadata or {}

        # Analyze the spec
        analysis = await self._analyze_spec()

        if not analysis.get("concerns"):
            # Spec looks good!
            response = f"""I'm {self.agent['name']}, and I've reviewed the spec from a {self.agent['role'].lower()} perspective.

{analysis.get('overall_assessment', 'The spec looks solid!')}

**Quality Score: {analysis.get('spec_quality', 85)}/100**

I don't see any major concerns in my area. The spec appears ready to proceed. Let me know if you'd like me to look at anything specific!"""
            self.is_complete = True
        else:
            # Store concerns and start discussion
            self.concerns = [
                SpecConcern(
                    id=c["id"],
                    category=c["category"],
                    severity=c["severity"],
                    question=c["question"],
                    context=c["context"],
                    spec_section=c.get("spec_section", "general"),
                )
                for c in analysis["concerns"]
            ]

            # Build opening message
            critical_count = len([c for c in self.concerns if c.severity == "critical"])
            important_count = len([c for c in self.concerns if c.severity == "important"])

            severity_summary = []
            if critical_count:
                severity_summary.append(f"{critical_count} critical")
            if important_count:
                severity_summary.append(f"{important_count} important")

            first_concern = self.concerns[0]

            response = f"""I'm {self.agent['name']}, and I've reviewed the spec from a {self.agent['role'].lower()} perspective.

{analysis.get('overall_assessment', '')}

I have **{len(self.concerns)} items** to discuss ({', '.join(severity_summary) if severity_summary else 'minor items'}).

Let's start with the most important one:

**{first_concern.category.title()}** ({first_concern.severity}): {first_concern.question}

_{first_concern.context}_"""

        self.messages.append(ConversationMessage(
            role="assistant",
            content=response,
            timestamp=datetime.now().isoformat(),
            concern_id=self.concerns[0].id if self.concerns else "",
        ))

        return response

    async def respond(self, user_message: str) -> str:
        """Process user's response and continue the conversation."""
        # Add user message
        current_concern = self.concerns[self.current_concern_idx] if self.current_concern_idx < len(self.concerns) else None

        self.messages.append(ConversationMessage(
            role="user",
            content=user_message.strip(),
            timestamp=datetime.now().isoformat(),
            concern_id=current_concern.id if current_concern else "",
        ))

        # Check if user wants to skip or move on
        skip_phrases = ["skip", "move on", "next", "don't know", "not sure", "later"]
        if any(phrase in user_message.lower() for phrase in skip_phrases):
            return await self._move_to_next_concern(skipped=True)

        # Generate follow-up response
        followup = await self._generate_followup(user_message, current_concern)

        response = followup.get("response", "Thanks for that clarification.")

        # Handle concern status
        if followup.get("concern_status") == "resolved" and current_concern:
            current_concern.status = "resolved"
            current_concern.resolution = followup.get("resolution_summary", "")

            # Store any spec updates
            if followup.get("spec_update"):
                self.spec_updates.append(followup["spec_update"])

        # Determine next action
        if followup.get("next_action") == "next_concern":
            next_response = await self._move_to_next_concern()
            response = response + "\n\n" + next_response
        elif followup.get("next_action") == "complete":
            self.is_complete = True
            response = response + "\n\n" + self._generate_summary()

        self.messages.append(ConversationMessage(
            role="assistant",
            content=response,
            timestamp=datetime.now().isoformat(),
            concern_id=current_concern.id if current_concern else "",
        ))

        return response

    async def _move_to_next_concern(self, skipped: bool = False) -> str:
        """Move to the next concern in the list."""
        if skipped and self.current_concern_idx < len(self.concerns):
            self.concerns[self.current_concern_idx].status = "discussed"

        self.current_concern_idx += 1

        if self.current_concern_idx >= len(self.concerns):
            self.is_complete = True
            return self._generate_summary()

        next_concern = self.concerns[self.current_concern_idx]
        remaining = len(self.concerns) - self.current_concern_idx

        return f"""---

**Next item** ({remaining} remaining):

**{next_concern.category.title()}** ({next_concern.severity}): {next_concern.question}

_{next_concern.context}_"""

    async def _analyze_spec(self) -> Dict:
        """Analyze the spec and identify concerns."""
        # Get discussed topics from previous messages
        discussed = self._get_discussed_topics()

        prompt = self.ANALYSIS_PROMPT.format(
            spec_content=self.spec_content[:4000],  # Limit size
            spec_name=self.spec_name,
            spec_status=self.spec_metadata.get("status", "unknown"),
            task_count=self.spec_metadata.get("task_count", 0),
            agent_role=self.agent["role"],
            focus_areas=", ".join(self.agent["focus"]),
            discussed_topics="\n".join(f"- {t}" for t in discussed) if discussed else "None yet",
        )

        response = await self._call_llm(
            prompt,
            system=f"You are {self.agent['name']}, a {self.agent['role']} expert. {self.agent['style']} Respond only with valid JSON."
        )

        return self._parse_json(response)

    async def _generate_followup(self, user_message: str, current_concern: Optional[SpecConcern]) -> Dict:
        """Generate a follow-up response based on user's answer."""
        conversation_text = "\n".join([
            f"{m.role.upper()}: {m.content}"
            for m in self.messages[-6:]  # Last 6 messages for context
        ])

        concern_text = ""
        if current_concern:
            concern_text = f"""Category: {current_concern.category}
Severity: {current_concern.severity}
Question: {current_concern.question}
Context: {current_concern.context}
Section: {current_concern.spec_section}"""

        prompt = self.FOLLOWUP_PROMPT.format(
            spec_summary=self.spec_content[:1500],
            conversation=conversation_text,
            current_concern=concern_text or "General discussion",
            user_message=user_message,
            agent_name=self.agent["name"],
            agent_role=self.agent["role"],
        )

        response = await self._call_llm(
            prompt,
            system=f"You are {self.agent['name']}, a collaborative {self.agent['role']} expert. Be helpful and conversational. Respond only with valid JSON."
        )

        return self._parse_json(response)

    def _generate_summary(self) -> str:
        """Generate a summary when the conversation is complete."""
        resolved = [c for c in self.concerns if c.status == "resolved"]
        discussed = [c for c in self.concerns if c.status == "discussed"]

        summary_parts = [f"**{self.agent['icon']} {self.agent['name']} Review Complete**\n"]

        if resolved:
            summary_parts.append(f"**Resolved ({len(resolved)}):**")
            for c in resolved:
                summary_parts.append(f"- {c.question[:60]}... {'✓ ' + c.resolution[:40] if c.resolution else '✓'}")

        if discussed:
            summary_parts.append(f"\n**Noted ({len(discussed)}):**")
            for c in discussed:
                summary_parts.append(f"- {c.question[:60]}...")

        if self.spec_updates:
            summary_parts.append(f"\n**Suggested Spec Updates:**")
            for update in self.spec_updates:
                summary_parts.append(f"- {update}")

        if not self.concerns:
            summary_parts.append("No concerns identified - the spec looks good from my perspective!")

        summary_parts.append("\n---\nReady to continue with other agents or proceed to implementation.")

        return "\n".join(summary_parts)

    def _get_discussed_topics(self) -> List[str]:
        """Extract topics that have been discussed."""
        topics = []
        for concern in self.concerns:
            if concern.status in ["discussed", "resolved"]:
                topics.append(concern.question[:50])
        return topics

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
            # Try to extract JSON object
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            # Return minimal fallback
            return {
                "response": response[:500] if response else "I understand. Let's continue.",
                "concern_status": "needs_followup",
                "next_action": "followup",
            }

    async def _call_llm(self, prompt: str, system: str = None, timeout: int = 60) -> str:
        """Call LLM - tries OpenAI first, falls back to Ollama."""
        if self._using_openai and self.openai_api_key:
            try:
                return await self._call_openai(prompt, system, timeout)
            except Exception as e:
                print(f"[SpecConversation] OpenAI failed, falling back to Ollama: {e}")

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
            "max_tokens": 1024,
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
                "num_predict": 1024,
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
                "response": f"I'm having trouble connecting. Let's continue - {str(e)[:50]}",
                "concern_status": "needs_followup",
                "next_action": "followup",
            })

    def get_state(self) -> Dict[str, Any]:
        """Get current conversation state for UI."""
        current_concern = None
        if self.current_concern_idx < len(self.concerns):
            c = self.concerns[self.current_concern_idx]
            current_concern = {
                "id": c.id,
                "category": c.category,
                "severity": c.severity,
                "question": c.question,
            }

        return {
            "agent": self.agent,
            "is_complete": self.is_complete,
            "concerns_total": len(self.concerns),
            "concerns_resolved": len([c for c in self.concerns if c.status == "resolved"]),
            "concerns_remaining": len(self.concerns) - self.current_concern_idx,
            "current_concern": current_concern,
            "spec_updates": self.spec_updates,
        }

    def get_messages(self) -> List[Dict]:
        """Get all messages."""
        return [m.to_dict() for m in self.messages]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize conversation state."""
        return {
            "agent_type": self.agent_type,
            "messages": self.get_messages(),
            "concerns": [
                {
                    "id": c.id,
                    "category": c.category,
                    "severity": c.severity,
                    "question": c.question,
                    "context": c.context,
                    "spec_section": c.spec_section,
                    "status": c.status,
                    "resolution": c.resolution,
                }
                for c in self.concerns
            ],
            "current_concern_idx": self.current_concern_idx,
            "is_complete": self.is_complete,
            "spec_updates": self.spec_updates,
            "spec_name": self.spec_name,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        openai_api_key: str = None,
        openai_model: str = "gpt-4o-mini",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3",
    ) -> "SpecRefinementConversation":
        """Deserialize conversation state."""
        conv = cls(
            agent_type=data.get("agent_type", "sketch"),
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            ollama_url=ollama_url,
            ollama_model=ollama_model,
        )

        # Restore messages
        for msg_data in data.get("messages", []):
            conv.messages.append(ConversationMessage(
                role=msg_data.get("role", "user"),
                content=msg_data.get("content", ""),
                timestamp=msg_data.get("timestamp", ""),
                concern_id=msg_data.get("concern_id", ""),
            ))

        # Restore concerns
        for c_data in data.get("concerns", []):
            conv.concerns.append(SpecConcern(
                id=c_data["id"],
                category=c_data["category"],
                severity=c_data["severity"],
                question=c_data["question"],
                context=c_data["context"],
                spec_section=c_data.get("spec_section", ""),
                status=c_data.get("status", "open"),
                resolution=c_data.get("resolution", ""),
            ))

        conv.current_concern_idx = data.get("current_concern_idx", 0)
        conv.is_complete = data.get("is_complete", False)
        conv.spec_updates = data.get("spec_updates", [])
        conv.spec_name = data.get("spec_name", "")

        return conv
