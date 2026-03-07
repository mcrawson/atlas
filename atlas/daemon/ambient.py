"""Ambient daemon mode for ATLAS - continuous monitoring and awareness."""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable, List

from ..monitoring import MonitorManager, SystemMonitor, GitMonitor, WebMonitor, Alert, AlertSeverity
from ..notifications import Notifier
from ..tasks import TaskQueue, TaskWorker

logger = logging.getLogger("atlas.daemon.ambient")


class AmbientDaemon:
    """Enhanced daemon with ambient awareness and proactive monitoring."""

    def __init__(
        self,
        config: dict,
        task_processor: Callable = None,
        on_alert: Callable = None,
    ):
        """Initialize ambient daemon.

        Args:
            config: Configuration dictionary
            task_processor: Async function to process tasks
            on_alert: Callback for alerts (async function taking Alert)
        """
        self.config = config
        self.task_processor = task_processor
        self.on_alert = on_alert

        # Initialize components
        self.queue = TaskQueue()
        self.notifier = Notifier(
            enable_sound=config.get("notifications", {}).get("sound_urgent", True),
            enable_desktop=config.get("notifications", {}).get("desktop", True),
        )

        # Initialize monitor manager
        self.monitor_manager = MonitorManager()
        self._setup_monitors()

        # State tracking
        self._running = False
        self._last_monitor_check = None
        self._monitor_interval = config.get("monitoring", {}).get("interval", 300)

    def _setup_monitors(self):
        """Setup monitors based on configuration."""
        monitoring_config = self.config.get("monitoring", {})

        if not monitoring_config.get("enabled", True):
            return

        # System monitor
        system_config = monitoring_config.get("system", {})
        if system_config.get("enabled", True):
            self.monitor_manager.register(SystemMonitor(
                cpu_threshold=system_config.get("cpu_threshold", 80),
                memory_threshold=system_config.get("memory_threshold", 85),
                disk_threshold=system_config.get("disk_threshold", 90),
            ))

        # Git monitor
        git_config = monitoring_config.get("git", {})
        if git_config.get("enabled", True):
            repos = git_config.get("repos", [])
            if repos:
                self.monitor_manager.register(GitMonitor(
                    repos=repos,
                    check_uncommitted=git_config.get("check_uncommitted", True),
                    check_unpushed=git_config.get("check_unpushed", True),
                ))

        # Web monitor
        web_config = monitoring_config.get("web", {})
        if web_config.get("enabled", False):
            urls = web_config.get("urls", [])
            if urls:
                self.monitor_manager.register(WebMonitor(urls=urls))

    async def _check_monitors(self) -> List[Alert]:
        """Run all monitors and handle alerts.

        Returns:
            List of alerts generated
        """
        alerts = await self.monitor_manager.check_all()

        for alert in alerts:
            await self._handle_alert(alert)

        return alerts

    async def _handle_alert(self, alert: Alert):
        """Handle an alert - notify and optionally callback.

        Args:
            alert: The alert to handle
        """
        # Format message in butler style
        message = alert.format_butler_message()

        # Send notification based on severity
        if alert.severity == AlertSeverity.URGENT:
            self.notifier.urgent_message(message)
        elif alert.severity == AlertSeverity.WARNING:
            self.notifier.notify(
                "ATLAS Alert",
                message,
            )
        # INFO alerts are logged but not notified

        # Log
        logger.info(f"Alert [{alert.severity.value}] {alert.message}")

        # Callback if provided
        if self.on_alert:
            try:
                if asyncio.iscoroutinefunction(self.on_alert):
                    await self.on_alert(alert)
                else:
                    self.on_alert(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    async def _process_queue(self):
        """Process one task from the queue if available."""
        if not self.task_processor:
            return

        task = await self.queue.get_next_task()
        if not task:
            return

        logger.info(f"Processing task {task['id']}: {task['prompt'][:50]}...")

        from ..tasks import TaskStatus

        # Mark as running
        await self.queue.update_task_status(task["id"], TaskStatus.RUNNING)

        try:
            result, model_used = await self.task_processor(
                task["prompt"],
                task.get("task_type", "general")
            )

            await self.queue.update_task_status(
                task["id"],
                TaskStatus.COMPLETED,
                result=result,
                model_used=model_used,
            )

            self.notifier.task_completed(task["prompt"], result[:200] if result else None)
            logger.info(f"Task {task['id']} completed via {model_used}")

        except Exception as e:
            await self.queue.update_task_status(
                task["id"],
                TaskStatus.FAILED,
                error=str(e),
            )
            self.notifier.task_failed(task["prompt"], str(e))
            logger.error(f"Task {task['id']} failed: {e}")

    async def run(self):
        """Run the ambient daemon loop."""
        self._running = True
        logger.info("ATLAS Ambient Daemon starting...")

        # Initial monitor check
        await self._check_monitors()
        self._last_monitor_check = datetime.now()

        while self._running:
            try:
                # Check if it's time for monitors
                if self._last_monitor_check:
                    elapsed = (datetime.now() - self._last_monitor_check).total_seconds()
                    if elapsed >= self._monitor_interval:
                        await self._check_monitors()
                        self._last_monitor_check = datetime.now()

                # Process queue
                await self._process_queue()

                # Brief sleep
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                logger.info("Daemon cancelled")
                break
            except Exception as e:
                logger.error(f"Daemon error: {e}")
                await asyncio.sleep(30)

        logger.info("ATLAS Ambient Daemon stopped")

    def stop(self):
        """Signal the daemon to stop."""
        self._running = False
        logger.info("Daemon stop requested")

    def get_status(self) -> dict:
        """Get daemon status.

        Returns:
            Status dictionary
        """
        return {
            "running": self._running,
            "monitors": self.monitor_manager.get_status(),
            "last_monitor_check": (
                self._last_monitor_check.isoformat()
                if self._last_monitor_check else None
            ),
            "urgent_alerts": len(self.monitor_manager.get_urgent_alerts()),
        }
