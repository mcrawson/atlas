"""QC Agent - Quality Control for ATLAS.

The QC agent validates work at every stage against the Business Brief.
It uses LLM to evaluate actual quality and sellability, not just field checks.

QC Flow:
- Attempt 1: Warning + fix notes → return to agent
- Attempt 2: Still broken → BLOCK → escalate to user

The core question at every stage: "Would someone pay money for this?"
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from atlas.agents.base import BaseAgent, AgentStatus, AgentOutput

logger = logging.getLogger("atlas.agents.qc")


class QCVerdict(Enum):
    """QC verdict levels."""
    PASS = "pass"                      # Good to go
    PASS_WITH_NOTES = "pass_with_notes"  # Minor suggestions, can proceed
    NEEDS_REVISION = "needs_revision"  # Issues found, return to agent (attempt 1)
    BLOCKED = "blocked"                # Still broken after retry (attempt 2)


class IssueSeverity(Enum):
    """Severity of QC issues."""
    CRITICAL = "critical"    # Must fix - blocks progress
    WARNING = "warning"      # Should fix - may affect sellability
    INFO = "info"            # Suggestion for improvement


@dataclass
class QCIssue:
    """An issue found during QC."""
    description: str
    severity: IssueSeverity
    fix: str = ""            # How to fix it (actionable)
    location: str = ""       # Where in the output the issue was found
    brief_reference: str = ""  # Which part of Business Brief this relates to

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "severity": self.severity.value,
            "fix": self.fix,
            "location": self.location,
            "brief_reference": self.brief_reference,
        }


@dataclass
class QCReport:
    """Quality Control report for a piece of work."""

    # Verdict
    verdict: QCVerdict = QCVerdict.PASS
    verdict_reason: str = ""

    # Attempt tracking
    attempt: int = 1  # 1 = first check, 2 = after retry
    max_attempts: int = 2

    # Scores
    alignment_score: float = 0.0    # 0-100, how well it matches Business Brief
    sellability_score: float = 0.0  # 0-100, would someone pay for this?
    quality_score: float = 0.0      # 0-100, overall quality

    # Issues found
    issues: list[QCIssue] = field(default_factory=list)

    # Checks
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)

    # Summary for agent
    fix_instructions: str = ""  # Clear instructions for agent to fix

    # Metadata
    stage: str = ""  # brief, plan, mockup, build
    checked_at: datetime = field(default_factory=datetime.now)
    qc_notes: str = ""
    evaluation_mode: str = ""  # "react_source", "html_preview", "mixed"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "verdict_reason": self.verdict_reason,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "alignment_score": self.alignment_score,
            "sellability_score": self.sellability_score,
            "quality_score": self.quality_score,
            "issues": [i.to_dict() for i in self.issues],
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "fix_instructions": self.fix_instructions,
            "stage": self.stage,
            "checked_at": self.checked_at.isoformat(),
            "qc_notes": self.qc_notes,
            "evaluation_mode": self.evaluation_mode,
        }

    @property
    def critical_issues(self) -> list[QCIssue]:
        """Get only critical issues."""
        return [i for i in self.issues if i.severity == IssueSeverity.CRITICAL]

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return len(self.critical_issues) > 0

    @property
    def should_block(self) -> bool:
        """Check if we should block progress."""
        return self.verdict == QCVerdict.BLOCKED

    @property
    def can_proceed(self) -> bool:
        """Check if work can proceed."""
        return self.verdict in [QCVerdict.PASS, QCVerdict.PASS_WITH_NOTES]

    @classmethod
    def from_dict(cls, data: dict) -> "QCReport":
        """Create from dictionary."""
        issues = [
            QCIssue(
                description=i["description"],
                severity=IssueSeverity(i["severity"]),
                fix=i.get("fix", ""),
                location=i.get("location", ""),
                brief_reference=i.get("brief_reference", ""),
            )
            for i in data.get("issues", [])
        ]
        return cls(
            verdict=QCVerdict(data.get("verdict", "pass")),
            verdict_reason=data.get("verdict_reason", ""),
            attempt=data.get("attempt", 1),
            max_attempts=data.get("max_attempts", 2),
            alignment_score=data.get("alignment_score", 0.0),
            sellability_score=data.get("sellability_score", 0.0),
            quality_score=data.get("quality_score", 0.0),
            issues=issues,
            checks_passed=data.get("checks_passed", []),
            checks_failed=data.get("checks_failed", []),
            fix_instructions=data.get("fix_instructions", ""),
            stage=data.get("stage", ""),
            checked_at=datetime.fromisoformat(data["checked_at"]) if "checked_at" in data else datetime.now(),
            qc_notes=data.get("qc_notes", ""),
        )


# JSON schema for QC evaluation response
QC_RESPONSE_SCHEMA = """{
    "verdict": "pass | pass_with_notes | needs_revision",
    "verdict_reason": "string - clear explanation of verdict",
    "alignment_score": 0-100,
    "sellability_score": 0-100,
    "quality_score": 0-100,
    "issues": [
        {
            "description": "what's wrong",
            "severity": "critical | warning | info",
            "fix": "specific action to fix this",
            "location": "where in the output",
            "brief_reference": "which Business Brief section this relates to"
        }
    ],
    "checks_passed": ["list of things that are good"],
    "checks_failed": ["list of things that failed"],
    "fix_instructions": "clear step-by-step instructions for the agent to fix all issues",
    "qc_notes": "any additional observations"
}"""


class QCAgent(BaseAgent):
    """Quality Control agent for ATLAS.

    Validates work at every stage against the Business Brief.
    Uses LLM to evaluate actual quality and sellability.

    Flow:
    - Attempt 1: Warning + fix notes → return to agent
    - Attempt 2: Still broken → BLOCK → escalate to user
    """

    name = "qc"
    description = "Quality Control gatekeeper"
    icon = "✅"
    color = "#FF5722"

    def __init__(self, router=None, memory=None, **kwargs):
        """Initialize QC Agent.

        QC can work without router/memory for simple checks,
        but needs them for LLM-based evaluation.
        """
        # Allow QC to be initialized without router/memory for basic usage
        self.router = router
        self.memory = memory
        self.options = kwargs
        self._status = AgentStatus.IDLE
        self._current_task = None
        self._callbacks = []

    def get_system_prompt(self) -> str:
        """Get the system prompt for QC."""
        return """You are the QC Agent for ATLAS - the quality gatekeeper.

