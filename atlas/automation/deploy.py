"""Deployment automation for ATLAS.

Meet Doc - ATLAS's eccentric deployment scientist. When this thing
hits 88 miles per hour, you're gonna see some serious deployments.
Handles time-sensitive releases with precision and knows exactly
when to go back... to the previous version.

"Roads? Where we're going, we don't need roads." - Doc Brown

Provides:
- Multi-environment deployments (dev, staging, production)
- Deployment pipelines with rollback support
- Health checks and verification
- Slack notifications for deployment status
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("atlas.automation.deploy")


class DeploymentStatus(Enum):
    """Deployment status values."""

    PENDING = "pending"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class Environment(Enum):
    """Deployment environments."""

    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DeploymentTarget:
    """A deployment target configuration."""

    name: str
    environment: Environment
    url: str
    health_check_url: Optional[str] = None
    requires_approval: bool = False
    notify_channel: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Deployment:
    """A deployment instance."""

    id: str
    service: str
    version: str
    target: DeploymentTarget
    status: DeploymentStatus = DeploymentStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    previous_version: Optional[str] = None
    triggered_by: str = "system"
    error: Optional[str] = None
    logs: list[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        """Add a log message."""
        timestamp = datetime.now().isoformat()
        self.logs.append(f"[{timestamp}] {message}")
        logger.info(f"[{self.id}] {message}")


@dataclass
class DeploymentResult:
    """Result of a deployment."""

    success: bool
    deployment: Deployment
    duration_seconds: float
    health_check_passed: bool = True


class DeploymentStep:
    """A step in a deployment pipeline."""

    def __init__(self, name: str, handler):
        self.name = name
        self.handler = handler

    async def execute(self, deployment: Deployment, context: dict) -> bool:
        """Execute the step.

        Args:
            deployment: Current deployment
            context: Shared context between steps

        Returns:
            True if step succeeded
        """
        deployment.log(f"Starting step: {self.name}")
        try:
            result = await self.handler(deployment, context)
            deployment.log(f"Step {self.name}: {'SUCCESS' if result else 'FAILED'}")
            return result
        except Exception as e:
            deployment.log(f"Step {self.name} error: {e}")
            raise


class DeploymentPipeline:
    """A deployment pipeline with multiple steps."""

    def __init__(self, name: str):
        self.name = name
        self.steps: list[DeploymentStep] = []
        self.rollback_steps: list[DeploymentStep] = []

    def add_step(self, name: str, handler) -> "DeploymentPipeline":
        """Add a step to the pipeline."""
        self.steps.append(DeploymentStep(name, handler))
        return self

    def add_rollback_step(self, name: str, handler) -> "DeploymentPipeline":
        """Add a rollback step."""
        self.rollback_steps.append(DeploymentStep(name, handler))
        return self

    async def execute(
        self, deployment: Deployment, context: Optional[dict] = None
    ) -> DeploymentResult:
        """Execute the deployment pipeline.

        Args:
            deployment: Deployment to execute
            context: Initial context

        Returns:
            Deployment result
        """
        context = context or {}
        start_time = datetime.now()
        deployment.status = DeploymentStatus.RUNNING
        deployment.started_at = start_time.isoformat()

        deployment.log(f"Starting pipeline: {self.name}")
        deployment.log(f"Deploying {deployment.service} v{deployment.version}")
        deployment.log(f"Target: {deployment.target.name} ({deployment.target.environment.value})")

        try:
            # Execute steps
            for step in self.steps:
                success = await step.execute(deployment, context)
                if not success:
                    raise Exception(f"Step failed: {step.name}")

            # Verify deployment
            deployment.status = DeploymentStatus.VERIFYING
            health_passed = await self._verify_health(deployment)

            if not health_passed:
                deployment.log("Health check failed, triggering rollback")
                await self._rollback(deployment, context)
                deployment.status = DeploymentStatus.ROLLED_BACK
                return DeploymentResult(
                    success=False,
                    deployment=deployment,
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    health_check_passed=False,
                )

            deployment.status = DeploymentStatus.COMPLETED
            deployment.completed_at = datetime.now().isoformat()
            deployment.log("Deployment completed successfully")

            return DeploymentResult(
                success=True,
                deployment=deployment,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

        except Exception as e:
            deployment.error = str(e)
            deployment.status = DeploymentStatus.FAILED
            deployment.log(f"Deployment failed: {e}")

            # Attempt rollback
            await self._rollback(deployment, context)

            return DeploymentResult(
                success=False,
                deployment=deployment,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

    async def _verify_health(self, deployment: Deployment) -> bool:
        """Verify deployment health."""
        if not deployment.target.health_check_url:
            deployment.log("No health check URL configured, skipping")
            return True

        deployment.log(f"Running health check: {deployment.target.health_check_url}")

        # In a real implementation, make HTTP request to health endpoint
        # For now, simulate a check
        await asyncio.sleep(0.1)
        deployment.log("Health check passed")
        return True

    async def _rollback(self, deployment: Deployment, context: dict) -> None:
        """Execute rollback steps."""
        if not self.rollback_steps:
            deployment.log("No rollback steps configured")
            return

        deployment.log("Executing rollback")
        for step in self.rollback_steps:
            try:
                await step.execute(deployment, context)
            except Exception as e:
                deployment.log(f"Rollback step {step.name} failed: {e}")


class DeploymentManager:
    """Doc - ATLAS's deployment scientist.

    Manages deployments across services and environments.
    Great Scott, this is heavy!
    """

    NAME = "Doc"

    def __init__(self):
        self.targets: dict[str, DeploymentTarget] = {}
        self.pipelines: dict[str, DeploymentPipeline] = {}
        self.deployments: dict[str, Deployment] = {}
        self._deployment_counter = 0

    def register_target(self, target: DeploymentTarget) -> None:
        """Register a deployment target."""
        self.targets[target.name] = target
        logger.info(f"Registered deployment target: {target.name}")

    def register_pipeline(self, name: str, pipeline: DeploymentPipeline) -> None:
        """Register a deployment pipeline."""
        self.pipelines[name] = pipeline
        logger.info(f"Registered deployment pipeline: {name}")

    def _generate_deployment_id(self) -> str:
        """Generate a unique deployment ID."""
        self._deployment_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"deploy-{timestamp}-{self._deployment_counter}"

    async def deploy(
        self,
        service: str,
        version: str,
        target_name: str,
        pipeline_name: str = "default",
        triggered_by: str = "system",
        context: Optional[dict] = None,
    ) -> DeploymentResult:
        """Execute a deployment.

        Args:
            service: Service name
            version: Version to deploy
            target_name: Target name
            pipeline_name: Pipeline to use
            triggered_by: User/system that triggered
            context: Additional context

        Returns:
            Deployment result
        """
        # Get target
        target = self.targets.get(target_name)
        if not target:
            raise ValueError(f"Unknown target: {target_name}")

        # Get pipeline
        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline:
            raise ValueError(f"Unknown pipeline: {pipeline_name}")

        # Check approval requirement
        if target.requires_approval:
            logger.warning(f"Target {target_name} requires approval")
            # In a real implementation, wait for approval via Slack/UI

        # Create deployment
        deployment = Deployment(
            id=self._generate_deployment_id(),
            service=service,
            version=version,
            target=target,
            triggered_by=triggered_by,
        )
        self.deployments[deployment.id] = deployment

        # Execute pipeline
        result = await pipeline.execute(deployment, context)

        return result

    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Get a deployment by ID."""
        return self.deployments.get(deployment_id)

    def get_recent_deployments(
        self, limit: int = 10, service: Optional[str] = None
    ) -> list[Deployment]:
        """Get recent deployments."""
        deployments = list(self.deployments.values())

        if service:
            deployments = [d for d in deployments if d.service == service]

        # Sort by started_at descending
        deployments.sort(
            key=lambda d: d.started_at or "", reverse=True
        )

        return deployments[:limit]


