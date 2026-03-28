"""Agent Memory - Persistent memory for agents across sessions.

Stores decisions, positions, conversations, and lessons learned
so agents can reference past context in new debates.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """A recorded decision from a debate."""
    topic: str
    decision: str
    context: dict
    participants: list[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 1.0


@dataclass
class PositionChange:
    """Records when an agent changed their position."""
    agent_id: str
    topic: str
    original_position: str
    new_position: str
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LessonLearned:
    """A lesson learned from a project or debate."""
    lesson: str
    context: str
    source_project: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentMemory:
    """Persistent memory for agents across sessions.

    Stores:
    - Conversations: Full history of debates
    - Decisions: Final decisions on topics
    - Agent Positions: How agents positioned on topics (and changes)
    - User Preferences: Learned user preferences
    - Lessons Learned: Insights from past projects
    """

    def __init__(self, project_id: int, storage_dir: Path = None):
        self.project_id = project_id
        self.storage_dir = storage_dir or Path("data/memory")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.storage_dir / f"project_{project_id}.json"
        self._load()

    def _load(self) -> None:
        """Load memory from disk."""
        if self.memory_file.exists():
            try:
                self.data = json.loads(self.memory_file.read_text())
            except json.JSONDecodeError:
                logger.warning(f"Corrupted memory file, starting fresh: {self.memory_file}")
                self._init_empty()
        else:
            self._init_empty()

    def _init_empty(self) -> None:
        """Initialize empty memory structure."""
        self.data = {
            "project_id": self.project_id,
            "created_at": datetime.now().isoformat(),
            "conversations": [],
            "decisions": [],
            "position_changes": [],
            "user_preferences": {},
            "lessons_learned": [],
            "agent_contexts": {},  # Per-agent context storage
        }

    def save(self) -> None:
        """Save memory to disk."""
        self.data["updated_at"] = datetime.now().isoformat()
        self.memory_file.write_text(json.dumps(self.data, indent=2, default=str))

    # ==========================================================================
    # Decision Management
    # ==========================================================================

    def remember_decision(
        self,
        topic: str,
        decision: str,
        context: dict = None,
        participants: list[str] = None,
        confidence: float = 1.0
    ) -> None:
        """Record a decision made during debate."""
        decision_obj = Decision(
            topic=topic,
            decision=decision,
            context=context or {},
            participants=participants or [],
            confidence=confidence
        )
        self.data["decisions"].append(asdict(decision_obj))
        self.save()
        logger.info(f"Remembered decision: {topic} -> {decision[:50]}...")

    def get_decisions(self, topic_filter: str = None, limit: int = 10) -> list[dict]:
        """Get past decisions, optionally filtered by topic."""
        decisions = self.data["decisions"]

        if topic_filter:
            topic_lower = topic_filter.lower()
            decisions = [
                d for d in decisions
                if topic_lower in d["topic"].lower()
            ]

        return decisions[-limit:]

    def get_relevant_memories(self, topic: str, limit: int = 5) -> list[dict]:
        """Retrieve memories relevant to a current topic.

        Uses keyword matching to find related past decisions and lessons.
        """
        keywords = set(topic.lower().split())
        relevant = []

        # Search decisions
        for decision in self.data["decisions"]:
            decision_words = set(decision["topic"].lower().split())
            if keywords & decision_words:  # Any overlap
                relevant.append({
                    "type": "decision",
                    "topic": decision["topic"],
                    "content": decision["decision"],
                    "timestamp": decision["timestamp"]
                })

        # Search lessons
        for lesson in self.data["lessons_learned"]:
            lesson_words = set(lesson["lesson"].lower().split())
            if keywords & lesson_words:
                relevant.append({
                    "type": "lesson",
                    "content": lesson["lesson"],
                    "context": lesson["context"],
                    "timestamp": lesson["timestamp"]
                })

        # Sort by timestamp (most recent first)
        relevant.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return relevant[:limit]

    def format_memories_for_prompt(self, topic: str, limit: int = 3) -> str:
        """Format relevant memories as context for an LLM prompt."""
        memories = self.get_relevant_memories(topic, limit)
        if not memories:
            return ""

        lines = ["\nRELEVANT PAST CONTEXT:"]
        for mem in memories:
            if mem["type"] == "decision":
                lines.append(f"- Decision on '{mem['topic']}': {mem['content']}")
            else:
                lines.append(f"- Lesson learned: {mem['content']}")

        return "\n".join(lines)

    # ==========================================================================
    # Position Tracking
    # ==========================================================================

    def record_position(
        self,
        agent_id: str,
        topic: str,
        position: str,
        previous_position: str = None,
        reason: str = None
    ) -> None:
        """Record an agent's position on a topic."""
        if previous_position and previous_position != position:
            # This is a position change
            change = PositionChange(
                agent_id=agent_id,
                topic=topic,
                original_position=previous_position,
                new_position=position,
                reason=reason or "Convinced by argument"
            )
            self.data["position_changes"].append(asdict(change))
            logger.info(f"Position change recorded: {agent_id} on {topic}")

        # Update agent context
        if agent_id not in self.data["agent_contexts"]:
            self.data["agent_contexts"][agent_id] = {"positions": {}}

        self.data["agent_contexts"][agent_id]["positions"][topic] = {
            "position": position,
            "timestamp": datetime.now().isoformat()
        }

        self.save()

    def get_agent_positions(self, agent_id: str) -> dict:
        """Get all recorded positions for an agent."""
        return self.data["agent_contexts"].get(agent_id, {}).get("positions", {})

    def get_position_changes(self, topic: str = None) -> list[dict]:
        """Get all position changes, optionally filtered by topic."""
        changes = self.data["position_changes"]
        if topic:
            changes = [c for c in changes if topic.lower() in c["topic"].lower()]
        return changes

    # ==========================================================================
    # Lessons Learned
    # ==========================================================================

    def add_lesson(self, lesson: str, context: str = "", source_project: str = None) -> None:
        """Add a lesson learned from this project."""
        lesson_obj = LessonLearned(
            lesson=lesson,
            context=context,
            source_project=source_project
        )
        self.data["lessons_learned"].append(asdict(lesson_obj))
        self.save()

    def get_lessons(self, limit: int = 10) -> list[dict]:
        """Get recent lessons learned."""
        return self.data["lessons_learned"][-limit:]

    # ==========================================================================
    # User Preferences
    # ==========================================================================

    def set_preference(self, key: str, value: any) -> None:
        """Set a user preference."""
        self.data["user_preferences"][key] = {
            "value": value,
            "updated_at": datetime.now().isoformat()
        }
        self.save()

    def get_preference(self, key: str, default: any = None) -> any:
        """Get a user preference."""
        pref = self.data["user_preferences"].get(key)
        return pref["value"] if pref else default

    # ==========================================================================
    # Conversation Storage
    # ==========================================================================

    def store_conversation(self, messages: list[dict], summary: str = None) -> None:
        """Store a complete conversation."""
        self.data["conversations"].append({
            "messages": messages,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
            "message_count": len(messages)
        })
        self.save()

    def get_last_conversation(self) -> dict:
        """Get the most recent conversation."""
        if self.data["conversations"]:
            return self.data["conversations"][-1]
        return None

    # ==========================================================================
    # Agent Context
    # ==========================================================================

    def set_agent_context(self, agent_id: str, key: str, value: any) -> None:
        """Store context for a specific agent."""
        if agent_id not in self.data["agent_contexts"]:
            self.data["agent_contexts"][agent_id] = {"positions": {}}

        self.data["agent_contexts"][agent_id][key] = value
        self.save()

    def get_agent_context(self, agent_id: str, key: str = None) -> any:
        """Get context for a specific agent."""
        ctx = self.data["agent_contexts"].get(agent_id, {})
        if key:
            return ctx.get(key)
        return ctx

    # ==========================================================================
    # Summary & Stats
    # ==========================================================================

    def get_summary(self) -> dict:
        """Get a summary of this project's memory."""
        return {
            "project_id": self.project_id,
            "total_decisions": len(self.data["decisions"]),
            "total_position_changes": len(self.data["position_changes"]),
            "total_lessons": len(self.data["lessons_learned"]),
            "total_conversations": len(self.data["conversations"]),
            "agents_tracked": list(self.data["agent_contexts"].keys()),
            "created_at": self.data.get("created_at"),
            "updated_at": self.data.get("updated_at")
        }

    def clear(self) -> None:
        """Clear all memory (use with caution)."""
        self._init_empty()
        self.save()
        logger.info(f"Memory cleared for project {self.project_id}")


# Global memory registry
_memories: dict[int, AgentMemory] = {}


def get_memory(project_id: int) -> AgentMemory:
    """Get or create memory for a project."""
    if project_id not in _memories:
        _memories[project_id] = AgentMemory(project_id)
    return _memories[project_id]


def clear_memory_cache() -> None:
    """Clear the in-memory cache (memories persist on disk)."""
    _memories.clear()
