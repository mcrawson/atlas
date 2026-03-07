"""Background task worker for ATLAS."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .queue import TaskQueue, TaskStatus

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("atlas.worker")


class TaskWorker:
    """Async background worker for processing queued tasks."""

    def __init__(
        self,
        queue: TaskQueue,
        process_func: Callable,
        poll_interval: float = 30.0,
        on_complete: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """Initialize worker.

        Args:
            queue: TaskQueue instance
            process_func: Async function to process tasks. Takes (prompt, task_type) and returns (result, model_used)
            poll_interval: Seconds between queue checks
            on_complete: Optional callback when task completes
            on_error: Optional callback when task fails
        """
        self.queue = queue
        self.process_func = process_func
        self.poll_interval = poll_interval
        self.on_complete = on_complete
        self.on_error = on_error
        self._running = False
        self._current_task = None

    async def process_task(self, task: dict) -> None:
        """Process a single task.

        Args:
            task: Task dictionary from queue
        """
        task_id = task["id"]
        prompt = task["prompt"]
        task_type = task.get("task_type", "general")

        logger.info(f"Processing task {task_id}: {prompt[:50]}...")

        # Mark as running
        await self.queue.update_task_status(task_id, TaskStatus.RUNNING)
        self._current_task = task_id

        try:
            # Process the task
            result, model_used = await self.process_func(prompt, task_type)

            # Mark as completed
            await self.queue.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                result=result,
                model_used=model_used,
            )

            logger.info(f"Task {task_id} completed via {model_used}")

            if self.on_complete:
                await self._safe_callback(self.on_complete, task, result)

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")

            await self.queue.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=str(e),
            )

            if self.on_error:
                await self._safe_callback(self.on_error, task, e)

        finally:
            self._current_task = None

    async def _safe_callback(self, callback: Callable, *args) -> None:
        """Safely execute a callback."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Callback error: {e}")

    async def run(self) -> None:
        """Run the worker loop."""
        self._running = True
        logger.info("ATLAS worker started")

        while self._running:
            try:
                # Get next task
                task = await self.queue.get_next_task()

                if task:
                    await self.process_task(task)
                else:
                    # No tasks, wait before checking again
                    await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                logger.info("Worker cancelled")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(self.poll_interval)

        logger.info("ATLAS worker stopped")

    def stop(self) -> None:
        """Signal the worker to stop."""
        self._running = False
        logger.info("Worker stop requested")

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running

    @property
    def current_task(self) -> Optional[int]:
        """Get currently processing task ID."""
        return self._current_task


class BriefingGenerator:
    """Generate session briefings from completed tasks."""

    def __init__(self, queue: TaskQueue, memory_dir: Path):
        """Initialize briefing generator.

        Args:
            queue: TaskQueue instance
            memory_dir: Path to memory storage
        """
        self.queue = queue
        self.briefings_dir = memory_dir / "briefings"
        self.briefings_dir.mkdir(parents=True, exist_ok=True)

    async def generate_briefing(self) -> dict:
        """Generate a briefing from recent activity.

        Returns:
            Briefing dictionary
        """
        # Get queue stats
        stats = await self.queue.get_queue_stats()

        # Get recent completed tasks
        completed = await self.queue.get_recent_completed(hours=24)

        # Build briefing
        briefing = {
            "timestamp": datetime.now().isoformat(),
            "queue_stats": stats,
            "completed_today": len(completed),
            "tasks_summary": [],
        }

        # Summarize completed tasks
        for task in completed[:10]:  # Last 10
            summary = {
                "prompt": task["prompt"][:100] + "..." if len(task["prompt"]) > 100 else task["prompt"],
                "type": task.get("task_type", "general"),
                "model": task.get("model_used", "unknown"),
                "completed": task.get("completed_at", ""),
            }
            briefing["tasks_summary"].append(summary)

        return briefing

    async def save_briefing(self, briefing: dict) -> Path:
        """Save briefing to markdown file.

        Args:
            briefing: Briefing dictionary

        Returns:
            Path to saved briefing
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        path = self.briefings_dir / f"{timestamp}_briefing.md"

        lines = [
            f"# ATLAS Briefing - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Queue Status",
            "",
            f"- Pending: {briefing['queue_stats'].get('pending', 0)}",
            f"- Running: {briefing['queue_stats'].get('running', 0)}",
            f"- Completed (24h): {briefing['completed_today']}",
            f"- Failed: {briefing['queue_stats'].get('failed', 0)}",
            "",
        ]

        if briefing["tasks_summary"]:
            lines.extend([
                "## Recent Completed Tasks",
                "",
            ])
            for task in briefing["tasks_summary"]:
                lines.append(f"### {task['type'].title()} via {task['model']}")
                lines.append(f"> {task['prompt']}")
                lines.append("")

        path.write_text("\n".join(lines))
        return path

    def format_briefing_text(self, briefing: dict) -> str:
        """Format briefing for console display.

        Args:
            briefing: Briefing dictionary

        Returns:
            Formatted text
        """
        stats = briefing["queue_stats"]

        lines = [
            "=" * 50,
            "  ATLAS Background Task Briefing",
            "=" * 50,
            "",
            f"  Pending tasks:     {stats.get('pending', 0)}",
            f"  Currently running: {stats.get('running', 0)}",
            f"  Completed (24h):   {briefing['completed_today']}",
            f"  Failed:            {stats.get('failed', 0)}",
            "",
        ]

        if briefing["tasks_summary"]:
            lines.append("  Recent completions:")
            for task in briefing["tasks_summary"][:5]:
                lines.append(f"    - [{task['type']}] {task['prompt'][:40]}...")

        lines.append("=" * 50)

        return "\n".join(lines)
