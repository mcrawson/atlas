"""
General Mode Handler for overnight tasks.

Handles non-ATLAS tasks like research, drafts, and reviews using
lightweight role-based processing with optional QC passes.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from atlas.operator.config import OvernightConfig

logger = logging.getLogger(__name__)


@dataclass
class RoleConfig:
    """Configuration for a processing role."""
    system_prompt: str
    qc_role: Optional[str] = None  # Role to QC the output
    temperature: float = 0.7
    max_tokens: int = 4000


# Role definitions
ROLES: dict[str, RoleConfig] = {
    "researcher": RoleConfig(
        system_prompt="""You are a thorough research analyst. Your job is to:
- Find accurate, relevant information
- Cite sources when possible
- Distinguish between facts and opinions
- Be comprehensive but focused on the query
- Note when information may be outdated or uncertain

Format your response with clear sections and bullet points for readability.""",
        qc_role="factchecker",
        temperature=0.5,
        max_tokens=6000,
    ),
    "writer": RoleConfig(
        system_prompt="""You are a professional writer. Your job is to:
- Write clear, engaging content
- Match the appropriate tone for the context
- Use proper structure and formatting
- Be concise while being complete
- Create content that serves the reader's needs

Produce polished, ready-to-use content.""",
        qc_role="editor",
        temperature=0.8,
        max_tokens=4000,
    ),
    "editor": RoleConfig(
        system_prompt="""You are a professional editor. Your job is to:
- Check for clarity and flow
- Fix grammar and spelling issues
- Improve word choice and sentence structure
- Ensure consistent tone
- Verify logical organization

Provide edited content with tracked changes or explanations of major edits.""",
        qc_role=None,  # No further QC needed
        temperature=0.4,
        max_tokens=4000,
    ),
    "reviewer": RoleConfig(
        system_prompt="""You are a thorough reviewer. Your job is to:
- Identify issues, bugs, or problems
- Suggest specific improvements
- Highlight what works well
- Be constructive and actionable
- Prioritize feedback by importance

Provide structured feedback with clear categories.""",
        qc_role=None,
        temperature=0.5,
        max_tokens=3000,
    ),
    "factchecker": RoleConfig(
        system_prompt="""You are a rigorous fact-checker. Your job is to:
- Verify claims and statements
- Check sources for reliability
- Flag unverified or questionable claims
- Note when claims cannot be verified
- Correct factual errors

Be thorough but focus on significant claims, not trivial details.""",
        qc_role=None,
        temperature=0.3,
        max_tokens=3000,
    ),
    "analyst": RoleConfig(
        system_prompt="""You are a data analyst. Your job is to:
- Analyze information for patterns and insights
- Compare and contrast options
- Draw meaningful conclusions
- Quantify when possible
- Present findings clearly

Use structured analysis with clear reasoning.""",
        qc_role="reviewer",
        temperature=0.5,
        max_tokens=4000,
    ),
}


@dataclass
class GeneralResult:
    """Result from general mode processing."""
    content: str
    role_used: str
    qc_role_used: Optional[str]
    qc_feedback: Optional[str]
    iterations: int
    timestamp: datetime
    model_used: str


class GeneralMode:
    """
    Handles general tasks (research, drafts, reviews) using role-based processing.

    Features:
    - Role selection based on task content
    - Optional QC pass with appropriate reviewer role
    - Clean, structured output
    """

    def __init__(self, config: OvernightConfig, provider=None):
        self.config = config
        self._provider = provider
        self._claude_provider = None

    async def _get_provider(self):
        """Lazy-load the Claude provider."""
        if self._provider:
            return self._provider
        if self._claude_provider is None:
            from atlas.routing.providers.claude import ClaudeProvider
            self._claude_provider = ClaudeProvider()
        return self._claude_provider

    async def execute(
        self,
        task: dict,
        role: Optional[str] = None,
    ) -> GeneralResult:
        """
        Execute a general task with the appropriate role.

        Args:
            task: Task dict with 'prompt' and optional metadata
            role: Override role selection (default: auto-select)

        Returns:
            GeneralResult with content and metadata
        """
        prompt = task.get("prompt", "")
        metadata = task.get("metadata", {}) or {}

        # Select role
        if role is None:
            role = metadata.get("role") or self._select_role(prompt)

        if role not in ROLES:
            role = "researcher"  # Fallback

        role_config = ROLES[role]
        logger.info(f"Processing task with role: {role}")

        # Primary execution
        provider = await self._get_provider()
        result = await provider.generate(
            prompt=prompt,
            system_prompt=role_config.system_prompt,
            max_tokens=role_config.max_tokens,
            temperature=role_config.temperature,
        )

        qc_role_used = None
        qc_feedback = None
        iterations = 1

        # QC pass if role has one
        if role_config.qc_role and role_config.qc_role in ROLES:
            qc_role = role_config.qc_role
            qc_config = ROLES[qc_role]
            qc_role_used = qc_role

            qc_prompt = f"""Review the following content that was produced in response to this request:

