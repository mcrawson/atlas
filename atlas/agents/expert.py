"""Custom Expert Agent - Dynamically spawned domain expert for ATLAS projects.

The Custom Expert is created at Round Table kickoff based on the Business Brief.
It becomes the domain expert AND builder for the specific project.

Unlike generic builders, the Custom Expert:
- Knows the specific product being built
- Understands the target customer
- Has context from the Brief
- Evolves during the project
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from atlas.agents.base import BaseAgent, AgentStatus, AgentOutput
from atlas.agents.roundtable import MessageType, get_roundtable

logger = logging.getLogger("atlas.agents.expert")


@dataclass
class ExpertOutput:
    """Output from the Custom Expert."""
    content: str                      # The actual content/code/design
    output_type: str                  # html, css, markdown, code, etc.
    files: list[dict] = field(default_factory=list)  # Generated files
    notes: str = ""                   # Expert's notes about the work
    questions: list[str] = field(default_factory=list)  # Questions for team
    confidence: float = 0.9           # How confident in this output

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "output_type": self.output_type,
            "files": self.files,
            "notes": self.notes,
            "questions": self.questions,
            "confidence": self.confidence,
        }


class CustomExpert(BaseAgent):
    """Custom Expert agent - domain expert spawned for a specific project.

    Created at Round Table kickoff with a system prompt built from the Brief.
    Handles building the actual product with domain expertise.
    """

    # These get overridden per-instance
    name = "expert"
    description = "Custom domain expert"
    icon = "🧠"
    color = "#9C27B0"

    def __init__(
        self,
        router=None,
        memory=None,
        project_id: int = None,
        expert_config: dict = None,
        **kwargs
    ):
        """Initialize the Custom Expert.

        Args:
            router: ATLAS Router
            memory: Memory manager
            project_id: The project this expert is for
            expert_config: Config from Round Table (name, system_prompt, etc.)
        """
        super().__init__(router=router, memory=memory, **kwargs)

        self.project_id = project_id
        self.expert_config = expert_config or {}

        # Override identity from config
        if expert_config:
            self.name = expert_config.get("id", "expert")
            self.description = expert_config.get("expertise", "Custom domain expert")
            self._system_prompt = expert_config.get("system_prompt", "")
            self._expert_name = expert_config.get("name", "Expert")
        else:
            self._system_prompt = ""
            self._expert_name = "Expert"

        # Track what this expert has learned/built
        self._context_history: list[str] = []
        self._decisions_made: list[dict] = []

    def get_system_prompt(self) -> str:
        """Get the expert's system prompt (built from Brief)."""
        if self._system_prompt:
            return self._system_prompt

        # Fallback generic prompt
        return """You are a Custom Expert for an ATLAS project.
You are a domain expert who builds high-quality, sellable products.
Follow the Business Brief and coordinate with the team."""

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Process a task (build something).

        Args:
            task: What to build/do
            context: Additional context (Brief, conversation, etc.)
            previous_output: Output from previous step

        Returns:
            AgentOutput with the built content
        """
        self.status = AgentStatus.THINKING
        self._current_task = f"Building: {task[:50]}..."

        try:
            # Build the prompt
            prompt = self._build_prompt(task, context, previous_output)

            self.status = AgentStatus.WORKING
            logger.info(f"[{self._expert_name}] Working on: {task[:100]}")

            # Generate the output
            response, token_info = await self._generate_with_provider(
                prompt,
                system_prompt=self.get_system_prompt(),
                temperature=0.4,  # Balance creativity with consistency
            )

            # Parse the output
            expert_output = self._parse_output(response, task)

            # Log to conversation
            self._log_to_conversation(task, expert_output)

            # Store in context history
            self._context_history.append(f"Task: {task}\nOutput: {expert_output.notes}")

            self.status = AgentStatus.COMPLETED

            return AgentOutput(
                content=expert_output.content,
                artifacts={
                    "output": expert_output.to_dict(),
                    "expert_name": self._expert_name,
                    "output_type": expert_output.output_type,
                    "files": expert_output.files,
                },
                reasoning=expert_output.notes,
                tokens_used=token_info.get("total_tokens", 0),
                metadata={
                    "agent": self.name,
                    "expert_name": self._expert_name,
                    "confidence": expert_output.confidence,
                },
            )

        except Exception as e:
            logger.error(f"[{self._expert_name}] Error: {e}")
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Error: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )

    def _build_prompt(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> str:
        """Build the prompt for the task."""
        prompt_parts = [
            "## Task",
            task,
            "",
        ]

        # Add context
        if context:
            if context.get("brief"):
                brief = context["brief"]
                prompt_parts.extend([
                    "## Business Brief Reference",
                    f"Product: {brief.get('product_name')}",
                    f"Type: {brief.get('product_type')}",
                    f"Target: {brief.get('target_customer', {}).get('demographics', 'Unknown')}",
                    "",
                ])

            if context.get("conversation"):
                prompt_parts.extend([
                    "## Recent Team Conversation",
                    context["conversation"][:1500],  # Limit length
                    "",
                ])

            if context.get("plan"):
                prompt_parts.extend([
                    "## Build Plan",
                    str(context["plan"])[:1000],
                    "",
                ])

        # Add previous output
        if previous_output:
            prompt_parts.extend([
                "## Previous Step Output",
                previous_output.content[:1000],
                "",
            ])

        # Add context history
        if self._context_history:
            recent_history = self._context_history[-3:]  # Last 3 tasks
            prompt_parts.extend([
                "## What I've Done So Far",
                "\n".join(recent_history),
                "",
            ])

        # Add instructions
        prompt_parts.extend([
            "## Instructions",
            "Create the requested output. Be thorough and professional.",
            "The output must be SELLABLE - something a customer would pay for.",
            "",
            "Structure your response as:",
            "1. First, any notes or considerations",
            "2. Then the actual content/code",
            "3. Finally, any questions for the team",
            "",
            "If creating code/HTML, wrap it in appropriate code blocks.",
        ])

        return "\n".join(prompt_parts)

    def _parse_output(self, response: str, task: str) -> ExpertOutput:
        """Parse the LLM response into ExpertOutput."""
        # Extract code blocks
        code_blocks = re.findall(r'```(\w+)?\n(.*?)```', response, re.DOTALL)

        files = []
        main_content = response
        output_type = "text"

        if code_blocks:
            # Determine primary output type
            for lang, content in code_blocks:
                lang = lang or "text"
                if lang in ["html", "css", "javascript", "js"]:
                    output_type = "html"
                    files.append({
                        "type": lang,
                        "content": content.strip(),
                    })
                elif lang in ["python", "typescript", "json"]:
                    output_type = "code"
                    files.append({
                        "type": lang,
                        "content": content.strip(),
                    })
                elif lang == "markdown" or lang == "md":
                    output_type = "markdown"
                    files.append({
                        "type": "markdown",
                        "content": content.strip(),
                    })

            # Use the largest code block as main content
            if files:
                main_content = max(files, key=lambda f: len(f["content"]))["content"]

        # Extract notes (text before code blocks)
        notes_match = re.match(r'^(.*?)```', response, re.DOTALL)
        notes = notes_match.group(1).strip() if notes_match else ""

        # Extract questions
        questions = []
        question_patterns = [
            r'\*\*Question[s]?\*\*:?\s*(.*?)(?=\n\n|\Z)',
            r'Question[s]? for (?:the )?team:?\s*(.*?)(?=\n\n|\Z)',
        ]
        for pattern in question_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Split by bullet points or newlines
                for q in re.split(r'[-•]\s*|\n', match):
                    q = q.strip()
                    if q and len(q) > 10:
                        questions.append(q)

        return ExpertOutput(
            content=main_content,
            output_type=output_type,
            files=files,
            notes=notes[:500] if notes else f"Completed: {task[:100]}",
            questions=questions[:3],  # Max 3 questions
            confidence=0.85,
        )

    def _log_to_conversation(self, task: str, output: ExpertOutput):
        """Log activity to the Round Table conversation."""
        if not self.project_id:
            return

        roundtable = get_roundtable()

        # Log completion
        roundtable.add_message(
            project_id=self.project_id,
            sender=self.name,
            message_type=MessageType.UPDATE,
            content=f"Completed: {task[:100]}. {output.notes[:200]}",
        )

        # Log any questions
        for question in output.questions:
            roundtable.add_message(
                project_id=self.project_id,
                sender=self.name,
                message_type=MessageType.QUESTION,
                content=question,
            )

    def record_decision(self, decision: str, reasoning: str):
        """Record a decision made by this expert."""
        self._decisions_made.append({
            "decision": decision,
            "reasoning": reasoning,
            "timestamp": datetime.now().isoformat(),
        })

        # Log to conversation
        if self.project_id:
            roundtable = get_roundtable()
            roundtable.add_message(
                project_id=self.project_id,
                sender=self.name,
                message_type=MessageType.DECISION,
                content=f"**Decision:** {decision}\n**Reasoning:** {reasoning}",
            )

    def raise_concern(self, concern: str):
        """Raise a concern to the team."""
        if self.project_id:
            roundtable = get_roundtable()
            roundtable.add_message(
                project_id=self.project_id,
                sender=self.name,
                message_type=MessageType.CONCERN,
                content=concern,
            )

    async def ask_question(self, question: str, to_agent: Optional[str] = None):
        """Ask a question to the team or specific agent."""
        if self.project_id:
            roundtable = get_roundtable()
            roundtable.add_message(
                project_id=self.project_id,
                sender=self.name,
                message_type=MessageType.QUESTION,
                content=question,
                recipient=to_agent,
            )

    def handoff_to(self, agent: str, summary: str):
        """Hand off work to another agent."""
        if self.project_id:
            roundtable = get_roundtable()
            roundtable.add_message(
                project_id=self.project_id,
                sender=self.name,
                message_type=MessageType.HANDOFF,
                content=summary,
                recipient=agent,
            )

    def get_context_summary(self) -> str:
        """Get a summary of what this expert has learned/done."""
        summary_parts = [
            f"## {self._expert_name} Context",
            "",
            f"**Expertise:** {self.description}",
            "",
        ]

        if self._decisions_made:
            summary_parts.append("**Decisions Made:**")
            for d in self._decisions_made[-5:]:
                summary_parts.append(f"- {d['decision']}")
            summary_parts.append("")

        if self._context_history:
            summary_parts.append("**Recent Work:**")
            for h in self._context_history[-3:]:
                summary_parts.append(f"- {h[:100]}...")
            summary_parts.append("")

        return "\n".join(summary_parts)


def create_expert_for_project(
    project_id: int,
    router=None,
    memory=None,
    providers=None,
) -> Optional[CustomExpert]:
    """Create a Custom Expert for a project using Round Table config.

    Args:
        project_id: The project ID
        router: ATLAS Router
        memory: Memory manager
        providers: LLM providers

    Returns:
        CustomExpert instance or None if no session exists
    """
    roundtable = get_roundtable(router=router, memory=memory, providers=providers)
    session = roundtable.get_session(project_id)

    if not session or not session.custom_expert:
        logger.warning(f"No Round Table session or expert for project {project_id}")
        return None

    return CustomExpert(
        router=router,
        memory=memory,
        project_id=project_id,
        expert_config=session.custom_expert,
        providers=providers,
    )
