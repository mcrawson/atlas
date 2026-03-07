"""Tests for Slack integration."""

import hashlib
import hmac
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from atlas.integrations.slack import (
    SlackClient,
    SlackMessage,
    SlackNotifier,
    SlashCommand,
    SlackMessageType,
    handle_atlas_command,
    get_slack_client,
)


class TestSlackMessage:
    """Test SlackMessage dataclass."""

    def test_basic_message(self):
        """Test creating a basic message."""
        msg = SlackMessage(text="Hello", channel="#general")
        data = msg.to_dict()

        assert data["text"] == "Hello"
        assert data["channel"] == "#general"
        assert "blocks" not in data
        assert "attachments" not in data

    def test_message_with_blocks(self):
        """Test message with blocks."""
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}]
        msg = SlackMessage(text="Fallback", channel="#test", blocks=blocks)
        data = msg.to_dict()

        assert data["blocks"] == blocks
        assert data["text"] == "Fallback"

    def test_message_with_thread(self):
        """Test threaded message."""
        msg = SlackMessage(
            text="Reply", channel="#test", thread_ts="1234567890.123456"
        )
        data = msg.to_dict()

        assert data["thread_ts"] == "1234567890.123456"

    def test_unfurl_settings(self):
        """Test unfurl settings."""
        msg = SlackMessage(
            text="Link", channel="#test", unfurl_links=True, unfurl_media=False
        )
        data = msg.to_dict()

        assert data["unfurl_links"] is True
        assert data["unfurl_media"] is False


class TestSlashCommand:
    """Test SlashCommand dataclass."""

    def test_create_command(self):
        """Test creating a slash command."""
        cmd = SlashCommand(
            command="/atlas",
            text="status",
            user_id="U12345",
            user_name="testuser",
            channel_id="C12345",
            channel_name="general",
            team_id="T12345",
            response_url="https://hooks.slack.com/...",
            trigger_id="123.456.abc",
        )

        assert cmd.command == "/atlas"
        assert cmd.text == "status"
        assert cmd.user_name == "testuser"


