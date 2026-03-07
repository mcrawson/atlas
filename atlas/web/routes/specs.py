"""Spec management routes for ATLAS Web Dashboard."""

print(">>> LOADING SPECS ROUTES MODULE <<<")

import json
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse

# Lazy import to avoid startup errors
SpecGenerator = None
SpecManager = None

def _lazy_import():
    global SpecGenerator, SpecManager
    if SpecGenerator is None:
        from atlas.specs import SpecGenerator as SG, SpecManager as SM
        SpecGenerator = SG
        SpecManager = SM

router = APIRouter()
print(f">>> SPECS ROUTER CREATED: {router} <<<")


@router.get("/test")
async def test_route():
    """Simple test route to verify routing works."""
    return PlainTextResponse("Specs router is working!")


def get_spec_manager(request: Request):
    """Get or create SpecManager from app state."""
    _lazy_import()
    if not hasattr(request.app.state, "spec_manager") or request.app.state.spec_manager is None:
        data_dir = Path(__file__).parent.parent.parent.parent / "data"
        request.app.state.spec_manager = SpecManager(data_dir / "specs.db")
    return request.app.state.spec_manager


def get_spec_generator(request: Request):
    """Get or create SpecGenerator."""
    _lazy_import()
    if not hasattr(request.app.state, "spec_generator") or request.app.state.spec_generator is None:
        request.app.state.spec_generator = SpecGenerator()
    return request.app.state.spec_generator


# ============================================
# STATIC ROUTES (must come before /{spec_id})
# ============================================

@router.get("/", response_class=HTMLResponse)
@router.get("", response_class=HTMLResponse)
async def specs_list(request: Request):
    """List all specs."""
    templates = request.app.state.templates
    spec_manager = get_spec_manager(request)

    # Get all specs from database
    specs = []
    try:
        import sqlite3
        with sqlite3.connect(spec_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM specs ORDER BY created_at DESC"
            )
            specs = [dict(row) for row in cursor.fetchall()]
    except Exception:
        pass

    return templates.TemplateResponse("specs_list.html", {
        "request": request,
        "specs": specs,
        "page_title": "Specs",
    })


@router.get("/new", response_class=HTMLResponse)
async def new_spec_form(request: Request, project_id: int = None):
    """Show form to create a new spec."""
    templates = request.app.state.templates

    # Get projects for dropdown
    projects = []
    if request.app.state.project_manager:
        projects = await request.app.state.project_manager.get_projects()

    return templates.TemplateResponse("spec_new.html", {
        "request": request,
        "projects": projects,
        "selected_project_id": project_id,
        "page_title": "New Spec",
    })


@router.post("/generate")
async def generate_spec(
    request: Request,
    idea: str = Form(...),
    project_id: int = Form(None),
    features: str = Form(""),
    technical: str = Form(""),
    constraints: str = Form(""),
    write_files: bool = Form(False),
    output_dir: str = Form(""),
):
    """Generate a spec from an idea using AI."""
    spec_generator = get_spec_generator(request)
    spec_manager = get_spec_manager(request)

    # Parse features list
    feature_list = [f.strip() for f in features.split("\n") if f.strip()]

    context = {
        "features": feature_list,
        "technical": technical,
        "constraints": constraints,
    }

    try:
        # Generate spec using AI
        spec = await spec_generator.generate_from_idea(idea, context)

        # Save to database
        spec_dir = None
        if write_files and output_dir:
            result = spec_generator.write_spec_files(spec, output_dir)
            spec_dir = result["spec_dir"]

        spec_id = spec_manager.save_spec(spec, project_id, spec_dir)

        return RedirectResponse(f"/specs/{spec_id}", status_code=303)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# API endpoints (must come before /{spec_id})
@router.get("/api/project/{project_id}")
async def get_project_specs(request: Request, project_id: int):
    """Get all specs for a project (API/HTMX endpoint)."""
    spec_manager = get_spec_manager(request)
    templates = request.app.state.templates
    specs = spec_manager.get_specs_for_project(project_id)

    # Check if this is an HTMX request
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("partials/specs_list.html", {
            "request": request,
            "specs": specs,
        })

    return {"specs": specs}


# ============================================
# DYNAMIC ROUTES (with {spec_id} parameter)
# ============================================

@router.get("/{spec_id}", response_class=HTMLResponse)
async def spec_detail(request: Request, spec_id: int):
    """View spec details."""
    templates = request.app.state.templates
    spec_manager = get_spec_manager(request)

    spec = spec_manager.get_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    tasks = spec_manager.get_tasks_for_spec(spec_id)
    progress = spec_manager.get_spec_progress(spec_id)

    # Parse metadata JSON
    metadata = {}
    if spec.get("metadata"):
        try:
            metadata = json.loads(spec["metadata"])
        except Exception:
            pass

    return templates.TemplateResponse("spec_detail.html", {
        "request": request,
        "spec": spec,
        "tasks": tasks,
        "progress": progress,
        "metadata": metadata,
        "page_title": spec.get("name", "Spec"),
    })


