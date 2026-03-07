"""
MCP Resource definitions for ATLAS Oracle.

Implements 4 resources for AI assistant access:
- atlas://projects - Project list
- atlas://agents/status - Agent status
- atlas://conversations/recent - Recent memory
- atlas://tasks/pending - Pending tasks
"""

import logging
from typing import Any, Optional

from .models import ResourceDefinition, ResourceContent

logger = logging.getLogger(__name__)


def get_resource_definitions() -> list[ResourceDefinition]:
    """Return all MCP resource definitions."""
    return [
        ResourceDefinition(
            uri="atlas://projects",
            name="ATLAS Projects",
            description="List of all ATLAS projects with their current status and task counts.",
            mime_type="application/json",
        ),
        ResourceDefinition(
            uri="atlas://agents/status",
            name="Agent Pipeline Status",
            description="Current status of the ATLAS agent pipeline (Architect, Mason, Oracle).",
            mime_type="application/json",
        ),
        ResourceDefinition(
            uri="atlas://conversations/recent",
            name="Recent Conversations",
            description="Recent conversation history and memory context.",
            mime_type="application/json",
        ),
        ResourceDefinition(
            uri="atlas://tasks/pending",
            name="Pending Tasks",
            description="List of pending tasks across all projects.",
            mime_type="application/json",
        ),
    ]