class TestSlackClient:
    """Test SlackClient class."""

    @pytest.fixture
    def client(self):
        """Create a Slack client."""
        return SlackClient(
            bot_token="xoxb-test-token",
            signing_secret="test-signing-secret",
        )

    def test_initialization(self, client):
        """Test client initializes correctly."""
        assert client.bot_token == "xoxb-test-token"
        assert client.signing_secret == "test-signing-secret"

    def test_is_configured(self, client):
        """Test is_configured property."""
        assert client.is_configured is True

        unconfigured = SlackClient()
        assert unconfigured.is_configured is False

    def test_verify_signature_valid(self, client):
        """Test valid signature verification."""
        timestamp = str(int(time.time()))
        body = b'{"test": "data"}'

        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        signature = (
            "v0="
            + hmac.new(
                client.signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        assert client.verify_signature(body, timestamp, signature) is True

    def test_verify_signature_invalid(self, client):
        """Test invalid signature rejection."""
        timestamp = str(int(time.time()))
        body = b'{"test": "data"}'

        assert client.verify_signature(body, timestamp, "v0=invalid") is False

    def test_verify_signature_old_timestamp(self, client):
        """Test old timestamp rejection."""
        old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
        body = b'{"test": "data"}'

        assert client.verify_signature(body, old_timestamp, "v0=anything") is False

    def test_register_command(self, client):
        """Test registering command handlers."""

        async def handler(cmd):
            return {"text": "handled"}

        client.register_command("/test", handler)
        assert "/test" in client._command_handlers

    def test_register_action(self, client):
        """Test registering action handlers."""

        async def handler(payload, action):
            return {}

        client.register_action("button_click", handler)
        assert "button_click" in client._action_handlers

    @pytest.mark.asyncio
    async def test_handle_command_registered(self, client):
        """Test handling a registered command."""

        async def handler(cmd):
            return {"response_type": "in_channel", "text": f"Hello {cmd.user_name}"}

        client.register_command("/greet", handler)

        cmd = SlashCommand(
            command="/greet",
            text="",
            user_id="U123",
            user_name="tester",
            channel_id="C123",
            channel_name="test",
            team_id="T123",
            response_url="https://...",
            trigger_id="123",
        )

        result = await client.handle_command(cmd)
        assert result["text"] == "Hello tester"

    @pytest.mark.asyncio
    async def test_handle_command_unknown(self, client):
        """Test handling unknown command."""
        cmd = SlashCommand(
            command="/unknown",
            text="",
            user_id="U123",
            user_name="tester",
            channel_id="C123",
            channel_name="test",
            team_id="T123",
            response_url="https://...",
            trigger_id="123",
        )

        result = await client.handle_command(cmd)
        assert "Unknown command" in result["text"]

    @pytest.mark.asyncio
    async def test_handle_command_error(self, client):
        """Test handling command error."""

        async def failing_handler(cmd):
            raise ValueError("Test error")

        client.register_command("/fail", failing_handler)

        cmd = SlashCommand(
            command="/fail",
            text="",
            user_id="U123",
            user_name="tester",
            channel_id="C123",
            channel_name="test",
            team_id="T123",
            response_url="https://...",
            trigger_id="123",
        )

        result = await client.handle_command(cmd)
        assert "Error" in result["text"]

    @pytest.mark.asyncio
    async def test_send_message(self, client):
        """Test sending a message."""
        with patch.object(client, "_api_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"ok": True, "ts": "123.456"}

            msg = SlackMessage(text="Test", channel="#test")
            result = await client.send_message(msg)

            mock_call.assert_called_once()
            assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_send_text(self, client):
        """Test sending simple text."""
        with patch.object(client, "send_message", new_callable=AsyncMock) as mock:
            mock.return_value = {"ok": True}

            await client.send_text("#test", "Hello world")

            mock.assert_called_once()
            call_msg = mock.call_args[0][0]
            assert call_msg.text == "Hello world"
            assert call_msg.channel == "#test"

    @pytest.mark.asyncio
    async def test_send_blocks(self, client):
        """Test sending blocks."""
        with patch.object(client, "send_message", new_callable=AsyncMock) as mock:
            mock.return_value = {"ok": True}

            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Hi"}}]
            await client.send_blocks("#test", blocks)

            mock.assert_called_once()
            call_msg = mock.call_args[0][0]
            assert call_msg.blocks == blocks

    @pytest.mark.asyncio
    async def test_add_reaction(self, client):
        """Test adding reaction."""
        with patch.object(client, "_api_call", new_callable=AsyncMock) as mock:
            mock.return_value = {"ok": True}

            await client.add_reaction("#test", "123.456", "thumbsup")

            mock.assert_called_once_with(
                "reactions.add",
                {"channel": "#test", "timestamp": "123.456", "name": "thumbsup"},
            )


class TestSlackNotifier:
    """Test SlackNotifier class."""

    @pytest.fixture
    def notifier(self):
        """Create a notifier with mock client."""
        client = MagicMock(spec=SlackClient)
        client.send_blocks = AsyncMock(return_value={"ok": True})
        return SlackNotifier(client, default_channel="#atlas")

    @pytest.mark.asyncio
    async def test_notify_build_start(self, notifier):
        """Test build start notification."""
        await notifier.notify_build_start(
            project="atlas",
            branch="main",
            commit="abc1234",
        )

        notifier.client.send_blocks.assert_called_once()
        call_args = notifier.client.send_blocks.call_args
        assert call_args.kwargs["channel"] == "#atlas"
        assert "build started" in call_args.kwargs["text"].lower()

    @pytest.mark.asyncio
    async def test_notify_build_complete_success(self, notifier):
        """Test successful build notification."""
        await notifier.notify_build_complete(
            project="atlas",
            branch="main",
            success=True,
            duration_seconds=125,
        )

        notifier.client.send_blocks.assert_called_once()
        blocks = notifier.client.send_blocks.call_args.kwargs["blocks"]
        block_text = blocks[0]["text"]["text"]
        assert "Succeeded" in block_text
        assert "white_check_mark" in block_text

    @pytest.mark.asyncio
    async def test_notify_build_complete_failure(self, notifier):
        """Test failed build notification."""
        await notifier.notify_build_complete(
            project="atlas",
            branch="feature",
            success=False,
            duration_seconds=45,
        )

        notifier.client.send_blocks.assert_called_once()
        blocks = notifier.client.send_blocks.call_args.kwargs["blocks"]
        block_text = blocks[0]["text"]["text"]
        assert "Failed" in block_text

    @pytest.mark.asyncio
    async def test_notify_cost_report(self, notifier):
        """Test cost report notification."""
        await notifier.notify_cost_report(
            daily_cost=5.50,
            daily_budget=10.0,
            top_models=[
                {"model": "gpt-4o", "cost": 3.0, "requests": 50},
                {"model": "claude-sonnet", "cost": 2.5, "requests": 30},
            ],
        )

        notifier.client.send_blocks.assert_called_once()
        blocks = notifier.client.send_blocks.call_args.kwargs["blocks"]
        assert any("Cost Report" in str(b) for b in blocks)

    @pytest.mark.asyncio
    async def test_notify_alert_warning(self, notifier):
        """Test warning alert notification."""
        await notifier.notify_alert(
            title="High CPU Usage",
            message="CPU at 85%",
            severity="warning",
        )

        notifier.client.send_blocks.assert_called_once()
        text = notifier.client.send_blocks.call_args.kwargs["text"]
        assert "WARNING" in text

    @pytest.mark.asyncio
    async def test_notify_deployment(self, notifier):
        """Test deployment notification."""
        await notifier.notify_deployment(
            service="atlas-web",
            version="v1.2.3",
            environment="production",
            status="completed",
        )

        notifier.client.send_blocks.assert_called_once()
        blocks = notifier.client.send_blocks.call_args.kwargs["blocks"]
        block_text = blocks[0]["text"]["text"]
        assert "atlas-web" in block_text
        assert "production" in block_text


class TestDefaultCommandHandlers:
    """Test default slash command handlers."""

    @pytest.fixture
    def command(self):
        """Create a base command."""
        return SlashCommand(
            command="/atlas",
            text="",
            user_id="U123",
            user_name="tester",
            channel_id="C123",
            channel_name="test",
            team_id="T123",
            response_url="https://...",
            trigger_id="123",
        )

    @pytest.mark.asyncio
    async def test_handle_atlas_help(self, command):
        """Test /atlas help."""
        command.text = "help"
        result = await handle_atlas_command(command)

        assert "ATLAS Commands" in result["text"]
        assert "/atlas status" in result["text"]

    @pytest.mark.asyncio
    async def test_handle_atlas_status(self, command):
        """Test /atlas status."""
        command.text = "status"
        result = await handle_atlas_command(command)

        assert "ATLAS Status" in str(result)

    @pytest.mark.asyncio
    async def test_handle_atlas_unknown(self, command):
        """Test unknown subcommand."""
        command.text = "foobar"
        result = await handle_atlas_command(command)

        assert "Unknown subcommand" in result["text"]

    @pytest.mark.asyncio
    async def test_handle_atlas_empty(self, command):
        """Test /atlas with no subcommand shows help."""
        command.text = ""
        result = await handle_atlas_command(command)

        assert "ATLAS Commands" in result["text"]


class TestGlobalSlackClient:
    """Test global Slack client instance."""

    def test_get_slack_client_singleton(self):
        """Test singleton behavior."""
        import atlas.integrations.slack as module

        module._slack_client = None

        client1 = get_slack_client()
        client2 = get_slack_client()

        assert client1 is client2

    def test_default_handlers_registered(self):
        """Test default handlers are registered."""
        import atlas.integrations.slack as module

        module._slack_client = None

        client = get_slack_client()
        assert "/atlas" in client._command_handlers