@router.get("/{spec_id}/requirements", response_class=HTMLResponse)
async def spec_requirements(request: Request, spec_id: int):
    """View spec requirements in markdown format."""
    templates = request.app.state.templates
    spec_manager = get_spec_manager(request)

    spec = spec_manager.get_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    # Get requirements from metadata
    metadata = {}
    requirements = []
    if spec.get("metadata"):
        try:
            metadata = json.loads(spec["metadata"])
        except Exception:
            pass

    # If spec_dir exists, read requirements.md
    requirements_content = ""
    if spec.get("spec_dir"):
        spec_files = spec_manager.read_spec_files(spec["spec_dir"])
        requirements_content = spec_files.get("requirements", "")

    return templates.TemplateResponse("spec_requirements.html", {
        "request": request,
        "spec": spec,
        "requirements_content": requirements_content,
        "page_title": f"Requirements: {spec.get('name', 'Spec')}",
    })


@router.get("/{spec_id}/design", response_class=HTMLResponse)
async def spec_design(request: Request, spec_id: int):
    """View spec design in markdown format."""
    templates = request.app.state.templates
    spec_manager = get_spec_manager(request)

    spec = spec_manager.get_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    # If spec_dir exists, read design.md
    design_content = ""
    if spec.get("spec_dir"):
        spec_files = spec_manager.read_spec_files(spec["spec_dir"])
        design_content = spec_files.get("design", "")

    return templates.TemplateResponse("spec_design.html", {
        "request": request,
        "spec": spec,
        "design_content": design_content,
        "page_title": f"Design: {spec.get('name', 'Spec')}",
    })


@router.get("/{spec_id}/tasks", response_class=HTMLResponse)
async def spec_tasks(request: Request, spec_id: int):
    """View and manage spec tasks."""
    templates = request.app.state.templates
    spec_manager = get_spec_manager(request)

    spec = spec_manager.get_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    tasks = spec_manager.get_tasks_for_spec(spec_id)
    progress = spec_manager.get_spec_progress(spec_id)

    # Group tasks by status
    task_groups = {
        "pending": [],
        "in_progress": [],
        "completed": [],
        "blocked": [],
    }
    for task in tasks:
        status = task.get("status", "pending")
        if status in task_groups:
            task_groups[status].append(task)

    return templates.TemplateResponse("spec_tasks.html", {
        "request": request,
        "spec": spec,
        "tasks": tasks,
        "task_groups": task_groups,
        "progress": progress,
        "page_title": f"Tasks: {spec.get('name', 'Spec')}",
    })


