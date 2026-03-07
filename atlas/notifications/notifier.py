"""Notification system for ATLAS - desktop and sound notifications."""

import subprocess
import shutil
from enum import Enum
from pathlib import Path
from typing import Optional


class NotificationLevel(Enum):
    """Notification urgency levels."""
    INFO = "info"
    NORMAL = "normal"
    URGENT = "urgent"


class Notifier:
    """Cross-platform notification system."""

    def __init__(
        self,
        enable_sound: bool = True,
        enable_desktop: bool = True,
    ):
        """Initialize notifier.

        Args:
            enable_sound: Enable sound notifications for urgent messages
            enable_desktop: Enable desktop notifications
        """
        self.enable_sound = enable_sound
        self.enable_desktop = enable_desktop
        self._notify_send = shutil.which("notify-send")
        self._paplay = shutil.which("paplay")

    def _play_sound(self, sound_type: str = "complete") -> None:
        """Play a notification sound.

        Args:
            sound_type: Type of sound (complete, urgent, error)
        """
        if not self.enable_sound or not self._paplay:
            return

        # Try common Linux notification sounds
        sound_paths = {
            "complete": [
                "/usr/share/sounds/freedesktop/stereo/complete.oga",
                "/usr/share/sounds/gnome/default/alerts/drip.ogg",
            ],
            "urgent": [
                "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
                "/usr/share/sounds/gnome/default/alerts/bark.ogg",
            ],
            "error": [
                "/usr/share/sounds/freedesktop/stereo/dialog-error.oga",
                "/usr/share/sounds/gnome/default/alerts/glass.ogg",
            ],
        }

        for path in sound_paths.get(sound_type, []):
            if Path(path).exists():
                try:
                    subprocess.run(
                        [self._paplay, path],
                        capture_output=True,
                        timeout=5,
                    )
                    return
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    continue

    def _send_desktop_notification(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.NORMAL,
    ) -> bool:
        """Send a desktop notification.

        Args:
            title: Notification title
            message: Notification body
            level: Notification urgency level

        Returns:
            True if notification was sent
        """
        if not self.enable_desktop or not self._notify_send:
            return False

        urgency_map = {
            NotificationLevel.INFO: "low",
            NotificationLevel.NORMAL: "normal",
            NotificationLevel.URGENT: "critical",
        }

        try:
            subprocess.run(
                [
                    self._notify_send,
                    "--urgency", urgency_map.get(level, "normal"),
                    "--app-name", "ATLAS",
                    "--icon", "dialog-information",
                    title,
                    message,
                ],
                capture_output=True,
                timeout=5,
            )
            return True
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

    def notify(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.NORMAL,
    ) -> None:
        """Send a notification.

        Args:
            title: Notification title
            message: Notification body
            level: Notification urgency level
        """
        # Send desktop notification
        self._send_desktop_notification(title, message, level)

        # Play sound for urgent notifications
        if level == NotificationLevel.URGENT:
            self._play_sound("urgent")
        elif level == NotificationLevel.INFO:
            self._play_sound("complete")

    def task_completed(self, task_prompt: str, result_preview: Optional[str] = None) -> None:
        """Notify that a background task completed.

        Args:
            task_prompt: The original task prompt
            result_preview: Optional preview of the result
        """
        title = "ATLAS: Task Completed"
        message = task_prompt[:100] + ("..." if len(task_prompt) > 100 else "")

        if result_preview:
            message += f"\n\n{result_preview[:200]}"

        self.notify(title, message, NotificationLevel.INFO)

    def task_failed(self, task_prompt: str, error: str) -> None:
        """Notify that a background task failed.

        Args:
            task_prompt: The original task prompt
            error: Error message
        """
        title = "ATLAS: Task Failed"
        message = f"{task_prompt[:50]}...\n\nError: {error[:100]}"

        self.notify(title, message, NotificationLevel.URGENT)
        self._play_sound("error")

    def urgent_message(self, message: str) -> None:
        """Send an urgent notification.

        Args:
            message: The urgent message
        """
        self.notify("ATLAS: Urgent", message, NotificationLevel.URGENT)

    def briefing_ready(self) -> None:
        """Notify that a briefing is ready."""
        self.notify(
            "ATLAS: Briefing Ready",
            "Your session briefing is ready, sir.",
            NotificationLevel.NORMAL,
        )

    def is_available(self) -> bool:
        """Check if notifications are available.

        Returns:
            True if at least one notification method is available
        """
        return bool(self._notify_send) or bool(self._paplay)
