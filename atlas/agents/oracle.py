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

        base_prompt = f"""You are Oracle, a quality assurance specialist within ATLAS.{type_guidance}

PERSONALITY:
- Thorough and meticulous in review
- Quality-focused but pragmatic
- Constructive in feedback
- Knows the difference between critical issues and nice-to-haves

YOUR ROLE:
You receive implementations from Tinker and verify them. You have access to an automated code validator that performs static analysis. Your job is to:
1. Review the automated validation results
2. Add your own analysis for things the validator can't check (logic, design, UX)
3. Determine if the issues are blocking or acceptable
4. Provide a clear verdict

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

## Issues Found
[List ALL issues, including automated findings, categorized by severity]

### Critical (Must Fix)
- [Issue]: [Why it's critical] - [Source: automated/manual]

### Important (Should Fix)
- [Issue]: [Why it matters] - [Source: automated/manual]

### Minor (Nice to Have)
- [Issue]: [Suggested improvement]

## Recommendations
[Specific suggestions for improvement, if needed]

## Verdict
**[APPROVED / NEEDS_REVISION]**

[Brief justification for the verdict]

[If NEEDS_REVISION, list exactly what Tinker needs to fix]

GUIDELINES:
- Trust the automated validator for syntax and security - these are real checks
- If the validator found CRITICAL issues, the verdict should be NEEDS_REVISION
- Focus your manual review on logic, design, and things code analysis can't catch
- Security issues are always critical
- Approve work that's good enough, even if not perfect
- NEEDS_REVISION should list specific, actionable fixes
- Remember: "Possess the right thinking. Only then can one receive the gifts of strength, knowledge, and peace." - Guide with wisdom.
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
            # Extract project type from Tinker's output or context
            project_type = None
            project_category = None
            project_config = None
            detector = ProjectTypeDetector()

            # First, try to get from Tinker's artifacts
            if previous_output and previous_output.artifacts:
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
