"""
ATLAS Guidance System

Reduces hallucinations and improves output quality through:
1. Task Decomposition - Break large tasks into validated subtasks
2. Output Constraints - Structured templates with required sections
3. Validation Checkpoints - Verify outputs meet requirements before proceeding

This module provides guardrails for each agent to produce focused, accurate outputs.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class ValidationStatus(Enum):
    """Status of a validation check."""
    PASSED = "passed"
    WARNING = "warning"  # Can proceed but flagged
    FAILED = "failed"    # Must fix before proceeding


@dataclass
class ValidationResult:
    """Result of a validation checkpoint."""
    status: ValidationStatus
    checks: List[Dict[str, Any]]  # Individual check results
    summary: str
    suggestions: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status != ValidationStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "passed": self.passed,
            "checks": self.checks,
            "summary": self.summary,
            "suggestions": self.suggestions,
        }


@dataclass
class Subtask:
    """A decomposed subtask with clear scope."""
    id: str
    title: str
    description: str
    scope: str  # What this subtask covers
    success_criteria: List[str]  # How to verify completion
    dependencies: List[str] = field(default_factory=list)  # IDs of required subtasks
    estimated_complexity: str = "medium"  # simple, medium, complex
    completed: bool = False
    output: Optional[str] = None


@dataclass
class OutputTemplate:
    """Template constraining agent output structure."""
    name: str
    required_sections: List[str]
    optional_sections: List[str] = field(default_factory=list)
    max_length: int = 4000  # Max characters
    format_hints: Dict[str, str] = field(default_factory=dict)

    def get_template_prompt(self) -> str:
        """Generate prompt text describing the required format."""
        sections = "\n".join(f"- **{s}** (required)" for s in self.required_sections)
        if self.optional_sections:
            sections += "\n" + "\n".join(f"- {s} (optional)" for s in self.optional_sections)

        hints = ""
        if self.format_hints:
            hints = "\n\nFormat guidelines:\n" + "\n".join(
                f"- {k}: {v}" for k, v in self.format_hints.items()
            )

        return f"""Structure your response with these sections:
{sections}