class ResourceProvider:
    """Provides MCP resource content using ATLAS managers."""

    def __init__(
        self,
        project_manager=None,
        agent_manager=None,
        memory_manager=None,
    ):
        """Initialize with ATLAS managers."""
        self.project_manager = project_manager
        self.agent_manager = agent_manager
        self.memory_manager = memory_manager

    async def get_resource(self, uri: str) -> Optional[ResourceContent]:
        """Get resource content by URI."""
        try:
            # Parse URI to determine handler
            if uri == "atlas://projects":
                return await self._get_projects_resource()
            elif uri == "atlas://agents/status":
                return await self._get_agents_status_resource()
            elif uri == "atlas://conversations/recent":
                return await self._get_conversations_resource()
            elif uri == "atlas://tasks/pending":
                return await self._get_pending_tasks_resource()
            else:
                logger.warning(f"Unknown resource URI: {uri}")
                return None
        except Exception as e:
            logger.exception(f"Error getting resource {uri}: {e}")
            return None

    async def _get_projects_resource(self) -> ResourceContent:
        """Get projects resource content."""
        if not self.project_manager:
            return ResourceContent(
                uri="atlas://projects",
                name="ATLAS Projects",
                content={"error": "Project manager not initialized", "projects": []},
            )

        try:
            projects = await self.project_manager.get_projects(include_tasks=True)

            project_list = []
            for p in projects:
                project_list.append({
                    "id": p.id,
                    "name": p.name,
                    "description": p.description[:200] if p.description else "",
                    "status": p.status.value,
                    "task_count": len(p.tasks) if p.tasks else 0,
                    "pending_tasks": sum(
                        1 for t in (p.tasks or []) if t.status.value == "pending"
                    ),
                    "completed_tasks": sum(
                        1 for t in (p.tasks or []) if t.status.value == "completed"
                    ),
                    "tags": p.tags,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                })

            return ResourceContent(
                uri="atlas://projects",
                name="ATLAS Projects",
                content={
                    "projects": project_list,
                    "total": len(project_list),
                    "summary": {
                        "active": sum(1 for p in projects if p.status.value == "active"),
                        "completed": sum(1 for p in projects if p.status.value == "completed"),
                        "archived": sum(1 for p in projects if p.status.value == "archived"),
                    },
                },
                description="List of all ATLAS projects with status and task counts",
            )
        except Exception as e:
            logger.exception(f"Error getting projects resource: {e}")
            return ResourceContent(
                uri="atlas://projects",
                name="ATLAS Projects",
                content={"error": str(e), "projects": []},
            )

    async def _get_agents_status_resource(self) -> ResourceContent:
        """Get agent status resource content."""
        if not self.agent_manager:
            return ResourceContent(
                uri="atlas://agents/status",
                name="Agent Pipeline Status",
                content={"error": "Agent manager not initialized", "agents": {}},
            )

        try:
            all_status = self.agent_manager.get_all_status()

            agents_data = {}
            for name, status in all_status.items():
                agent = getattr(self.agent_manager, name, None)
                agents_data[name] = {
                    "status": status.value if hasattr(status, "value") else str(status),
                    "current_task": getattr(agent, "current_task", None) if agent else None,
                    "last_activity": getattr(agent, "last_activity", None) if agent else None,
                }

            return ResourceContent(
                uri="atlas://agents/status",
                name="Agent Pipeline Status",
                content={
                    "agents": agents_data,
                    "pipeline_ready": all(
                        s.value == "idle" if hasattr(s, "value") else s == "idle"
                        for s in all_status.values()
                    ),
                },
                description="Current status of ATLAS agents (Architect, Mason, Oracle)",
            )
        except Exception as e:
            logger.exception(f"Error getting agent status resource: {e}")
            return ResourceContent(
                uri="atlas://agents/status",
                name="Agent Pipeline Status",
                content={"error": str(e), "agents": {}},
            )

    async def _get_conversations_resource(self) -> ResourceContent:
        """Get recent conversations resource content."""
        if not self.memory_manager:
            return ResourceContent(
                uri="atlas://conversations/recent",
                name="Recent Conversations",
                content={"error": "Memory manager not initialized", "conversations": []},
            )

        try:
            # Get recent conversations (limit 20)
            conversations = await self.memory_manager.get_recent(limit=20)

            conv_list = []
            for conv in conversations:
                conv_list.append({
                    "id": conv.id if hasattr(conv, "id") else None,
                    "role": conv.role if hasattr(conv, "role") else "unknown",
                    "content": conv.content[:300] if hasattr(conv, "content") else str(conv)[:300],
                    "timestamp": conv.timestamp.isoformat() if hasattr(conv, "timestamp") else None,
                    "project_id": conv.project_id if hasattr(conv, "project_id") else None,
                })

            return ResourceContent(
                uri="atlas://conversations/recent",
                name="Recent Conversations",
                content={
                    "conversations": conv_list,
                    "total": len(conv_list),
                },
                description="Recent conversation history for context",
            )
        except Exception as e:
            logger.exception(f"Error getting conversations resource: {e}")
            return ResourceContent(
                uri="atlas://conversations/recent",
                name="Recent Conversations",
                content={"error": str(e), "conversations": []},
            )

    async def _get_pending_tasks_resource(self) -> ResourceContent:
        """Get pending tasks resource content."""
        if not self.project_manager:
            return ResourceContent(
                uri="atlas://tasks/pending",
                name="Pending Tasks",
                content={"error": "Project manager not initialized", "tasks": []},
            )

        try:
            # Get all projects with tasks
            projects = await self.project_manager.get_projects(include_tasks=True)

            pending_tasks = []
            for project in projects:
                for task in (project.tasks or []):
                    if task.status.value == "pending":
                        pending_tasks.append({
                            "id": task.id,
                            "project_id": project.id,
                            "project_name": project.name,
                            "title": task.title,
                            "description": task.description[:200] if task.description else "",
                            "priority": task.priority,
                            "tags": task.tags,
                            "created_at": task.created_at.isoformat() if task.created_at else None,
                        })

            # Sort by priority (highest first)
            pending_tasks.sort(key=lambda t: t["priority"], reverse=True)

            return ResourceContent(
                uri="atlas://tasks/pending",
                name="Pending Tasks",
                content={
                    "tasks": pending_tasks,
                    "total": len(pending_tasks),
                },
                description="Pending tasks across all projects, sorted by priority",
            )
        except Exception as e:
            logger.exception(f"Error getting pending tasks resource: {e}")
            return ResourceContent(
                uri="atlas://tasks/pending",
                name="Pending Tasks",
                content={"error": str(e), "tasks": []},
            )