ORIGINAL REQUEST:
{prompt}

CONTENT TO REVIEW:
{result}

Provide your {qc_role} feedback. If there are issues, be specific about what needs to change."""

            qc_feedback = await provider.generate(
                prompt=qc_prompt,
                system_prompt=qc_config.system_prompt,
                max_tokens=qc_config.max_tokens,
                temperature=qc_config.temperature,
            )
            iterations = 2

            # Check if significant issues were found
            issues_found = self._check_for_issues(qc_feedback)

            if issues_found:
                # Revise based on feedback
                revision_prompt = f"""Original request: {prompt}

Your previous response:
{result}

{qc_role.title()} feedback:
{qc_feedback}

Please revise your response to address the feedback. Produce an improved version."""

                result = await provider.generate(
                    prompt=revision_prompt,
                    system_prompt=role_config.system_prompt,
                    max_tokens=role_config.max_tokens,
                    temperature=role_config.temperature,
                )
                iterations = 3

        return GeneralResult(
            content=result,
            role_used=role,
            qc_role_used=qc_role_used,
            qc_feedback=qc_feedback,
            iterations=iterations,
            timestamp=datetime.now(),
            model_used="claude",
        )

    def _select_role(self, prompt: str) -> str:
        """Select the best role based on prompt content."""
        prompt_lower = prompt.lower()

        # Role keywords
        role_keywords = {
            "researcher": ["research", "find", "explore", "investigate", "sources", "information", "what is", "how does"],
            "writer": ["write", "draft", "compose", "create content", "blog", "article", "email", "letter"],
            "editor": ["edit", "proofread", "review writing", "grammar", "tone", "revise"],
            "reviewer": ["review", "code review", "feedback", "critique", "evaluate"],
            "factchecker": ["verify", "fact-check", "validate", "confirm", "accurate", "true"],
            "analyst": ["analyze", "data", "trends", "insights", "compare", "metrics", "statistics"],
        }

        best_role = "researcher"  # Default
        best_score = 0

        for role, keywords in role_keywords.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > best_score:
                best_score = score
                best_role = role

        return best_role

    def _check_for_issues(self, qc_feedback: str) -> bool:
        """Check if QC feedback indicates significant issues."""
        feedback_lower = qc_feedback.lower()

        # Positive indicators (no issues)
        positive = ["looks good", "no issues", "well done", "accurate", "correct", "solid"]
        if any(p in feedback_lower for p in positive):
            return False

        # Issue indicators
        issue_markers = [
            "incorrect", "error", "wrong", "inaccurate", "misleading",
            "missing", "needs", "should", "must", "unclear", "confusing",
            "issue", "problem", "concern", "fix", "revise",
        ]

        issue_count = sum(1 for marker in issue_markers if marker in feedback_lower)
        return issue_count >= 2

    async def save_result(
        self,
        result: GeneralResult,
        task: dict,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Save the result to a file."""
        if output_dir is None:
            output_dir = self.config.general.output_dir

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = result.timestamp.strftime("%Y%m%d-%H%M%S")
        role = result.role_used
        prompt_slug = task.get("prompt", "task")[:30].replace(" ", "-").lower()
        prompt_slug = "".join(c for c in prompt_slug if c.isalnum() or c == "-")

        filename = f"{timestamp}-{role}-{prompt_slug}.md"
        filepath = output_dir / filename

        # Build content
        content = f"""# Overnight Task Result

**Role:** {result.role_used}
**Timestamp:** {result.timestamp.isoformat()}
**Iterations:** {result.iterations}
**QC Role:** {result.qc_role_used or 'None'}

## Original Request

{task.get('prompt', 'No prompt')}

## Result

{result.content}
"""

        if result.qc_feedback:
            content += f"""
## QC Feedback ({result.qc_role_used})

{result.qc_feedback}
"""

        filepath.write_text(content)
        logger.info(f"Saved result to: {filepath}")
        return filepath
