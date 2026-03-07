"""
ATLAS Smart Idea Conversation

An AI-powered conversation system that uses Ollama to intelligently
flesh out vague ideas before sending them to the Architect.

Unlike the scripted conversation, this system:
1. Analyzes the idea for completeness
2. Identifies specific gaps and ambiguities
3. Asks targeted follow-up questions
4. Continues until the idea is ready for planning
"""

import asyncio
import aiohttp
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from atlas.projects.idea_types import IdeaTypeDetector, IdeaType, IDEA_CONFIGS
from atlas.projects.project_types import ProjectTypeDetector, ProjectType, ProjectCategory


@dataclass
class IdeaBrief:
    """A fully fleshed out idea ready for the Architect."""
    title: str = ""
    description: str = ""
    problem_statement: str = ""
    target_users: str = ""
    core_features: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    technical_requirements: str = ""
    constraints: str = ""
    scope: str = ""  # MVP, full product, prototype
    readiness_score: int = 0  # 0-100, needs 80+ to proceed
    idea_type: str = "unknown"  # product, process, research, concept, decision, document
    idea_type_confidence: float = 0.0
    # Project type (for PRODUCT ideas)
    project_type: str = ""  # e.g., "web_spa", "mobile_ios", "cli_tool"
    project_category: str = ""  # e.g., "web", "app", "cli"
    project_type_confidence: float = 0.0
    suggested_stack: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "problem_statement": self.problem_statement,
            "target_users": self.target_users,
            "core_features": self.core_features,
            "success_criteria": self.success_criteria,
            "technical_requirements": self.technical_requirements,
            "constraints": self.constraints,
            "scope": self.scope,
            "readiness_score": self.readiness_score,
            "idea_type": self.idea_type,
            "idea_type_confidence": self.idea_type_confidence,
            "project_type": self.project_type,
            "project_category": self.project_category,
            "project_type_confidence": self.project_type_confidence,
            "suggested_stack": self.suggested_stack,
        }

    def is_ready(self) -> bool:
        """Check if the idea is ready for the Architect."""
        return self.readiness_score >= 80

    def get_missing_elements(self) -> List[str]:
        """Get list of missing or weak elements."""
        missing = []
        if not self.description or len(self.description) < 50:
            missing.append("detailed description")
        if not self.problem_statement:
            missing.append("problem statement")
        if not self.target_users:
            missing.append("target users")
        if len(self.core_features) < 2:
            missing.append("core features (at least 2)")
        if not self.scope:
            missing.append("project scope")
        return missing


@dataclass
class ConversationMessage:
    """A message in the conversation."""
    role: str  # "assistant" or "user"
    content: str
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


