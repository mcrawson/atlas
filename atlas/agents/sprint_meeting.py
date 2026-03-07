"""Sprint Meeting - Multi-agent plan review and discussion.

Before building begins, agents gather to review Sketch's plan from their
unique perspectives. This catches issues early and improves plan quality.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

from .base import AgentOutput, AgentStatus

logger = logging.getLogger("atlas.agents.sprint_meeting")


class ReviewVerdict(Enum):
    """Agent's verdict on the plan."""
    APPROVED = "approved"          # Looks good, ready to build
    CONCERNS = "concerns"          # Has concerns but can proceed
    NEEDS_REVISION = "needs_revision"  # Plan needs changes before building
    BLOCKED = "blocked"            # Cannot proceed without resolution


@dataclass
class AgentReview:
    """Review from a single agent."""
    agent_name: str
    agent_icon: str
    verdict: ReviewVerdict
    summary: str
    concerns: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    tokens_used: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "agent_icon": self.agent_icon,
            "verdict": self.verdict.value,
            "summary": self.summary,
            "concerns": self.concerns,
            "questions": self.questions,
            "suggestions": self.suggestions,
            "tokens_used": self.tokens_used,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentReview":
        return cls(
            agent_name=data["agent_name"],
            agent_icon=data["agent_icon"],
            verdict=ReviewVerdict(data["verdict"]),
            summary=data["summary"],
            concerns=data.get("concerns", []),
            questions=data.get("questions", []),
            suggestions=data.get("suggestions", []),
            tokens_used=data.get("tokens_used", 0),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
        )


@dataclass
class SprintMeetingResult:
    """Result of a sprint meeting."""
    reviews: list[AgentReview]
    overall_verdict: ReviewVerdict
    summary: str
    can_proceed: bool
    total_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "reviews": [r.to_dict() for r in self.reviews],
            "overall_verdict": self.overall_verdict.value,
            "summary": self.summary,
            "can_proceed": self.can_proceed,
            "total_tokens": self.total_tokens,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SprintMeetingResult":
        return cls(
            reviews=[AgentReview.from_dict(r) for r in data.get("reviews", [])],
            overall_verdict=ReviewVerdict(data["overall_verdict"]),
            summary=data["summary"],
            can_proceed=data["can_proceed"],
            total_tokens=data.get("total_tokens", 0),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
        )


# Review prompts for each agent
REVIEW_PROMPTS = {
    "tinker": """You are Tinker, the implementation specialist. Review this plan from a builder's perspective.

PLAN TO REVIEW:
{plan}

PROJECT CONTEXT:
{context}

Analyze the plan and provide your review:

1. **Implementation Feasibility**: Can this actually be built as specified?
2. **Technical Concerns**: Any architectural issues, missing dependencies, or unclear requirements?
3. **Effort Estimate**: Is the scope realistic? Any parts that might take longer than expected?
4. **Questions**: What do you need clarified before building?
5. **Suggestions**: How could this plan be improved?

Format your response as:
## Summary
[1-2 sentence overall assessment]

## Verdict
[APPROVED / CONCERNS / NEEDS_REVISION / BLOCKED]

## Concerns
- [List any concerns]

## Questions
- [List any questions for Sketch]

## Suggestions
- [List any improvements]""",

    "oracle": """You are Oracle, the quality verification specialist. Review this plan from a testing perspective.

PLAN TO REVIEW:
{plan}

PROJECT CONTEXT:
{context}

Analyze the plan and provide your review:

1. **Testability**: Can this be properly verified? Are success criteria clear?
2. **Quality Risks**: What could go wrong? Edge cases to consider?
3. **Verification Strategy**: How will you test each component?
4. **Missing Requirements**: Any gaps in the specification?
5. **Suggestions**: How could this plan be more testable?

Format your response as:
## Summary
[1-2 sentence overall assessment]

## Verdict
[APPROVED / CONCERNS / NEEDS_REVISION / BLOCKED]

## Concerns
- [List any concerns]

## Questions
- [List any questions for Sketch]

## Suggestions
- [List any improvements]""",

    "launch": """You are Launch, the deployment specialist. Review this plan from a deployment perspective.

PLAN TO REVIEW:
{plan}

PROJECT CONTEXT:
{context}

Analyze the plan and provide your review:

1. **Deployment Path**: Is there a clear path to production/release?
2. **Platform Requirements**: Any accounts, certificates, or setup needed?
3. **Blockers**: Anything that could prevent deployment?
4. **Timeline Concerns**: Any platform review times or processes to consider?
5. **Suggestions**: What should be added to make deployment smoother?

Format your response as:
## Summary
[1-2 sentence overall assessment]

## Verdict
[APPROVED / CONCERNS / NEEDS_REVISION / BLOCKED]

## Concerns
- [List any concerns]

## Questions
- [List any questions for Sketch]

## Suggestions
- [List any improvements]""",
}


