"""Data models for ATLAS Spec-Driven Development.

Based on Kiro's EARS (Easy Approach to Requirements Syntax) methodology.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RequirementType(Enum):
    """Types of requirements in EARS format."""
    UBIQUITOUS = "ubiquitous"  # The system shall...
    EVENT_DRIVEN = "event_driven"  # When <trigger>, the system shall...
    STATE_DRIVEN = "state_driven"  # While <state>, the system shall...
    OPTIONAL = "optional"  # Where <feature>, the system shall...
    COMPLEX = "complex"  # Combination of the above


class TaskStatus(Enum):
    """Status of implementation tasks."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class Priority(Enum):
    """Priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AcceptanceCriteria:
    """Acceptance criteria for a requirement."""
    id: str
    description: str
    verified: bool = False
    notes: str = ""


@dataclass
class Requirement:
    """A requirement in EARS format.

    EARS Format Examples:
    - Ubiquitous: "The system shall <action>"
    - Event-driven: "When <trigger>, the system shall <action>"
    - State-driven: "While <state>, the system shall <action>"
    - Optional: "Where <feature>, the system shall <action>"
    """
    id: str
    title: str
    description: str
    type: RequirementType
    priority: Priority = Priority.MEDIUM
    acceptance_criteria: list[AcceptanceCriteria] = field(default_factory=list)
    user_story: str = ""  # As a <role>, I want <goal>, so that <benefit>
    dependencies: list[str] = field(default_factory=list)
    notes: str = ""

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        md = f"### {self.id}: {self.title}\n\n"

        if self.user_story:
            md += f"**User Story:** {self.user_story}\n\n"

        md += f"**Type:** {self.type.value.replace('_', ' ').title()}\n"
        md += f"**Priority:** {self.priority.value.title()}\n\n"
        md += f"**Requirement:** {self.description}\n\n"

        if self.acceptance_criteria:
            md += "**Acceptance Criteria:**\n"
            for ac in self.acceptance_criteria:
                status = "✅" if ac.verified else "⬜"
                md += f"- {status} {ac.id}: {ac.description}\n"
            md += "\n"

        if self.dependencies:
            md += f"**Dependencies:** {', '.join(self.dependencies)}\n\n"

        if self.notes:
            md += f"**Notes:** {self.notes}\n\n"

        return md


@dataclass
class DesignComponent:
    """A component in the design."""
    name: str
    description: str
    responsibilities: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class DesignDoc:
    """Technical design document."""
    title: str
    overview: str
    architecture: str = ""
    components: list[DesignComponent] = field(default_factory=list)
    data_model: str = ""
    api_design: str = ""
    error_handling: str = ""
    testing_strategy: str = ""
    security_considerations: str = ""
    performance_considerations: str = ""
    diagrams: list[str] = field(default_factory=list)  # ASCII diagrams or image paths

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        md = f"# {self.title}\n\n"
        md += f"## Overview\n\n{self.overview}\n\n"

        if self.architecture:
            md += f"## Architecture\n\n{self.architecture}\n\n"

        if self.components:
            md += "## Components\n\n"
            for comp in self.components:
                md += f"### {comp.name}\n\n"
                md += f"{comp.description}\n\n"
                if comp.responsibilities:
                    md += "**Responsibilities:**\n"
                    for r in comp.responsibilities:
                        md += f"- {r}\n"
                    md += "\n"
                if comp.interfaces:
                    md += "**Interfaces:**\n"
                    for i in comp.interfaces:
                        md += f"- {i}\n"
                    md += "\n"

        if self.data_model:
            md += f"## Data Model\n\n{self.data_model}\n\n"

        if self.api_design:
            md += f"## API Design\n\n{self.api_design}\n\n"

        if self.error_handling:
            md += f"## Error Handling\n\n{self.error_handling}\n\n"

        if self.testing_strategy:
            md += f"## Testing Strategy\n\n{self.testing_strategy}\n\n"

        if self.security_considerations:
            md += f"## Security Considerations\n\n{self.security_considerations}\n\n"

        if self.performance_considerations:
            md += f"## Performance Considerations\n\n{self.performance_considerations}\n\n"

        for i, diagram in enumerate(self.diagrams):
            md += f"## Diagram {i+1}\n\n```\n{diagram}\n```\n\n"

        return md


@dataclass
class Task:
    """An implementation task."""
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    requirement_ids: list[str] = field(default_factory=list)  # Links to requirements
    subtasks: list[str] = field(default_factory=list)
    files_to_modify: list[str] = field(default_factory=list)
    estimated_effort: str = ""  # e.g., "30 min", "2 hours"
    actual_effort: str = ""
    notes: str = ""
    completed_at: Optional[datetime] = None

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        status_icons = {
            TaskStatus.PENDING: "⬜",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.BLOCKED: "🚫",
            TaskStatus.SKIPPED: "⏭️",
        }
        icon = status_icons.get(self.status, "⬜")

        md = f"### {icon} {self.id}: {self.title}\n\n"
        md += f"{self.description}\n\n"

        md += f"**Status:** {self.status.value.replace('_', ' ').title()}\n"
        md += f"**Priority:** {self.priority.value.title()}\n"

        if self.requirement_ids:
            md += f"**Requirements:** {', '.join(self.requirement_ids)}\n"

        if self.estimated_effort:
            md += f"**Estimated Effort:** {self.estimated_effort}\n"

        if self.files_to_modify:
            md += "\n**Files to Modify:**\n"
            for f in self.files_to_modify:
                md += f"- `{f}`\n"

        if self.subtasks:
            md += "\n**Subtasks:**\n"
            for st in self.subtasks:
                md += f"- [ ] {st}\n"

        md += "\n"
        return md


@dataclass
class TaskList:
    """Collection of implementation tasks."""
    title: str
    tasks: list[Task] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        md = f"# {self.title}\n\n"

        # Progress summary
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in self.tasks if t.status == TaskStatus.IN_PROGRESS)

        md += "## Progress\n\n"
        md += f"- **Total Tasks:** {total}\n"
        md += f"- **Completed:** {completed} ({(completed/total*100) if total else 0:.0f}%)\n"
        md += f"- **In Progress:** {in_progress}\n"
        md += f"- **Remaining:** {total - completed - in_progress}\n\n"

        md += "## Tasks\n\n"
        for task in self.tasks:
            md += task.to_markdown()

        return md

    @property
    def progress_percentage(self) -> float:
        """Get overall progress as percentage."""
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return (completed / len(self.tasks)) * 100


@dataclass
class Spec:
    """Complete specification for a feature/project."""
    name: str
    description: str
    requirements: list[Requirement] = field(default_factory=list)
    design: Optional[DesignDoc] = None
    tasks: Optional[TaskList] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "requirements_count": len(self.requirements),
            "tasks_count": len(self.tasks.tasks) if self.tasks else 0,
            "progress": self.tasks.progress_percentage if self.tasks else 0,
        }
