"""Git repository monitoring for ATLAS - repo changes, PR status, CI failures."""

import subprocess
from pathlib import Path
from typing import List, Optional
import logging

from .monitor import Monitor, Alert, AlertSeverity

logger = logging.getLogger("atlas.monitoring.git")


class GitMonitor(Monitor):
    """Monitor git repositories for changes and issues."""

    name = "git"
    check_interval = 600  # 10 minutes

    def __init__(
        self,
        repos: List[str] = None,
        check_uncommitted: bool = True,
        check_unpushed: bool = True,
        check_stash: bool = True,
        **kwargs
    ):
        """Initialize git monitor.

        Args:
            repos: List of repository paths to monitor
            check_uncommitted: Alert on uncommitted changes
            check_unpushed: Alert on unpushed commits
            check_stash: Alert if stash is not empty
        """
        super().__init__(**kwargs)
        self.repos = [Path(r).expanduser() for r in (repos or [])]
        self.check_uncommitted = check_uncommitted
        self.check_unpushed = check_unpushed
        self.check_stash = check_stash

    async def check(self) -> List[Alert]:
        """Check git repositories.

        Returns:
            List of alerts for any issues
        """
        alerts = []

        for repo_path in self.repos:
            if not repo_path.exists():
                continue

            if not (repo_path / ".git").exists():
                continue

            repo_alerts = await self._check_repo(repo_path)
            alerts.extend(repo_alerts)

        return alerts

    async def _check_repo(self, repo_path: Path) -> List[Alert]:
        """Check a single repository.

        Args:
            repo_path: Path to the repository

        Returns:
            List of alerts for this repo
        """
        alerts = []
        repo_name = repo_path.name

        # Check for uncommitted changes
        if self.check_uncommitted:
            uncommitted = self._get_uncommitted_changes(repo_path)
            if uncommitted:
                alerts.append(Alert(
                    monitor_name=self.name,
                    severity=AlertSeverity.INFO,
                    message=f"you have uncommitted changes in {repo_name} ({uncommitted['modified']} modified, {uncommitted['untracked']} untracked).",
                    action_suggestion="Shall I prepare a commit summary?",
                    data={"repo": str(repo_path), **uncommitted},
                ))

        # Check for unpushed commits
        if self.check_unpushed:
            unpushed = self._get_unpushed_count(repo_path)
            if unpushed and unpushed > 0:
                severity = AlertSeverity.WARNING if unpushed >= 5 else AlertSeverity.INFO
                alerts.append(Alert(
                    monitor_name=self.name,
                    severity=severity,
                    message=f"you have {unpushed} unpushed commit{'s' if unpushed > 1 else ''} in {repo_name}.",
                    action_suggestion="Would you like to push these changes?",
                    data={"repo": str(repo_path), "unpushed_count": unpushed},
                ))

        # Check stash
        if self.check_stash:
            stash_count = self._get_stash_count(repo_path)
            if stash_count and stash_count > 0:
                alerts.append(Alert(
                    monitor_name=self.name,
                    severity=AlertSeverity.INFO,
                    message=f"you have {stash_count} stashed change{'s' if stash_count > 1 else ''} in {repo_name}.",
                    action_suggestion="These may be work you've forgotten about, sir.",
                    data={"repo": str(repo_path), "stash_count": stash_count},
                ))

        # Check if behind remote
        behind = self._check_behind_remote(repo_path)
        if behind and behind > 0:
            alerts.append(Alert(
                monitor_name=self.name,
                severity=AlertSeverity.INFO,
                message=f"{repo_name} is {behind} commit{'s' if behind > 1 else ''} behind the remote.",
                action_suggestion="You may want to pull the latest changes.",
                data={"repo": str(repo_path), "behind_count": behind},
            ))

        return alerts

    def _run_git(self, repo_path: Path, *args) -> Optional[str]:
        """Run a git command in a repo.

        Args:
            repo_path: Repository path
            *args: Git command arguments

        Returns:
            Command output or None on failure
        """
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path)] + list(args),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.debug(f"Git command failed in {repo_path}: {e}")
        return None

    def _get_uncommitted_changes(self, repo_path: Path) -> Optional[dict]:
        """Get uncommitted changes count.

        Args:
            repo_path: Repository path

        Returns:
            Dict with modified/untracked counts, or None
        """
        status = self._run_git(repo_path, "status", "--porcelain")
        if status is None:
            return None

        if not status:
            return None

        modified = 0
        untracked = 0

        for line in status.split("\n"):
            if line.startswith("??"):
                untracked += 1
            elif line.strip():
                modified += 1

        if modified == 0 and untracked == 0:
            return None

        return {"modified": modified, "untracked": untracked}

    def _get_unpushed_count(self, repo_path: Path) -> Optional[int]:
        """Get count of unpushed commits.

        Args:
            repo_path: Repository path

        Returns:
            Number of unpushed commits, or None
        """
        # Get current branch
        branch = self._run_git(repo_path, "branch", "--show-current")
        if not branch:
            return None

        # Check if tracking remote
        remote = self._run_git(repo_path, "config", f"branch.{branch}.remote")
        if not remote:
            return None

        # Count commits ahead
        count = self._run_git(
            repo_path,
            "rev-list",
            "--count",
            f"{remote}/{branch}..HEAD"
        )

        if count:
            try:
                return int(count)
            except ValueError:
                pass

        return None

    def _get_stash_count(self, repo_path: Path) -> Optional[int]:
        """Get stash count.

        Args:
            repo_path: Repository path

        Returns:
            Number of stash entries, or None
        """
        stash_list = self._run_git(repo_path, "stash", "list")
        if stash_list is None:
            return None

        if not stash_list:
            return 0

        return len(stash_list.split("\n"))

    def _check_behind_remote(self, repo_path: Path) -> Optional[int]:
        """Check how far behind remote.

        Args:
            repo_path: Repository path

        Returns:
            Number of commits behind, or None
        """
        # Fetch latest (quietly)
        self._run_git(repo_path, "fetch", "--quiet")

        # Get current branch
        branch = self._run_git(repo_path, "branch", "--show-current")
        if not branch:
            return None

        # Check if tracking remote
        remote = self._run_git(repo_path, "config", f"branch.{branch}.remote")
        if not remote:
            return None

        # Count commits behind
        count = self._run_git(
            repo_path,
            "rev-list",
            "--count",
            f"HEAD..{remote}/{branch}"
        )

        if count:
            try:
                return int(count)
            except ValueError:
                pass

        return None

    def get_repo_summary(self, repo_path: Path) -> dict:
        """Get a summary of repository status.

        Args:
            repo_path: Repository path

        Returns:
            Status summary dictionary
        """
        repo_path = Path(repo_path).expanduser()

        if not repo_path.exists() or not (repo_path / ".git").exists():
            return {"error": "Not a git repository"}

        summary = {
            "path": str(repo_path),
            "name": repo_path.name,
        }

        # Current branch
        branch = self._run_git(repo_path, "branch", "--show-current")
        summary["branch"] = branch or "unknown"

        # Last commit
        last_commit = self._run_git(
            repo_path,
            "log", "-1", "--format=%s (%ar)"
        )
        summary["last_commit"] = last_commit or "unknown"

        # Status
        uncommitted = self._get_uncommitted_changes(repo_path)
        summary["uncommitted_changes"] = uncommitted or {"modified": 0, "untracked": 0}

        unpushed = self._get_unpushed_count(repo_path)
        summary["unpushed_commits"] = unpushed or 0

        stash = self._get_stash_count(repo_path)
        summary["stash_count"] = stash or 0

        return summary
