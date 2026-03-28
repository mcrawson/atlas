"""Planner Agent - Creates build plans from Business Briefs.

The Planner creates detailed, actionable build plans based on the Brief.
Works with the Custom Expert to ensure plans are feasible.

Part of the Round Table coordination system.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from atlas.agents.base import BaseAgent, AgentStatus, AgentOutput
from atlas.agents.roundtable import MessageType, get_roundtable

logger = logging.getLogger("atlas.agents.planner")


@dataclass
class BuildPhase:
    """A phase in the build plan."""
    name: str
    description: str
    deliverables: list[str]
    estimated_time: str = ""
    dependencies: list[str] = field(default_factory=list)
    qc_checkpoint: bool = False  # Whether QC should check after this phase

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "deliverables": self.deliverables,
            "estimated_time": self.estimated_time,
            "dependencies": self.dependencies,
            "qc_checkpoint": self.qc_checkpoint,
        }


@dataclass
class BuildPlan:
    """A complete build plan for a project."""
    project_name: str
    product_type: str
    summary: str
    phases: list[BuildPhase]
    total_estimated_time: str = ""
    success_criteria: list[str] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    tools_needed: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "product_type": self.product_type,
            "summary": self.summary,
            "phases": [p.to_dict() for p in self.phases],
            "total_estimated_time": self.total_estimated_time,
            "success_criteria": self.success_criteria,
            "risks": self.risks,
            "tools_needed": self.tools_needed,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BuildPlan":
        phases = [
            BuildPhase(
                name=p["name"],
                description=p["description"],
                deliverables=p.get("deliverables", []),
                estimated_time=p.get("estimated_time", ""),
                dependencies=p.get("dependencies", []),
                qc_checkpoint=p.get("qc_checkpoint", False),
            )
            for p in data.get("phases", [])
        ]
        return cls(
            project_name=data.get("project_name", ""),
            product_type=data.get("product_type", ""),
            summary=data.get("summary", ""),
            phases=phases,
            total_estimated_time=data.get("total_estimated_time", ""),
            success_criteria=data.get("success_criteria", []),
            risks=data.get("risks", []),
            tools_needed=data.get("tools_needed", []),
            notes=data.get("notes", ""),
        )


# JSON schema for plan response
PLAN_SCHEMA = """{
    "project_name": "string",
    "product_type": "printable | document | web | app",
    "summary": "string - brief overview of the plan",
    "phases": [
        {
            "name": "Phase name",
            "description": "What this phase accomplishes",
            "deliverables": ["list", "of", "outputs"],
            "estimated_time": "e.g., '2 hours' (human equivalent time)",
            "dependencies": ["phases this depends on"],
            "qc_checkpoint": true/false
        }
    ],
    "total_estimated_time": "e.g., '8 hours' (human equivalent - how long a developer would take)",
    "success_criteria": ["measurable criteria from Brief"],
    "risks": [
        {
            "risk": "description",
            "mitigation": "how to handle it"
        }
    ],
    "tools_needed": ["list of tools/technologies"],
    "notes": "any additional notes"
}"""


class PlannerAgent(BaseAgent):
    """Planner agent - creates build plans from Business Briefs.

    Works with the Round Table system:
    - Receives Brief at kickoff
    - Creates actionable build plan
    - Coordinates with Custom Expert
    - Hands off to QC for plan review
    """

    name = "planner"
    description = "Strategic build planner"
    icon = "📋"
    color = "#2196F3"

    def __init__(self, router=None, memory=None, project_id: int = None, **kwargs):
        super().__init__(router=router, memory=memory, **kwargs)
        self.project_id = project_id

    def get_system_prompt(self) -> str:
        """Get the Planner's system prompt."""
        return """You are the Planner agent for ATLAS.

## Your Role
You create detailed, actionable build plans from Business Briefs.
Your plans guide the Custom Expert in building the product.

## Planning Philosophy
1. **Brief is Truth** - The Business Brief defines what success looks like
2. **Phases are Clear** - Each phase has specific deliverables
3. **QC Checkpoints** - Build in quality gates
4. **Human Equivalent Time** - Estimate how long this would take a human developer (ATLAS builds instantly, but this helps users understand project complexity)
5. **Sellable Output** - Every phase moves toward a sellable product

## Planning Process
1. Understand the Brief completely
2. Identify the product type and requirements
3. Break work into logical phases
4. Define clear deliverables for each phase
5. Identify QC checkpoints
6. List risks and mitigations
7. Specify tools needed

## Phase Guidelines

For **PRINTABLE** products:
- Phase 1: Design/Layout planning
- Phase 2: Template creation
- Phase 3: Content population
- Phase 4: Print-ready finalization
- QC checkpoints after design and final

For **DOCUMENT** products:
- Phase 1: Outline and structure
- Phase 2: Content writing
- Phase 3: Formatting and design
- Phase 4: Publishing prep
- QC checkpoints after outline and final

For **WEB** products:
- Phase 1: Architecture planning
- Phase 2: Core functionality
- Phase 3: UI/UX implementation
- Phase 4: Testing and polish
- QC checkpoints after architecture and final

For **APP** products:
- Phase 1: Feature specification
- Phase 2: Core development
- Phase 3: UI implementation
- Phase 4: Testing and optimization
- QC checkpoints after spec and final

## Output
Return valid JSON matching the schema provided.
Be specific about deliverables - vague plans lead to vague products."""

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Create a build plan from a Brief.

        Args:
            task: Planning request
            context: Should include 'brief' - the Business Brief
            previous_output: Previous agent output

        Returns:
            AgentOutput with BuildPlan
        """
        self.status = AgentStatus.THINKING
        self._current_task = "Creating build plan..."

        try:
            # Get the Brief
            brief = context.get("brief", {}) if context else {}
            if not brief:
                raise ValueError("No Business Brief provided")

            # Build the prompt
            prompt = self._build_planning_prompt(brief, context)

            self.status = AgentStatus.WORKING
            logger.info(f"[Planner] Creating plan for: {brief.get('product_name', 'Unknown')}")

            # Generate the plan
            response, token_info = await self._generate_with_provider(
                prompt,
                system_prompt=self.get_system_prompt(),
                temperature=0.3,
            )

            # Parse the plan
            plan = self._parse_plan(response)

            # Log to conversation
            self._log_to_conversation(plan)

            self.status = AgentStatus.COMPLETED

            return AgentOutput(
                content=plan.summary,
                artifacts={
                    "plan": plan.to_dict(),
                    "type": "build_plan",
                },
                reasoning=f"Created {len(plan.phases)}-phase plan for {plan.product_type} product",
                tokens_used=token_info.get("total_tokens", 0),
                next_agent="qc",  # QC should review the plan
                metadata={
                    "agent": self.name,
                    "phases": len(plan.phases),
                    "qc_checkpoints": sum(1 for p in plan.phases if p.qc_checkpoint),
                },
            )

        except Exception as e:
            logger.error(f"[Planner] Error: {e}")
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Planning failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )

    def _build_planning_prompt(self, brief: dict, context: Optional[dict]) -> str:
        """Build the planning prompt."""
        prompt_parts = [
            "## Business Brief",
            f"**Product:** {brief.get('product_name', 'Unknown')}",
            f"**Type:** {brief.get('product_type', 'Unknown')}",
            f"**Recommendation:** {brief.get('recommendation', 'Unknown')}",
            "",
            f"**Executive Summary:**",
            brief.get('executive_summary', 'No summary'),
            "",
        ]

        # Target customer
        target = brief.get('target_customer', {})
        if target:
            prompt_parts.extend([
                "**Target Customer:**",
                f"- Demographics: {target.get('demographics', 'Unknown')}",
            ])
            if target.get('pain_points'):
                prompt_parts.append(f"- Pain Points: {', '.join(target['pain_points'][:3])}")
            prompt_parts.append("")

        # Success criteria
        criteria = brief.get('success_criteria', [])
        if criteria:
            prompt_parts.extend([
                "**Success Criteria (must achieve):**",
            ])
            for c in criteria:
                prompt_parts.append(f"- {c}")
            prompt_parts.append("")

        # Financials
        financials = brief.get('financials', {})
        if financials:
            prompt_parts.extend([
                "**Financial Context:**",
                f"- Pricing: {financials.get('pricing', 'TBD')}",
                f"- Production Cost: {financials.get('production_cost', 'TBD')}",
                "",
            ])

        # Add conversation context if available
        if context and context.get('conversation'):
            prompt_parts.extend([
                "## Team Conversation",
                context['conversation'][:1000],
                "",
            ])

        # Instructions
        prompt_parts.extend([
            "## Your Task",
            "Create a detailed build plan for this product.",
            "",
            "Requirements:",
            "1. Break into logical phases",
            "2. Each phase needs clear deliverables",
            "3. Include QC checkpoints (at least 2)",
            "4. Identify risks and mitigations",
            "5. List tools/technologies needed",
            "",
            "Return JSON matching this schema:",
            PLAN_SCHEMA,
        ])

        return "\n".join(prompt_parts)

    def _parse_plan(self, response: str) -> BuildPlan:
        """Parse LLM response into BuildPlan."""
        try:
            # Extract JSON
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.strip()
                start = json_str.find('{')
                end = json_str.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = json_str[start:end]

            data = json.loads(json_str)
            return BuildPlan.from_dict(data)

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"[Planner] Failed to parse plan: {e}")
            # Return a minimal plan
            return BuildPlan(
                project_name="Unknown",
                product_type="unknown",
                summary="Failed to parse plan - manual review needed",
                phases=[
                    BuildPhase(
                        name="Review",
                        description="Manual plan creation needed",
                        deliverables=["Plan document"],
                        qc_checkpoint=True,
                    )
                ],
                notes=f"Parse error: {str(e)}",
            )

    def _log_to_conversation(self, plan: BuildPlan):
        """Log plan creation to Round Table conversation."""
        if not self.project_id:
            return

        roundtable = get_roundtable()

        # Announce plan
        phase_summary = ", ".join([p.name for p in plan.phases])
        roundtable.add_message(
            project_id=self.project_id,
            sender=self.name,
            message_type=MessageType.UPDATE,
            content=f"Build plan created: {len(plan.phases)} phases ({phase_summary}). Estimated time: {plan.total_estimated_time}",
            metadata={"plan_summary": plan.summary},
        )

        # Note QC checkpoints
        qc_phases = [p.name for p in plan.phases if p.qc_checkpoint]
        if qc_phases:
            roundtable.add_message(
                project_id=self.project_id,
                sender=self.name,
                message_type=MessageType.UPDATE,
                content=f"QC checkpoints scheduled after: {', '.join(qc_phases)}",
                recipient="qc",
            )

        # Handoff to QC for review
        roundtable.add_message(
            project_id=self.project_id,
            sender=self.name,
            message_type=MessageType.HANDOFF,
            content="Plan ready for QC review. Please verify alignment with Brief.",
            recipient="qc",
        )
