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


# Required topics that must be discussed before analysis (by product type)
REQUIRED_TOPICS = {
    "printable": {
        "what_it_is": "What kind of printable (planner, journal, worksheet, etc.)",
        "who_its_for": "Who will use this and their situation",
        "problem_solved": "What problem or need it addresses",
        "key_sections": "Main sections, pages, or components",
        "how_theyll_use_it": "How and when people will use it",
        "style_preferences": "Look and feel (minimal, colorful, etc.)",
        "price_expectations": "What they'd charge or what similar products cost",
    },
    "document": {
        "what_it_is": "Type of document (ebook, guide, workbook, etc.)",
        "who_its_for": "Target reader and their current situation",
        "problem_solved": "What transformation or learning it provides",
        "key_sections": "Main chapters or sections",
        "format": "Length, format, exercises included",
        "unique_angle": "What makes this different from other resources",
        "price_expectations": "Pricing thoughts",
    },
    "web": {
        "what_it_does": "Core function of the site",
        "who_its_for": "Who will use it and why",
        "problem_solved": "What problem it solves",
        "key_features": "Main features for first version",
        "user_accounts": "Whether people need to sign up/log in",
        "monetization": "How it makes money (if applicable)",
        "similar_sites": "Sites that do something similar",
    },
    "app": {
        "what_it_does": "Core function of the app",
        "who_its_for": "Who will use it",
        "when_theyd_use_it": "The moment someone opens the app",
        "key_screens": "Main screens or features",
        "platform": "iOS, Android, or both",
        "offline_needs": "Whether it needs to work offline",
        "similar_apps": "Apps that do something similar",
    },
}


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
    # Design preferences
    design_style: str = ""  # minimal, playful, corporate, elegant, bold, etc.
    color_scheme: str = ""  # user's color preferences or theme
    design_inspiration: str = ""  # apps/sites they like, reference examples
    design_priorities: List[str] = field(default_factory=list)  # e.g., ["easy to use", "visually impressive", "fast"]
    # Topic tracking for thorough conversations
    topics_covered: Dict[str, bool] = field(default_factory=dict)
    # Market research (filled by Analyst)
    competitors: List[str] = field(default_factory=list)
    price_range: str = ""
    market_opportunity: str = ""

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
            "design_style": self.design_style,
            "color_scheme": self.color_scheme,
            "design_inspiration": self.design_inspiration,
            "design_priorities": self.design_priorities,
            "topics_covered": self.topics_covered,
            "competitors": self.competitors,
            "price_range": self.price_range,
            "market_opportunity": self.market_opportunity,
        }

    def is_ready(self) -> bool:
        """Check if the idea is ready for the Architect."""
        return self.readiness_score >= 80

    def get_missing_elements(self) -> List[str]:
        """Get list of missing or weak elements."""
        missing = []
        # CRITICAL: Product format/type should be asked FIRST
        if not self.project_type and not self.project_category:
            missing.insert(0, "product format (digital app/website vs physical/printable)")
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
        # Check for design preferences on visual projects
        if self.project_category in ["app", "web", ""]:
            if not self.design_style and not self.color_scheme:
                missing.append("design preferences (style, colors, inspiration)")
        return missing

    def get_required_topics(self) -> Dict[str, str]:
        """Get required topics for this product type."""
        return REQUIRED_TOPICS.get(self.project_category, REQUIRED_TOPICS.get("printable", {}))

    def get_topics_coverage(self) -> tuple:
        """Get (covered_count, total_count, percentage) for required topics."""
        required = self.get_required_topics()
        if not required:
            return (0, 0, 100)
        covered = sum(1 for topic in required if self.topics_covered.get(topic, False))
        total = len(required)
        percentage = int((covered / total) * 100) if total > 0 else 100
        return (covered, total, percentage)

    def get_uncovered_topics(self) -> List[tuple]:
        """Get list of (topic_key, topic_description) that haven't been covered."""
        required = self.get_required_topics()
        uncovered = []
        for key, description in required.items():
            if not self.topics_covered.get(key, False):
                uncovered.append((key, description))
        return uncovered

    def is_ready_for_analysis(self) -> bool:
        """Check if enough topics are covered for analysis (at least 80%)."""
        covered, total, percentage = self.get_topics_coverage()
        return percentage >= 80


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

    SYSTEM_PROMPT = """You're helping someone figure out what they want to create. Talk like a friendly person, not a consultant.

HOW TO TALK:
- Use plain, everyday language
- Keep responses short - 2-3 sentences is usually enough
- Ask one question at a time
- If their answer is vague, ask a follow-up: "Tell me more about that"

WHAT TO FIND OUT:
- What are they making? (app, website, printable, guide, etc.)
- Who is it for?
- What problem does it solve or what does it help people do?
- What are the main parts or features?

IF THEY ASK FOR YOUR IDEAS:
- Give them 2-3 simple suggestions
- Ask which sounds right to them

IF THEY SAY "I don't know":
- Offer a couple options: "It could be something like X, or maybe Y - which sounds closer?"
- Help them figure it out, don't just wait for them to know

DON'T:
- Use jargon like "users", "target audience", "value proposition", "monetization"
- Ask multiple questions at once
- Give long responses
- Sound like a business consultant

Talk like you're helping a friend figure out their idea over coffee."""

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
    "design_style": "visual style: minimal, playful, corporate, elegant, bold, etc.",
    "color_scheme": "color preferences or theme mentioned",
    "design_inspiration": "apps/websites they referenced as inspiration",
    "design_priorities": ["what matters most in the design, e.g. 'easy to use', 'fun', 'professional'"],
    "readiness_score": 0-100,
    "missing_elements": ["what's still unclear - INCLUDE design preferences if not discussed for visual projects"],
    "next_question": "a NEW question not yet asked (or empty string if ready)"
}}

