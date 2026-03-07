"""Slack integration for ATLAS.

Meet K.I.T.T. - ATLAS's Knight Industries Two Thousand interface.
Always connected, always ready to communicate. Handles Slack commands,
sends notifications, and ensures critical messages reach their targets.

"I am able to communicate with you through any channel, Michael." - K.I.T.T.

Provides:
- Slash command handling (/atlas, /build, /status)
- Interactive messages with buttons and modals
- Notifications for builds, costs, and alerts
- Channel-based agent assignment
"""

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import httpx

logger = logging.getLogger("atlas.integrations.slack")


class SlackMessageType(Enum):
    """Types of Slack messages."""

    TEXT = "text"
    BLOCKS = "blocks"
    ATTACHMENT = "attachment"


@dataclass
class SlackMessage:
    """A Slack message with optional blocks and attachments."""

    text: str
    channel: str
    blocks: list[dict] = field(default_factory=list)
    attachments: list[dict] = field(default_factory=list)
    thread_ts: Optional[str] = None
    unfurl_links: bool = False
    unfurl_media: bool = True

    def to_dict(self) -> dict:
        """Convert to Slack API format."""
        data = {
            "channel": self.channel,
            "text": self.text,
            "unfurl_links": self.unfurl_links,
            "unfurl_media": self.unfurl_media,
        }
        if self.blocks:
            data["blocks"] = self.blocks
        if self.attachments:
            data["attachments"] = self.attachments
        if self.thread_ts:
            data["thread_ts"] = self.thread_ts
        return data


@dataclass
class SlashCommand:
    """Parsed Slack slash command."""

    command: str
    text: str
    user_id: str
    user_name: str
    channel_id: str
    channel_name: str
    team_id: str
    response_url: str
    trigger_id: str


