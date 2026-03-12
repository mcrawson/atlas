"""Project Manager - SQLite-backed project CRUD operations."""

import json
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Project, ProjectTask, ProjectStatus, TaskStatus


class ProjectManager:
    """Manages projects and tasks with SQLite persistence.

    Uses the existing ATLAS data directory for storage.
    """

    def __init__(self, data_dir: Path):
        """Initialize project manager.

        Args:
            data_dir: Path to ATLAS data directory
        """
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "projects.db"
        self._initialized = False

    async def init_db(self):
        """Initialize the database schema."""
        if self._initialized:
            return

        self.data_dir.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            # Projects table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'active',
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Project tasks table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS project_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 0,
                    agent_outputs TEXT DEFAULT '[]',
                    artifacts TEXT DEFAULT '{}',
                    tags TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)

            # Index for faster queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_project_id
                ON project_tasks (project_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status
                ON project_tasks (status)
            """)

            # GitHub sync table for Transporter
            await db.execute("""
                CREATE TABLE IF NOT EXISTS github_sync (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    atlas_task_id INTEGER UNIQUE,
                    github_repo TEXT NOT NULL,
                    github_issue_number INTEGER NOT NULL,
                    last_sync TEXT,
                    sync_status TEXT DEFAULT 'pending',
                    FOREIGN KEY (atlas_task_id) REFERENCES project_tasks(id) ON DELETE CASCADE
                )
            """)

            # Index for GitHub sync lookups
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_github_sync_repo_issue
                ON github_sync (github_repo, github_issue_number)
            """)

            await db.commit()

        self._initialized = True

    async def create_project(
        self,
        name: str,
        description: str = "",
        tags: list[str] = None,
        metadata: dict = None,
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name
            description: Project description
            tags: Optional tags
            metadata: Optional metadata

        Returns:
            Created Project
        """
        await self.init_db()

        now = datetime.now().isoformat()
        tags = tags or []
        metadata = metadata or {}

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO projects (name, description, tags, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, description, json.dumps(tags), json.dumps(metadata), now, now)
            )
            await db.commit()

            return Project(
                id=cursor.lastrowid,
                name=name,
                description=description,
                tags=tags,
                metadata=metadata,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )

    async def get_project(self, project_id: int, include_tasks: bool = True) -> Optional[Project]:
        """Get a project by ID.

        Args:
            project_id: Project ID
            include_tasks: Whether to load tasks

        Returns:
            Project or None
        """
        await self.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            project = self._row_to_project(row)

            if include_tasks:
                tasks_cursor = await db.execute(
                    "SELECT * FROM project_tasks WHERE project_id = ? ORDER BY priority DESC, created_at ASC",
                    (project_id,)
                )
                task_rows = await tasks_cursor.fetchall()
                project.tasks = [self._row_to_task(r) for r in task_rows]

            return project

    async def get_projects(
        self,
        status: Optional[ProjectStatus] = None,
        limit: int = 50,
        include_tasks: bool = False,
    ) -> list[Project]:
        """Get all projects.

        Args:
            status: Optional status filter
            limit: Maximum projects to return
            include_tasks: Whether to load tasks

        Returns:
            List of Projects
        """
        await self.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if status:
                cursor = await db.execute(
                    "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status.value, limit)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM projects ORDER BY updated_at DESC LIMIT ?",
                    (limit,)
                )

            rows = await cursor.fetchall()
            projects = [self._row_to_project(r) for r in rows]

            if include_tasks:
                for project in projects:
                    tasks_cursor = await db.execute(
                        "SELECT * FROM project_tasks WHERE project_id = ? ORDER BY priority DESC",
                        (project.id,)
                    )
                    task_rows = await tasks_cursor.fetchall()
                    project.tasks = [self._row_to_task(r) for r in task_rows]

            return projects

    async def update_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[Project]:
        """Update a project.

        Args:
            project_id: Project ID
            name: New name
            description: New description
            status: New status
            tags: New tags
            metadata: New metadata

        Returns:
            Updated Project or None
        """
        await self.init_db()

        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if status is not None:
            updates.append("status = ?")
            params.append(status.value)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not updates:
            return await self.get_project(project_id)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(project_id)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()

        return await self.get_project(project_id)

    async def delete_project(self, project_id: int) -> bool:
        """Delete a project and its tasks.

        Args:
            project_id: Project ID

        Returns:
            True if deleted
        """
        await self.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            # Tasks are deleted via CASCADE
            cursor = await db.execute(
                "DELETE FROM projects WHERE id = ?",
                (project_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def add_task(
        self,
        project_id: int,
        title: str,
        description: str = "",
        priority: int = 0,
        tags: list[str] = None,
        metadata: dict = None,
    ) -> Optional[ProjectTask]:
        """Add a task to a project.

        Args:
            project_id: Project ID
            title: Task title
            description: Task description
            priority: Task priority (higher = more important)
            tags: Optional tags
            metadata: Optional metadata

        Returns:
            Created ProjectTask or None if project doesn't exist
        """
        await self.init_db()

        # Verify project exists
        project = await self.get_project(project_id, include_tasks=False)
        if not project:
            return None

        now = datetime.now().isoformat()
        tags = tags or []

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO project_tasks
                (project_id, title, description, priority, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, title, description, priority, json.dumps(tags), now, now)
            )
            await db.commit()

            return ProjectTask(
                id=cursor.lastrowid,
                project_id=project_id,
                title=title,
                description=description,
                priority=priority,
                tags=tags,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )

    # Alias for MCP tools compatibility
    create_task = add_task

    async def get_task(self, task_id: int) -> Optional[ProjectTask]:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            ProjectTask or None
        """
        await self.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                "SELECT * FROM project_tasks WHERE id = ?",
                (task_id,)
            )
            row = await cursor.fetchone()

            return self._row_to_task(row) if row else None

    async def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
    ) -> Optional[ProjectTask]:
        """Update a task's status.

        Args:
            task_id: Task ID
            status: New status

        Returns:
            Updated ProjectTask or None
        """
        await self.init_db()

        now = datetime.now().isoformat()
        # Handle both enum and string status
        status_str = status.value if hasattr(status, 'value') else status
        completed_statuses = (TaskStatus.COMPLETED, TaskStatus.FAILED)
        is_completed = status in completed_statuses or status_str in ('completed', 'failed')
        completed_at = now if is_completed else None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE project_tasks
                SET status = ?, updated_at = ?, completed_at = ?
                WHERE id = ?
                """,
                (status_str, now, completed_at, task_id)
            )
            await db.commit()

        return await self.get_task(task_id)

    async def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[int] = None,
        agent_outputs: Optional[list] = None,
        artifacts: Optional[dict] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[ProjectTask]:
        """Update a task.

        Args:
            task_id: Task ID
            title: New title
            description: New description
            status: New status
            priority: New priority
            agent_outputs: Agent outputs (replaces existing)
            artifacts: Artifacts (replaces existing)
            tags: New tags

        Returns:
            Updated ProjectTask or None
        """
        await self.init_db()

        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if status is not None:
            updates.append("status = ?")
            # Handle both enum and string status
            status_str = status.value if hasattr(status, 'value') else status
            params.append(status_str)
            # Check for completion status
            completed_statuses = (TaskStatus.COMPLETED, TaskStatus.FAILED)
            is_completed = status in completed_statuses or status_str in ('completed', 'failed')
            if is_completed:
                updates.append("completed_at = ?")
                params.append(datetime.now().isoformat())
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        if agent_outputs is not None:
            updates.append("agent_outputs = ?")
            params.append(json.dumps([o.to_dict() if hasattr(o, 'to_dict') else o for o in agent_outputs]))
        if artifacts is not None:
            updates.append("artifacts = ?")
            params.append(json.dumps(artifacts))
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))

        if not updates:
            return await self.get_task(task_id)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(task_id)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE project_tasks SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()

        return await self.get_task(task_id)

    async def add_agent_output(
        self,
        task_id: int,
        agent_name: str,
        content: str,
        artifacts: dict = None,
        metadata: dict = None,
    ) -> Optional[ProjectTask]:
        """Add an agent output to a task.

        Args:
            task_id: Task ID
            agent_name: Name of the agent
            content: Output content
            artifacts: Optional artifacts
            metadata: Optional metadata

        Returns:
            Updated ProjectTask or None
        """
        task = await self.get_task(task_id)
        if not task:
            return None

        from .models import AgentWorkOutput
        task.agent_outputs.append(AgentWorkOutput(
            agent_name=agent_name,
            content=content,
            artifacts=artifacts or {},
            metadata=metadata or {},
        ))

        return await self.update_task(
            task_id,
            agent_outputs=task.agent_outputs,
        )

    async def get_project_tasks(
        self,
        project_id: int,
        status: Optional[TaskStatus] = None,
    ) -> list[ProjectTask]:
        """Get tasks for a project.

        Args:
            project_id: Project ID
            status: Optional status filter

        Returns:
            List of ProjectTasks
        """
        await self.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if status:
                cursor = await db.execute(
                    "SELECT * FROM project_tasks WHERE project_id = ? AND status = ? ORDER BY priority DESC",
                    (project_id, status.value)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM project_tasks WHERE project_id = ? ORDER BY priority DESC",
                    (project_id,)
                )

            rows = await cursor.fetchall()
            return [self._row_to_task(r) for r in rows]

    async def get_all_pending_tasks(self, limit: int = 20) -> list[ProjectTask]:
        """Get all pending tasks across projects.

        Args:
            limit: Maximum tasks to return

        Returns:
            List of pending ProjectTasks
        """
        await self.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                """
                SELECT * FROM project_tasks
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
                """,
                (limit,)
            )
            rows = await cursor.fetchall()
            return [self._row_to_task(r) for r in rows]

    async def get_stats(self) -> dict:
        """Get project and task statistics.

        Returns:
            Statistics dictionary
        """
        await self.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            # Project counts by status
            cursor = await db.execute(
                "SELECT status, COUNT(*) as count FROM projects GROUP BY status"
            )
            project_counts = {row[0]: row[1] for row in await cursor.fetchall()}

            # Task counts by status
            cursor = await db.execute(
                "SELECT status, COUNT(*) as count FROM project_tasks GROUP BY status"
            )
            task_counts = {row[0]: row[1] for row in await cursor.fetchall()}

            # Total counts
            cursor = await db.execute("SELECT COUNT(*) FROM projects")
            total_projects = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT COUNT(*) FROM project_tasks")
            total_tasks = (await cursor.fetchone())[0]

            return {
                "total_projects": total_projects,
                "total_tasks": total_tasks,
                "projects_by_status": project_counts,
                "tasks_by_status": task_counts,
            }

    def _row_to_project(self, row) -> Project:
        """Convert database row to Project."""
        return Project(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            status=ProjectStatus(row["status"]),
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_task(self, row) -> ProjectTask:
        """Convert database row to ProjectTask."""
        from .models import AgentWorkOutput

        agent_outputs_raw = json.loads(row["agent_outputs"])
        agent_outputs = [AgentWorkOutput.from_dict(o) for o in agent_outputs_raw]

        return ProjectTask(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            priority=row["priority"],
            agent_outputs=agent_outputs,
            artifacts=json.loads(row["artifacts"]),
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )
