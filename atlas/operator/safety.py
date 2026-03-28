"""
Safety Layer for Overnight Autonomous Operations.

Prevents destructive actions, enforces time windows, manages git branches,
and ensures rate limiting.
"""

import asyncio
import logging
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from atlas.operator.config import OvernightConfig

logger = logging.getLogger(__name__)


class SafetyViolation(Exception):
    """Raised when a safety check fails."""
    pass


class SafetyLayer:
    """
    Enforces safety guardrails for autonomous overnight operations.

    Guardrails:
    - Time window enforcement (only run overnight)
    - Git branch management (never commit to main)
    - Command whitelisting
    - Rate limiting
    - Test requirements for code changes
    """

    def __init__(self, config: OvernightConfig):
        self.config = config
        self._last_request_time: Optional[datetime] = None
        self._request_count = 0
        self._consecutive_errors = 0
        self._session_start: Optional[datetime] = None

    # --- Time Window ---

    def is_in_window(self) -> bool:
        """Check if current time is within the overnight window."""
        now = datetime.now()
        hour = now.hour

        start = self.config.schedule.start_hour
        end = self.config.schedule.end_hour

        # Handle overnight wrap (e.g., 23 to 6)
        if start > end:
            return hour >= start or hour < end
        else:
            return start <= hour < end

    def check_window(self) -> None:
        """Raise if not in overnight window."""
        if not self.is_in_window():
            raise SafetyViolation(
                f"Outside overnight window ({self.config.schedule.start_hour}:00 - "
                f"{self.config.schedule.end_hour}:00). Use --force to override."
            )

    def check_runtime(self) -> None:
        """Check if session has exceeded max runtime."""
        if self._session_start is None:
            return

        elapsed = datetime.now() - self._session_start
        max_runtime = timedelta(minutes=self.config.limits.max_runtime_minutes)

        if elapsed > max_runtime:
            raise SafetyViolation(
                f"Session exceeded max runtime of {self.config.limits.max_runtime_minutes} minutes"
            )

    def start_session(self) -> None:
        """Mark session start for runtime tracking."""
        self._session_start = datetime.now()
        self._request_count = 0
        self._consecutive_errors = 0

    # --- Rate Limiting ---

    async def wait_for_rate_limit(self) -> None:
        """Wait if needed to respect rate limits."""
        if self._last_request_time is None:
            self._last_request_time = datetime.now()
            return

        min_delay = timedelta(seconds=self.config.limits.min_delay_seconds)
        elapsed = datetime.now() - self._last_request_time

        if elapsed < min_delay:
            wait_time = (min_delay - elapsed).total_seconds()
            logger.debug(f"Rate limiting: waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)

        self._last_request_time = datetime.now()
        self._request_count += 1

    def check_rate_limit(self) -> bool:
        """Check if we're within rate limits (non-blocking check)."""
        if self._last_request_time is None:
            return True

        min_delay = timedelta(seconds=self.config.limits.min_delay_seconds)
        elapsed = datetime.now() - self._last_request_time
        return elapsed >= min_delay

    # --- Error Tracking ---

    def record_error(self) -> None:
        """Record a consecutive error."""
        self._consecutive_errors += 1

    def record_success(self) -> None:
        """Reset consecutive error count on success."""
        self._consecutive_errors = 0

    def check_error_threshold(self) -> None:
        """Check if we've exceeded the error threshold."""
        if self._consecutive_errors >= self.config.limits.max_consecutive_errors:
            raise SafetyViolation(
                f"Exceeded max consecutive errors ({self.config.limits.max_consecutive_errors})"
            )

    # --- Task Limits ---

    def check_task_limit(self, completed: int) -> None:
        """Check if we've hit the task limit."""
        if completed >= self.config.limits.max_tasks:
            raise SafetyViolation(
                f"Reached max tasks limit ({self.config.limits.max_tasks})"
            )

    # --- Git Safety ---

    def get_current_branch(self, repo_path: Path) -> str:
        """Get current git branch name."""
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def is_on_main(self, repo_path: Path) -> bool:
        """Check if on main/master branch."""
        branch = self.get_current_branch(repo_path)
        return branch in ("main", "master")

    def is_overnight_branch(self, branch: str) -> bool:
        """Check if branch is an overnight-created branch."""
        return branch.startswith(self.config.safety.branch_prefix)

    async def create_branch(self, repo_path: Path, name: str) -> str:
        """
        Create and checkout a new branch for overnight work.

        Returns the full branch name.
        """
        # Ensure we start from main/master
        current = self.get_current_branch(repo_path)
        if not self.is_on_main(repo_path) and not self.is_overnight_branch(current):
            # Stash any changes first
            subprocess.run(["git", "stash"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "checkout", "main"], cwd=repo_path, capture_output=True)

        # Pull latest
        subprocess.run(["git", "pull", "--rebase"], cwd=repo_path, capture_output=True)

        # Create new branch
        branch_name = f"{self.config.safety.branch_prefix}{name}"
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # Branch might already exist, try to check it out
            result = subprocess.run(
                ["git", "checkout", branch_name],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise SafetyViolation(f"Failed to create/checkout branch: {result.stderr}")

        logger.info(f"Created/switched to branch: {branch_name}")
        return branch_name

    def can_commit(self, repo_path: Path, changed_files: list[str]) -> tuple[bool, str]:
        """
        Check if the proposed changes are safe to commit.

        Returns (is_safe, reason).
        """
        # Never commit on main/master
        if self.is_on_main(repo_path):
            return False, "Cannot commit on main/master branch"

        # Check for protected files
        protected_patterns = [
            r"\.env",
            r"credentials",
            r"secrets?\.ya?ml",
            r"\.pem$",
            r"\.key$",
        ]

        for file in changed_files:
            for pattern in protected_patterns:
                if re.search(pattern, file, re.IGNORECASE):
                    return False, f"Protected file pattern: {file}"

        return True, "OK"

    async def run_tests(self, repo_path: Path, test_path: Optional[str] = None) -> tuple[bool, str]:
        """
        Run tests and return (passed, output).
        """
        cmd = ["python", "-m", "pytest"]
        if test_path:
            cmd.append(test_path)
        cmd.extend(["-v", "--tb=short"])

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        passed = result.returncode == 0
        output = result.stdout + result.stderr
        return passed, output

    # --- Command Safety ---

    def is_safe_command(self, cmd: str) -> bool:
        """Check if a command is allowed."""
        # Check blocked patterns
        for blocked in self.config.safety.blocked_patterns:
            if blocked in cmd:
                logger.warning(f"Blocked command pattern: {blocked}")
                return False

        # Check if it matches allowed patterns
        for allowed in self.config.safety.allowed_commands:
            if cmd.startswith(allowed):
                return True

        # Allow read-only git commands
        safe_git = [
            "git status",
            "git log",
            "git diff",
            "git show",
            "git branch",
            "git stash list",
        ]
        for safe in safe_git:
            if cmd.startswith(safe):
                return True

        # Allow python script execution (careful)
        if cmd.startswith("python ") or cmd.startswith("python3 "):
            # But not with suspicious flags
            if "-c" in cmd:
                return False
            return True

        return False

    async def safe_execute(self, cmd: str, cwd: Optional[Path] = None) -> tuple[int, str, str]:
        """
        Execute a command if it passes safety checks.

        Returns (returncode, stdout, stderr).
        """
        if not self.is_safe_command(cmd):
            raise SafetyViolation(f"Command not in allowed list: {cmd}")

        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )

        return result.returncode, result.stdout, result.stderr

    # --- Composite Checks ---

    def full_preflight_check(self, completed_tasks: int = 0, force: bool = False) -> None:
        """
        Run all preflight safety checks.

        Raises SafetyViolation if any check fails.
        """
        if not force:
            self.check_window()

        self.check_runtime()
        self.check_error_threshold()
        self.check_task_limit(completed_tasks)
