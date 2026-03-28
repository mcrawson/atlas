"""ATLAS Multi-Agent System.

Specialized agents work together under ATLAS's coordination:
- Analyst (Business Intelligence): Market analysis, Business Briefs, Go/No-Go recommendations
- Sketch (Planning Agent): Planning, risk analysis, design
- Tinker (Building Agent): Building, implementation, coding
- Oracle (Verification Agent): Verification, QA, testing
- QC (Quality Control): Checks work against Business Brief at every stage
- Mockup (Preview Agent): Creates polished visual previews before building
- Finisher (Polish Agent): Completeness verification, polish, shipping readiness
- Launch (Deployment Agent): Publishing to app stores, registries, platforms
- Buzz (Communications Agent): Notifications, status updates
- Hype (Advertising Agent): Marketing, promotion, copywriting
- Cortex (Training Agent): Training data intelligence, readiness assessment
"""

from .base import BaseAgent, AgentStatus, AgentOutput
from .analyst import AnalystAgent, BusinessBrief
from .architect import ArchitectAgent
from .mason import MasonAgent
from .oracle import OracleAgent
from .qc import QCAgent, QCReport, QCVerdict, IssueSeverity
from .kickoff import KickoffAgent, KickoffPlan
from .mockup import MockupAgent, MockupOutput, MockupType
from .finisher import FinisherAgent
from .launch import LaunchAgent
from .buzz import Buzz, get_buzz
from .hype import HypeAgent, get_hype, init_hype
from .cortex import Cortex, get_cortex
from .sprint_meeting import SprintMeeting, SprintMeetingResult, AgentReview, ReviewVerdict, get_sprint_meeting
from .manager import AgentManager, WorkflowMode
from .director import DirectorAgent, BuildPhase, run_director
from .message_broker import MessageBroker, AgentMessage, MessageType, BuildStatus, get_broker
from .factory import AgentFactory, TeamComposition, CustomExpert
from .personalities import AgentPersonality, DebateStyle, CommunicationStyle, get_personality
from .memory import AgentMemory, get_memory

__all__ = [
    # Base
    "BaseAgent",
    "AgentStatus",
    "AgentOutput",
    # ATLAS 3.0 Agents
    "AnalystAgent",
    "BusinessBrief",
    "QCAgent",
    "QCReport",
    "QCVerdict",
    "IssueSeverity",
    "KickoffAgent",
    "KickoffPlan",
    "MockupAgent",
    "MockupOutput",
    "MockupType",
    # Core Agents
    "ArchitectAgent",
    "MasonAgent",
    "OracleAgent",
    "FinisherAgent",
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
    "WorkflowMode",
    # Layla-style Debate System
    "DirectorAgent",
    "BuildPhase",
    "run_director",
    "MessageBroker",
    "AgentMessage",
    "MessageType",
    "BuildStatus",
    "get_broker",
    "AgentFactory",
    "TeamComposition",
    "CustomExpert",
    "AgentPersonality",
    "DebateStyle",
    "CommunicationStyle",
    "get_personality",
    "AgentMemory",
    "get_memory",
]
