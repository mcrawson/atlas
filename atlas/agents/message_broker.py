"""Message Broker - Central hub for agent-to-agent communication.

Handles all messaging between agents and streams to UI via WebSocket.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Any
from enum import Enum
import json

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages in the conversation."""
    SYSTEM = "system"           # System announcements
    DISCUSSION = "discussion"   # Agent discussion/opinion
    QUESTION = "question"       # Agent asking a question
    ANSWER = "answer"           # Agent answering
    DECISION = "decision"       # Director decision
    PROGRESS = "progress"       # Build progress update
    DELIVERABLE = "deliverable" # Completed artifact
    QC_REPORT = "qc_report"     # QC evaluation
    HANDOFF = "handoff"         # Handing off to another agent
    CONCERN = "concern"         # Agent raising an issue
    RESOLUTION = "resolution"   # Issue resolved
    TYPING = "typing"           # Agent is thinking/typing
    TYPING_STOP = "typing_stop" # Agent finished typing
    TEXT_CHUNK = "text_chunk"   # Partial text for streaming
    USER = "user"               # Message from the user
    INTERRUPTION = "interruption"  # Agent interrupting another
    POSITION_CHANGE = "position_change"  # Agent changed their position


@dataclass
class AgentMessage:
    """A message in the agent conversation."""
    sender: str
    content: str
    message_type: MessageType = MessageType.DISCUSSION
    recipient: Optional[str] = None  # None = broadcast to all
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "content": self.content,
            "message_type": self.message_type.value,
            "recipient": self.recipient,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class BuildStatus:
    """Current build status."""
    phase: str
    progress: int  # 0-100
    current_action: str
    agent: str

    def to_dict(self) -> dict:
        return {
            "type": "status_update",
            "phase": self.phase,
            "progress": self.progress,
            "current_action": self.current_action,
            "agent": self.agent,
        }


@dataclass
class AgentPosition:
    """Tracks an agent's position on a topic."""
    agent_id: str
    topic: str
    position: str
    confidence: float = 0.8
    changed_from: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "topic": self.topic,
            "position": self.position,
            "confidence": self.confidence,
            "changed_from": self.changed_from,
            "timestamp": self.timestamp.isoformat(),
        }


