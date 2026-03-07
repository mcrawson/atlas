"""
GitHub sync data models for ATLAS Transporter.

Defines dataclasses for sync state, mappings, and GitHub data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import os


class SyncStatus(Enum):
    """Status of a sync operation."""
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncDirection(Enum):
    """Direction of sync operation."""
    ATLAS_TO_GITHUB = "atlas_to_github"
    GITHUB_TO_ATLAS = "github_to_atlas"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class TransporterConfig:
    """Configuration for the GitHub Transporter."""

    # Authentication
    token: str = ""
    webhook_secret: str = ""

    # Defaults
    default_repo: str = ""

    # Sync settings
    auto_sync: bool = True
    sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    post_agent_outputs: bool = True

    # Labels and formatting
    atlas_label: str = "atlas-task"
    priority_labels: dict[int, str] = field(default_factory=lambda: {
        0: "priority:low",
        1: "priority:medium",
        2: "priority:high",
        3: "priority:critical",
    })

    @classmethod
    def from_env(cls) -> "TransporterConfig":
        """Load configuration from environment variables."""
        return cls(
            token=os.getenv("ATLAS_GITHUB_TOKEN", ""),
            webhook_secret=os.getenv("ATLAS_GITHUB_WEBHOOK_SECRET", ""),
            default_repo=os.getenv("ATLAS_GITHUB_DEFAULT_REPO", ""),
            auto_sync=os.getenv("ATLAS_GITHUB_AUTO_SYNC", "true").lower() == "true",
            post_agent_outputs=os.getenv("ATLAS_GITHUB_POST_OUTPUTS", "true").lower() == "true",
        )

    @property
    def is_configured(self) -> bool:
        """Check if GitHub integration is properly configured."""
        return bool(self.token)


@dataclass
class SyncMapping:
    """Mapping between ATLAS task and GitHub issue."""

    id: Optional[int] = None
    atlas_task_id: int = 0
    github_repo: str = ""
    github_issue_number: int = 0
    last_sync: Optional[datetime] = None
    sync_status: SyncStatus = SyncStatus.PENDING
    atlas_updated_at: Optional[datetime] = None
    github_updated_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "atlas_task_id": self.atlas_task_id,
            "github_repo": self.github_repo,
            "github_issue_number": self.github_issue_number,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "sync_status": self.sync_status.value,
            "atlas_updated_at": self.atlas_updated_at.isoformat() if self.atlas_updated_at else None,
            "github_updated_at": self.github_updated_at.isoformat() if self.github_updated_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncMapping":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            atlas_task_id=data.get("atlas_task_id", 0),
            github_repo=data.get("github_repo", ""),
            github_issue_number=data.get("github_issue_number", 0),
            last_sync=datetime.fromisoformat(data["last_sync"]) if data.get("last_sync") else None,
            sync_status=SyncStatus(data.get("sync_status", "pending")),
            atlas_updated_at=datetime.fromisoformat(data["atlas_updated_at"]) if data.get("atlas_updated_at") else None,
            github_updated_at=datetime.fromisoformat(data["github_updated_at"]) if data.get("github_updated_at") else None,
            metadata=data.get("metadata", {}),
        )


@dataclass
class SyncState:
    """Overall sync state for the transporter."""

    last_full_sync: Optional[datetime] = None
    mappings_count: int = 0
    pending_count: int = 0
    synced_count: int = 0
    failed_count: int = 0
    conflict_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "last_full_sync": self.last_full_sync.isoformat() if self.last_full_sync else None,
            "mappings_count": self.mappings_count,
            "pending_count": self.pending_count,
            "synced_count": self.synced_count,
            "failed_count": self.failed_count,
            "conflict_count": self.conflict_count,
        }


@dataclass
class GitHubIssueData:
    """Data for a GitHub issue."""

    number: int = 0
    title: str = ""
    body: str = ""
    state: str = "open"
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    milestone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    html_url: str = ""
    user: str = ""
    comments_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "labels": self.labels,
            "assignees": self.assignees,
            "milestone": self.milestone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "html_url": self.html_url,
            "user": self.user,
            "comments_count": self.comments_count,
        }

    @classmethod
    def from_github_response(cls, data: dict) -> "GitHubIssueData":
        """Create from GitHub API response."""
        return cls(
            number=data.get("number", 0),
            title=data.get("title", ""),
            body=data.get("body", "") or "",
            state=data.get("state", "open"),
            labels=[label["name"] if isinstance(label, dict) else label for label in data.get("labels", [])],
            assignees=[user["login"] if isinstance(user, dict) else user for user in data.get("assignees", [])],
            milestone=data.get("milestone", {}).get("title") if data.get("milestone") else None,
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")) if data.get("updated_at") else None,
            closed_at=datetime.fromisoformat(data["closed_at"].replace("Z", "+00:00")) if data.get("closed_at") else None,
            html_url=data.get("html_url", ""),
            user=data.get("user", {}).get("login", ""),
            comments_count=data.get("comments", 0),
        )


@dataclass
class GitHubCommentData:
    """Data for a GitHub issue comment."""

    id: int = 0
    body: str = ""
    user: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    html_url: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "body": self.body,
            "user": self.user,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "html_url": self.html_url,
        }

    @classmethod
    def from_github_response(cls, data: dict) -> "GitHubCommentData":
        """Create from GitHub API response."""
        return cls(
            id=data.get("id", 0),
            body=data.get("body", ""),
            user=data.get("user", {}).get("login", ""),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")) if data.get("updated_at") else None,
            html_url=data.get("html_url", ""),
        )


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    direction: SyncDirection
    atlas_task_id: Optional[int] = None
    github_issue_number: Optional[int] = None
    github_repo: Optional[str] = None
    message: str = ""
    error: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "direction": self.direction.value,
            "atlas_task_id": self.atlas_task_id,
            "github_issue_number": self.github_issue_number,
            "github_repo": self.github_repo,
            "message": self.message,
            "error": self.error,
            "url": self.url,
        }