Keep your response under {self.max_length} characters. Be concise and focused.
{hints}"""


# =============================================================================
# OUTPUT TEMPLATES FOR EACH AGENT
# =============================================================================

ARCHITECT_TEMPLATE = OutputTemplate(
    name="architect_plan",
    required_sections=[
        "Understanding",      # What the task is asking for
        "Approach",          # High-level strategy
        "Components",        # Key parts to build
        "Steps",             # Ordered implementation steps
        "Risks",             # Potential issues
    ],
    optional_sections=[
        "Alternatives",      # Other approaches considered
        "Questions",         # Clarifications needed
    ],
    max_length=3000,
    format_hints={
        "Steps": "Number each step (1, 2, 3...)",
        "Components": "Use bullet points",
        "Risks": "Include mitigation strategies",
    }
)

MASON_TEMPLATE = OutputTemplate(
    name="mason_build",
    required_sections=[
        "Implementation Summary",  # What was built
        "Files",                   # Files created/modified
        "Code",                    # The actual code
        "Usage",                   # How to use it
    ],
    optional_sections=[
        "Dependencies",      # Required packages
        "Notes",            # Implementation notes
    ],
    max_length=6000,  # Longer for code
    format_hints={
        "Code": "Use markdown code blocks with language tags",
        "Files": "List with full paths",
        "Usage": "Include example commands or code",
    }
)

ORACLE_TEMPLATE = OutputTemplate(
    name="oracle_verification",
    required_sections=[
        "Summary",           # Overall assessment
        "Checklist",         # What was verified
        "Issues",            # Problems found (or 'None')
        "Verdict",           # APPROVED or NEEDS_REVISION
    ],
    optional_sections=[
        "Recommendations",   # Suggested improvements
        "Test Results",      # If tests were run
    ],
    max_length=2500,
    format_hints={
        "Checklist": "Use ✅ or ❌ for each item",
        "Verdict": "Must be exactly APPROVED or NEEDS_REVISION",
        "Issues": "Be specific about location and fix",
    }
)


# =============================================================================
# TASK DECOMPOSITION
# =============================================================================

class TaskDecomposer:
    """Breaks large tasks into manageable subtasks."""

    # Keywords suggesting task complexity
    COMPLEXITY_INDICATORS = {
        "simple": ["fix", "update", "change", "rename", "add comment", "typo"],
        "complex": ["build", "create", "implement", "design", "refactor", "migrate",
                   "integrate", "full", "complete", "entire", "system", "architecture"],
    }

    @classmethod
    def estimate_complexity(cls, task: str) -> str:
        """Estimate task complexity from description."""
        task_lower = task.lower()

        # Check for simple indicators
        for indicator in cls.COMPLEXITY_INDICATORS["simple"]:
            if indicator in task_lower:
                return "simple"

        # Check for complex indicators
        complex_count = sum(
            1 for indicator in cls.COMPLEXITY_INDICATORS["complex"]
            if indicator in task_lower
        )

        if complex_count >= 2:
            return "complex"
        elif complex_count == 1:
            return "medium"

        # Default based on length
        if len(task) < 50:
            return "simple"
        elif len(task) > 200:
            return "complex"
        return "medium"

    @classmethod
    def decompose(cls, task: str, context: Dict[str, Any] = None) -> List[Subtask]:
        """Break a task into subtasks based on complexity."""
        complexity = cls.estimate_complexity(task)
        context = context or {}

        if complexity == "simple":
            # Simple tasks don't need decomposition
            return [Subtask(
                id="main",
                title="Complete Task",
                description=task,
                scope="Full task",
                success_criteria=["Task completed as requested"],
                estimated_complexity="simple",
            )]

        # Extract features if provided
        features = context.get("features", [])

        subtasks = []

        # Always start with understanding/planning
        subtasks.append(Subtask(
            id="understand",
            title="Understand Requirements",
            description="Analyze the task and identify key requirements",
            scope="Requirements analysis",
            success_criteria=[
                "All requirements identified",
                "Ambiguities clarified",
                "Scope defined",
            ],
            estimated_complexity="simple",
        ))

        # Design phase for complex tasks
        if complexity == "complex":
            subtasks.append(Subtask(
                id="design",
                title="Design Solution",
                description="Create high-level design and architecture",
                scope="Solution architecture",
                success_criteria=[
                    "Components identified",
                    "Interfaces defined",
                    "Data flow mapped",
                ],
                dependencies=["understand"],
                estimated_complexity="medium",
            ))

        # Core implementation - split by features if available
        if features:
            for i, feature in enumerate(features[:5]):  # Limit to 5 features
                subtasks.append(Subtask(
                    id=f"feature_{i}",
                    title=f"Implement: {feature[:50]}",
                    description=f"Build the {feature} functionality",
                    scope=feature,
                    success_criteria=[
                        f"{feature} works as expected",
                        "Code is clean and documented",
                    ],
                    dependencies=["design"] if complexity == "complex" else ["understand"],
                    estimated_complexity="medium",
                ))
        else:
            # Generic implementation subtask
            subtasks.append(Subtask(
                id="implement",
                title="Core Implementation",
                description="Build the main functionality",
                scope="Core features",
                success_criteria=[
                    "Main functionality works",
                    "Code follows best practices",
                ],
                dependencies=["design"] if complexity == "complex" else ["understand"],
                estimated_complexity="medium",
            ))

        # Testing/verification
        subtasks.append(Subtask(
            id="verify",
            title="Verify Implementation",
            description="Test and validate the implementation",
            scope="Quality assurance",
            success_criteria=[
                "All features tested",
                "No critical bugs",
                "Meets requirements",
            ],
            dependencies=[s.id for s in subtasks if s.id.startswith("feature_") or s.id == "implement"],
            estimated_complexity="simple",
        ))

        return subtasks

    @classmethod
    def get_current_focus(cls, subtasks: List[Subtask]) -> Optional[Subtask]:
        """Get the next subtask to work on."""
        for subtask in subtasks:
            if subtask.completed:
                continue
            # Check if dependencies are met
            deps_met = all(
                any(s.id == dep and s.completed for s in subtasks)
                for dep in subtask.dependencies
            )
            if deps_met:
                return subtask
        return None

    @classmethod
    def get_focus_prompt(cls, subtask: Subtask) -> str:
        """Generate a focused prompt for the current subtask."""
        criteria = "\n".join(f"- {c}" for c in subtask.success_criteria)
        return f"""
**Current Focus: {subtask.title}**

Scope: {subtask.scope}
Description: {subtask.description}

Success Criteria:
{criteria}

