"""
GitHub webhook event handlers for ATLAS Transporter.

Handles incoming GitHub webhook events and syncs changes to ATLAS.
Integrates with the existing WebhookHandler pattern from atlas/automation/webhooks.py.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Optional

from .models import (
    TransporterConfig,
    GitHubIssueData,
    SyncDirection,
    SyncResult,
)

logger = logging.getLogger(__name__)

# Singleton instance
_github_sync_handler: Optional["GitHubSyncHandler"] = None


def get_github_sync_handler(
    transporter=None,
    config: Optional[TransporterConfig] = None,
) -> "GitHubSyncHandler":
    """Get or create the global GitHub sync handler instance.

    Args:
        transporter: Transporter instance for sync operations
        config: Configuration

    Returns:
        GitHubSyncHandler instance
    """
    global _github_sync_handler
    if _github_sync_handler is None:
        _github_sync_handler = GitHubSyncHandler(transporter, config)
    return _github_sync_handler


class GitHubSyncHandler:
    """Handles GitHub webhook events for ATLAS sync.

    Integrates with GitHubWebhookHandler from atlas/automation/webhooks.py
    to process issue and comment events.
    """

    def __init__(
        self,
        transporter=None,
        config: Optional[TransporterConfig] = None,
    ):
        """Initialize the sync handler.

        Args:
            transporter: Transporter instance for sync operations
            config: Configuration
        """
        self.transporter = transporter
        self.config = config or TransporterConfig.from_env()
        self._event_handlers: dict[str, list[Callable]] = {}

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default event handlers."""
        self.on("issues.opened", self._handle_issue_opened)
        self.on("issues.edited", self._handle_issue_edited)
        self.on("issues.closed", self._handle_issue_closed)
        self.on("issues.reopened", self._handle_issue_reopened)
        self.on("issues.labeled", self._handle_issue_labeled)
        self.on("issues.unlabeled", self._handle_issue_unlabeled)
        self.on("issue_comment.created", self._handle_comment_created)

    def on(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type.

        Args:
            event_type: Event type (e.g., "issues.opened", "issue_comment.created")
            handler: Async handler function
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def update_transporter(self, transporter):
        """Update the transporter reference (for late binding).

        Args:
            transporter: Transporter instance
        """
        self.transporter = transporter

    async def handle_event(self, event_type: str, payload: dict) -> list[SyncResult]:
        """Handle a GitHub webhook event.

        Args:
            event_type: Event type from X-GitHub-Event header + action
            payload: Event payload

        Returns:
            List of sync results from handlers
        """
        results = []

        # Get handlers for this event type
        handlers = self._event_handlers.get(event_type, [])

        if not handlers:
            logger.debug(f"No handlers registered for event: {event_type}")
            return results

        for handler in handlers:
            try:
                result = await handler(payload)
                if result:
                    results.append(result)
            except Exception as e:
                logger.exception(f"Error in handler for {event_type}: {e}")
                results.append(SyncResult(
                    success=False,
                    direction=SyncDirection.GITHUB_TO_ATLAS,
                    error=str(e),
                    message=f"Handler error for {event_type}",
                ))

        return results

    def _extract_repo(self, payload: dict) -> str:
        """Extract repository full name from payload.

        Args:
            payload: GitHub webhook payload

        Returns:
            Repository in "owner/repo" format
        """
        repo_data = payload.get("repository", {})
        return repo_data.get("full_name", "")

    def _extract_issue_data(self, payload: dict) -> Optional[GitHubIssueData]:
        """Extract issue data from payload.

        Args:
            payload: GitHub webhook payload

        Returns:
            GitHubIssueData or None
        """
        issue_data = payload.get("issue")
        if not issue_data:
            return None
        return GitHubIssueData.from_github_response(issue_data)

    def _has_atlas_label(self, issue_data: GitHubIssueData) -> bool:
        """Check if issue has the ATLAS tracking label.

        Args:
            issue_data: Issue data

        Returns:
            True if issue has atlas-task label
        """
        return self.config.atlas_label in issue_data.labels

    async def _handle_issue_opened(self, payload: dict) -> Optional[SyncResult]:
        """Handle issues.opened event.

        Creates a new ATLAS task if the issue has the atlas-task label.

        Args:
            payload: GitHub webhook payload

        Returns:
            SyncResult or None
        """
        if not self.transporter:
            logger.warning("Transporter not initialized, skipping issue sync")
            return None

        issue_data = self._extract_issue_data(payload)
        if not issue_data:
            return None

        repo = self._extract_repo(payload)

        # Only sync if issue has atlas-task label
        if not self._has_atlas_label(issue_data):
            logger.debug(f"Issue {repo}#{issue_data.number} doesn't have atlas-task label, skipping")
            return None

        logger.info(f"Syncing new issue {repo}#{issue_data.number} to ATLAS")

        try:
            result = await self.transporter.sync_issue_to_atlas(
                repo=repo,
                issue_number=issue_data.number,
            )
            return result
        except Exception as e:
            logger.exception(f"Error syncing issue to ATLAS: {e}")
            return SyncResult(
                success=False,
                direction=SyncDirection.GITHUB_TO_ATLAS,
                github_repo=repo,
                github_issue_number=issue_data.number,
                error=str(e),
                message="Failed to sync issue to ATLAS",
            )

    async def _handle_issue_edited(self, payload: dict) -> Optional[SyncResult]:
        """Handle issues.edited event.

        Updates linked ATLAS task if the issue is tracked.

        Args:
            payload: GitHub webhook payload

        Returns:
            SyncResult or None
        """
        if not self.transporter:
            return None

        issue_data = self._extract_issue_data(payload)
        if not issue_data:
            return None

        repo = self._extract_repo(payload)

        # Check if this issue is linked to an ATLAS task
        mapping = await self.transporter.get_mapping_by_issue(repo, issue_data.number)
        if not mapping:
            logger.debug(f"Issue {repo}#{issue_data.number} not linked to ATLAS, skipping")
            return None

        logger.info(f"Updating ATLAS task {mapping.atlas_task_id} from issue {repo}#{issue_data.number}")

        try:
            result = await self.transporter.sync_issue_to_atlas(
                repo=repo,
                issue_number=issue_data.number,
            )
            return result
        except Exception as e:
            logger.exception(f"Error updating ATLAS task: {e}")
            return SyncResult(
                success=False,
                direction=SyncDirection.GITHUB_TO_ATLAS,
                github_repo=repo,
                github_issue_number=issue_data.number,
                atlas_task_id=mapping.atlas_task_id,
                error=str(e),
                message="Failed to update ATLAS task",
            )

    async def _handle_issue_closed(self, payload: dict) -> Optional[SyncResult]:
        """Handle issues.closed event.

        Marks linked ATLAS task as completed.

        Args:
            payload: GitHub webhook payload

        Returns:
            SyncResult or None
        """
        if not self.transporter:
            return None

        issue_data = self._extract_issue_data(payload)
        if not issue_data:
            return None

        repo = self._extract_repo(payload)

        mapping = await self.transporter.get_mapping_by_issue(repo, issue_data.number)
        if not mapping:
            return None

        logger.info(f"Marking ATLAS task {mapping.atlas_task_id} as completed (issue closed)")

        try:
            # Update task status to completed
            if self.transporter.project_manager:
                await self.transporter.project_manager.update_task(
                    task_id=mapping.atlas_task_id,
                    status="completed",
                )
                return SyncResult(
                    success=True,
                    direction=SyncDirection.GITHUB_TO_ATLAS,
                    github_repo=repo,
                    github_issue_number=issue_data.number,
                    atlas_task_id=mapping.atlas_task_id,
                    message="Task marked as completed",
                )
        except Exception as e:
            logger.exception(f"Error marking task as completed: {e}")
            return SyncResult(
                success=False,
                direction=SyncDirection.GITHUB_TO_ATLAS,
                error=str(e),
                message="Failed to mark task as completed",
            )

        return None

    async def _handle_issue_reopened(self, payload: dict) -> Optional[SyncResult]:
        """Handle issues.reopened event.

        Marks linked ATLAS task as pending/in_progress.

        Args:
            payload: GitHub webhook payload

        Returns:
            SyncResult or None
        """
        if not self.transporter:
            return None

        issue_data = self._extract_issue_data(payload)
        if not issue_data:
            return None

        repo = self._extract_repo(payload)

        mapping = await self.transporter.get_mapping_by_issue(repo, issue_data.number)
        if not mapping:
            return None

        logger.info(f"Reopening ATLAS task {mapping.atlas_task_id} (issue reopened)")

        try:
            if self.transporter.project_manager:
                await self.transporter.project_manager.update_task(
                    task_id=mapping.atlas_task_id,
                    status="pending",
                )
                return SyncResult(
                    success=True,
                    direction=SyncDirection.GITHUB_TO_ATLAS,
                    github_repo=repo,
                    github_issue_number=issue_data.number,
                    atlas_task_id=mapping.atlas_task_id,
                    message="Task reopened",
                )
        except Exception as e:
            logger.exception(f"Error reopening task: {e}")

        return None

    async def _handle_issue_labeled(self, payload: dict) -> Optional[SyncResult]:
        """Handle issues.labeled event.

        If atlas-task label is added, start tracking the issue.

        Args:
            payload: GitHub webhook payload

        Returns:
            SyncResult or None
        """
        if not self.transporter:
            return None

        label = payload.get("label", {}).get("name", "")
        if label != self.config.atlas_label:
            return None

        issue_data = self._extract_issue_data(payload)
        if not issue_data:
            return None

        repo = self._extract_repo(payload)

        # Check if already linked
        mapping = await self.transporter.get_mapping_by_issue(repo, issue_data.number)
        if mapping:
            logger.debug(f"Issue {repo}#{issue_data.number} already linked to ATLAS")
            return None

        logger.info(f"Starting to track issue {repo}#{issue_data.number} (atlas-task label added)")

        try:
            result = await self.transporter.sync_issue_to_atlas(
                repo=repo,
                issue_number=issue_data.number,
            )
            return result
        except Exception as e:
            logger.exception(f"Error starting to track issue: {e}")
            return SyncResult(
                success=False,
                direction=SyncDirection.GITHUB_TO_ATLAS,
                github_repo=repo,
                github_issue_number=issue_data.number,
                error=str(e),
                message="Failed to start tracking issue",
            )

    async def _handle_issue_unlabeled(self, payload: dict) -> Optional[SyncResult]:
        """Handle issues.unlabeled event.

        If atlas-task label is removed, we keep the link but log it.

        Args:
            payload: GitHub webhook payload

        Returns:
            SyncResult or None
        """
        label = payload.get("label", {}).get("name", "")
        if label != self.config.atlas_label:
            return None

        issue_data = self._extract_issue_data(payload)
        if not issue_data:
            return None

        repo = self._extract_repo(payload)

        logger.info(f"atlas-task label removed from {repo}#{issue_data.number}, link preserved")
        # We don't unlink - the mapping stays for history
        return None

    async def _handle_comment_created(self, payload: dict) -> Optional[SyncResult]:
        """Handle issue_comment.created event.

        Logs comment activity for linked issues.

        Args:
            payload: GitHub webhook payload

        Returns:
            SyncResult or None
        """
        if not self.transporter:
            return None

        issue_data = self._extract_issue_data(payload)
        if not issue_data:
            return None

        repo = self._extract_repo(payload)

        mapping = await self.transporter.get_mapping_by_issue(repo, issue_data.number)
        if not mapping:
            return None

        comment = payload.get("comment", {})
        comment_body = comment.get("body", "")
        comment_user = comment.get("user", {}).get("login", "unknown")

        # Don't process our own comments to avoid loops
        if "[ATLAS Agent]" in comment_body:
            return None

        logger.info(
            f"Comment from {comment_user} on linked issue {repo}#{issue_data.number} "
            f"(ATLAS task {mapping.atlas_task_id})"
        )

        # Could add comment to task metadata or trigger re-sync here
        return None


def register_with_webhook_router(
    webhook_router,
    transporter=None,
    config: Optional[TransporterConfig] = None,
):
    """Register GitHub sync handlers with the existing webhook router.

    This integrates with atlas/automation/webhooks.py GitHubWebhookHandler.

    Args:
        webhook_router: WebhookRouter instance
        transporter: Transporter instance
        config: Configuration
    """
    from atlas.automation.webhooks import WebhookSource, GitHubWebhookHandler

    handler = get_github_sync_handler(transporter, config)

    # Get or create GitHub webhook handler
    github_handler = webhook_router.handlers.get(WebhookSource.GITHUB)
    if not github_handler:
        github_handler = GitHubWebhookHandler(
            secret=config.webhook_secret if config else None
        )
        webhook_router.register_handler(WebhookSource.GITHUB, github_handler)

    # Register sync handlers for each event type
    async def make_sync_handler(event_type: str):
        async def sync_handler(payload: dict):
            results = await handler.handle_event(event_type, payload)
            return [r.to_dict() for r in results if r]
        return sync_handler

    # Register handlers
    for event_type in handler._event_handlers.keys():
        # Split event type into event and action
        parts = event_type.split(".")
        if len(parts) == 2:
            event, action = parts
            full_event = f"{event}.{action}"
        else:
            full_event = event_type

        async def create_handler(et=full_event):
            async def h(payload):
                results = await handler.handle_event(et, payload)
                return [r.to_dict() for r in results if r]
            return h

        import asyncio
        github_handler.on(full_event, asyncio.coroutine(create_handler)())

    logger.info("Registered GitHub sync handlers with webhook router")
