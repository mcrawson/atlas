"""Oracle - Verification and quality assurance.

The all-seeing eye. Examines every line, questions every decision,
and ensures nothing ships until it meets the standard. Part critic,
part guardian—the last line of defense against bugs and bad patterns.
"""

from typing import Optional
from .base import BaseAgent, AgentOutput, AgentStatus
from .code_validator import CodeValidator, ValidationResult
from atlas.projects.project_types import (
    ProjectTypeDetector, ProjectType, ProjectCategory, PROJECT_CONFIGS
)
from atlas.standards import get_agent_philosophy, SELLABILITY_CHECKLIST, PRODUCT_INTEGRATIONS


# Type-specific verification checklists
TYPE_VERIFICATION = {
    ProjectCategory.APP: """
## App-Specific Verification

### App Store Compliance
- [ ] App follows platform guidelines (iOS HIG / Material Design)
- [ ] No private API usage
- [ ] Proper permission requests with justification
- [ ] Privacy policy requirements addressed
- [ ] Age rating appropriate

### Mobile Best Practices
- [ ] Handles offline/poor connectivity gracefully
- [ ] Respects system settings (dark mode, font size)
- [ ] Proper lifecycle handling (backgrounding, etc.)
- [ ] Efficient battery/resource usage
- [ ] Accessibility labels present

### Store Listing Ready
- [ ] Icon meets specifications
- [ ] Screenshots list is complete
- [ ] Description is compelling and accurate
""",

    ProjectCategory.WEB: """
## Web-Specific Verification

### Performance
- [ ] Reasonable load time expected
- [ ] Images optimized or optimization noted
- [ ] No obvious performance issues in code

### SEO & Accessibility
- [ ] Semantic HTML structure
- [ ] Alt text for images
- [ ] Meta tags present
- [ ] Proper heading hierarchy

### Security
- [ ] No exposed secrets in code
- [ ] Input validation present
- [ ] XSS prevention considered

### Responsiveness
- [ ] Mobile breakpoints addressed
- [ ] Touch-friendly interactions
""",

    ProjectCategory.DOCUMENT: """
## Document-Specific Verification

### Content Quality
- [ ] Clear structure and flow
- [ ] Consistent tone and style
- [ ] No obvious gaps in content outline

### Publishing Requirements
- [ ] Cover specs are correct for target platform
- [ ] Page size/margins specified
- [ ] ISBN/copyright needs addressed
- [ ] All required sections present (TOC, copyright, etc.)

### Formatting
- [ ] Font choices are appropriate
- [ ] Chapter structure is consistent
- [ ] Headers/footers considered
""",

    ProjectCategory.API: """
## API-Specific Verification

### API Design
- [ ] RESTful conventions followed (if REST)
- [ ] Consistent endpoint naming
- [ ] Proper HTTP methods used
- [ ] Clear error responses

### Security
- [ ] Authentication implemented correctly
- [ ] Authorization checks present
- [ ] Input validation on all endpoints
- [ ] Rate limiting considered

### Documentation
- [ ] All endpoints documented
- [ ] Request/response examples provided
- [ ] Authentication instructions clear
""",

    ProjectCategory.CLI: """
## CLI-Specific Verification

### Usability
- [ ] Help text is comprehensive
- [ ] Error messages are helpful
- [ ] Exit codes are meaningful
- [ ] Common flags work as expected (-h, -v, etc.)

### Robustness
- [ ] Handles invalid input gracefully
- [ ] File path edge cases considered
- [ ] Interruption handling (Ctrl+C)
""",

    ProjectCategory.LIBRARY: """
## Library-Specific Verification

### API Design
- [ ] Public API is clean and intuitive
- [ ] Type definitions are complete
- [ ] Breaking changes avoided (if update)

### Quality
- [ ] Test coverage is adequate
- [ ] Documentation is complete
- [ ] No unnecessary dependencies
""",

    ProjectCategory.SCRIPT: """
## Script-Specific Verification

### Reliability
- [ ] Error handling is appropriate
- [ ] Idempotent if applicable
- [ ] Logging is helpful

### Safety
- [ ] Destructive operations have safeguards
- [ ] Credentials handled securely
""",

    ProjectCategory.PRINTABLE: """
## Physical Product Verification

### Print Quality
- [ ] Page dimensions correct for target format (Letter, A4, A5, etc.)
- [ ] Print margins adequate (minimum 0.5 inch / 12mm)
- [ ] Bleed areas included if needed for full-bleed printing
- [ ] Resolution sufficient for print (images, graphics)
- [ ] Colors are print-safe (CMYK-friendly if applicable)

### Content Completeness
- [ ] All required pages/sections present
- [ ] Cover design included (front, back, spine if applicable)
- [ ] Page numbering present and correct
- [ ] Table of contents matches actual pages
- [ ] No placeholder or Lorem Ipsum content

### Usability
- [ ] Writing spaces are adequate size for handwriting
- [ ] Instructions are clear and easy to follow
- [ ] Layout is intuitive and user-friendly
- [ ] Fonts are readable at print size (minimum 10pt for body text)

### Production Ready
- [ ] Files export cleanly to PDF
- [ ] No cropped elements at page edges
- [ ] Binding side margins account for binding method
- [ ] Page order is correct for printing
""",
}