ATLAS MISSION: Build SELLABLE products. Every output must be something
a customer would pay money for.

YOUR ROLE: Quality Control
You evaluate work at every stage against the Business Brief.
You're not checking boxes - you're asking: "Would someone pay for this?"

YOUR STANDARDS:
1. ALIGNMENT - Does this match what the Business Brief promised?
2. QUALITY - Is this professional, polished work?
3. SELLABILITY - Would the target customer actually buy this?

CRITICAL INSTRUCTION - COMPREHENSIVE FIRST CHECK:
**You MUST find ALL issues in your FIRST evaluation.** Do not:
- Hold back issues for later
- Discover "new" issues after fixes are applied
- Be inconsistent between evaluations

Go through EVERY item in the provided checklist systematically.
Report ALL problems you find in ONE comprehensive list.
The user should NOT see new issues after applying your fixes.

EVALUATION APPROACH:
- Be thorough but fair - catch real issues, not nitpicks
- Be specific - "The executive summary doesn't mention the target customer" not "summary is bad"
- Be actionable - Always provide specific fix instructions
- Compare against the Brief - Every check should reference the Brief
- Be COMPLETE - List every issue in one pass, not spread across multiple checks

SEVERITY LEVELS:
- CRITICAL: Must fix. Product won't sell with this issue. Blocks progress.
- WARNING: Should fix. Affects quality/sellability but not fatal.
- INFO: Could improve. Nice-to-have suggestions.

SCORING:
- Alignment (0-100): How well does this match the Business Brief?
- Sellability (0-100): Would the target customer pay for this?
- Quality (0-100): Is this professional, polished work?

