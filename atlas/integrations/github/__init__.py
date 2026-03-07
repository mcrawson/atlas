"""
ATLAS GitHub Integration - Transporter Module.

Provides bidirectional sync between ATLAS tasks and GitHub Issues,
inspired by Jason Statham from hiro-labs (moving things fast and efficiently).

Features:
- Sync ATLAS tasks to GitHub Issues
- Sync GitHub Issues to ATLAS tasks
- Post agent outputs as issue comments
- Webhook handling for real-time sync

Usage:
    from atlas.integrations.github import get_transporter, TransporterConfig

    # Get singleton transporter instance
    transporter = get_transporter()

    # Sync a task to GitHub
    issue_url = await transporter.sync_task_to_github(task_id=1, repo="owner/repo")

    # Link existing task to issue
    await transporter.link_task_to_issue(task_id=1, repo="owner/repo", issue_number=42)

Environment variables:
    ATLAS_GITHUB_TOKEN - GitHub personal access token
    ATLAS_GITHUB_DEFAULT_REPO - Default repository (owner/repo)
    ATLAS_GITHUB_WEBHOOK_SECRET - Webhook signature secret
"""

from .models import (
    TransporterConfig,
    SyncState,
    SyncMapping,
    SyncStatus,
    GitHubIssueData,
    GitHubCommentData,
)
from .api import GitHubAPI, get_github_api
from .transporter import Transporter, get_transporter
from .handlers import GitHubSyncHandler, get_github_sync_handler

__all__ = [
    # Main transporter
    "Transporter",
    "get_transporter",
    # Configuration
    "TransporterConfig",
    # Data models
    "SyncState",
    "SyncMapping",
    "SyncStatus",
    "GitHubIssueData",
    "GitHubCommentData",
    # API client
    "GitHubAPI",
    "get_github_api",
    # Webhook handlers
    "GitHubSyncHandler",
    "get_github_sync_handler",
]
