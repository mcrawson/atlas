"""Test Runner - Runs actual tests for ATLAS projects."""

import subprocess
import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class TestFramework(Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    JEST = "jest"
    MOCHA = "mocha"
    VITEST = "vitest"
    GO_TEST = "go_test"
    CARGO_TEST = "cargo_test"
    UNKNOWN = "unknown"


@dataclass
class TestResult:
    """Result of running tests."""
    success: bool
    framework: TestFramework
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total: int = 0
    duration: float = 0.0
    output: str = ""
    error: str = ""
    failed_tests: list[str] = field(default_factory=list)


class TestRunner:
    """Runs tests for various project types."""

    def __init__(self, project_dir: Path):
        """Initialize test runner.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = Path(project_dir)

    def detect_framework(self) -> TestFramework:
        """Detect the test framework used by the project.

        Returns:
            TestFramework enum value
        """
        # Check for Python (pytest)
        if (self.project_dir / "pytest.ini").exists() or \
           (self.project_dir / "pyproject.toml").exists() or \
           (self.project_dir / "setup.py").exists() or \
           list(self.project_dir.glob("**/test_*.py")) or \
           list(self.project_dir.glob("**/*_test.py")):
            return TestFramework.PYTEST

        # Check for JavaScript/TypeScript
        package_json = self.project_dir / "package.json"
        if package_json.exists():
            try:
                pkg = json.loads(package_json.read_text())
                scripts = pkg.get("scripts", {})
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                if "vitest" in deps:
                    return TestFramework.VITEST
                if "jest" in deps:
                    return TestFramework.JEST
                if "mocha" in deps:
                    return TestFramework.MOCHA
            except Exception:
                pass

        # Check for Go
        if list(self.project_dir.glob("**/*_test.go")):
            return TestFramework.GO_TEST

        # Check for Rust
        if (self.project_dir / "Cargo.toml").exists():
            return TestFramework.CARGO_TEST

        return TestFramework.UNKNOWN

    def run(self, framework: Optional[TestFramework] = None) -> TestResult:
        """Run tests using the detected or specified framework.

        Args:
            framework: Optional framework to use (auto-detect if None)

        Returns:
            TestResult with details
        """
        if framework is None:
            framework = self.detect_framework()

        if framework == TestFramework.UNKNOWN:
            return TestResult(
                success=False,
                framework=framework,
                error="Could not detect test framework",
            )

        runners = {
            TestFramework.PYTEST: self._run_pytest,
            TestFramework.JEST: self._run_jest,
            TestFramework.VITEST: self._run_vitest,
            TestFramework.MOCHA: self._run_mocha,
            TestFramework.GO_TEST: self._run_go_test,
            TestFramework.CARGO_TEST: self._run_cargo_test,
        }

        runner = runners.get(framework)
        if runner:
            return runner()

        return TestResult(
            success=False,
            framework=framework,
            error=f"No runner implemented for {framework.value}",
        )

    def _run_command(self, cmd: list[str], timeout: int = 120) -> tuple[bool, str, str]:
        """Run a command and return results.

        Args:
            cmd: Command to run
            timeout: Timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return (
                result.returncode == 0,
                result.stdout,
                result.stderr,
            )
        except subprocess.TimeoutExpired:
            return False, "", f"Test timed out after {timeout} seconds"
        except FileNotFoundError as e:
            return False, "", f"Command not found: {cmd[0]}"
        except Exception as e:
            return False, "", str(e)

    def _run_pytest(self) -> TestResult:
        """Run pytest tests."""
        success, stdout, stderr = self._run_command([
            "python", "-m", "pytest", "-v", "--tb=short"
        ])

        result = TestResult(
            success=success,
            framework=TestFramework.PYTEST,
            output=stdout,
            error=stderr,
        )

        # Parse pytest output
        for line in stdout.split("\n"):
            if " passed" in line or " failed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        try:
                            result.passed = int(parts[i-1])
                        except ValueError:
                            pass
                    if part == "failed" and i > 0:
                        try:
                            result.failed = int(parts[i-1])
                        except ValueError:
                            pass
                    if part == "skipped" and i > 0:
                        try:
                            result.skipped = int(parts[i-1])
                        except ValueError:
                            pass

        result.total = result.passed + result.failed + result.skipped
        return result

    def _run_jest(self) -> TestResult:
        """Run Jest tests."""
        success, stdout, stderr = self._run_command([
            "npx", "jest", "--json", "--outputFile=/tmp/jest-results.json"
        ])

        result = TestResult(
            success=success,
            framework=TestFramework.JEST,
            output=stdout,
            error=stderr,
        )

        # Try to parse JSON output
        try:
            json_path = Path("/tmp/jest-results.json")
            if json_path.exists():
                data = json.loads(json_path.read_text())
                result.passed = data.get("numPassedTests", 0)
                result.failed = data.get("numFailedTests", 0)
                result.total = data.get("numTotalTests", 0)
                result.skipped = result.total - result.passed - result.failed
        except Exception:
            pass

        return result

    def _run_vitest(self) -> TestResult:
        """Run Vitest tests."""
        success, stdout, stderr = self._run_command([
            "npx", "vitest", "run"
        ])

        result = TestResult(
            success=success,
            framework=TestFramework.VITEST,
            output=stdout,
            error=stderr,
        )

        # Parse vitest output
        for line in stdout.split("\n"):
            if "Tests" in line and ("passed" in line or "failed" in line):
                # Parse: "Tests  2 passed (2)"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        try:
                            result.passed = int(parts[i-1])
                        except ValueError:
                            pass
                    if part == "failed" and i > 0:
                        try:
                            result.failed = int(parts[i-1])
                        except ValueError:
                            pass

        result.total = result.passed + result.failed
        return result

    def _run_mocha(self) -> TestResult:
        """Run Mocha tests."""
        success, stdout, stderr = self._run_command([
            "npx", "mocha", "--reporter", "spec"
        ])

        result = TestResult(
            success=success,
            framework=TestFramework.MOCHA,
            output=stdout,
            error=stderr,
        )

        # Parse mocha output
        for line in stdout.split("\n"):
            if "passing" in line:
                parts = line.split()
                if parts:
                    try:
                        result.passed = int(parts[0])
                    except ValueError:
                        pass
            if "failing" in line:
                parts = line.split()
                if parts:
                    try:
                        result.failed = int(parts[0])
                    except ValueError:
                        pass

        result.total = result.passed + result.failed
        return result

    def _run_go_test(self) -> TestResult:
        """Run Go tests."""
        success, stdout, stderr = self._run_command([
            "go", "test", "-v", "./..."
        ])

        result = TestResult(
            success=success,
            framework=TestFramework.GO_TEST,
            output=stdout,
            error=stderr,
        )

        # Parse go test output
        for line in stdout.split("\n"):
            if line.startswith("--- PASS:"):
                result.passed += 1
            elif line.startswith("--- FAIL:"):
                result.failed += 1
            elif line.startswith("--- SKIP:"):
                result.skipped += 1

        result.total = result.passed + result.failed + result.skipped
        return result

    def _run_cargo_test(self) -> TestResult:
        """Run Rust/Cargo tests."""
        success, stdout, stderr = self._run_command([
            "cargo", "test"
        ])

        result = TestResult(
            success=success,
            framework=TestFramework.CARGO_TEST,
            output=stdout + stderr,  # Cargo outputs to both
            error="",
        )

        # Parse cargo test output
        # Look for: "test result: ok. 5 passed; 0 failed; 0 ignored"
        for line in (stdout + stderr).split("\n"):
            if "test result:" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed;" and i > 0:
                        try:
                            result.passed = int(parts[i-1])
                        except ValueError:
                            pass
                    if part == "failed;" and i > 0:
                        try:
                            result.failed = int(parts[i-1])
                        except ValueError:
                            pass
                    if part == "ignored" and i > 0:
                        try:
                            result.skipped = int(parts[i-1])
                        except ValueError:
                            pass

        result.total = result.passed + result.failed + result.skipped
        return result

    def get_test_summary(self, result: TestResult) -> str:
        """Generate a human-readable test summary.

        Args:
            result: TestResult to summarize

        Returns:
            Formatted summary string
        """
        if not result.success and result.total == 0:
            return f"Failed to run tests: {result.error}"

        emoji = "✅" if result.success else "❌"
        status = "PASSED" if result.success else "FAILED"

        summary = f"""
{emoji} Tests {status}

Framework: {result.framework.value}
Total: {result.total}
  ✅ Passed:  {result.passed}
  ❌ Failed:  {result.failed}
  ⏭️  Skipped: {result.skipped}
"""

        if result.failed_tests:
            summary += "\nFailed tests:\n"
            for test in result.failed_tests:
                summary += f"  - {test}\n"

        return summary.strip()
