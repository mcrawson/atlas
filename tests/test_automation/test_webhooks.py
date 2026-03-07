"""Tests for webhook handling functionality."""

import hashlib
import hmac
import pytest
from unittest.mock import AsyncMock, MagicMock

from atlas.automation.webhooks import (
    WebhookEvent,
    WebhookResponse,
    WebhookSource,
    WebhookHandler,
    WebhookRouter,
    GitHubWebhookHandler,
    GitHubEvent,
    create_github_handler,
    get_webhook_router,
    on_push_deploy,
    on_pr_opened,
)


class TestWebhookEvent:
    """Test WebhookEvent dataclass."""

    def test_create_event(self):
        """Test creating a webhook event."""
        event = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type="push",
            payload={"ref": "refs/heads/main"},
        )

        assert event.source == WebhookSource.GITHUB
        assert event.event_type == "push"
        assert event.payload["ref"] == "refs/heads/main"
        assert event.timestamp is not None

    def test_event_with_headers(self):
        """Test event with headers."""
        event = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type="push",
            payload={},
            headers={"X-GitHub-Event": "push"},
        )

        assert event.headers["X-GitHub-Event"] == "push"


class TestWebhookResponse:
    """Test WebhookResponse dataclass."""

    def test_success_response(self):
        """Test successful response."""
        response = WebhookResponse(
            success=True,
            message="Processed",
            actions_taken=["deployed", "notified"],
        )

        assert response.success is True
        assert len(response.actions_taken) == 2

    def test_failure_response(self):
        """Test failure response."""
        response = WebhookResponse(
            success=False,
            message="Handler not found",
        )

        assert response.success is False
        assert response.actions_taken == []


class TestWebhookHandler:
    """Test base WebhookHandler class."""

    def test_verify_signature_sha256(self):
        """Test SHA256 signature verification."""
        secret = "test-secret"
        handler = WebhookHandler(secret=secret)

        body = b'{"test": "data"}'
        expected = "sha256=" + hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()

        assert handler.verify_signature(body, expected, "sha256") is True

    def test_verify_signature_sha1(self):
        """Test SHA1 signature verification."""
        secret = "test-secret"
        handler = WebhookHandler(secret=secret)

        body = b'{"test": "data"}'
        expected = "sha1=" + hmac.new(
            secret.encode(), body, hashlib.sha1
        ).hexdigest()

        assert handler.verify_signature(body, expected, "sha1") is True

    def test_verify_signature_invalid(self):
        """Test invalid signature rejection."""
        handler = WebhookHandler(secret="test-secret")

        assert handler.verify_signature(b"data", "sha256=invalid", "sha256") is False

    def test_verify_signature_no_secret(self):
        """Test verification without secret allows all."""
        handler = WebhookHandler()

        assert handler.verify_signature(b"data", "anything", "sha256") is True


