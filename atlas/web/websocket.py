"""WebSocket handler for real-time updates."""

import asyncio
import json
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Active WebSocket connections
active_connections: Set[WebSocket] = set()


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.connections: Set[WebSocket] = set()

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
