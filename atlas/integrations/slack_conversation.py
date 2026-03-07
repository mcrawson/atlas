"""Slack Conversation Manager for ATLAS.

Adapts SmartIdeaConversation to work with Slack threads.
Stores conversation state in SQLite and formats responses for Slack.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger("atlas.integrations.slack_conversation")

# Character limit for Slack messages
SLACK_CHAR_LIMIT = 3000


@dataclass
class SlackConversation:
    """A Slack-based idea conversation."""

    id: int
    channel_id: str
    thread_ts: str
    user_id: str
    conversation_state: dict  # Serialized SmartIdeaConversation
    project_id: Optional[int] = None
    status: str = "active"  # active, completed, cancelled
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SlackConversationManager:
    """Manages Slack-based idea conversations.

    Bridges SmartIdeaConversation with Slack threads, storing
    conversation state in SQLite for persistence across messages.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the conversation manager.

        Args:
            data_dir: Directory for SQLite database
        """
        if data_dir is None:
            # Use ATLAS data directory
            data_dir = Path(__file__).parent.parent.parent / "data"

        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "slack_conversations.db"
        self._initialized = False

    async def init_db(self):
        """Initialize the database schema."""
        if self._initialized:
            return

        self.data_dir.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS slack_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    thread_ts TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    conversation_state TEXT DEFAULT '{}',
                    project_id INTEGER,
                    status TEXT DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(channel_id, thread_ts)
                )
            """)

            # Index for quick lookups
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_slack_conv_thread
                ON slack_conversations (channel_id, thread_ts)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_slack_conv_user
                ON slack_conversations (user_id, status)
            """)

            await db.commit()

        self._initialized = True
        logger.info("Slack conversations database initialized")

    async def start_conversation(
        self,
        channel_id: str,
        thread_ts: str,
        user_id: str,
        initial_idea: str,
    ) -> tuple[str, int]:
        """Start a new conversation from a Slack mention.

        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            user_id: Slack user ID
            initial_idea: The initial idea text

        Returns:
            Tuple of (response message, conversation ID)
        """
        await self.init_db()

        # Create SmartIdeaConversation
        from atlas.agents.smart_conversation import SmartIdeaConversation

        openai_key = os.environ.get("OPENAI_API_KEY")
        conversation = SmartIdeaConversation(
            openai_api_key=openai_key,
            openai_model="gpt-4o-mini",
        )

        # Start the conversation
        response = await conversation.start(initial_idea)

        # Serialize state
        state = conversation.to_dict()

        # Store in database
        now = datetime.now().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO slack_conversations
                (channel_id, thread_ts, user_id, conversation_state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (channel_id, thread_ts, user_id, json.dumps(state), now, now)
            )
            await db.commit()
            conversation_id = cursor.lastrowid

        logger.info(
            f"Started Slack conversation {conversation_id} "
            f"in {channel_id} thread {thread_ts}"
        )

        # Format response for Slack
        slack_response = self._format_for_slack(response, conversation)

        return slack_response, conversation_id

    async def continue_conversation(
        self,
        channel_id: str,
        thread_ts: str,
        message: str,
    ) -> Optional[str]:
        """Continue an existing conversation with a new message.

        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            message: User's message

        Returns:
            Response message, or None if conversation not found
        """
        await self.init_db()

        # Get existing conversation
        conv = await self.get_conversation(channel_id, thread_ts)
        if not conv:
            logger.warning(
                f"No conversation found for {channel_id}/{thread_ts}"
            )
            return None

        if conv.status != "active":
            logger.info(f"Conversation {conv.id} is {conv.status}, ignoring message")
            return None

        # Restore SmartIdeaConversation
        from atlas.agents.smart_conversation import SmartIdeaConversation

        openai_key = os.environ.get("OPENAI_API_KEY")
        conversation = SmartIdeaConversation.from_dict(
            conv.conversation_state,
            openai_api_key=openai_key,
            openai_model="gpt-4o-mini",
        )

        # Process the message
        response = await conversation.respond(message)

        # Check if conversation is complete
        new_status = "completed" if conversation.is_complete else "active"

        # Save updated state
        state = conversation.to_dict()
        now = datetime.now().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE slack_conversations
                SET conversation_state = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(state), new_status, now, conv.id)
            )
            await db.commit()

        logger.info(
            f"Continued conversation {conv.id}, "
            f"readiness: {conversation.brief.readiness_score}%, "
            f"complete: {conversation.is_complete}"
        )

        # Format response for Slack
        slack_response = self._format_for_slack(response, conversation)

        return slack_response

    async def get_conversation(
        self,
        channel_id: str,
        thread_ts: str,
    ) -> Optional[SlackConversation]:
        """Get a conversation by channel and thread.

        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp

        Returns:
            SlackConversation or None
        """
        await self.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM slack_conversations
                WHERE channel_id = ? AND thread_ts = ?
                """,
                (channel_id, thread_ts)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return SlackConversation(
                id=row["id"],
                channel_id=row["channel_id"],
                thread_ts=row["thread_ts"],
                user_id=row["user_id"],
                conversation_state=json.loads(row["conversation_state"]),
                project_id=row["project_id"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    async def get_conversation_by_id(
        self,
        conversation_id: int,
    ) -> Optional[SlackConversation]:
        """Get a conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            SlackConversation or None
        """
        await self.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM slack_conversations WHERE id = ?",
                (conversation_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return SlackConversation(
                id=row["id"],
                channel_id=row["channel_id"],
                thread_ts=row["thread_ts"],
                user_id=row["user_id"],
                conversation_state=json.loads(row["conversation_state"]),
                project_id=row["project_id"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    async def link_project(
        self,
        conversation_id: int,
        project_id: int,
    ) -> bool:
        """Link a conversation to a created project.

        Args:
            conversation_id: Conversation ID
            project_id: Project ID in ATLAS

        Returns:
            True if updated
        """
        await self.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE slack_conversations
                SET project_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (project_id, datetime.now().isoformat(), conversation_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def complete_conversation(
        self,
        conversation_id: int,
    ) -> bool:
        """Mark a conversation as completed.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if updated
        """
        await self.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE slack_conversations
                SET status = 'completed', updated_at = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), conversation_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    def _format_for_slack(
        self,
        response: str,
        conversation,
    ) -> str:
        """Format a response for Slack.

        Args:
            response: Raw response text
            conversation: SmartIdeaConversation instance

        Returns:
            Slack-formatted response
        """
        # Truncate if too long
        if len(response) > SLACK_CHAR_LIMIT:
            response = response[:SLACK_CHAR_LIMIT - 100] + "\n\n_(message truncated)_"

        # Add readiness indicator if conversation is in progress
        if not conversation.is_complete and conversation.brief.readiness_score > 0:
            progress = conversation.brief.readiness_score
            bar_filled = int(progress / 10)
            bar_empty = 10 - bar_filled
            progress_bar = ">" * bar_filled + "-" * bar_empty
            response += f"\n\n`[{progress_bar}] {progress}% ready`"

        return response

    def get_idea_summary_blocks(
        self,
        conversation,
        conversation_id: int,
        atlas_url: str = "",
    ) -> list[dict]:
        """Generate Block Kit blocks for idea summary.

        Args:
            conversation: SmartIdeaConversation instance
            conversation_id: Conversation ID for button value
            atlas_url: Base URL for ATLAS (optional)

        Returns:
            List of Block Kit blocks
        """
        brief = conversation.brief

        # Build feature list
        features_text = "\n".join(
            f"- {f}" for f in brief.core_features[:5]
        ) if brief.core_features else "_No features defined_"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Idea Ready: {brief.title}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": brief.description[:500] if brief.description else "_No description_",
                },
            },
            {
                "type": "divider",
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Problem:*\n{brief.problem_statement[:200] if brief.problem_statement else 'Not defined'}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Target Users:*\n{brief.target_users[:200] if brief.target_users else 'Not defined'}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Core Features:*\n{features_text}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Scope:*\n{brief.scope or 'Not defined'}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Readiness:*\n{brief.readiness_score}/100",
                    },
                ],
            },
            {
                "type": "divider",
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Create Project",
                            "emoji": True,
                        },
                        "style": "primary",
                        "action_id": "create_project",
                        "value": str(conversation_id),
                    },
                ],
            },
        ]

        # Add "View in ATLAS" button if URL is provided
        if atlas_url:
            blocks[-1]["elements"].append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "View in ATLAS",
                    "emoji": True,
                },
                "action_id": "view_in_atlas",
                "url": atlas_url,
            })

        return blocks


# Singleton instance
_conversation_manager: Optional[SlackConversationManager] = None


def get_conversation_manager() -> SlackConversationManager:
    """Get or create the global conversation manager."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = SlackConversationManager()
    return _conversation_manager