IMPORTANT:
- The next_question MUST be different from all questions already asked.
- CRITICAL: If product format is unclear (digital vs physical, app vs web vs printable), ASK ABOUT THIS FIRST before other questions.
- For apps/websites, ASK about design preferences (style, colors, inspiration) if not yet discussed.
- If readiness >= 80, set next_question to empty string.
- Do NOT mark readiness >= 80 until product format is clear.

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
1. CRITICAL: If product FORMAT is unclear (digital vs physical, app vs web vs printable), this MUST be the next_question. Do not proceed without knowing this.
2. If the user has clearly stated WHAT they want to build, WHO it's for, and WHAT FORMAT, that's 60-70% ready
3. Simple, straightforward ideas should reach 80+ quickly - don't over-complicate
4. The next_question MUST be different from all questions already asked
5. If we have enough info (readiness >= 80), set next_question to empty string
6. Do NOT set readiness >= 80 until product format is known

RESPOND ONLY WITH THE JSON OBJECT, no other text."""

    def __init__(
        self,
        openai_api_key: str = None,
        openai_model: str = "gpt-4o-mini",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3",
        project_identity: Optional[Dict[str, Any]] = None,  # Canonical product type from form
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
        # Canonical project identity from user's explicit selection
        self._project_identity = project_identity
        if project_identity:
            # Pre-populate brief with known product type
            self.brief.project_category = project_identity.get("product_type", "")
            self._project_type_confirmed = True  # Don't ask - we already know!

    # Type-specific opening questions
    # Friendly openers in plain language - no jargon
    TYPE_SPECIFIC_OPENERS = {
        "printable": """Nice! I love helping people create printables.

So tell me more about what you're picturing. Is this a planner, a journal, worksheets, something else? And what's it helping people do - stay organized, track something, learn something new?

