"""WebSocket handler for real-time updates and agent conversation streaming."""

import asyncio
import json
import logging
from typing import Set, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

# Active WebSocket connections (global)
active_connections: Set[WebSocket] = set()

# Per-project connections for agent conversations
project_connections: Dict[int, Set[WebSocket]] = {}


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.project_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept and register a new connection."""
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a connection."""
        self.connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connections."""
        if not self.connections:
            return

        message_str = json.dumps(message)
        disconnected = set()

        for connection in self.connections:
            try:
                await connection.send_text(message_str)
            except Exception:
                disconnected.add(connection)

        # Clean up disconnected clients
        self.connections -= disconnected

    async def send_to(self, websocket: WebSocket, message: dict):
        """Send a message to a specific connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            self.connections.discard(websocket)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates.

    Message types sent to clients:
    - agent_status: Agent status updates
    - workflow_start: Workflow has started
    - workflow_complete: Workflow has completed
    - workflow_error: Workflow encountered an error
    - activity: General activity feed updates
    """
    await manager.connect(websocket)

    # Get agent manager if available
    agent_manager = websocket.app.state.agent_manager

    # Register callback for agent events
    def on_workflow_event(event):
        """Forward workflow events to WebSocket."""
        asyncio.create_task(manager.broadcast({
            "type": event.event_type,
            "agent": event.agent_name,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
        }))

    if agent_manager:
        agent_manager.register_event_callback(on_workflow_event)

    try:
        # Send initial status
        if agent_manager:
            await manager.send_to(websocket, {
                "type": "init",
                "agents": agent_manager.get_all_status(),
            })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # Ping every 30 seconds
                )

                # Handle incoming messages (e.g., task submission)
                try:
                    message = json.loads(data)
                    await handle_message(websocket, message)
                except json.JSONDecodeError:
                    await manager.send_to(websocket, {
                        "type": "error",
                        "message": "Invalid JSON",
                    })

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
        if agent_manager:
            agent_manager.unregister_event_callback(on_workflow_event)


async def handle_message(websocket: WebSocket, message: dict):
    """Handle incoming WebSocket messages."""
    msg_type = message.get("type")

    if msg_type == "pong":
        # Heartbeat response
        return

    elif msg_type == "get_status":
        # Request current status
        agent_manager = websocket.app.state.agent_manager
        if agent_manager:
            await manager.send_to(websocket, {
                "type": "status",
                "agents": agent_manager.get_all_status(),
            })

    elif msg_type == "execute_task":
        # Execute a task via WebSocket
        agent_manager = websocket.app.state.agent_manager
        if not agent_manager:
            await manager.send_to(websocket, {
                "type": "error",
                "message": "Agent manager not available",
            })
            return

        task = message.get("task")
        mode = message.get("mode", "sequential")

        if not task:
            await manager.send_to(websocket, {
                "type": "error",
                "message": "Task is required",
            })
            return

        from atlas.agents.manager import WorkflowMode

        mode_map = {
            "sequential": WorkflowMode.SEQUENTIAL,
            "direct_build": WorkflowMode.DIRECT_BUILD,
            "verify_only": WorkflowMode.VERIFY_ONLY,
        }

        try:
            outputs = await agent_manager.execute_workflow(
                task=task,
                mode=mode_map.get(mode, WorkflowMode.SEQUENTIAL),
            )

            results = {}
            for agent_name, output in outputs.items():
                if hasattr(output, 'to_dict'):
                    results[agent_name] = output.to_dict()

            await manager.send_to(websocket, {
                "type": "task_complete",
                "task": task,
                "results": results,
            })

        except Exception as e:
            await manager.send_to(websocket, {
                "type": "task_error",
                "task": task,
                "error": str(e),
            })

    else:
        await manager.send_to(websocket, {
            "type": "error",
            "message": f"Unknown message type: {msg_type}",
        })


async def broadcast_event(event_type: str, data: dict):
    """Broadcast an event to all connected clients.

    This function can be called from other parts of the application
    to push updates to all connected WebSocket clients.
    """
    await manager.broadcast({
        "type": event_type,
        **data,
    })


# ============================================================================
# Project-specific WebSocket for Agent Conversation Streaming
# ============================================================================

class ProjectConnectionManager:
    """Manages WebSocket connections per project for agent conversations."""

    def __init__(self):
        self.connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, project_id: int) -> None:
        """Accept a new WebSocket connection for a project."""
        await websocket.accept()

        async with self._lock:
            if project_id not in self.connections:
                self.connections[project_id] = set()
            self.connections[project_id].add(websocket)

        logger.info(f"WebSocket connected for project {project_id}")

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "project_id": project_id,
            "message": "Connected to agent conversation stream"
        })

        # Register with message broker
        try:
            from ..agents.message_broker import get_broker
            broker = get_broker(project_id)

            # Create async callback for this project
            async def ui_callback(msg):
                await self.send_to_project(project_id, msg)

            broker.subscribe_ui(ui_callback)
        except Exception as e:
            logger.warning(f"Could not subscribe to broker: {e}")

    async def disconnect(self, websocket: WebSocket, project_id: int) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if project_id in self.connections:
                self.connections[project_id].discard(websocket)
                if not self.connections[project_id]:
                    del self.connections[project_id]

        logger.info(f"WebSocket disconnected for project {project_id}")

    async def send_to_project(self, project_id: int, message: dict) -> None:
        """Send a message to all connections for a project."""
        if project_id not in self.connections:
            return

        dead_connections = set()

        for websocket in self.connections[project_id].copy():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to websocket: {e}")
                dead_connections.add(websocket)

        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                for ws in dead_connections:
                    if project_id in self.connections:
                        self.connections[project_id].discard(ws)

    async def send_history(self, websocket: WebSocket, project_id: int) -> None:
        """Send conversation history to a newly connected client."""
        try:
            from ..agents.message_broker import get_broker
            broker = get_broker(project_id)
            history = broker.get_history()

            for msg in history:
                await websocket.send_json({
                    "type": "agent_message",
                    **msg.to_dict()
                })
        except Exception as e:
            logger.warning(f"Could not send history: {e}")


# Global project connection manager
project_manager = ProjectConnectionManager()


@router.websocket("/ws/projects/{project_id}/conversation")
async def project_conversation_endpoint(websocket: WebSocket, project_id: int):
    """WebSocket endpoint for real-time agent conversation streaming.

    Clients receive:
    - agent_message: Messages from agents in the conversation
    - status_update: Build progress updates
    - deliverable: Completed artifacts
    """
    await project_manager.connect(websocket, project_id)

    try:
        # Send existing conversation history
        await project_manager.send_history(websocket, project_id)

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )

                # Handle client commands
                try:
                    msg = json.loads(data)
                    cmd = msg.get("type")

                    if cmd == "ping":
                        await websocket.send_json({"type": "pong"})

                    elif cmd == "pong":
                        pass  # Heartbeat response

                    elif cmd == "get_history":
                        await project_manager.send_history(websocket, project_id)

                    elif cmd == "user_message":
                        # Handle user joining the conversation
                        content = msg.get("content")
                        if content:
                            await handle_user_message(project_id, content)

                except json.JSONDecodeError:
                    pass

            except asyncio.TimeoutError:
                # Send ping to keep alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception(f"WebSocket error for project {project_id}: {e}")
    finally:
        await project_manager.disconnect(websocket, project_id)


async def push_to_project(project_id: int, message: dict):
    """Push a message to all clients watching a project.

    Can be called from anywhere in the application.
    """
    await project_manager.send_to_project(project_id, message)


async def handle_user_message(project_id: int, content: str):
    """Handle a user message sent to an active agent conversation.

    Routes the message to the active director for the project.
    """
    try:
        from ..agents.message_broker import get_broker, AgentMessage, MessageType

        # Create user message and broadcast via broker
        broker = get_broker(project_id)
        msg = AgentMessage(
            sender="user",
            content=content,
            message_type=MessageType.USER,
        )
        await broker.broadcast(msg)

        # Try to get the active director to handle the response
        # This will be handled by the director's message subscription
        logger.info(f"User message broadcast for project {project_id}: {content[:50]}...")

    except Exception as e:
        logger.error(f"Failed to handle user message: {e}")
        # Send error back to UI
        await project_manager.send_to_project(project_id, {
            "type": "error",
            "message": f"Failed to process message: {str(e)}"
        })
