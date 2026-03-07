"""System monitoring for ATLAS - CPU, memory, disk, and network alerts."""

import shutil
import subprocess
from pathlib import Path
from typing import List
import logging

from .monitor import Monitor, Alert, AlertSeverity

logger = logging.getLogger("atlas.monitoring.system")


class SystemMonitor(Monitor):
    """Monitor system resources and services."""

    name = "system"
    check_interval = 300  # 5 minutes

    def __init__(
        self,
        cpu_threshold: int = 80,
        memory_threshold: int = 85,
        disk_threshold: int = 90,
        **kwargs
    ):
        """Initialize system monitor.

        Args:
            cpu_threshold: CPU usage percentage to alert
            memory_threshold: Memory usage percentage to alert
            disk_threshold: Disk usage percentage to alert
        """
        super().__init__(**kwargs)
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold

    async def check(self) -> List[Alert]:
        """Check system resources.

        Returns:
            List of alerts for any issues
        """
        alerts = []

        # Check disk usage
        disk_alert = self._check_disk()
        if disk_alert:
            alerts.append(disk_alert)

        # Check memory
        memory_alert = self._check_memory()
        if memory_alert:
            alerts.append(memory_alert)

        # Check CPU
        cpu_alert = self._check_cpu()
        if cpu_alert:
            alerts.append(cpu_alert)

        # Check Ollama service
        ollama_alert = self._check_ollama()
        if ollama_alert:
            alerts.append(ollama_alert)

        return alerts

    def _check_disk(self) -> Alert | None:
        """Check disk usage.

        Returns:
            Alert if disk is low, else None
        """
        try:
            total, used, free = shutil.disk_usage("/")
            percent_used = (used / total) * 100

            if percent_used >= 95:
                return Alert(
                    monitor_name=self.name,
                    severity=AlertSeverity.URGENT,
                    message=f"your disk is {percent_used:.1f}% full. Only {free / (1024**3):.1f}GB remaining.",
                    action_suggestion="Shall I investigate what's using the most space?",
                    data={"disk_percent": percent_used, "free_gb": free / (1024**3)},
                )
            elif percent_used >= self.disk_threshold:
                return Alert(
                    monitor_name=self.name,
                    severity=AlertSeverity.WARNING,
                    message=f"your disk is {percent_used:.1f}% full.",
                    action_suggestion="You may wish to free up some space soon, sir.",
                    data={"disk_percent": percent_used, "free_gb": free / (1024**3)},
                )
        except Exception as e:
            logger.error(f"Failed to check disk: {e}")

        return None

    def _check_memory(self) -> Alert | None:
        """Check memory usage.

        Returns:
            Alert if memory is low, else None
        """
        try:
            with open("/proc/meminfo") as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        value = int(parts[1])
                        meminfo[key] = value

            total = meminfo.get("MemTotal", 0)
            available = meminfo.get("MemAvailable", 0)

            if total > 0:
                percent_used = ((total - available) / total) * 100

                if percent_used >= 95:
                    return Alert(
                        monitor_name=self.name,
                        severity=AlertSeverity.URGENT,
                        message=f"memory usage is critically high at {percent_used:.1f}%.",
                        action_suggestion="Consider closing some applications, sir.",
                        data={"memory_percent": percent_used},
                    )
                elif percent_used >= self.memory_threshold:
                    return Alert(
                        monitor_name=self.name,
                        severity=AlertSeverity.WARNING,
                        message=f"memory usage is at {percent_used:.1f}%.",
                        data={"memory_percent": percent_used},
                    )
        except Exception as e:
            logger.error(f"Failed to check memory: {e}")

        return None

    def _check_cpu(self) -> Alert | None:
        """Check CPU usage (using load average).

        Returns:
            Alert if CPU is high, else None
        """
        try:
            with open("/proc/loadavg") as f:
                load_1, load_5, load_15, *_ = f.read().split()
                load_1 = float(load_1)
                load_5 = float(load_5)

            # Get number of CPUs
            try:
                import os
                num_cpus = os.cpu_count() or 1
            except Exception:
                num_cpus = 1

            # Load average > num_cpus means overloaded
            load_percent = (load_5 / num_cpus) * 100

            if load_percent >= 150:  # Significantly overloaded
                return Alert(
                    monitor_name=self.name,
                    severity=AlertSeverity.URGENT,
                    message=f"the system is under heavy load (load average: {load_5:.2f}, {num_cpus} CPUs).",
                    action_suggestion="Some processes may be consuming excessive resources, sir.",
                    data={"load_average": load_5, "cpus": num_cpus},
                )
            elif load_percent >= 100:  # At capacity
                return Alert(
                    monitor_name=self.name,
                    severity=AlertSeverity.WARNING,
                    message=f"the system is at full capacity (load average: {load_5:.2f}).",
                    data={"load_average": load_5, "cpus": num_cpus},
                )
        except Exception as e:
            logger.error(f"Failed to check CPU: {e}")

        return None

    def _check_ollama(self) -> Alert | None:
        """Check if Ollama is running.

        Returns:
            Alert if Ollama is not running (info level)
        """
        try:
            result = subprocess.run(
                ["pgrep", "-f", "ollama"],
                capture_output=True,
                timeout=5,
            )

            if result.returncode != 0:
                return Alert(
                    monitor_name=self.name,
                    severity=AlertSeverity.INFO,
                    message="Ollama is not currently running.",
                    action_suggestion="Local AI capabilities will be limited. Shall I start it?",
                    data={"service": "ollama", "status": "stopped"},
                )
        except Exception as e:
            logger.debug(f"Failed to check Ollama: {e}")

        return None

    def get_system_summary(self) -> dict:
        """Get a summary of system status.

        Returns:
            Dictionary with system metrics
        """
        summary = {}

        # Disk
        try:
            total, used, free = shutil.disk_usage("/")
            summary["disk"] = {
                "total_gb": round(total / (1024**3), 1),
                "used_gb": round(used / (1024**3), 1),
                "free_gb": round(free / (1024**3), 1),
                "percent_used": round((used / total) * 100, 1),
            }
        except Exception:
            summary["disk"] = {"error": "unavailable"}

        # Memory
        try:
            with open("/proc/meminfo") as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        value = int(parts[1])
                        meminfo[key] = value

            total = meminfo.get("MemTotal", 0) / 1024 / 1024
            available = meminfo.get("MemAvailable", 0) / 1024 / 1024
            summary["memory"] = {
                "total_gb": round(total, 1),
                "available_gb": round(available, 1),
                "percent_used": round((total - available) / total * 100, 1) if total > 0 else 0,
            }
        except Exception:
            summary["memory"] = {"error": "unavailable"}

        # Load
        try:
            with open("/proc/loadavg") as f:
                parts = f.read().split()
                summary["load"] = {
                    "1min": float(parts[0]),
                    "5min": float(parts[1]),
                    "15min": float(parts[2]),
                }
        except Exception:
            summary["load"] = {"error": "unavailable"}

        return summary