OUTPUT: Return valid JSON matching the schema provided."""

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Process is required by BaseAgent but QC uses specific check methods."""
        # QC doesn't use the generic process method
        # Use specific check methods instead
        return AgentOutput(
            content="Use specific QC check methods: check_business_brief(), check_plan(), check_mockup(), check_build()",
            status=AgentStatus.ERROR,
        )

    async def _evaluate_with_llm(
        self,
        prompt: str,
        stage: str,
        attempt: int = 1,
    ) -> QCReport:
        """Use LLM to evaluate quality.

        Args:
            prompt: The evaluation prompt
            stage: Which stage we're checking
            attempt: Which attempt this is (1 or 2)

        Returns:
            QCReport from LLM evaluation
        """
        if not self.router:
            logger.warning("[QC] No router available, using basic evaluation")
            return self._basic_evaluation(stage, attempt)

        try:
            self.status = AgentStatus.WORKING
            logger.info(f"[QC] Evaluating {stage} (attempt {attempt})")

            response, token_info = await self._generate_with_provider(
                prompt,
                system_prompt=self.get_system_prompt(),
                temperature=0.2,  # Low temperature for consistent evaluation
            )

            # Parse the JSON response
            report = self._parse_qc_response(response, stage, attempt)
            self.status = AgentStatus.COMPLETED
            return report

        except Exception as e:
            logger.error(f"[QC] LLM evaluation failed: {e}")
            self.status = AgentStatus.ERROR
            # Return a safe fallback
            return QCReport(
                verdict=QCVerdict.NEEDS_REVISION,
                verdict_reason=f"QC evaluation failed: {str(e)}",
                stage=stage,
                attempt=attempt,
                issues=[QCIssue(
                    description="QC system error - manual review required",
                    severity=IssueSeverity.CRITICAL,
                    fix="Please review manually and retry",
                )],
            )

    def _parse_qc_response(self, response: str, stage: str, attempt: int) -> QCReport:
        """Parse LLM response into QCReport."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON
                json_str = response.strip()
                # Find the first { and last }
                start = json_str.find('{')
                end = json_str.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = json_str[start:end]

            data = json.loads(json_str)

            # Parse issues
            issues = []
            for i in data.get("issues", []):
                issues.append(QCIssue(
                    description=i.get("description", ""),
                    severity=IssueSeverity(i.get("severity", "warning")),
                    fix=i.get("fix", ""),
                    location=i.get("location", ""),
                    brief_reference=i.get("brief_reference", ""),
                ))

            # Determine verdict based on attempt
            verdict_str = data.get("verdict", "pass")
            if attempt == 2 and verdict_str == "needs_revision":
                # Second attempt still has issues = BLOCKED
                verdict = QCVerdict.BLOCKED
                verdict_reason = "Issues not fixed after retry. Escalating to user."
            else:
                verdict = QCVerdict(verdict_str)
                verdict_reason = data.get("verdict_reason", "")

            return QCReport(
                verdict=verdict,
                verdict_reason=verdict_reason,
                attempt=attempt,
                alignment_score=float(data.get("alignment_score", 0)),
                sellability_score=float(data.get("sellability_score", 0)),
                quality_score=float(data.get("quality_score", 0)),
                issues=issues,
                checks_passed=data.get("checks_passed", []),
                checks_failed=data.get("checks_failed", []),
                fix_instructions=data.get("fix_instructions", ""),
                stage=stage,
                qc_notes=data.get("qc_notes", ""),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"[QC] Failed to parse response: {e}")
            logger.debug(f"[QC] Response was: {response[:500]}")
            return QCReport(
                verdict=QCVerdict.NEEDS_REVISION,
                verdict_reason=f"Failed to parse QC evaluation: {str(e)}",
                stage=stage,
                attempt=attempt,
                issues=[QCIssue(
                    description="QC response parsing failed",
                    severity=IssueSeverity.WARNING,
                    fix="Retry QC check",
                )],
            )

    def _basic_evaluation(self, stage: str, attempt: int) -> QCReport:
        """Basic evaluation without LLM (fallback)."""
        return QCReport(
            verdict=QCVerdict.PASS_WITH_NOTES,
            verdict_reason="Basic check only - LLM evaluation unavailable",
            stage=stage,
            attempt=attempt,
            qc_notes="Full QC requires LLM. This is a basic structural check.",
        )

    # =========================================================================
    # Stage-specific check methods
    # =========================================================================

    async def check_business_brief(
        self,
        brief: dict,
        idea: str,
        attempt: int = 1,
    ) -> QCReport:
        """Check a Business Brief for quality and viability.

        Args:
            brief: The Business Brief to check
            idea: The original idea for context
            attempt: Which attempt this is (1 or 2)

        Returns:
            QCReport with findings
        """
        self._current_task = "Checking Business Brief"

        prompt = f"""Evaluate this Business Brief for quality and sellability.