class TestGitHubWebhookHandler:
    """Test GitHubWebhookHandler class."""

    @pytest.fixture
    def handler(self):
        """Create a GitHub webhook handler."""
        return GitHubWebhookHandler(secret="github-secret")

    def test_register_handler(self, handler):
        """Test registering event handler."""

        async def my_handler(payload):
            return "handled"

        handler.on("push", my_handler)
        assert "push" in handler._event_handlers
        assert len(handler._event_handlers["push"]) == 1

    def test_verify_github_signature(self, handler):
        """Test GitHub signature verification."""
        body = b'{"action": "opened"}'
        signature = "sha256=" + hmac.new(
            b"github-secret", body, hashlib.sha256
        ).hexdigest()

        assert handler.verify_github_signature(body, signature) is True

    @pytest.mark.asyncio
    async def test_handle_registered_event(self, handler):
        """Test handling a registered event."""
        handled = []

        async def my_handler(payload):
            handled.append(payload)
            return "processed"

        handler.on("push", my_handler)

        event = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type="push",
            payload={"ref": "refs/heads/main"},
        )

        response = await handler.handle(event)

        assert response.success is True
        assert len(handled) == 1
        assert "processed" in response.actions_taken

    @pytest.mark.asyncio
    async def test_handle_unregistered_event(self, handler):
        """Test handling unregistered event."""
        event = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type="unknown_event",
            payload={},
        )

        response = await handler.handle(event)

        assert response.success is True
        assert "No handlers" in response.message

    @pytest.mark.asyncio
    async def test_handle_handler_error(self, handler):
        """Test handler error is caught."""

        async def failing_handler(payload):
            raise ValueError("Test error")

        handler.on("push", failing_handler)

        event = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type="push",
            payload={},
        )

        response = await handler.handle(event)

        # Should not raise, error is caught
        assert response.success is True
        assert any("ERROR" in a for a in response.actions_taken)

    def test_get_repo_info(self):
        """Test extracting repo info."""
        payload = {
            "repository": {
                "name": "atlas",
                "full_name": "org/atlas",
                "owner": {"login": "org"},
                "html_url": "https://github.com/org/atlas",
                "default_branch": "main",
                "private": False,
            }
        }

        info = GitHubWebhookHandler.get_repo_info(payload)

        assert info["name"] == "atlas"
        assert info["owner"] == "org"
        assert info["default_branch"] == "main"

    def test_get_push_info(self):
        """Test extracting push info."""
        payload = {
            "ref": "refs/heads/main",
            "before": "abc123",
            "after": "def456",
            "commits": [{"id": "def456"}],
            "pusher": {"name": "developer"},
            "compare": "https://github.com/compare/abc...def",
        }

        info = GitHubWebhookHandler.get_push_info(payload)

        assert info["branch"] == "main"
        assert info["before"] == "abc123"
        assert info["after"] == "def456"
        assert info["pusher"] == "developer"

    def test_get_pr_info(self):
        """Test extracting PR info."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Add feature",
                "state": "open",
                "user": {"login": "developer"},
                "html_url": "https://github.com/org/repo/pull/42",
                "base": {"ref": "main"},
                "head": {"ref": "feature-branch"},
                "draft": False,
            },
        }

        info = GitHubWebhookHandler.get_pr_info(payload)

        assert info["number"] == 42
        assert info["title"] == "Add feature"
        assert info["action"] == "opened"
        assert info["base_branch"] == "main"
        assert info["head_branch"] == "feature-branch"


class TestWebhookRouter:
    """Test WebhookRouter class."""

    @pytest.fixture
    def router(self):
        """Create a webhook router."""
        return WebhookRouter()

    def test_register_handler(self, router):
        """Test registering a handler."""
        handler = GitHubWebhookHandler()
        router.register_handler(WebhookSource.GITHUB, handler)

        assert WebhookSource.GITHUB in router.handlers

    @pytest.mark.asyncio
    async def test_route_to_handler(self, router):
        """Test routing to correct handler."""
        handler = MagicMock(spec=GitHubWebhookHandler)
        handler.handle = AsyncMock(
            return_value=WebhookResponse(success=True, message="OK")
        )

        router.register_handler(WebhookSource.GITHUB, handler)

        event = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type="push",
            payload={},
        )

        response = await router.route(event)

        handler.handle.assert_called_once()
        assert response.success is True

    @pytest.mark.asyncio
    async def test_route_no_handler(self, router):
        """Test routing with no handler."""
        event = WebhookEvent(
            source=WebhookSource.GITLAB,
            event_type="push",
            payload={},
        )

        response = await router.route(event)

        assert response.success is False
        assert "No handler" in response.message

    @pytest.mark.asyncio
    async def test_middleware(self, router):
        """Test middleware execution."""
        middleware_called = []

        async def middleware(event):
            middleware_called.append(event)
            return event

        router.add_middleware(middleware)

        handler = MagicMock(spec=GitHubWebhookHandler)
        handler.handle = AsyncMock(
            return_value=WebhookResponse(success=True, message="OK")
        )
        router.register_handler(WebhookSource.GITHUB, handler)

        event = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type="push",
            payload={},
        )

        await router.route(event)

        assert len(middleware_called) == 1

    @pytest.mark.asyncio
    async def test_middleware_blocks(self, router):
        """Test middleware can block request."""

        async def blocking_middleware(event):
            return None  # Block

        router.add_middleware(blocking_middleware)

        handler = MagicMock(spec=GitHubWebhookHandler)
        router.register_handler(WebhookSource.GITHUB, handler)

        event = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type="push",
            payload={},
        )

        response = await router.route(event)

        assert response.success is False
        assert "middleware" in response.message.lower()


class TestDefaultHandlers:
    """Test default webhook handler functions."""

    @pytest.mark.asyncio
    async def test_on_push_deploy_main(self):
        """Test push deploy on main branch."""
        payload = {
            "ref": "refs/heads/main",
            "repository": {"name": "atlas"},
            "commits": [],
        }

        result = await on_push_deploy(payload)

        assert "triggered" in result.lower()

    @pytest.mark.asyncio
    async def test_on_push_deploy_feature(self):
        """Test push deploy on feature branch (skipped)."""
        payload = {
            "ref": "refs/heads/feature-x",
            "repository": {"name": "atlas"},
            "commits": [],
        }

        result = await on_push_deploy(payload)

        assert "skipped" in result.lower()

    @pytest.mark.asyncio
    async def test_on_pr_opened(self):
        """Test PR opened handler."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Add feature",
            },
        }

        result = await on_pr_opened(payload)

        assert "#42" in result

    @pytest.mark.asyncio
    async def test_on_pr_closed(self):
        """Test PR closed is skipped."""
        payload = {
            "action": "closed",
            "pull_request": {
                "number": 42,
                "title": "Add feature",
            },
        }

        result = await on_pr_opened(payload)

        assert "skipped" in result.lower()


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_github_handler(self):
        """Test creating GitHub handler with defaults."""
        handler = create_github_handler("test-secret")

        assert handler.secret == "test-secret"
        assert "push" in handler._event_handlers
        assert "pull_request" in handler._event_handlers

    def test_get_webhook_router_singleton(self):
        """Test singleton behavior."""
        import atlas.automation.webhooks as module

        module._webhook_router = None

        router1 = get_webhook_router()
        router2 = get_webhook_router()

        assert router1 is router2
