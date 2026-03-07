"""
Buzz - ATLAS Communications Agent

The messenger. Buzz keeps everyone in the loop—routing notifications,
delivering updates, and making sure no important message gets lost in the void.

Handles:
- Agent completion notifications
- Project phase transitions
- Build status updates
- Error alerts
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("atlas.agents.buzz")

# Try to import Slack client, but don't fail if not configured
try:
    from atlas.integrations.slack import SlackClient, SlackNotifier, get_slack_client
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False


@dataclass
class BuzzConfig:
    """Configuration for Buzz notifications."""
    slack_enabled: bool = True
    slack_channel: str = "#atlas"
    web_push_enabled: bool = False
    email_enabled: bool = False


class Buzz:
    """ATLAS Communications Agent.

    Sends notifications when agents complete work, projects change phase,
    or important events occur. Currently supports Slack, with room to add
    email, web push, and other channels.
    """

    NAME = "Buzz"
    ICON = "📡"

    def __init__(self, config: Optional[BuzzConfig] = None):
        """Initialize Buzz.

        Args:
            config: Notification configuration
        """
        self.config = config or BuzzConfig()
        self._slack_client: Optional[SlackClient] = None
        self._slack_notifier: Optional[SlackNotifier] = None

        # Initialize Slack if available and configured
        if SLACK_AVAILABLE and self.config.slack_enabled:
            self._slack_client = get_slack_client()
            if self._slack_client.is_configured:
                self._slack_notifier = SlackNotifier(
                    self._slack_client,
                    self.config.slack_channel
                )
                logger.info(f"[{self.NAME}] Slack notifications enabled")
            else:
                logger.info(f"[{self.NAME}] Slack not configured (missing token)")

        # Track notification history for web UI
        self._recent_notifications: list[dict] = []

    @property
    def is_configured(self) -> bool:
        """Check if any notification channel is configured."""
        return (
            (self._slack_notifier is not None) or
            self.config.web_push_enabled or
            self.config.email_enabled
        )

    def _log_notification(self, event_type: str, message: str, data: dict = None):
        """Log a notification for the web UI."""
        from datetime import datetime
        notification = {
            "type": event_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        }
        self._recent_notifications.append(notification)
        # Keep only last 50
        if len(self._recent_notifications) > 50:
            self._recent_notifications = self._recent_notifications[-50:]

        logger.info(f"[{self.NAME}] {event_type}: {message}")

    def get_recent_notifications(self, limit: int = 10) -> list[dict]:
        """Get recent notifications for the web UI."""
        return self._recent_notifications[-limit:]

    # ==================== Agent Notifications ====================

    async def notify_idea_ready(
        self,
        project_id: int,
        project_name: str,
        readiness_score: int,
    ) -> bool:
        """Notify that an idea is ready for planning.

        Args:
            project_id: Project ID
            project_name: Project name
            readiness_score: Idea readiness percentage

        Returns:
            True if notification was sent
        """
        message = f"Idea '{project_name}' is ready for planning ({readiness_score}% clarity)"
        self._log_notification("idea_ready", message, {
            "project_id": project_id,
            "readiness_score": readiness_score,
        })

        if self._slack_notifier:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"💡 *Idea Ready for Planning*\n*{project_name}*",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Clarity: {readiness_score}%"},
                    ],
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Start Planning"},
                            "url": f"/projects/{project_id}",
                            "action_id": "start_planning",
                        }
                    ],
                },
            ]
            await self._slack_notifier.client.send_blocks(
                channel=self.config.slack_channel,
                blocks=blocks,
                text=message,
            )
            return True

        return False

    async def notify_sketch_complete(
        self,
        project_id: int,
        project_name: str,
        tokens_used: int = 0,
    ) -> bool:
        """Notify that Sketch finished planning.

        Args:
            project_id: Project ID
            project_name: Project name
            tokens_used: Tokens used for planning

        Returns:
            True if notification was sent
        """
        message = f"Sketch finished planning '{project_name}'"
        self._log_notification("sketch_complete", message, {
            "project_id": project_id,
            "tokens_used": tokens_used,
        })

        if self._slack_notifier:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"💡 *Sketch Finished Planning*\n*{project_name}*",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Tokens: {tokens_used:,}"},
                    ],
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Review Plan"},
                            "url": f"/projects/{project_id}",
                            "action_id": "review_plan",
                        }
                    ],
                },
            ]
            await self._slack_notifier.client.send_blocks(
                channel=self.config.slack_channel,
                blocks=blocks,
                text=message,
            )
            return True

        return False

    async def notify_tinker_complete(
        self,
        project_id: int,
        project_name: str,
        tokens_used: int = 0,
        files_generated: int = 0,
    ) -> bool:
        """Notify that Tinker finished building.

        Args:
            project_id: Project ID
            project_name: Project name
            tokens_used: Tokens used for building
            files_generated: Number of files generated

        Returns:
            True if notification was sent
        """
        message = f"Tinker finished building '{project_name}'"
        self._log_notification("tinker_complete", message, {
            "project_id": project_id,
            "tokens_used": tokens_used,
            "files_generated": files_generated,
        })

        if self._slack_notifier:
            context_parts = [f"Tokens: {tokens_used:,}"]
            if files_generated:
                context_parts.append(f"Files: {files_generated}")

            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🛠️ *Tinker Finished Building*\n*{project_name}*",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": " | ".join(context_parts)},
                    ],
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Review Build"},
                            "url": f"/projects/{project_id}",
                            "action_id": "review_build",
                        }
                    ],
                },
            ]
            await self._slack_notifier.client.send_blocks(
                channel=self.config.slack_channel,
                blocks=blocks,
                text=message,
            )
            return True

        return False

    async def notify_oracle_verdict(
        self,
        project_id: int,
        project_name: str,
        verdict: str,
        tokens_used: int = 0,
    ) -> bool:
        """Notify that Oracle finished verification.

        Args:
            project_id: Project ID
            project_name: Project name
            verdict: APPROVED or NEEDS_REVISION
            tokens_used: Tokens used for verification

        Returns:
            True if notification was sent
        """
        approved = verdict == "APPROVED"
        emoji = "✅" if approved else "⚠️"
        status = "Approved" if approved else "Needs Revision"

        message = f"Oracle {status.lower()} '{project_name}'"
        self._log_notification("oracle_verdict", message, {
            "project_id": project_id,
            "verdict": verdict,
            "tokens_used": tokens_used,
        })

        if self._slack_notifier:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🔮 *Oracle Verification: {status}*\n*{project_name}*",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"{emoji} {verdict} | Tokens: {tokens_used:,}"},
                    ],
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Report"},
                            "url": f"/projects/{project_id}",
                            "action_id": "view_verification",
                        }
                    ],
                },
            ]
            await self._slack_notifier.client.send_blocks(
                channel=self.config.slack_channel,
                blocks=blocks,
                text=message,
            )
            return True

        return False

    async def notify_project_complete(
        self,
        project_id: int,
        project_name: str,
        total_tokens: int = 0,
        files_written: list[str] = None,
    ) -> bool:
        """Notify that a project is complete and delivered.

        Args:
            project_id: Project ID
            project_name: Project name
            total_tokens: Total tokens used
            files_written: List of files written to disk

        Returns:
            True if notification was sent
        """
        file_count = len(files_written) if files_written else 0
        message = f"Project '{project_name}' is complete!"
        self._log_notification("project_complete", message, {
            "project_id": project_id,
            "total_tokens": total_tokens,
            "file_count": file_count,
        })

        if self._slack_notifier:
            context_parts = [f"Total tokens: {total_tokens:,}"]
            if file_count:
                context_parts.append(f"Files: {file_count}")

            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📤 *Project Complete!*\n*{project_name}*",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": " | ".join(context_parts)},
                    ],
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Project"},
                            "url": f"/projects/{project_id}",
                            "action_id": "view_project",
                        }
                    ],
                },
            ]
            await self._slack_notifier.client.send_blocks(
                channel=self.config.slack_channel,
                blocks=blocks,
                text=message,
            )
            return True

        return False

    async def notify_error(
        self,
        project_id: int,
        project_name: str,
        agent: str,
        error: str,
    ) -> bool:
        """Notify about an error during agent execution.

        Args:
            project_id: Project ID
            project_name: Project name
            agent: Agent that encountered the error
            error: Error message

        Returns:
            True if notification was sent
        """
        message = f"Error in {agent} for '{project_name}': {error[:100]}"
        self._log_notification("error", message, {
            "project_id": project_id,
            "agent": agent,
            "error": error,
        })

        if self._slack_notifier:
            await self._slack_notifier.notify_alert(
                title=f"{agent} Error",
                message=f"*Project:* {project_name}\n*Error:* {error[:500]}",
                severity="warning",
            )
            return True

        return False


    # ==================== Slack Conversation Methods ====================

    async def start_slack_conversation(
        self,
        channel: str,
        thread_ts: str,
        user_id: str,
        initial_idea: str,
    ) -> Optional[str]:
        """Start a Slack-based idea conversation.

        Args:
            channel: Slack channel ID
            thread_ts: Thread timestamp
            user_id: Slack user ID
            initial_idea: The initial idea text

        Returns:
            Response message to post, or None on failure
        """
        try:
            from atlas.integrations.slack_conversation import get_conversation_manager

            manager = get_conversation_manager()
            response, conversation_id = await manager.start_conversation(
                channel_id=channel,
                thread_ts=thread_ts,
                user_id=user_id,
                initial_idea=initial_idea,
            )

            self._log_notification("slack_conversation_started", f"Started conversation {conversation_id}", {
                "channel": channel,
                "thread_ts": thread_ts,
                "user_id": user_id,
            })

            return response

        except Exception as e:
            logger.error(f"Failed to start Slack conversation: {e}", exc_info=True)
            return None

    async def continue_slack_conversation(
        self,
        channel: str,
        thread_ts: str,
        message: str,
    ) -> Optional[str]:
        """Continue a Slack-based idea conversation.

        Args:
            channel: Slack channel ID
            thread_ts: Thread timestamp
            message: User's message

        Returns:
            Response message to post, or None on failure
        """
        try:
            from atlas.integrations.slack_conversation import get_conversation_manager

            manager = get_conversation_manager()
            response = await manager.continue_conversation(
                channel_id=channel,
                thread_ts=thread_ts,
                message=message,
            )

            return response

        except Exception as e:
            logger.error(f"Failed to continue Slack conversation: {e}", exc_info=True)
            return None

    async def post_idea_summary(
        self,
        channel: str,
        thread_ts: str,
        conversation_id: int,
        atlas_url: str = "",
    ) -> bool:
        """Post an idea summary with action buttons to Slack.

        Args:
            channel: Slack channel ID
            thread_ts: Thread timestamp
            conversation_id: Conversation ID
            atlas_url: Base URL for ATLAS

        Returns:
            True if posted successfully
        """
        try:
            from atlas.integrations.slack_conversation import get_conversation_manager
            from atlas.agents.smart_conversation import SmartIdeaConversation
            import os

            manager = get_conversation_manager()
            conv = await manager.get_conversation_by_id(conversation_id)

            if not conv:
                logger.error(f"Conversation {conversation_id} not found")
                return False

            # Restore conversation
            conversation = SmartIdeaConversation.from_dict(
                conv.conversation_state,
                openai_api_key=os.environ.get("OPENAI_API_KEY"),
            )

            # Get Block Kit blocks
            blocks = manager.get_idea_summary_blocks(
                conversation=conversation,
                conversation_id=conversation_id,
                atlas_url=atlas_url,
            )

            # Post to Slack
            if self._slack_client and self._slack_client.is_configured:
                await self._slack_client.send_blocks(
                    channel=channel,
                    blocks=blocks,
                    text=f"Idea ready: {conversation.brief.title}",
                    thread_ts=thread_ts,
                )

                self._log_notification("idea_summary_posted", f"Posted summary for conversation {conversation_id}", {
                    "channel": channel,
                    "thread_ts": thread_ts,
                    "title": conversation.brief.title,
                })

                return True

            return False

        except Exception as e:
            logger.error(f"Failed to post idea summary: {e}", exc_info=True)
            return False


# Singleton instance
_buzz: Optional[Buzz] = None


def get_buzz() -> Buzz:
    """Get or create the global Buzz instance."""
    global _buzz
    if _buzz is None:
        config = BuzzConfig(
            slack_enabled=os.environ.get("SLACK_BOT_TOKEN") is not None,
            slack_channel=os.environ.get("ATLAS_SLACK_CHANNEL", "#atlas"),
        )
        _buzz = Buzz(config)
    return _buzz