class SmartIdeaConversation:
    """
    AI-powered conversation to flesh out project ideas.

    Uses Ollama to:
    1. Detect idea type (product, process, research, concept, decision, document)
    2. Analyze idea completeness
    3. Generate targeted questions based on idea type
    4. Extract structured information
    5. Determine when idea is ready
    """

    # System prompts for different idea types
    SYSTEM_PROMPTS = {
        "product": """You are an expert product consultant helping someone clarify their project idea.
Your job is to transform a vague idea into a clear, actionable product brief.""",

        "process": """You are an expert process consultant helping someone design a workflow or procedure.
Your job is to understand what they're trying to accomplish and help them design clear, effective steps.""",

        "research": """You are an expert research consultant helping someone investigate a topic.
Your job is to understand what they want to learn and help them scope their research effectively.""",

        "concept": """You are a thoughtful thinking partner helping someone explore and develop an idea.
Your job is to help them think through possibilities, implications, and flesh out abstract concepts.""",

        "decision": """You are a decision-making consultant helping someone evaluate options.
Your job is to understand the decision, the options, the criteria, and help them think it through clearly.""",

        "document": """You are a writing consultant helping someone plan a document.
Your job is to understand what they need to write, for whom, and help them structure it effectively.""",

        "unknown": """You are a helpful consultant. Start by understanding what the person is trying to accomplish.""",
    }

    SYSTEM_PROMPT = """You are an expert product consultant helping someone clarify their project idea.

Your job is to have a collaborative conversation that transforms a vague idea into a clear, actionable project brief.

IMPORTANT GUIDELINES:
- Ask ONE focused question at a time
- Be conversational and encouraging, not interrogating
- Dig deeper when answers are vague ("tell me more about...", "what specifically...")
- Help them think through implications they might not have considered
- Focus on WHAT and WHY before HOW (technical details come last)

WHEN THEY ASK FOR YOUR INPUT (e.g., "what do you think?", "any suggestions?", "help me brainstorm"):
- ALWAYS offer 3-5 concrete suggestions based on what you know about their idea
- Explain briefly why each suggestion might work for their use case
- Then ask which ones resonate or if they have other ideas
- Be a collaborative partner, not just an interviewer

WHEN THEY SAY "I don't know" or seem stuck:
- Offer options: "Based on what you've described, you could..."
- Give examples from similar projects
- Help them discover what they want through suggestions

NEVER:
- Ask multiple questions at once
- Ignore their questions - if they ask you something, answer it!
- Move on without acknowledging what they said
- Be passive when they want your expertise

Your response should be natural and conversational, like a helpful colleague who brings ideas to the table."""

    # Type-specific analysis prompts
    ANALYSIS_PROMPTS = {
        "product": """Analyze this product idea conversation and extract structured information.

Conversation so far:
{conversation}

Current understanding:
{current_brief}

Questions already asked in this conversation:
{questions_asked}

Respond with a JSON object containing:
{{
    "title": "short project title",
    "description": "what they want to build",
    "problem_statement": "the problem this solves",
    "target_users": "who will use this",
    "core_features": ["feature 1", "feature 2", ...],
    "success_criteria": ["how they'll know it works"],
    "technical_requirements": "any technical preferences",
    "constraints": "limitations mentioned",
    "scope": "MVP/prototype/full product",
    "readiness_score": 0-100,
    "missing_elements": ["what's still unclear"],
    "next_question": "a NEW question not yet asked (or empty string if ready)"
}}

IMPORTANT: The next_question MUST be different from all questions already asked.
If readiness >= 80, set next_question to empty string.

RESPOND ONLY WITH THE JSON OBJECT.""",

        "process": """Analyze this process/workflow conversation and extract structured information.

Conversation so far:
{conversation}

Current understanding:
{current_brief}

Questions already asked in this conversation:
{questions_asked}

Respond with a JSON object containing:
{{
    "title": "short process title",
    "description": "what this process accomplishes",
    "problem_statement": "what pain point this addresses",
    "target_users": "who performs this process",
    "core_features": ["step 1", "step 2", ...],
    "success_criteria": ["how they'll know it's working"],
    "technical_requirements": "tools or systems involved",
    "constraints": "rules, policies, limitations",
    "scope": "simple/moderate/comprehensive",
    "readiness_score": 0-100,
    "missing_elements": ["what's still unclear"],
    "next_question": "a NEW question not yet asked (or empty string if ready)"
}}

IMPORTANT: The next_question MUST be different from all questions already asked.
If readiness >= 80, set next_question to empty string.

RESPOND ONLY WITH THE JSON OBJECT.""",

        "research": """Analyze this research topic conversation and extract structured information.

Conversation so far:
{conversation}

Current understanding:
{current_brief}

Questions already asked in this conversation:
{questions_asked}

Respond with a JSON object containing:
{{
    "title": "research topic title",
    "description": "what they want to learn",
    "problem_statement": "why this research matters",
    "target_users": "who will use this research",
    "core_features": ["question 1", "question 2", ...],
    "success_criteria": ["what they need to know"],
    "technical_requirements": "depth and format needed",
    "constraints": "time, scope limitations",
    "scope": "quick overview/deep dive/comprehensive",
    "readiness_score": 0-100,
    "missing_elements": ["what's still unclear"],
    "next_question": "a NEW question not yet asked (or empty string if ready)"
}}

IMPORTANT: The next_question MUST be different from all questions already asked.
If readiness >= 80, set next_question to empty string.

RESPOND ONLY WITH THE JSON OBJECT.""",

        "concept": """Analyze this concept exploration conversation and extract structured information.

Conversation so far:
{conversation}

Current understanding:
{current_brief}

Questions already asked in this conversation:
{questions_asked}

Respond with a JSON object containing:
{{
    "title": "concept name",
    "description": "what the concept/idea is about",
    "problem_statement": "what inspired or motivated this",
    "target_users": "who this affects or benefits",
    "core_features": ["aspect 1", "aspect 2", ...],
    "success_criteria": ["what makes this concept successful"],
    "technical_requirements": "implementation considerations",
    "constraints": "boundaries or limitations",
    "scope": "exploration/definition/actionable",
    "readiness_score": 0-100,
    "missing_elements": ["what's still unclear"],
    "next_question": "a NEW question not yet asked (or empty string if ready)"
}}

IMPORTANT: The next_question MUST be different from all questions already asked.
If readiness >= 80, set next_question to empty string.

RESPOND ONLY WITH THE JSON OBJECT.""",

        "decision": """Analyze this decision-making conversation and extract structured information.

Conversation so far:
{conversation}

Current understanding:
{current_brief}

Questions already asked in this conversation:
{questions_asked}

Respond with a JSON object containing:
{{
    "title": "decision to make",
    "description": "context and background",
    "problem_statement": "why this decision matters",
    "target_users": "who is affected",
    "core_features": ["option 1", "option 2", ...],
    "success_criteria": ["what makes a good choice"],
    "technical_requirements": "criteria and factors",
    "constraints": "dealbreakers or requirements",
    "scope": "reversible/significant/major",
    "readiness_score": 0-100,
    "missing_elements": ["what's still unclear"],
    "next_question": "a NEW question not yet asked (or empty string if ready)"
}}

IMPORTANT: The next_question MUST be different from all questions already asked.
If readiness >= 80, set next_question to empty string.

RESPOND ONLY WITH THE JSON OBJECT.""",

        "document": """Analyze this document planning conversation and extract structured information.

Conversation so far:
{conversation}

Current understanding:
{current_brief}

Questions already asked in this conversation:
{questions_asked}

Respond with a JSON object containing:
{{
    "title": "document title",
    "description": "what the document covers",
    "problem_statement": "purpose of this document",
    "target_users": "who will read this",
    "core_features": ["section 1", "section 2", ...],
    "success_criteria": ["what makes it effective"],
    "technical_requirements": "format, length, style",
    "constraints": "requirements or guidelines",
    "scope": "brief/standard/comprehensive",
    "readiness_score": 0-100,
    "missing_elements": ["what's still unclear"],
    "next_question": "a NEW question not yet asked (or empty string if ready)"
}}

IMPORTANT: The next_question MUST be different from all questions already asked.
If readiness >= 80, set next_question to empty string.

RESPOND ONLY WITH THE JSON OBJECT.""",
    }

    # Default/unknown analysis prompt
    ANALYSIS_PROMPT = """Analyze this conversation and extract structured information.

Conversation so far:
{conversation}

Current understanding:
{current_brief}

Questions already asked in this conversation:
{questions_asked}

Respond with a JSON object containing:
{{
    "title": "short title",
    "description": "what they want to accomplish",
    "problem_statement": "the underlying need",
    "target_users": "who benefits",
    "core_features": ["element 1", "element 2", ...],
    "success_criteria": ["how they'll know it's done"],
    "technical_requirements": "any specific needs",
    "constraints": "limitations mentioned",
    "scope": "small/medium/large",
    "readiness_score": 0-100,
    "missing_elements": ["what's still unclear"],
    "next_question": "a NEW question not yet asked (or empty string if ready)"
}}

Readiness scoring guidelines:
- 0-30: Very vague, don't know what they want
- 30-50: Basic idea is clear but missing key details
- 50-70: Good understanding, minor gaps
- 70-85: Almost ready, just filling in nice-to-haves
- 85-100: Ready for planning

IMPORTANT RULES:
1. If the user has clearly stated WHAT they want to build and WHO it's for, that's already 60-70% ready
2. Simple, straightforward ideas should reach 80+ quickly - don't over-complicate
3. The next_question MUST be different from all questions already asked
4. If we have enough info (readiness >= 80), set next_question to empty string

RESPOND ONLY WITH THE JSON OBJECT, no other text."""

    def __init__(
        self,
        openai_api_key: str = None,
        openai_model: str = "gpt-4o-mini",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3",
    ):
        # OpenAI config (preferred)
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        # Ollama config (fallback)
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        # Conversation state
        self.messages: List[ConversationMessage] = []
        self.brief = IdeaBrief()
        self.is_complete = False
        self._analysis_cache: Optional[Dict] = None
        self._idea_type_detector = IdeaTypeDetector()
        self._project_type_detector = ProjectTypeDetector()
        self._detected_type: Optional[IdeaType] = None
        self._type_confirmed: bool = False
        self._project_type_confirmed: bool = False
        # Track which provider we're using
        self._using_openai = bool(openai_api_key)

    async def start(self, initial_idea: str = "") -> str:
        """Start the conversation, optionally with an initial idea."""
        if initial_idea and initial_idea.strip():
            # User provided an initial idea
            self.messages.append(ConversationMessage(
                role="user",
                content=initial_idea.strip(),
                timestamp=datetime.now().isoformat(),
            ))

            # Detect idea type from initial input
            detected_type, confidence = self._idea_type_detector.detect(initial_idea)
            self._detected_type = detected_type
            self.brief.idea_type = detected_type.value
            self.brief.idea_type_confidence = confidence

            type_intro = ""
            project_intro = ""

            # If confident about type, acknowledge it
            if confidence >= 0.7 and detected_type != IdeaType.UNKNOWN:
                self._type_confirmed = True
                config = IDEA_CONFIGS.get(detected_type)
                type_intro = f"This sounds like a **{config.name.lower()}** - {config.description.lower()}. "

            # For PRODUCT ideas, also detect project type (app, website, etc.)
            if detected_type == IdeaType.PRODUCT:
                proj_type, proj_cat, proj_conf = self._project_type_detector.detect(initial_idea)
                if proj_conf >= 0.5:
                    self.brief.project_type = proj_type.value
                    self.brief.project_category = proj_cat.value
                    self.brief.project_type_confidence = proj_conf
                    proj_config = self._project_type_detector.get_config(proj_type)
                    if proj_config:
                        self.brief.suggested_stack = proj_config.suggested_stack
                        if proj_conf >= 0.7:
                            self._project_type_confirmed = True
                            project_intro = f"Specifically, this looks like a **{proj_config.name}**. "

            # Analyze and respond
            response = await self._generate_response(type_context=type_intro + project_intro)
            self.messages.append(ConversationMessage(
                role="assistant",
                content=response,
                timestamp=datetime.now().isoformat(),
            ))
            return response
        else:
            # Start fresh with open-ended question
            opener = "Hi! I'm here to help you flesh out your idea. What's on your mind? It could be something you want to build, a process to design, a decision to make, or just a concept to explore."
            self.messages.append(ConversationMessage(
                role="assistant",
                content=opener,
                timestamp=datetime.now().isoformat(),
            ))
            return opener

    async def respond(self, user_message: str) -> str:
        """Process user's response and continue the conversation."""
        # Add user message
        self.messages.append(ConversationMessage(
            role="user",
            content=user_message.strip(),
            timestamp=datetime.now().isoformat(),
        ))

        # Count exchanges (user messages)
        user_messages = len([m for m in self.messages if m.role == "user"])

        # Re-detect idea type if not confirmed (may become clearer)
        all_text = " ".join(m.content for m in self.messages if m.role == "user")
        if not self._type_confirmed:
            detected_type, confidence = self._idea_type_detector.detect(all_text)
            if confidence > self.brief.idea_type_confidence:
                self._detected_type = detected_type
                self.brief.idea_type = detected_type.value
                self.brief.idea_type_confidence = confidence
                if confidence >= 0.7:
                    self._type_confirmed = True

        # Re-detect project type if not confirmed (for PRODUCT ideas)
        if self._detected_type == IdeaType.PRODUCT and not self._project_type_confirmed:
            proj_type, proj_cat, proj_conf = self._project_type_detector.detect(all_text)
            if proj_conf > self.brief.project_type_confidence:
                self.brief.project_type = proj_type.value
                self.brief.project_category = proj_cat.value
                self.brief.project_type_confidence = proj_conf
                proj_config = self._project_type_detector.get_config(proj_type)
                if proj_config:
                    self.brief.suggested_stack = proj_config.suggested_stack
                if proj_conf >= 0.7:
                    self._project_type_confirmed = True

        try:
            # Analyze current state
            analysis = await self._analyze_conversation()
            self._analysis_cache = analysis

            # Update brief from analysis
            self._update_brief(analysis)

            # FORCE MINIMUM PROGRESS: Each exchange adds at least 15% readiness
            # This prevents the LLM from keeping us stuck at 50%
            min_readiness = min(user_messages * 15, 100)  # 15% per exchange, max 100
            if self.brief.readiness_score < min_readiness:
                print(f"[SmartConversation] Forcing minimum readiness: {self.brief.readiness_score}% -> {min_readiness}%")
                self.brief.readiness_score = min_readiness

            # Log progress
            print(f"[SmartConversation] Exchange #{user_messages}, Readiness: {self.brief.readiness_score}%, "
                  f"Missing: {analysis.get('missing_elements', [])}")

            # HARD CAP: After 5 exchanges, we're done (75% minimum from formula above)
            if user_messages >= 5:
                print(f"[SmartConversation] COMPLETE after {user_messages} exchanges!")
                self.is_complete = True
                self.brief.readiness_score = max(self.brief.readiness_score, 85)
                summary = self._generate_summary()
                self.messages.append(ConversationMessage(
                    role="assistant",
                    content=summary,
                    timestamp=datetime.now().isoformat(),
                ))
                return summary

            # Check if ready (threshold is 80)
            # Generate next question - pass exchange count to avoid repetition
            response = await self._generate_response(
                analysis.get("next_question"),
                exchange_number=user_messages
            )

        except Exception as e:
            # Fallback response if AI fails
            response = "Thanks for that! Can you tell me more about what specific problem this solves for users?"

        self.messages.append(ConversationMessage(
            role="assistant",
            content=response,
            timestamp=datetime.now().isoformat(),
        ))

        return response

    async def _call_llm(self, prompt: str, system: str = None, timeout: int = 60) -> str:
        """Call LLM - tries OpenAI first, falls back to Ollama."""
        if self._using_openai and self.openai_api_key:
            try:
                print(f"[SmartConversation] Using OpenAI ({self.openai_model})")
                result = await self._call_openai(prompt, system, timeout)
                print(f"[SmartConversation] OpenAI response received ({len(result)} chars)")
                return result
            except Exception as e:
                print(f"[SmartConversation] OpenAI failed, falling back to Ollama: {e}")
                # Fall through to Ollama
        else:
            print(f"[SmartConversation] Using Ollama (OpenAI key not set)")
        return await self._call_ollama(prompt, system, timeout)

    async def _call_openai(self, prompt: str, system: str = None, timeout: int = 60) -> str:
        """Call OpenAI API."""
        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }

        messages = [
            {"role": "system", "content": system or self.SYSTEM_PROMPT},
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
        except aiohttp.ClientError as e:
            raise Exception(f"OpenAI connection error: {e}")

    async def _call_ollama(self, prompt: str, system: str = None, timeout: int = 60) -> str:
        """Call Ollama API (fallback)."""
        url = f"{self.ollama_url}/api/generate"

        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "system": system or self.SYSTEM_PROMPT,
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
        except asyncio.TimeoutError:
            return "I'm taking a bit longer to think. Could you try again or rephrase your response?"
        except aiohttp.ClientError as e:
            return f"I'm having trouble connecting. Please try again. (Error: {str(e)[:50]})"
        except Exception as e:
            return f"Something went wrong. Let's continue - could you tell me more about your idea?"

    async def _analyze_conversation(self) -> Dict:
        """Analyze conversation and extract structured info."""
        conversation_text = "\n".join([
            f"{m.role.upper()}: {m.content}"
            for m in self.messages
        ])

        # Get questions already asked
        questions_asked = self._extract_questions_asked()
        questions_text = "\n".join(f"- {q}" for q in questions_asked) if questions_asked else "None yet"

        # Get type-specific analysis prompt
        idea_type = self.brief.idea_type if self.brief.idea_type else "unknown"
        analysis_prompt = self.ANALYSIS_PROMPTS.get(idea_type, self.ANALYSIS_PROMPT)

        # Format prompt - handle both old prompts (without questions_asked) and new ones
        try:
            prompt = analysis_prompt.format(
                conversation=conversation_text,
                current_brief=json.dumps(self.brief.to_dict(), indent=2),
                questions_asked=questions_text
            )
        except KeyError:
            # Old prompt format without questions_asked
            prompt = analysis_prompt.format(
                conversation=conversation_text,
                current_brief=json.dumps(self.brief.to_dict(), indent=2)
            )

        response = await self._call_llm(
            prompt,
            system="You are a JSON extraction assistant. Respond only with valid JSON."
        )

        # Parse JSON from response
        try:
            # Try to find JSON in response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback - try to extract JSON object
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except (json.JSONDecodeError, ValueError):
                    pass
            # Return minimal analysis
            return {
                "readiness_score": 30,
                "next_question": "Could you tell me more about what you're trying to build?",
                "missing_elements": ["more details needed"]
            }

    def _extract_questions_asked(self) -> List[str]:
        """Extract questions that have been asked in previous assistant messages."""
        questions = []
        for msg in self.messages:
            if msg.role == "assistant":
                # Find sentences ending with ?
                import re
                found = re.findall(r'[^.!?]*\?', msg.content)
                questions.extend([q.strip() for q in found if len(q.strip()) > 10])
        return questions

    def _get_topics_covered(self) -> List[str]:
        """Determine which conversation topics have been covered."""
        covered = []
        brief = self.brief

        if brief.description and len(brief.description) > 20:
            covered.append("what they want to build (core idea)")
        if brief.problem_statement and len(brief.problem_statement) > 10:
            covered.append("the problem it solves")
        if brief.target_users and len(brief.target_users) > 5:
            covered.append("who will use it (target users)")
        if brief.core_features and len(brief.core_features) >= 2:
            covered.append("main features")
        if brief.scope:
            covered.append("project scope (MVP vs full)")
        if brief.technical_requirements:
            covered.append("technical preferences")
        if brief.constraints:
            covered.append("constraints and limitations")

        return covered

    async def _generate_response(self, suggested_question: str = None, type_context: str = "", exchange_number: int = 1) -> str:
        """Generate the next conversational response."""
        conversation_text = "\n".join([
            f"{m.role.upper()}: {m.content}"
            for m in self.messages[-10:]  # Last 10 messages for context
        ])

        # Get appropriate system prompt based on detected type
        idea_type_key = self.brief.idea_type if self.brief.idea_type else "unknown"
        system_prompt = self.SYSTEM_PROMPTS.get(idea_type_key, self.SYSTEM_PROMPTS["unknown"])

        # Check if user is asking for suggestions/input
        last_user_msg = ""
        for msg in reversed(self.messages):
            if msg.role == "user":
                last_user_msg = msg.content.lower()
                break

        asking_for_input = any(phrase in last_user_msg for phrase in [
            "what do you think", "what would you", "any suggestions", "any ideas",
            "help me", "suggest", "recommend", "your opinion", "you think",
            "i don't know", "not sure", "idk", "no idea", "unsure",
            "what should", "what could", "what are some", "give me",
            "can you suggest", "brainstorm", "examples", "options"
        ])

        # Build context about what we know so far
        known_context = "\n## What we've learned so far:"
        if self.brief.title:
            known_context += f"\n- Project: {self.brief.title}"
        if self.brief.description:
            known_context += f"\n- Description: {self.brief.description[:150]}"
        if self.brief.target_users:
            known_context += f"\n- Target users: {self.brief.target_users}"
        if self.brief.core_features:
            known_context += f"\n- Features: {', '.join(self.brief.core_features[:3])}"
        if self.brief.problem_statement:
            known_context += f"\n- Problem: {self.brief.problem_statement[:100]}"

        # Track topics already covered
        topics_covered = self._get_topics_covered()
        if topics_covered:
            known_context += f"\n\n## Topics already covered (DO NOT ask about these again):\n- " + "\n- ".join(topics_covered)

        # Track questions already asked
        questions_asked = self._extract_questions_asked()
        if questions_asked:
            # Show last few questions to avoid repetition
            recent_questions = questions_asked[-5:]
            known_context += f"\n\n## Questions already asked (DO NOT repeat or rephrase these):\n- " + "\n- ".join(recent_questions)

        # Define topic progression - each exchange focuses on a NEW topic
        topics_by_exchange = {
            1: "the core idea and what problem it solves",
            2: "who will use this and why they need it",
            3: "the main features or components",
            4: "scope and priorities (MVP vs full version)",
            5: "any technical preferences or constraints",
        }

        # Skip topics that are already covered
        current_topic = None
        for ex_num in range(exchange_number, 6):
            topic = topics_by_exchange.get(ex_num, "")
            # Check if this topic overlaps with covered topics
            topic_covered = False
            for covered in topics_covered:
                if any(word in covered.lower() for word in topic.lower().split()[:3]):
                    topic_covered = True
                    break
            if not topic_covered:
                current_topic = topic
                break

        if not current_topic:
            current_topic = "confirming understanding and wrapping up"

        if asking_for_input:
            # User wants suggestions - be collaborative!
            prompt = f"""The user is asking for YOUR input/suggestions. This is your chance to be helpful!

Previous messages:
{conversation_text}
{known_context}

IMPORTANT: The user asked for your suggestions. You MUST:
1. Offer 3-5 specific, concrete suggestions based on what you know about their project
2. Briefly explain why each suggestion could work for their use case
3. Ask which ones resonate with them (or if they have other ideas)

Be a collaborative partner! Share your expertise. Don't just ask another question."""
        else:
            # Normal conversation - focus on the current topic for this exchange
            prompt = f"""Continue this conversation naturally. This is exchange #{exchange_number}.

Previous messages:
{conversation_text}
{known_context}

YOUR TASK FOR THIS EXCHANGE: Focus on {current_topic}

CRITICAL RULES:
1. NEVER ask about topics listed in "Topics already covered" - we have that info
2. NEVER repeat or rephrase questions listed in "Questions already asked"
3. Ask ONE new question about {current_topic}
4. Acknowledge what they just said before asking your question
5. Keep it conversational and brief (2-3 sentences max)
6. If we have enough info, say so and summarize instead of asking more questions"""

        return await self._call_llm(prompt, system=system_prompt)

    def _update_brief(self, analysis: Dict):
        """Update the idea brief from analysis."""
        if "title" in analysis and analysis["title"]:
            self.brief.title = analysis["title"]
        if "description" in analysis and analysis["description"]:
            self.brief.description = analysis["description"]
        if "problem_statement" in analysis and analysis["problem_statement"]:
            self.brief.problem_statement = analysis["problem_statement"]
        if "target_users" in analysis and analysis["target_users"]:
            self.brief.target_users = analysis["target_users"]
        if "core_features" in analysis and analysis["core_features"]:
            self.brief.core_features = analysis["core_features"]
        if "success_criteria" in analysis and analysis["success_criteria"]:
            self.brief.success_criteria = analysis["success_criteria"]
        if "technical_requirements" in analysis and analysis["technical_requirements"]:
            self.brief.technical_requirements = analysis["technical_requirements"]
        if "constraints" in analysis and analysis["constraints"]:
            self.brief.constraints = analysis["constraints"]
        if "scope" in analysis and analysis["scope"]:
            self.brief.scope = analysis["scope"]
        if "readiness_score" in analysis:
            self.brief.readiness_score = int(analysis["readiness_score"])

    def _generate_summary(self) -> str:
        """Generate a type-appropriate summary when conversation is complete."""
        features = "\n".join(f"  - {f}" for f in self.brief.core_features) if self.brief.core_features else "  - To be defined"
        criteria = "\n".join(f"  - {c}" for c in self.brief.success_criteria) if self.brief.success_criteria else "  - To be defined"

        idea_type = self.brief.idea_type
        config = IDEA_CONFIGS.get(self._detected_type) if self._detected_type else None
        icon = config.icon if config else "📋"
        type_name = config.name if config else "Project"

        # For PRODUCT ideas, show project type instead of generic "Product"
        if idea_type == "product" and self.brief.project_type:
            proj_config = self._project_type_detector.get_config(
                ProjectType(self.brief.project_type)
            ) if self.brief.project_type else None
            if proj_config:
                icon = proj_config.icon or icon
                type_name = proj_config.name

        # Type-specific labels
        labels = {
            "product": {"features": "Core Features", "verb": "build", "action": "Start Planning"},
            "process": {"features": "Key Steps", "verb": "design", "action": "Start Designing"},
            "research": {"features": "Research Questions", "verb": "investigate", "action": "Start Research"},
            "concept": {"features": "Key Aspects", "verb": "explore", "action": "Start Exploring"},
            "decision": {"features": "Options", "verb": "decide", "action": "Start Analysis"},
            "document": {"features": "Key Sections", "verb": "write", "action": "Start Writing"},
        }
        type_labels = labels.get(idea_type, {"features": "Core Elements", "verb": "accomplish", "action": "Start Planning"})

        # Build stack line for products
        stack_line = ""
        if idea_type == "product" and self.brief.suggested_stack:
            stack_line = f"\n**Suggested Stack:** {', '.join(self.brief.suggested_stack)}"

        return f"""Great! I have a clear picture of what you want to {type_labels['verb']}. Here's the summary:

{icon} **{self.brief.title}** ({type_name})

{self.brief.description}

**Why:** {self.brief.problem_statement}

**Who:** {self.brief.target_users}

**{type_labels['features']}:**
{features}

**Success Criteria:**
{criteria}

**Scope:** {self.brief.scope}{stack_line}
{f"**Technical Notes:** {self.brief.technical_requirements}" if self.brief.technical_requirements else ""}
{f"**Constraints:** {self.brief.constraints}" if self.brief.constraints else ""}

---
**Readiness Score: {self.brief.readiness_score}/100**

This is ready for Sketch to create a detailed plan. Click "{type_labels['action']}" when you're ready!"""

    def get_current_question(self) -> Dict[str, Any]:
        """Get current state for the UI."""
        # Get type info
        config = IDEA_CONFIGS.get(self._detected_type) if self._detected_type else None
        type_info = {
            "type": self.brief.idea_type,
            "confidence": self.brief.idea_type_confidence,
            "name": config.name if config else "Unknown",
            "icon": config.icon if config else "📋",
            "confirmed": self._type_confirmed,
        } if config else None

        if self.is_complete:
            return {
                "complete": True,
                "stage": "complete",
                "summary": self._generate_summary(),
                "brief": self.brief.to_dict(),
                "idea_type": type_info,
            }

        last_assistant = None
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                last_assistant = msg.content
                break

        return {
            "complete": False,
            "stage": "conversation",
            "question": last_assistant or "Tell me about your idea...",
            "readiness_score": self.brief.readiness_score,
            "brief": self.brief.to_dict(),
            "idea_type": type_info,
        }

    def get_messages(self) -> List[Dict]:
        """Get all messages."""
        return [m.to_dict() for m in self.messages]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize conversation state."""
        return {
            "messages": self.get_messages(),
            "brief": self.brief.to_dict(),
            "is_complete": self.is_complete,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        openai_api_key: str = None,
        openai_model: str = "gpt-4o-mini",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3",
    ) -> "SmartIdeaConversation":
        """Deserialize conversation state."""
        conv = cls(
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
            ))

        # Restore brief
        brief_data = data.get("brief", {})
        idea_type_str = brief_data.get("idea_type", "unknown")
        idea_type_confidence = brief_data.get("idea_type_confidence", 0.0)

        conv.brief = IdeaBrief(
            title=brief_data.get("title", ""),
            description=brief_data.get("description", ""),
            problem_statement=brief_data.get("problem_statement", ""),
            target_users=brief_data.get("target_users", ""),
            core_features=brief_data.get("core_features", []),
            success_criteria=brief_data.get("success_criteria", []),
            technical_requirements=brief_data.get("technical_requirements", ""),
            constraints=brief_data.get("constraints", ""),
            scope=brief_data.get("scope", ""),
            readiness_score=brief_data.get("readiness_score", 0),
            idea_type=idea_type_str,
            idea_type_confidence=idea_type_confidence,
            project_type=brief_data.get("project_type", ""),
            project_category=brief_data.get("project_category", ""),
            project_type_confidence=brief_data.get("project_type_confidence", 0.0),
            suggested_stack=brief_data.get("suggested_stack", []),
        )

        # Restore detected type enum
        try:
            conv._detected_type = IdeaType(idea_type_str)
            conv._type_confirmed = idea_type_confidence >= 0.7
        except ValueError:
            conv._detected_type = IdeaType.UNKNOWN
            conv._type_confirmed = False

        # Restore project type confirmation
        conv._project_type_confirmed = brief_data.get("project_type_confidence", 0.0) >= 0.7

        conv.is_complete = data.get("is_complete", False)

        return conv

    def get_architect_brief(self) -> str:
        """Generate a comprehensive, type-appropriate brief for the Architect."""
        features = "\n".join(f"- {f}" for f in self.brief.core_features)
        criteria = "\n".join(f"- {c}" for c in self.brief.success_criteria)

        idea_type = self.brief.idea_type
        config = IDEA_CONFIGS.get(self._detected_type) if self._detected_type else None
        type_name = config.name if config else "Project"
        phases = config.phases if config else ["plan", "build", "verify", "deliver"]

        # Type-specific brief formats
        if idea_type == "process":
            return f"""# Process Design Brief: {self.brief.title}

## Overview
{self.brief.description}

## Problem Being Solved
{self.brief.problem_statement}

## Process Participants
{self.brief.target_users}

## Key Steps / Actions
{features}

## Success Criteria
{criteria}

## Tools & Systems
{self.brief.technical_requirements or "No specific tools required"}

## Rules & Constraints
{self.brief.constraints or "None specified"}

## Scope
{self.brief.scope}

## Phases
Design → Document → Review → Deliver

---
*This process brief was developed through an interactive conversation.*
"""
        elif idea_type == "research":
            return f"""# Research Brief: {self.brief.title}

## Research Topic
{self.brief.description}

## Research Purpose
{self.brief.problem_statement}

## Who Needs This Research
{self.brief.target_users}

## Key Questions to Answer
{features}

## Success Criteria
{criteria}

## Depth & Format
{self.brief.technical_requirements or "Standard depth - comprehensive but focused"}

## Scope & Limitations
{self.brief.constraints or "None specified"}
Scope: {self.brief.scope}

## Phases
Scope → Investigate → Synthesize → Deliver

---
*This research brief was developed through an interactive conversation.*
"""
        elif idea_type == "concept":
            return f"""# Concept Exploration Brief: {self.brief.title}

## The Concept
{self.brief.description}

## Origin / Inspiration
{self.brief.problem_statement}

## Who This Affects
{self.brief.target_users}

## Key Aspects to Explore
{features}

## What Success Looks Like
{criteria}

## Considerations
{self.brief.technical_requirements or "No specific constraints"}

## Boundaries
{self.brief.constraints or "None specified"}
Exploration Depth: {self.brief.scope}

## Phases
Explore → Expand → Synthesize → Deliver

---
*This concept brief was developed through an interactive conversation.*
"""
        elif idea_type == "decision":
            return f"""# Decision Brief: {self.brief.title}

## Decision Context
{self.brief.description}

## Why This Decision Matters
{self.brief.problem_statement}

## Who Is Affected
{self.brief.target_users}

## Options Being Considered
{features}

## Decision Criteria
{criteria}

## Evaluation Factors
{self.brief.technical_requirements or "Standard evaluation approach"}

## Constraints & Dealbreakers
{self.brief.constraints or "None specified"}

## Decision Scope
{self.brief.scope}

## Phases
Frame → Analyze → Recommend → Deliver

---
*This decision brief was developed through an interactive conversation.*
"""
        elif idea_type == "document":
            return f"""# Document Brief: {self.brief.title}

## Document Purpose
{self.brief.description}

## Why This Document Is Needed
{self.brief.problem_statement}

## Target Audience
{self.brief.target_users}

## Key Sections / Topics
{features}

## Success Criteria
{criteria}

## Format & Style
{self.brief.technical_requirements or "Standard professional format"}

## Requirements & Guidelines
{self.brief.constraints or "None specified"}

## Document Scope
{self.brief.scope}

## Phases
Outline → Draft → Review → Deliver

---
*This document brief was developed through an interactive conversation.*
"""
        else:
            # Default product format
            return f"""# Project Brief: {self.brief.title}

## Overview
{self.brief.description}

## Problem Statement
{self.brief.problem_statement}

## Target Users
{self.brief.target_users}

## Core Features
{features}

## Success Criteria
{criteria}

## Scope
{self.brief.scope}

## Technical Requirements
{self.brief.technical_requirements or "No specific requirements - use best practices"}

## Constraints
{self.brief.constraints or "None specified"}

## Phases
Plan → Build → Verify → Deliver

---
*This brief was developed through an interactive conversation to ensure clarity and completeness.*
"""