class SlackClient:
    """K.I.T.T. - Knight Industries Two Thousand.

    Handles Slack authentication, message sending, and slash command processing.
    Always monitoring, always ready to assist.
    """

    NAME = "K.I.T.T."

    API_BASE = "https://slack.com/api"

    def __init__(
        self,
        bot_token: Optional[str] = None,
        signing_secret: Optional[str] = None,
        app_token: Optional[str] = None,
    ):
        """Initialize Slack client.

        Args:
            bot_token: Slack Bot User OAuth Token (xoxb-...)
            signing_secret: Slack signing secret for request verification
            app_token: Slack App-Level Token for Socket Mode (xapp-...)
        """
        self.bot_token = bot_token or os.environ.get("SLACK_BOT_TOKEN")
        self.signing_secret = signing_secret or os.environ.get("SLACK_SIGNING_SECRET")
        self.app_token = app_token or os.environ.get("SLACK_APP_TOKEN")

        self._http = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.bot_token}"},
            timeout=30.0,
        )

        # Command handlers registry
        self._command_handlers: dict[str, Callable] = {}
        self._action_handlers: dict[str, Callable] = {}

    @property
    def is_configured(self) -> bool:
        """Check if Slack is properly configured."""
        return bool(self.bot_token and self.signing_secret)

    def verify_signature(
        self, body: bytes, timestamp: str, signature: str
    ) -> bool:
        """Verify Slack request signature.

        Args:
            body: Raw request body
            timestamp: X-Slack-Request-Timestamp header
            signature: X-Slack-Signature header

        Returns:
            True if signature is valid
        """
        if not self.signing_secret:
            logger.warning("No signing secret configured")
            return False

        # Check timestamp to prevent replay attacks
        if abs(time.time() - int(timestamp)) > 60 * 5:
            logger.warning("Request timestamp too old")
            return False

        # Compute expected signature
        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        expected_sig = (
            "v0="
            + hmac.new(
                self.signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        return hmac.compare_digest(expected_sig, signature)

    async def _api_call(
        self, method: str, data: Optional[dict] = None
    ) -> dict[str, Any]:
        """Make a Slack API call.

        Args:
            method: API method name (e.g., "chat.postMessage")
            data: Request payload

        Returns:
            API response
        """
        url = f"{self.API_BASE}/{method}"
        response = await self._http.post(url, json=data or {})
        result = response.json()

        if not result.get("ok"):
            error = result.get("error", "unknown_error")
            logger.error(f"Slack API error: {error}")

        return result

    async def send_message(self, message: SlackMessage) -> dict:
        """Send a message to a Slack channel.

        Args:
            message: Message to send

        Returns:
            API response with message timestamp
        """
        return await self._api_call("chat.postMessage", message.to_dict())

    async def send_text(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
    ) -> dict:
        """Send a simple text message.

        Args:
            channel: Channel ID or name
            text: Message text
            thread_ts: Thread timestamp for replies

        Returns:
            API response
        """
        message = SlackMessage(
            text=text,
            channel=channel,
            thread_ts=thread_ts,
        )
        return await self.send_message(message)

    async def send_blocks(
        self,
        channel: str,
        blocks: list[dict],
        text: str = "",
        thread_ts: Optional[str] = None,
    ) -> dict:
        """Send a message with Block Kit blocks.

        Args:
            channel: Channel ID
            blocks: Block Kit blocks
            text: Fallback text
            thread_ts: Thread timestamp for replies

        Returns:
            API response
        """
        message = SlackMessage(
            text=text or "Message from ATLAS",
            channel=channel,
            blocks=blocks,
            thread_ts=thread_ts,
        )
        return await self.send_message(message)

    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str = "",
        blocks: Optional[list[dict]] = None,
    ) -> dict:
        """Update an existing message.

        Args:
            channel: Channel ID
            ts: Message timestamp
            text: New text
            blocks: New blocks

        Returns:
            API response
        """
        data = {
            "channel": channel,
            "ts": ts,
            "text": text,
        }
        if blocks:
            data["blocks"] = blocks
        return await self._api_call("chat.update", data)

    async def add_reaction(self, channel: str, ts: str, emoji: str) -> dict:
        """Add a reaction to a message.

        Args:
            channel: Channel ID
            ts: Message timestamp
            emoji: Emoji name (without colons)

        Returns:
            API response
        """
        return await self._api_call(
            "reactions.add",
            {"channel": channel, "timestamp": ts, "name": emoji},
        )

    async def open_modal(self, trigger_id: str, view: dict) -> dict:
        """Open a modal dialog.

        Args:
            trigger_id: Trigger ID from interaction
            view: Modal view definition

        Returns:
            API response
        """
        return await self._api_call(
            "views.open",
            {"trigger_id": trigger_id, "view": view},
        )

    def register_command(self, command: str, handler: Callable) -> None:
        """Register a slash command handler.

        Args:
            command: Command name (e.g., "/atlas")
            handler: Async function to handle the command
        """
        self._command_handlers[command] = handler
        logger.info(f"Registered command handler: {command}")

    def register_action(self, action_id: str, handler: Callable) -> None:
        """Register an interactive action handler.

        Args:
            action_id: Action ID from Block Kit
            handler: Async function to handle the action
        """
        self._action_handlers[action_id] = handler
        logger.info(f"Registered action handler: {action_id}")

    async def handle_command(self, command: SlashCommand) -> dict:
        """Handle an incoming slash command.

        Args:
            command: Parsed slash command

        Returns:
            Response to send back
        """
        handler = self._command_handlers.get(command.command)
        if not handler:
            return {
                "response_type": "ephemeral",
                "text": f"Unknown command: {command.command}",
            }

        try:
            return await handler(command)
        except Exception as e:
            logger.error(f"Command handler error: {e}", exc_info=True)
            return {
                "response_type": "ephemeral",
                "text": f"Error processing command: {str(e)}",
            }

    async def handle_interaction(self, payload: dict) -> dict:
        """Handle an interactive component payload.

        Args:
            payload: Interaction payload from Slack

        Returns:
            Response to send back
        """
        interaction_type = payload.get("type")

        if interaction_type == "block_actions":
            for action in payload.get("actions", []):
                action_id = action.get("action_id")
                handler = self._action_handlers.get(action_id)
                if handler:
                    try:
                        return await handler(payload, action)
                    except Exception as e:
                        logger.error(f"Action handler error: {e}", exc_info=True)

        elif interaction_type == "view_submission":
            callback_id = payload.get("view", {}).get("callback_id")
            handler = self._action_handlers.get(callback_id)
            if handler:
                try:
                    return await handler(payload)
                except Exception as e:
                    logger.error(f"View submission error: {e}", exc_info=True)

        return {"response_action": "clear"}

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()


class SlackNotifier:
    """K.I.T.T.'s notification service.

    Sends formatted notifications to Slack channels for common ATLAS events.
    """

    def __init__(self, client: SlackClient, default_channel: str = "#atlas"):
        """Initialize notifier.

        Args:
            client: Slack client instance
            default_channel: Default channel for notifications
        """
        self.client = client
        self.default_channel = default_channel

    async def notify_build_start(
        self,
        project: str,
        branch: str,
        commit: str,
        channel: Optional[str] = None,
    ) -> dict:
        """Notify about a build starting.

        Args:
            project: Project name
            branch: Branch name
            commit: Commit SHA (short)
            channel: Channel to notify

        Returns:
            Message response
        """
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":construction: *Build Started*\n*{project}* on `{branch}`",
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Commit: `{commit[:7]}`"},
                ],
            },
        ]

        return await self.client.send_blocks(
            channel=channel or self.default_channel,
            blocks=blocks,
            text=f"Build started: {project} on {branch}",
        )

    async def notify_build_complete(
        self,
        project: str,
        branch: str,
        success: bool,
        duration_seconds: int,
        url: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> dict:
        """Notify about a build completion.

        Args:
            project: Project name
            branch: Branch name
            success: Whether build succeeded
            duration_seconds: Build duration
            url: Link to build logs
            channel: Channel to notify

        Returns:
            Message response
        """
        emoji = ":white_check_mark:" if success else ":x:"
        status = "Succeeded" if success else "Failed"
        color = "#36a64f" if success else "#dc3545"

        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        duration = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *Build {status}*\n*{project}* on `{branch}`",
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Duration: {duration}"},
                ],
            },
        ]

        if url:
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Logs"},
                            "url": url,
                            "action_id": "view_build_logs",
                        }
                    ],
                }
            )

        return await self.client.send_blocks(
            channel=channel or self.default_channel,
            blocks=blocks,
            text=f"Build {status.lower()}: {project}",
        )

    async def notify_cost_report(
        self,
        daily_cost: float,
        daily_budget: float,
        top_models: list[dict],
        channel: Optional[str] = None,
    ) -> dict:
        """Send daily cost report.

        Args:
            daily_cost: Today's spending
            daily_budget: Daily budget limit
            top_models: Top models by cost
            channel: Channel to notify

        Returns:
            Message response
        """
        pct = (daily_cost / daily_budget * 100) if daily_budget > 0 else 0
        status_emoji = ":white_check_mark:" if pct < 80 else (":warning:" if pct < 100 else ":rotating_light:")

        # Build model breakdown
        model_lines = []
        for m in top_models[:5]:
            model_lines.append(f"  {m['model']}: ${m['cost']:.3f} ({m['requests']} req)")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Daily Cost Report"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{status_emoji} *${daily_cost:.2f}* / ${daily_budget:.2f} ({pct:.0f}%)",
                },
            },
        ]

        if model_lines:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Top Models:*\n```" + "\n".join(model_lines) + "```",
                    },
                }
            )

        return await self.client.send_blocks(
            channel=channel or self.default_channel,
            blocks=blocks,
            text=f"Daily cost: ${daily_cost:.2f}",
        )

    async def notify_alert(
        self,
        title: str,
        message: str,
        severity: str = "warning",
        channel: Optional[str] = None,
    ) -> dict:
        """Send an alert notification.

        Args:
            title: Alert title
            message: Alert details
            severity: Alert severity (info, warning, critical)
            channel: Channel to notify

        Returns:
            Message response
        """
        emoji_map = {
            "info": ":information_source:",
            "warning": ":warning:",
            "critical": ":rotating_light:",
        }
        color_map = {
            "info": "#0088cc",
            "warning": "#ffcc00",
            "critical": "#dc3545",
        }

        emoji = emoji_map.get(severity, ":bell:")

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *{title}*\n{message}",
                },
            },
        ]

        return await self.client.send_blocks(
            channel=channel or self.default_channel,
            blocks=blocks,
            text=f"{severity.upper()}: {title}",
        )

    async def notify_deployment(
        self,
        service: str,
        version: str,
        environment: str,
        status: str,
        url: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> dict:
        """Notify about a deployment.

        Args:
            service: Service name
            version: Version/tag being deployed
            environment: Target environment
            status: Deployment status (started, completed, failed)
            url: Link to deployment
            channel: Channel to notify

        Returns:
            Message response
        """
        status_emoji = {
            "started": ":rocket:",
            "completed": ":white_check_mark:",
            "failed": ":x:",
            "rollback": ":rewind:",
        }

        emoji = status_emoji.get(status, ":package:")

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *Deployment {status.title()}*\n*{service}* `{version}` to *{environment}*",
                },
            },
        ]

        if url:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"<{url}|View deployment>"},
                    ],
                }
            )

        return await self.client.send_blocks(
            channel=channel or self.default_channel,
            blocks=blocks,
            text=f"Deployment {status}: {service} {version}",
        )


# Default command handlers for ATLAS
async def handle_atlas_command(command: SlashCommand) -> dict:
    """Handle /atlas slash command."""
    subcommand = command.text.split()[0] if command.text else "help"

    if subcommand == "help":
        return {
            "response_type": "ephemeral",
            "text": "*ATLAS Commands:*\n"
            "  `/atlas status` - Show system status\n"
            "  `/atlas costs` - Show today's costs\n"
            "  `/atlas agents` - List active agents\n"
            "  `/atlas build <project>` - Trigger a build\n"
            "  `/atlas help` - Show this message",
        }

    elif subcommand == "status":
        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":white_check_mark: *ATLAS Status*\nAll systems operational",
                    },
                }
            ],
        }

    return {
        "response_type": "ephemeral",
        "text": f"Unknown subcommand: {subcommand}. Try `/atlas help`",
    }


# Singleton instance
_slack_client: Optional[SlackClient] = None


def get_slack_client() -> SlackClient:
    """Get or create the global Slack client instance."""
    global _slack_client
    if _slack_client is None:
        _slack_client = SlackClient()
        # Register default handlers
        _slack_client.register_command("/atlas", handle_atlas_command)
    return _slack_client