## Original Idea
{idea}

## Business Brief to Evaluate
```json
{json.dumps(brief, indent=2, default=str)}
```

## Evaluation Criteria

1. **Completeness** - Does it have all required sections?
   - Product name and type
   - Executive summary
   - Target customer (demographics, pain points)
   - Market analysis
   - Financial projections (realistic, not guessed)
   - Success criteria (measurable)
   - Go/No-Go recommendation with reasoning

2. **Quality** - Is the analysis thorough?
   - Are financial projections based on research, not guesses?
   - Is the target customer specific enough to find?
   - Are success criteria measurable?
   - Is the recommendation well-justified?

3. **Sellability** - Does this describe a sellable product?
   - Is there a clear value proposition?
   - Is pricing realistic for the market?
   - Is the target customer real and reachable?

## Your Task
Evaluate this Brief and return a JSON response:

{QC_RESPONSE_SCHEMA}

Be specific. If something is missing or weak, explain exactly what's wrong
and how to fix it. Reference specific sections of the Brief."""

        return await self._evaluate_with_llm(prompt, "business_brief", attempt)

    async def check_plan(
        self,
        plan: dict,
        brief: dict,
        attempt: int = 1,
    ) -> QCReport:
        """Check a build plan against the Business Brief.

        Args:
            plan: The plan to check
            brief: The Business Brief to check against
            attempt: Which attempt this is (1 or 2)

        Returns:
            QCReport with findings
        """
        self._current_task = "Checking Build Plan"

        prompt = f"""Evaluate this Build Plan against the Business Brief.

## Business Brief (Source of Truth)
```json
{json.dumps(brief, indent=2, default=str)}
```

## Build Plan to Evaluate
```json
{json.dumps(plan, indent=2, default=str)}
```

## Evaluation Criteria

1. **Alignment** - Does the plan deliver what the Brief promised?
   - Does it build the product described in the Brief?
   - Does it target the customer identified in the Brief?
   - Will it achieve the success criteria in the Brief?

2. **Completeness** - Is the plan thorough?
   - Are all deliverables specified?
   - Is the timeline realistic?
   - Are dependencies identified?

3. **Feasibility** - Can this plan be executed?
   - Are the technical requirements clear?
   - Is the scope manageable?
   - Are risks identified?

## Your Task
Compare the Plan against the Brief. Return JSON:

{QC_RESPONSE_SCHEMA}

If the Plan doesn't match the Brief, cite specific mismatches.
Example: "Brief says target customer is 'busy professionals' but Plan
doesn't include mobile-friendly features."
"""

        return await self._evaluate_with_llm(prompt, "plan", attempt)

    async def check_mockup(
        self,
        mockup: dict,
        brief: dict,
        plan: dict,
        attempt: int = 1,
    ) -> QCReport:
        """Check a mockup against the plan and Business Brief.

        Args:
            mockup: The mockup to check
            brief: The Business Brief
            plan: The build plan
            attempt: Which attempt this is (1 or 2)

        Returns:
            QCReport with findings
        """
        self._current_task = "Checking Mockup"

        prompt = f"""Evaluate this Mockup against the Business Brief and Plan.

## Business Brief (Source of Truth)
```json
{json.dumps(brief, indent=2, default=str)}
```

## Build Plan
```json
{json.dumps(plan, indent=2, default=str)}
```

## Mockup to Evaluate
```json
{json.dumps(mockup, indent=2, default=str)}
```

## Evaluation Criteria

1. **Alignment** - Does the mockup match the Brief and Plan?
   - Does it look like the product described?
   - Does it serve the target customer's needs?
   - Does it include planned features?

2. **Quality** - Does it look professional?
   - Is the design polished?
   - Is it visually appealing?
   - Does it match industry standards for this product type?

3. **Sellability** - Would someone pay for this?
   - Does it look like a finished product?
   - Would the target customer want this?
   - Does it stand out from competitors mentioned in Brief?

## Your Task
Evaluate the Mockup. Return JSON:

{QC_RESPONSE_SCHEMA}

