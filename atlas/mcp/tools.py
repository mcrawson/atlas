"""
MCP Tool definitions for ATLAS Oracle.

Implements 7 tools for AI assistant integration:
- list_projects: List projects with status filter
- get_project: Get project by ID with tasks
- create_task: Create task in project
- execute_task: Run task through agent pipeline
- search_knowledge: Search knowledge base
- get_memory_context: Get recent conversations
- get_agent_status: Get agent pipeline status
"""

import logging
from typing import Any, Optional

from .models import ToolDefinition, ToolCallResult, ToolResultType

logger = logging.getLogger(__name__)


def get_tool_definitions() -> list[ToolDefinition]:
    """Return all MCP tool definitions."""
    return [
        ToolDefinition(
            name="list_projects",
            description="List ATLAS projects with optional status filter. Returns project summaries including task counts.",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status: 'active', 'completed', 'archived', or 'all'",
                        "enum": ["active", "completed", "archived", "all"],
                        "default": "all",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of projects to return",
                        "default": 20,
                    },
                },
                "required": [],
            },
        ),
        ToolDefinition(
            name="get_project",
            description="Get detailed information about a specific project including all its tasks.",
            input_schema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The project ID to retrieve",
                    },
                    "include_tasks": {
                        "type": "boolean",
                        "description": "Whether to include task details",
                        "default": True,
                    },
                },
                "required": ["project_id"],
            },
        ),
        ToolDefinition(
            name="create_task",
            description="Create a new task in an ATLAS project.",
            input_schema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The project ID to add the task to",
                    },
                    "title": {
                        "type": "string",
                        "description": "Task title (brief description)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed task description",
                        "default": "",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority level (higher = more important)",
                        "default": 0,
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization",
                        "default": [],
                    },
                },
                "required": ["project_id", "title"],
            },
        ),
        ToolDefinition(
            name="execute_task",
            description="Execute a task through the ATLAS agent pipeline (Architect -> Mason -> Oracle). Returns execution results and any generated artifacts.",
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "The task ID to execute",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Workflow mode: 'sequential' (full pipeline), 'direct_build' (skip planning), 'verify_only' (review only)",
                        "enum": ["sequential", "direct_build", "verify_only"],
                        "default": "sequential",
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context for execution",
                        "default": {},
                    },
                },
                "required": ["task_id"],
            },
        ),
        ToolDefinition(
            name="search_knowledge",
            description="Search the ATLAS knowledge base using full-text search. Returns relevant documents and snippets.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10,
                    },
                    "source_filter": {
                        "type": "string",
                        "description": "Filter by source type",
                        "default": None,
                    },
                },
                "required": ["query"],
            },
        ),
        ToolDefinition(
            name="get_memory_context",
            description="Get recent conversation history and memory context for continuity.",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent conversations to retrieve",
                        "default": 10,
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Filter by project context",
                        "default": None,
                    },
                },
                "required": [],
            },
        ),
        ToolDefinition(
            name="get_agent_status",
            description="Get current status of the ATLAS agent pipeline including Architect, Mason, and Oracle agents.",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Specific agent to query (architect, mason, oracle) or 'all' for all agents",
                        "enum": ["architect", "mason", "oracle", "all"],
                        "default": "all",
                    },
                },
                "required": [],
            },
        ),
    ]