Paint me a picture of who's going to use this and what problem it solves for them.""",

        "document": """Cool! Let's figure out what you want to create.

Is this like a guide, an ebook, a workbook, or something else? And who's it for - what do you want them to walk away knowing or being able to do?

Tell me more about what you're thinking.""",

        "web": """Awesome! Let's talk about what you want to build.

What's the main thing people will come to your site to do? And who are these people - what problem are you solving for them?

Walk me through what you're imagining.""",

        "app": """Cool! Let's figure out what you want this app to do.

When someone pulls out their phone and opens your app, what are they trying to do? Is it something they'd do every day, once in a while, or just when they need it?

Tell me more about what you're picturing.""",
    }

    # Type-specific topics to explore (plain language)
    TYPE_SPECIFIC_TOPICS = {
        "printable": {
            1: "what kind of printable this is and what it helps people do",
            2: "who's going to use this and what their day-to-day life is like",
            3: "what sections or pages it should have",
            4: "how it should look - size, style, colors",
            5: "how people will actually use it - when, how often, where",
        },
        "document": {
            1: "what this guide or ebook is about and what people will learn",
            2: "who's going to read this and what they're struggling with",
            3: "what the main sections or chapters should cover",
            4: "the format - is it a quick read, a detailed guide, a workbook with exercises",
            5: "what makes this different from other stuff on the topic",
        },
        "web": {
            1: "what the main thing people will do on this site",
            2: "who's going to use it and what problem it solves for them",
            3: "what features it needs to have when it first launches",
            4: "how people will find it and what makes them come back",
            5: "whether it needs accounts, payments, or other features",
        },
        "app": {
            1: "what the app does and when someone would open it",
            2: "who's going to use it and what phones they have",
            3: "what the main screens should be",
            4: "whether it needs to work offline or connect to other things",
            5: "what would make people use it regularly",
        },
    }

    # Friendly system prompts - talk like a helpful friend, not a consultant
    TYPE_SPECIFIC_SYSTEM_PROMPTS = {
        "printable": """You're helping someone figure out what printable they want to create - like a planner, journal, or worksheet.

Talk like a friendly person who's helped create a lot of these before. Use plain, everyday language. No business jargon.

YOUR JOB:
- Help them get clear on what they're making and who it's for
- Ask about the practical stuff: What sections should it have? How will people use it day to day?
- If they're unsure, offer simple suggestions: "A lot of planners have a spot for goals at the top - would that be helpful?"
- Think about real life: Will they print this at home? How much time do they have to fill it out?

KEEP IT SIMPLE:
- Short responses, 2-3 sentences usually
- One question at a time
- If they give a short answer, ask a follow-up: "Tell me more about that"
- Use words like "you" and "they" not "users" or "target audience" """,

        "document": """You're helping someone figure out what guide or ebook they want to write.

Talk like a friendly person helping them think it through. Plain language, no marketing speak.

YOUR JOB:
- Help them get clear on what they're writing and who it's for
- Ask what readers will learn or be able to do after reading it
- If they're unsure about structure, offer simple ideas: "Some guides start with the basics, then go deeper - would that work?"
- Think about their reader: What do they already know? What's confusing them?

KEEP IT SIMPLE:
- Short responses
- One question at a time
- No words like "transformation" or "value proposition" - just talk normally""",

        "web": """You're helping someone figure out what website or web app they want to build.

Talk like a friend who knows about websites. Plain language, no tech jargon unless they use it first.

YOUR JOB:
- Help them get clear on what the site does and who it's for
- Ask about the main thing people will do on the site
- If they mention lots of features, help them focus: "If you could only build one thing first, what would it be?"
- Think practically: Do people need to log in? Will they come back regularly or just once?

KEEP IT SIMPLE:
- Short responses
- One question at a time
- Say "website" not "platform", "people" not "users" """,

        "app": """You're helping someone figure out what phone app they want to build.

Talk like a friend who knows about apps. Plain language, not technical.

YOUR JOB:
- Help them get clear on what the app does and who it's for
- Ask when someone would open this app - what are they trying to do in that moment?
- If they have lots of ideas, help them focus: "What's the one main thing the app needs to do?"
- Think about real phone use: Is this something people do every day? While waiting in line? At home?

KEEP IT SIMPLE:
- Short responses
- One question at a time
- Say "phone" not "mobile device", "people" not "users" """,
    }

    async def start(self, initial_idea: str = "") -> str:
        """Start the conversation, optionally with an initial idea."""
        if initial_idea and initial_idea.strip():
            # User provided an initial idea
            self.messages.append(ConversationMessage(
                role="user",
                content=initial_idea.strip(),
                timestamp=datetime.now().isoformat(),
            ))

            # Check if we have a locked project_identity (user already chose product type)
            if self._project_identity and self._project_identity.get("locked"):
                product_type = self._project_identity.get("product_type", "")
                product_name = self._project_identity.get("product_type_name", product_type.title())

                # Set the brief with known type
                self.brief.project_category = product_type
                self._project_type_confirmed = True
                self._type_confirmed = True
                self._detected_type = IdeaType.PRODUCT
                self.brief.idea_type = "product"
                self.brief.idea_type_confidence = 1.0

                # Generate a response that actually acknowledges what they said
                system_prompt = self.TYPE_SPECIFIC_SYSTEM_PROMPTS.get(product_type, self.SYSTEM_PROMPT)

                first_response_prompt = f"""Someone just told you their idea: "{initial_idea}"

They want to create a {product_name.lower()}.

Write a friendly first response that:
1. Shows you understood what they said (don't repeat it back word for word, just acknowledge it naturally)
2. Asks ONE follow-up question to learn more

Keep it short - 2-3 sentences max. Sound like a friend, not a consultant. No jargon."""

                response = await self._call_llm(first_response_prompt, system=system_prompt)

                # Clean up response if needed
                response = response.strip()

                self.messages.append(ConversationMessage(
                    role="assistant",
                    content=response,
                    timestamp=datetime.now().isoformat(),
                ))
                return response

            # No project_identity - use detection (legacy flow)
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

            # Detect which topics have been covered
            topics_covered = await self._detect_topics_covered()
            self.brief.topics_covered.update(topics_covered)

            # Calculate readiness based on topic coverage
            covered, total, coverage_pct = self.brief.get_topics_coverage()

            # Readiness = topic coverage (main driver)
            # Give a small boost per message to avoid getting stuck
            msg_bonus = min(user_messages * 5, 20)  # Up to 20% bonus for engagement
            self.brief.readiness_score = min(coverage_pct + msg_bonus, 100)

            # Log progress
            print(f"[SmartConversation] Exchange #{user_messages}, Topics: {covered}/{total} ({coverage_pct}%), "
                  f"Readiness: {self.brief.readiness_score}%")

            # Check if all required topics are covered (or max 12 exchanges as safety valve)
            if coverage_pct >= 100 or user_messages >= 12:
                print(f"[SmartConversation] COMPLETE - all topics covered!")
                self.is_complete = True
                self.brief.readiness_score = max(self.brief.readiness_score, 90)
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

    async def _detect_topics_covered(self) -> Dict[str, bool]:
        """Analyze conversation to detect which required topics have been discussed."""
        required = self.brief.get_required_topics()
        if not required:
            return {}

        conversation_text = "\n".join([
            f"{m.role.upper()}: {m.content}"
            for m in self.messages
        ])

        # Build topic list for the prompt
        topics_list = "\n".join([f"- {key}: {desc}" for key, desc in required.items()])

        prompt = f"""Look at this conversation and determine which topics have been discussed.

CONVERSATION:
{conversation_text}

TOPICS TO CHECK:
{topics_list}

For each topic, mark it as true if the conversation has meaningfully discussed it (not just mentioned in passing).

Return a JSON object with each topic key and true/false:
{{{", ".join([f'"{k}": true/false' for k in required.keys()])}}}

Only return the JSON object, nothing else."""

        try:
            response = await self._call_llm(
                prompt,
                system="You analyze conversations and return JSON. Only output valid JSON."
            )

            # Parse response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            return json.loads(response)
        except Exception as e:
            print(f"[SmartConversation] Topic detection failed: {e}")
            return {}

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

        # Get appropriate system prompt - prefer type-specific prompts when product type is locked
        if self._project_identity and self._project_identity.get("locked"):
            product_type = self._project_identity.get("product_type", "")
            system_prompt = self.TYPE_SPECIFIC_SYSTEM_PROMPTS.get(product_type, self.SYSTEM_PROMPT)
        else:
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
            known_context += f"\n- Who it's for: {self.brief.target_users}"
        if self.brief.core_features:
            known_context += f"\n- Key parts: {', '.join(self.brief.core_features[:3])}"
        if self.brief.problem_statement:
            known_context += f"\n- What it helps with: {self.brief.problem_statement[:100]}"

        # Show topic progress
        covered, total, coverage_pct = self.brief.get_topics_coverage()
        uncovered_topics = self.brief.get_uncovered_topics()

        if self.brief.topics_covered:
            covered_list = [k for k, v in self.brief.topics_covered.items() if v]
            if covered_list:
                known_context += f"\n\n## Topics we've covered ({covered}/{total}):\n- " + "\n- ".join(covered_list)

        if uncovered_topics:
            known_context += f"\n\n## Topics we still need to discuss:\n- " + "\n- ".join([desc for _, desc in uncovered_topics])

        # Track questions already asked
        questions_asked = self._extract_questions_asked()
        if questions_asked:
            recent_questions = questions_asked[-5:]
            known_context += f"\n\n## Questions already asked (don't repeat):\n- " + "\n- ".join(recent_questions)

        # Get the next uncovered topic to focus on
        if uncovered_topics:
            next_topic_key, next_topic_desc = uncovered_topics[0]
            current_topic = next_topic_desc
        else:
            current_topic = "wrapping up - we've covered everything"

        if asking_for_input:
            # User wants suggestions
            prompt = f"""They're asking for your ideas or suggestions. Give them 2-3 simple options.

Previous messages:
{conversation_text}
{known_context}

Give 2-3 short suggestions based on what they've told you. Keep it simple - one sentence each. Then ask which sounds right.

Talk like a friend, not a consultant. No jargon."""
        else:
            # Regular conversation flow
            prompt = f"""Keep the conversation going naturally.

Previous messages:
{conversation_text}
{known_context}

FOCUS ON: {current_topic}

HOW TO RESPOND:
- React to what they just said (don't just say "great!" - actually respond to it)
- Ask ONE follow-up question about {current_topic}
- Keep it short - 2-3 sentences max
- If they gave a short answer, ask them to tell you more
- If they seem unsure, give them a couple options to pick from

TALK LIKE A FRIEND:
- Say "you" and "people" not "users"
- No jargon like "target audience" or "use case"
- Short, casual sentences

DON'T ask about things in "Topics already covered" - we know those already."""

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
        # Design preferences
        if "design_style" in analysis and analysis["design_style"]:
            self.brief.design_style = analysis["design_style"]
        if "color_scheme" in analysis and analysis["color_scheme"]:
            self.brief.color_scheme = analysis["color_scheme"]
        if "design_inspiration" in analysis and analysis["design_inspiration"]:
            self.brief.design_inspiration = analysis["design_inspiration"]
        if "design_priorities" in analysis and analysis["design_priorities"]:
            self.brief.design_priorities = analysis["design_priorities"]

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

        # Get topic coverage
        covered, total, coverage_pct = self.brief.get_topics_coverage()
        required_topics = self.brief.get_required_topics()

        # Include required topics in brief for template
        brief_dict = self.brief.to_dict()
        brief_dict["required_topics"] = required_topics
        brief_dict["topics_coverage_pct"] = coverage_pct

        if self.is_complete:
            return {
                "complete": True,
                "stage": "complete",
                "summary": self._generate_summary(),
                "brief": brief_dict,
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
            "brief": brief_dict,
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
            "project_identity": self._project_identity,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        openai_api_key: str = None,
        openai_model: str = "gpt-4o-mini",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3",
        project_identity: Dict[str, Any] = None,
    ) -> "SmartIdeaConversation":
        """Deserialize conversation state."""
        # Use passed project_identity OR restore from serialized data
        identity = project_identity or data.get("project_identity")

        conv = cls(
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            ollama_url=ollama_url,
            ollama_model=ollama_model,
            project_identity=identity,
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
            # Build design section if available
            design_section = ""
            if self.brief.design_style or self.brief.color_scheme or self.brief.design_inspiration or self.brief.design_priorities:
                design_parts = []
                if self.brief.design_style:
                    design_parts.append(f"- **Style:** {self.brief.design_style}")
                if self.brief.color_scheme:
                    design_parts.append(f"- **Colors:** {self.brief.color_scheme}")
                if self.brief.design_inspiration:
                    design_parts.append(f"- **Inspiration:** {self.brief.design_inspiration}")
                if self.brief.design_priorities:
                    priorities = ", ".join(self.brief.design_priorities) if isinstance(self.brief.design_priorities, list) else self.brief.design_priorities
                    design_parts.append(f"- **Priorities:** {priorities}")
                design_section = f"""

## Design Preferences
{chr(10).join(design_parts)}
"""
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
{design_section}
## Technical Requirements
{self.brief.technical_requirements or "No specific requirements - use best practices"}

## Constraints
{self.brief.constraints or "None specified"}

## Phases
Plan → Build → Verify → Deliver

---
*This brief was developed through an interactive conversation to ensure clarity and completeness.*
"""
