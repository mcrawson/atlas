"""Slack webhook routes for ATLAS.

Handles incoming Slack events, commands, and interactive actions.
Routes messages to appropriate handlers for two-way Slack integration.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException, Depends

logger = logging.getLogger("atlas.web.routes.slack")

router = APIRouter()


def get_slack_client():
    """Get the Slack client from app state."""
    from atlas.integrations.slack import get_slack_client
    return get_slack_client()


def get_slack_handlers():
    """Get the Slack handlers module."""
    from atlas.integrations import slack_handlers
    return slack_handlers


async def verify_slack_request(request: Request) -> bytes:
    """Verify Slack request signature.

    Args:
        request: FastAPI request

    Returns:
        Raw request body

    Raises:
        HTTPException: If verification fails
    """
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    slack_client = get_slack_client()

    if not slack_client.verify_signature(body, timestamp, signature):
        logger.warning("Slack signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    return body


@router.post("/events")
async def slack_events(request: Request):
    """Handle Slack Events API webhooks.

    Handles:
    - URL verification challenge
    - app_mention events (when @atlas is mentioned)
    - message events (thread replies)
    """
    body = await request.body()

    # Parse JSON
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle URL verification challenge (no signature check needed)
    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge", "")
        logger.info("Slack URL verification challenge received")
        return {"challenge": challenge}

    # Verify signature for all other requests
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    slack_client = get_slack_client()

    if not slack_client.verify_signature(body, timestamp, signature):
        logger.warning("Slack signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Handle event callbacks
    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        event_type = event.get("type")

        logger.info(f"Received Slack event: {event_type}")

        handlers = get_slack_handlers()

        # Process events in background to respond quickly to Slack
        # Slack retries if we don't respond within 3 seconds
        import asyncio

        if event_type == "app_mention":
            # User mentioned @atlas - start new conversation
            asyncio.create_task(handlers.handle_app_mention(event))

        elif event_type == "message":
            # Check if this is a thread reply (not a bot message)
            if event.get("thread_ts") and not event.get("bot_id"):
                asyncio.create_task(handlers.handle_message(event))

        # Return immediately so Slack doesn't retry
        return Response(status_code=200)

    return Response(status_code=200)


@router.post("/commands")
async def slack_commands(request: Request):
    """Handle Slack slash commands.

    Handles commands like:
    - /atlas idea <description>
    - /atlas status
    - /atlas help
    """
    body = await verify_slack_request(request)

    # Parse form data
    form_data = {}
    for item in body.decode().split("&"):
        if "=" in item:
            key, value = item.split("=", 1)
            from urllib.parse import unquote_plus
            form_data[key] = unquote_plus(value)

    command = form_data.get("command", "")
    text = form_data.get("text", "")
    user_id = form_data.get("user_id", "")
    user_name = form_data.get("user_name", "")
    channel_id = form_data.get("channel_id", "")
    channel_name = form_data.get("channel_name", "")
    response_url = form_data.get("response_url", "")
    trigger_id = form_data.get("trigger_id", "")

    logger.info(f"Received Slack command: {command} {text} from {user_name}")

    from atlas.integrations.slack import SlashCommand
    parsed_command = SlashCommand(
        command=command,
        text=text,
        user_id=user_id,
        user_name=user_name,
        channel_id=channel_id,
        channel_name=channel_name,
        team_id=form_data.get("team_id", ""),
        response_url=response_url,
        trigger_id=trigger_id,
    )

    slack_client = get_slack_client()
    response = await slack_client.handle_command(parsed_command)

    return response


@router.post("/actions")
async def slack_actions(request: Request):
    """Handle Slack interactive component actions.

    Handles:
    - Button clicks (Create Project, View in ATLAS)
    - Modal submissions
    """
    body = await verify_slack_request(request)

    # Parse form data - Slack sends payload as form-encoded
    form_data = {}
    for item in body.decode().split("&"):
        if "=" in item:
            key, value = item.split("=", 1)
            from urllib.parse import unquote_plus
            form_data[key] = unquote_plus(value)

    # Parse the payload JSON
    payload_str = form_data.get("payload", "{}")
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid payload JSON")

    action_type = payload.get("type")
    logger.info(f"Received Slack action: {action_type}")

    handlers = get_slack_handlers()

    if action_type == "block_actions":
        # Button clicks
        actions = payload.get("actions", [])
        for action in actions:
            action_id = action.get("action_id", "")

            if action_id == "create_project":
                result = await handlers.handle_create_project_action(payload, action)
                return result

            elif action_id == "view_in_atlas":
                # Just acknowledge - the button has a URL that opens ATLAS
                return Response(status_code=200)

    elif action_type == "view_submission":
        # Modal form submission
        callback_id = payload.get("view", {}).get("callback_id", "")
        result = await handlers.handle_modal_submission(payload, callback_id)
        return result

    return Response(status_code=200)
