"""
ATLAS Transporter - GitHub Issues Bidirectional Sync.

Main sync class that handles bidirectional synchronization between
ATLAS tasks and GitHub Issues, like Jason Statham transporting goods
efficiently between two worlds.

Features:
- Sync ATLAS tasks to GitHub Issues
- Sync GitHub Issues to ATLAS tasks
- Post agent outputs as issue comments
- Manual linking of existing tasks/issues
- Full sync of all linked items
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from .models import (
    TransporterConfig,
    SyncMapping,
    SyncState,
    SyncStatus,
    SyncDirection,
    SyncResult,
    GitHubIssueData,
)
from .api import GitHubAPI, get_github_api
from atlas.projects.models import TaskStatus

logger = logging.getLogger(__name__)

# Singleton instance
_transporter: Optional["Transporter"] = None


def get_transporter(
    project_manager=None,
    agent_manager=None,
    config: Optional[TransporterConfig] = None,
) -> "Transporter":
    """Get or create the global Transporter instance.

    Args:
        project_manager: ATLAS ProjectManager instance
        agent_manager: ATLAS AgentManager instance (for output posting)
        config: Configuration

    Returns:
        Transporter instance
    """
    global _transporter
    if _transporter is None:
        _transporter = Transporter(
            project_manager=project_manager,
            agent_manager=agent_manager,
            config=config,
        )
    return _transporter


class Transporter:
    """Bidirectional sync between ATLAS tasks and GitHub Issues.

    The Transporter moves tasks between ATLAS and GitHub like
    a professional driver - fast, reliable, and without drama.
    """

    def __init__(
        self,
        project_manager=None,
        agent_manager=None,
        config: Optional[TransporterConfig] = None,
    ):
        """Initialize the Transporter.

        Args:
            project_manager: ATLAS ProjectManager instance
            agent_manager: ATLAS AgentManager instance
            config: Configuration
        """
        self.config = config or TransporterConfig.from_env()
        self.project_manager = project_manager
        self.agent_manager = agent_manager
        self.api = get_github_api(self.config)

        # Sync state
        self._sync_state = SyncState()

    def update_managers(
        self,
        project_manager=None,
        agent_manager=None,
    ):
        """Update manager references (for late binding).

        Args:
            project_manager: ATLAS ProjectManager instance
            agent_manager: ATLAS AgentManager instance
        """
        if project_manager is not None:
            self.project_manager = project_manager
        if agent_manager is not None:
            self.agent_manager = agent_manager

    # Sync operations

    async def sync_task_to_github(
        self,
        task_id: int,
        repo: Optional[str] = None,
        create_if_missing: bool = True,
    ) -> SyncResult:
        """Sync an ATLAS task to GitHub as an issue.

        Args:
            task_id: ATLAS task ID
            repo: Repository in "owner/repo" format (uses default if not provided)
            create_if_missing: Create issue if not linked

        Returns:
            SyncResult with outcome
        """
        if not self.project_manager:
            return SyncResult(
                success=False,
                direction=SyncDirection.ATLAS_TO_GITHUB,
                atlas_task_id=task_id,
                error="Project manager not initialized",
                message="Cannot sync without project manager",
            )

        repo = repo or self.config.default_repo
        if not repo:
            return SyncResult(
                success=False,
                direction=SyncDirection.ATLAS_TO_GITHUB,
                atlas_task_id=task_id,
                error="No repository specified",
                message="Provide repo parameter or set ATLAS_GITHUB_DEFAULT_REPO",
            )

        try:
            # Get the task
            task = await self.project_manager.get_task(task_id)
            if not task:
                return SyncResult(
                    success=False,
                    direction=SyncDirection.ATLAS_TO_GITHUB,
                    atlas_task_id=task_id,
                    error=f"Task {task_id} not found",
                    message="Task does not exist",
                )

            # Check for existing mapping
            mapping = await self.get_mapping_by_task(task_id)

            if mapping:
                # Update existing issue
                logger.info(f"Updating GitHub issue {mapping.github_repo}#{mapping.github_issue_number} from task {task_id}")
                issue = await self._update_issue_from_task(task, mapping)
                mapping.last_sync = datetime.now()
                mapping.sync_status = SyncStatus.SYNCED
                await self._save_mapping(mapping)

                return SyncResult(
                    success=True,
                    direction=SyncDirection.ATLAS_TO_GITHUB,
                    atlas_task_id=task_id,
                    github_repo=mapping.github_repo,
                    github_issue_number=mapping.github_issue_number,
                    url=issue.html_url,
                    message="Issue updated",
                )
            elif create_if_missing:
                # Create new issue
                logger.info(f"Creating GitHub issue for task {task_id} in {repo}")
                issue = await self._create_issue_from_task(task, repo)

                # Create mapping
                mapping = SyncMapping(
                    atlas_task_id=task_id,
                    github_repo=repo,
                    github_issue_number=issue.number,
                    last_sync=datetime.now(),
                    sync_status=SyncStatus.SYNCED,
                    atlas_updated_at=task.updated_at,
                    github_updated_at=issue.updated_at,
                )
                await self._save_mapping(mapping)

                return SyncResult(
                    success=True,
                    direction=SyncDirection.ATLAS_TO_GITHUB,
                    atlas_task_id=task_id,
                    github_repo=repo,
                    github_issue_number=issue.number,
                    url=issue.html_url,
                    message="Issue created",
                )
            else:
                return SyncResult(
                    success=False,
                    direction=SyncDirection.ATLAS_TO_GITHUB,
                    atlas_task_id=task_id,
                    error="No existing mapping and create_if_missing=False",
                    message="Task not linked to GitHub issue",
                )

        except Exception as e:
            logger.exception(f"Error syncing task {task_id} to GitHub: {e}")
            return SyncResult(
                success=False,
                direction=SyncDirection.ATLAS_TO_GITHUB,
                atlas_task_id=task_id,
                error=str(e),
                message="Sync failed",
            )

    async def sync_issue_to_atlas(
        self,
        repo: str,
        issue_number: int,
        project_id: Optional[int] = None,
        create_if_missing: bool = True,
    ) -> SyncResult:
        """Sync a GitHub issue to ATLAS as a task.

        Args:
            repo: Repository in "owner/repo" format
            issue_number: GitHub issue number
            project_id: ATLAS project ID (creates default if not provided)
            create_if_missing: Create task if not linked

        Returns:
            SyncResult with outcome
        """
        if not self.project_manager:
            return SyncResult(
                success=False,
                direction=SyncDirection.GITHUB_TO_ATLAS,
                github_repo=repo,
                github_issue_number=issue_number,
                error="Project manager not initialized",
                message="Cannot sync without project manager",
            )

        try:
            # Get the issue
            issue = await self.api.get_issue(repo, issue_number)
            if not issue:
                return SyncResult(
                    success=False,
                    direction=SyncDirection.GITHUB_TO_ATLAS,
                    github_repo=repo,
                    github_issue_number=issue_number,
                    error=f"Issue {repo}#{issue_number} not found",
                    message="Issue does not exist",
                )

            # Check for existing mapping
            mapping = await self.get_mapping_by_issue(repo, issue_number)

            if mapping:
                # Update existing task
                logger.info(f"Updating ATLAS task {mapping.atlas_task_id} from issue {repo}#{issue_number}")
                await self._update_task_from_issue(issue, mapping.atlas_task_id)
                mapping.last_sync = datetime.now()
                mapping.sync_status = SyncStatus.SYNCED
                mapping.github_updated_at = issue.updated_at
                await self._save_mapping(mapping)

                return SyncResult(
                    success=True,
                    direction=SyncDirection.GITHUB_TO_ATLAS,
                    atlas_task_id=mapping.atlas_task_id,
                    github_repo=repo,
                    github_issue_number=issue_number,
                    url=issue.html_url,
                    message="Task updated",
                )
            elif create_if_missing:
                # Create new task
                if not project_id:
                    # Get or create default project for GitHub issues
                    project_id = await self._get_or_create_github_project(repo)

                logger.info(f"Creating ATLAS task for issue {repo}#{issue_number} in project {project_id}")
                task = await self._create_task_from_issue(issue, project_id)

                # Create mapping
                mapping = SyncMapping(
                    atlas_task_id=task.id,
                    github_repo=repo,
                    github_issue_number=issue_number,
                    last_sync=datetime.now(),
                    sync_status=SyncStatus.SYNCED,
                    atlas_updated_at=task.updated_at,
                    github_updated_at=issue.updated_at,
                )
                await self._save_mapping(mapping)

                return SyncResult(
                    success=True,
                    direction=SyncDirection.GITHUB_TO_ATLAS,
                    atlas_task_id=task.id,
                    github_repo=repo,
                    github_issue_number=issue_number,
                    url=issue.html_url,
                    message="Task created",
                )
            else:
                return SyncResult(
                    success=False,
                    direction=SyncDirection.GITHUB_TO_ATLAS,
                    github_repo=repo,
                    github_issue_number=issue_number,
                    error="No existing mapping and create_if_missing=False",
                    message="Issue not linked to ATLAS task",
                )

        except Exception as e:
            logger.exception(f"Error syncing issue {repo}#{issue_number} to ATLAS: {e}")
            return SyncResult(
                success=False,
                direction=SyncDirection.GITHUB_TO_ATLAS,
                github_repo=repo,
                github_issue_number=issue_number,
                error=str(e),
                message="Sync failed",
            )

    async def post_agent_output(
        self,
        task_id: int,
        output: dict[str, Any],
        summary: Optional[str] = None,
    ) -> SyncResult:
        """Post agent output as a comment on linked GitHub issue.

        Args:
            task_id: ATLAS task ID
            output: Agent output dictionary
            summary: Optional summary to include

        Returns:
            SyncResult with outcome
        """
        mapping = await self.get_mapping_by_task(task_id)
        if not mapping:
            return SyncResult(
                success=False,
                direction=SyncDirection.ATLAS_TO_GITHUB,
                atlas_task_id=task_id,
                error="Task not linked to GitHub issue",
                message="Cannot post output without GitHub link",
            )

        try:
            # Format the comment
            comment_body = self._format_agent_output_comment(output, summary)

            # Post comment
            comment = await self.api.create_comment(
                repo=mapping.github_repo,
                issue_number=mapping.github_issue_number,
                body=comment_body,
            )

            logger.info(f"Posted agent output to {mapping.github_repo}#{mapping.github_issue_number}")

            return SyncResult(
                success=True,
                direction=SyncDirection.ATLAS_TO_GITHUB,
                atlas_task_id=task_id,
                github_repo=mapping.github_repo,
                github_issue_number=mapping.github_issue_number,
                url=comment.html_url,
                message="Agent output posted as comment",
            )

        except Exception as e:
            logger.exception(f"Error posting agent output: {e}")
            return SyncResult(
                success=False,
                direction=SyncDirection.ATLAS_TO_GITHUB,
                atlas_task_id=task_id,
                error=str(e),
                message="Failed to post agent output",
            )

    async def link_task_to_issue(
        self,
        task_id: int,
        repo: str,
        issue_number: int,
    ) -> SyncResult:
        """Manually link an ATLAS task to a GitHub issue.

        Args:
            task_id: ATLAS task ID
            repo: Repository in "owner/repo" format
            issue_number: GitHub issue number

        Returns:
            SyncResult with outcome
        """
        # Verify task exists
        if self.project_manager:
            task = await self.project_manager.get_task(task_id)
            if not task:
                return SyncResult(
                    success=False,
                    direction=SyncDirection.BIDIRECTIONAL,
                    atlas_task_id=task_id,
                    error=f"Task {task_id} not found",
                    message="Task does not exist",
                )

        # Verify issue exists
        issue = await self.api.get_issue(repo, issue_number)
        if not issue:
            return SyncResult(
                success=False,
                direction=SyncDirection.BIDIRECTIONAL,
                github_repo=repo,
                github_issue_number=issue_number,
                error=f"Issue {repo}#{issue_number} not found",
                message="Issue does not exist",
            )

        # Check for existing mappings
        existing_task_mapping = await self.get_mapping_by_task(task_id)
        if existing_task_mapping:
            return SyncResult(
                success=False,
                direction=SyncDirection.BIDIRECTIONAL,
                atlas_task_id=task_id,
                error="Task already linked to another issue",
                message=f"Task linked to {existing_task_mapping.github_repo}#{existing_task_mapping.github_issue_number}",
            )

        existing_issue_mapping = await self.get_mapping_by_issue(repo, issue_number)
        if existing_issue_mapping:
            return SyncResult(
                success=False,
                direction=SyncDirection.BIDIRECTIONAL,
                github_repo=repo,
                github_issue_number=issue_number,
                error="Issue already linked to another task",
                message=f"Issue linked to task {existing_issue_mapping.atlas_task_id}",
            )

        # Create mapping
        mapping = SyncMapping(
            atlas_task_id=task_id,
            github_repo=repo,
            github_issue_number=issue_number,
            last_sync=datetime.now(),
            sync_status=SyncStatus.SYNCED,
        )
        await self._save_mapping(mapping)

        # Add atlas-task label to issue
        try:
            await self.api.add_labels(repo, issue_number, [self.config.atlas_label])
        except Exception as e:
            logger.warning(f"Could not add label to issue: {e}")

        logger.info(f"Linked task {task_id} to issue {repo}#{issue_number}")

        return SyncResult(
            success=True,
            direction=SyncDirection.BIDIRECTIONAL,
            atlas_task_id=task_id,
            github_repo=repo,
            github_issue_number=issue_number,
            url=issue.html_url,
            message="Task linked to issue",
        )

    async def sync_all(self) -> list[SyncResult]:
        """Sync all linked tasks/issues.

        Returns:
            List of SyncResults for each mapping
        """
        results = []
        mappings = await self._get_all_mappings()

        for mapping in mappings:
            try:
                # Sync task to GitHub (updates issue if task is newer)
                result = await self.sync_task_to_github(
                    task_id=mapping.atlas_task_id,
                    repo=mapping.github_repo,
                    create_if_missing=False,
                )
                results.append(result)
            except Exception as e:
                logger.exception(f"Error syncing mapping {mapping.id}: {e}")
                results.append(SyncResult(
                    success=False,
                    direction=SyncDirection.BIDIRECTIONAL,
                    atlas_task_id=mapping.atlas_task_id,
                    github_repo=mapping.github_repo,
                    github_issue_number=mapping.github_issue_number,
                    error=str(e),
                    message="Full sync failed for this mapping",
                ))

        self._sync_state.last_full_sync = datetime.now()
        return results

    async def get_sync_status(self) -> SyncState:
        """Get current sync state.

        Returns:
            SyncState with counts
        """
        mappings = await self._get_all_mappings()
        self._sync_state.mappings_count = len(mappings)
        self._sync_state.pending_count = sum(1 for m in mappings if m.sync_status == SyncStatus.PENDING)
        self._sync_state.synced_count = sum(1 for m in mappings if m.sync_status == SyncStatus.SYNCED)
        self._sync_state.failed_count = sum(1 for m in mappings if m.sync_status == SyncStatus.FAILED)
        self._sync_state.conflict_count = sum(1 for m in mappings if m.sync_status == SyncStatus.CONFLICT)
        return self._sync_state

    # Mapping operations

    async def get_mapping_by_task(self, task_id: int) -> Optional[SyncMapping]:
        """Get mapping for an ATLAS task.

        Args:
            task_id: ATLAS task ID

        Returns:
            SyncMapping or None
        """
        if not self.project_manager:
            return None

        try:
            # Query from github_sync table
            import aiosqlite
            async with aiosqlite.connect(self.project_manager.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM github_sync WHERE atlas_task_id = ?",
                    (task_id,)
                )
                row = await cursor.fetchone()
                if row:
                    return self._row_to_mapping(row)
                return None
        except Exception as e:
            logger.debug(f"Error getting mapping for task {task_id}: {e}")
            return None

    async def get_mapping_by_issue(
        self, repo: str, issue_number: int
    ) -> Optional[SyncMapping]:
        """Get mapping for a GitHub issue.

        Args:
            repo: Repository in "owner/repo" format
            issue_number: Issue number

        Returns:
            SyncMapping or None
        """
        if not self.project_manager:
            return None

        try:
            import aiosqlite
            async with aiosqlite.connect(self.project_manager.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM github_sync WHERE github_repo = ? AND github_issue_number = ?",
                    (repo, issue_number)
                )
                row = await cursor.fetchone()
                if row:
                    return self._row_to_mapping(row)
                return None
        except Exception as e:
            logger.debug(f"Error getting mapping for issue {repo}#{issue_number}: {e}")
            return None

    # Private helper methods

    async def _save_mapping(self, mapping: SyncMapping) -> None:
        """Save a sync mapping to database."""
        if not self.project_manager:
            return

        import aiosqlite
        async with aiosqlite.connect(self.project_manager.db_path) as db:
            if mapping.id:
                # Update existing
                await db.execute(
                    """
                    UPDATE github_sync SET
                        atlas_task_id = ?,
                        github_repo = ?,
                        github_issue_number = ?,
                        last_sync = ?,
                        sync_status = ?
                    WHERE id = ?
                    """,
                    (
                        mapping.atlas_task_id,
                        mapping.github_repo,
                        mapping.github_issue_number,
                        mapping.last_sync.isoformat() if mapping.last_sync else None,
                        mapping.sync_status.value,
                        mapping.id,
                    )
                )
            else:
                # Insert new
                cursor = await db.execute(
                    """
                    INSERT INTO github_sync (atlas_task_id, github_repo, github_issue_number, last_sync, sync_status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        mapping.atlas_task_id,
                        mapping.github_repo,
                        mapping.github_issue_number,
                        mapping.last_sync.isoformat() if mapping.last_sync else None,
                        mapping.sync_status.value,
                    )
                )
                mapping.id = cursor.lastrowid
            await db.commit()

    async def _get_all_mappings(self) -> list[SyncMapping]:
        """Get all sync mappings from database."""
        if not self.project_manager:
            return []

        try:
            import aiosqlite
            async with aiosqlite.connect(self.project_manager.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM github_sync")
                rows = await cursor.fetchall()
                return [self._row_to_mapping(row) for row in rows]
        except Exception as e:
            logger.debug(f"Error getting all mappings: {e}")
            return []

    def _row_to_mapping(self, row) -> SyncMapping:
        """Convert database row to SyncMapping."""
        return SyncMapping(
            id=row["id"],
            atlas_task_id=row["atlas_task_id"],
            github_repo=row["github_repo"],
            github_issue_number=row["github_issue_number"],
            last_sync=datetime.fromisoformat(row["last_sync"]) if row["last_sync"] else None,
            sync_status=SyncStatus(row["sync_status"]),
        )

    async def _create_issue_from_task(self, task, repo: str) -> GitHubIssueData:
        """Create GitHub issue from ATLAS task."""
        # Build issue body
        body = self._format_task_body(task)

        # Get labels
        labels = [self.config.atlas_label]
        if task.priority in self.config.priority_labels:
            labels.append(self.config.priority_labels[task.priority])
        labels.extend(task.tags)

        return await self.api.create_issue(
            repo=repo,
            title=task.title,
            body=body,
            labels=labels,
        )

    async def _update_issue_from_task(self, task, mapping: SyncMapping) -> GitHubIssueData:
        """Update GitHub issue from ATLAS task."""
        body = self._format_task_body(task)

        # Get labels
        labels = [self.config.atlas_label]
        if task.priority in self.config.priority_labels:
            labels.append(self.config.priority_labels[task.priority])
        labels.extend(task.tags)

        # Map task status to issue state (handle both enum and string)
        status_str = task.status.value if hasattr(task.status, 'value') else task.status
        state = "closed" if status_str == "completed" else "open"

        return await self.api.update_issue(
            repo=mapping.github_repo,
            issue_number=mapping.github_issue_number,
            title=task.title,
            body=body,
            state=state,
            labels=labels,
        )

    async def _create_task_from_issue(self, issue: GitHubIssueData, project_id: int):
        """Create ATLAS task from GitHub issue."""
        # Extract tags from labels (excluding system labels)
        tags = [
            label for label in issue.labels
            if label != self.config.atlas_label
            and not label.startswith("priority:")
        ]

        # Map priority from labels
        priority = 0
        for p, label in self.config.priority_labels.items():
            if label in issue.labels:
                priority = p
                break

        return await self.project_manager.create_task(
            project_id=project_id,
            title=issue.title,
            description=issue.body,
            priority=priority,
            tags=tags,
            metadata={
                "github_url": issue.html_url,
                "github_user": issue.user,
            },
        )

    async def _update_task_from_issue(self, issue: GitHubIssueData, task_id: int):
        """Update ATLAS task from GitHub issue."""
        # Map issue state to task status
        status = TaskStatus.COMPLETED if issue.state == "closed" else TaskStatus.PENDING

        # Extract tags from labels
        tags = [
            label for label in issue.labels
            if label != self.config.atlas_label
            and not label.startswith("priority:")
        ]

        # Map priority from labels
        priority = 0
        for p, label in self.config.priority_labels.items():
            if label in issue.labels:
                priority = p
                break

        return await self.project_manager.update_task(
            task_id=task_id,
            title=issue.title,
            description=issue.body,
            status=status,
            priority=priority,
            tags=tags,
        )

    async def _get_or_create_github_project(self, repo: str) -> int:
        """Get or create a project for GitHub issues."""
        project_name = f"GitHub: {repo}"

        # Look for existing project
        projects = await self.project_manager.get_projects()
        for p in projects:
            if p.name == project_name:
                return p.id

        # Create new project
        project = await self.project_manager.create_project(
            name=project_name,
            description=f"Issues synced from GitHub repository {repo}",
            tags=["github", "imported"],
            metadata={"github_repo": repo},
        )
        return project.id

    def _format_task_body(self, task) -> str:
        """Format task as GitHub issue body."""
        lines = []

        if task.description:
            lines.append(task.description)
            lines.append("")

        lines.append("---")
        lines.append("*Synced from ATLAS*")
        lines.append(f"- **Task ID**: {task.id}")
        # Handle both enum and string status
        status_str = task.status.value if hasattr(task.status, 'value') else task.status
        lines.append(f"- **Status**: {status_str}")
        lines.append(f"- **Priority**: {task.priority}")

        if task.tags:
            lines.append(f"- **Tags**: {', '.join(task.tags)}")

        return "\n".join(lines)

    def _format_agent_output_comment(
        self, output: dict[str, Any], summary: Optional[str] = None
    ) -> str:
        """Format agent output as GitHub comment."""
        lines = ["## [ATLAS Agent] Workflow Results", ""]

        if summary:
            lines.append(summary)
            lines.append("")

        for agent_name, agent_output in output.items():
            lines.append(f"### {agent_name.title()}")

            if isinstance(agent_output, dict):
                content = agent_output.get("content", "")
                status = agent_output.get("status", "completed")
                lines.append(f"**Status**: {status}")
                lines.append("")
                if content:
                    # Truncate long content
                    if len(content) > 2000:
                        content = content[:2000] + "\n\n...(truncated)"
                    lines.append(content)
            else:
                lines.append(str(agent_output)[:2000])

            lines.append("")

        lines.append("---")
        lines.append("*Generated by ATLAS Agent Pipeline*")

        return "\n".join(lines)
