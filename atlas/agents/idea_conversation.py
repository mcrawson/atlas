"""
ATLAS Idea Conversation System

An interactive conversation flow to help users formulate their project ideas.
Asks targeted questions to extract clear requirements, features, and constraints.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import re


class ConversationStage(Enum):
    """Stages of the idea conversation."""
    INITIAL = "initial"           # First message - what do you want to build?
    CLARIFY_GOAL = "clarify_goal" # What problem does it solve?
    FEATURES = "features"         # What features do you need?
    USERS = "users"               # Who will use it?
    TECHNICAL = "technical"       # Any technical preferences?
    CONSTRAINTS = "constraints"   # Timeline, budget, limitations?
    SUMMARY = "summary"           # Confirm the idea
    COMPLETE = "complete"         # Ready to plan


@dataclass
class ConversationMessage:
    """A message in the idea conversation."""
    role: str  # "assistant" or "user"
    content: str
    stage: str
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "stage": self.stage,
            "timestamp": self.timestamp,
        }


@dataclass
class IdeaContext:
    """Extracted context from the conversation."""
    core_idea: str = ""
    problem: str = ""
    features: List[str] = field(default_factory=list)
    target_users: str = ""
    technical_preferences: str = ""
    constraints: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "core_idea": self.core_idea,
            "problem": self.problem,
            "features": self.features,
            "target_users": self.target_users,
            "technical_preferences": self.technical_preferences,
            "constraints": self.constraints,
        }

    def is_complete(self) -> bool:
        """Check if we have enough info to proceed."""
        return bool(self.core_idea and (self.problem or self.features))


# Question templates for each stage
STAGE_QUESTIONS = {
    ConversationStage.INITIAL: {
        "question": "What would you like to build? Describe your idea in a few sentences.",
        "placeholder": "e.g., A task management app for remote teams...",
        "help": "Don't worry about being perfect - we'll refine it together.",
    },
    ConversationStage.CLARIFY_GOAL: {
        "question": "What problem does this solve? Who has this problem?",
        "placeholder": "e.g., Teams struggle to track tasks across time zones...",
        "help": "Understanding the 'why' helps create a better solution.",
        "skip_allowed": True,
    },
    ConversationStage.FEATURES: {
        "question": "What are the must-have features? List the top 3-5.",
        "placeholder": "e.g., User login, task creation, notifications...",
        "help": "Focus on essential features first. We can add more later.",
        "skip_allowed": True,
    },
    ConversationStage.USERS: {
        "question": "Who will use this? Describe your target users.",
        "placeholder": "e.g., Small business owners, developers, students...",
        "help": "Knowing your users helps prioritize features.",
        "skip_allowed": True,
    },
    ConversationStage.TECHNICAL: {
        "question": "Any technical preferences? Languages, frameworks, or platforms?",
        "placeholder": "e.g., Python, React, mobile app, REST API...",
        "help": "Leave blank if you're flexible on technology choices.",
        "skip_allowed": True,
    },
    ConversationStage.CONSTRAINTS: {
        "question": "Any constraints? Timeline, budget, or limitations to consider?",
        "placeholder": "e.g., MVP in 2 weeks, must work offline...",
        "help": "Constraints help us scope the project appropriately.",
        "skip_allowed": True,
    },
    ConversationStage.SUMMARY: {
        "question": "Here's what I understood. Does this look right?",
        "help": "Review the summary and confirm or make corrections.",
        "is_summary": True,
    },
}


class IdeaConversation:
    """
    Manages an interactive conversation to formulate a project idea.

    Usage:
        conv = IdeaConversation()

        # Get initial question
        question = conv.get_current_question()

        # Process user response
        next_question = conv.process_response("I want to build a chat app")

        # Continue until complete
        while not conv.is_complete:
            question = conv.get_current_question()
            # ... get user input ...
            conv.process_response(user_input)

        # Get final context
        context = conv.get_context()
    """

    STAGE_ORDER = [
        ConversationStage.INITIAL,
        ConversationStage.CLARIFY_GOAL,
        ConversationStage.FEATURES,
        ConversationStage.USERS,
        ConversationStage.TECHNICAL,
        ConversationStage.CONSTRAINTS,
        ConversationStage.SUMMARY,
        ConversationStage.COMPLETE,
    ]

    def __init__(self, initial_idea: str = ""):
        self.messages: List[ConversationMessage] = []
        self.context = IdeaContext()
        self.current_stage = ConversationStage.INITIAL
        self._stage_index = 0

        # If we have an initial idea, process it
        if initial_idea and initial_idea.strip():
            self.context.core_idea = initial_idea.strip()
            # Record that the user provided the initial idea
            self.messages.append(ConversationMessage(
                role="user",
                content=initial_idea.strip(),
                stage=ConversationStage.INITIAL.value,
            ))
            self._advance_stage()
            # Add assistant's follow-up question
            next_q = self.get_current_question()
            self.messages.append(ConversationMessage(
                role="assistant",
                content=next_q.get("question", ""),
                stage=self.current_stage.value,
            ))

    @property
    def is_complete(self) -> bool:
        return self.current_stage == ConversationStage.COMPLETE

    def get_current_question(self) -> Dict[str, Any]:
        """Get the current question to ask the user."""
        if self.current_stage == ConversationStage.COMPLETE:
            return {
                "stage": "complete",
                "question": "Your idea is ready! Click 'Start Planning' to continue.",
                "complete": True,
            }

        stage_info = STAGE_QUESTIONS.get(self.current_stage, {})

        # For summary stage, generate the summary
        if stage_info.get("is_summary"):
            return {
                "stage": self.current_stage.value,
                "question": stage_info["question"],
                "summary": self._generate_summary(),
                "help": stage_info.get("help", ""),
                "is_summary": True,
                "can_skip": False,
            }

        return {
            "stage": self.current_stage.value,
            "question": stage_info.get("question", "Tell me more..."),
            "placeholder": stage_info.get("placeholder", ""),
            "help": stage_info.get("help", ""),
            "can_skip": stage_info.get("skip_allowed", False),
        }

    def process_response(self, response: str, skip: bool = False) -> Dict[str, Any]:
        """
        Process the user's response and advance the conversation.

        Returns the next question or completion status.
        """
        response = response.strip()

        # Record the user message
        self.messages.append(ConversationMessage(
            role="user",
            content=response if not skip else "[skipped]",
            stage=self.current_stage.value,
        ))

        # Extract information based on current stage
        if not skip and response:
            self._extract_info(response)

        # Handle summary confirmation
        if self.current_stage == ConversationStage.SUMMARY:
            if self._is_confirmation(response):
                self.current_stage = ConversationStage.COMPLETE
                return {"complete": True, "context": self.context.to_dict()}
            else:
                # User wants to make changes - could add edit flow here
                self.current_stage = ConversationStage.COMPLETE
                return {"complete": True, "context": self.context.to_dict()}

        # Advance to next stage
        self._advance_stage()

        # Record assistant's next question
        next_q = self.get_current_question()
        self.messages.append(ConversationMessage(
            role="assistant",
            content=next_q.get("question", ""),
            stage=self.current_stage.value,
        ))

        return next_q

    def _extract_info(self, response: str):
        """Extract relevant information from the response based on current stage."""
        if self.current_stage == ConversationStage.INITIAL:
            self.context.core_idea = response

        elif self.current_stage == ConversationStage.CLARIFY_GOAL:
            self.context.problem = response

        elif self.current_stage == ConversationStage.FEATURES:
            # Parse features from response (split by newlines, commas, or numbers)
            features = self._parse_features(response)
            self.context.features = features

        elif self.current_stage == ConversationStage.USERS:
            self.context.target_users = response

        elif self.current_stage == ConversationStage.TECHNICAL:
            self.context.technical_preferences = response

        elif self.current_stage == ConversationStage.CONSTRAINTS:
            self.context.constraints = response

    def _parse_features(self, text: str) -> List[str]:
        """Parse a list of features from freeform text."""
        features = []

        # Split by newlines first
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove common list prefixes
            line = re.sub(r'^[\-\*\•\d+\.]+\s*', '', line)

            # If line contains commas and is short, might be comma-separated
            if ',' in line and len(line) < 100:
                parts = [p.strip() for p in line.split(',')]
                features.extend([p for p in parts if p])
            else:
                if line:
                    features.append(line)

        # Deduplicate while preserving order
        seen = set()
        unique_features = []
        for f in features:
            if f.lower() not in seen:
                seen.add(f.lower())
                unique_features.append(f)

        return unique_features[:10]  # Limit to 10 features

    def _advance_stage(self):
        """Move to the next conversation stage."""
        self._stage_index += 1
        if self._stage_index < len(self.STAGE_ORDER):
            self.current_stage = self.STAGE_ORDER[self._stage_index]
        else:
            self.current_stage = ConversationStage.COMPLETE

    def _generate_summary(self) -> str:
        """Generate a summary of the collected information."""
        parts = []

        parts.append(f"**Project Idea:** {self.context.core_idea}")

        if self.context.problem:
            parts.append(f"**Problem:** {self.context.problem}")

        if self.context.features:
            features_str = "\n".join(f"  - {f}" for f in self.context.features)
            parts.append(f"**Features:**\n{features_str}")

        if self.context.target_users:
            parts.append(f"**Target Users:** {self.context.target_users}")

        if self.context.technical_preferences:
            parts.append(f"**Technical:** {self.context.technical_preferences}")

        if self.context.constraints:
            parts.append(f"**Constraints:** {self.context.constraints}")

        return "\n\n".join(parts)

    def _is_confirmation(self, response: str) -> bool:
        """Check if the response is a confirmation."""
        response_lower = response.lower()
        confirmations = ["yes", "yeah", "yep", "correct", "looks good", "lgtm",
                        "confirm", "ok", "okay", "sure", "right", "good", "perfect"]
        return any(c in response_lower for c in confirmations)

    def get_context(self) -> IdeaContext:
        """Get the extracted context."""
        return self.context

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all conversation messages."""
        return [m.to_dict() for m in self.messages]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize conversation state."""
        return {
            "stage": self.current_stage.value,
            "stage_index": self._stage_index,
            "messages": self.get_messages(),
            "context": self.context.to_dict(),
            "is_complete": self.is_complete,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IdeaConversation":
        """Deserialize conversation state."""
        conv = cls()
        conv._stage_index = data.get("stage_index", 0)
        conv.current_stage = ConversationStage(data.get("stage", "initial"))

        # Restore context
        ctx_data = data.get("context", {})
        conv.context = IdeaContext(
            core_idea=ctx_data.get("core_idea", ""),
            problem=ctx_data.get("problem", ""),
            features=ctx_data.get("features", []),
            target_users=ctx_data.get("target_users", ""),
            technical_preferences=ctx_data.get("technical_preferences", ""),
            constraints=ctx_data.get("constraints", ""),
        )

        # Restore messages
        for msg_data in data.get("messages", []):
            conv.messages.append(ConversationMessage(
                role=msg_data.get("role", "user"),
                content=msg_data.get("content", ""),
                stage=msg_data.get("stage", "initial"),
                timestamp=msg_data.get("timestamp", ""),
            ))

        return conv


def get_quick_questions() -> List[Dict[str, str]]:
    """Get quick-start questions for the idea phase."""
    return [
        {
            "question": "What type of project?",
            "options": ["Web App", "CLI Tool", "API", "Mobile App", "Script", "Other"]
        },
        {
            "question": "Primary language?",
            "options": ["Python", "JavaScript", "TypeScript", "Go", "Rust", "Other"]
        },
        {
            "question": "Complexity?",
            "options": ["Simple (hours)", "Medium (days)", "Complex (weeks)"]
        },
    ]
