"""Slack event handlers for ATLAS.

Handles Slack events routed from the webhook endpoints:
- app_mention: When @atlas is mentioned, start a conversation
- message: When user replies in a thread, continue conversation
- actions: When user clicks buttons (Create Project, etc.)
"""

import asyncio
import logging
import os
import re
import time
from typing import Optional, Set

logger = logging.getLogger("atlas.integrations.slack_handlers")

# Track processed events to prevent duplicates (Slack retries if we're slow)
_processed_events: Set[str] = set()
_processed_events_timestamps: dict[str, float] = {}
MAX_EVENT_AGE = 60  # seconds to remember processed events


def _is_duplicate_event(event_id: str) -> bool:
    """Check if we've already processed this event.

    Args:
        event_id: Unique event identifier

    Returns:
        True if this is a duplicate
    """
    # Clean old events
    now = time.time()
    old_events = [eid for eid, ts in _processed_events_timestamps.items() if now - ts > MAX_EVENT_AGE]
    for eid in old_events:
        _processed_events.discard(eid)
        _processed_events_timestamps.pop(eid, None)

    # Check if duplicate
    if event_id in _processed_events:
        return True

    # Mark as processed
    _processed_events.add(event_id)
    _processed_events_timestamps[event_id] = now
    return False


def _extract_idea_from_mention(text: str) -> str:
    """Extract the idea text from a mention.

    Removes the @atlas mention and cleans up the text.

    Args:
        text: Raw message text with mention

    Returns:
        Cleaned idea text
    """
    # Remove <@U12345> style mentions
    cleaned = re.sub(r"<@[A-Z0-9]+>", "", text)
    # Remove multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


async def handle_app_mention(event: dict) -> None:
    """Handle @atlas mention - start a new conversation.

    Args:
        event: Slack event payload
    """
    from atlas.integrations.slack import get_slack_client
    from atlas.integrations.slack_conversation import get_conversation_manager
    from atlas.agents.buzz import get_buzz

    channel = event.get("channel", "")
    user = event.get("user", "")
    text = event.get("text", "")
    ts = event.get("ts", "")  # Message timestamp (becomes thread_ts)
    event_ts = event.get("event_ts", ts)

    # Deduplicate - Slack retries if we're slow
    event_id = f"mention:{channel}:{event_ts}"
    if _is_duplicate_event(event_id):
        logger.debug(f"Skipping duplicate app_mention event: {event_id}")
        return

    logger.info(f"App mention from {user} in {channel}: {text[:50]}...")

    # Extract the idea from the mention
    idea = _extract_idea_from_mention(text)

    if not idea:
        # No idea provided, send a helpful message
        slack = get_slack_client()
        await slack.send_text(
            channel=channel,
            text=(
                "Hi! I'm Buzz, here to help flesh out your ideas. "
                "What would you like to build? Just tell me your idea and "
                "I'll ask some questions to make sure we understand it fully."
            ),
            thread_ts=ts,
        )
        return

    # Start a new conversation
    manager = get_conversation_manager()

    try:
        response, conversation_id = await manager.start_conversation(
            channel_id=channel,
            thread_ts=ts,
            user_id=user,
            initial_idea=idea,
        )

        # Send the response in a thread
        slack = get_slack_client()
        await slack.send_text(
            channel=channel,
            text=response,
            thread_ts=ts,
        )

        logger.info(f"Started conversation {conversation_id} for idea: {idea[:50]}...")

    except Exception as e:
        logger.error(f"Failed to start conversation: {e}", exc_info=True)
        slack = get_slack_client()
        await slack.send_text(
            channel=channel,
            text="Sorry, I encountered an error starting the conversation. Please try again.",
            thread_ts=ts,
        )


async def handle_message(event: dict) -> None:
    """Handle thread reply - continue an existing conversation.

    Args:
        event: Slack event payload
    """
    from atlas.integrations.slack import get_slack_client
    from atlas.integrations.slack_conversation import get_conversation_manager
    from atlas.agents.smart_conversation import SmartIdeaConversation

    channel = event.get("channel", "")
    user = event.get("user", "")
    text = event.get("text", "")
    thread_ts = event.get("thread_ts", "")
    event_ts = event.get("event_ts", event.get("ts", ""))

    # Ignore bot messages
    if event.get("bot_id"):
        logger.debug("Ignoring bot message")
        return

    # Ignore messages from apps/bots
    if event.get("subtype") in ("bot_message", "message_changed", "message_deleted"):
        logger.debug(f"Ignoring message subtype: {event.get('subtype')}")
        return

    # Deduplicate - Slack retries if we're slow
    event_id = f"message:{channel}:{event_ts}"
    if _is_duplicate_event(event_id):
        logger.debug(f"Skipping duplicate message event: {event_id}")
        return

    logger.info(f"Thread message from {user} in {channel}/{thread_ts}: {text[:50]}...")

    # Get conversation manager
    manager = get_conversation_manager()

    # Check if there's an active conversation for this thread
    conv = await manager.get_conversation(channel, thread_ts)
    if not conv:
        # No conversation for this thread, ignore
        logger.debug(f"No conversation found for thread {thread_ts}")
        return

    if conv.status != "active":
        logger.debug(f"Conversation {conv.id} is {conv.status}, ignoring")
        return

    try:
        # Continue the conversation
        response = await manager.continue_conversation(
            channel_id=channel,
            thread_ts=thread_ts,
            message=text,
        )

        if not response:
            return

        slack = get_slack_client()

        # Check if conversation is now complete
        conv = await manager.get_conversation(channel, thread_ts)
        conversation = SmartIdeaConversation.from_dict(
            conv.conversation_state,
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
        )

        if conversation.is_complete:
            # Send summary with action buttons
            atlas_url = os.environ.get("ATLAS_URL", "")
            blocks = manager.get_idea_summary_blocks(
                conversation=conversation,
                conversation_id=conv.id,
                atlas_url=atlas_url,
            )

            await slack.send_blocks(
                channel=channel,
                blocks=blocks,
                text=f"Idea ready: {conversation.brief.title}",
                thread_ts=thread_ts,
            )
        else:
            # Send regular response
            await slack.send_text(
                channel=channel,
                text=response,
                thread_ts=thread_ts,
            )

        logger.info(
            f"Continued conversation {conv.id}, "
            f"complete: {conversation.is_complete}"
        )

    except Exception as e:
        logger.error(f"Failed to continue conversation: {e}", exc_info=True)
        slack = get_slack_client()
        await slack.send_text(
            channel=channel,
            text="Sorry, I encountered an error. Please try again.",
            thread_ts=thread_ts,
        )


