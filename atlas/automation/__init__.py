"""ATLAS Automation System.

Execute deployment commands, build scripts, and automated workflows.
Includes webhook handling and deployment pipelines.
"""

from .models import AutomationTask, CommandResult, TaskStatus
from .executor import CommandExecutor
from .manager import AutomationManager
from .webhooks import (
    WebhookEvent,
    WebhookResponse,
    WebhookSource,
    WebhookHandler,
    WebhookRouter,
    GitHubWebhookHandler,
    GitHubEvent,
    create_github_handler,
    get_webhook_router,
)
from .deploy import (
    Deployment,
    DeploymentResult,
    DeploymentStatus,
    DeploymentTarget,
    DeploymentPipeline,
    DeploymentManager,
    DeploymentStep,
    Environment,
    create_default_pipeline,
    create_blue_green_pipeline,
    get_deployment_manager,
)

__all__ = [
    # Existing
    "AutomationTask",
    "CommandResult",
    "TaskStatus",
    "CommandExecutor",
    "AutomationManager",
    # Webhooks
    "WebhookEvent",
    "WebhookResponse",
    "WebhookSource",
    "WebhookHandler",
    "WebhookRouter",
    "GitHubWebhookHandler",
    "GitHubEvent",
    "create_github_handler",
    "get_webhook_router",
    # Deployment
    "Deployment",
    "DeploymentResult",
    "DeploymentStatus",
    "DeploymentTarget",
    "DeploymentPipeline",
    "DeploymentManager",
    "DeploymentStep",
    "Environment",
    "create_default_pipeline",
    "create_blue_green_pipeline",
    "get_deployment_manager",
]