Focus on: Does this mockup represent a product someone would pay for?
"""

        return await self._evaluate_with_llm(prompt, "mockup", attempt)

    async def check_build(
        self,
        output: dict,
        brief: dict,
        mockup: Optional[dict] = None,
        kickoff_plan: Optional[dict] = None,
        attempt: int = 1,
    ) -> QCReport:
        """Check a build output against the mockup, Brief, and Kickoff Plan.

        Args:
            output: The build output to check
            brief: The Business Brief
            mockup: The approved mockup (optional)
            kickoff_plan: The kickoff plan with scope, tech stack, priorities (optional)
            attempt: Which attempt this is (1 or 2)

        Returns:
            QCReport with findings
        """
        self._current_task = "Checking Build Output"

        mockup_section = ""
        if mockup:
            mockup_section = f"""
## Approved Mockup
```json
{json.dumps(mockup, indent=2, default=str)}
```
"""

        # Include kickoff plan context
        kickoff_section = ""
        if kickoff_plan:
            scope = kickoff_plan.get("scope", {})
            tech_stack = kickoff_plan.get("tech_stack", {})
            priorities = kickoff_plan.get("priority_features", [])
            risks = kickoff_plan.get("risk_areas", [])

            kickoff_section = f"""
## Kickoff Plan (Technical Requirements)

### Scope
**In Scope:** {', '.join(scope.get('in_scope', [])[:5])}
**Out of Scope:** {', '.join(scope.get('out_of_scope', [])[:3])}

### Tech Stack
- Framework: {tech_stack.get('framework', 'Not specified')}
- Styling: {tech_stack.get('styling', 'Not specified')}
- Build: {tech_stack.get('build', 'Not specified')}

### Priority Features (in order)
{chr(10).join([f'{i+1}. {p}' for i, p in enumerate(priorities[:5])])}

### Risk Areas (verify these!)
{chr(10).join([f'- {r}' for r in risks[:4]])}
"""

        # Check if this is a React build by looking for .tsx/.jsx files
        react_source_section = ""
        react_files = {}
        if isinstance(output, dict):
            # Look for actual file content in extracted_files or assembled_files
            files_dict = output.get("extracted_files") or output.get("assembled_files") or {}
            if isinstance(files_dict, dict):
                for filename, content in files_dict.items():
                    if filename.endswith(('.tsx', '.jsx')):
                        react_files[filename] = content

        # Determine evaluation mode based on presence of React files
        evaluation_mode = "react_source" if react_files else "html_preview"

        # If React files found, extract and include source code in evaluation
        if react_files:
            react_source_section = "\n\n## React Source Files (CRITICAL - Evaluate These!)"
            react_source_section += "\n\nNOTE: This is a React SPA. The HTML preview shows an empty <div id='root'> which is normal."
            react_source_section += "\nYou MUST evaluate the React source code below for features and functionality:\n"
            for filename, content in react_files.items():
                # Truncate very large files
                preview = content[:3000] + "\n... (truncated)" if len(content) > 3000 else content
                react_source_section += f"\n### {filename}\n```tsx\n{preview}\n```\n"

        prompt = f"""Evaluate this Build Output. Is it ready to sell?

## Business Brief (Source of Truth)
```json
{json.dumps(brief, indent=2, default=str)}
```
{kickoff_section}
{mockup_section}
## Build Output to Evaluate
```json
{json.dumps(output, indent=2, default=str)}
```
{react_source_section}

## IMPORTANT: COMPREHENSIVE EVALUATION
**You MUST identify ALL issues in this single check.** Do not hold back issues for later.
Go through EVERY item in the checklist below and report any problems you find.
The goal is ONE thorough check, not multiple rounds of discovery.

## MANDATORY CHECKLIST - Check EVERY item:

### 1. ALIGNMENT (Does it match the Brief and Kickoff Plan?)
- [ ] Product matches the type specified in Brief (app, document, printable, etc.)
- [ ] Product name/title matches Brief
- [ ] Target customer needs are addressed
- [ ] Value proposition is clear
- [ ] Success criteria can be measured
- [ ] Pricing tier/model matches Brief
- [ ] Stays within defined SCOPE (not building out-of-scope features)
- [ ] Uses specified TECH STACK (framework, styling, build tools)