Stay focused on this specific subtask. Do not work on other parts yet.
"""


# =============================================================================
# VALIDATION CHECKPOINTS
# =============================================================================

class ValidationCheckpoint:
    """Validates agent outputs before proceeding."""

    @classmethod
    def validate_architect_output(cls, output: str, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate Architect's plan output."""
        checks = []
        suggestions = []

        # Check for required sections
        required_found = 0
        for section in ARCHITECT_TEMPLATE.required_sections:
            found = bool(re.search(rf'\b{section}\b', output, re.IGNORECASE))
            checks.append({
                "name": f"Has {section} section",
                "passed": found,
                "required": True,
            })
            if found:
                required_found += 1
            else:
                suggestions.append(f"Add a '{section}' section to the plan")

        # Check for numbered steps
        has_steps = bool(re.search(r'\d+[\.\)]\s+\w', output))
        checks.append({
            "name": "Has numbered steps",
            "passed": has_steps,
            "required": False,
        })
        if not has_steps:
            suggestions.append("Number your implementation steps for clarity")

        # Check length
        under_limit = len(output) <= ARCHITECT_TEMPLATE.max_length
        checks.append({
            "name": f"Under {ARCHITECT_TEMPLATE.max_length} chars",
            "passed": under_limit,
            "required": False,
        })
        if not under_limit:
            suggestions.append("Consider condensing the plan - focus on key points")

        # Check for vague language
        vague_phrases = ["somehow", "maybe", "might work", "not sure", "i think"]
        vague_found = [p for p in vague_phrases if p in output.lower()]
        checks.append({
            "name": "No vague language",
            "passed": len(vague_found) == 0,
            "required": False,
        })
        if vague_found:
            suggestions.append(f"Remove vague language: {', '.join(vague_found)}")

        # Determine overall status
        if required_found < len(ARCHITECT_TEMPLATE.required_sections) // 2:
            status = ValidationStatus.FAILED
            summary = "Plan is missing critical sections"
        elif required_found < len(ARCHITECT_TEMPLATE.required_sections):
            status = ValidationStatus.WARNING
            summary = "Plan is acceptable but could be improved"
        else:
            status = ValidationStatus.PASSED
            summary = "Plan meets all requirements"

        return ValidationResult(
            status=status,
            checks=checks,
            summary=summary,
            suggestions=suggestions,
        )

    @classmethod
    def validate_mason_output(cls, output: str, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate Mason's implementation output."""
        checks = []
        suggestions = []

        # Check for code blocks
        has_code = "```" in output
        checks.append({
            "name": "Contains code blocks",
            "passed": has_code,
            "required": True,
        })
        if not has_code:
            suggestions.append("Include code in markdown code blocks (```)")

        # Check for file references
        has_files = bool(re.search(r'\.(py|js|ts|html|css|json|yaml|yml|md)\b', output))
        checks.append({
            "name": "References specific files",
            "passed": has_files,
            "required": True,
        })
        if not has_files:
            suggestions.append("Specify which files are created/modified")

        # Check for required sections
        required_found = 0
        for section in MASON_TEMPLATE.required_sections:
            found = bool(re.search(rf'\b{section}\b', output, re.IGNORECASE))
            checks.append({
                "name": f"Has {section} section",
                "passed": found,
                "required": True,
            })
            if found:
                required_found += 1

        # Check for incomplete code markers
        incomplete_markers = ["TODO", "FIXME", "...", "pass  #", "NotImplemented"]
        incomplete_found = [m for m in incomplete_markers if m in output]
        checks.append({
            "name": "No incomplete code markers",
            "passed": len(incomplete_found) == 0,
            "required": False,
        })
        if incomplete_found:
            suggestions.append(f"Complete all code - found: {', '.join(incomplete_found)}")

        # Determine status
        critical_failed = not has_code or not has_files
        if critical_failed:
            status = ValidationStatus.FAILED
            summary = "Implementation is missing code or file references"
        elif required_found < len(MASON_TEMPLATE.required_sections):
            status = ValidationStatus.WARNING
            summary = "Implementation could use better structure"
        else:
            status = ValidationStatus.PASSED
            summary = "Implementation meets requirements"

        return ValidationResult(
            status=status,
            checks=checks,
            summary=summary,
            suggestions=suggestions,
        )

    @classmethod
    def validate_oracle_output(cls, output: str, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate Oracle's verification output."""
        checks = []
        suggestions = []

        # Check for verdict
        has_approved = "APPROVED" in output.upper()
        has_revision = "NEEDS_REVISION" in output.upper() or "NEEDS REVISION" in output.upper()
        has_verdict = has_approved or has_revision
        checks.append({
            "name": "Contains clear verdict",
            "passed": has_verdict,
            "required": True,
        })
        if not has_verdict:
            suggestions.append("Must include APPROVED or NEEDS_REVISION verdict")

        # Check for checklist items
        has_checklist = bool(re.search(r'[✅❌✓✗\[\]]', output))
        checks.append({
            "name": "Has verification checklist",
            "passed": has_checklist,
            "required": True,
        })
        if not has_checklist:
            suggestions.append("Include a checklist of what was verified")

        # Check for required sections
        for section in ORACLE_TEMPLATE.required_sections:
            found = bool(re.search(rf'\b{section}\b', output, re.IGNORECASE))
            checks.append({
                "name": f"Has {section} section",
                "passed": found,
                "required": False,
            })

        # Check for specific feedback
        is_specific = len(output) > 200 and any(
            word in output.lower()
            for word in ["line", "function", "variable", "file", "error", "issue"]
        )
        checks.append({
            "name": "Provides specific feedback",
            "passed": is_specific,
            "required": False,
        })
        if not is_specific:
            suggestions.append("Provide more specific feedback about what was reviewed")

        # Determine status
        if not has_verdict:
            status = ValidationStatus.FAILED
            summary = "Verification must include a clear verdict"
        elif not has_checklist:
            status = ValidationStatus.WARNING
            summary = "Verification should include a checklist"
        else:
            status = ValidationStatus.PASSED
            summary = "Verification is complete"

        return ValidationResult(
            status=status,
            checks=checks,
            summary=summary,
            suggestions=suggestions,
        )

    @classmethod
    def validate_output(cls, agent: str, output: str, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate output based on agent type."""
        validators = {
            "architect": cls.validate_architect_output,
            "mason": cls.validate_mason_output,
            "oracle": cls.validate_oracle_output,
        }

        validator = validators.get(agent.lower())
        if validator:
            return validator(output, context)

        # Default validation
        return ValidationResult(
            status=ValidationStatus.PASSED,
            checks=[],
            summary="No specific validation for this agent",
        )


# =============================================================================
# GUIDANCE SYSTEM - MAIN INTERFACE
# =============================================================================

class GuidanceSystem:
    """
    Main interface for the guidance system.

    Usage:
        guidance = GuidanceSystem()

        # Get decomposed subtasks
        subtasks = guidance.decompose_task("Build a REST API with auth")

        # Get focused prompt for current subtask
        current = guidance.get_current_subtask(subtasks)
        prompt = guidance.get_agent_prompt("architect", task, subtask=current)

        # Validate output before proceeding
        validation = guidance.validate("architect", output)
        if validation.passed:
            # Continue to next phase
        else:
            # Show validation.suggestions to user
    """

    def __init__(self):
        self.decomposer = TaskDecomposer()
        self.validator = ValidationCheckpoint()
        self.templates = {
            "architect": ARCHITECT_TEMPLATE,
            "mason": MASON_TEMPLATE,
            "oracle": ORACLE_TEMPLATE,
        }

    def decompose_task(self, task: str, context: Dict[str, Any] = None) -> List[Subtask]:
        """Decompose a task into manageable subtasks."""
        return self.decomposer.decompose(task, context)

    def get_current_subtask(self, subtasks: List[Subtask]) -> Optional[Subtask]:
        """Get the next subtask to focus on."""
        return self.decomposer.get_current_focus(subtasks)

    def get_agent_prompt(
        self,
        agent: str,
        task: str,
        context: Dict[str, Any] = None,
        subtask: Optional[Subtask] = None,
        previous_output: Optional[str] = None,
    ) -> str:
        """
        Generate a guided prompt for an agent.

        Includes:
        - Output template requirements
        - Current subtask focus (if applicable)
        - Previous context (if applicable)
        """
        template = self.templates.get(agent.lower())
        if not template:
            return task

        parts = [task]

        # Add subtask focus
        if subtask:
            parts.append(self.decomposer.get_focus_prompt(subtask))

        # Add template requirements
        parts.append("\n---\n**Output Format:**\n" + template.get_template_prompt())

        # Add previous context summary (truncated)
        if previous_output:
            truncated = previous_output[:1500] + "..." if len(previous_output) > 1500 else previous_output
            parts.append(f"\n---\n**Previous Phase Output (for reference):**\n{truncated}")

        return "\n\n".join(parts)

    def validate(self, agent: str, output: str, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate agent output."""
        return self.validator.validate_output(agent, output, context)

    def get_template(self, agent: str) -> Optional[OutputTemplate]:
        """Get the output template for an agent."""
        return self.templates.get(agent.lower())

    def estimate_complexity(self, task: str) -> str:
        """Estimate task complexity."""
        return self.decomposer.estimate_complexity(task)


# Singleton instance
_guidance: Optional[GuidanceSystem] = None


def get_guidance() -> GuidanceSystem:
    """Get the global guidance system instance."""
    global _guidance
    if _guidance is None:
        _guidance = GuidanceSystem()
    return _guidance
