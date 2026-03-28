"""
Healer Mode Handler for ATLAS bug fixes.

Autonomous bug fixing within the ATLAS codebase, operating on
feature branches with test validation.
"""

import logging
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from atlas.operator.config import OvernightConfig
from atlas.operator.safety import SafetyLayer

logger = logging.getLogger(__name__)


@dataclass
class IssueAnalysis:
    """Analysis of a bug/issue."""
    summary: str
    likely_cause: str
    affected_files: list[str]
    fix_strategy: str
    test_files: list[str]
    confidence: float  # 0.0 - 1.0


@dataclass
class FixAttempt:
    """A single fix attempt."""
    file_path: str
    original_content: str
    modified_content: str
    change_description: str


@dataclass
class HealerResult:
    """Result from healer mode processing."""
    success: bool
    branch: str
    analysis: IssueAnalysis
    fixes: list[FixAttempt]
    tests_passed: bool
    test_output: str
    commit_sha: Optional[str]
    error: Optional[str]
    timestamp: datetime


class HealerMode:
    """
    Autonomous ATLAS bug fixing.

    Features:
    - Creates feature branches for all changes
    - Analyzes issues to identify root cause
    - Generates and applies fixes
    - Validates with tests before committing
    - Never touches main branch
    """

    def __init__(self, config: OvernightConfig, safety: SafetyLayer, provider=None):
        self.config = config
        self.safety = safety
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

    @property
    def atlas_root(self) -> Path:
        return self.config.atlas.root

    async def execute(self, task: dict) -> HealerResult:
        """
        Execute an ATLAS bug fix task.

        Args:
            task: Task dict with 'prompt' describing the bug

        Returns:
            HealerResult with fix status and details
        """
        prompt = task.get("prompt", "")
        timestamp = datetime.now()

        # 1. Create working branch
        date_str = timestamp.strftime("%Y%m%d-%H%M%S")
        branch_name = f"fix-{date_str}"

        try:
            branch = await self.safety.create_branch(self.atlas_root, branch_name)
        except Exception as e:
            return HealerResult(
                success=False,
                branch=branch_name,
                analysis=IssueAnalysis("", "", [], "", [], 0.0),
                fixes=[],
                tests_passed=False,
                test_output="",
                commit_sha=None,
                error=f"Failed to create branch: {e}",
                timestamp=timestamp,
            )

        try:
            # 2. Analyze the issue
            analysis = await self._analyze_issue(prompt)
            logger.info(f"Issue analysis: {analysis.summary}")

            if analysis.confidence < 0.5:
                return HealerResult(
                    success=False,
                    branch=branch,
                    analysis=analysis,
                    fixes=[],
                    tests_passed=False,
                    test_output="",
                    commit_sha=None,
                    error=f"Low confidence ({analysis.confidence:.0%}) in analysis. Skipping fix.",
                    timestamp=timestamp,
                )

            # 3. Read relevant code
            code_context = await self._read_files(analysis.affected_files)

            # 4. Generate fix
            fixes = await self._generate_fix(analysis, code_context, prompt)

            if not fixes:
                return HealerResult(
                    success=False,
                    branch=branch,
                    analysis=analysis,
                    fixes=[],
                    tests_passed=False,
                    test_output="",
                    commit_sha=None,
                    error="Could not generate a fix",
                    timestamp=timestamp,
                )

            # 5. Apply fixes
            for fix in fixes:
                await self._apply_fix(fix)

            # 6. Run tests
            test_path = None
            if analysis.test_files:
                test_path = analysis.test_files[0]

            tests_passed, test_output = await self.safety.run_tests(
                self.atlas_root, test_path
            )

            # 7. Commit if tests pass
            commit_sha = None
            if tests_passed:
                commit_sha = await self._commit_changes(analysis.summary, fixes)

            return HealerResult(
                success=tests_passed,
                branch=branch,
                analysis=analysis,
                fixes=fixes,
                tests_passed=tests_passed,
                test_output=test_output,
                commit_sha=commit_sha,
                error=None if tests_passed else "Tests failed",
                timestamp=timestamp,
            )

        except Exception as e:
            logger.exception("Error in healer mode")
            return HealerResult(
                success=False,
                branch=branch,
                analysis=IssueAnalysis("", "", [], "", [], 0.0),
                fixes=[],
                tests_passed=False,
                test_output="",
                commit_sha=None,
                error=str(e),
                timestamp=timestamp,
            )

    async def _analyze_issue(self, prompt: str) -> IssueAnalysis:
        """Analyze the issue to identify affected files and fix strategy."""
        provider = await self._get_provider()

        # Get project structure for context
        structure = await self._get_project_structure()

        analysis_prompt = f"""Analyze this ATLAS bug/issue and identify:
1. A clear summary of the problem
2. The likely root cause
3. Which files are most likely affected
4. A strategy to fix it
5. Which test files should be run to verify

ATLAS Project Structure:
{structure}

Issue Description:
{prompt}

Respond in this exact format:
SUMMARY: <one line summary>
LIKELY_CAUSE: <brief explanation of root cause>
AFFECTED_FILES: <comma-separated list of file paths relative to atlas root, e.g., atlas/agents/mason.py>
FIX_STRATEGY: <description of how to fix>
TEST_FILES: <comma-separated list of test file paths, or "all" for full test suite>
CONFIDENCE: <0.0-1.0 how confident you are in this analysis>"""

        response = await provider.generate(
            prompt=analysis_prompt,
            system_prompt="You are an expert Python developer analyzing bugs in the ATLAS codebase. Be precise about file paths.",
            max_tokens=2000,
            temperature=0.3,
        )

        # Parse response
        return self._parse_analysis(response)

    def _parse_analysis(self, response: str) -> IssueAnalysis:
        """Parse the analysis response."""
        lines = response.strip().split("\n")

        summary = ""
        likely_cause = ""
        affected_files = []
        fix_strategy = ""
        test_files = []
        confidence = 0.5

        for line in lines:
            if line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("LIKELY_CAUSE:"):
                likely_cause = line.replace("LIKELY_CAUSE:", "").strip()
            elif line.startswith("AFFECTED_FILES:"):
                files_str = line.replace("AFFECTED_FILES:", "").strip()
                affected_files = [f.strip() for f in files_str.split(",") if f.strip()]
            elif line.startswith("FIX_STRATEGY:"):
                fix_strategy = line.replace("FIX_STRATEGY:", "").strip()
            elif line.startswith("TEST_FILES:"):
                test_str = line.replace("TEST_FILES:", "").strip()
                if test_str.lower() != "all":
                    test_files = [f.strip() for f in test_str.split(",") if f.strip()]
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except ValueError:
                    confidence = 0.5

        return IssueAnalysis(
            summary=summary,
            likely_cause=likely_cause,
            affected_files=affected_files,
            fix_strategy=fix_strategy,
            test_files=test_files,
            confidence=confidence,
        )

    async def _get_project_structure(self) -> str:
        """Get ATLAS project structure for context."""
        result = subprocess.run(
            ["find", "atlas", "-name", "*.py", "-type", "f"],
            cwd=self.atlas_root,
            capture_output=True,
            text=True,
        )
        files = sorted(result.stdout.strip().split("\n"))
        return "\n".join(files[:100])  # Limit to 100 files

    async def _read_files(self, file_paths: list[str]) -> dict[str, str]:
        """Read content of specified files."""
        context = {}
        for file_path in file_paths[:5]:  # Limit to 5 files
            full_path = self.atlas_root / file_path
            if full_path.exists():
                try:
                    context[file_path] = full_path.read_text()
                except Exception as e:
                    logger.warning(f"Could not read {file_path}: {e}")
        return context

    async def _generate_fix(
        self,
        analysis: IssueAnalysis,
        code_context: dict[str, str],
        original_prompt: str,
    ) -> list[FixAttempt]:
        """Generate fixes for the identified issue."""
        provider = await self._get_provider()

        fixes = []

        for file_path, content in code_context.items():
            fix_prompt = f"""Generate a fix for this issue in the file {file_path}.

Issue: {analysis.summary}
Root Cause: {analysis.likely_cause}
Fix Strategy: {analysis.fix_strategy}

Current file content:
```python
{content}
```

Original bug report:
{original_prompt}

Respond with:
1. CHANGE_DESCRIPTION: Brief description of what you're changing
2. MODIFIED_CONTENT: The complete modified file content

Use this exact format:
CHANGE_DESCRIPTION: <description>
MODIFIED_CONTENT:
```python
<complete file content with fix applied>
```"""

            response = await provider.generate(
                prompt=fix_prompt,
                system_prompt="You are an expert Python developer fixing bugs. Make minimal, targeted changes. Preserve all existing functionality.",
                max_tokens=8000,
                temperature=0.2,
            )

            # Parse the fix
            fix = self._parse_fix(response, file_path, content)
            if fix:
                fixes.append(fix)

        return fixes

    def _parse_fix(
        self, response: str, file_path: str, original_content: str
    ) -> Optional[FixAttempt]:
        """Parse a fix response."""
        # Extract change description
        change_desc = ""
        if "CHANGE_DESCRIPTION:" in response:
            desc_match = re.search(r"CHANGE_DESCRIPTION:\s*(.+?)(?=MODIFIED_CONTENT:|$)", response, re.DOTALL)
            if desc_match:
                change_desc = desc_match.group(1).strip()

        # Extract modified content
        code_match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
        if not code_match:
            return None

        modified_content = code_match.group(1)

        # Sanity check - modified content should be different
        if modified_content.strip() == original_content.strip():
            return None

        return FixAttempt(
            file_path=file_path,
            original_content=original_content,
            modified_content=modified_content,
            change_description=change_desc,
        )

    async def _apply_fix(self, fix: FixAttempt) -> None:
        """Apply a fix to a file."""
        full_path = self.atlas_root / fix.file_path
        full_path.write_text(fix.modified_content)
        logger.info(f"Applied fix to {fix.file_path}: {fix.change_description}")

    async def _commit_changes(
        self, summary: str, fixes: list[FixAttempt]
    ) -> Optional[str]:
        """Commit the changes."""
        # Stage changed files
        for fix in fixes:
            subprocess.run(
                ["git", "add", fix.file_path],
                cwd=self.atlas_root,
                capture_output=True,
            )

        # Check if there are changes to commit
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.atlas_root,
            capture_output=True,
            text=True,
        )
        if not status.stdout.strip():
            return None

        # Commit
        commit_msg = f"fix: {summary}\n\nAutomated overnight fix.\n\nCo-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=self.atlas_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"Commit failed: {result.stderr}")
            return None

        # Get commit SHA
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.atlas_root,
            capture_output=True,
            text=True,
        )

        return sha_result.stdout.strip()[:8]
