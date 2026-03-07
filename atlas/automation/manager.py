"""Automation Manager - orchestrates automation tasks."""

import asyncio
import uuid
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, AsyncIterator

from .models import AutomationTask, TaskStatus, CommandRisk, CommandResult
from .executor import CommandExecutor


class AutomationManager:
    """Manages automation tasks with persistence and execution."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize automation manager.

        Args:
            db_path: Path to SQLite database
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "automation.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Active tasks being executed
        self._running_tasks: dict[str, AutomationTask] = {}
        self._task_callbacks: dict[str, list[Callable]] = {}

    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS automation_tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    commands TEXT NOT NULL,
                    status TEXT NOT NULL,
                    working_dir TEXT,
                    env_vars TEXT,
                    results TEXT,
                    risk_level TEXT,
                    requires_approval INTEGER,
                    approved INTEGER,
                    approved_by TEXT,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    error TEXT,
                    source TEXT
                )
            """)
            conn.commit()

    def create_task(
        self,
        name: str,
        commands: list[str],
        description: str = "",
        working_dir: Optional[str] = None,
        env_vars: Optional[dict] = None,
        source: Optional[str] = None,
        auto_approve_safe: bool = True,
    ) -> AutomationTask:
        """Create a new automation task.

        Args:
            name: Task name
            commands: List of commands to execute
            description: Task description
            working_dir: Working directory
            env_vars: Environment variables
            source: Source (e.g., "knowledge:ios-deployment")
            auto_approve_safe: Auto-approve if all commands are safe

        Returns:
            Created AutomationTask
        """
        task_id = str(uuid.uuid4())[:8]

        # Assess overall risk
        executor = CommandExecutor()
        max_risk = CommandRisk.LOW
        for cmd in commands:
            risk, _ = executor.assess_risk(cmd)
            if risk.value > max_risk.value:
                max_risk = risk

        # Determine if approval needed
        requires_approval = max_risk != CommandRisk.LOW
        approved = not requires_approval if auto_approve_safe else False

        task = AutomationTask(
            id=task_id,
            name=name,
            description=description,
            commands=commands,
            status=TaskStatus.PENDING if approved else TaskStatus.AWAITING_APPROVAL,
            working_dir=working_dir,
            env_vars=env_vars or {},
            risk_level=max_risk,
            requires_approval=requires_approval,
            approved=approved,
            source=source,
        )

        self._save_task(task)
        return task

    def create_from_knowledge(
        self,
        knowledge_entry_id: str,
        working_dir: Optional[str] = None,
        env_vars: Optional[dict] = None,
    ) -> Optional[AutomationTask]:
        """Create an automation task from a knowledge base entry.

        Args:
            knowledge_entry_id: ID of the knowledge entry
            working_dir: Working directory
            env_vars: Environment variables

        Returns:
            Created AutomationTask or None if entry not found
        """
        try:
            from ..knowledge import KnowledgeManager

            km = KnowledgeManager()
            entry = km.get(knowledge_entry_id)

            if not entry or not entry.commands:
                return None

            return self.create_task(
                name=f"Run: {entry.title}",
                commands=entry.commands,
                description=f"Commands from {entry.title}",
                working_dir=working_dir,
                env_vars=env_vars,
                source=f"knowledge:{knowledge_entry_id}",
            )
        except ImportError:
            return None

    def approve_task(self, task_id: str, approved_by: str = "user") -> bool:
        """Approve a task for execution.

        Args:
            task_id: Task ID to approve
            approved_by: Who approved (for audit)

        Returns:
            True if approved successfully
        """
        task = self.get_task(task_id)
        if not task:
            return False

        if task.status != TaskStatus.AWAITING_APPROVAL:
            return False

        task.approved = True
        task.approved_by = approved_by
        task.status = TaskStatus.PENDING
        self._save_task(task)
        return True

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancelled
        """
        task = self.get_task(task_id)
        if not task:
            return False

        if task.is_complete:
            return False

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        self._save_task(task)
        return True

    async def execute_task(
        self,
        task_id: str,
        on_output: Optional[Callable[[str, str], None]] = None,
        on_command_complete: Optional[Callable[[int, CommandResult], None]] = None,
    ) -> AutomationTask:
        """Execute an automation task.

        Args:
            task_id: Task ID to execute
            on_output: Callback(task_id, line) for output
            on_command_complete: Callback(index, result) per command

        Returns:
            Updated task after execution
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if not task.approved:
            raise ValueError(f"Task {task_id} not approved")

        if task.status == TaskStatus.RUNNING:
            raise ValueError(f"Task {task_id} already running")

        # Update status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self._running_tasks[task_id] = task
        self._save_task(task)

        # Create executor
        executor = CommandExecutor(
            working_dir=task.working_dir,
            env_vars=task.env_vars,
        )

        try:
            # Execute each command
            for i, command in enumerate(task.commands):
                if on_output:
                    on_output(task_id, f"\n$ {command}\n")

                result = await executor.execute(
                    command,
                    on_output=lambda line: on_output(task_id, line) if on_output else None,
                )

                task.results.append(result)

                if on_command_complete:
                    on_command_complete(i, result)

                # Stop on failure
                if not result.success:
                    task.status = TaskStatus.FAILED
                    task.error = f"Command failed: {command}"
                    break

            # Mark complete if all succeeded
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.COMPLETED

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

        finally:
            task.completed_at = datetime.now()
            self._running_tasks.pop(task_id, None)
            self._save_task(task)

        return task

    async def execute_single_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
        require_approval: bool = True,
    ) -> CommandResult:
        """Execute a single command (convenience method).

        Args:
            command: Command to execute
            working_dir: Working directory
            require_approval: Whether to require approval for risky commands

        Returns:
            CommandResult
        """
        executor = CommandExecutor(working_dir=working_dir)

        # Check if safe
        if require_approval and not executor.is_safe(command):
            risk, reason = executor.assess_risk(command)
            raise ValueError(
                f"Command requires approval (risk: {risk.value}): {reason or command}"
            )

        return await executor.execute(command)

    def get_task(self, task_id: str) -> Optional[AutomationTask]:
        """Get a task by ID."""
        # Check running tasks first
        if task_id in self._running_tasks:
            return self._running_tasks[task_id]

        # Load from database
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM automation_tasks WHERE id = ?",
                (task_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_task(row)
        return None

    def get_pending_tasks(self) -> list[AutomationTask]:
        """Get all pending/awaiting approval tasks."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM automation_tasks
                WHERE status IN (?, ?)
                ORDER BY created_at DESC
            """, (TaskStatus.PENDING.value, TaskStatus.AWAITING_APPROVAL.value))
            return [self._row_to_task(row) for row in cursor.fetchall()]

    def get_recent_tasks(self, limit: int = 20) -> list[AutomationTask]:
        """Get recent tasks."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM automation_tasks
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [self._row_to_task(row) for row in cursor.fetchall()]

    def _save_task(self, task: AutomationTask):
        """Save task to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO automation_tasks
                (id, name, description, commands, status, working_dir, env_vars,
                 results, risk_level, requires_approval, approved, approved_by,
                 created_at, started_at, completed_at, error, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id,
                task.name,
                task.description,
                json.dumps(task.commands),
                task.status.value,
                task.working_dir,
                json.dumps(task.env_vars),
                json.dumps([r.to_dict() for r in task.results]),
                task.risk_level.value,
                1 if task.requires_approval else 0,
                1 if task.approved else 0,
                task.approved_by,
                task.created_at.isoformat(),
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                task.error,
                task.source,
            ))
            conn.commit()

    def _row_to_task(self, row: sqlite3.Row) -> AutomationTask:
        """Convert database row to AutomationTask."""
        results_data = json.loads(row["results"]) if row["results"] else []
        results = [
            CommandResult(
                command=r["command"],
                exit_code=r["exit_code"],
                stdout=r["stdout"],
                stderr=r["stderr"],
                duration_ms=r["duration_ms"],
                success=r["success"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
            )
            for r in results_data
        ]

        return AutomationTask(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            commands=json.loads(row["commands"]),
            status=TaskStatus(row["status"]),
            working_dir=row["working_dir"],
            env_vars=json.loads(row["env_vars"]) if row["env_vars"] else {},
            results=results,
            risk_level=CommandRisk(row["risk_level"]),
            requires_approval=bool(row["requires_approval"]),
            approved=bool(row["approved"]),
            approved_by=row["approved_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"],
            source=row["source"],
        )