class OracleAgent(BaseAgent):
    """Oracle: Quality guardian and verifier.

    The all-seeing eye. Examines every line, questions every decision,
    and ensures nothing ships until it meets the standard.

    Output Format:
    - Verification Summary: What was reviewed
    - Analysis Results: Detailed findings
    - Issues Found: Any problems discovered
    - Recommendations: Suggested improvements
    - Verdict: APPROVED / NEEDS_REVISION
    """

    name = "oracle"
    description = "The all-seeing eye"
    icon = "🔮"
    color = "#9B59B6"

    def get_system_prompt(
        self,
        validation_result: Optional[ValidationResult] = None,
        project_category: ProjectCategory = None,
        project_config=None
    ) -> str:
        """Get Oracle's system prompt, optionally with validation results and project type."""

        # Get type-specific verification checklist
        type_verification = ""
        if project_category and project_category in TYPE_VERIFICATION:
            type_verification = TYPE_VERIFICATION[project_category]

        # Get type-specific guidance
        type_guidance = ""
        if project_config:
            type_guidance = f"""

PROJECT TYPE: {project_config.name}
Key verification points for this type:
{chr(10).join('- ' + v for v in project_config.verification_focus)}"""

        # Get agent-specific philosophy
        philosophy = get_agent_philosophy("oracle")

        base_prompt = f"""You are Oracle, the SELLABILITY ENFORCER within ATLAS.{type_guidance}

{philosophy}

PERSONALITY:
- Thorough and meticulous in review
- UNCOMPROMISING on sellability - if it's not ready to sell, it's NEEDS_REVISION
- Constructive in feedback
- Knows the difference between "works" and "sellable"

YOUR ROLE:
You verify whether products are SELLABLE - ready to list on a marketplace for real money.
You have access to an automated code validator. Your job is to:
1. Review the automated validation results
2. Apply the SELLABILITY TEST: "Would a customer pay $10+ for this right now?"
3. Check for completeness, polish, and professional quality
4. Recommend integrations (Canva, Figma, etc.) when visual polish is needed
5. REJECT anything that isn't ready to sell

OUTPUT FORMAT - Always structure your response as:

## My Reasoning
[Explain your verification approach - what you focused on, why certain things are critical issues vs minor, and your reasoning for the final verdict. This helps the human reviewer understand your quality assessment.]

## Automated Validation Results
[Summarize what the code validator found - this proves we actually checked the code]

## Manual Analysis

### Correctness
- [Does it solve the original task?]
- [Are there logical errors the validator couldn't catch?]

### Design & Architecture
- [Is the structure sensible?]
- [Are there better approaches?]

### User Experience (if applicable)
- [Will this be usable?]
- [Any UX concerns?]

### Completeness Check
- [ ] All functionality from task description is implemented
- [ ] No placeholder content (Lorem ipsum, TODO, FIXME, etc.)
- [ ] No stub/empty implementations
- [ ] All imports/dependencies are properly specified
- [ ] Error handling is present for critical operations

## Issues Found
[List ALL issues, including automated findings, categorized by severity]

### Critical (Must Fix)
- [Issue]: [Why it's critical] - [Source: automated/manual]

### Important (Should Fix)
- [Issue]: [Why it matters] - [Source: automated/manual]

### Minor (Nice to Have)
- [Issue]: [Suggested improvement]

## Sellability Assessment
Answer honestly: "Would a customer pay $10+ for this right now?"

### Completeness Checklist
- [ ] Zero TODOs, FIXMEs, or placeholder comments
- [ ] Zero abbreviations like "<!-- Repeat for other days -->"
- [ ] Every feature mentioned is fully implemented
- [ ] All sample data is real and substantial (not Lorem ipsum)

### Polish Checklist
- [ ] Professional visual design (not developer defaults)
- [ ] Consistent styling throughout
- [ ] Proper typography, spacing, colors
- [ ] Print-ready for physical products / Store-ready for apps

### Functionality Checklist
- [ ] Works completely out of the box
- [ ] No configuration required to use
- [ ] Handles edge cases gracefully
- [ ] Includes clear instructions if needed

**SELLABLE**: YES / NO / NEEDS_WORK
**Visual Polish**: Does it look professional? (If NO, recommend Canva/Figma)
**Marketplace Ready**: Could this go on Etsy/App Store/Amazon today?

## Recommended Integrations
[If product needs polish, recommend specific integrations:]
- Canva: [What assets to create - covers, icons, graphics]
- Figma: [What UI/UX work is needed]
- Publishing: [Which platform to publish to]

## Verdict
**[APPROVED / NEEDS_REVISION / NEEDS_POLISH]**

- APPROVED = Ready to sell immediately
- NEEDS_REVISION = Code/content issues must be fixed
- NEEDS_POLISH = Works but needs Canva/Figma for visual quality

[Brief justification for the verdict]

[If not APPROVED, list exactly what needs to happen]

GUIDELINES:
- Trust the automated validator for syntax and security - these are real checks
- If the validator found CRITICAL issues, the verdict should be NEEDS_REVISION
- THE PRIMARY QUESTION: "Is this SELLABLE right now?"
- If it looks like a developer prototype, it's NEEDS_POLISH (recommend Canva/Figma)
- If it has TODOs, placeholders, or abbreviations, it's NEEDS_REVISION
- Security issues are always critical
- Completeness is NON-NEGOTIABLE - every feature must be fully implemented
- Always recommend integrations that would improve sellability
- Remember: ATLAS produces sellable products, not demos.

AUTOMATIC REJECTION CRITERIA (always NEEDS_REVISION):
- Placeholder content: "Lorem ipsum", "TODO", "FIXME", "[placeholder]", "example.com"
- Missing error handling for critical operations
- Missing required functionality from the task description
- Hardcoded credentials or API keys
- Empty functions or stub implementations
- Missing required files for the project type (e.g., app needs icon, web needs index.html)

UPDATE VERIFICATION (when reviewing updates to existing products):
- Verify the specific change requested was actually implemented
- Check that existing functionality was NOT broken by the update
- For bug fixes: confirm the bug is actually fixed, not just masked
- For new features: ensure they integrate cleanly with existing code
- Verify version number was bumped appropriately
- Check for regression risks in related functionality
- Changelog entry should accurately describe the change
{type_verification}"""

        if validation_result:
            validation_summary = f"""

AUTOMATED VALIDATION RESULTS (from code analysis):
- Score: {validation_result.score}/100
- Status: {'PASSED' if validation_result.passed else 'FAILED'}
- Code blocks found: {validation_result.code_blocks_found}
- Valid code blocks: {validation_result.code_blocks_valid}
- Checks run: {', '.join(validation_result.checks_run)}

Issues found by automated analysis:"""
            for issue in validation_result.issues:
                validation_summary += f"\n- [{issue.severity.value.upper()}] {issue.category}: {issue.message}"
                if issue.file:
                    validation_summary += f" (in {issue.file})"
                if issue.line:
                    validation_summary += f" at line {issue.line}"

            if not validation_result.issues:
                validation_summary += "\n- No issues found by automated analysis"

            base_prompt += validation_summary

        return base_prompt

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Verify Tinker's implementation.

        Args:
            task: The original task
            context: Optional context (test results, existing code)
            previous_output: Tinker's implementation

        Returns:
            AgentOutput with verdict and recommendations
        """
        self.status = AgentStatus.THINKING
        self._current_task = task

        try:
            # Extract project type from context, Tinker's output, or detect
            project_type = None
            project_category = None
            project_config = None
            detector = ProjectTypeDetector()

            # First, try to get from context (passed from project metadata)
            if context:
                type_str = context.get("project_type")
                cat_str = context.get("project_category")
                type_config = context.get("project_type_config")
                if type_str:
                    try:
                        project_type = ProjectType(type_str)
                        project_config = detector.get_config(project_type)
                        project_category = project_config.category if project_config else None
                    except (ValueError, KeyError):
                        pass
                elif cat_str:
                    try:
                        project_category = ProjectCategory(cat_str)
                    except (ValueError, KeyError):
                        pass

            # Second, try to get from Tinker's artifacts
            if not project_type and previous_output and previous_output.artifacts:
                type_str = previous_output.artifacts.get("project_type")
                cat_str = previous_output.artifacts.get("project_category")
                if type_str:
                    try:
                        project_type = ProjectType(type_str)
                        project_config = detector.get_config(project_type)
                        project_category = project_config.category if project_config else None
                    except (ValueError, KeyError):
                        pass
                elif cat_str:
                    try:
                        project_category = ProjectCategory(cat_str)
                    except (ValueError, KeyError):
                        pass

            # Fallback: detect from task
            if not project_type:
                project_type, project_category, _ = detector.detect(task)
                project_config = detector.get_config(project_type)

            print(f"[Oracle] Verifying {project_type.value if project_type else 'unknown'} ({project_category.value if project_category else 'unknown'})")

            # First, run automated code validation
            validation_result: Optional[ValidationResult] = None
            code_to_validate = ""

            if previous_output:
                code_to_validate = previous_output.content
            else:
                code_to_validate = task

            # Run the code validator
            validator = CodeValidator()
            validation_result = validator.validate(code_to_validate, context)

            # Build verification prompt with validation results
            if previous_output:
                prompt = f"""Review and verify this implementation:

