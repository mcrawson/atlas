"""Pydantic models for ATLAS Web API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# --- Enums ---

class WorkflowModeEnum(str, Enum):
    """Workflow execution modes."""
    # Creation modes
    SEQUENTIAL = "sequential"
    DIRECT_BUILD = "direct_build"
    VERIFY_ONLY = "verify_only"
    SPEC_DRIVEN = "spec_driven"
    FULL_DEPLOY = "full_deploy"
    DEPLOY_ONLY = "deploy_only"
    FULL_POLISH = "full_polish"
    FULL_CAMPAIGN = "full_campaign"
    PROMOTE_ONLY = "promote_only"
    # Update modes
    UPDATE = "update"
    UPDATE_PATCH = "update_patch"
    UPDATE_MINOR = "update_minor"
    UPDATE_MAJOR = "update_major"
    HOTFIX = "hotfix"


class AgentStatusEnum(str, Enum):
    """Agent status values."""
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


class TaskStatusEnum(str, Enum):
    """Task status values."""
    PENDING = "pending"
    PLANNING = "planning"
    BUILDING = "building"
    VERIFYING = "verifying"
    REVISION = "revision"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriorityEnum(int, Enum):
    """Task priority levels."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


# --- Request Models ---

class TaskRequest(BaseModel):
    """Request model for task execution.

    Execute a task through the ATLAS multi-agent pipeline.
    The task will be processed by Architect, Mason, and Oracle agents.
    """
    task: str = Field(..., min_length=1, max_length=10000, description="Task description")
    mode: WorkflowModeEnum = Field(default=WorkflowModeEnum.SEQUENTIAL, description="Workflow mode")
    context: Optional[dict[str, Any]] = Field(default=None, description="Optional context")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task": "Build a REST API for user authentication with JWT tokens",
                    "mode": "sequential",
                    "context": {"language": "python", "framework": "fastapi"}
                }
            ]
        }
    }

    @field_validator("task")
    @classmethod
    def task_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Task cannot be empty or whitespace only")
        return v.strip()


class ProjectCreateRequest(BaseModel):
    """Request model for project creation.

    Create a new project in ATLAS to track development progress.
    """
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: str = Field(default="", max_length=5000, description="Project description")
    tags: list[str] = Field(default_factory=list, max_length=20, description="Project tags")
    idea: str = Field(default="", max_length=10000, description="Original idea text")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "E-commerce Platform",
                    "description": "A modern e-commerce platform with user auth, product catalog, and payments",
                    "tags": ["python", "fastapi", "react", "postgresql"],
                    "idea": "Build a scalable e-commerce solution for small businesses"
                }
            ]
        }
    }

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Project name cannot be empty")
        return v.strip()

    @field_validator("tags")
    @classmethod
    def tags_valid(cls, v: list[str]) -> list[str]:
        return [tag.strip().lower() for tag in v if tag.strip()]


class ProjectUpdateRequest(BaseModel):
    """Request model for project updates."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    tags: Optional[list[str]] = Field(None, max_length=20)
    status: Optional[str] = Field(None, max_length=50)


class TaskCreateRequest(BaseModel):
    """Request model for task creation.

    Add a task to a project for tracking and execution.
    """
    title: str = Field(..., min_length=1, max_length=500, description="Task title")
    description: str = Field(default="", max_length=5000, description="Task description")
    priority: TaskPriorityEnum = Field(default=TaskPriorityEnum.MEDIUM, description="Task priority")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Implement user registration endpoint",
                    "description": "Create POST /api/users/register with email validation and password hashing",
                    "priority": 2
                }
            ]
        }
    }

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Task title cannot be empty")
        return v.strip()


class IdeaConversationRequest(BaseModel):
    """Request model for idea conversation."""
    message: str = Field(..., min_length=1, max_length=5000, description="User message")

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class FeedbackRequest(BaseModel):
    """Request model for feedback submission."""
    feedback_type: str = Field(..., description="Type: thumbs_up, thumbs_down, comment")
    content: str = Field(default="", max_length=2000, description="Feedback content")
    section: Optional[str] = Field(None, max_length=100, description="Section being rated")

    @field_validator("feedback_type")
    @classmethod
    def valid_feedback_type(cls, v: str) -> str:
        valid_types = {"thumbs_up", "thumbs_down", "comment", "suggestion", "bug"}
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid feedback type. Must be one of: {valid_types}")
        return v.lower()


# --- Response Models ---

class AgentStatusResponse(BaseModel):
    """Response model for agent status."""
    name: str
    description: str
    icon: str
    color: str
    status: AgentStatusEnum
    current_task: Optional[str] = None


class AgentsStatusResponse(BaseModel):
    """Response model for all agents status."""
    agents: dict[str, AgentStatusResponse]


class TaskResponse(BaseModel):
    """Response model for a task."""
    id: int
    project_id: int
    title: str
    description: str
    priority: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProjectResponse(BaseModel):
    """Response model for a project."""
    id: int
    name: str
    description: str
    status: str
    tags: list[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    tasks: list[TaskResponse] = []

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Response model for project list."""
    projects: list[ProjectResponse]
    total: int = 0


class ProjectStatsResponse(BaseModel):
    """Response model for project statistics."""
    total_projects: int = 0
    completed_projects: int = 0
    in_progress_projects: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0


class StatusResponse(BaseModel):
    """Response model for system status.

    Returns the current health and statistics of the ATLAS system.
    """
    status: str = "ok"
    agents: dict[str, Any] = {}
    projects: ProjectStatsResponse = ProjectStatsResponse()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "ok",
                    "agents": {
                        "architect": {"status": "idle", "name": "Architect"},
                        "mason": {"status": "idle", "name": "Mason"},
                        "oracle": {"status": "idle", "name": "Oracle"}
                    },
                    "projects": {
                        "total_projects": 5,
                        "completed_projects": 2,
                        "in_progress_projects": 3,
                        "total_tasks": 15,
                        "completed_tasks": 8
                    }
                }
            ]
        }
    }


class TaskExecutionResponse(BaseModel):
    """Response model for task execution.

    Returns the results of running a task through the agent pipeline.
    """
    status: str
    task: str
    mode: str
    results: dict[str, Any]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "completed",
                    "task": "Build a REST API for user authentication",
                    "mode": "sequential",
                    "results": {
                        "architect": {"content": "System design specification..."},
                        "mason": {"content": "Implementation code..."},
                        "oracle": {"content": "Review: APPROVED"}
                    }
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Response model for errors."""
    detail: str
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = "healthy"
    version: str = "2.0.0"
    checks: dict[str, dict[str, Any]] = {}

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "version": "2.0.0",
                    "checks": {
                        "database": {"status": "ok", "latency_ms": 5},
                        "agents": {"status": "ok", "count": 3},
                        "providers": {"status": "ok", "available": ["ollama", "openai"]}
                    }
                }
            ]
        }
    }
