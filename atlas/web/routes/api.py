"""REST API routes for ATLAS Web."""

import logging
import time
from fastapi import APIRouter, Request, HTTPException

from atlas.web.models import (
    TaskRequest,
    ProjectCreateRequest,
    TaskCreateRequest,
    WorkflowModeEnum,
    # Response models
    StatusResponse,
    ProjectStatsResponse,
    AgentsStatusResponse,
    ProjectListResponse,
    ProjectResponse,
    TaskResponse,
    TaskExecutionResponse,
    SuccessResponse,
    ErrorResponse,
    HealthCheckResponse,
)

logger = logging.getLogger("atlas.web.api")
router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check(request: Request) -> HealthCheckResponse:
    """Health check endpoint for monitoring.

    Returns detailed health status of all system components:
    - Database connectivity
    - Agent availability
    - Provider status

    Use this endpoint for:
    - Load balancer health checks
    - Kubernetes liveness/readiness probes
    - Monitoring systems
    """
    checks = {}
    overall_status = "healthy"

    # Check database/project manager
    project_manager = request.app.state.project_manager
    if project_manager:
        try:
            start = time.time()
            # Simple connectivity check
            await project_manager.get_stats()
            latency_ms = int((time.time() - start) * 1000)
            checks["database"] = {
                "status": "ok",
                "latency_ms": latency_ms,
            }
        except Exception as e:
            logger.error(f"Health check - database error: {e}")
            checks["database"] = {
                "status": "error",
                "error": str(e),
            }
            overall_status = "degraded"
    else:
        checks["database"] = {"status": "not_configured"}

    # Check agents
    agent_manager = request.app.state.agent_manager
    if agent_manager:
        try:
            agents = agent_manager.get_all_status()
            checks["agents"] = {
                "status": "ok",
                "count": len(agents),
                "agents": list(agents.keys()),
            }
        except Exception as e:
            logger.error(f"Health check - agents error: {e}")
            checks["agents"] = {
                "status": "error",
                "error": str(e),
            }
            overall_status = "degraded"
    else:
        checks["agents"] = {"status": "not_configured"}

    # Check providers
    providers = request.app.state.providers
    if providers:
        available = []
        unavailable = []
        for name, provider in providers.items():
            try:
                if hasattr(provider, "is_available") and provider.is_available():
                    available.append(name)
                else:
                    unavailable.append(name)
            except Exception:
                unavailable.append(name)

        checks["providers"] = {
            "status": "ok" if available else "warning",
            "available": available,
            "unavailable": unavailable,
        }
        if not available:
            overall_status = "degraded"
    else:
        checks["providers"] = {"status": "not_configured"}

    return HealthCheckResponse(
        status=overall_status,
        version="2.0.0",
        checks=checks,
    )


@router.get("/status", response_model=StatusResponse)
async def get_status(request: Request) -> StatusResponse:
    """Get system status."""
    agent_manager = request.app.state.agent_manager
    project_manager = request.app.state.project_manager

    agents = {}
    projects = ProjectStatsResponse()

    if agent_manager:
        agents = agent_manager.get_all_status()

    if project_manager:
        try:
            stats = await project_manager.get_stats()
            projects = ProjectStatsResponse(**stats)
        except Exception as e:
            logger.error(f"Failed to get project stats: {e}")

    return StatusResponse(status="ok", agents=agents, projects=projects)