class SprintMeeting:
    """Orchestrates a sprint meeting where agents review a plan."""

    def __init__(self, agent_manager):
        """Initialize with agent manager.

        Args:
            agent_manager: The AgentManager with access to all agents
        """
        self.agent_manager = agent_manager

    async def conduct_meeting(
        self,
        plan: str,
        context: Optional[dict] = None,
        include_agents: list[str] = None,
    ) -> SprintMeetingResult:
        """Conduct a sprint meeting to review a plan.

        Args:
            plan: The plan content from Sketch
            context: Project context
            include_agents: Which agents to include (default: all)

        Returns:
            SprintMeetingResult with all reviews
        """
        if include_agents is None:
            include_agents = ["tinker", "oracle", "launch"]

        context = context or {}
        context_str = self._format_context(context)

        # Run reviews in parallel for speed
        review_tasks = []
        for agent_name in include_agents:
            if agent_name in REVIEW_PROMPTS:
                review_tasks.append(
                    self._get_agent_review(agent_name, plan, context_str)
                )

        reviews = await asyncio.gather(*review_tasks, return_exceptions=True)

        # Filter out exceptions and collect valid reviews
        valid_reviews = []
        for review in reviews:
            if isinstance(review, AgentReview):
                valid_reviews.append(review)
            elif isinstance(review, Exception):
                logger.error(f"Review failed: {review}")

        # Determine overall verdict
        overall_verdict, can_proceed = self._determine_overall_verdict(valid_reviews)
        summary = self._generate_summary(valid_reviews, overall_verdict)
        total_tokens = sum(r.tokens_used for r in valid_reviews)

        return SprintMeetingResult(
            reviews=valid_reviews,
            overall_verdict=overall_verdict,
            summary=summary,
            can_proceed=can_proceed,
            total_tokens=total_tokens,
        )

    async def _get_agent_review(
        self,
        agent_name: str,
        plan: str,
        context_str: str,
    ) -> AgentReview:
        """Get a review from a specific agent.

        Args:
            agent_name: Name of the agent
            plan: The plan to review
            context_str: Formatted context string

        Returns:
            AgentReview from the agent
        """
        prompt = REVIEW_PROMPTS[agent_name].format(plan=plan, context=context_str)

        # Get the agent
        agent = getattr(self.agent_manager, agent_name, None)
        if agent_name == "tinker":
            agent = self.agent_manager.mason
        elif agent_name == "launch":
            agent = self.agent_manager.launch

        if not agent:
            return AgentReview(
                agent_name=agent_name,
                agent_icon=self._get_agent_icon(agent_name),
                verdict=ReviewVerdict.APPROVED,
                summary="Agent not available for review",
            )

        try:
            # Use the agent's provider to generate review
            response, token_info = await agent._generate_with_provider(
                prompt,
                temperature=0.5,
            )

            # Parse the response
            return self._parse_review(agent_name, response, token_info)

        except Exception as e:
            logger.error(f"Error getting review from {agent_name}: {e}")
            return AgentReview(
                agent_name=agent_name,
                agent_icon=self._get_agent_icon(agent_name),
                verdict=ReviewVerdict.CONCERNS,
                summary=f"Review failed: {str(e)[:100]}",
                concerns=[f"Could not complete review: {str(e)}"],
            )

    def _parse_review(
        self,
        agent_name: str,
        response: str,
        token_info: dict,
    ) -> AgentReview:
        """Parse an agent's review response.

        Args:
            agent_name: Name of the agent
            response: Raw response text
            token_info: Token usage info

        Returns:
            Parsed AgentReview
        """
        # Extract verdict
        verdict = ReviewVerdict.CONCERNS  # Default
        response_upper = response.upper()
        if "## VERDICT" in response_upper:
            verdict_section = response.split("## Verdict")[1].split("##")[0] if "## Verdict" in response else ""
            if "APPROVED" in verdict_section.upper():
                verdict = ReviewVerdict.APPROVED
            elif "BLOCKED" in verdict_section.upper():
                verdict = ReviewVerdict.BLOCKED
            elif "NEEDS_REVISION" in verdict_section.upper() or "NEEDS REVISION" in verdict_section.upper():
                verdict = ReviewVerdict.NEEDS_REVISION
            elif "CONCERNS" in verdict_section.upper():
                verdict = ReviewVerdict.CONCERNS

        # Extract summary
        summary = ""
        if "## Summary" in response:
            summary = response.split("## Summary")[1].split("##")[0].strip()
        else:
            # Use first paragraph as summary
            summary = response.split("\n\n")[0][:200]

        # Extract concerns
        concerns = self._extract_list_section(response, "## Concerns")

        # Extract questions
        questions = self._extract_list_section(response, "## Questions")

        # Extract suggestions
        suggestions = self._extract_list_section(response, "## Suggestions")

        return AgentReview(
            agent_name=agent_name,
            agent_icon=self._get_agent_icon(agent_name),
            verdict=verdict,
            summary=summary,
            concerns=concerns,
            questions=questions,
            suggestions=suggestions,
            tokens_used=token_info.get("total_tokens", 0),
        )

    def _extract_list_section(self, text: str, section_header: str) -> list[str]:
        """Extract bullet points from a section."""
        items = []
        if section_header in text:
            section = text.split(section_header)[1].split("##")[0]
            for line in section.strip().split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    item = line[2:].strip()
                    if item and item.lower() not in ["none", "n/a", "no concerns", "no questions", "no suggestions"]:
                        items.append(item)
        return items

    def _get_agent_icon(self, agent_name: str) -> str:
        """Get the icon for an agent."""
        icons = {
            "sketch": "💡",
            "tinker": "🛠️",
            "oracle": "🔮",
            "launch": "📤",
            "buzz": "📡",
            "hype": "🎉",
            "sentry": "🛡️",
            "tally": "💰",
            "cortex": "🧠",
        }
        return icons.get(agent_name, "🤖")

    def _format_context(self, context: dict) -> str:
        """Format context dict as readable string."""
        parts = []
        if context.get("description"):
            parts.append(f"Description: {context['description']}")
        if context.get("problem"):
            parts.append(f"Problem: {context['problem']}")
        if context.get("features"):
            features = context["features"]
            if isinstance(features, list):
                parts.append(f"Features: {', '.join(features)}")
            else:
                parts.append(f"Features: {features}")
        if context.get("technical"):
            parts.append(f"Technical: {context['technical']}")
        return "\n".join(parts) if parts else "No additional context"

    def _determine_overall_verdict(
        self,
        reviews: list[AgentReview],
    ) -> tuple[ReviewVerdict, bool]:
        """Determine overall verdict from all reviews.

        Returns:
            Tuple of (overall_verdict, can_proceed)
        """
        if not reviews:
            return ReviewVerdict.APPROVED, True

        # If any agent is blocked, we're blocked
        if any(r.verdict == ReviewVerdict.BLOCKED for r in reviews):
            return ReviewVerdict.BLOCKED, False

        # If any agent needs revision, we need revision
        if any(r.verdict == ReviewVerdict.NEEDS_REVISION for r in reviews):
            return ReviewVerdict.NEEDS_REVISION, False

        # If any agent has concerns, we have concerns but can proceed
        if any(r.verdict == ReviewVerdict.CONCERNS for r in reviews):
            return ReviewVerdict.CONCERNS, True

        # All approved
        return ReviewVerdict.APPROVED, True

    def _generate_summary(
        self,
        reviews: list[AgentReview],
        overall_verdict: ReviewVerdict,
    ) -> str:
        """Generate a summary of the meeting."""
        if not reviews:
            return "No reviews collected."

        agent_verdicts = ", ".join(
            f"{r.agent_icon} {r.agent_name.title()}: {r.verdict.value}"
            for r in reviews
        )

        all_concerns = []
        for r in reviews:
            all_concerns.extend(r.concerns)

        if overall_verdict == ReviewVerdict.APPROVED:
            return f"All agents approve the plan. {agent_verdicts}"
        elif overall_verdict == ReviewVerdict.CONCERNS:
            return f"Plan approved with concerns. {agent_verdicts}. Key concerns: {'; '.join(all_concerns[:3])}"
        elif overall_verdict == ReviewVerdict.NEEDS_REVISION:
            return f"Plan needs revision before proceeding. {agent_verdicts}"
        else:
            return f"Plan is blocked. {agent_verdicts}. Must resolve: {'; '.join(all_concerns[:3])}"


def get_sprint_meeting(agent_manager) -> SprintMeeting:
    """Create a sprint meeting orchestrator."""
    return SprintMeeting(agent_manager)
