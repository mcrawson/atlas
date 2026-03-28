"""
Overnight Autonomous Operator for ATLAS.

Routes and executes tasks overnight with appropriate safety guardrails.
Supports both ATLAS-specific tasks (fix bugs, build products) and
general tasks (research, drafts, reviews).
"""

from atlas.operator.overnight import OvernightOperator
from atlas.operator.router import TaskRouter
from atlas.operator.safety import SafetyLayer
from atlas.operator.config import OvernightConfig

__all__ = [
    "OvernightOperator",
    "TaskRouter",
    "SafetyLayer",
    "OvernightConfig",
]
