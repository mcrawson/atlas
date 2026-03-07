"""
Code Validator for Oracle

Performs real static analysis on generated code to catch actual errors,
not just relying on LLM judgment.
"""

import re
import ast
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class Severity(Enum):
    """Severity levels for issues."""
    CRITICAL = "critical"      # Must fix - code won't work
    HIGH = "high"              # Security issues, major bugs
    MEDIUM = "medium"          # Should fix - best practices
    LOW = "low"                # Nice to have - style improvements
    INFO = "info"              # Informational


@dataclass
class ValidationIssue:
    """A specific issue found during validation."""
    severity: Severity
    category: str
    message: str
    line: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "line": self.line,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
            "file": self.file,
        }


@dataclass
class ValidationResult:
    """Complete validation result."""
    passed: bool
    score: int  # 0-100
    issues: List[ValidationIssue] = field(default_factory=list)
    checks_run: List[str] = field(default_factory=list)
    summary: str = ""
    code_blocks_found: int = 0
    code_blocks_valid: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "issues": [i.to_dict() for i in self.issues],
            "checks_run": self.checks_run,
            "summary": self.summary,
            "code_blocks_found": self.code_blocks_found,
            "code_blocks_valid": self.code_blocks_valid,
            "issue_counts": {
                "critical": sum(1 for i in self.issues if i.severity == Severity.CRITICAL),
                "high": sum(1 for i in self.issues if i.severity == Severity.HIGH),
                "medium": sum(1 for i in self.issues if i.severity == Severity.MEDIUM),
                "low": sum(1 for i in self.issues if i.severity == Severity.LOW),
                "info": sum(1 for i in self.issues if i.severity == Severity.INFO),
            }
        }


