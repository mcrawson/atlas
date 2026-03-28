"""
Slack integration for the Overnight Operator.

Reads tasks from a Slack channel and posts briefings back.
"""

import os
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)


class SlackClient:
    """Simple async Slack client for the overnight operator."""

    BASE_URL = "https://slack.com/api"

    def __init__(self, token: Optional[str] = None, channel: Optional[str] = None):
        self.token = token or os.environ.get("SLACK_BOT_TOKEN")
        self.channel = channel or os.environ.get("SLACK_CHANNEL", "overnight-agent")
        self._channel_id: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        """Check if Slack is configured."""
        return bool(self.token)

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an authenticated request to Slack API."""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/{endpoint}"
            async with session.request(method, url, headers=headers, **kwargs) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    logger.error(f"Slack API error: {data.get('error')}")
                return data

    async def get_channel_id(self) -> Optional[str]:
        """Get the channel ID for the configured channel name."""
        if self._channel_id:
            return self._channel_id

        # Try public channels first
        data = await self._request("GET", "conversations.list", params={
            "types": "public_channel,private_channel",
            "limit": 200,
        })

        if data.get("ok"):
            for channel in data.get("channels", []):
                if channel.get("name") == self.channel:
                    self._channel_id = channel.get("id")
                    return self._channel_id

        logger.warning(f"Could not find channel: {self.channel}")
        return None

    async def get_recent_messages(self, hours: int = 24) -> list[dict]:
        """Get messages from the channel in the last N hours."""
        channel_id = await self.get_channel_id()
        if not channel_id:
            return []

        oldest = (datetime.now() - timedelta(hours=hours)).timestamp()

        data = await self._request("GET", "conversations.history", params={
            "channel": channel_id,
            "oldest": str(oldest),
            "limit": 100,
        })

        if not data.get("ok"):
            return []

        messages = []
        for msg in data.get("messages", []):
            # Skip bot messages and system messages
            if msg.get("bot_id") or msg.get("subtype"):
                continue
            messages.append(msg)

        return messages

    async def parse_tasks_from_messages(self, messages: list[dict]) -> list[dict]:
        """Parse task definitions from Slack messages."""
        tasks = []

        for msg in messages:
            text = msg.get("text", "").strip()
            if not text:
                continue

            # Strip Slack user mentions like <@U0AQ6GSDPAL>
            text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()

            # Strip Slack channel mentions like <#C0AK9N1R7J5|channel-name>
            text = re.sub(r'<#[A-Z0-9]+\|[^>]+>', '', text).strip()

            # Strip URLs that Slack wraps like <http://example.com|example.com>
            text = re.sub(r'<(https?://[^|>]+)\|[^>]+>', r'\1', text)

            if not text:
                continue

            # Parse task type from tags like [atlas-fix] or [atlas-build]
            task_type = None
            if "[atlas-fix]" in text.lower():
                task_type = "atlas-fix"
                text = re.sub(r'\[atlas-fix\]', '', text, flags=re.IGNORECASE).strip()
            elif "[atlas-build]" in text.lower():
                task_type = "atlas-build"
                text = re.sub(r'\[atlas-build\]', '', text, flags=re.IGNORECASE).strip()
            elif "[fix]" in text.lower():
                task_type = "atlas-fix"
                text = re.sub(r'\[fix\]', '', text, flags=re.IGNORECASE).strip()
            elif "[build]" in text.lower():
                task_type = "atlas-build"
                text = re.sub(r'\[build\]', '', text, flags=re.IGNORECASE).strip()
            elif "[research]" in text.lower():
                task_type = "general"
                text = re.sub(r'\[research\]', '', text, flags=re.IGNORECASE).strip()

            # Parse priority from [p1], [p2], etc.
            priority = 0
            priority_match = re.search(r'\[p(\d+)\]', text, re.IGNORECASE)
            if priority_match:
                priority = int(priority_match.group(1))
                text = re.sub(r'\[p\d+\]', '', text, flags=re.IGNORECASE).strip()

            if text:
                tasks.append({
                    "prompt": text,
                    "type": task_type,
                    "priority": priority,
                    "ts": msg.get("ts"),  # Message timestamp for reactions
                })

        return tasks

    async def add_reaction(self, message_ts: str, emoji: str = "white_check_mark") -> bool:
        """Add a reaction to a message."""
        channel_id = await self.get_channel_id()
        if not channel_id:
            return False

        data = await self._request("POST", "reactions.add", json={
            "channel": channel_id,
            "timestamp": message_ts,
            "name": emoji,
        })

        return data.get("ok", False)

    async def post_message(self, text: str, thread_ts: Optional[str] = None) -> bool:
        """Post a message to the channel."""
        channel_id = await self.get_channel_id()
        if not channel_id:
            return False

        payload = {
            "channel": channel_id,
            "text": text,
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts

        data = await self._request("POST", "chat.postMessage", json=payload)
        return data.get("ok", False)

    async def post_briefing(self, briefing: str) -> bool:
        """Post the morning briefing to the channel."""
        return await self.post_message(briefing)

    async def upload_file(self, content: str, filename: str, title: str) -> bool:
        """Upload a file using Slack's new files.uploadV2 API."""
        channel_id = await self.get_channel_id()
        if not channel_id:
            return False

        try:
            # Step 1: Get upload URL
            data = await self._request("POST", "files.getUploadURLExternal", json={
                "filename": filename,
                "length": len(content.encode('utf-8')),
            })

            if not data.get("ok"):
                logger.error(f"Failed to get upload URL: {data.get('error')}")
                return False

            upload_url = data.get("upload_url")
            file_id = data.get("file_id")

            # Step 2: Upload content to the URL
            async with aiohttp.ClientSession() as session:
                async with session.post(upload_url, data=content.encode('utf-8')) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to upload file content: {resp.status}")
                        return False

            # Step 3: Complete the upload
            complete_data = await self._request("POST", "files.completeUploadExternal", json={
                "files": [{"id": file_id, "title": title}],
                "channel_id": channel_id,
            })

            return complete_data.get("ok", False)

        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return False

    async def post_full_report(self, briefing_msg_ts: str, content: str) -> bool:
        """Post the full report as a thread reply (fallback if file upload fails)."""
        # Split into chunks if too long (Slack limit is ~40k chars)
        max_len = 3900  # Leave room for formatting

        if len(content) <= max_len:
            return await self.post_message(f"*Full Report:*\n```{content}```", thread_ts=briefing_msg_ts)

        # Split into multiple messages
        chunks = [content[i:i+max_len] for i in range(0, len(content), max_len)]
        success = True
        for i, chunk in enumerate(chunks):
            header = f"*Full Report (Part {i+1}/{len(chunks)}):*\n" if len(chunks) > 1 else "*Full Report:*\n"
            result = await self.post_message(f"{header}```{chunk}```", thread_ts=briefing_msg_ts)
            success = success and result

        return success

    async def notify_start(self) -> bool:
        """Notify that the overnight session is starting."""
        return await self.post_message(
            ":moon: *Overnight session starting...*\n"
            "I'll process your tasks and report back when done."
        )

    async def notify_task_received(self, task: dict) -> bool:
        """Acknowledge a task with a reaction."""
        if task.get("ts"):
            return await self.add_reaction(task["ts"], "eyes")
        return False

    async def notify_task_complete(self, task: dict, success: bool) -> bool:
        """Mark a task as complete with a reaction."""
        if task.get("ts"):
            emoji = "white_check_mark" if success else "x"
            return await self.add_reaction(task["ts"], emoji)
        return False
