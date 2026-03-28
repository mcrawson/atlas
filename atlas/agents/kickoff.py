"""Kickoff Agent - Project Kickoff and Planning for ATLAS.

The Kickoff agent validates analyst approval, creates project scope,
defines tech stack, and prepares structured handoff to Architect.

Flow:
1. Validates Brief has "go" recommendation
2. Creates project scope, constraints, and tech stack
3. Defines QC checkpoints
4. Hands off to Architect with clear instructions
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from atlas.agents.base import BaseAgent, AgentStatus, AgentOutput

logger = logging.getLogger("atlas.agents.kickoff")


@dataclass
class BuildPhase:
    """A phase in the build plan."""
    name: str
    description: str
    deliverables: list[str] = field(default_factory=list)
    estimated_time: str = ""
    qc_checkpoint: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "deliverables": self.deliverables,
            "estimated_time": self.estimated_time,
            "qc_checkpoint": self.qc_checkpoint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BuildPhase":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            deliverables=data.get("deliverables", []),
            estimated_time=data.get("estimated_time", ""),
            qc_checkpoint=data.get("qc_checkpoint", False),
        )


@dataclass
class KickoffPlan:
    """Project kickoff plan with scope, tech stack, and handoff instructions."""

    # Project basics
    project_name: str = ""
    product_type: str = ""  # printable, document, web, app
    brief_confidence: float = 0.0

    # Scope definition
    scope: dict[str, Any] = field(default_factory=dict)
    # Expected: in_scope, out_of_scope, assumptions

    constraints: list[str] = field(default_factory=list)

    # Tech stack decision
    tech_stack: dict[str, str] = field(default_factory=dict)
    tech_stack_reasoning: str = ""

    # Build phases
    phases: list[BuildPhase] = field(default_factory=list)
    qc_checkpoints: list[str] = field(default_factory=list)

    # Handoff to Architect
    architect_instructions: str = ""
    priority_features: list[str] = field(default_factory=list)
    risk_areas: list[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "product_type": self.product_type,
            "brief_confidence": self.brief_confidence,
            "scope": self.scope,
            "constraints": self.constraints,
            "tech_stack": self.tech_stack,
            "tech_stack_reasoning": self.tech_stack_reasoning,
            "phases": [p.to_dict() for p in self.phases],
            "qc_checkpoints": self.qc_checkpoints,
            "architect_instructions": self.architect_instructions,
            "priority_features": self.priority_features,
            "risk_areas": self.risk_areas,
            "created_at": self.created_at.isoformat(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KickoffPlan":
        phases = [BuildPhase.from_dict(p) for p in data.get("phases", [])]
        return cls(
            project_name=data.get("project_name", ""),
            product_type=data.get("product_type", ""),
            brief_confidence=data.get("brief_confidence", 0.0),
            scope=data.get("scope", {}),
            constraints=data.get("constraints", []),
            tech_stack=data.get("tech_stack", {}),
            tech_stack_reasoning=data.get("tech_stack_reasoning", ""),
            phases=phases,
            qc_checkpoints=data.get("qc_checkpoints", []),
            architect_instructions=data.get("architect_instructions", ""),
            priority_features=data.get("priority_features", []),
            risk_areas=data.get("risk_areas", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            notes=data.get("notes", ""),
        )

    def get_summary(self) -> str:
        """Get human-readable summary of the kickoff plan."""
        phase_list = "\n".join([f"  {i+1}. {p.name}" for i, p in enumerate(self.phases)])
        tech_list = "\n".join([f"  - {k}: {v}" for k, v in self.tech_stack.items()])
        priority_list = "\n".join([f"  - {f}" for f in self.priority_features[:5]])

        return f"""# Kickoff Plan: {self.project_name}

## Product Type
{self.product_type.upper()}

## Scope
**In Scope:**
{self._format_list(self.scope.get('in_scope', []))}

**Out of Scope:**
{self._format_list(self.scope.get('out_of_scope', []))}

## Tech Stack
{tech_list}

**Reasoning:** {self.tech_stack_reasoning}

## Build Phases
{phase_list}

## QC Checkpoints
{self._format_list(self.qc_checkpoints)}

## Priority Features
{priority_list}

## Risk Areas
{self._format_list(self.risk_areas)}