class CodeValidator:
    """
    Validates code extracted from Mason's output.

    Performs real checks:
    1. Syntax validation (Python, JavaScript, etc.)
    2. Security pattern detection
    3. Common bug detection
    4. Best practice checks
    """

    # Security patterns to check
    SECURITY_PATTERNS = {
        "python": [
            (r'eval\s*\(', "Use of eval() is dangerous - can execute arbitrary code", Severity.HIGH),
            (r'exec\s*\(', "Use of exec() is dangerous - can execute arbitrary code", Severity.HIGH),
            (r'subprocess\.call\s*\([^,]*shell\s*=\s*True', "Shell=True in subprocess is dangerous", Severity.HIGH),
            (r'os\.system\s*\(', "os.system() is vulnerable to command injection, use subprocess", Severity.MEDIUM),
            (r'pickle\.load', "pickle.load() can execute arbitrary code, use JSON instead", Severity.MEDIUM),
            (r'yaml\.load\s*\([^)]*\)', "yaml.load() without Loader is unsafe, use yaml.safe_load()", Severity.HIGH),
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected", Severity.CRITICAL),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key detected", Severity.CRITICAL),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret detected", Severity.CRITICAL),
            (r'cursor\.execute\s*\([^,]*%', "Possible SQL injection - use parameterized queries", Severity.HIGH),
            (r'\.format\s*\(.*\).*execute', "Possible SQL injection via string formatting", Severity.HIGH),
            (r'f["\'].*{.*}.*["\'].*execute', "Possible SQL injection via f-string", Severity.HIGH),
        ],
        "javascript": [
            (r'eval\s*\(', "Use of eval() is dangerous", Severity.HIGH),
            (r'innerHTML\s*=', "innerHTML can lead to XSS, use textContent instead", Severity.MEDIUM),
            (r'document\.write\s*\(', "document.write() can lead to XSS", Severity.MEDIUM),
            (r'\.html\s*\(.*\+', "jQuery .html() with concatenation may cause XSS", Severity.MEDIUM),
            (r'dangerouslySetInnerHTML', "dangerouslySetInnerHTML should be used with caution", Severity.MEDIUM),
            (r'password\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded password detected", Severity.CRITICAL),
            (r'api[_-]?key\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded API key detected", Severity.CRITICAL),
            (r'exec\s*\(', "Use of exec() is dangerous", Severity.HIGH),
        ],
        "sql": [
            (r'--.*password', "Password in SQL comment", Severity.MEDIUM),
            (r'DROP\s+TABLE', "DROP TABLE statement detected - ensure this is intentional", Severity.MEDIUM),
            (r'DELETE\s+FROM\s+\w+\s*;', "DELETE without WHERE - will delete all rows", Severity.HIGH),
            (r'TRUNCATE\s+TABLE', "TRUNCATE TABLE detected - ensure this is intentional", Severity.MEDIUM),
        ],
        "bash": [
            (r'\$\([^)]*\$[A-Z_]+', "Command substitution with unquoted variable", Severity.MEDIUM),
            (r'rm\s+-rf\s+/', "Dangerous rm -rf on root path", Severity.CRITICAL),
            (r'chmod\s+777', "chmod 777 gives everyone full permissions", Severity.MEDIUM),
            (r'curl.*\|\s*bash', "Piping curl to bash is dangerous", Severity.HIGH),
            (r'wget.*\|\s*bash', "Piping wget to bash is dangerous", Severity.HIGH),
        ],
    }

    # Common bug patterns
    BUG_PATTERNS = {
        "python": [
            (r'def\s+\w+\s*\([^)]*\):\s*\n\s*\n', "Empty function definition", Severity.MEDIUM),
            (r'except:\s*\n\s*pass', "Bare except with pass - silently swallowing errors", Severity.MEDIUM),
            (r'except\s+Exception:\s*\n\s*pass', "Catching Exception and passing - errors ignored", Severity.MEDIUM),
            (r'import\s+\*', "Star import makes code harder to debug", Severity.LOW),
            (r'==\s*None', "Use 'is None' instead of '== None'", Severity.LOW),
            (r'!=\s*None', "Use 'is not None' instead of '!= None'", Severity.LOW),
            (r'if\s+True:', "Condition always True - likely debugging code left in", Severity.MEDIUM),
            (r'while\s+True:(?!.*break)', "Infinite loop without visible break", Severity.MEDIUM),
            (r'TODO|FIXME|XXX|HACK', "TODO/FIXME comment left in code", Severity.INFO),
            (r'print\s*\(', "Print statement (consider using logging)", Severity.INFO),
        ],
        "javascript": [
            (r'console\.log\s*\(', "console.log left in code", Severity.INFO),
            (r'var\s+', "Use let/const instead of var", Severity.LOW),
            (r'==(?!=)', "Use === instead of == for strict equality", Severity.LOW),
            (r'!=(?!=)', "Use !== instead of != for strict inequality", Severity.LOW),
            (r'debugger\s*;', "Debugger statement left in code", Severity.MEDIUM),
            (r'alert\s*\(', "Alert statement left in code", Severity.MEDIUM),
            (r'TODO|FIXME|XXX|HACK', "TODO/FIXME comment left in code", Severity.INFO),
        ],
    }

    def __init__(self):
        self.code_block_pattern = re.compile(
            r'```(\w+)?\s*\n(.*?)```',
            re.DOTALL
        )

    def validate(self, build_output: str, context: Optional[Dict] = None) -> ValidationResult:
        """
        Validate all code in the build output.

        Args:
            build_output: The raw output from Mason
            context: Optional context with requirements

        Returns:
            ValidationResult with all findings
        """
        issues: List[ValidationIssue] = []
        checks_run: List[str] = []
        code_blocks = self._extract_code_blocks(build_output)

        valid_blocks = 0
        total_blocks = len(code_blocks)

        for lang, code, filename in code_blocks:
            block_issues, block_checks = self._validate_block(lang, code, filename)
            issues.extend(block_issues)
            checks_run.extend(block_checks)

            # Check if this block is valid (no critical issues)
            critical_in_block = any(
                i.severity == Severity.CRITICAL and i.file == filename
                for i in block_issues
            )
            if not critical_in_block:
                valid_blocks += 1

        # Run structural checks
        struct_issues, struct_checks = self._validate_structure(build_output, code_blocks)
        issues.extend(struct_issues)
        checks_run.extend(struct_checks)

        # Calculate score
        score = self._calculate_score(issues, total_blocks, valid_blocks)

        # Determine if passed
        critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == Severity.HIGH)
        passed = critical_count == 0 and high_count <= 2

        # Generate summary
        summary = self._generate_summary(issues, total_blocks, valid_blocks, passed)

        return ValidationResult(
            passed=passed,
            score=score,
            issues=issues,
            checks_run=list(set(checks_run)),
            summary=summary,
            code_blocks_found=total_blocks,
            code_blocks_valid=valid_blocks,
        )

    def _extract_code_blocks(self, text: str) -> List[Tuple[str, str, Optional[str]]]:
        """Extract code blocks with language and optional filename."""
        blocks = []

        for match in self.code_block_pattern.finditer(text):
            language = (match.group(1) or "text").lower()
            code = match.group(2).strip()

            # Try to find filename from context
            start_pos = match.start()
            preceding_text = text[max(0, start_pos - 200):start_pos]

            filename = None
            file_match = re.search(r'(?:###?\s*)?`([^`]+\.[a-zA-Z0-9]+)`', preceding_text)
            if file_match:
                filename = file_match.group(1)

            blocks.append((language, code, filename))

        return blocks

    def _validate_block(
        self,
        language: str,
        code: str,
        filename: Optional[str]
    ) -> Tuple[List[ValidationIssue], List[str]]:
        """Validate a single code block."""
        issues: List[ValidationIssue] = []
        checks_run: List[str] = []

        # Syntax validation for Python
        if language in ["python", "py"]:
            syntax_issues = self._check_python_syntax(code, filename)
            issues.extend(syntax_issues)
            checks_run.append("Python syntax validation")

        # Syntax validation for JavaScript
        elif language in ["javascript", "js", "jsx", "typescript", "ts", "tsx"]:
            # Basic syntax checks (can't fully parse without a JS parser)
            checks_run.append("JavaScript basic syntax check")
            # Check for obvious syntax errors
            if code.count('{') != code.count('}'):
                issues.append(ValidationIssue(
                    severity=Severity.CRITICAL,
                    category="Syntax",
                    message="Mismatched curly braces",
                    file=filename,
                ))
            if code.count('(') != code.count(')'):
                issues.append(ValidationIssue(
                    severity=Severity.CRITICAL,
                    category="Syntax",
                    message="Mismatched parentheses",
                    file=filename,
                ))

        # Security checks
        lang_key = self._normalize_language(language)
        if lang_key in self.SECURITY_PATTERNS:
            security_issues = self._check_patterns(
                code, self.SECURITY_PATTERNS[lang_key], "Security", filename
            )
            issues.extend(security_issues)
            checks_run.append(f"{language} security pattern check")

        # Bug pattern checks
        if lang_key in self.BUG_PATTERNS:
            bug_issues = self._check_patterns(
                code, self.BUG_PATTERNS[lang_key], "Code Quality", filename
            )
            issues.extend(bug_issues)
            checks_run.append(f"{language} bug pattern check")

        return issues, checks_run

    def _check_python_syntax(
        self,
        code: str,
        filename: Optional[str]
    ) -> List[ValidationIssue]:
        """Check Python code for syntax errors."""
        issues = []

        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(ValidationIssue(
                severity=Severity.CRITICAL,
                category="Syntax",
                message=f"Python syntax error: {e.msg}",
                line=e.lineno,
                code_snippet=e.text.strip() if e.text else None,
                file=filename,
                suggestion="Fix the syntax error before the code can run",
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=Severity.CRITICAL,
                category="Syntax",
                message=f"Failed to parse Python: {str(e)}",
                file=filename,
            ))

        return issues

    def _check_patterns(
        self,
        code: str,
        patterns: List[Tuple[str, str, Severity]],
        category: str,
        filename: Optional[str]
    ) -> List[ValidationIssue]:
        """Check code against regex patterns."""
        issues = []

        for pattern, message, severity in patterns:
            matches = list(re.finditer(pattern, code, re.IGNORECASE))
            for match in matches:
                # Find line number
                line = code[:match.start()].count('\n') + 1
                # Get snippet
                snippet_start = max(0, match.start() - 20)
                snippet_end = min(len(code), match.end() + 20)
                snippet = code[snippet_start:snippet_end].strip()

                issues.append(ValidationIssue(
                    severity=severity,
                    category=category,
                    message=message,
                    line=line,
                    code_snippet=snippet[:100],
                    file=filename,
                ))

        return issues

    def _validate_structure(
        self,
        build_output: str,
        code_blocks: List[Tuple[str, str, Optional[str]]]
    ) -> Tuple[List[ValidationIssue], List[str]]:
        """Validate overall structure of the output."""
        issues: List[ValidationIssue] = []
        checks_run: List[str] = []

        checks_run.append("Structure validation")

        # Check for required sections
        required_sections = ["Implementation", "Files Modified"]
        for section in required_sections:
            if section not in build_output:
                issues.append(ValidationIssue(
                    severity=Severity.LOW,
                    category="Structure",
                    message=f"Missing '{section}' section in output",
                    suggestion=f"Add a '## {section}' section for completeness",
                ))

        # Check for visual preview
        if "## Visual Preview" not in build_output:
            issues.append(ValidationIssue(
                severity=Severity.LOW,
                category="Structure",
                message="No Visual Preview section provided",
                suggestion="Add a Visual Preview with ASCII diagram or HTML mockup",
            ))

        # Check that there's actual code
        if len(code_blocks) == 0:
            issues.append(ValidationIssue(
                severity=Severity.HIGH,
                category="Content",
                message="No code blocks found in implementation",
                suggestion="The implementation should include actual code",
            ))

        # Check for test instructions
        if "## Notes for Oracle" not in build_output and "testing" not in build_output.lower():
            issues.append(ValidationIssue(
                severity=Severity.LOW,
                category="Documentation",
                message="No testing instructions provided",
                suggestion="Add notes for how to verify the implementation",
            ))

        return issues, checks_run

    def _normalize_language(self, language: str) -> str:
        """Normalize language identifier."""
        mapping = {
            "py": "python",
            "js": "javascript",
            "ts": "javascript",
            "jsx": "javascript",
            "tsx": "javascript",
            "sh": "bash",
            "shell": "bash",
            "zsh": "bash",
        }
        return mapping.get(language, language)

    def _calculate_score(
        self,
        issues: List[ValidationIssue],
        total_blocks: int,
        valid_blocks: int
    ) -> int:
        """Calculate quality score 0-100."""
        # Start at 100
        score = 100

        # Deduct for issues
        for issue in issues:
            if issue.severity == Severity.CRITICAL:
                score -= 25
            elif issue.severity == Severity.HIGH:
                score -= 15
            elif issue.severity == Severity.MEDIUM:
                score -= 5
            elif issue.severity == Severity.LOW:
                score -= 2
            # INFO doesn't deduct

        # Bonus/penalty for valid blocks ratio
        if total_blocks > 0:
            validity_ratio = valid_blocks / total_blocks
            if validity_ratio == 1.0:
                score += 5  # Bonus for all blocks valid
            elif validity_ratio < 0.5:
                score -= 10  # Penalty if less than half are valid

        return max(0, min(100, score))

    def _generate_summary(
        self,
        issues: List[ValidationIssue],
        total_blocks: int,
        valid_blocks: int,
        passed: bool
    ) -> str:
        """Generate human-readable summary."""
        critical = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        high = sum(1 for i in issues if i.severity == Severity.HIGH)
        medium = sum(1 for i in issues if i.severity == Severity.MEDIUM)
        low = sum(1 for i in issues if i.severity == Severity.LOW)

        if passed:
            if len(issues) == 0:
                return "All checks passed - code is ready for delivery"
            else:
                return f"Passed with {len(issues)} minor issue(s) to consider"
        else:
            parts = []
            if critical > 0:
                parts.append(f"{critical} critical")
            if high > 0:
                parts.append(f"{high} high-severity")
            return f"Needs revision: {', '.join(parts)} issue(s) found"