### 2. COMPLETENESS (Are priority features implemented?)
- [ ] All PRIORITY FEATURES from kickoff plan are implemented
- [ ] All promised features/sections are present
- [ ] No placeholder text ("Lorem ipsum", "TODO", "[INSERT]")
- [ ] All screens/pages are implemented (for apps/web)
- [ ] All required files are generated
- [ ] Navigation works between all sections

### 3. QUALITY (Is it polished?)
- [ ] Professional appearance
- [ ] Consistent styling throughout
- [ ] No broken elements or layout issues
- [ ] Clear, readable content
- [ ] No obvious typos or grammatical errors
- [ ] Matches mockup (if provided)
- [ ] RISK AREAS from kickoff plan are addressed/mitigated

### 4. FUNCTIONALITY (Does it work?)
- [ ] Core features function as expected
- [ ] Error handling exists where needed
- [ ] User flows are intuitive
- [ ] No dead ends or broken links

### 5. SELLABILITY (Would someone pay?)
- [ ] Looks like a finished product (not a prototype)
- [ ] Competitive with similar products in market
- [ ] Price-appropriate quality
- [ ] Ready for customer to use immediately

## Your Task
Go through EVERY checkbox above. For ANY item that fails, add it to issues.
Be specific about what's wrong and how to fix it.

Return JSON:

{QC_RESPONSE_SCHEMA}

CRITICAL: List ALL issues you find. Do not save issues for later checks.
If something fails a checkbox, it MUST be in your issues list.
"""

        report = await self._evaluate_with_llm(prompt, "build", attempt)
        report.evaluation_mode = evaluation_mode
        return report

    async def full_review(
        self,
        output: dict,
        brief: dict,
        plan: dict,
        mockup: dict,
        attempt: int = 1,
    ) -> QCReport:
        """Full QC review of a completed build.

        Comprehensive check of all aspects before delivery.

        Args:
            output: The build output
            brief: The Business Brief
            plan: The build plan
            mockup: The approved mockup
            attempt: Which attempt this is (1 or 2)

        Returns:
            Comprehensive QCReport
        """
        self._current_task = "Full QC Review"

        prompt = f"""Perform a FULL quality review of this completed build.

## Business Brief (Source of Truth)
```json
{json.dumps(brief, indent=2, default=str)}
```

## Build Plan
```json
{json.dumps(plan, indent=2, default=str)}
```

## Approved Mockup
```json
{json.dumps(mockup, indent=2, default=str)}
```

## Final Build Output
```json
{json.dumps(output, indent=2, default=str)}
```

## IMPORTANT: COMPREHENSIVE EVALUATION
**You MUST identify ALL issues in this single check.** Do not hold back issues.
Go through EVERY item in the checklist below and report any problems you find.
The goal is ONE thorough check, not multiple rounds of discovery.

## MANDATORY CHECKLIST - Check EVERY item:

### Alignment
- [ ] Output matches Business Brief description
- [ ] Target customer needs are served
- [ ] Success criteria can be measured
- [ ] Product type is correct
- [ ] Product name/title matches Brief
- [ ] Value proposition is implemented

### Completeness
- [ ] All promised features/sections are present
- [ ] No placeholder text ("Lorem ipsum", "TODO", "[INSERT]")
- [ ] All screens/pages are implemented
- [ ] All required files are generated

### Quality
- [ ] Output is complete and polished
- [ ] No obvious bugs or issues
- [ ] Matches the approved mockup
- [ ] Professional presentation
- [ ] Consistent styling throughout
- [ ] No typos or grammatical errors

### Sellability
- [ ] Clear value proposition
- [ ] Competitive with market (per Brief research)
- [ ] Price-appropriate quality
- [ ] Ready to list on target marketplace
- [ ] Looks like finished product (not prototype)

### Delivery Readiness
- [ ] All files/assets included
- [ ] Documentation complete (if needed)
- [ ] Ready for customer download/use
- [ ] Navigation works between sections

## Your Task
Go through EVERY checkbox above. For ANY item that fails, add it to issues.
Complete the full review. Return JSON:

{QC_RESPONSE_SCHEMA}

CRITICAL: List ALL issues you find. Do not save issues for later checks.
If something fails a checkbox, it MUST be in your issues list.
This is the FINAL gate. Be thorough NOW, not across multiple checks.
"""

        return await self._evaluate_with_llm(prompt, "full_review", attempt)
