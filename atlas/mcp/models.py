"""
MCP Server data models for ATLAS Oracle.

Defines dataclasses for tool results, resource content,
and configuration following ATLAS patterns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import os


class ToolResultType(Enum):
    """Type of tool result content."""
    TEXT = "text"
    JSON = "json"
    ERROR = "error"


@dataclass
class OracleConfig:
    """Configuration for the Oracle MCP Server."""

    # Server settings
    enabled: bool = True
    port: int = 8765
    host: str = "localhost"

    # Feature flags
    allow_task_execution: bool = True
    allow_project_modification: bool = True
    max_search_results: int = 50

    # Rate limiting
    max_requests_per_minute: int = 60

    @classmethod
    def from_env(cls) -> "OracleConfig":
        """Load configuration from environment variables."""
        return cls(
            enabled=os.getenv("ATLAS_MCP_ENABLED", "true").lower() == "true",
            port=int(os.getenv("ATLAS_MCP_PORT", "8765")),
            host=os.getenv("ATLAS_MCP_HOST", "localhost"),
            allow_task_execution=os.getenv("ATLAS_MCP_ALLOW_EXECUTION", "true").lower() == "true",
            allow_project_modification=os.getenv("ATLAS_MCP_ALLOW_MODIFICATION", "true").lower() == "true",
            max_search_results=int(os.getenv("ATLAS_MCP_MAX_RESULTS", "50")),
            max_requests_per_minute=int(os.getenv("ATLAS_MCP_RATE_LIMIT", "60")),
        )


@dataclass
class ToolCallResult:
    """Result from executing an MCP tool."""

    success: bool
    content: Any
    content_type: ToolResultType = ToolResultType.JSON
    error_message: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_mcp_response(self) -> list[dict]:
        """Convert to MCP tool response format."""
        if self.content_type == ToolResultType.ERROR:
            return [{
                "type": "text",
                "text": f"Error: {self.error_message or self.content}",
            }]
        elif self.content_type == ToolResultType.TEXT:
            return [{
                "type": "text",
                "text": str(self.content),
            }]
        else:
            # JSON content
            import json
            return [{
                "type": "text",
                "text": json.dumps(self.content, indent=2, default=str),
            }]


@dataclass
class ResourceContent:
    """Content for an MCP resource."""

    uri: str
    name: str
    content: Any
    mime_type: str = "application/json"
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_mcp_response(self) -> dict:
        """Convert to MCP resource response format."""
        import json

        if self.mime_type == "application/json":
            text = json.dumps(self.content, indent=2, default=str)
        else:
            text = str(self.content)

        return {
            "uri": self.uri,
            "mimeType": self.mime_type,
            "text": text,
        }


@dataclass
class ToolDefinition:
    """Definition for an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]

    def to_mcp_format(self) -> dict:
        """Convert to MCP tool definition format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class ResourceDefinition:
    """Definition for an MCP resource."""

    uri: str
    name: str
    description: str
    mime_type: str = "application/json"

    def to_mcp_format(self) -> dict:
        """Convert to MCP resource definition format."""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class AgentStatusData:
    """Status data for an agent."""

    name: str
    status: str
    current_task: Optional[str] = None
    last_activity: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status,
            "current_task": self.current_task,
            "last_activity": self.last_activity,
            "metadata": self.metadata,
        }


@dataclass
class SearchResult:
    """Result from knowledge base search."""

    id: str
    title: str
    content: str
    score: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "score": self.score,
            "source": self.source,
            "metadata": self.metadata,
        }
