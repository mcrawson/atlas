"""External integrations for ATLAS - smart home, calendar, email, Slack, GitHub."""

from .home_assistant import HomeAssistantClient
from .smart_home import SmartHomeController
from .google_auth import GoogleAuth, setup_google_auth
from .calendar import CalendarClient
from .email import EmailClient

# Slack requires httpx - import conditionally
try:
    from .slack import (
        SlackClient,
        SlackMessage,
        SlackNotifier,
        SlashCommand,
        get_slack_client,
    )
    _SLACK_AVAILABLE = True
except ImportError:
    _SLACK_AVAILABLE = False
    SlackClient = None
    SlackMessage = None
    SlackNotifier = None
    SlashCommand = None
    get_slack_client = None

# GitHub integration requires httpx - import conditionally
try:
    from .github import (
        Transporter,
        get_transporter,
        TransporterConfig,
        GitHubAPI,
        get_github_api,
    )
    _GITHUB_AVAILABLE = True
except ImportError:
    _GITHUB_AVAILABLE = False
    Transporter = None
    get_transporter = None
    TransporterConfig = None
    GitHubAPI = None
    get_github_api = None

__all__ = [
    "HomeAssistantClient",
    "SmartHomeController",
    "GoogleAuth",
    "setup_google_auth",
    "CalendarClient",
    "EmailClient",
    # Slack (requires httpx)
    "SlackClient",
    "SlackMessage",
    "SlackNotifier",
    "SlashCommand",
    "get_slack_client",
    # GitHub (requires httpx)
    "Transporter",
    "get_transporter",
    "TransporterConfig",
    "GitHubAPI",
    "get_github_api",
]
