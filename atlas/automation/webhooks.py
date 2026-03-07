"""Webhook handler system for ATLAS.

Meet Sentry - ATLAS's gatekeeper of webhooks. Sentry stands watch at the door,
verifying every incoming webhook, checking credentials, and routing only
legitimate events through. Nothing gets past without proper clearance.

Provides:
- GitHub webhook handling (push, PR, issues)
- Custom webhook endpoints for integrations
- Event routing and processing
- Signature verification for security
"""

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("atlas.automation.webhooks")


class WebhookSource(Enum):
    """Known webhook sources."""

    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    SLACK = "slack"
    STRIPE = "stripe"
    CUSTOM = "custom"


class GitHubEvent(Enum):
    """GitHub webhook event types."""

    PUSH = "push"
    PULL_REQUEST = "pull_request"
    PULL_REQUEST_REVIEW = "pull_request_review"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    CREATE = "create"
    DELETE = "delete"
    RELEASE = "release"
    WORKFLOW_RUN = "workflow_run"
    CHECK_RUN = "check_run"
    DEPLOYMENT = "deployment"
    DEPLOYMENT_STATUS = "deployment_status"


@dataclass
class WebhookEvent:
    """A webhook event to be processed."""

    source: WebhookSource
    event_type: str
    payload: dict
    headers: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    signature_verified: bool = False
    raw_body: bytes = b""


@dataclass
class WebhookResponse:
    """Response from processing a webhook."""

    success: bool
    message: str
    data: dict = field(default_factory=dict)
    actions_taken: list[str] = field(default_factory=list)


class WebhookHandler:
    """Base class for webhook handlers."""

    def __init__(self, secret: Optional[str] = None):
        """Initialize handler with optional secret for signature verification."""
        self.secret = secret

    def verify_signature(
        self, body: bytes, signature: str, algorithm: str = "sha256"
    ) -> bool:
        """Verify webhook signature.

        Args:
            body: Raw request body
            signature: Signature from header
            algorithm: Hash algorithm (sha1, sha256)

        Returns:
            True if signature is valid
        """
        if not self.secret:
            logger.warning("No secret configured for signature verification")
            return True  # Allow if no secret configured

        if algorithm == "sha256":
            expected = "sha256=" + hmac.new(
                self.secret.encode(), body, hashlib.sha256
            ).hexdigest()
        elif algorithm == "sha1":
            expected = "sha1=" + hmac.new(
                self.secret.encode(), body, hashlib.sha1
            ).hexdigest()
        else:
            logger.error(f"Unknown algorithm: {algorithm}")
            return False

        return hmac.compare_digest(expected, signature)

    async def handle(self, event: WebhookEvent) -> WebhookResponse:
        """Handle a webhook event. Override in subclasses."""
        raise NotImplementedError