Original Task: {task}

Implementation from Tinker:
{previous_output.content}

The automated code validator has already run and found:
- Score: {validation_result.score}/100
- Passed: {validation_result.passed}
- Critical issues: {sum(1 for i in validation_result.issues if i.severity.value == 'critical')}
- High-severity issues: {sum(1 for i in validation_result.issues if i.severity.value == 'high')}
- Code blocks found: {validation_result.code_blocks_found}
- Valid code blocks: {validation_result.code_blocks_valid}

Now provide your manual analysis focusing on:
1. Does the implementation correctly solve the original task?
2. Are there logical errors the validator couldn't catch?
3. Is the design and architecture sensible?

Based on BOTH the automated results and your manual review, provide your verdict."""
            else:
                # Direct verification of code
                prompt = f"""Review this code/implementation:

{task}

The automated code validator has already run and found:
- Score: {validation_result.score}/100
- Passed: {validation_result.passed}
- Issues found: {len(validation_result.issues)}

Analyze for:
1. Correctness
2. Logical errors
3. Design quality"""

            if context:
                if "test_results" in context:
                    prompt += f"\n\nTest Results:\n{context['test_results']}"
                if "requirements" in context:
                    prompt += f"\n\nRequirements:\n{context['requirements']}"

            self.status = AgentStatus.WORKING

            # Generate verification with validation context and project type in system prompt
            response, token_info = await self._generate_with_provider(
                prompt,
                system_prompt=self.get_system_prompt(validation_result, project_category, project_config),
                temperature=0.3,  # Low temperature for precise analysis
            )

            # Extract reasoning section if present
            reasoning = ""
            if "## My Reasoning" in response:
                parts = response.split("## My Reasoning")
                if len(parts) > 1:
                    reasoning_end = parts[1].find("\n## ")
                    if reasoning_end > 0:
                        reasoning = parts[1][:reasoning_end].strip()
                    else:
                        reasoning = parts[1].strip()

            # Log to memory
            if self.memory:
                self.memory.save_conversation(
                    user_message=f"[Oracle Verifying] {task}",
                    assistant_response=response,
                    model="oracle",
                    task_type="verification"
                )

            # Parse verdict from response - but also consider automated validation
            verdict = "UNKNOWN"
            needs_revision = False

            # If automated validation found critical issues, force NEEDS_REVISION
            critical_count = sum(1 for i in validation_result.issues if i.severity.value == 'critical')
            if critical_count > 0:
                verdict = "NEEDS_REVISION"
                needs_revision = True
            else:
                # Parse from LLM response
                response_upper = response.upper()
                if "**APPROVED**" in response_upper or "VERDICT: APPROVED" in response_upper:
                    verdict = "APPROVED"
                elif "**NEEDS_REVISION**" in response_upper or "VERDICT: NEEDS_REVISION" in response_upper:
                    verdict = "NEEDS_REVISION"
                    needs_revision = True
                elif "APPROVED" in response_upper and "NEEDS_REVISION" not in response_upper:
                    verdict = "APPROVED"
                elif "NEEDS_REVISION" in response_upper:
                    verdict = "NEEDS_REVISION"
                    needs_revision = True

            self.status = AgentStatus.COMPLETED

            return AgentOutput(
                content=response,
                reasoning=reasoning,
                tokens_used=token_info.get("total_tokens", 0),
                prompt_tokens=token_info.get("prompt_tokens", 0),
                completion_tokens=token_info.get("completion_tokens", 0),
                artifacts={
                    "task": task,
                    "type": "verification",
                    "verdict": verdict,
                    "validation": validation_result.to_dict() if validation_result else None,
                    "project_type": project_type.value if project_type else None,
                    "project_category": project_category.value if project_category else None,
                },
                # If needs revision, send back to Mason
                next_agent="mason" if needs_revision else None,
                metadata={
                    "agent": self.name,
                    "verdict": verdict,
                    "needs_revision": needs_revision,
                    "provider": token_info.get("provider", "unknown"),
                    "validation_score": validation_result.score if validation_result else 0,
                    "validation_passed": validation_result.passed if validation_result else False,
                    "project_type": project_type.value if project_type else "unknown",
                    "project_category": project_category.value if project_category else "unknown",
                },
            )

        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Verification failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )
        finally:
            self._current_task = None