@router.post("/task", response_model=TaskExecutionResponse)
async def execute_task(request: Request, task_request: TaskRequest) -> TaskExecutionResponse:
    """Execute a task through the agent pipeline.

    Request body:
        - task: The task description
        - mode: Workflow mode (sequential, direct_build, verify_only)
        - context: Optional context dictionary
    """
    agent_manager = request.app.state.agent_manager

    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not initialized")

    from atlas.agents.manager import WorkflowMode

    mode_map = {
        # Creation modes
        WorkflowModeEnum.SEQUENTIAL: WorkflowMode.SEQUENTIAL,
        WorkflowModeEnum.DIRECT_BUILD: WorkflowMode.DIRECT_BUILD,
        WorkflowModeEnum.VERIFY_ONLY: WorkflowMode.VERIFY_ONLY,
        WorkflowModeEnum.SPEC_DRIVEN: WorkflowMode.SPEC_DRIVEN,
        WorkflowModeEnum.FULL_DEPLOY: WorkflowMode.FULL_DEPLOY,
        WorkflowModeEnum.DEPLOY_ONLY: WorkflowMode.DEPLOY_ONLY,
        WorkflowModeEnum.FULL_POLISH: WorkflowMode.FULL_POLISH,
        WorkflowModeEnum.FULL_CAMPAIGN: WorkflowMode.FULL_CAMPAIGN,
        WorkflowModeEnum.PROMOTE_ONLY: WorkflowMode.PROMOTE_ONLY,
        # Update modes
        WorkflowModeEnum.UPDATE: WorkflowMode.UPDATE,
        WorkflowModeEnum.UPDATE_PATCH: WorkflowMode.UPDATE_PATCH,
        WorkflowModeEnum.UPDATE_MINOR: WorkflowMode.UPDATE_MINOR,
        WorkflowModeEnum.UPDATE_MAJOR: WorkflowMode.UPDATE_MAJOR,
        WorkflowModeEnum.HOTFIX: WorkflowMode.HOTFIX,
    }
    workflow_mode = mode_map.get(task_request.mode, WorkflowMode.SEQUENTIAL)

    try:
        outputs = await agent_manager.execute_workflow(
            task=task_request.task,
            mode=workflow_mode,
            context=task_request.context,
        )

        results = {}
        for agent_name, output in outputs.items():
            if hasattr(output, 'to_dict'):
                results[agent_name] = output.to_dict()
            else:
                results[agent_name] = str(output)

        return TaskExecutionResponse(
            status="completed",
            task=task_request.task,
            mode=task_request.mode.value,
            results=results,
        )

    except Exception as e:
        logger.error(f"Task execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", response_model=AgentsStatusResponse)
async def get_agents(request: Request) -> AgentsStatusResponse:
    """Get agent status."""
    agent_manager = request.app.state.agent_manager

    if not agent_manager:
        return AgentsStatusResponse(agents={})

    return AgentsStatusResponse(agents=agent_manager.get_all_status())


@router.get("/projects", response_model=ProjectListResponse)
async def get_projects(request: Request, include_tasks: bool = False) -> ProjectListResponse:
    """Get all projects."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        return ProjectListResponse(projects=[], total=0)

    try:
        projects = await project_manager.get_projects(include_tasks=include_tasks)
        project_list = [p.to_dict() for p in projects]
        return ProjectListResponse(projects=project_list, total=len(project_list))
    except Exception as e:
        logger.error(f"Failed to get projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects", response_model=SuccessResponse, status_code=201)
async def create_project(request: Request, project_request: ProjectCreateRequest) -> SuccessResponse:
    """Create a new project."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    try:
        project = await project_manager.create_project(
            name=project_request.name,
            description=project_request.description,
            tags=project_request.tags,
        )
        return SuccessResponse(
            success=True,
            message="Project created successfully",
            data={"project": project.to_dict()}
        )
    except Exception as e:
        logger.error(f"Failed to create project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=SuccessResponse)
async def get_project(request: Request, project_id: int) -> SuccessResponse:
    """Get a specific project."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id, include_tasks=True)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return SuccessResponse(
        success=True,
        message="Project retrieved successfully",
        data={"project": project.to_dict()}
    )


@router.post("/projects/{project_id}/tasks", response_model=SuccessResponse, status_code=201)
async def add_task(request: Request, project_id: int, task_request: TaskCreateRequest) -> SuccessResponse:
    """Add a task to a project."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    task = await project_manager.add_task(
        project_id=project_id,
        title=task_request.title,
        description=task_request.description,
        priority=task_request.priority,
    )

    if not task:
        raise HTTPException(status_code=404, detail="Project not found")

    return SuccessResponse(
        success=True,
        message="Task created successfully",
        data={"task": task.to_dict()}
    )