class ToolExecutor:
    """Executes MCP tools using ATLAS managers."""

    def __init__(
        self,
        project_manager=None,
        agent_manager=None,
        knowledge_manager=None,
        memory_manager=None,
    ):
        """Initialize with ATLAS managers."""
        self.project_manager = project_manager
        self.agent_manager = agent_manager
        self.knowledge_manager = knowledge_manager
        self.memory_manager = memory_manager

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolCallResult:
        """Execute a tool by name with arguments."""
        try:
            handler = getattr(self, f"_execute_{tool_name}", None)
            if handler is None:
                return ToolCallResult(
                    success=False,
                    content=None,
                    content_type=ToolResultType.ERROR,
                    error_message=f"Unknown tool: {tool_name}",
                )
            return await handler(arguments)
        except Exception as e:
            logger.exception(f"Tool execution error for {tool_name}: {e}")
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message=str(e),
            )

    async def _execute_list_projects(self, args: dict[str, Any]) -> ToolCallResult:
        """List projects with optional status filter."""
        if not self.project_manager:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="Project manager not initialized",
            )

        status = args.get("status", "all")
        limit = args.get("limit", 20)

        try:
            projects = await self.project_manager.get_projects(include_tasks=True)

            # Filter by status if not "all"
            if status != "all":
                projects = [p for p in projects if p.status.value == status]

            # Limit results
            projects = projects[:limit]

            # Convert to serializable format
            project_list = []
            for p in projects:
                project_list.append({
                    "id": p.id,
                    "name": p.name,
                    "description": p.description[:200] if p.description else "",
                    "status": p.status.value,
                    "task_count": len(p.tasks) if p.tasks else 0,
                    "tags": p.tags,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                })

            return ToolCallResult(
                success=True,
                content={"projects": project_list, "total": len(project_list)},
            )
        except Exception as e:
            logger.exception(f"Error listing projects: {e}")
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message=str(e),
            )

    async def _execute_get_project(self, args: dict[str, Any]) -> ToolCallResult:
        """Get project by ID with tasks."""
        if not self.project_manager:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="Project manager not initialized",
            )

        project_id = args.get("project_id")
        include_tasks = args.get("include_tasks", True)

        if project_id is None:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="project_id is required",
            )

        try:
            project = await self.project_manager.get_project(
                project_id, include_tasks=include_tasks
            )

            if not project:
                return ToolCallResult(
                    success=False,
                    content=None,
                    content_type=ToolResultType.ERROR,
                    error_message=f"Project {project_id} not found",
                )

            # Convert to serializable format
            project_data = {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status.value,
                "tags": project.tags,
                "metadata": project.metadata,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            }

            if include_tasks and project.tasks:
                project_data["tasks"] = [
                    {
                        "id": t.id,
                        "title": t.title,
                        "description": t.description,
                        "status": t.status.value,
                        "priority": t.priority,
                        "tags": t.tags,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                    }
                    for t in project.tasks
                ]

            return ToolCallResult(success=True, content=project_data)
        except Exception as e:
            logger.exception(f"Error getting project: {e}")
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message=str(e),
            )

    async def _execute_create_task(self, args: dict[str, Any]) -> ToolCallResult:
        """Create a task in a project."""
        if not self.project_manager:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="Project manager not initialized",
            )

        project_id = args.get("project_id")
        title = args.get("title")

        if not project_id or not title:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="project_id and title are required",
            )

        try:
            task = await self.project_manager.create_task(
                project_id=project_id,
                title=title,
                description=args.get("description", ""),
                priority=args.get("priority", 0),
                tags=args.get("tags", []),
            )

            return ToolCallResult(
                success=True,
                content={
                    "id": task.id,
                    "project_id": task.project_id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status.value,
                    "priority": task.priority,
                    "tags": task.tags,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                },
            )
        except Exception as e:
            logger.exception(f"Error creating task: {e}")
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message=str(e),
            )

    async def _execute_execute_task(self, args: dict[str, Any]) -> ToolCallResult:
        """Execute a task through the agent pipeline."""
        if not self.project_manager:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="Project manager not initialized",
            )

        if not self.agent_manager:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="Agent manager not initialized",
            )

        task_id = args.get("task_id")
        mode = args.get("mode", "sequential")
        context = args.get("context", {})

        if task_id is None:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="task_id is required",
            )

        try:
            # Get the task
            task = await self.project_manager.get_task(task_id)
            if not task:
                return ToolCallResult(
                    success=False,
                    content=None,
                    content_type=ToolResultType.ERROR,
                    error_message=f"Task {task_id} not found",
                )

            # Map mode string to enum
            from atlas.agents.manager import WorkflowMode

            mode_map = {
                "sequential": WorkflowMode.SEQUENTIAL,
                "direct_build": WorkflowMode.DIRECT_BUILD,
                "verify_only": WorkflowMode.VERIFY_ONLY,
            }
            workflow_mode = mode_map.get(mode, WorkflowMode.SEQUENTIAL)

            # Execute workflow
            outputs = await self.agent_manager.execute_workflow(
                task=f"{task.title}: {task.description}",
                mode=workflow_mode,
                context=context,
            )

            # Store outputs in task
            await self.project_manager.update_task(
                task_id=task_id,
                status="in_progress",
            )

            # Format outputs for response
            result_outputs = {}
            for agent_name, output in outputs.items():
                result_outputs[agent_name] = {
                    "content": output.content if hasattr(output, "content") else str(output),
                    "status": output.status.value if hasattr(output, "status") else "completed",
                    "metadata": output.metadata if hasattr(output, "metadata") else {},
                }

            return ToolCallResult(
                success=True,
                content={
                    "task_id": task_id,
                    "mode": mode,
                    "outputs": result_outputs,
                },
            )
        except Exception as e:
            logger.exception(f"Error executing task: {e}")
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message=str(e),
            )

    async def _execute_search_knowledge(self, args: dict[str, Any]) -> ToolCallResult:
        """Search the knowledge base."""
        if not self.knowledge_manager:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="Knowledge manager not initialized",
            )

        query = args.get("query")
        limit = args.get("limit", 10)
        source_filter = args.get("source_filter")

        if not query:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="query is required",
            )

        try:
            results = await self.knowledge_manager.search(
                query=query,
                limit=limit,
                source=source_filter,
            )

            # Format results
            search_results = []
            for r in results:
                search_results.append({
                    "id": r.id if hasattr(r, "id") else None,
                    "title": r.title if hasattr(r, "title") else "",
                    "content": r.content[:500] if hasattr(r, "content") else str(r)[:500],
                    "score": r.score if hasattr(r, "score") else 0.0,
                    "source": r.source if hasattr(r, "source") else "unknown",
                })

            return ToolCallResult(
                success=True,
                content={"query": query, "results": search_results, "total": len(search_results)},
            )
        except Exception as e:
            logger.exception(f"Error searching knowledge: {e}")
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message=str(e),
            )

    async def _execute_get_memory_context(self, args: dict[str, Any]) -> ToolCallResult:
        """Get recent memory context."""
        if not self.memory_manager:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="Memory manager not initialized",
            )

        limit = args.get("limit", 10)
        project_id = args.get("project_id")

        try:
            # Get recent conversations
            conversations = await self.memory_manager.get_recent(
                limit=limit,
                project_id=project_id,
            )

            # Format for response
            context_data = []
            for conv in conversations:
                context_data.append({
                    "id": conv.id if hasattr(conv, "id") else None,
                    "role": conv.role if hasattr(conv, "role") else "unknown",
                    "content": conv.content[:500] if hasattr(conv, "content") else str(conv)[:500],
                    "timestamp": conv.timestamp.isoformat() if hasattr(conv, "timestamp") else None,
                })

            return ToolCallResult(
                success=True,
                content={"conversations": context_data, "total": len(context_data)},
            )
        except Exception as e:
            logger.exception(f"Error getting memory context: {e}")
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message=str(e),
            )

    async def _execute_get_agent_status(self, args: dict[str, Any]) -> ToolCallResult:
        """Get agent pipeline status."""
        if not self.agent_manager:
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message="Agent manager not initialized",
            )

        agent_name = args.get("agent_name", "all")

        try:
            all_status = self.agent_manager.get_all_status()

            if agent_name == "all":
                status_data = {}
                for name, status in all_status.items():
                    status_data[name] = {
                        "status": status.value if hasattr(status, "value") else str(status),
                        "current_task": getattr(self.agent_manager, name, None)
                        and getattr(getattr(self.agent_manager, name), "current_task", None),
                    }
                return ToolCallResult(
                    success=True,
                    content={"agents": status_data},
                )
            else:
                if agent_name not in all_status:
                    return ToolCallResult(
                        success=False,
                        content=None,
                        content_type=ToolResultType.ERROR,
                        error_message=f"Unknown agent: {agent_name}",
                    )

                status = all_status[agent_name]
                return ToolCallResult(
                    success=True,
                    content={
                        "name": agent_name,
                        "status": status.value if hasattr(status, "value") else str(status),
                    },
                )
        except Exception as e:
            logger.exception(f"Error getting agent status: {e}")
            return ToolCallResult(
                success=False,
                content=None,
                content_type=ToolResultType.ERROR,
                error_message=str(e),
            )
