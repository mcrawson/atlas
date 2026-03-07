"""Automation web routes."""

import asyncio
from fastapi import APIRouter, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from ...automation import AutomationManager, CommandExecutor

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("/", response_class=HTMLResponse)
async def automation_index(request: Request):
    """Automation dashboard."""
    manager = AutomationManager()
    pending = manager.get_pending_tasks()
    recent = manager.get_recent_tasks(limit=10)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "automation.html",
        {
            "request": request,
            "pending_tasks": pending,
            "recent_tasks": recent,
        }
    )


@router.post("/task/create")
async def create_task(
    request: Request,
    name: str = Form(...),
    commands: str = Form(...),
    working_dir: str = Form(None),
):
    """Create a new automation task."""
    manager = AutomationManager()

    # Parse commands (one per line)
    cmd_list = [c.strip() for c in commands.split('\n') if c.strip()]

    if not cmd_list:
        return JSONResponse({"error": "No commands provided"}, status_code=400)

    task = manager.create_task(
        name=name,
        commands=cmd_list,
        working_dir=working_dir if working_dir else None,
    )

    return RedirectResponse(f"/automation/task/{task.id}", status_code=303)


@router.get("/task/{task_id}", response_class=HTMLResponse)
async def view_task(request: Request, task_id: str):
    """View task details."""
    manager = AutomationManager()
    task = manager.get_task(task_id)

    if not task:
        return HTMLResponse("<h1>Task not found</h1>", status_code=404)

    # Get risk info for each command
    executor = CommandExecutor()
    command_risks = []
    for cmd in task.commands:
        risk, reason = executor.assess_risk(cmd)
        command_risks.append({"command": cmd, "risk": risk.value, "reason": reason})

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "automation_task.html",
        {
            "request": request,
            "task": task,
            "command_risks": command_risks,
        }
    )


@router.post("/task/{task_id}/approve")
async def approve_task(request: Request, task_id: str):
    """Approve a task for execution."""
    manager = AutomationManager()

    if manager.approve_task(task_id, approved_by="web_user"):
        return RedirectResponse(f"/automation/task/{task_id}", status_code=303)
    else:
        return JSONResponse({"error": "Could not approve task"}, status_code=400)


@router.post("/task/{task_id}/cancel")
async def cancel_task(request: Request, task_id: str):
    """Cancel a task."""
    manager = AutomationManager()

    if manager.cancel_task(task_id):
        return RedirectResponse(f"/automation/task/{task_id}", status_code=303)
    else:
        return JSONResponse({"error": "Could not cancel task"}, status_code=400)


@router.post("/task/{task_id}/execute")
async def execute_task(request: Request, task_id: str, background_tasks: BackgroundTasks):
    """Execute a task."""
    manager = AutomationManager()
    task = manager.get_task(task_id)

    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)

    if not task.approved:
        return JSONResponse({"error": "Task not approved"}, status_code=400)

    # Execute in background
    async def run_task():
        await manager.execute_task(task_id)

    background_tasks.add_task(asyncio.create_task, run_task())

    return RedirectResponse(f"/automation/task/{task_id}", status_code=303)


@router.get("/from-knowledge/{entry_id}")
async def create_from_knowledge(request: Request, entry_id: str, working_dir: str = None):
    """Create automation task from knowledge entry."""
    manager = AutomationManager()
    task = manager.create_from_knowledge(
        entry_id,
        working_dir=working_dir,
    )

    if task:
        return RedirectResponse(f"/automation/task/{task.id}", status_code=303)
    else:
        return JSONResponse({"error": "Could not create task from knowledge entry"}, status_code=400)


@router.get("/api/task/{task_id}")
async def api_task_status(task_id: str):
    """Get task status (for polling)."""
    manager = AutomationManager()
    task = manager.get_task(task_id)

    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)

    return JSONResponse(task.to_dict())
