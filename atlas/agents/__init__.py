"""ATLAS Multi-Agent System.

Specialized agents work together under ATLAS's coordination:
- Sketch (Planning Agent): Planning, risk analysis, design
- Tinker (Building Agent): Building, implementation, coding
- Oracle (Verification Agent): Verification, QA, testing
- Launch (Deployment Agent): Publishing to app stores, registries, platforms
- Buzz (Communications Agent): Notifications, status updates
- Hype (Advertising Agent): Marketing, promotion, copywriting
- Cortex (Training Agent): Training data intelligence, readiness assessment
"""

from .base import BaseAgent, AgentStatus, AgentOutput
from .architect import ArchitectAgent
from .mason import MasonAgent
from .oracle import OracleAgent
from .launch import LaunchAgent
from .buzz import Buzz, get_buzz
from .hype import HypeAgent, get_hype, init_hype
from .cortex import Cortex, get_cortex
from .sprint_meeting import SprintMeeting, SprintMeetingResult, AgentReview, ReviewVerdict, get_sprint_meeting
from .manager import AgentManager

__all__ = [
    "BaseAgent",
    "AgentStatus",
    "AgentOutput",
    "ArchitectAgent",
    "MasonAgent",
    "OracleAgent",
    "LaunchAgent",
    "Buzz",
    "get_buzz",
    "HypeAgent",
    "get_hype",
    "init_hype",
    "Cortex",
    "get_cortex",
    "SprintMeeting",
    "SprintMeetingResult",
    "AgentReview",
    "ReviewVerdict",
    "get_sprint_meeting",
    "AgentManager",
]