class MessageBroker:
    """Central hub for all agent communication.

    - Routes messages between agents
    - Maintains conversation history
    - Streams messages to UI via WebSocket callbacks
    - Tracks agent positions on topics
    - Supports typing indicators and streaming
    """

    def __init__(self, project_id: int):
        self.project_id = project_id
        self.messages: list[AgentMessage] = []
        self.subscribers: dict[str, Callable] = {}  # agent_id -> callback
        self.ui_callbacks: list[Callable] = []  # WebSocket push functions
        self._lock = asyncio.Lock()
        self.positions: dict[str, list[AgentPosition]] = {}  # topic -> positions
        self.typing_agents: set[str] = set()  # Currently typing agents

    async def send(self, message: AgentMessage) -> None:
        """Send a message to specific agent(s) or broadcast."""
        async with self._lock:
            self.messages.append(message)

        logger.info(f"[{message.sender}] → [{message.recipient or 'ALL'}]: {message.content[:100]}")

        # Route to specific agent or broadcast
        if message.recipient:
            if message.recipient in self.subscribers:
                await self._deliver(message, self.subscribers[message.recipient])
        else:
            # Broadcast to all agents
            for agent_id, callback in self.subscribers.items():
                if agent_id != message.sender:  # Don't send to self
                    await self._deliver(message, callback)

        # Always stream to UI
        await self._stream_to_ui(message)

    async def broadcast(self, message: AgentMessage) -> None:
        """Broadcast message to all agents."""
        message.recipient = None
        await self.send(message)

    async def _deliver(self, message: AgentMessage, callback: Callable) -> None:
        """Deliver message to an agent's callback."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(message)
            else:
                callback(message)
        except Exception as e:
            logger.error(f"Failed to deliver message: {e}")

    async def _stream_to_ui(self, message: AgentMessage) -> None:
        """Push message to all connected UI clients."""
        payload = {
            "type": "agent_message",
            **message.to_dict()
        }

        for callback in self.ui_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(payload)
                else:
                    callback(payload)
            except Exception as e:
                logger.error(f"Failed to stream to UI: {e}")

    async def push_status(self, status: BuildStatus) -> None:
        """Send build status update to UI."""
        for callback in self.ui_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(status.to_dict())
                else:
                    callback(status.to_dict())
            except Exception as e:
                logger.error(f"Failed to push status: {e}")

    async def push_deliverable(self, name: str, preview_url: str, download_url: str = None) -> None:
        """Send completed deliverable to UI."""
        payload = {
            "type": "deliverable",
            "name": name,
            "preview_url": preview_url,
            "download_url": download_url or preview_url,
            "timestamp": datetime.now().isoformat(),
        }

        for callback in self.ui_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(payload)
                else:
                    callback(payload)
            except Exception as e:
                logger.error(f"Failed to push deliverable: {e}")

    async def push_typing(self, agent_id: str, is_typing: bool) -> None:
        """Send typing indicator to UI."""
        if is_typing:
            self.typing_agents.add(agent_id)
        else:
            self.typing_agents.discard(agent_id)

        payload = {
            "type": "typing" if is_typing else "typing_stop",
            "agent": agent_id,
            "timestamp": datetime.now().isoformat(),
        }

        for callback in self.ui_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(payload)
                else:
                    callback(payload)
            except Exception as e:
                logger.error(f"Failed to push typing indicator: {e}")

    async def push_text_chunk(self, agent_id: str, text: str) -> None:
        """Send a chunk of streaming text to UI."""
        payload = {
            "type": "text_chunk",
            "agent": agent_id,
            "text": text,
            "timestamp": datetime.now().isoformat(),
        }

        for callback in self.ui_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(payload)
                else:
                    callback(payload)
            except Exception as e:
                logger.error(f"Failed to push text chunk: {e}")

    def update_position(
        self,
        agent_id: str,
        topic: str,
        position: str,
        confidence: float = 0.8,
        changed_from: str = None
    ) -> AgentPosition:
        """Track an agent's position on a topic."""
        pos = AgentPosition(
            agent_id=agent_id,
            topic=topic,
            position=position,
            confidence=confidence,
            changed_from=changed_from,
        )

        if topic not in self.positions:
            self.positions[topic] = []

        # Replace existing position for this agent on this topic
        self.positions[topic] = [
            p for p in self.positions[topic] if p.agent_id != agent_id
        ]
        self.positions[topic].append(pos)

        logger.debug(f"Position updated: {agent_id} on {topic}: {position[:50]}...")
        return pos

    def get_positions_for_topic(self, topic: str) -> list[AgentPosition]:
        """Get all agent positions on a topic."""
        return self.positions.get(topic, [])

    def get_agent_position(self, agent_id: str, topic: str) -> Optional[AgentPosition]:
        """Get a specific agent's position on a topic."""
        for pos in self.positions.get(topic, []):
            if pos.agent_id == agent_id:
                return pos
        return None

    def check_consensus(self, topic: str) -> tuple[bool, Optional[str]]:
        """Check if agents have reached consensus on a topic.

        Returns: (has_consensus, common_position_or_None)
        """
        positions = self.get_positions_for_topic(topic)
        if not positions:
            return False, None

        # Simple consensus: all positions contain similar core idea
        # This is a basic implementation - could be made smarter with LLM
        position_texts = [p.position.lower() for p in positions]

        # Check if all positions are roughly aligned (contains same key words)
        if len(positions) < 2:
            return False, None

        first_words = set(position_texts[0].split()[:5])
        all_aligned = all(
            len(first_words & set(pt.split()[:5])) >= 2
            for pt in position_texts[1:]
        )

        if all_aligned:
            return True, positions[0].position

        return False, None

    def subscribe_agent(self, agent_id: str, callback: Callable) -> None:
        """Register an agent to receive messages."""
        self.subscribers[agent_id] = callback
        logger.debug(f"Agent subscribed: {agent_id}")

    def unsubscribe_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self.subscribers:
            del self.subscribers[agent_id]
            logger.debug(f"Agent unsubscribed: {agent_id}")

    def subscribe_ui(self, callback: Callable) -> None:
        """Register a UI WebSocket callback."""
        self.ui_callbacks.append(callback)

    def unsubscribe_ui(self, callback: Callable) -> None:
        """Unregister a UI callback."""
        if callback in self.ui_callbacks:
            self.ui_callbacks.remove(callback)

    def get_history(self) -> list[AgentMessage]:
        """Get full conversation history."""
        return self.messages.copy()

    def get_history_for_agent(self, agent_id: str) -> list[AgentMessage]:
        """Get messages relevant to a specific agent."""
        return [
            msg for msg in self.messages
            if msg.recipient is None or msg.recipient == agent_id or msg.sender == agent_id
        ]

    def get_recent(self, count: int = 10) -> list[AgentMessage]:
        """Get most recent messages."""
        return self.messages[-count:]

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []


# Global broker registry (per project)
_brokers: dict[int, MessageBroker] = {}


def get_broker(project_id: int) -> MessageBroker:
    """Get or create a message broker for a project."""
    if project_id not in _brokers:
        _brokers[project_id] = MessageBroker(project_id)
    return _brokers[project_id]


def remove_broker(project_id: int) -> None:
    """Remove a project's broker (cleanup)."""
    if project_id in _brokers:
        del _brokers[project_id]
