"""Tests for atlas.agents.memory module."""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from atlas.agents.memory import (
    AgentMemory,
    Decision,
    PositionChange,
    LessonLearned,
    get_memory,
    clear_memory_cache,
)


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for memory storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def memory(temp_memory_dir):
    """Create a fresh AgentMemory instance."""
    return AgentMemory(project_id=999, storage_dir=temp_memory_dir)


class TestDecision:
    """Tests for Decision dataclass."""

    def test_create_decision(self):
        """Test creating a decision."""
        decision = Decision(
            topic="Color scheme",
            decision="Use blue and white",
            context={"reason": "brand consistency"},
            participants=["planner", "qc"],
        )
        assert decision.topic == "Color scheme"
        assert decision.decision == "Use blue and white"
        assert decision.participants == ["planner", "qc"]
        assert decision.confidence == 1.0

    def test_decision_has_timestamp(self):
        """Test that decision has automatic timestamp."""
        decision = Decision(
            topic="Test",
            decision="Test decision",
            context={},
            participants=[],
        )
        assert decision.timestamp is not None
        # Should be a valid ISO format string
        datetime.fromisoformat(decision.timestamp)


class TestPositionChange:
    """Tests for PositionChange dataclass."""

    def test_create_position_change(self):
        """Test creating a position change."""
        change = PositionChange(
            agent_id="planner",
            topic="Navigation style",
            original_position="Use tabs",
            new_position="Use sidebar",
            reason="Better for mobile",
        )
        assert change.agent_id == "planner"
        assert change.original_position == "Use tabs"
        assert change.new_position == "Use sidebar"


class TestLessonLearned:
    """Tests for LessonLearned dataclass."""

    def test_create_lesson(self):
        """Test creating a lesson learned."""
        lesson = LessonLearned(
            lesson="Always validate input before processing",
            context="QC found bug in form submission",
            source_project="Project Alpha",
        )
        assert lesson.lesson == "Always validate input before processing"
        assert lesson.source_project == "Project Alpha"


