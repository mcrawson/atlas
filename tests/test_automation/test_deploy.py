"""Tests for deployment automation functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from atlas.automation.deploy import (
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
    step_pull_image,
    step_stop_service,
    step_start_service,
)


class TestDeploymentTarget:
    """Test DeploymentTarget dataclass."""

    def test_create_target(self):
        """Test creating a deployment target."""
        target = DeploymentTarget(
            name="production",
            environment=Environment.PRODUCTION,
            url="https://api.example.com",
            health_check_url="https://api.example.com/health",
            requires_approval=True,
            notify_channel="#deployments",
        )

        assert target.name == "production"
        assert target.environment == Environment.PRODUCTION
        assert target.requires_approval is True

    def test_minimal_target(self):
        """Test minimal target configuration."""
        target = DeploymentTarget(
            name="dev",
            environment=Environment.DEV,
            url="http://localhost:8000",
        )

        assert target.health_check_url is None
        assert target.requires_approval is False


class TestDeployment:
    """Test Deployment dataclass."""

    @pytest.fixture
    def target(self):
        """Create a test target."""
        return DeploymentTarget(
            name="staging",
            environment=Environment.STAGING,
            url="https://staging.example.com",
        )

    def test_create_deployment(self, target):
        """Test creating a deployment."""
        deployment = Deployment(
            id="deploy-123",
            service="atlas-api",
            version="v1.2.3",
            target=target,
        )

        assert deployment.id == "deploy-123"
        assert deployment.service == "atlas-api"
        assert deployment.status == DeploymentStatus.PENDING
        assert deployment.logs == []

    def test_deployment_log(self, target):
        """Test adding log messages."""
        deployment = Deployment(
            id="deploy-123",
            service="atlas-api",
            version="v1.2.3",
            target=target,
        )

        deployment.log("Starting deployment")
        deployment.log("Pulling image")

        assert len(deployment.logs) == 2
        assert "Starting deployment" in deployment.logs[0]


class TestDeploymentStep:
    """Test DeploymentStep class."""

    @pytest.fixture
    def target(self):
        return DeploymentTarget(
            name="test", environment=Environment.DEV, url="http://test"
        )

    @pytest.mark.asyncio
    async def test_execute_step_success(self, target):
        """Test executing a successful step."""

        async def handler(deployment, context):
            context["executed"] = True
            return True

        step = DeploymentStep("test_step", handler)
        deployment = Deployment(
            id="test", service="svc", version="v1", target=target
        )
        context = {}

        result = await step.execute(deployment, context)

        assert result is True
        assert context["executed"] is True

    @pytest.mark.asyncio
    async def test_execute_step_failure(self, target):
        """Test executing a failing step."""

        async def handler(deployment, context):
            return False

        step = DeploymentStep("failing_step", handler)
        deployment = Deployment(
            id="test", service="svc", version="v1", target=target
        )

        result = await step.execute(deployment, {})

        assert result is False

    @pytest.mark.asyncio
    async def test_execute_step_error(self, target):
        """Test step that raises an error."""

        async def handler(deployment, context):
            raise ValueError("Step error")

        step = DeploymentStep("error_step", handler)
        deployment = Deployment(
            id="test", service="svc", version="v1", target=target
        )

        with pytest.raises(ValueError):
            await step.execute(deployment, {})


class TestDeploymentPipeline:
    """Test DeploymentPipeline class."""

    @pytest.fixture
    def target(self):
        return DeploymentTarget(
            name="test", environment=Environment.DEV, url="http://test"
        )

    def test_create_pipeline(self):
        """Test creating a pipeline."""
        pipeline = DeploymentPipeline("test-pipeline")

        assert pipeline.name == "test-pipeline"
        assert pipeline.steps == []

    def test_add_step(self):
        """Test adding steps."""
        pipeline = DeploymentPipeline("test")

        async def step1(d, c):
            return True

        async def step2(d, c):
            return True

        pipeline.add_step("step1", step1).add_step("step2", step2)

        assert len(pipeline.steps) == 2
        assert pipeline.steps[0].name == "step1"

    @pytest.mark.asyncio
    async def test_execute_success(self, target):
        """Test successful pipeline execution."""
        pipeline = DeploymentPipeline("success")

        async def step(d, c):
            return True

        pipeline.add_step("step", step)

        deployment = Deployment(
            id="test", service="svc", version="v1", target=target
        )

        result = await pipeline.execute(deployment)

        assert result.success is True
        assert deployment.status == DeploymentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_failure_triggers_rollback(self, target):
        """Test failed pipeline triggers rollback."""
        pipeline = DeploymentPipeline("failing")
        rollback_called = []

        async def failing_step(d, c):
            return False

        async def rollback_step(d, c):
            rollback_called.append(True)
            return True

        pipeline.add_step("fail", failing_step)
        pipeline.add_rollback_step("rollback", rollback_step)

        deployment = Deployment(
            id="test", service="svc", version="v1", target=target
        )

        result = await pipeline.execute(deployment)

        assert result.success is False
        assert deployment.status == DeploymentStatus.FAILED
        assert len(rollback_called) == 1


class TestDeploymentManager:
    """Test DeploymentManager class."""

    @pytest.fixture
    def manager(self):
        """Create a deployment manager."""
        manager = DeploymentManager()

        # Register a target
        target = DeploymentTarget(
            name="staging",
            environment=Environment.STAGING,
            url="https://staging.example.com",
        )
        manager.register_target(target)

        # Register a simple pipeline
        pipeline = DeploymentPipeline("simple")

        async def step(d, c):
            return True

        pipeline.add_step("deploy", step)
        manager.register_pipeline("simple", pipeline)

        return manager

    def test_register_target(self, manager):
        """Test registering targets."""
        target = DeploymentTarget(
            name="production",
            environment=Environment.PRODUCTION,
            url="https://prod.example.com",
        )

        manager.register_target(target)

        assert "production" in manager.targets

    def test_register_pipeline(self, manager):
        """Test registering pipelines."""
        pipeline = DeploymentPipeline("new-pipeline")
        manager.register_pipeline("new-pipeline", pipeline)

        assert "new-pipeline" in manager.pipelines

    @pytest.mark.asyncio
    async def test_deploy_success(self, manager):
        """Test successful deployment."""
        result = await manager.deploy(
            service="atlas-api",
            version="v1.2.3",
            target_name="staging",
            pipeline_name="simple",
            triggered_by="test",
        )

        assert result.success is True
        assert result.deployment.service == "atlas-api"
        assert result.deployment.version == "v1.2.3"

    @pytest.mark.asyncio
    async def test_deploy_unknown_target(self, manager):
        """Test deployment with unknown target."""
        with pytest.raises(ValueError, match="Unknown target"):
            await manager.deploy(
                service="svc",
                version="v1",
                target_name="nonexistent",
            )

    @pytest.mark.asyncio
    async def test_deploy_unknown_pipeline(self, manager):
        """Test deployment with unknown pipeline."""
        with pytest.raises(ValueError, match="Unknown pipeline"):
            await manager.deploy(
                service="svc",
                version="v1",
                target_name="staging",
                pipeline_name="nonexistent",
            )

    def test_get_deployment(self, manager):
        """Test getting deployment by ID."""

        async def run_deploy():
            result = await manager.deploy(
                service="svc",
                version="v1",
                target_name="staging",
                pipeline_name="simple",
            )
            return result.deployment.id

        import asyncio

        deployment_id = asyncio.get_event_loop().run_until_complete(run_deploy())

        deployment = manager.get_deployment(deployment_id)
        assert deployment is not None
        assert deployment.service == "svc"

    def test_get_recent_deployments(self, manager):
        """Test getting recent deployments."""
        import asyncio

        async def run_deploys():
            await manager.deploy("svc1", "v1", "staging", "simple")
            await manager.deploy("svc2", "v2", "staging", "simple")

        asyncio.get_event_loop().run_until_complete(run_deploys())

        recent = manager.get_recent_deployments(limit=5)
        assert len(recent) == 2


class TestBuiltInSteps:
    """Test built-in deployment steps."""

    @pytest.fixture
    def deployment(self):
        target = DeploymentTarget(
            name="test", environment=Environment.DEV, url="http://test"
        )
        return Deployment(
            id="test", service="atlas", version="v1.0", target=target
        )

    @pytest.mark.asyncio
    async def test_step_pull_image(self, deployment):
        """Test pull image step."""
        context = {}
        result = await step_pull_image(deployment, context)

        assert result is True
        assert "image" in context
        assert "atlas:v1.0" in context["image"]

    @pytest.mark.asyncio
    async def test_step_stop_service(self, deployment):
        """Test stop service step."""
        result = await step_stop_service(deployment, {})
        assert result is True

    @pytest.mark.asyncio
    async def test_step_start_service(self, deployment):
        """Test start service step."""
        context = {"image": "atlas:v1.0"}
        result = await step_start_service(deployment, context)
        assert result is True


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_default_pipeline(self):
        """Test creating default pipeline."""
        pipeline = create_default_pipeline()

        assert pipeline.name == "default"
        assert len(pipeline.steps) == 3
        assert len(pipeline.rollback_steps) == 1

    def test_create_blue_green_pipeline(self):
        """Test creating blue-green pipeline."""
        pipeline = create_blue_green_pipeline()

        assert pipeline.name == "blue-green"
        assert len(pipeline.steps) == 3
        assert len(pipeline.rollback_steps) == 1

    def test_get_deployment_manager_singleton(self):
        """Test singleton behavior."""
        import atlas.automation.deploy as module

        module._deployment_manager = None

        manager1 = get_deployment_manager()
        manager2 = get_deployment_manager()

        assert manager1 is manager2

    def test_get_deployment_manager_has_defaults(self):
        """Test manager has default pipelines."""
        import atlas.automation.deploy as module

        module._deployment_manager = None

        manager = get_deployment_manager()

        assert "default" in manager.pipelines
        assert "blue-green" in manager.pipelines