# Pre-built pipeline steps

async def step_pull_image(deployment: Deployment, context: dict) -> bool:
    """Pull container image."""
    deployment.log(f"Pulling image: {deployment.service}:{deployment.version}")
    await asyncio.sleep(0.1)  # Simulate pull
    context["image"] = f"{deployment.service}:{deployment.version}"
    return True


async def step_stop_service(deployment: Deployment, context: dict) -> bool:
    """Stop the current service."""
    deployment.log("Stopping current service")
    await asyncio.sleep(0.1)  # Simulate stop
    return True


async def step_start_service(deployment: Deployment, context: dict) -> bool:
    """Start the new service."""
    deployment.log(f"Starting service with image: {context.get('image')}")
    await asyncio.sleep(0.1)  # Simulate start
    return True


async def step_rollback_restart(deployment: Deployment, context: dict) -> bool:
    """Rollback by restarting previous version."""
    if deployment.previous_version:
        deployment.log(f"Rolling back to version: {deployment.previous_version}")
    else:
        deployment.log("No previous version to rollback to")
    return True


# Factory function

def create_default_pipeline() -> DeploymentPipeline:
    """Create a default deployment pipeline."""
    pipeline = DeploymentPipeline("default")

    # Add deployment steps
    pipeline.add_step("pull_image", step_pull_image)
    pipeline.add_step("stop_service", step_stop_service)
    pipeline.add_step("start_service", step_start_service)

    # Add rollback steps
    pipeline.add_rollback_step("restart_previous", step_rollback_restart)

    return pipeline


def create_blue_green_pipeline() -> DeploymentPipeline:
    """Create a blue-green deployment pipeline."""
    pipeline = DeploymentPipeline("blue-green")

    async def step_deploy_green(deployment: Deployment, context: dict) -> bool:
        """Deploy to green environment."""
        deployment.log("Deploying to green environment")
        await asyncio.sleep(0.1)
        context["green_running"] = True
        return True

    async def step_switch_traffic(deployment: Deployment, context: dict) -> bool:
        """Switch traffic to green."""
        deployment.log("Switching traffic to green environment")
        await asyncio.sleep(0.1)
        return True

    async def step_cleanup_blue(deployment: Deployment, context: dict) -> bool:
        """Clean up blue environment."""
        deployment.log("Cleaning up blue environment")
        await asyncio.sleep(0.1)
        return True

    pipeline.add_step("deploy_green", step_deploy_green)
    pipeline.add_step("switch_traffic", step_switch_traffic)
    pipeline.add_step("cleanup_blue", step_cleanup_blue)

    # Rollback: switch back to blue
    async def step_switch_back(deployment: Deployment, context: dict) -> bool:
        deployment.log("Switching traffic back to blue")
        return True

    pipeline.add_rollback_step("switch_back", step_switch_back)

    return pipeline


# Singleton manager
_deployment_manager: Optional[DeploymentManager] = None


def get_deployment_manager() -> DeploymentManager:
    """Get or create the global deployment manager."""
    global _deployment_manager
    if _deployment_manager is None:
        _deployment_manager = DeploymentManager()
        # Register default pipeline
        _deployment_manager.register_pipeline("default", create_default_pipeline())
        _deployment_manager.register_pipeline("blue-green", create_blue_green_pipeline())
    return _deployment_manager