## Instructions for Architect
{self.architect_instructions}
"""

    def _format_list(self, items: list) -> str:
        if not items:
            return "  (none specified)"
        return "\n".join([f"  - {item}" for item in items])


# JSON schema for kickoff response
KICKOFF_SCHEMA = """{
    "project_name": "string - name from Brief",
    "product_type": "printable | document | web | app",
    "brief_confidence": 0.0-1.0,
    "scope": {
        "in_scope": ["features/deliverables we WILL build"],
        "out_of_scope": ["things we are NOT building"],
        "assumptions": ["assumptions we're making"]
    },
    "constraints": ["technical or business constraints"],
    "tech_stack": {
        "framework": "e.g., React, HTML/CSS, Canva format",
        "styling": "e.g., Tailwind CSS, inline styles",
        "build": "e.g., Vite, static HTML"
    },
    "tech_stack_reasoning": "why this stack is appropriate for the product type",
    "phases": [
        {
            "name": "Phase name",
            "description": "What this phase accomplishes",
            "deliverables": ["list of outputs"],
            "estimated_time": "e.g., 2 hours",
            "qc_checkpoint": true/false
        }
    ],
    "qc_checkpoints": ["list of QC check descriptions"],
    "architect_instructions": "clear instructions for the Architect agent",
    "priority_features": ["ordered list of most important features"],
    "risk_areas": ["areas that need extra attention"],
    "notes": "any additional notes"
}"""


class KickoffAgent(BaseAgent):
    """Kickoff agent - validates approval and creates project plan.

    Responsibilities:
    - Validate Brief recommendation is "go"
    - Create project scope and constraints
    - Select appropriate tech stack
    - Define build phases with QC checkpoints
    - Prepare clear handoff to Architect
    """

    name = "kickoff"
    description = "Project kickoff and planning coordinator"
    icon = "🚀"
    color = "#4CAF50"

    def get_system_prompt(self) -> str:
        """Get the Kickoff agent's system prompt."""
        return """You are the Kickoff Agent for ATLAS.

## Your Role
You bridge the gap between business analysis (Analyst) and technical planning (Architect).
After the Analyst gives a "go" recommendation, you:
1. Validate the Brief is complete and actionable
2. Define clear project scope (in/out)
3. Select appropriate tech stack for the product type
4. Create build phases with QC checkpoints
5. Prepare instructions for the Architect

## Tech Stack Guidelines by Product Type

### PRINTABLE Products
- Format: PDF, PNG, or editable template
- Tools: HTML/CSS for templates, PDF generation
- Stack: Static HTML with print-friendly CSS
- QC Focus: Print dimensions, color space, margins

### DOCUMENT Products
- Format: PDF, EPUB, or markdown
- Tools: Markdown, HTML for formatting
- Stack: Markdown + CSS, PDF export
- QC Focus: Formatting, readability, structure

### WEB Products
- Simple: Static HTML/CSS/JS
- Interactive: React or Vue with Tailwind
- Complex: Full stack with backend
- QC Focus: Responsive design, accessibility, performance

### APP Products
- Mobile: React Native, Flutter, or PWA
- Desktop: Electron or native
- QC Focus: Platform guidelines, UX, performance

## Phase Planning Rules
1. Every project needs at least 3 phases
2. Phase 1: Setup/scaffolding
3. Middle phases: Core feature implementation
4. Final phase: Polish and testing
5. QC checkpoint after Phase 1 and final phase minimum

## Output
Return valid JSON matching the schema provided.
Be specific and actionable - vague kickoffs lead to vague products."""

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Process kickoff request and create a KickoffPlan.

        Args:
            task: Kickoff request
            context: Should include 'brief' - the Business Brief
            previous_output: Previous agent output (Analyst)

        Returns:
            AgentOutput with KickoffPlan
        """
        self.status = AgentStatus.THINKING
        self._current_task = "Validating Brief approval..."

        try:
            # Get the Brief from context
            brief = context.get("brief", {}) if context else {}
            if not brief:
                raise ValueError("No Business Brief provided")

            # Validate Brief recommendation
            recommendation = brief.get("recommendation", "")
            if recommendation != "go":
                self.status = AgentStatus.COMPLETED
                return AgentOutput(
                    content=f"Cannot kickoff - Brief recommendation is '{recommendation}', not 'go'",
                    status=AgentStatus.COMPLETED,
                    artifacts={"blocked": True, "reason": f"Brief not approved (recommendation: {recommendation})"},
                    metadata={"agent": self.name, "blocked": True},
                )

            # Create the kickoff plan
            self._current_task = f"Creating kickoff plan for {brief.get('product_name', 'project')}..."

            prompt = self._build_kickoff_prompt(brief, context)

            self.status = AgentStatus.WORKING
            logger.info(f"[Kickoff] Creating plan for: {brief.get('product_name', 'Unknown')}")

            response, token_info = await self._generate_with_provider(
                prompt,
                system_prompt=self.get_system_prompt(),
                temperature=0.3,
            )

            # Parse the kickoff plan
            plan = self._parse_kickoff_plan(response)

            # Ensure we have the product name from Brief
            if not plan.project_name:
                plan.project_name = brief.get("product_name", "Unknown Project")
            if not plan.product_type:
                plan.product_type = brief.get("product_type", "unknown")
            plan.brief_confidence = brief.get("confidence", 0.0)

            self.status = AgentStatus.COMPLETED

            return AgentOutput(
                content=plan.get_summary(),
                artifacts={
                    "kickoff_plan": plan.to_dict(),
                    "type": "kickoff_plan",
                },
                reasoning=f"Created kickoff plan with {len(plan.phases)} phases, {len(plan.qc_checkpoints)} QC checkpoints",
                tokens_used=token_info.get("total_tokens", 0),
                next_agent="architect",
                metadata={
                    "agent": self.name,
                    "product_type": plan.product_type,
                    "phases": len(plan.phases),
                    "qc_checkpoints": len(plan.qc_checkpoints),
                },
            )

        except Exception as e:
            logger.error(f"[Kickoff] Error: {e}")
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Kickoff failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e), "agent": self.name},
            )
        finally:
            self._current_task = None

    def _build_kickoff_prompt(self, brief: dict, context: Optional[dict]) -> str:
        """Build the kickoff prompt from the Brief."""
        prompt_parts = [
            "## Business Brief (Approved for Building)",
            f"**Product:** {brief.get('product_name', 'Unknown')}",
            f"**Type:** {brief.get('product_type', 'Unknown')}",
            f"**Confidence:** {brief.get('confidence', 0) * 100:.0f}%",
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
                pain_points = target['pain_points']
                if isinstance(pain_points, list):
                    prompt_parts.append(f"- Pain Points: {', '.join(pain_points[:3])}")
                else:
                    prompt_parts.append(f"- Pain Points: {pain_points}")
            prompt_parts.append("")

        # Success criteria
        criteria = brief.get('success_criteria', [])
        if criteria:
            prompt_parts.extend(["**Success Criteria:**"])
            for c in criteria[:5]:
                if isinstance(c, dict):
                    prompt_parts.append(f"- {c.get('criterion', str(c))}")
                else:
                    prompt_parts.append(f"- {c}")
            prompt_parts.append("")

        # SWOT - focus on strengths and risks
        swot = brief.get('swot', {})
        if swot:
            strengths = swot.get('strengths', [])
            threats = swot.get('threats', [])
            if strengths:
                prompt_parts.append(f"**Strengths:** {', '.join(strengths[:3])}")
            if threats:
                prompt_parts.append(f"**Threats/Risks:** {', '.join(threats[:3])}")
            prompt_parts.append("")

        # Add any project identity from context
        if context and context.get("project_identity"):
            identity = context["project_identity"]
            prompt_parts.extend([
                "## Project Identity (LOCKED)",
                f"Product Type: **{identity.get('product_type_name', identity['product_type']).upper()}**",
                "This type was explicitly chosen and cannot be changed.",
                "",
            ])

        # Instructions
        prompt_parts.extend([
            "## Your Task",
            "",
            "Create a comprehensive Kickoff Plan that:",
            "1. Defines clear scope (what we WILL and WON'T build)",
            "2. Selects appropriate tech stack for the product type",
            "3. Creates logical build phases with deliverables",
            "4. Identifies QC checkpoints (at least 2: after setup and final)",
            "5. Lists priority features in order of importance",
            "6. Identifies risk areas needing extra attention",
            "7. Writes clear instructions for the Architect agent",
            "",
            "Return JSON matching this schema:",
            KICKOFF_SCHEMA,
        ])

        return "\n".join(prompt_parts)

    def _parse_kickoff_plan(self, response: str) -> KickoffPlan:
        """Parse LLM response into KickoffPlan."""
        try:
            # Extract JSON from response
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
            return KickoffPlan.from_dict(data)

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"[Kickoff] Failed to parse plan: {e}")
            # Return a minimal plan
            return KickoffPlan(
                project_name="Unknown",
                product_type="unknown",
                scope={"in_scope": ["TBD"], "out_of_scope": [], "assumptions": []},
                phases=[
                    BuildPhase(
                        name="Planning",
                        description="Manual kickoff needed - parse failed",
                        deliverables=["Kickoff plan"],
                        qc_checkpoint=True,
                    )
                ],
                architect_instructions="Manual kickoff creation required - automated parsing failed",
                notes=f"Parse error: {str(e)}",
            )
