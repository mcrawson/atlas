"""
Overnight Autonomous Operator for ATLAS.

Main orchestrator that routes tasks to appropriate handlers and
manages the overnight processing session.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from atlas.operator.config import OvernightConfig
from atlas.operator.router import TaskRouter, TaskMode, RoutingResult
from atlas.operator.safety import SafetyLayer, SafetyViolation
from atlas.operator.modes.general import GeneralMode, GeneralResult
from atlas.operator.modes.healer import HealerMode, HealerResult
from atlas.operator.modes.builder import BuilderMode, BuildResult
from atlas.tasks.queue import TaskQueue, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class SessionStats:
    """Statistics for an overnight session."""
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    general_tasks: int = 0
    atlas_fixes: int = 0
    atlas_builds: int = 0
    stop_reason: str = ""


@dataclass
class TaskResult:
    """Unified result from any mode."""
    task_id: str
    mode: TaskMode
    success: bool
    summary: str
    details: str
    output_path: Optional[Path] = None
    branch: Optional[str] = None  # For healer mode


class OvernightOperator:
    """
    Routes and executes overnight tasks.

    Supports:
    - General tasks (research, drafts, reviews) via GeneralMode
    - ATLAS bug fixes via HealerMode
    - ATLAS product builds via BuilderMode
    """

    def __init__(self, config: Optional[OvernightConfig] = None):
        self.config = config or OvernightConfig.load()
        self.queue = TaskQueue()
        self.router = TaskRouter()
        self.safety = SafetyLayer(self.config)

        # Mode handlers
        self.general_mode = GeneralMode(self.config)
        self.healer_mode = HealerMode(self.config, self.safety)
        self.builder_mode = BuilderMode(self.config)

        # Session tracking
        self.stats = SessionStats()
        self._results: list[TaskResult] = []
        self._running = False

    async def run(
        self,
        test_mode: bool = False,
        force: bool = False,
        max_tasks: Optional[int] = None,
    ) -> SessionStats:
        """
        Run the overnight processing session.

        Args:
            test_mode: Process only 1 task for testing
            force: Skip time window check
            max_tasks: Override max tasks limit

        Returns:
            SessionStats with session summary
        """
        self._running = True
        self.stats = SessionStats()
        self._results = []

        # Initialize queue (called automatically on first operation)
        await self.queue._ensure_initialized()

        # Start session
        self.safety.start_session()

        task_limit = 1 if test_mode else (max_tasks or self.config.limits.max_tasks)

        logger.info(f"Starting overnight session (limit: {task_limit} tasks)")

        try:
            # Preflight check
            if not force and not test_mode:
                self.safety.check_window()

            while self._running:
                # Check limits
                try:
                    self.safety.full_preflight_check(
                        completed_tasks=self.stats.tasks_completed,
                        force=force or test_mode,
                    )
                except SafetyViolation as e:
                    self.stats.stop_reason = str(e)
                    logger.info(f"Stopping: {e}")
                    break

                # Check task limit
                if self.stats.tasks_completed >= task_limit:
                    self.stats.stop_reason = "Task limit reached"
                    break

                # Get next task
                task = await self.queue.get_next_task()
                if not task:
                    self.stats.stop_reason = "Queue empty"
                    logger.info("Queue empty, stopping")
                    break

                # Process task
                result = await self._process_task(task)
                self._results.append(result)

                if result.success:
                    self.stats.tasks_completed += 1
                    self.safety.record_success()
                else:
                    self.stats.tasks_failed += 1
                    self.safety.record_error()

                # Rate limiting
                await self.safety.wait_for_rate_limit()

        except SafetyViolation as e:
            self.stats.stop_reason = f"Safety violation: {e}"
            logger.warning(f"Safety violation: {e}")

        except Exception as e:
            self.stats.stop_reason = f"Error: {e}"
            logger.exception("Unexpected error in overnight session")

        finally:
            self._running = False
            self.stats.ended_at = datetime.now()

        # Generate and save briefing
        if self.config.briefing.enabled:
            await self._save_briefing()

        return self.stats

    def stop(self) -> None:
        """Signal the session to stop."""
        self._running = False
        self.stats.stop_reason = "Manual stop"

    async def _process_task(self, task: dict) -> TaskResult:
        """Process a single task with the appropriate handler."""
        task_id = task.get("id", "unknown")
        prompt = task.get("prompt", "")

        logger.info(f"Processing task {task_id}: {prompt[:50]}...")

        # Mark as running
        await self.queue.update_task_status(task_id, TaskStatus.RUNNING)

        # Route task
        routing = self.router.classify(task)
        logger.info(f"Routed to: {routing.mode.value} (confidence: {routing.confidence:.0%})")

        try:
            if routing.mode == TaskMode.GENERAL:
                result = await self._process_general(task, routing)
                self.stats.general_tasks += 1

            elif routing.mode == TaskMode.ATLAS_FIX:
                result = await self._process_healer(task)
                self.stats.atlas_fixes += 1

            elif routing.mode == TaskMode.ATLAS_BUILD:
                result = await self._process_builder(task)
                self.stats.atlas_builds += 1

            else:
                result = TaskResult(
                    task_id=task_id,
                    mode=routing.mode,
                    success=False,
                    summary="Unknown mode",
                    details="",
                )

            # Update queue status
            if result.success:
                await self.queue.update_task_status(
                    task_id,
                    TaskStatus.COMPLETED,
                    result=result.summary,
                )
            else:
                await self.queue.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    error=result.details,
                )

            return result

        except Exception as e:
            logger.exception(f"Error processing task {task_id}")
            await self.queue.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=str(e),
            )
            return TaskResult(
                task_id=task_id,
                mode=routing.mode,
                success=False,
                summary="Processing error",
                details=str(e),
            )

    async def _process_general(
        self, task: dict, routing: RoutingResult
    ) -> TaskResult:
        """Process a general task."""
        task_id = task.get("id", "unknown")

        result: GeneralResult = await self.general_mode.execute(
            task,
            role=routing.suggested_role,
        )

        # Save output
        output_path = await self.general_mode.save_result(result, task)

        # Extract key findings (first ~800 chars or first few paragraphs)
        content_preview = result.content[:800]
        if len(result.content) > 800:
            # Try to break at a paragraph
            last_para = content_preview.rfind("\n\n")
            if last_para > 400:
                content_preview = content_preview[:last_para]
            content_preview += "..."

        return TaskResult(
            task_id=task_id,
            mode=TaskMode.GENERAL,
            success=True,
            summary=f"{result.role_used}: {task.get('prompt', '')[:50]}",
            details=content_preview,
            output_path=output_path,
        )

    async def _process_healer(self, task: dict) -> TaskResult:
        """Process an ATLAS fix task."""
        task_id = task.get("id", "unknown")

        result: HealerResult = await self.healer_mode.execute(task)

        summary = f"Fix: {result.analysis.summary[:50]}" if result.analysis.summary else "Fix attempted"

        details = ""
        if result.success:
            details = f"Branch: {result.branch}\nCommit: {result.commit_sha}\nTests: PASS"
        else:
            details = f"Branch: {result.branch}\nError: {result.error}\nTests: {'PASS' if result.tests_passed else 'FAIL'}"

        return TaskResult(
            task_id=task_id,
            mode=TaskMode.ATLAS_FIX,
            success=result.success,
            summary=summary,
            details=details,
            branch=result.branch,
        )

    async def _process_builder(self, task: dict) -> TaskResult:
        """Process an ATLAS build task."""
        task_id = task.get("id", "unknown")

        result: BuildResult = await self.builder_mode.execute(task)

        summary = f"Build: {result.project_name}" if result.project_name else "Build attempted"

        details = f"QC: {result.qc_status}\nIterations: {result.iterations}"
        if result.project_path:
            details += f"\nPath: {result.project_path}"
        if result.error:
            details += f"\nError: {result.error}"

        return TaskResult(
            task_id=task_id,
            mode=TaskMode.ATLAS_BUILD,
            success=result.success,
            summary=summary,
            details=details,
            output_path=result.project_path,
        )

    async def _save_briefing(self) -> Path:
        """Generate and save the morning briefing."""
        briefing_dir = self.config.briefing.dir
        briefing_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d")
        briefing_path = briefing_dir / f"briefing-{timestamp}.md"

        # Build briefing content
        content = self._format_briefing()

        briefing_path.write_text(content)
        logger.info(f"Saved briefing to: {briefing_path}")

        # Also save as JSON for programmatic access
        json_path = briefing_dir / f"briefing-{timestamp}.json"
        json_data = {
            "stats": {
                "started_at": self.stats.started_at.isoformat(),
                "ended_at": self.stats.ended_at.isoformat() if self.stats.ended_at else None,
                "tasks_completed": self.stats.tasks_completed,
                "tasks_failed": self.stats.tasks_failed,
                "general_tasks": self.stats.general_tasks,
                "atlas_fixes": self.stats.atlas_fixes,
                "atlas_builds": self.stats.atlas_builds,
                "stop_reason": self.stats.stop_reason,
            },
            "results": [
                {
                    "task_id": r.task_id,
                    "mode": r.mode.value,
                    "success": r.success,
                    "summary": r.summary,
                    "output_path": str(r.output_path) if r.output_path else None,
                    "branch": r.branch,
                }
                for r in self._results
            ],
        }
        json_path.write_text(json.dumps(json_data, indent=2))

        return briefing_path

    def _format_briefing(self, include_details: bool = True) -> str:
        """Format the briefing as markdown."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        start_time = self.stats.started_at.strftime("%I:%M %p")
        end_time = self.stats.ended_at.strftime("%I:%M %p") if self.stats.ended_at else "In progress"

        content = f"""# Overnight Session Report - {date_str}

## Summary
- **Started:** {start_time}
- **Ended:** {end_time}
- **Tasks Completed:** {self.stats.tasks_completed}
- **Tasks Failed:** {self.stats.tasks_failed}
- **Stop Reason:** {self.stats.stop_reason or 'Normal completion'}

"""

        # ATLAS Fixes
        fixes = [r for r in self._results if r.mode == TaskMode.ATLAS_FIX]
        if fixes:
            content += f"## ATLAS Fixes ({len(fixes)})\n\n"
            for r in fixes:
                status = "✅" if r.success else "⚠️"
                content += f"### {status} {r.summary}\n"
                if r.branch:
                    content += f"**Branch:** `{r.branch}`\n"
                if include_details and r.details:
                    content += f"\n{r.details}\n"
                content += "\n---\n\n"

        # Products Built
        builds = [r for r in self._results if r.mode == TaskMode.ATLAS_BUILD]
        if builds:
            content += f"## Products Built ({len(builds)})\n\n"
            for r in builds:
                status = "✅" if r.success else "⚠️"
                content += f"### {status} {r.summary}\n"
                if r.output_path:
                    content += f"**Path:** `{r.output_path}`\n"
                if include_details and r.details:
                    content += f"\n{r.details}\n"
                content += "\n---\n\n"

        # General Tasks (Research & Drafts)
        general = [r for r in self._results if r.mode == TaskMode.GENERAL]
        if general:
            content += f"## Research & Drafts ({len(general)})\n\n"
            for r in general:
                status = "✅" if r.success else "⚠️"
                content += f"### {status} {r.summary}\n"
                if r.output_path:
                    content += f"**Full report:** `{r.output_path}`\n"
                if include_details and r.details:
                    content += f"\n**Key Findings:**\n{r.details}\n"
                content += "\n---\n\n"

        # Needs Review
        needs_review = [r for r in self._results if not r.success]
        if needs_review:
            content += "## ⚠️ Needs Your Review\n"
            for r in needs_review:
                content += f"- [ ] {r.summary}\n"

        return content

    def _format_slack_briefing(self) -> str:
        """Format a bulleted summary with key findings for Slack."""
        date_str = datetime.now().strftime("%Y-%m-%d")

        content = f":sunrise: *Overnight Report - {date_str}*\n"
        content += f"✅ {self.stats.tasks_completed} completed | ❌ {self.stats.tasks_failed} failed\n\n"

        # ATLAS Fixes
        fixes = [r for r in self._results if r.mode == TaskMode.ATLAS_FIX]
        if fixes:
            content += "*ATLAS Fixes:*\n"
            for r in fixes:
                status = "✅" if r.success else "❌"
                content += f"• {status} {r.summary}"
                if r.branch:
                    content += f" (`{r.branch}`)"
                content += "\n"
            content += "\n"

        # Products Built
        builds = [r for r in self._results if r.mode == TaskMode.ATLAS_BUILD]
        if builds:
            content += "*Products Built:*\n"
            for r in builds:
                status = "✅" if r.success else "❌"
                content += f"• {status} {r.summary}\n"
                if r.output_path:
                    content += f"   📁 `{r.output_path}`\n"
            content += "\n"

        # Research & Drafts - with key findings
        general = [r for r in self._results if r.mode == TaskMode.GENERAL]
        if general:
            content += "*Research & Drafts:*\n"
            for r in general:
                status = "✅" if r.success else "❌"
                task_name = r.summary.split(": ", 1)[-1] if ": " in r.summary else r.summary
                content += f"• {status} *{task_name}*\n"

                # Extract key points from details
                if r.success and r.details:
                    key_points = self._extract_key_points(r.details)
                    for point in key_points[:5]:  # Max 5 key points
                        content += f"   ◦ {point}\n"
            content += "\n"

        # Failed tasks needing review
        failed = [r for r in self._results if not r.success]
        if failed:
            content += "*⚠️ Needs Review:*\n"
            for r in failed:
                content += f"• {r.summary}\n"
            content += "\n"

        content += "_Full details in morning briefing_"

        return content

    def _extract_key_points(self, content: str) -> list[str]:
        """Extract key points/headings from content for summary."""
        import re

        key_points = []

        # Truncate at QC Feedback section to skip QC-related headers
        qc_match = re.search(r'^##\s+QC Feedback', content, re.MULTILINE | re.IGNORECASE)
        if qc_match:
            content = content[:qc_match.start()]

        # First, look for numbered H2 headers (## 1., ## 2., etc.) - these are usually the main items
        numbered_h2 = re.findall(r'^##\s+\d+\.\s*\**([^#\n]+?)\**\s*$', content, re.MULTILINE)
        for h in numbered_h2:
            cleaned = h.strip().strip('*').strip()
            if cleaned and len(cleaned) > 3 and len(cleaned) < 60:
                key_points.append(cleaned)

        # If not enough numbered H2, look at ### headers (specific items)
        if len(key_points) < 5:
            h3_headers = re.findall(r'^###\s+\**(?:\d+\.)?\s*([^#\n]+?)\**\s*$', content, re.MULTILINE)
            for h in h3_headers:
                cleaned = h.strip().strip('*').strip()
                if cleaned and len(cleaned) > 3 and len(cleaned) < 60:
                    skip_words = ['overview', 'summary', 'conclusion', 'introduction',
                                  'key features', 'setup requirements', 'security notes',
                                  'limitations', 'implementation']
                    if cleaned.lower() not in skip_words and not any(w in cleaned.lower() for w in skip_words):
                        key_points.append(cleaned)

        # If still not enough, add non-numbered H2 headers
        if len(key_points) < 3:
            h2_headers = re.findall(r'^##\s+\**([^#\n\d]+?)\**\s*$', content, re.MULTILINE)
            for h in h2_headers:
                cleaned = h.strip().strip('*').strip()
                if cleaned and len(cleaned) > 3 and len(cleaned) < 60:
                    skip_words = ['overview', 'summary', 'conclusion', 'introduction',
                                  'result', 'original request', 'qc feedback', 'implementation']
                    if cleaned.lower() not in skip_words and not any(w in cleaned.lower() for w in skip_words):
                        key_points.append(cleaned)

        # If still not enough, look for bold items at start of lines
        if len(key_points) < 3:
            bold_items = re.findall(r'^\**\s*[-•]?\s*\**([A-Z][^:\n]{3,50}?)(?:\**\s*[-:]|$)', content, re.MULTILINE)
            for b in bold_items:
                cleaned = b.strip().strip('*').strip()
                if cleaned and len(cleaned) > 3:
                    key_points.append(cleaned)

        # Deduplicate while preserving order
        seen = set()
        unique_points = []
        for p in key_points:
            p_lower = p.lower()
            if p_lower not in seen:
                seen.add(p_lower)
                unique_points.append(p)

        return unique_points

    # --- Queue Management Methods ---

    async def add_task(
        self,
        prompt: str,
        task_type: Optional[str] = None,
        priority: int = 0,
        metadata: Optional[dict] = None,
    ) -> str:
        """Add a task to the queue."""
        task_id = await self.queue.add_task(
            prompt=prompt,
            task_type=task_type or "general",
            priority=priority,
            metadata=metadata,
        )
        logger.info(f"Added task {task_id}: {prompt[:50]}...")
        return task_id

    async def get_queue_status(self) -> dict:
        """Get current queue statistics."""
        return await self.queue.get_queue_stats()

    async def list_pending_tasks(self, limit: int = 20) -> list[dict]:
        """List pending tasks."""
        return await self.queue.get_tasks_by_status(TaskStatus.PENDING, limit)
