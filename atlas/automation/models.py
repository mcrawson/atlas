"""Automation system data models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class TaskStatus(Enum):
    """Status of an automation task."""
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommandRisk(Enum):
    """Risk level of a command."""
    LOW = "low"           # Read-only, no side effects
    MEDIUM = "medium"     # Local changes, reversible
    HIGH = "high"         # Network calls, file writes
    CRITICAL = "critical" # Destructive, irreversible


@dataclass
class CommandResult:
    """Result of executing a command."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AutomationTask:
    """An automation task with commands to execute."""
    id: str
    name: str
    description: str
    commands: list[str]
    status: TaskStatus = TaskStatus.PENDING
    working_dir: Optional[str] = None
    env_vars: dict = field(default_factory=dict)
    results: list[CommandResult] = field(default_factory=list)
    risk_level: CommandRisk = CommandRisk.MEDIUM
    requires_approval: bool = True
    approved: bool = False
    approved_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    source: Optional[str] = None  # e.g., "knowledge:ios-deployment"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "commands": self.commands,
            "status": self.status.value,
            "working_dir": self.working_dir,
            "env_vars": {k: "***" for k in self.env_vars},  # Hide values
            "results": [r.to_dict() for r in self.results],
            "risk_level": self.risk_level.value,
            "requires_approval": self.requires_approval,
            "approved": self.approved,
            "approved_by": self.approved_by,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "source": self.source,
        }

    @property
    def progress(self) -> float:
        """Get progress as percentage."""
        if not self.commands:
            return 0.0
        return (len(self.results) / len(self.commands)) * 100

    @property
    def is_complete(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