@router.post("/{spec_id}/tasks/{task_id}/status")
async def update_task_status(
    request: Request,
    spec_id: int,
    task_id: str,
    status: str = Form(...),
):
    """Update a task's status."""
    spec_manager = get_spec_manager(request)

    valid_statuses = ["pending", "in_progress", "completed", "blocked"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    success = spec_manager.update_task_status(spec_id, task_id, status)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update task status")

    # Return to tasks page
    return RedirectResponse(f"/specs/{spec_id}/tasks", status_code=303)


@router.get("/{spec_id}/execute", response_class=HTMLResponse)
async def execute_spec_task(request: Request, spec_id: int):
    """Show interface to execute next spec task through agents."""
    templates = request.app.state.templates
    spec_manager = get_spec_manager(request)

    spec = spec_manager.get_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    # Get next pending task
    pending_tasks = spec_manager.get_pending_tasks(spec_id)
    next_task = pending_tasks[0] if pending_tasks else None

    progress = spec_manager.get_spec_progress(spec_id)

    return templates.TemplateResponse("spec_execute.html", {
        "request": request,
        "spec": spec,
        "next_task": next_task,
        "pending_tasks": pending_tasks,
        "progress": progress,
        "page_title": f"Execute: {spec.get('name', 'Spec')}",
    })


@router.post("/{spec_id}/execute/{task_id}")
async def execute_task(request: Request, spec_id: int, task_id: str):
    """Execute a spec task through the agent workflow."""
    spec_manager = get_spec_manager(request)
    agent_manager = request.app.state.agent_manager

    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent system not available")

    # Get spec and task
    spec = spec_manager.get_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    tasks = spec_manager.get_tasks_for_spec(spec_id)
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Mark task as in progress
    spec_manager.update_task_status(spec_id, task_id, "in_progress")

    # Build context from spec
    context = {
        "spec_name": spec.get("name"),
        "spec_description": spec.get("description"),
        "task_title": task.get("title"),
        "task_description": task.get("description") or task.get("title"),
        "requirement_ids": task.get("requirement_ids", "[]"),
    }

    # Read spec files if available
    if spec.get("spec_dir"):
        spec_files = spec_manager.read_spec_files(spec["spec_dir"])
        context["requirements"] = spec_files.get("requirements", "")
        context["design"] = spec_files.get("design", "")

    try:
        # Execute through agent workflow
        from atlas.agents.manager import WorkflowMode

        task_prompt = f"""Execute this spec task:

Task: {task.get('title')}
Description: {task.get('description') or task.get('title')}
Priority: {task.get('priority', 'medium')}

Context:
- Spec: {spec.get('name')}
- Requirements: {context.get('requirement_ids', '[]')}

{f"Design Context:{chr(10)}{context.get('design', '')[:2000]}" if context.get('design') else ""}
"""

        outputs = await agent_manager.execute_workflow(
            task_prompt,
            mode=WorkflowMode.SEQUENTIAL,
            context=context
        )

        # Check if Oracle approved
        oracle_output = outputs.get("oracle")
        if oracle_output and oracle_output.metadata.get("verdict") == "APPROVED":
            spec_manager.update_task_status(spec_id, task_id, "completed")

        return RedirectResponse(f"/specs/{spec_id}/tasks", status_code=303)

    except Exception as e:
        # Mark as pending again on error
        spec_manager.update_task_status(spec_id, task_id, "pending")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{spec_id}/progress")
async def get_spec_progress_api(request: Request, spec_id: int):
    """Get spec progress (API endpoint for HTMX polling)."""
    spec_manager = get_spec_manager(request)
    progress = spec_manager.get_spec_progress(spec_id)
    return progress


@router.post("/{spec_id}/chat")
async def spec_chat(request: Request, spec_id: int):
    """Chat with Sketch about a spec."""
    from fastapi.responses import JSONResponse

    spec_manager = get_spec_manager(request)
    agent_manager = request.app.state.agent_manager

    # Get spec
    spec = spec_manager.get_spec(spec_id)
    if not spec:
        return JSONResponse({"error": "Spec not found"}, status_code=404)

    # Parse request body
    try:
        body = await request.json()
        message = body.get("message", "")
        history = body.get("history", [])
    except Exception:
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    if not message.strip():
        return JSONResponse({"error": "Message is required"}, status_code=400)

    # Get spec context
    spec_context = f"""
SPEC: {spec.get('name', 'Unnamed Spec')}
DESCRIPTION: {spec.get('description', 'No description')}
STATUS: {spec.get('status', 'unknown')}
"""

    # Get tasks summary
    tasks = spec_manager.get_tasks_for_spec(spec_id)
    if tasks:
        progress = spec_manager.get_spec_progress(spec_id)
        spec_context += f"""
TASKS: {progress.get('total', 0)} total ({progress.get('completed', 0)} completed, {progress.get('pending', 0)} pending)
"""

    # Read spec files if available
    if spec.get("spec_dir"):
        spec_files = spec_manager.read_spec_files(spec["spec_dir"])
        if spec_files.get("requirements"):
            spec_context += f"\nREQUIREMENTS SUMMARY:\n{spec_files['requirements'][:1500]}...\n"

    # Build system prompt for Sketch
    system_prompt = """You are Sketch, the strategic planning agent within ATLAS.

You are helping the user refine and understand a specification. You have access to the spec details below.

YOUR ROLE IN THIS CONVERSATION:
- Answer questions about the spec
- Help clarify requirements
- Suggest improvements or additions
- Identify potential gaps or risks
- Help the user understand what will be built

Be helpful, specific, and reference the actual spec content when answering.

SPEC CONTEXT:
""" + spec_context

    # If no AI provider, provide a fallback response
    if not agent_manager or not hasattr(agent_manager, 'router'):
        fallback = f"""I'm Sketch, but I'm currently running without an AI provider.

Here's what I know about this spec:
- **Name:** {spec.get('name', 'Unnamed')}
- **Status:** {spec.get('status', 'unknown')}
- **Tasks:** {len(tasks)} total

To get intelligent responses, please configure an AI provider in ATLAS settings.

In the meantime, you can:
- View the Requirements, Design, and Tasks documents
- Manually edit the spec files if they exist
- Execute tasks through the agent workflow"""

        return JSONResponse({"response": fallback})

    try:
        # Build conversation for the AI
        full_prompt = system_prompt + "\n\nUser question: " + message

        # Use the router to generate response
        response_text, token_info = await agent_manager.router.generate(
            prompt=full_prompt,
            temperature=0.7,
        )

        return JSONResponse({
            "response": response_text,
            "tokens_used": token_info.get("total_tokens", 0),
        })

    except Exception as e:
        return JSONResponse({
            "error": f"Failed to generate response: {str(e)}"
        }, status_code=500)
