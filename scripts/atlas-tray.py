#!/usr/bin/env python3
"""ATLAS System Tray - Windows tray icon for ATLAS status and control.

This script runs on the Windows side and communicates with ATLAS in WSL2.
It provides a system tray icon with status and menu options.

Requirements:
    pip install pystray pillow

Usage:
    python atlas-tray.py

Installation:
    1. Install Python for Windows
    2. pip install pystray pillow
    3. Create a shortcut in Windows Startup folder pointing to this script
"""

import subprocess
import socket
import threading
import time
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("Please install required packages: pip install pystray pillow")
    exit(1)


class ATLASTray:
    """Windows system tray icon for ATLAS."""

    # Configuration
    WSL_DISTRO = "Ubuntu"
    ATLAS_PATH = "~/ai-workspace/atlas/scripts/atlas"
    STATUS_PORT = 19765  # Port for status communication

    def __init__(self):
        """Initialize the tray application."""
        self.icon = None
        self.status = "idle"
        self.running = True

    def create_icon_image(self, status: str = "idle") -> Image:
        """Create the tray icon image.

        Args:
            status: Current status (idle, active, alert)

        Returns:
            PIL Image for the icon
        """
        # Create a 64x64 image
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Color based on status
        colors = {
            "idle": "#4a90d9",      # Blue
            "active": "#4adb4a",    # Green
            "alert": "#db4a4a",     # Red
            "processing": "#dba84a", # Orange
        }
        color = colors.get(status, colors["idle"])

        # Draw a stylized "A" for ATLAS
        # Outer circle
        draw.ellipse([4, 4, size-4, size-4], outline=color, width=3)

        # Inner "A" shape
        center = size // 2
        draw.polygon([
            (center, 12),           # Top
            (12, size - 12),        # Bottom left
            (size - 12, size - 12), # Bottom right
        ], outline=color, width=2)

        # Crossbar of the A
        draw.line([(20, size - 24), (size - 20, size - 24)], fill=color, width=2)

        return image

    def open_atlas(self):
        """Open ATLAS in Windows Terminal."""
        try:
            cmd = f'wt.exe -w ATLAS wsl.exe -d {self.WSL_DISTRO} {self.ATLAS_PATH}'
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            print(f"Failed to open ATLAS: {e}")

    def get_status(self):
        """Get ATLAS daemon status."""
        try:
            result = subprocess.run(
                ['wsl.exe', '-d', self.WSL_DISTRO, '--',
                 'systemctl', '--user', 'is-active', 'atlas'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() == "active"
        except Exception:
            return False

    def start_daemon(self):
        """Start the ATLAS daemon."""
        try:
            subprocess.run(
                ['wsl.exe', '-d', self.WSL_DISTRO, '--',
                 'systemctl', '--user', 'start', 'atlas'],
                timeout=10,
            )
        except Exception as e:
            print(f"Failed to start daemon: {e}")

    def stop_daemon(self):
        """Stop the ATLAS daemon."""
        try:
            subprocess.run(
                ['wsl.exe', '-d', self.WSL_DISTRO, '--',
                 'systemctl', '--user', 'stop', 'atlas'],
                timeout=10,
            )
        except Exception as e:
            print(f"Failed to stop daemon: {e}")

    def show_briefing(self):
        """Show the ATLAS briefing."""
        try:
            cmd = f'wt.exe -w ATLAS wsl.exe -d {self.WSL_DISTRO} {self.ATLAS_PATH} briefing'
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            print(f"Failed to show briefing: {e}")

    def on_quit(self, icon, item):
        """Handle quit menu item."""
        self.running = False
        icon.stop()

    def on_open(self, icon, item):
        """Handle open menu item."""
        self.open_atlas()

    def on_start_daemon(self, icon, item):
        """Handle start daemon menu item."""
        self.start_daemon()
        self.update_icon_status()

    def on_stop_daemon(self, icon, item):
        """Handle stop daemon menu item."""
        self.stop_daemon()
        self.update_icon_status()

    def on_briefing(self, icon, item):
        """Handle briefing menu item."""
        self.show_briefing()

    def create_menu(self):
        """Create the tray menu."""
        daemon_running = self.get_status()

        return pystray.Menu(
            pystray.MenuItem("Open ATLAS", self.on_open, default=True),
            pystray.MenuItem("Show Briefing", self.on_briefing),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Start Daemon" if not daemon_running else "Stop Daemon",
                self.on_start_daemon if not daemon_running else self.on_stop_daemon
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.on_quit),
        )

    def update_icon_status(self):
        """Update the icon based on daemon status."""
        if self.icon:
            daemon_running = self.get_status()
            self.status = "active" if daemon_running else "idle"
            self.icon.icon = self.create_icon_image(self.status)
            self.icon.menu = self.create_menu()

    def status_monitor(self):
        """Background thread to monitor status."""
        while self.running:
            try:
                self.update_icon_status()
            except Exception:
                pass
            time.sleep(30)  # Check every 30 seconds

    def run(self):
        """Run the tray application."""
        # Create icon
        self.icon = pystray.Icon(
            "ATLAS",
            self.create_icon_image(),
            "ATLAS - Automated Thinking, Learning & Advisory System",
            menu=self.create_menu(),
        )

        # Start status monitor thread
        monitor_thread = threading.Thread(target=self.status_monitor, daemon=True)
        monitor_thread.start()

        # Run the icon
        self.icon.run()


def main():
    """Entry point."""
    print("Starting ATLAS System Tray...")
    tray = ATLASTray()
    tray.run()


if __name__ == "__main__":
    main()
