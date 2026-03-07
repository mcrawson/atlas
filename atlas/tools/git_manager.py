"""Git Manager - Handles git operations for ATLAS projects."""

import subprocess
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class GitResult:
    """Result of a git operation."""
    success: bool
    message: str = ""
    output: str = ""
    error: str = ""


class GitManager:
    """Manages git operations for ATLAS projects."""

    def __init__(self, project_dir: Path):
        """Initialize git manager.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = Path(project_dir)

    def _run_git(self, *args: str) -> GitResult:
        """Run a git command.

        Args:
            *args: Git command arguments

        Returns:
            GitResult with output
        """
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            return GitResult(
                success=result.returncode == 0,
                output=result.stdout.strip(),
                error=result.stderr.strip(),
            )

        except subprocess.TimeoutExpired:
            return GitResult(success=False, error="Git command timed out")
        except FileNotFoundError:
            return GitResult(success=False, error="Git is not installed")
        except Exception as e:
            return GitResult(success=False, error=str(e))

    def is_git_repo(self) -> bool:
        """Check if the project is a git repository."""
        git_dir = self.project_dir / ".git"
        return git_dir.exists()

    def init(self, initial_branch: str = "main") -> GitResult:
        """Initialize a new git repository.

        Args:
            initial_branch: Name of the initial branch

        Returns:
            GitResult
        """
        if self.is_git_repo():
            return GitResult(success=True, message="Already a git repository")

        result = self._run_git("init", "-b", initial_branch)
        if result.success:
            result.message = f"Initialized git repository with branch '{initial_branch}'"

            # Create .gitignore
            self._create_gitignore()

        return result

    def _create_gitignore(self):
        """Create a default .gitignore file."""
        gitignore_content = """# Dependencies
node_modules/
venv/
__pycache__/
*.pyc
.env

# Build outputs
dist/
build/
*.egg-info/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Testing
coverage/
.pytest_cache/
"""
        gitignore_path = self.project_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(gitignore_content)

    def status(self) -> GitResult:
        """Get git status."""
        return self._run_git("status", "--short")

    def add(self, *files: str) -> GitResult:
        """Stage files for commit.

        Args:
            *files: Files to stage. If empty, stages all changes.

        Returns:
            GitResult
        """
        if not files:
            return self._run_git("add", "-A")
        return self._run_git("add", *files)

    def commit(
        self,
        message: str,
        description: Optional[str] = None,
    ) -> GitResult:
        """Create a commit.

        Args:
            message: Commit message (first line)
            description: Optional longer description

        Returns:
            GitResult
        """
        # Build full commit message
        full_message = message
        if description:
            full_message += f"\n\n{description}"

        # Add ATLAS signature
        full_message += "\n\n🔨 Built with ATLAS"

        result = self._run_git("commit", "-m", full_message)
        if result.success:
            result.message = f"Committed: {message}"

        return result

    def auto_commit(
        self,
        task_description: str,
        files_changed: list[str],
    ) -> GitResult:
        """Automatically stage and commit changes.

        Args:
            task_description: Description of what was done
            files_changed: List of files that were changed

        Returns:
            GitResult
        """
        # Initialize if needed
        if not self.is_git_repo():
            init_result = self.init()
            if not init_result.success:
                return init_result

        # Stage all changes
        add_result = self.add()
        if not add_result.success:
            return add_result

        # Check if there are changes to commit
        status_result = self.status()
        if not status_result.output.strip():
            return GitResult(success=True, message="No changes to commit")

        # Generate commit message
        commit_msg = self._generate_commit_message(task_description, files_changed)

        # Commit
        return self.commit(commit_msg["title"], commit_msg["body"])

    def _generate_commit_message(
        self,
        task_description: str,
        files_changed: list[str],
    ) -> dict:
        """Generate a descriptive commit message.

        Args:
            task_description: What was done
            files_changed: List of files changed

        Returns:
            Dict with 'title' and 'body'
        """
        # Determine commit type based on files
        if any("test" in f.lower() for f in files_changed):
            prefix = "test"
        elif any(f.endswith(".md") for f in files_changed):
            prefix = "docs"
        elif any("fix" in task_description.lower()):
            prefix = "fix"
        elif any(f in ["package.json", "requirements.txt", "pyproject.toml"] for f in files_changed):
            prefix = "chore"
        else:
            prefix = "feat"

        # Shorten task description for title
        title = task_description[:50]
        if len(task_description) > 50:
            title = title.rsplit(' ', 1)[0] + "..."

        title = f"{prefix}: {title}"

        # Build body
        body_lines = ["Files changed:"]
        for f in files_changed[:10]:  # Limit to 10 files
            body_lines.append(f"  - {f}")
        if len(files_changed) > 10:
            body_lines.append(f"  - ... and {len(files_changed) - 10} more")

        return {
            "title": title,
            "body": "\n".join(body_lines),
        }

    def log(self, count: int = 5) -> GitResult:
        """Get recent commits.

        Args:
            count: Number of commits to show

        Returns:
            GitResult with log output
        """
        return self._run_git("log", f"-{count}", "--oneline")

    def diff(self, staged: bool = False) -> GitResult:
        """Get diff of changes.

        Args:
            staged: If True, show staged changes

        Returns:
            GitResult with diff output
        """
        if staged:
            return self._run_git("diff", "--staged")
        return self._run_git("diff")

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = self._run_git("branch", "--show-current")
        return result.output if result.success else "unknown"

    def create_branch(self, branch_name: str) -> GitResult:
        """Create and switch to a new branch.

        Args:
            branch_name: Name of the new branch

        Returns:
            GitResult
        """
        result = self._run_git("checkout", "-b", branch_name)
        if result.success:
            result.message = f"Created and switched to branch '{branch_name}'"
        return result