class TestAgentMemory:
    """Tests for AgentMemory class."""

    def test_init_creates_empty_structure(self, memory):
        """Test that new memory has empty structure."""
        assert memory.data["project_id"] == 999
        assert memory.data["decisions"] == []
        assert memory.data["position_changes"] == []
        assert memory.data["lessons_learned"] == []
        assert memory.data["conversations"] == []

    def test_save_and_load(self, temp_memory_dir):
        """Test that memory persists to disk."""
        # Create memory and add data
        memory1 = AgentMemory(project_id=123, storage_dir=temp_memory_dir)
        memory1.remember_decision(
            topic="Test topic",
            decision="Test decision",
            context={"key": "value"},
        )

        # Create new memory instance for same project
        memory2 = AgentMemory(project_id=123, storage_dir=temp_memory_dir)

        # Should have the saved decision
        assert len(memory2.data["decisions"]) == 1
        assert memory2.data["decisions"][0]["topic"] == "Test topic"

    def test_remember_decision(self, memory):
        """Test remembering a decision."""
        memory.remember_decision(
            topic="Layout choice",
            decision="Use grid layout",
            context={"reason": "flexibility"},
            participants=["planner", "expert"],
            confidence=0.9,
        )

        decisions = memory.get_decisions()
        assert len(decisions) == 1
        assert decisions[0]["topic"] == "Layout choice"
        assert decisions[0]["decision"] == "Use grid layout"
        assert decisions[0]["confidence"] == 0.9

    def test_get_decisions_with_filter(self, memory):
        """Test filtering decisions by topic."""
        memory.remember_decision("Color scheme", "Blue", {})
        memory.remember_decision("Font choice", "Arial", {})
        memory.remember_decision("Color palette", "Pastel", {})

        color_decisions = memory.get_decisions(topic_filter="color")
        assert len(color_decisions) == 2

    def test_get_decisions_limit(self, memory):
        """Test limiting number of decisions returned."""
        for i in range(10):
            memory.remember_decision(f"Topic {i}", f"Decision {i}", {})

        limited = memory.get_decisions(limit=5)
        assert len(limited) == 5

    def test_get_relevant_memories(self, memory):
        """Test getting memories relevant to a topic."""
        memory.remember_decision("Navigation design", "Use sidebar", {})
        memory.remember_decision("Color scheme", "Blue theme", {})
        memory.add_lesson("Navigation should be accessible", "UX review")

        relevant = memory.get_relevant_memories("navigation layout")
        assert len(relevant) >= 1
        # Should find navigation-related memories
        topics = [m.get("topic", m.get("content", "")) for m in relevant]
        assert any("navigation" in t.lower() for t in topics)

    def test_format_memories_for_prompt(self, memory):
        """Test formatting memories for LLM prompt."""
        memory.remember_decision("API design", "Use REST", {})
        memory.add_lesson("REST is easier to debug", "past project")

        formatted = memory.format_memories_for_prompt("API endpoints")
        assert "RELEVANT PAST CONTEXT:" in formatted
        assert "REST" in formatted

    def test_format_memories_empty(self, memory):
        """Test formatting when no relevant memories exist."""
        formatted = memory.format_memories_for_prompt("unrelated topic xyz")
        assert formatted == ""

    def test_record_position(self, memory):
        """Test recording agent position."""
        memory.record_position(
            agent_id="planner",
            topic="Database choice",
            position="Use PostgreSQL",
        )

        positions = memory.get_agent_positions("planner")
        assert "Database choice" in positions
        assert positions["Database choice"]["position"] == "Use PostgreSQL"

    def test_record_position_change(self, memory):
        """Test recording position change."""
        memory.record_position(
            agent_id="planner",
            topic="Framework",
            position="Use React",
            previous_position="Use Vue",
            reason="Better ecosystem",
        )

        changes = memory.get_position_changes()
        assert len(changes) == 1
        assert changes[0]["original_position"] == "Use Vue"
        assert changes[0]["new_position"] == "Use React"

    def test_add_lesson(self, memory):
        """Test adding lessons learned."""
        memory.add_lesson(
            lesson="Always test on mobile first",
            context="QC found mobile issues late",
            source_project="Mobile App v1",
        )

        lessons = memory.get_lessons()
        assert len(lessons) == 1
        assert lessons[0]["lesson"] == "Always test on mobile first"

    def test_set_and_get_preference(self, memory):
        """Test user preference storage."""
        memory.set_preference("theme", "dark")
        memory.set_preference("auto_save", True)

        assert memory.get_preference("theme") == "dark"
        assert memory.get_preference("auto_save") is True
        assert memory.get_preference("unknown") is None
        assert memory.get_preference("unknown", "default") == "default"

    def test_store_conversation(self, memory):
        """Test storing conversation history."""
        messages = [
            {"sender": "planner", "content": "Let's discuss"},
            {"sender": "qc", "content": "I agree"},
        ]
        memory.store_conversation(messages, summary="Quick discussion")

        last_conv = memory.get_last_conversation()
        assert last_conv is not None
        assert len(last_conv["messages"]) == 2
        assert last_conv["summary"] == "Quick discussion"

    def test_set_agent_context(self, memory):
        """Test storing agent-specific context."""
        memory.set_agent_context("qc", "last_review", {"score": 8})
        memory.set_agent_context("qc", "focus_areas", ["performance", "security"])

        ctx = memory.get_agent_context("qc")
        assert ctx["last_review"]["score"] == 8
        assert "performance" in ctx["focus_areas"]

    def test_get_summary(self, memory):
        """Test getting memory summary."""
        memory.remember_decision("Test", "Decision", {})
        memory.add_lesson("Test lesson", "context")
        memory.set_agent_context("qc", "key", "value")

        summary = memory.get_summary()
        assert summary["project_id"] == 999
        assert summary["total_decisions"] == 1
        assert summary["total_lessons"] == 1
        assert "qc" in summary["agents_tracked"]

    def test_clear_memory(self, memory):
        """Test clearing all memory."""
        memory.remember_decision("Test", "Decision", {})
        memory.add_lesson("Test", "context")

        memory.clear()

        assert len(memory.data["decisions"]) == 0
        assert len(memory.data["lessons_learned"]) == 0


class TestGetMemory:
    """Tests for get_memory function."""

    def test_get_memory_returns_same_instance(self):
        """Test that get_memory returns cached instance."""
        clear_memory_cache()
        
        mem1 = get_memory(123)
        mem2 = get_memory(123)
        
        assert mem1 is mem2

    def test_get_memory_different_projects(self):
        """Test that different projects get different memories."""
        clear_memory_cache()
        
        mem1 = get_memory(111)
        mem2 = get_memory(222)
        
        assert mem1 is not mem2
        assert mem1.project_id == 111
        assert mem2.project_id == 222


class TestClearMemoryCache:
    """Tests for clear_memory_cache function."""

    def test_clear_cache(self):
        """Test that clearing cache creates new instances."""
        mem1 = get_memory(999)
        clear_memory_cache()
        mem2 = get_memory(999)
        
        assert mem1 is not mem2
