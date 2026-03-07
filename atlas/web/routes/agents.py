"""Agent management routes for ATLAS Web."""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("", response_class=HTMLResponse)
async def agent_status(request: Request):
    """Show agent status page."""
    templates = request.app.state.templates
    agent_manager = request.app.state.agent_manager

    agents = {}
    if agent_manager:
        agents = agent_manager.get_all_status()

    return templates.TemplateResponse(
        "agents.html",
        {
            "request": request,
            "agents": agents,
        }
    )


@router.post("/execute", response_class=HTMLResponse)
async def execute_task(
    request: Request,
    task: str = Form(...),
    mode: str = Form("sequential"),
):
    """Execute a task through the agent pipeline."""
    templates = request.app.state.templates
    agent_manager = request.app.state.agent_manager

    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not initialized")

    from atlas.agents.manager import WorkflowMode

    # Map mode string to enum
    mode_map = {
        "sequential": WorkflowMode.SEQUENTIAL,
        "direct_build": WorkflowMode.DIRECT_BUILD,
        "verify_only": WorkflowMode.VERIFY_ONLY,
    }
    workflow_mode = mode_map.get(mode, WorkflowMode.SEQUENTIAL)

    try:
        outputs = await agent_manager.execute_workflow(
            task=task,
            mode=workflow_mode,
        )

        # Format outputs for display
        results = []
        files_written = None

        for agent_name, output in outputs.items():
            # Handle file write results separately
            if agent_name == "files":
                files_written = {
                    "success": output.success,
                    "project_dir": output.project_dir,
                    "files": output.files_written,
                    "errors": output.errors,
                }
                continue

            if hasattr(output, 'content'):
                results.append({
                    "agent": agent_name,
                    "content": output.content,
                    "status": output.status.value if hasattr(output, 'status') else "completed",
                    "metadata": output.metadata if hasattr(output, 'metadata') else {},
                })

        # Return results partial or full page
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "partials/execution_results.html",
                {
                    "request": request,
                    "task": task,
                    "results": results,
                    "files_written": files_written,
                }
            )

        return templates.TemplateResponse(
            "execution_results.html",
            {
                "request": request,
                "task": task,
                "results": results,
                "files_written": files_written,
            }
        )

    except Exception as e:
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "partials/error.html",
                {
                    "request": request,
                    "error": str(e),
                }
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/partials/status", response_class=HTMLResponse)
async def agent_status_partial(request: Request):
    """Get agent status partial for HTMX polling."""
    templates = request.app.state.templates
    agent_manager = request.app.state.agent_manager

    agents = {}
    if agent_manager:
        agents = agent_manager.get_all_status()

    return templates.TemplateResponse(
        "partials/agent_status.html",
        {
            "request": request,
            "agents": agents,
        }
    )
