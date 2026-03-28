"""
Code Validator - Validates Mason's output for quality and runnability.

Checks:
- Syntax validity for all code files
- Import resolution
- Format compliance (file markers used?)
- Code completeness (no TODO/FIXME/placeholder)
"""

import ast
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: str  # "error", "warning", "info"
    file: str
    line: Optional[int]
    message: str
    code: str  # Issue code like "SYNTAX_ERROR", "MISSING_IMPORT"


@dataclass
class ValidationResult:
    """Result of code validation."""
    passed: bool
    score: float  # 0.0 to 1.0
    issues: list[ValidationIssue] = field(default_factory=list)
    summary: str = ""

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "passed": self.passed,
            "score": self.score,
            "issues": [
                {"severity": i.severity, "message": i.message, "file": i.file, "line": i.line}
                for i in self.issues
            ],
            "summary": self.summary,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
        }


class CodeValidator:
    """Validates code files for quality and runnability."""

    def __init__(self):
        self.issues: list[ValidationIssue] = []

    def validate(self, files: dict[str, str], mason_output: str = "") -> ValidationResult:
        """Validate all files.

        Args:
            files: Dict of filename -> code content
            mason_output: Raw Mason output for format checking

        Returns:
            ValidationResult with pass/fail and issues
        """
        self.issues = []

        # Check format compliance
        self._check_format_compliance(mason_output)

        # Validate each file
        for filename, content in files.items():
            self._validate_file(filename, content)

        # Calculate score
        total_checks = max(len(files) * 3 + 2, 1)  # 3 checks per file + 2 format
        failed_checks = self.error_count
        score = max(0, (total_checks - failed_checks) / total_checks)

        passed = self.error_count == 0
        summary = self._generate_summary()

        return ValidationResult(
            passed=passed,
            score=score,
            issues=self.issues,
            summary=summary
        )

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    def _check_format_compliance(self, mason_output: str):
        """Check if Mason followed the expected output format."""
        if not mason_output:
            return

        # Check for file markers
        file_markers = re.findall(r'###\s*`([^`]+)`', mason_output)
        code_blocks = re.findall(r'```\w+', mason_output)

        if code_blocks and not file_markers:
            self.issues.append(ValidationIssue(
                severity="warning",
                file="<output>",
                line=None,
                message="Mason did not use file markers (### `filename.ext`). File names may be incorrect.",
                code="FORMAT_NO_MARKERS"
            ))

        # Check for required sections
        required_sections = ["Summary", "Files", "How to Run"]
        for section in required_sections:
            if f"## {section}" not in mason_output:
                self.issues.append(ValidationIssue(
                    severity="info",
                    file="<output>",
                    line=None,
                    message=f"Missing recommended section: '## {section}'",
                    code="FORMAT_MISSING_SECTION"
                ))

    def _validate_file(self, filename: str, content: str):
        """Validate a single file."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext == "py":
            self._validate_python(filename, content)
        elif ext in ("js", "jsx", "ts", "tsx"):
            self._validate_javascript(filename, content)
        elif ext == "json":
            self._validate_json(filename, content)
        elif ext == "pdf":
            self._validate_pdf(filename, content)

        # Common checks for all files
        self._check_placeholders(filename, content)

    def _validate_pdf(self, filename: str, content: str):
        """Validate PDF files - catch fake PDFs that are just text descriptions."""
        # Real PDFs start with %PDF
        if not content.strip().startswith('%PDF'):
            # Check if it's just a text description
            if content.strip().startswith('[') or 'containing' in content.lower():
                self.issues.append(ValidationIssue(
                    severity="error",
                    file=filename,
                    line=None,
                    message="NOT SELLABLE: PDF file is a text description, not an actual PDF",
                    code="SELLABILITY_FAKE_PDF"
                ))
            else:
                self.issues.append(ValidationIssue(
                    severity="error",
                    file=filename,
                    line=None,
                    message="NOT SELLABLE: File has .pdf extension but is not a valid PDF",
                    code="INVALID_PDF"
                ))

    def _validate_python(self, filename: str, content: str):
        """Validate Python code."""
        # Syntax check
        try:
            ast.parse(content)
        except SyntaxError as e:
            self.issues.append(ValidationIssue(
                severity="error",
                file=filename,
                line=e.lineno,
                message=f"Syntax error: {e.msg}",
                code="SYNTAX_ERROR"
            ))
            return  # Can't do more checks if syntax is invalid

        # Check for common missing imports
        lines = content.split("\n")
        import_section = "\n".join(l for l in lines if l.strip().startswith(("import ", "from ")))

        checks = [
            ("requests.", "import requests", "MISSING_IMPORT_REQUESTS"),
            ("@app.", "FastAPI", "MISSING_IMPORT_FASTAPI"),
            ("click.", "import click", "MISSING_IMPORT_CLICK"),
            ("json.", "import json", "MISSING_IMPORT_JSON"),
            ("os.", "import os", "MISSING_IMPORT_OS"),
            ("Path(", "pathlib", "MISSING_IMPORT_PATHLIB"),
        ]

        for usage, import_check, code in checks:
            if usage in content and import_check not in import_section:
                self.issues.append(ValidationIssue(
                    severity="error",
                    file=filename,
                    line=None,
                    message=f"Uses '{usage}' but missing import for {import_check}",
                    code=code
                ))

        # Check for entry point in main files
        if filename in ("main.py", "app.py", "cli.py"):
            if "__main__" not in content:
                self.issues.append(ValidationIssue(
                    severity="warning",
                    file=filename,
                    line=None,
                    message="Main file missing entry point (if __name__ == '__main__':)",
                    code="MISSING_ENTRY_POINT"
                ))

    def _validate_javascript(self, filename: str, content: str):
        """Validate JavaScript code (basic checks)."""
        # Check for obvious syntax issues
        brackets = content.count("{") - content.count("}")
        parens = content.count("(") - content.count(")")

        if abs(brackets) > 0:
            self.issues.append(ValidationIssue(
                severity="error",
                file=filename,
                line=None,
                message=f"Unbalanced curly braces (diff: {brackets})",
                code="SYNTAX_BRACKETS"
            ))

        if abs(parens) > 0:
            self.issues.append(ValidationIssue(
                severity="error",
                file=filename,
                line=None,
                message=f"Unbalanced parentheses (diff: {parens})",
                code="SYNTAX_PARENS"
            ))

    def _validate_json(self, filename: str, content: str):
        """Validate JSON file."""
        import json
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            self.issues.append(ValidationIssue(
                severity="error",
                file=filename,
                line=e.lineno,
                message=f"Invalid JSON: {e.msg}",
                code="JSON_INVALID"
            ))

    def _check_placeholders(self, filename: str, content: str):
        """Check for placeholder content that shouldn't be in production code."""
        # Warning-level placeholders
        warning_placeholders = [
            (r'\bTODO\b', "TODO comment found"),
            (r'\bFIXME\b', "FIXME comment found"),
            (r'\bXXX\b', "XXX marker found"),
            (r'YOUR_API_KEY|API_KEY_HERE|REPLACE_ME', "Placeholder API key found"),
            (r'lorem ipsum', "Lorem ipsum placeholder text"),
            (r'example\.com', "Example.com placeholder domain"),
        ]

        # ERROR-level placeholders - these mean the file is NOT SELLABLE
        error_placeholders = [
            # LLM bracket placeholders
            (r'\[PDF containing[^\]]*\]', "LLM placeholder - PDF not actually created"),
            (r'\[Image[^\]]*\]', "LLM placeholder - image not actually created"),
            (r'\[Insert[^\]]*\]', "LLM placeholder - content not provided"),
            (r'\[Add[^\]]*here\]', "LLM placeholder - content not provided"),
            (r'\[Your[^\]]*\]', "LLM placeholder - user content not templated properly"),
            # HTML comment abbreviations - catch all "repeat" patterns
            (r'<!--\s*repeat\s+', "HTML abbreviation - content not expanded"),
            (r'<!--\s*similar\s+', "HTML abbreviation - content not expanded"),
            (r'<!--\s*\d+\s+more', "HTML abbreviation - content not expanded"),
            (r'<!--\s*add\s+more\s+\w+\s+as\s+needed', "HTML abbreviation - incomplete content"),
            (r'<!--\s*end\s+of\s+.*block', "HTML abbreviation - single block instead of multiple"),
            (r'<!--\s*remaining\s+\d+', "HTML abbreviation - not all items created"),
            (r'<!--\s*(continue|etc|and\s+so\s+on)', "HTML abbreviation - incomplete"),
            # Numbered placeholder patterns
            (r'(ingredient|step|item|task)\s*[1-3]\b(?![\w\d])', "Generic numbered placeholder"),
            (r'recipe\s+title\b', "Generic title placeholder"),
            # Ellipsis abbreviations
            (r'\.{3}\s*(repeat|similar|more|etc)', "LLM abbreviation - content not complete"),
            # "for the remaining X" patterns
            (r'for\s+the\s+remaining\s+\d+', "LLM abbreviation - not all items created"),
        ]

        for pattern, message in error_placeholders:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                self.issues.append(ValidationIssue(
                    severity="error",
                    file=filename,
                    line=None,
                    message=f"NOT SELLABLE: {message}",
                    code="SELLABILITY_PLACEHOLDER"
                ))

        for pattern, message in warning_placeholders:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                self.issues.append(ValidationIssue(
                    severity="warning",
                    file=filename,
                    line=None,
                    message=message,
                    code="PLACEHOLDER_CONTENT"
                ))

    def _generate_summary(self) -> str:
        """Generate a human-readable summary."""
        if not self.issues:
            return "All validation checks passed."

        errors = self.error_count
        warnings = sum(1 for i in self.issues if i.severity == "warning")

        parts = []
        if errors:
            parts.append(f"{errors} error{'s' if errors != 1 else ''}")
        if warnings:
            parts.append(f"{warnings} warning{'s' if warnings != 1 else ''}")

        return f"Found {', '.join(parts)}."


def validate_code(files: dict[str, str], mason_output: str = "") -> ValidationResult:
    """Convenience function to validate code files."""
    validator = CodeValidator()
    return validator.validate(files, mason_output)
