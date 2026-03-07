"""SQLite-based task queue for ATLAS background processing."""

import asyncio
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import aiosqlite


class TaskStatus(Enum):
    """Task status states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskQueue:
    """Persistent task queue using SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize task queue.

        Args:
            db_path: Path to SQLite database. Defaults to ~/ai-workspace/atlas/data/tasks.db
        """
        self.db_path = db_path or Path.home() / "ai-workspace" / "atlas" / "data" / "tasks.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure database schema exists."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt TEXT NOT NULL,
                    task_type TEXT DEFAULT 'general',
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    error TEXT,
                    model_used TEXT,
                    metadata TEXT
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)
            """)
            await db.commit()

        self._initialized = True

    async def add_task(
        self,
        prompt: str,
        task_type: str = "general",
        priority: int = 0,
        metadata: Optional[dict] = None,
    ) -> int:
        """Add a new task to the queue.

        Args:
            prompt: The task prompt/description
            task_type: Type of task (research, code, review, draft, general)
            priority: Priority level (higher = more urgent)
            metadata: Optional metadata dictionary

        Returns:
            Task ID
        """
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO tasks (prompt, task_type, status, priority, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    prompt,
                    task_type,
                    TaskStatus.PENDING.value,
                    priority,
                    datetime.now().isoformat(),
                    json.dumps(metadata) if metadata else None,
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_next_task(self) -> Optional[dict]:
        """Get the next pending task (highest priority, oldest first).

        Returns:
            Task dictionary or None if no pending tasks
        """
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM tasks
                WHERE status = ?
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                """,
                (TaskStatus.PENDING.value,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
        result: Optional[str] = None,
        error: Optional[str] = None,
        model_used: Optional[str] = None,
    ) -> None:
        """Update task status.

        Args:
            task_id: Task ID to update
            status: New status
            result: Task result (for completed tasks)
            error: Error message (for failed tasks)
            model_used: Model that processed the task
        """
        await self._ensure_initialized()

        now = datetime.now().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            if status == TaskStatus.RUNNING:
                await db.execute(
                    "UPDATE tasks SET status = ?, started_at = ? WHERE id = ?",
                    (status.value, now, task_id),
                )
            elif status == TaskStatus.COMPLETED:
                await db.execute(
                    """
                    UPDATE tasks SET status = ?, completed_at = ?, result = ?, model_used = ?
                    WHERE id = ?
                    """,
                    (status.value, now, result, model_used, task_id),
                )
            elif status == TaskStatus.FAILED:
                await db.execute(
                    "UPDATE tasks SET status = ?, completed_at = ?, error = ? WHERE id = ?",
                    (status.value, now, error, task_id),
                )
            else:
                await db.execute(
                    "UPDATE tasks SET status = ? WHERE id = ?",
                    (status.value, task_id),
                )
            await db.commit()

    async def get_task(self, task_id: int) -> Optional[dict]:
        """Get a specific task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task dictionary or None
        """
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def get_tasks_by_status(self, status: TaskStatus, limit: int = 50) -> list[dict]:
        """Get tasks by status.

        Args:
            status: Status to filter by
            limit: Maximum number of tasks to return

        Returns:
            List of task dictionaries
        """
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM tasks
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (status.value, limit),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_recent_completed(self, hours: int = 24) -> list[dict]:
        """Get recently completed tasks.

        Args:
            hours: Number of hours to look back

        Returns:
            List of completed task dictionaries
        """
        await self._ensure_initialized()

        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM tasks
                WHERE status = ? AND completed_at > ?
                ORDER BY completed_at DESC
                """,
                (TaskStatus.COMPLETED.value, cutoff),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_queue_stats(self) -> dict:
        """Get queue statistics.

        Returns:
            Dictionary with counts by status
        """
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT status, COUNT(*) as count
                FROM tasks
                GROUP BY status
                """
            )
            rows = await cursor.fetchall()
            stats = {status.value: 0 for status in TaskStatus}
            for row in rows:
                stats[row[0]] = row[1]
            return stats

    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """Remove old completed/failed tasks.

        Args:
            days: Delete tasks older than this many days

        Returns:
            Number of deleted tasks
        """
        await self._ensure_initialized()

        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM tasks
                WHERE status IN (?, ?) AND created_at < ?
                """,
                (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, cutoff),
            )
            await db.commit()
            return cursor.rowcount