async def handle_create_project_action(payload: dict, action: dict) -> dict:
    """Handle Create Project button click.

    Args:
        payload: Full interaction payload
        action: The specific action that was clicked

    Returns:
        Response dict
    """
    from atlas.integrations.slack import get_slack_client
    from atlas.integrations.slack_conversation import get_conversation_manager
    from atlas.agents.smart_conversation import SmartIdeaConversation
    from atlas.projects.manager import ProjectManager
    from pathlib import Path

    conversation_id = int(action.get("value", "0"))
    user = payload.get("user", {})
    user_id = user.get("id", "")
    channel = payload.get("channel", {})
    channel_id = channel.get("id", "")
    message = payload.get("message", {})
    thread_ts = message.get("thread_ts") or message.get("ts", "")

    logger.info(f"Create project action for conversation {conversation_id}")

    manager = get_conversation_manager()
    slack = get_slack_client()

    try:
        # Get conversation
        conv = await manager.get_conversation_by_id(conversation_id)
        if not conv:
            logger.error(f"Conversation {conversation_id} not found")
            await slack.send_text(
                channel=channel_id,
                text="Sorry, I couldn't find that conversation. Please try again.",
                thread_ts=thread_ts,
            )
            return {"response_action": "clear"}

        # Restore conversation state
        conversation = SmartIdeaConversation.from_dict(
            conv.conversation_state,
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
        )

        brief = conversation.brief

        # Create project in ATLAS
        data_dir = Path(__file__).parent.parent.parent / "data"
        project_manager = ProjectManager(data_dir)

        # Build metadata from brief
        metadata = {
            "source": "slack",
            "slack_channel": conv.channel_id,
            "slack_thread": conv.thread_ts,
            "slack_user": conv.user_id,
            "idea_type": brief.idea_type,
            "readiness_score": brief.readiness_score,
            "core_features": brief.core_features,
            "success_criteria": brief.success_criteria,
            "target_users": brief.target_users,
            "problem_statement": brief.problem_statement,
            "scope": brief.scope,
            "technical_requirements": brief.technical_requirements,
            "constraints": brief.constraints,
        }

        project = await project_manager.create_project(
            name=brief.title or "Untitled Project",
            description=brief.description or "",
            metadata=metadata,
        )

        # Link conversation to project
        await manager.link_project(conversation_id, project.id)
        await manager.complete_conversation(conversation_id)

        logger.info(f"Created project {project.id}: {project.name}")

        # Send confirmation
        atlas_url = os.environ.get("ATLAS_URL", "")
        project_url = f"{atlas_url}/projects/{project.id}" if atlas_url else ""

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":white_check_mark: *Project Created!*\n*{project.name}*",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Project ID: {project.id} | Created by <@{user_id}>",
                    },
                ],
            },
        ]

        if project_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Open in ATLAS",
                            "emoji": True,
                        },
                        "url": project_url,
                        "action_id": "open_project",
                    },
                ],
            })

        await slack.send_blocks(
            channel=channel_id,
            blocks=blocks,
            text=f"Project created: {project.name}",
            thread_ts=thread_ts,
        )

        # Notify via Buzz
        from atlas.agents.buzz import get_buzz
        buzz = get_buzz()
        await buzz.notify_idea_ready(
            project_id=project.id,
            project_name=project.name,
            readiness_score=brief.readiness_score,
        )

        return {"response_action": "clear"}

    except Exception as e:
        logger.error(f"Failed to create project: {e}", exc_info=True)
        await slack.send_text(
            channel=channel_id,
            text=f"Sorry, I couldn't create the project: {str(e)}",
            thread_ts=thread_ts,
        )
        return {"response_action": "clear"}


async def handle_modal_submission(payload: dict, callback_id: str) -> dict:
    """Handle modal form submissions.

    Args:
        payload: Full interaction payload
        callback_id: Modal callback ID

    Returns:
        Response dict
    """
    logger.info(f"Modal submission: {callback_id}")

    # Currently no modals implemented
    # Add handlers here as needed

    return {"response_action": "clear"}


def get_error_blocks(title: str, message: str) -> list[dict]:
    """Generate error message blocks.

    Args:
        title: Error title
        message: Error details

    Returns:
        List of Block Kit blocks
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":x: *{title}*\n{message}",
            },
        },
    ]


def get_success_blocks(title: str, message: str) -> list[dict]:
    """Generate success message blocks.

    Args:
        title: Success title
        message: Details

    Returns:
        List of Block Kit blocks
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":white_check_mark: *{title}*\n{message}",
            },
        },
    ]