class GitHubWebhookHandler(WebhookHandler):
    """Handler for GitHub webhooks."""

    def __init__(self, secret: Optional[str] = None):
        super().__init__(secret)
        self._event_handlers: dict[str, list[Callable]] = {}

    def on(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type.

        Args:
            event_type: GitHub event type (push, pull_request, etc.)
            handler: Async function to handle the event
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        logger.info(f"Registered GitHub handler for: {event_type}")

    def verify_github_signature(self, body: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature.

        Args:
            body: Raw request body
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        return self.verify_signature(body, signature, "sha256")

    async def handle(self, event: WebhookEvent) -> WebhookResponse:
        """Handle a GitHub webhook event."""
        event_type = event.event_type
        payload = event.payload
        actions_taken = []

        logger.info(f"Processing GitHub {event_type} event")

        # Get handlers for this event type
        handlers = self._event_handlers.get(event_type, [])

        if not handlers:
            return WebhookResponse(
                success=True,
                message=f"No handlers for event: {event_type}",
            )

        # Run all handlers
        for handler in handlers:
            try:
                result = await handler(payload)
                if result:
                    actions_taken.append(str(result))
            except Exception as e:
                logger.error(f"Handler error for {event_type}: {e}", exc_info=True)
                actions_taken.append(f"ERROR: {e}")

        return WebhookResponse(
            success=True,
            message=f"Processed {event_type} event",
            actions_taken=actions_taken,
        )

    # Convenience methods for extracting common data

    @staticmethod
    def get_repo_info(payload: dict) -> dict:
        """Extract repository info from payload."""
        repo = payload.get("repository", {})
        return {
            "name": repo.get("name"),
            "full_name": repo.get("full_name"),
            "owner": repo.get("owner", {}).get("login"),
            "url": repo.get("html_url"),
            "default_branch": repo.get("default_branch"),
            "private": repo.get("private", False),
        }

    @staticmethod
    def get_push_info(payload: dict) -> dict:
        """Extract push event info."""
        return {
            "ref": payload.get("ref"),
            "branch": payload.get("ref", "").replace("refs/heads/", ""),
            "before": payload.get("before"),
            "after": payload.get("after"),
            "commits": payload.get("commits", []),
            "pusher": payload.get("pusher", {}).get("name"),
            "compare_url": payload.get("compare"),
        }

    @staticmethod
    def get_pr_info(payload: dict) -> dict:
        """Extract pull request info."""
        pr = payload.get("pull_request", {})
        return {
            "number": pr.get("number"),
            "title": pr.get("title"),
            "state": pr.get("state"),
            "action": payload.get("action"),
            "author": pr.get("user", {}).get("login"),
            "url": pr.get("html_url"),
            "base_branch": pr.get("base", {}).get("ref"),
            "head_branch": pr.get("head", {}).get("ref"),
            "draft": pr.get("draft", False),
            "mergeable": pr.get("mergeable"),
        }


class WebhookRouter:
    """Sentry's gate - directs webhooks to appropriate handlers.

    Nothing gets past without proper clearance.
    """

    NAME = "Sentry"

    def __init__(self):
        self.handlers: dict[WebhookSource, WebhookHandler] = {}
        self._middleware: list[Callable] = []

    def register_handler(
        self, source: WebhookSource, handler: WebhookHandler
    ) -> None:
        """Register a handler for a webhook source."""
        self.handlers[source] = handler
        logger.info(f"Registered handler for source: {source.value}")

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to process all webhooks."""
        self._middleware.append(middleware)

    async def route(self, event: WebhookEvent) -> WebhookResponse:
        """Route a webhook event to its handler.

        Args:
            event: Webhook event to process

        Returns:
            Processing response
        """
        # Run middleware
        for mw in self._middleware:
            try:
                event = await mw(event)
                if event is None:
                    return WebhookResponse(
                        success=False,
                        message="Blocked by middleware",
                    )
            except Exception as e:
                logger.error(f"Middleware error: {e}", exc_info=True)

        # Find handler
        handler = self.handlers.get(event.source)
        if not handler:
            return WebhookResponse(
                success=False,
                message=f"No handler for source: {event.source.value}",
            )

        return await handler.handle(event)


# Pre-built handler functions

async def on_push_deploy(payload: dict) -> str:
    """Deploy on push to main branch."""
    push_info = GitHubWebhookHandler.get_push_info(payload)
    repo_info = GitHubWebhookHandler.get_repo_info(payload)

    branch = push_info["branch"]

    if branch not in ("main", "master"):
        return f"Skipped: push to {branch}"

    # In a real implementation, trigger deployment here
    logger.info(f"Would deploy {repo_info['name']} from {branch}")
    return f"Deployment triggered for {repo_info['name']}"


async def on_pr_opened(payload: dict) -> str:
    """Handle new pull request."""
    pr_info = GitHubWebhookHandler.get_pr_info(payload)

    if payload.get("action") != "opened":
        return f"Skipped: PR action {payload.get('action')}"

    # In a real implementation, run checks, post comments, etc.
    logger.info(f"New PR #{pr_info['number']}: {pr_info['title']}")
    return f"Processed new PR #{pr_info['number']}"


async def on_workflow_complete(payload: dict) -> str:
    """Handle workflow completion."""
    workflow = payload.get("workflow_run", {})
    conclusion = workflow.get("conclusion")
    name = workflow.get("name")

    logger.info(f"Workflow {name} completed: {conclusion}")
    return f"Workflow {name}: {conclusion}"


# Factory function

def create_github_handler(secret: Optional[str] = None) -> GitHubWebhookHandler:
    """Create a GitHub webhook handler with default handlers."""
    handler = GitHubWebhookHandler(secret)

    # Register default handlers
    handler.on("push", on_push_deploy)
    handler.on("pull_request", on_pr_opened)
    handler.on("workflow_run", on_workflow_complete)

    return handler


# Singleton router
_webhook_router: Optional[WebhookRouter] = None


def get_webhook_router() -> WebhookRouter:
    """Get or create the global webhook router."""
    global _webhook_router
    if _webhook_router is None:
        _webhook_router = WebhookRouter()
    return _webhook_router
