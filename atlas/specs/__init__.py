"""ATLAS Spec-Driven Development System.

Inspired by Kiro's spec-driven approach, this module provides:
- Requirements engineering with EARS format
- Design documentation
- Task breakdown and tracking
- Spec file generation and management
"""

from .generator import SpecGenerator
from .models import Spec, Requirement, DesignDoc, TaskList, Task
from .manager import SpecManager

__all__ = [
    "SpecGenerator",
    "Spec",
    "Requirement",
    "DesignDoc",
    "TaskList",
    "Task",
    "SpecManager",
]
