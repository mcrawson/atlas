"""Spec Manager for ATLAS.

Manages spec files, tracks progress, and integrates with the agent workflow.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

from .models import Spec, TaskStatus


class SpecManager:
    """Manages specs with persistence."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize spec manager.

        Args:
            db_path: Path to SQLite database
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "specs.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS specs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    spec_dir TEXT,
                    version TEXT DEFAULT '1.0.0',
                    status TEXT DEFAULT 'active',
                    requirements_count INTEGER DEFAULT 0,
                    tasks_count INTEGER DEFAULT 0,
                    tasks_completed INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spec_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spec_id INTEGER,
                    task_id TEXT NOT NULL,
                    title TEXT,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'medium',
                    requirement_ids TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (spec_id) REFERENCES specs(id)
                )
            """)
            conn.commit()

    def save_spec(
        self,
        spec: Spec,
        project_id: Optional[int] = None,
        spec_dir: Optional[str] = None,
    ) -> int:
        """Save a spec to the database.

        Args:
            spec: The spec to save
            project_id: Optional project ID to associate with
            spec_dir: Optional spec directory path

        Returns:
            The spec ID
        """
        now = datetime.now().isoformat()
        tasks_count = len(spec.tasks.tasks) if spec.tasks else 0
        tasks_completed = sum(
            1 for t in (spec.tasks.tasks if spec.tasks else [])
            if t.status == TaskStatus.COMPLETED
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO specs (
                    project_id, name, description, spec_dir, version,
                    requirements_count, tasks_count, tasks_completed,
                    created_at, updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                spec.name,
                spec.description,
                spec_dir,
                spec.version,
                len(spec.requirements),
                tasks_count,
                tasks_completed,
                now,
                now,
                json.dumps(spec.to_dict()),
            ))
            spec_id = cursor.lastrowid

            # Save tasks
            if spec.tasks:
                for task in spec.tasks.tasks:
                    conn.execute("""
                        INSERT INTO spec_tasks (
                            spec_id, task_id, title, status, priority, requirement_ids
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        spec_id,
                        task.id,
                        task.title,
                        task.status.value,
                        task.priority.value,
                        json.dumps(task.requirement_ids),
                    ))

            conn.commit()
            return spec_id

    def get_spec(self, spec_id: int) -> Optional[dict]:
        """Get a spec by ID.

        Args:
            spec_id: The spec ID

        Returns:
            Spec data or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM specs WHERE id = ?",
                (spec_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def get_specs_for_project(self, project_id: int) -> list[dict]:
        """Get all specs for a project.

        Args:
            project_id: The project ID

        Returns:
            List of spec data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM specs WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_tasks_for_spec(self, spec_id: int) -> list[dict]:
        """Get all tasks for a spec.

        Args:
            spec_id: The spec ID

        Returns:
            List of task data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM spec_tasks WHERE spec_id = ? ORDER BY task_id",
                (spec_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_task_status(
        self,
        spec_id: int,
        task_id: str,
        status: str,
    ) -> bool:
        """Update a task's status.

        Args:
            spec_id: The spec ID
            task_id: The task ID
            status: New status

        Returns:
            True if updated
        """
        now = datetime.now().isoformat()
        completed_at = now if status == "completed" else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE spec_tasks
                SET status = ?, completed_at = ?
                WHERE spec_id = ? AND task_id = ?
            """, (status, completed_at, spec_id, task_id))

            # Update spec progress
            cursor = conn.execute("""
                SELECT COUNT(*) as completed FROM spec_tasks
                WHERE spec_id = ? AND status = 'completed'
            """, (spec_id,))
            completed = cursor.fetchone()[0]

            conn.execute("""
                UPDATE specs SET tasks_completed = ?, updated_at = ?
                WHERE id = ?
            """, (completed, now, spec_id))

            conn.commit()
            return True

    def get_pending_tasks(self, spec_id: int) -> list[dict]:
        """Get all pending tasks for a spec.

        Args:
            spec_id: The spec ID

        Returns:
            List of pending tasks
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM spec_tasks
                WHERE spec_id = ? AND status = 'pending'
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                    END,
                    task_id
            """, (spec_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_spec_progress(self, spec_id: int) -> dict:
        """Get progress for a spec.

        Args:
            spec_id: The spec ID

        Returns:
            Progress data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get counts
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked
                FROM spec_tasks WHERE spec_id = ?
            """, (spec_id,))
            row = cursor.fetchone()

            total = row["total"] or 0
            completed = row["completed"] or 0

            return {
                "total": total,
                "completed": completed,
                "in_progress": row["in_progress"] or 0,
                "pending": row["pending"] or 0,
                "blocked": row["blocked"] or 0,
                "percentage": (completed / total * 100) if total > 0 else 0,
            }

    def read_spec_files(self, spec_dir: str) -> dict:
        """Read spec files from a directory.

        Args:
            spec_dir: Path to spec directory

        Returns:
            Dict with file contents
        """
        path = Path(spec_dir)
        files = {}

        req_path = path / "requirements.md"
        if req_path.exists():
            files["requirements"] = req_path.read_text()

        design_path = path / "design.md"
        if design_path.exists():
            files["design"] = design_path.read_text()

        tasks_path = path / "tasks.md"
        if tasks_path.exists():
            files["tasks"] = tasks_path.read_text()

        return files

    def find_kiro_specs(self, project_dir: str) -> list[str]:
        """Find all .kiro spec directories in a project.

        Args:
            project_dir: Project directory path

        Returns:
            List of spec directory paths
        """
        kiro_dir = Path(project_dir) / ".kiro" / "specs"
        if not kiro_dir.exists():
            return []

        specs = []
        for spec_dir in kiro_dir.iterdir():
            if spec_dir.is_dir():
                specs.append(str(spec_dir))

        return specs
