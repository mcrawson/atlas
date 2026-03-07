"""Windows toast notifications from WSL2 for ATLAS."""

import subprocess
import shutil
import logging
from typing import Optional

logger = logging.getLogger("atlas.notifications.windows")


class WindowsToast:
    """Send Windows toast notifications from WSL2."""

    def __init__(self, app_id: str = "ATLAS"):
        """Initialize Windows toast notifier.

        Args:
            app_id: Application ID for notifications
        """
        self.app_id = app_id
        self._powershell = shutil.which("powershell.exe")
        if not self._powershell:
            # Try common locations
            common_paths = [
                "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                "/mnt/c/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe",
            ]
            for path in common_paths:
                if shutil.which(path):
                    self._powershell = path
                    break

    def is_available(self) -> bool:
        """Check if Windows toast notifications are available.

        Returns:
            True if running in WSL2 with PowerShell access
        """
        return self._powershell is not None

    def send(
        self,
        title: str,
        message: str,
        icon: Optional[str] = None,
        sound: bool = True,
    ) -> bool:
        """Send a Windows toast notification.

        Args:
            title: Notification title
            message: Notification message
            icon: Optional icon path (Windows path)
            sound: Whether to play notification sound

        Returns:
            True if notification was sent
        """
        if not self.is_available():
            logger.warning("Windows toast not available - not in WSL2 or no PowerShell")
            return False

        # Escape quotes in title and message
        title = title.replace('"', '`"').replace("'", "`'")
        message = message.replace('"', '`"').replace("'", "`'")

        # Build PowerShell script
        ps_script = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
    <visual>
        <binding template="ToastText02">
            <text id="1">{title}</text>
            <text id="2">{message}</text>
        </binding>
    </visual>
    {"<audio src='ms-winsoundevent:Notification.Default'/>" if sound else "<audio silent='true'/>"}
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)

$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{self.app_id}")
$notifier.Show($toast)
'''

        try:
            result = subprocess.run(
                [self._powershell, "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.warning(f"Toast notification failed: {result.stderr}")
                return False

            return True

        except subprocess.TimeoutExpired:
            logger.warning("Toast notification timed out")
            return False
        except Exception as e:
            logger.error(f"Toast notification error: {e}")
            return False

    def send_progress(
        self,
        title: str,
        message: str,
        progress: float,
    ) -> bool:
        """Send a toast with progress bar (Windows 10+).

        Args:
            title: Notification title
            message: Status message
            progress: Progress value 0.0 to 1.0

        Returns:
            True if notification was sent
        """
        if not self.is_available():
            return False

        # Progress toast requires more complex XML
        title = title.replace('"', '`"').replace("'", "`'")
        message = message.replace('"', '`"').replace("'", "`'")

        ps_script = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{title}</text>
            <progress title="{message}" value="{progress}" valueStringOverride="{int(progress * 100)}%" status="Processing..."/>
        </binding>
    </visual>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)

$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{self.app_id}")
$notifier.Show($toast)
'''

        try:
            result = subprocess.run(
                [self._powershell, "-NoProfile", "-Command", ps_script],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Progress toast error: {e}")
            return False

    def send_with_buttons(
        self,
        title: str,
        message: str,
        buttons: list[tuple[str, str]],
    ) -> bool:
        """Send a toast with action buttons.

        Args:
            title: Notification title
            message: Notification message
            buttons: List of (label, argument) tuples

        Returns:
            True if notification was sent

        Note:
            Button actions require an app to handle them.
            This is primarily for visual purposes in ATLAS.
        """
        if not self.is_available():
            return False

        title = title.replace('"', '`"').replace("'", "`'")
        message = message.replace('"', '`"').replace("'", "`'")

        # Build button XML
        button_xml = ""
        for label, arg in buttons[:3]:  # Max 3 buttons
            label = label.replace('"', '`"')
            arg = arg.replace('"', '`"')
            button_xml += f'<action content="{label}" arguments="{arg}"/>'

        ps_script = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{title}</text>
            <text>{message}</text>
        </binding>
    </visual>
    <actions>
        {button_xml}
    </actions>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)

$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{self.app_id}")
$notifier.Show($toast)
'''

        try:
            result = subprocess.run(
                [self._powershell, "-NoProfile", "-Command", ps_script],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Button toast error: {e}")
            return False
