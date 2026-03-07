"""Data models for ATLAS project management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ProjectStatus(Enum):
    """Status of a project."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(Enum):
    """Status of a task within a project."""
    PENDING = "pending"
    PLANNING = "planning"  # Architect is working
    BUILDING = "building"  # Mason is working
    VERIFYING = "verifying"  # Oracle is working
    REVISION = "revision"  # Back to Mason after Oracle rejection
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentWorkOutput:
    """Output from a single agent's work on a task."""
    agent_name: str
    content: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    reasoning: str = ""  # Agent's thought process
    tokens_used: int = 0  # Total tokens for this output
    prompt_tokens: int = 0  # Input tokens
    completion_tokens: int = 0  # Output tokens
    approved: bool = False  # User approval status
    approved_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "content": self.content,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "reasoning": self.reasoning,
            "tokens_used": self.tokens_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "approved": self.approved,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentWorkOutput":
        """Create from dictionary."""
        return cls(
            agent_name=data["agent_name"],
            content=data["content"],
            artifacts=data.get("artifacts", {}),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            reasoning=data.get("reasoning", ""),
            tokens_used=data.get("tokens_used", 0),
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            approved=data.get("approved", False),
            approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None,
        )


@dataclass
class ProjectTask:
    """A task within a project that flows through agents."""
    id: Optional[int] = None
    project_id: Optional[int] = None
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    agent_outputs: list[AgentWorkOutput] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "agent_outputs": [o.to_dict() for o in self.agent_outputs],
            "artifacts": self.artifacts,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectTask":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            project_id=data.get("project_id"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "pending")),
            priority=data.get("priority", 0),
            agent_outputs=[AgentWorkOutput.from_dict(o) for o in data.get("agent_outputs", [])],
            artifacts=data.get("artifacts", {}),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )

    def add_agent_output(self, agent_name: str, content: str, artifacts: dict = None, metadata: dict = None):
        """Add output from an agent."""
        self.agent_outputs.append(AgentWorkOutput(
            agent_name=agent_name,
            content=content,
            artifacts=artifacts or {},
            metadata=metadata or {},
        ))
        self.updated_at = datetime.now()

    def get_latest_output(self) -> Optional[AgentWorkOutput]:
        """Get the most recent agent output."""
        return self.agent_outputs[-1] if self.agent_outputs else None

    def get_outputs_by_agent(self, agent_name: str) -> list[AgentWorkOutput]:
        """Get all outputs from a specific agent."""
        return [o for o in self.agent_outputs if o.agent_name == agent_name]

    @property
    def is_complete(self) -> bool:
        """Check if task is in a completed state."""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)

    @property
    def is_active(self) -> bool:
        """Check if task is currently being worked on."""
        return self.status in (TaskStatus.PLANNING, TaskStatus.BUILDING, TaskStatus.VERIFYING, TaskStatus.REVISION)


@dataclass
class Project:
    """A project containing multiple tasks."""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    tasks: list[ProjectTask] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "tasks": [t.to_dict() for t in self.tasks],
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            status=ProjectStatus(data.get("status", "active")),
            tasks=[ProjectTask.from_dict(t) for t in data.get("tasks", [])],
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )

    @property
    def progress(self) -> float:
        """Calculate project progress as percentage."""
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.is_complete)
        return (completed / len(self.tasks)) * 100

    @property
    def task_counts(self) -> dict[str, int]:
        """Get counts of tasks by status."""
        counts = {status.value: 0 for status in TaskStatus}
        for task in self.tasks:
            counts[task.status.value] += 1
        return counts

    def add_task(self, task: ProjectTask) -> ProjectTask:
        """Add a task to the project."""
        task.project_id = self.id
        self.tasks.append(task)
        self.updated_at = datetime.now()
        return task

    def get_task(self, task_id: int) -> Optional[ProjectTask]:
        """Get a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_pending_tasks(self) -> list[ProjectTask]:
        """Get all pending tasks."""
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]

    def get_active_tasks(self) -> list[ProjectTask]:
        """Get all active (in-progress) tasks."""
        return [t for t in self.tasks if t.is_active]
