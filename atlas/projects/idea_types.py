"""
Idea Type Detection and Classification

Detects what kind of idea the user has based on conversation cues,
and provides appropriate workflows for each type.
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class IdeaType(Enum):
    """Types of ideas ATLAS can help with."""
    PRODUCT = "product"       # Build something (app, website, tool, API)
    PROCESS = "process"       # Design a workflow, SOP, automation
    RESEARCH = "research"     # Investigate, compare, learn about something
    CONCEPT = "concept"       # Explore and flesh out an abstract idea
    DECISION = "decision"     # Make a choice between options
    DOCUMENT = "document"     # Write something (report, proposal, plan)
    UNKNOWN = "unknown"       # Not yet determined


@dataclass
class IdeaTypeConfig:
    """Configuration for each idea type."""
    type: IdeaType
    name: str
    description: str
    icon: str
    phases: list[str]
    agent_roles: dict[str, str]  # agent_name: role_description
    output_format: str
    conversation_stages: list[dict]


# Detection patterns for each idea type
DETECTION_PATTERNS = {
    IdeaType.PRODUCT: {
        "keywords": [
            r'\b(build|create|make|develop|code|app|website|tool|api|software|platform|system)\b',
            r'\b(implement|program|application|mobile app|web app|service)\b',
        ],
        "phrases": [
            r'i want to (build|create|make|develop)',
            r'can you (build|create|make|develop)',
            r'let\'s (build|create|make)',
            r'need (a|an) (app|tool|website|api|system)',
        ],
        "weight": 1.0,
    },
    IdeaType.PROCESS: {
        "keywords": [
            r'\b(process|workflow|procedure|steps|automation|automate|routine|sop)\b',
            r'\b(how (do|should|can) (we|i|you)|checklist|template|guide)\b',
        ],
        "phrases": [
            r'how (do|should|can) (we|i) (handle|manage|do|organize)',
            r'what\'s the (best|right) (way|process|procedure)',
            r'create a (process|workflow|procedure)',
            r'automate (the|this|my)',
            r'streamline',
        ],
        "weight": 1.0,
    },
    IdeaType.RESEARCH: {
        "keywords": [
            r'\b(research|investigate|explore|study|learn|understand|find out)\b',
            r'\b(what is|how does|why does|explain|tell me about)\b',
        ],
        "phrases": [
            r'(what|how|why) (is|are|does|do)',
            r'tell me (about|more)',
            r'i want to (learn|understand|know)',
            r'research (on|about|into)',
            r'find (out|information)',
        ],
        "weight": 0.8,  # Lower weight as questions are common
    },
    IdeaType.CONCEPT: {
        "keywords": [
            r'\b(idea|concept|theory|thinking|thought|vision|imagine)\b',
            r'\b(what if|brainstorm|explore|flesh out|develop the idea)\b',
        ],
        "phrases": [
            r'i\'ve been thinking (about|of)',
            r'what if (we|i|there)',
            r'i have (an idea|a concept|this idea)',
            r'let\'s (brainstorm|explore|think about)',
            r'help me (think through|flesh out|develop)',
        ],
        "weight": 1.0,
    },
    IdeaType.DECISION: {
        "keywords": [
            r'\b(decide|decision|choose|choice|option|compare|versus|vs)\b',
            r'\b(should (i|we)|which (one|is better)|pros and cons)\b',
        ],
        "phrases": [
            r'should (i|we) (use|go with|choose|pick)',
            r'(compare|comparing) .+ (to|vs|versus|and)',
            r'which (one|is better|should)',
            r'(pros|cons) (and|of)',
            r'help me (decide|choose)',
            r'what\'s the (best|better) (option|choice)',
        ],
        "weight": 1.0,
    },
    IdeaType.DOCUMENT: {
        "keywords": [
            r'\b(write|draft|document|report|proposal|plan|memo|email|letter)\b',
            r'\b(documentation|readme|guide|manual|spec|specification)\b',
        ],
        "phrases": [
            r'write (a|an|the|me)',
            r'draft (a|an|the)',
            r'help me write',
            r'create (a|an) (document|report|proposal|plan)',
            r'document (the|this|my)',
        ],
        "weight": 1.0,
    },
}


# Workflow configurations for each idea type
IDEA_CONFIGS = {
    IdeaType.PRODUCT: IdeaTypeConfig(
        type=IdeaType.PRODUCT,
        name="Product",
        description="Build something - an app, website, tool, or system",
        icon="🔨",
        phases=["plan", "build", "verify", "deliver"],
        agent_roles={
            "architect": "Plan the technical implementation, architecture, and approach",
            "mason": "Write the code and build the solution",
            "oracle": "Verify code quality, security, and correctness",
        },
        output_format="code",
        conversation_stages=[
            {"id": "clarify_goal", "question": "What problem does this solve? Who has this problem?"},
            {"id": "features", "question": "What are the must-have features? List the top 3-5."},
            {"id": "users", "question": "Who will use this? Describe your target users."},
            {"id": "technical", "question": "Any technical preferences? Languages, frameworks, or platforms?"},
            {"id": "constraints", "question": "Any constraints? Timeline, budget, or limitations?"},
        ],
    ),
    IdeaType.PROCESS: IdeaTypeConfig(
        type=IdeaType.PROCESS,
        name="Process",
        description="Design a workflow, procedure, or system of steps",
        icon="⚙️",
        phases=["design", "document", "review", "deliver"],
        agent_roles={
            "architect": "Design the workflow structure, identify steps and decision points",
            "mason": "Document the process with clear steps, templates, and checklists",
            "oracle": "Review for gaps, edge cases, and improvements",
        },
        output_format="workflow",
        conversation_stages=[
            {"id": "clarify_goal", "question": "What's the goal of this process? What should it achieve?"},
            {"id": "current_state", "question": "How is this currently done? What's not working?"},
            {"id": "stakeholders", "question": "Who's involved in this process? Who does what?"},
            {"id": "triggers", "question": "What triggers this process? How does it start and end?"},
            {"id": "constraints", "question": "Any rules, requirements, or constraints to follow?"},
        ],
    ),
    IdeaType.RESEARCH: IdeaTypeConfig(
        type=IdeaType.RESEARCH,
        name="Research",
        description="Investigate a topic, gather information, learn something",
        icon="🔍",
        phases=["scope", "investigate", "synthesize", "deliver"],
        agent_roles={
            "architect": "Define research questions, scope, and methodology",
            "mason": "Gather information, find sources, compile findings",
            "oracle": "Fact-check, identify gaps, validate conclusions",
        },
        output_format="report",
        conversation_stages=[
            {"id": "clarify_goal", "question": "What do you want to learn or find out?"},
            {"id": "context", "question": "What do you already know? Any background context?"},
            {"id": "scope", "question": "How deep should we go? Quick overview or detailed analysis?"},
            {"id": "focus", "question": "Any specific aspects or angles to focus on?"},
            {"id": "output", "question": "How will you use this research? What format is most useful?"},
        ],
    ),
    IdeaType.CONCEPT: IdeaTypeConfig(
        type=IdeaType.CONCEPT,
        name="Concept",
        description="Explore and develop an abstract idea or vision",
        icon="💡",
        phases=["explore", "expand", "synthesize", "deliver"],
        agent_roles={
            "architect": "Explore the concept space, identify dimensions and possibilities",
            "mason": "Develop the idea, add detail, create frameworks",
            "oracle": "Challenge assumptions, find weaknesses, strengthen the concept",
        },
        output_format="concept_doc",
        conversation_stages=[
            {"id": "clarify_goal", "question": "Tell me about this idea. What's the core concept?"},
            {"id": "inspiration", "question": "What inspired this? What problem or opportunity sparked it?"},
            {"id": "vision", "question": "If this idea fully existed, what would it look like?"},
            {"id": "concerns", "question": "What concerns or unknowns do you have about it?"},
            {"id": "next_steps", "question": "What would help most - exploring possibilities, finding gaps, or making it concrete?"},
        ],
    ),
    IdeaType.DECISION: IdeaTypeConfig(
        type=IdeaType.DECISION,
        name="Decision",
        description="Evaluate options and make a choice",
        icon="⚖️",
        phases=["frame", "analyze", "recommend", "deliver"],
        agent_roles={
            "architect": "Frame the decision, identify criteria and options",
            "mason": "Analyze each option, gather pros/cons, create comparison",
            "oracle": "Validate analysis, identify biases, stress-test recommendation",
        },
        output_format="decision_doc",
        conversation_stages=[
            {"id": "clarify_goal", "question": "What decision are you trying to make?"},
            {"id": "options", "question": "What are the options you're considering?"},
            {"id": "criteria", "question": "What matters most? What criteria should drive this decision?"},
            {"id": "constraints", "question": "Any constraints or dealbreakers?"},
            {"id": "timeline", "question": "When do you need to decide? How reversible is this?"},
        ],
    ),
    IdeaType.DOCUMENT: IdeaTypeConfig(
        type=IdeaType.DOCUMENT,
        name="Document",
        description="Write a document, report, or other written content",
        icon="📝",
        phases=["outline", "draft", "review", "deliver"],
        agent_roles={
            "architect": "Create the structure, outline key sections and points",
            "mason": "Write the content, develop each section",
            "oracle": "Review for clarity, completeness, and quality",
        },
        output_format="document",
        conversation_stages=[
            {"id": "clarify_goal", "question": "What kind of document? What's its purpose?"},
            {"id": "audience", "question": "Who will read this? What do they need to know or do?"},
            {"id": "key_points", "question": "What are the main points or messages?"},
            {"id": "tone", "question": "What tone? Formal, casual, technical, persuasive?"},
            {"id": "length", "question": "How long should it be? Any format requirements?"},
        ],
    ),
}


class IdeaTypeDetector:
    """Detects the type of idea from conversation text."""

    def __init__(self):
        self.patterns = DETECTION_PATTERNS
        self.configs = IDEA_CONFIGS

    def detect(self, text: str, context: Optional[dict] = None) -> tuple[IdeaType, float]:
        """
        Detect the idea type from text.

        Args:
            text: The conversation text to analyze
            context: Optional context from previous messages

        Returns:
            Tuple of (IdeaType, confidence score 0-1)
        """
        text_lower = text.lower()
        scores = {idea_type: 0.0 for idea_type in IdeaType if idea_type != IdeaType.UNKNOWN}

        for idea_type, patterns in self.patterns.items():
            weight = patterns.get("weight", 1.0)

            # Check keywords
            for keyword_pattern in patterns.get("keywords", []):
                matches = re.findall(keyword_pattern, text_lower, re.IGNORECASE)
                scores[idea_type] += len(matches) * 0.5 * weight

            # Check phrases (higher weight)
            for phrase_pattern in patterns.get("phrases", []):
                matches = re.findall(phrase_pattern, text_lower, re.IGNORECASE)
                scores[idea_type] += len(matches) * 1.5 * weight

        # Find the highest scoring type
        if not scores or max(scores.values()) == 0:
            return IdeaType.UNKNOWN, 0.0

        best_type = max(scores, key=scores.get)
        max_score = scores[best_type]

        # Normalize confidence (cap at 1.0)
        total_score = sum(scores.values())
        if total_score > 0:
            confidence = min(max_score / total_score, 1.0)
            # Boost confidence if score is high enough
            if max_score >= 3.0:
                confidence = max(confidence, 0.8)
        else:
            confidence = 0.0

        return best_type, confidence

    def detect_from_conversation(self, messages: list[dict]) -> tuple[IdeaType, float]:
        """
        Detect idea type from a full conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Tuple of (IdeaType, confidence)
        """
        # Weight recent messages more heavily
        combined_text = ""
        for i, msg in enumerate(messages):
            if msg.get("role") == "user":
                # More weight to recent and first messages
                weight = 2 if i == 0 else (1.5 if i >= len(messages) - 2 else 1)
                combined_text += (msg.get("content", "") + " ") * int(weight)

        return self.detect(combined_text)

    def get_config(self, idea_type: IdeaType) -> IdeaTypeConfig:
        """Get the configuration for an idea type."""
        return self.configs.get(idea_type, self.configs[IdeaType.PRODUCT])

    def get_conversation_stages(self, idea_type: IdeaType) -> list[dict]:
        """Get conversation stages for an idea type."""
        config = self.get_config(idea_type)
        return config.conversation_stages

    def get_phases(self, idea_type: IdeaType) -> list[str]:
        """Get workflow phases for an idea type."""
        config = self.get_config(idea_type)
        return config.phases

    def suggest_type(self, text: str) -> dict:
        """
        Suggest idea type with explanation.

        Returns dict with type, confidence, and reasoning.
        """
        idea_type, confidence = self.detect(text)

        if idea_type == IdeaType.UNKNOWN or confidence < 0.3:
            return {
                "type": IdeaType.UNKNOWN,
                "confidence": confidence,
                "suggestion": "I'm not sure what type of idea this is yet. Can you tell me more?",
                "options": [
                    {"type": t.value, "name": c.name, "icon": c.icon, "desc": c.description}
                    for t, c in self.configs.items()
                ],
            }

        config = self.get_config(idea_type)
        return {
            "type": idea_type,
            "confidence": confidence,
            "name": config.name,
            "icon": config.icon,
            "description": config.description,
            "phases": config.phases,
            "suggestion": f"This sounds like a {config.name.lower()} - {config.description.lower()}. Should we proceed with this approach?",
        }