@router.post("/projects/{project_id}/tasks/{task_id}/execute", response_model=SuccessResponse)
async def execute_project_task(request: Request, project_id: int, task_id: int) -> SuccessResponse:
    """Execute a project task through the agent pipeline."""
    project_manager = request.app.state.project_manager
    agent_manager = request.app.state.agent_manager

    if not project_manager or not agent_manager:
        raise HTTPException(status_code=500, detail="Managers not initialized")

    task = await project_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    from atlas.projects.models import TaskStatus
    from atlas.agents.manager import WorkflowMode

    await project_manager.update_task_status(task_id, TaskStatus.PLANNING)

    try:
        outputs = await agent_manager.execute_workflow(
            task=f"{task.title}\n\n{task.description}",
            mode=WorkflowMode.SEQUENTIAL,
        )

        # Store outputs
        for agent_name, output in outputs.items():
            if hasattr(output, 'content'):
                await project_manager.add_agent_output(
                    task_id=task_id,
                    agent_name=agent_name,
                    content=output.content,
                    artifacts=output.artifacts,
                    metadata=output.metadata,
                )

        # Update status
        oracle_output = outputs.get("oracle")
        if oracle_output and oracle_output.metadata.get("verdict") == "APPROVED":
            await project_manager.update_task_status(task_id, TaskStatus.COMPLETED)
        else:
            await project_manager.update_task_status(task_id, TaskStatus.REVISION)

        # Return updated task
        updated_task = await project_manager.get_task(task_id)
        return SuccessResponse(
            success=True,
            message="Task executed successfully",
            data={"task": updated_task.to_dict()}
        )

    except Exception as e:
        logger.error(f"Task execution failed: {e}", exc_info=True)
        await project_manager.update_task_status(task_id, TaskStatus.FAILED)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/preview", response_model=SuccessResponse)
async def update_project_preview(request: Request, project_id: int) -> SuccessResponse:
    """Update product preview data for a project.

    Handles both JSON data and multipart form data (for file uploads).
    """
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content_type = request.headers.get("content-type", "")

    try:
        if "multipart/form-data" in content_type:
            # Handle file uploads
            from fastapi import UploadFile
            import os
            from pathlib import Path

            form = await request.form()
            preview_data_str = form.get("preview_data", "{}")

            import json
            preview_data = json.loads(preview_data_str) if preview_data_str else {}

            # Handle icon upload
            icon_file = form.get("icon")
            if icon_file and hasattr(icon_file, 'file'):
                uploads_dir = Path("uploads") / "previews" / str(project_id)
                uploads_dir.mkdir(parents=True, exist_ok=True)

                icon_path = uploads_dir / f"icon_{icon_file.filename}"
                with open(icon_path, "wb") as f:
                    f.write(await icon_file.read())
                preview_data["icon"] = f"/uploads/previews/{project_id}/icon_{icon_file.filename}"

            # Handle screenshot upload
            screenshot_file = form.get("screenshot")
            if screenshot_file and hasattr(screenshot_file, 'file'):
                uploads_dir = Path("uploads") / "previews" / str(project_id)
                uploads_dir.mkdir(parents=True, exist_ok=True)

                ss_path = uploads_dir / f"screenshot_{screenshot_file.filename}"
                with open(ss_path, "wb") as f:
                    f.write(await screenshot_file.read())
                preview_data["screenshot"] = f"/uploads/previews/{project_id}/screenshot_{screenshot_file.filename}"

        else:
            # Handle JSON
            import json
            body = await request.json()
            preview_data = body.get("preview_data", {})

        # Update project metadata
        metadata = project.metadata or {}
        metadata["product_preview"] = preview_data

        await project_manager.update_project(project_id, metadata=metadata)

        return SuccessResponse(
            success=True,
            message="Preview data updated successfully",
            data={"preview": preview_data}
        )

    except Exception as e:
        logger.error(f"Error updating preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
