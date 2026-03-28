"""Project management routes for ATLAS Web."""

import os
import re
import logging
from datetime import datetime
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from atlas.agents.governor import Governor, get_governor
from atlas.agents.training_collector import get_collector
from atlas.agents.guidance import get_guidance, TaskDecomposer
from atlas.agents.smart_conversation import SmartIdeaConversation
from atlas.agents.build_preview import BuildPreviewGenerator
from atlas.agents.buzz import get_buzz
from atlas.agents.sprint_meeting import get_sprint_meeting
from atlas.specs import SpecGenerator
from atlas.projects.project_types import ProjectTypeDetector, ProjectCategory

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_openai_key() -> str:
    """Get OpenAI API key from environment or config."""
    # Try environment first
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    # Try config file
    try:
        from atlas.core import Config
        config = Config()
        return config.get_api_key("openai")
    except (ImportError, AttributeError, KeyError):
        return None


def _create_conversation(project_identity: dict = None) -> SmartIdeaConversation:
    """Create a SmartIdeaConversation with the best available LLM."""
    openai_key = _get_openai_key()
    return SmartIdeaConversation(
        openai_api_key=openai_key,
        openai_model="gpt-4o-mini",  # Fast and cheap for conversations
        project_identity=project_identity,  # Pass canonical product type
    )


@router.get("", response_class=HTMLResponse)
async def list_projects(request: Request):
    """List all projects."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    projects = []
    stats = {}

    if project_manager:
        try:
            projects = await project_manager.get_projects(include_tasks=True)
            stats = await project_manager.get_stats()
        except Exception:
            pass

    return templates.TemplateResponse(
        "projects.html",
        {
            "request": request,
            "projects": projects,
            "stats": stats,
        }
    )


@router.post("/new-idea", response_class=HTMLResponse)
async def create_from_idea(request: Request, idea: str = Form(...), product_type: str = Form("app")):
    """Create a new project from an idea."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    # Detect project type from the idea
    detector = ProjectTypeDetector()
    project_type_detected, project_category, confidence = detector.detect(idea)
    type_config = detector.get_config(project_type_detected)

    # Build metadata with project type info
    # Create canonical project_identity - single source of truth for what we're building
    from datetime import datetime
    type_names = {"printable": "Printable", "document": "Document", "web": "Web App", "app": "Mobile App"}

    metadata = {
        "phase": "idea",
        "project_type": project_type_detected.value,
        "project_category": project_category.value,
        "project_type_confidence": confidence,
        # CANONICAL PROJECT IDENTITY - single source of truth
        "project_identity": {
            "product_type": product_type,  # printable, document, web, app
            "product_type_name": type_names.get(product_type, product_type.title()),
            "source": "user_explicit",  # user_explicit, analyst_inferred, conversation
            "confirmed": True,  # User explicitly chose this
            "locked": True,  # Agents cannot change this
            "set_at": datetime.now().isoformat(),
        },
    }

    # Add type-specific config if available
    if type_config:
        metadata["project_type_config"] = {
            "name": type_config.name,
            "description": type_config.description,
            "suggested_stack": type_config.suggested_stack,
            "build_approach": type_config.build_approach,
            "verification_focus": type_config.verification_focus,
            "key_questions": type_config.key_questions,
        }

    # Create project with the idea as name and detected type
    project = await project_manager.create_project(
        name=idea[:100],  # Truncate for name
        description=idea,
        metadata=metadata
    )

    return RedirectResponse(url=f"/projects/{project.id}", status_code=303)


@router.get("/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: int):
    """Show project details with pipeline view."""
    from atlas.standards import get_integrations_for_product

    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id, include_tasks=True)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Extract preview from build metadata if available
    preview = None
    publish_platforms = []
    if project.metadata:
        build_data = project.metadata.get("build", {})
        preview = build_data.get("preview")

        # Get publishing recommendations based on project type
        project_type = project.metadata.get("project_type", "")
        if project_type:
            integrations = get_integrations_for_product(project_type)
            publish_platforms = integrations.get("publish", [])

    return templates.TemplateResponse(
        "project_detail.html",
        {
            "request": request,
            "project": project,
            "preview": preview,
            "publish_platforms": publish_platforms,
        }
    )


@router.post("/{project_id}/idea/respond", response_class=HTMLResponse)
async def idea_conversation_respond(
    request: Request,
    project_id: int,
    response: str = Form(""),
):
    """Handle a response in the AI-powered idea conversation."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get or create smart conversation from project metadata
    metadata = project.metadata.copy() if project.metadata else {}
    conv_data = metadata.get("smart_conversation", {})

    openai_key = _get_openai_key()
    project_identity = metadata.get("project_identity")
    if conv_data:
        conversation = SmartIdeaConversation.from_dict(
            conv_data, openai_api_key=openai_key, project_identity=project_identity
        )
    else:
        conversation = _create_conversation(project_identity=project_identity)
        # Start with initial idea if available
        if project.description:
            await conversation.start(project.description)

    # Process the user's response with AI
    await conversation.respond(response)

    # Save conversation state
    metadata["smart_conversation"] = conversation.to_dict()

    # Save idea type info for display in header
    current_question = conversation.get_current_question()
    if current_question.get("idea_type"):
        metadata["idea_type"] = current_question["idea_type"]

    # If conversation is complete, update project context and move to planning
    if conversation.is_complete:
        brief = conversation.brief
        metadata["context"] = {
            "description": brief.description,
            "problem": brief.problem_statement,
            "features": brief.core_features,
            "technical": brief.technical_requirements,
            "target_users": brief.target_users,
            "constraints": brief.constraints,
            "success_criteria": brief.success_criteria,
            "scope": brief.scope,
        }
        metadata["architect_brief"] = conversation.get_architect_brief()
        # DON'T auto-transition to plan phase - let user click "Start Planning"
        # The UI will show the completion state with the "Start Planning" button
        # Update project with refined title/description
        await project_manager.update_project(
            project_id,
            name=brief.title or project.name,
            description=brief.description or project.description,
            metadata=metadata
        )

        # Notify via Buzz that idea is ready for planning
        buzz = get_buzz()
        await buzz.notify_idea_ready(
            project_id=project_id,
            project_name=brief.title or project.name,
            readiness_score=brief.readiness_score
        )
    else:
        await project_manager.update_project(project_id, metadata=metadata)

    # Re-fetch project with updates
    project = await project_manager.get_project(project_id)

    # Return partial HTML for HTMX
    return templates.TemplateResponse(
        "partials/smart_conversation.html",
        {
            "request": request,
            "project": project,
            "conversation": conversation.to_dict(),
            "current_question": conversation.get_current_question(),
        }
    )


@router.get("/{project_id}/idea/conversation", response_class=HTMLResponse)
async def get_idea_conversation(request: Request, project_id: int):
    """Get the current AI-powered idea conversation state."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get or create smart conversation
    metadata = project.metadata or {}
    conv_data = metadata.get("smart_conversation", {})

    openai_key = _get_openai_key()
    project_identity = metadata.get("project_identity")
    if conv_data:
        conversation = SmartIdeaConversation.from_dict(
            conv_data, openai_api_key=openai_key, project_identity=project_identity
        )
    else:
        conversation = _create_conversation(project_identity=project_identity)
        # Start conversation with AI
        await conversation.start(project.description or "")
        # Save initial state with idea type
        new_metadata = metadata.copy()
        new_metadata["smart_conversation"] = conversation.to_dict()
        current_question = conversation.get_current_question()
        if current_question.get("idea_type"):
            new_metadata["idea_type"] = current_question["idea_type"]
        await project_manager.update_project(project_id, metadata=new_metadata)

    return templates.TemplateResponse(
        "partials/smart_conversation.html",
        {
            "request": request,
            "project": project,
            "conversation": conversation.to_dict(),
            "current_question": conversation.get_current_question(),
        }
    )


@router.post("/{project_id}/skip-to-planning")
async def skip_to_planning(request: Request, project_id: int):
    """Skip conversation and go directly to planning with current info."""
    from fastapi.responses import RedirectResponse

    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get conversation data and extract what we have
    metadata = project.metadata.copy() if project.metadata else {}
    conv_data = metadata.get("smart_conversation", {})
    project_identity = metadata.get("project_identity")

    if conv_data:
        openai_key = _get_openai_key()
        conversation = SmartIdeaConversation.from_dict(
            conv_data, openai_api_key=openai_key, project_identity=project_identity
        )

        # Force complete and generate brief from what we have
        conversation.is_complete = True
        conversation.brief.readiness_score = 80  # Force ready

        # Build context from conversation
        brief = conversation.brief
        metadata["context"] = {
            "description": brief.description or project.description or "User project",
            "problem": brief.problem_statement or "To be defined",
            "features": brief.core_features or ["Core functionality"],
            "technical": brief.technical_requirements or "",
            "target_users": brief.target_users or "General users",
            "constraints": brief.constraints or "",
            "success_criteria": brief.success_criteria or [],
            "scope": brief.scope or "MVP",
        }
        metadata["architect_brief"] = conversation.get_architect_brief()
        metadata["smart_conversation"] = conversation.to_dict()

        # Set phase to 'plan' so Architect runs
        metadata["phase"] = "plan"

        # Use guidance system for task decomposition
        description = brief.description or project.description or "User project"
        guidance = get_guidance()
        complexity = guidance.estimate_complexity(description)
        subtasks = guidance.decompose_task(description, metadata["context"])

        # Set up plan data
        metadata["plan"] = {
            "overview": description,
            "features": brief.core_features or ["Feature analysis in progress..."],
            "architecture": brief.technical_requirements or "To be determined",
            "milestones": [
                "Project setup and scaffolding",
                "Core functionality implementation",
                "Testing and refinement",
                "Final delivery"
            ],
            "risks": ["Scope may need refinement based on complexity"],
            "complexity": complexity,
            "subtasks": [{"id": s.id, "title": s.title, "scope": s.scope} for s in subtasks],
        }

        # Update project
        await project_manager.update_project(
            project_id,
            name=brief.title or project.name,
            description=brief.description or project.description,
            metadata=metadata
        )

    # Redirect to project page (will show planning UI)
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


# ==========================================
# ATLAS 3.0 - Business Analysis Routes
# ==========================================

@router.post("/{project_id}/start-analysis", response_class=HTMLResponse)
async def start_business_analysis(request: Request, project_id: int):
    """Start business analysis - Analyst creates comprehensive Business Brief.

    This is the ATLAS 3.0 flow: Idea Chat -> Business Analysis -> Planning
    """
    from atlas.agents.analyst import AnalystAgent, BusinessBrief

    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}

    # Get the idea from conversation or description
    idea = project.description or ""
    idea_type = None
    conversation_brief = {}

    if metadata.get("smart_conversation"):
        conv_data = metadata["smart_conversation"]
        if conv_data.get("brief"):
            conversation_brief = conv_data["brief"]
            idea = conversation_brief.get("description", idea)
        # Get the detected idea type (printable, document, web, app)
        if conv_data.get("current_question", {}).get("idea_type"):
            idea_type = conv_data["current_question"]["idea_type"]

    # Also check top-level idea_type
    if not idea_type and metadata.get("idea_type"):
        idea_type = metadata["idea_type"]

    # Build rich context for the Analyst
    context = metadata.get("context", {})

    # Pass project_identity as THE source of truth
    project_identity = metadata.get("project_identity")
    if project_identity:
        # Canonical identity - agents MUST respect this
        context["project_identity"] = project_identity
        context["product_type"] = project_identity["product_type"]
        context["product_type_name"] = project_identity["product_type_name"]
        idea = f"[PRODUCT TYPE: {project_identity['product_type_name']} - {project_identity['product_type'].upper()}]\n\n{idea}"
    elif idea_type:
        # Fallback for older projects without project_identity
        context["product_type"] = idea_type.get("type", "unknown")
        context["product_type_name"] = idea_type.get("name", "Product")
        idea = f"[PRODUCT TYPE: {idea_type.get('name', 'Unknown')} - {idea_type.get('type', 'unknown').upper()}]\n\n{idea}"

    # Add conversation brief details - including topic coverage for confidence scoring
    if conversation_brief:
        context["brief"] = conversation_brief  # Pass full brief including topics_covered
        if conversation_brief.get("core_features"):
            context["core_features"] = conversation_brief["core_features"]
        if conversation_brief.get("target_users"):
            context["target_users"] = conversation_brief["target_users"]
        if conversation_brief.get("problem_statement"):
            context["problem_statement"] = conversation_brief["problem_statement"]
        if conversation_brief.get("description"):
            context["description"] = conversation_brief["description"]

    # Update phase to analyzing
    metadata["phase"] = "analyzing"
    await project_manager.update_project(project_id, metadata=metadata)

    try:
        # Create and run Analyst
        analyst = AnalystAgent(
            router=request.app.state.router,
            memory=request.app.state.memory,
            providers=request.app.state.providers
        )

        # Run the analysis
        output = await analyst.process(idea, context=context)

        if output.artifacts and "brief" in output.artifacts:
            brief_data = output.artifacts["brief"]
            metadata["business_brief"] = brief_data
            metadata["phase"] = "brief_review"

            await project_manager.update_project(project_id, metadata=metadata)

            # Return the business brief partial
            return templates.TemplateResponse(
                "partials/business_brief.html",
                {
                    "request": request,
                    "project_id": project_id,
                    "brief": brief_data,
                }
            )
        else:
            # Analysis failed
            metadata["phase"] = "idea"
            metadata["analysis_error"] = output.content
            await project_manager.update_project(project_id, metadata=metadata)

            return templates.TemplateResponse(
                "partials/error.html",
                {
                    "request": request,
                    "error": f"Analysis failed: {output.content}",
                }
            )

    except Exception as e:
        logger.error(f"Business analysis failed for project {project_id}: {e}")
        metadata["phase"] = "idea"
        metadata["analysis_error"] = str(e)
        await project_manager.update_project(project_id, metadata=metadata)

        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": f"Analysis failed: {str(e)}",
            }
        )


@router.get("/{project_id}/business-brief", response_class=HTMLResponse)
async def get_business_brief(request: Request, project_id: int):
    """Get the current business brief for a project."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata or {}
    brief = metadata.get("business_brief")

    return templates.TemplateResponse(
        "partials/business_brief.html",
        {
            "request": request,
            "project_id": project_id,
            "brief": brief,
        }
    )


@router.post("/{project_id}/approve-brief", response_class=HTMLResponse)
async def approve_business_brief(request: Request, project_id: int):
    """Approve the business brief and proceed to planning.

    This also determines which builder to use based on product_type.
    """
    from atlas.agents.builders import get_builder_for_type

    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}

    # Mark brief as approved
    if metadata.get("business_brief"):
        metadata["business_brief"]["approved"] = True
        metadata["business_brief"]["approved_at"] = datetime.now().isoformat()

        # Use project_identity as THE source of truth for builder routing
        project_identity = metadata.get("project_identity", {})
        if project_identity.get("product_type"):
            product_type = project_identity["product_type"].lower()
        else:
            # Fallback to business_brief for older projects
            product_type = metadata["business_brief"].get("product_type", "").lower()

        # Map general types to builder types
        builder_type_map = {
            "printable": "printable_builder",
            "document": "document_builder",
            "web": "web_builder",
            "app": "app_builder",
        }

        builder_type = builder_type_map.get(product_type, "web_builder")  # Default to web

        # Map general types to specific ProjectType enum values for Mason routing
        # Mason expects specific types like "web_spa", "mobile_cross_platform", etc.
        project_type_map = {
            "printable": "printable_planner",  # Default printable type
            "document": "doc_guide",           # Default document type
            "web": "web_spa",                  # Default web type
            "app": "web_spa",                  # Apps default to web SPA (React/Vue)
        }
        specific_project_type = project_type_map.get(product_type, "web_spa")

        # Store builder info for later phases
        metadata["assigned_builder"] = {
            "type": builder_type,
            "product_type": product_type,
            "source": "project_identity" if project_identity.get("product_type") else "business_brief",
            "assigned_at": datetime.now().isoformat(),
        }

        # CRITICAL: Set project_type at top level for Mason routing
        # Mason looks for context["project_type"] to determine what to build
        metadata["project_type"] = specific_project_type
        metadata["project_category"] = product_type  # Keep original category for reference

        # Log the assignment
        logger.info(f"[Kickoff] Project {project_id}: product_type={product_type} -> builder={builder_type} (source: {metadata['assigned_builder']['source']})")

    # Trigger Round Table V2 kickoff
    try:
        from atlas.agents.roundtable_v2 import get_roundtable_v2

        roundtable = get_roundtable_v2(
            router=request.app.state.router,
            memory=getattr(request.app.state, 'memory', None),
            providers=getattr(request.app.state, 'providers', {}),
        )

        idea = project.description or metadata.get("idea", "")
        session = await roundtable.kickoff(project_id, metadata["business_brief"], idea)

        # Store Round Table session in metadata
        metadata["roundtable"] = session.to_dict()

        # Store kickoff_plan at top level for easy access
        if session.kickoff_plan:
            metadata["kickoff_plan"] = session.kickoff_plan

        # Log specialists spawned
        specialist_names = [s.name for s in session.specialists] if session.specialists else []
        logger.info(f"[Kickoff] Round Table V2 complete. Specialists: {specialist_names}")
        logger.info(f"[Kickoff] Deliverables: {len(session.deliverables)}, Timeline phases: {len(session.timeline)}")
        logger.info(f"[Kickoff] Tech stack: {session.kickoff_plan.get('tech_stack', {}).get('framework', 'N/A')}")

    except Exception as e:
        logger.error(f"[Kickoff] Round Table V2 failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Continue anyway - Round Table is enhancement, not blocker

    # Move to planning phase
    metadata["phase"] = "plan"

    await project_manager.update_project(project_id, metadata=metadata)

    # Redirect to project page to start planning
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


# NOTE: run_kickoff route removed - functionality merged into RoundTableV2.kickoff()
# The kickoff_plan is now created as part of approve_business_brief flow


@router.post("/{project_id}/override-brief", response_class=HTMLResponse)
async def override_business_brief(request: Request, project_id: int):
    """Override a no-go or needs-research recommendation and proceed anyway.

    User is overriding the recommendation but we still assign the builder.
    """
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}

    # Mark brief as overridden
    if metadata.get("business_brief"):
        metadata["business_brief"]["overridden"] = True
        metadata["business_brief"]["overridden_at"] = datetime.now().isoformat()
        metadata["business_brief"]["original_recommendation"] = metadata["business_brief"].get("recommendation")

        # Use project_identity as THE source of truth for builder routing
        project_identity = metadata.get("project_identity", {})
        if project_identity.get("product_type"):
            product_type = project_identity["product_type"].lower()
        else:
            # Fallback to business_brief for older projects
            product_type = metadata["business_brief"].get("product_type", "").lower()

        builder_type_map = {
            "printable": "printable_builder",
            "document": "document_builder",
            "web": "web_builder",
            "app": "app_builder",
        }
        builder_type = builder_type_map.get(product_type, "web_builder")

        metadata["assigned_builder"] = {
            "type": builder_type,
            "product_type": product_type,
            "source": "project_identity" if project_identity.get("product_type") else "business_brief",
            "assigned_at": datetime.now().isoformat(),
            "overridden": True,  # Flag that recommendation was overridden
        }

        logger.info(f"[Kickoff] Project {project_id} (overridden): product_type={product_type} -> builder={builder_type} (source: {metadata['assigned_builder']['source']})")

    # Trigger Round Table V2 kickoff even for overridden briefs
    try:
        from atlas.agents.roundtable_v2 import get_roundtable_v2

        roundtable = get_roundtable_v2(
            router=request.app.state.router,
            memory=getattr(request.app.state, 'memory', None),
            providers=getattr(request.app.state, 'providers', {}),
        )

        idea = project.description or metadata.get("idea", "")
        session = await roundtable.kickoff(project_id, metadata["business_brief"], idea)

        # Store Round Table session in metadata
        metadata["roundtable"] = session.to_dict()

        specialist_names = [s.name for s in session.specialists] if session.specialists else []
        logger.info(f"[Kickoff] Round Table V2 (overridden) complete. Specialists: {specialist_names}")

    except Exception as e:
        logger.error(f"[Kickoff] Round Table V2 failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Move to planning phase
    metadata["phase"] = "plan"

    await project_manager.update_project(project_id, metadata=metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/run-qc", response_class=HTMLResponse)
async def run_qc_check(request: Request, project_id: int):
    """Run QC check on the business brief before approval.

    QC Flow:
    - Attempt 1: Warning + fix notes -> return to agent
    - Attempt 2: Still broken -> BLOCK -> escalate to user
    """
    from atlas.agents.qc import QCAgent

    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}
    brief_data = metadata.get("business_brief", {})

    if not brief_data:
        raise HTTPException(status_code=400, detail="No business brief to check")

    # Determine attempt number based on previous QC
    previous_qc = metadata.get("qc_report", {})
    if previous_qc and previous_qc.get("verdict") == "needs_revision":
        # This is a retry after issues were found
        attempt = previous_qc.get("attempt", 1) + 1
    else:
        attempt = 1

    # Initialize QC agent with router and providers for LLM evaluation
    qc_agent = QCAgent(
        router=request.app.state.router,
        memory=getattr(request.app.state, 'memory', None),
        providers=getattr(request.app.state, 'providers', {}),
    )
    idea = project.description or metadata.get("idea", "")

    try:
        qc_report = await qc_agent.check_business_brief(brief_data, idea, attempt=attempt)

        # Store QC report in metadata
        metadata["qc_report"] = qc_report.to_dict()
        metadata["qc_report"]["run_at"] = datetime.now().isoformat()
        await project_manager.update_project(project_id, metadata=metadata)

        # Return QC report partial
        return templates.TemplateResponse(
            "partials/qc_report.html",
            {
                "request": request,
                "project_id": project_id,
                "qc_type": "brief",
                "qc_endpoint": f"/projects/{project_id}/run-qc",
                "qc_container": "#qc-report-container",
                "qc_report": qc_report.to_dict(),
            }
        )
    except Exception as e:
        logger.error(f"QC check failed: {e}")
        return templates.TemplateResponse(
            "partials/qc_report.html",
            {
                "request": request,
                "project_id": project_id,
                "qc_type": "brief",
                "qc_endpoint": f"/projects/{project_id}/run-qc",
                "qc_container": "#qc-report-container",
                "qc_report": {
                    "verdict": "error",
                    "verdict_reason": f"QC check failed: {str(e)}",
                    "checks_passed": [],
                    "issues": [],
                },
            }
        )


@router.get("/{project_id}/qc-report", response_class=HTMLResponse)
async def get_qc_report(request: Request, project_id: int):
    """Get the current QC report for a project."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}
    qc_report = metadata.get("qc_report")

    return templates.TemplateResponse(
        "partials/qc_report.html",
        {
            "request": request,
            "project_id": project_id,
            "qc_report": qc_report,
        }
    )


@router.post("/{project_id}/qc-plan", response_class=HTMLResponse)
async def run_qc_plan(request: Request, project_id: int):
    """Run QC check on the build plan."""
    from atlas.agents.qc import QCAgent

    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}
    build_plan = metadata.get("build_plan", {})

    if not build_plan:
        return templates.TemplateResponse(
            "partials/qc_report.html",
            {
                "request": request,
                "project_id": project_id,
                "qc_type": "plan",
                "qc_endpoint": f"/projects/{project_id}/qc-plan",
                "qc_container": "#plan-qc-report-container",
                "qc_report": {
                    "verdict": "error",
                    "summary": "No build plan to check. Generate a build plan first.",
                    "checks_passed": [],
                    "issues": [],
                },
            }
        )

    # Initialize QC agent
    qc_agent = QCAgent(
        router=request.app.state.router,
        memory=getattr(request.app.state, 'memory', None),
        providers=getattr(request.app.state, 'providers', {}),
    )

    try:
        # Get the brief for context
        brief_data = metadata.get("business_brief", {})

        # Check the build plan
        qc_report = await qc_agent.check_plan(build_plan, brief_data, attempt=1)

        # Store QC report
        metadata["plan_qc_report"] = qc_report.to_dict()
        metadata["plan_qc_report"]["run_at"] = datetime.now().isoformat()
        await project_manager.update_project(project_id, metadata=metadata)

        return templates.TemplateResponse(
            "partials/qc_report.html",
            {
                "request": request,
                "project_id": project_id,
                "qc_type": "plan",
                "qc_endpoint": f"/projects/{project_id}/qc-plan",
                "qc_container": "#plan-qc-report-container",
                "qc_report": qc_report.to_dict(),
            }
        )
    except Exception as e:
        logger.error(f"QC plan check failed: {e}")
        return templates.TemplateResponse(
            "partials/qc_report.html",
            {
                "request": request,
                "project_id": project_id,
                "qc_type": "plan",
                "qc_endpoint": f"/projects/{project_id}/qc-plan",
                "qc_container": "#plan-qc-report-container",
                "qc_report": {
                    "verdict": "error",
                    "summary": f"QC check failed: {str(e)}",
                    "checks_passed": [],
                    "issues": [],
                },
            }
        )


@router.post("/{project_id}/qc-build", response_class=HTMLResponse)
async def run_qc_build(request: Request, project_id: int):
    """Run QC check on the build output."""
    from atlas.agents.qc import QCAgent

    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}
    build = metadata.get("build", {})

    # Check if there's actual build output
    has_output = build.get("output") or build.get("agent_output", {}).get("content")
    if not has_output:
        return templates.TemplateResponse(
            "partials/qc_report.html",
            {
                "request": request,
                "project_id": project_id,
                "qc_type": "build",
                "qc_endpoint": f"/projects/{project_id}/qc-build",
                "qc_container": "#build-qc-report-container",
                "qc_report": {
                    "verdict": "error",
                    "summary": "No build output to check. Complete the build first.",
                    "checks_passed": [],
                    "issues": [],
                },
            }
        )

    # Initialize QC agent
    qc_agent = QCAgent(
        router=request.app.state.router,
        memory=getattr(request.app.state, 'memory', None),
        providers=getattr(request.app.state, 'providers', {}),
    )

    try:
        # Get the brief for context
        brief_data = metadata.get("business_brief", {})
        if not brief_data:
            brief_data = metadata.get("smart_conversation", {}).get("brief", {})

        # Get kickoff_plan for scope, tech stack, priorities
        kickoff_plan = metadata.get("kickoff_plan", {})

        # Check revision count - be more lenient after multiple attempts
        revision_count = build.get("revision_count", 0)

        # Check the build output - pass the entire build dict and kickoff_plan
        qc_report = await qc_agent.check_build(
            build, brief_data, kickoff_plan=kickoff_plan, attempt=1
        )
        qc_dict = qc_report.to_dict()

        # After 3+ revisions, be more lenient
        if revision_count >= 3:
            issues = qc_dict.get("issues", [])
            critical_issues = [i for i in issues if isinstance(i, dict) and i.get("severity") == "critical"]

            if not critical_issues:
                # No critical issues after 3 revisions - pass with notes
                qc_dict["verdict"] = "pass_with_notes"
                qc_dict["verdict_reason"] = f"Passed after {revision_count} revisions. Minor improvements could still be made, but the product is sellable."
                qc_dict["revision_count"] = revision_count
            elif revision_count >= 5:
                # After 5 revisions, just pass and note the remaining issues
                qc_dict["verdict"] = "pass_with_notes"
                qc_dict["verdict_reason"] = f"Approved after {revision_count} revision attempts. Some issues remain but further iteration may not be productive. Consider manual review."
                qc_dict["revision_count"] = revision_count

        # Store QC report
        metadata["build_qc_report"] = qc_dict
        metadata["build_qc_report"]["run_at"] = datetime.now().isoformat()
        await project_manager.update_project(project_id, metadata=metadata)

        return templates.TemplateResponse(
            "partials/qc_report.html",
            {
                "request": request,
                "project_id": project_id,
                "qc_type": "build",
                "qc_endpoint": f"/projects/{project_id}/qc-build",
                "qc_container": "#build-qc-report-container",
                "qc_report": qc_dict,
            }
        )
    except Exception as e:
        logger.error(f"QC build check failed: {e}")
        return templates.TemplateResponse(
            "partials/qc_report.html",
            {
                "request": request,
                "project_id": project_id,
                "qc_type": "build",
                "qc_endpoint": f"/projects/{project_id}/qc-build",
                "qc_container": "#build-qc-report-container",
                "qc_report": {
                    "verdict": "error",
                    "summary": f"QC check failed: {str(e)}",
                    "checks_passed": [],
                    "issues": [],
                },
            }
        )


@router.get("/{project_id}/conversation", response_class=HTMLResponse)
async def get_conversation_log(request: Request, project_id: int):
    """Get the agent conversation log for a project."""
    from atlas.agents.roundtable_v2 import get_roundtable_v2 as get_roundtable

    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}

    # Get conversation from Round Table V2 or metadata
    roundtable = get_roundtable()
    session = roundtable.get_session(project_id)
    specialists = []

    if session:
        conversation = session.conversation.to_dict()
        # V2 has specialists (list), convert to expert format for backward compat
        specialists = [s.to_dict() for s in session.specialists] if session.specialists else []
        expert = specialists[0] if specialists else None
    else:
        # Fall back to stored data
        rt_data = metadata.get("roundtable", {})
        conversation = rt_data.get("conversation", {"messages": [], "participants": []})
        # V2 stores specialists, V1 stores custom_expert
        specialists = rt_data.get("specialists", [])
        expert = specialists[0] if specialists else rt_data.get("custom_expert")

    return templates.TemplateResponse(
        "partials/conversation_log.html",
        {
            "request": request,
            "project_id": project_id,
            "conversation": conversation,
            "expert": expert,
            "specialists": specialists,
            "project_name": project.name,
        }
    )


@router.get("/{project_id}/roundtable", response_class=HTMLResponse)
async def get_roundtable_status(request: Request, project_id: int):
    """Get Round Table status and participants."""
    from atlas.agents.roundtable_v2 import get_roundtable_v2 as get_roundtable

    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}

    roundtable = get_roundtable()
    session = roundtable.get_session(project_id)

    if session:
        rt_data = session.to_dict()
    else:
        rt_data = metadata.get("roundtable", {})

    return templates.TemplateResponse(
        "partials/roundtable_status.html",
        {
            "request": request,
            "project_id": project_id,
            "roundtable": rt_data,
            "project_name": project.name,
        }
    )


@router.post("/{project_id}/start-planning", response_class=HTMLResponse)
async def start_planning(request: Request, project_id: int):
    """Start the planning phase - Planner creates build plan."""
    from atlas.agents.planner import PlannerAgent
    from atlas.agents.roundtable_v2 import get_roundtable_v2 as get_roundtable

    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}
    brief = metadata.get("business_brief", {})

    if not brief:
        raise HTTPException(status_code=400, detail="No Business Brief found")

    # Get Round Table context
    roundtable = get_roundtable()
    session = roundtable.get_session(project_id)
    context = {
        "brief": brief,
    }

    # Pass project_identity as THE source of truth
    if metadata.get("project_identity"):
        context["project_identity"] = metadata["project_identity"]

    if session:
        context["conversation"] = session.conversation.format_for_context()

    # Create planner and generate plan
    planner = PlannerAgent(
        router=request.app.state.router,
        memory=getattr(request.app.state, 'memory', None),
        project_id=project_id,
        providers=getattr(request.app.state, 'providers', {}),
    )

    try:
        result = await planner.process("Create build plan from Brief", context=context)

        # Store plan in metadata
        if result.artifacts.get("plan"):
            metadata["build_plan"] = result.artifacts["plan"]
            metadata["phase"] = "plan_review"
            await project_manager.update_project(project_id, metadata=metadata)

        # Return plan display
        return templates.TemplateResponse(
            "partials/build_plan.html",
            {
                "request": request,
                "project_id": project_id,
                "plan": result.artifacts.get("plan", {}),
            }
        )

    except Exception as e:
        logger.error(f"Planning failed: {e}")
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": f"Planning failed: {str(e)}",
            }
        )


@router.post("/{project_id}/re-analyze", response_class=HTMLResponse)
async def re_analyze_idea(request: Request, project_id: int, additional_context: str = Form("")):
    """Re-run business analysis with additional context."""
    from atlas.agents.analyst import AnalystAgent

    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}

    # Get the idea and product type
    idea = project.description or ""
    idea_type = None
    conversation_brief = {}

    if metadata.get("smart_conversation"):
        conv_data = metadata["smart_conversation"]
        if conv_data.get("brief"):
            conversation_brief = conv_data["brief"]
            idea = conversation_brief.get("description", idea)
        if conv_data.get("current_question", {}).get("idea_type"):
            idea_type = conv_data["current_question"]["idea_type"]

    if not idea_type and metadata.get("idea_type"):
        idea_type = metadata["idea_type"]

    # Build context with project_identity as source of truth
    context = metadata.get("context", {})

    # Pass project_identity as THE source of truth
    project_identity = metadata.get("project_identity")
    if project_identity:
        context["project_identity"] = project_identity
        context["product_type"] = project_identity["product_type"]
        context["product_type_name"] = project_identity["product_type_name"]
        idea = f"[PRODUCT TYPE: {project_identity['product_type_name']} - {project_identity['product_type'].upper()}]\n\n{idea}"
    elif idea_type:
        # Fallback for older projects
        context["product_type"] = idea_type.get("type", "unknown")
        context["product_type_name"] = idea_type.get("name", "Product")
        idea = f"[PRODUCT TYPE: {idea_type.get('name', 'Unknown')} - {idea_type.get('type', 'unknown').upper()}]\n\n{idea}"

    if conversation_brief:
        if conversation_brief.get("core_features"):
            context["core_features"] = conversation_brief["core_features"]
        if conversation_brief.get("target_audience"):
            context["target_audience"] = conversation_brief["target_audience"]

    if additional_context:
        context["additional_research"] = additional_context
        # Also add it directly to the idea for better visibility to analyst
        idea = f"{idea}\n\nADDITIONAL CONTEXT FROM USER:\n{additional_context}"

    # Update phase
    metadata["phase"] = "analyzing"
    await project_manager.update_project(project_id, metadata=metadata)

    try:
        analyst = AnalystAgent(
            router=request.app.state.router,
            memory=request.app.state.memory,
            providers=request.app.state.providers
        )

        output = await analyst.process(idea, context=context)

        if output.artifacts and "brief" in output.artifacts:
            brief_data = output.artifacts["brief"]
            metadata["business_brief"] = brief_data
            metadata["phase"] = "brief_review"

            # Clear old QC report since we have a new brief
            if "qc_report" in metadata:
                del metadata["qc_report"]

            # Track tokens
            tokens = metadata.get("tokens", {"total": 0, "by_agent": {}})
            analyst_tokens = output.tokens_used
            tokens["total"] += analyst_tokens
            tokens["by_agent"]["analyst"] = tokens.get("by_agent", {}).get("analyst", 0) + analyst_tokens
            metadata["tokens"] = tokens

            await project_manager.update_project(project_id, metadata=metadata)

            # Redirect to project page to show updated brief
            return RedirectResponse(url=f"/projects/{project_id}", status_code=303)
        else:
            metadata["phase"] = "brief_review"  # Stay in review with previous brief
            metadata["reanalysis_error"] = output.content
            await project_manager.update_project(project_id, metadata=metadata)

            # Redirect back - error will be shown via metadata
            return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

    except Exception as e:
        logger.error(f"Re-analysis failed for project {project_id}: {e}")
        metadata["phase"] = "brief_review"
        metadata["reanalysis_error"] = str(e)
        await project_manager.update_project(project_id, metadata=metadata)

        # Redirect back - error will be shown via metadata
        return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/revise-idea", response_class=HTMLResponse)
async def revise_idea(request: Request, project_id: int):
    """Go back to idea conversation to revise the concept."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}

    # Reset to idea phase
    metadata["phase"] = "idea"

    # Clear the existing conversation completion state so user can continue
    if metadata.get("smart_conversation"):
        metadata["smart_conversation"]["is_complete"] = False

    await project_manager.update_project(project_id, metadata=metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


# ==========================================
# End ATLAS 3.0 Business Analysis Routes
# ==========================================


@router.post("/{project_id}/start-planning", response_class=HTMLResponse)
async def start_planning(
    request: Request,
    project_id: int,
    description: str = Form(""),
    problem: str = Form(""),
    features: str = Form(""),
    technical: str = Form(""),
):
    """Start the planning phase - Sketch creates a structured Spec (Requirements + Design + Tasks).

    This implements spec-driven development inspired by Kiro:
    - Requirements in EARS format with acceptance criteria
    - Design documentation with architecture and components
    - Tasks with requirement traceability
    """
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get or detect project type
    metadata = project.metadata or {}
    project_type = metadata.get("project_type")
    project_category = metadata.get("project_category")
    project_type_config = metadata.get("project_type_config")

    # Re-detect if not present (for older projects)
    if not project_type:
        detector = ProjectTypeDetector()
        from atlas.projects.project_types import ProjectType
        detected_type, detected_category, confidence = detector.detect(description or project.description)
        project_type = detected_type.value
        project_category = detected_category.value
        type_config = detector.get_config(detected_type)
        if type_config:
            project_type_config = {
                "name": type_config.name,
                "description": type_config.description,
                "suggested_stack": type_config.suggested_stack,
                "build_approach": type_config.build_approach,
                "verification_focus": type_config.verification_focus,
                "key_questions": type_config.key_questions,
            }

    # Build context for spec generation with project type
    feature_list = [f.strip() for f in features.split('\n') if f.strip()]

    context = {
        "description": description,
        "problem": problem,
        "features": feature_list,
        "technical": technical,
        "project_type": project_type,
        "project_category": project_category,
        "project_type_config": project_type_config,
    }

    # Use guidance system for complexity estimation
    guidance = get_guidance()
    complexity = guidance.estimate_complexity(description)

    # Initialize token tracking
    tokens = project.metadata.get("tokens", {"total": 0, "by_agent": {}}) if project.metadata else {"total": 0, "by_agent": {}}

    # Get Governor routing decision
    governor = get_governor(
        budget_limit=5.0,
        budget_used=tokens.get("total", 0) * 0.00001,
        prefer_local=False,
    )

    routing_decision = governor.route(
        task=description or "Generate project specification",
        agent_name="architect",
        context=context,
    )

    # Build the idea string for spec generation
    # Use form description if provided, otherwise use project description
    idea = description.strip() if description.strip() else (project.description or project.name or "")
    if problem:
        idea += f"\n\nProblem: {problem}"

    # Generate structured spec using SpecGenerator
    spec_generator = SpecGenerator(openai_api_key=_get_openai_key())
    spec_data = {}

    try:
        spec = await spec_generator.generate_from_idea(idea, context)

        # Convert spec to serializable format for storage
        spec_data = {
            "name": spec.name,
            "description": spec.description,
            "complexity": complexity,
            "routing": routing_decision.to_dict(),
            "requirements": [
                {
                    "id": req.id,
                    "title": req.title,
                    "description": req.description,
                    "type": req.type.value,
                    "priority": req.priority.value,
                    "user_story": req.user_story,
                    "acceptance_criteria": [
                        {"id": ac.id, "description": ac.description, "verified": ac.verified}
                        for ac in req.acceptance_criteria
                    ],
                }
                for req in spec.requirements
            ],
            "design": {
                "title": spec.design.title if spec.design else "",
                "overview": spec.design.overview if spec.design else "",
                "architecture": spec.design.architecture if spec.design else "",
                "components": [
                    {
                        "name": comp.name,
                        "description": comp.description,
                        "responsibilities": comp.responsibilities,
                        "interfaces": comp.interfaces,
                    }
                    for comp in (spec.design.components if spec.design else [])
                ],
                "data_model": spec.design.data_model if spec.design else "",
                "api_design": spec.design.api_design if spec.design else "",
                "error_handling": spec.design.error_handling if spec.design else "",
                "testing_strategy": spec.design.testing_strategy if spec.design else "",
            },
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "requirement_ids": task.requirement_ids,
                    "files_to_modify": task.files_to_modify,
                    "estimated_effort": task.estimated_effort,
                }
                for task in (spec.tasks.tasks if spec.tasks else [])
            ],
            "tech_stack": spec.tech_stack.to_dict() if spec.tech_stack else None,
        }

        # Add tech stack to context for Mason
        if spec.tech_stack:
            context["tech_stack"] = spec.tech_stack.to_dict()

        # Estimate tokens used (rough estimate for spec generation)
        estimated_tokens = len(idea.split()) * 10  # Rough estimate
        tokens["total"] += estimated_tokens
        tokens["by_agent"]["architect"] = tokens.get("by_agent", {}).get("architect", 0) + estimated_tokens

    except Exception as e:
        spec_data["error"] = str(e)
        # Notify via Buzz about the error
        buzz = get_buzz()
        await buzz.notify_error(
            project_id=project_id,
            project_name=project.name,
            agent="Sketch",
            error=str(e)
        )
        # Fallback to basic spec structure
        spec_data = _create_fallback_spec(description, problem, feature_list, technical, complexity)

    new_metadata = project.metadata.copy() if project.metadata else {}
    new_metadata["phase"] = "plan_review"
    new_metadata["spec"] = spec_data
    new_metadata["context"] = context
    new_metadata["tokens"] = tokens

    await project_manager.update_project(
        project_id,
        description=description,
        metadata=new_metadata
    )

    # Notify via Buzz that Sketch finished spec generation
    buzz = get_buzz()
    await buzz.notify_sketch_complete(
        project_id=project_id,
        project_name=project.name,
        tokens_used=tokens.get("total", 0)
    )

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


def _create_fallback_spec(description: str, problem: str, features: list, technical: str, complexity: str) -> dict:
    """Create a fallback spec when AI generation fails."""
    requirements = []
    for i, feature in enumerate(features, 1):
        requirements.append({
            "id": f"REQ-{i:03d}",
            "title": feature[:50],
            "description": f"The system shall {feature.lower()}",
            "type": "ubiquitous",
            "priority": "medium",
            "user_story": f"As a user, I want {feature.lower()}, so that I can benefit from this feature",
            "acceptance_criteria": [
                {"id": f"AC-{i:03d}-01", "description": f"Verify that {feature.lower()} works correctly", "verified": False}
            ],
        })

    tasks = [
        {
            "id": "TASK-001",
            "title": "Project Setup",
            "description": "Initialize project structure and dependencies",
            "status": "pending",
            "priority": "high",
            "requirement_ids": [],
            "files_to_modify": [],
            "estimated_effort": "1-2 hours",
        }
    ]
    for i, req in enumerate(requirements, 2):
        tasks.append({
            "id": f"TASK-{i:03d}",
            "title": f"Implement {req['title']}",
            "description": f"Implement functionality for: {req['description']}",
            "status": "pending",
            "priority": req["priority"],
            "requirement_ids": [req["id"]],
            "files_to_modify": [],
            "estimated_effort": "2-4 hours",
        })

    return {
        "name": description[:100],
        "description": description,
        "complexity": complexity,
        "requirements": requirements,
        "design": {
            "title": f"Design: {description[:50]}",
            "overview": description,
            "architecture": technical if technical else "To be determined based on requirements analysis.",
            "components": [],
            "data_model": "",
            "api_design": "",
            "error_handling": "Standard error handling with appropriate logging",
            "testing_strategy": "Unit tests for core functionality, integration tests for APIs",
        },
        "tasks": tasks,
        "fallback": True,
    }


def _format_spec_for_review(spec: dict) -> str:
    """Format a spec dict into readable text for agent review."""
    lines = []
    lines.append("# Project Specification")
    lines.append("")

    # Requirements section
    requirements = spec.get("requirements", [])
    if requirements:
        lines.append("## Requirements (EARS Format)")
        lines.append("")
        for req in requirements:
            lines.append(f"### {req['id']}: {req['title']}")
            if req.get("user_story"):
                lines.append(f"**User Story:** {req['user_story']}")
            lines.append(f"**Type:** {req.get('type', 'ubiquitous')}")
            lines.append(f"**Priority:** {req.get('priority', 'medium')}")
            lines.append(f"**Requirement:** {req['description']}")
            if req.get("acceptance_criteria"):
                lines.append("**Acceptance Criteria:**")
                for ac in req["acceptance_criteria"]:
                    lines.append(f"  - {ac['id']}: {ac['description']}")
            lines.append("")

    # Design section
    design = spec.get("design", {})
    if design:
        lines.append("## Design")
        lines.append("")
        if design.get("overview"):
            lines.append(f"**Overview:** {design['overview']}")
            lines.append("")
        if design.get("architecture"):
            lines.append(f"**Architecture:** {design['architecture']}")
            lines.append("")
        if design.get("components"):
            lines.append("**Components:**")
            for comp in design["components"]:
                lines.append(f"- **{comp['name']}**: {comp.get('description', '')}")
                if comp.get("responsibilities"):
                    for r in comp["responsibilities"]:
                        lines.append(f"  - {r}")
            lines.append("")
        if design.get("testing_strategy"):
            lines.append(f"**Testing Strategy:** {design['testing_strategy']}")
            lines.append("")

    # Tasks section
    tasks = spec.get("tasks", [])
    if tasks:
        lines.append("## Implementation Tasks")
        lines.append("")
        for task in tasks:
            req_ids = ", ".join(task.get("requirement_ids", [])) if task.get("requirement_ids") else "N/A"
            lines.append(f"### {task['id']}: {task['title']}")
            lines.append(f"**Priority:** {task.get('priority', 'medium')}")
            lines.append(f"**Implements:** {req_ids}")
            lines.append(f"**Description:** {task['description']}")
            if task.get("estimated_effort"):
                lines.append(f"**Estimated Effort:** {task['estimated_effort']}")
            lines.append("")

    return "\n".join(lines)


@router.post("/{project_id}/start-sprint-meeting", response_class=HTMLResponse)
async def start_sprint_meeting(request: Request, project_id: int):
    """Start a sprint meeting where agents review the plan."""
    project_manager = request.app.state.project_manager
    agent_manager = request.app.state.agent_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}
    tokens = new_metadata.get("tokens", {"total": 0, "by_agent": {}})

    # Get the spec to review (or fall back to old plan format)
    spec = new_metadata.get("spec", {})
    plan = new_metadata.get("plan", {})
    context = new_metadata.get("context", {})

    # Build a formatted spec content for review
    if spec:
        spec_content = _format_spec_for_review(spec)
    else:
        # Fallback to old plan format
        spec_content = plan.get("raw_plan", plan.get("agent_output", {}).get("content", ""))

    if agent_manager:
        try:
            # Conduct sprint meeting
            sprint_meeting = get_sprint_meeting(agent_manager)
            meeting_result = await sprint_meeting.conduct_meeting(
                plan=spec_content,
                context=context,
                include_agents=["tinker", "oracle", "launch"]
            )

            # Update token counts
            tokens["total"] += meeting_result.total_tokens
            tokens["by_agent"]["sprint_meeting"] = meeting_result.total_tokens

            # Store meeting results
            new_metadata["sprint_meeting"] = meeting_result.to_dict()
            new_metadata["phase"] = "sprint_meeting"
            new_metadata["tokens"] = tokens

        except Exception as e:
            new_metadata["sprint_meeting"] = {
                "error": str(e),
                "reviews": [],
                "overall_verdict": "concerns",
                "can_proceed": True,
                "summary": f"Meeting error: {str(e)}"
            }
            new_metadata["phase"] = "sprint_meeting"

            # Notify about error
            buzz = get_buzz()
            await buzz.notify_error(
                project_id=project_id,
                project_name=project.name,
                agent="Sprint Meeting",
                error=str(e)
            )
    else:
        # Demo mode - simulated meeting
        new_metadata["sprint_meeting"] = {
            "reviews": [
                {
                    "agent_name": "tinker",
                    "agent_icon": "🛠️",
                    "verdict": "approved",
                    "summary": "Plan looks implementable. Clear requirements and structure.",
                    "concerns": [],
                    "questions": [],
                    "suggestions": ["Consider adding error handling details"],
                    "tokens_used": 0,
                },
                {
                    "agent_name": "oracle",
                    "agent_icon": "🔮",
                    "verdict": "approved",
                    "summary": "Testable plan with clear success criteria.",
                    "concerns": [],
                    "questions": [],
                    "suggestions": ["Add specific test cases for edge cases"],
                    "tokens_used": 0,
                },
                {
                    "agent_name": "launch",
                    "agent_icon": "📤",
                    "verdict": "approved",
                    "summary": "Deployment path is clear. No blockers identified.",
                    "concerns": [],
                    "questions": [],
                    "suggestions": [],
                    "tokens_used": 0,
                },
            ],
            "overall_verdict": "approved",
            "summary": "All agents approve the plan.",
            "can_proceed": True,
            "total_tokens": 0,
        }
        new_metadata["phase"] = "sprint_meeting"

    await project_manager.update_project(project_id, metadata=new_metadata)
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/approve-plan", response_class=HTMLResponse)
async def approve_plan(request: Request, project_id: int, build_type: str = Form("static_html")):
    """Approve the spec and move to build phase - execute tasks from spec."""
    project_manager = request.app.state.project_manager
    agent_manager = request.app.state.agent_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}
    tokens = new_metadata.get("tokens", {"total": 0, "by_agent": {}})

    # Get spec and context
    spec = new_metadata.get("spec", {})
    context = new_metadata.get("context", {})
    tasks = spec.get("tasks", [])

    # Add project_identity as THE source of truth
    if new_metadata.get("project_identity"):
        context["project_identity"] = new_metadata["project_identity"]

    # Add project type info to context for agents (legacy support)
    context["project_type"] = new_metadata.get("project_type")
    context["project_category"] = new_metadata.get("project_category")
    context["project_type_config"] = new_metadata.get("project_type_config")

    # Add spec to context for Mason to reference
    context["spec"] = spec

    # Add build_type from user selection to context for Mason
    context["build_type"] = build_type
    logger.info(f"[Build] User selected build_type: {build_type}")

    # Add team chat summary if available (resolved concerns)
    if "team_chat" in new_metadata:
        team_chat = new_metadata["team_chat"]
        if "resolved_concerns" in team_chat:
            context["team_chat_summary"] = "\n".join(team_chat["resolved_concerns"])
        if "user_clarifications" in team_chat:
            context["user_clarifications"] = team_chat["user_clarifications"]

    # Get Governor routing decision for Mason
    governor = get_governor(
        budget_limit=5.0,
        budget_used=tokens.get("total", 0) * 0.00001,
        prefer_local=False,
    )

    routing_decision = governor.route(
        task=project.description or "Build the project",
        agent_name="mason",
        context=context,
    )

    # Initialize build tracking with task list from spec
    new_metadata["phase"] = "build"
    new_metadata["build"] = {
        "status": "in_progress",
        "progress": 0,
        "routing": routing_decision.to_dict(),
        "current_task_index": 0,
        "tasks_completed": [],
        "total_tasks": len(tasks),
    }

    await project_manager.update_project(project_id, metadata=new_metadata)

    # If we have an agent manager, run the Mason with spec-driven tasks
    if agent_manager:
        try:
            # Initialize variables that may be used later
            mason_tokens = 0
            regeneration_attempts = 0
            regeneration_history = []

            # Build context from spec for the Mason
            spec_content = _format_spec_for_review(spec)
            requirements = spec.get("requirements", [])
            design = spec.get("design", {})

            # Build task list for the prompt
            task_list = ""
            for i, task in enumerate(tasks, 1):
                req_refs = ", ".join(task.get("requirement_ids", [])) if task.get("requirement_ids") else ""
                task_list += f"{i}. [{task['id']}] {task['title']}"
                if req_refs:
                    task_list += f" (implements: {req_refs})"
                task_list += f"\n   {task['description']}\n"

            task_prompt = f"""Implement this project based on the approved specification.

PROJECT: {project.description}

DESIGN OVERVIEW:
{design.get('overview', 'No overview provided')}

ARCHITECTURE:
{design.get('architecture', 'Standard architecture')}

TASKS TO IMPLEMENT (in order):
{task_list}

TECHNICAL REQUIREMENTS:
{context.get('technical', 'Use best practices')}

For each task:
1. Implement the functionality described
2. Follow the design patterns specified
3. Ensure acceptance criteria from requirements are met
4. Add appropriate error handling and logging

Build the solution step by step, working through each task."""

            # Check if this is a planner/printable product - use templates for guaranteed quality
            from atlas.templates.planner_builder import is_planner_request, build_planner_direct
            # Check multiple sources for planner detection (description may have moved to spec)
            project_desc = project.description or ""
            project_name = project.name or ""
            spec_desc = spec.get("description", "")
            combined_text = f"{project_name} {project_desc} {spec_desc}"
            print(f"[DEBUG] Checking planner: name='{project_name}', desc='{project_desc[:30]}', spec='{spec_desc[:30]}' -> {is_planner_request(combined_text)}")

            if is_planner_request(combined_text):
                # Use template-based generation for planners
                print("[DEBUG] Using template system for planner!")
                logger.info("[Build] Using template system for planner product")

                # Extract customization hints from combined text
                color_scheme = "pastel_blue"  # default
                text_lower = combined_text.lower()
                if "pink" in text_lower or "rose" in text_lower:
                    color_scheme = "pastel_pink"
                elif "green" in text_lower or "nature" in text_lower:
                    color_scheme = "pastel_green"
                elif "lavender" in text_lower or "purple" in text_lower:
                    color_scheme = "pastel_lavender"
                elif "peach" in text_lower or "warm" in text_lower:
                    color_scheme = "pastel_peach"
                elif "minimalist" in text_lower or "minimal" in text_lower:
                    color_scheme = "minimalist"
                elif "ocean" in text_lower or "blue" in text_lower:
                    color_scheme = "ocean"

                # Generate using template
                html_content = build_planner_direct(
                    title=project.name or "Weekly Planner",
                    color_scheme=color_scheme,
                    year="2026",
                )

                # Create mock mason output with the template result
                from atlas.agents.base import AgentOutput
                from ..utils import parse_code_blocks
                from atlas.assembly.code_assembler import assemble_code
                from atlas.assembly.validator import validate_code
                from atlas.assembly.html_expander import expand_document_html

                mason_output = AgentOutput(
                    content=f"## Summary\nGenerated premium weekly planner using professional template.\n\n## Files\n\n### `planner.html`\n```html\n{html_content}\n```\n\n## How to Run\nOpen planner.html in a browser and print to PDF.",
                    tokens_used=0,
                )

                # Process template output (should always pass validation)
                extracted_files = parse_code_blocks(mason_output.content)
                assembly_result = assemble_code(extracted_files)
                assembled_files = assembly_result.files
                assembled_files = expand_document_html(assembled_files)
                validation_result = validate_code(assembled_files, mason_output.content)
                regeneration_attempts = 0
                regeneration_history = []
                mason_tokens = 0  # Template-based, no LLM tokens used

            else:
                # Standard Mason build for non-planner products
                # With auto-regeneration on validation failures
                from atlas.agents.base import AgentOutput
                from ..utils import parse_code_blocks
                from atlas.assembly.code_assembler import assemble_code
                from atlas.assembly.validator import validate_code
                from atlas.assembly.html_expander import expand_document_html

                MAX_REGENERATION_ATTEMPTS = 3
                spec_output = AgentOutput(content=spec_content) if spec_content else None

                regeneration_attempts = 0
                regeneration_history = []
                validation_result = None

                while regeneration_attempts < MAX_REGENERATION_ATTEMPTS:
                    regeneration_attempts += 1

                    # Build feedback from previous attempt if any
                    if regeneration_history:
                        last_attempt = regeneration_history[-1]
                        feedback = f"""
CRITICAL: Your previous output was NOT SELLABLE. Fix these issues:

{chr(10).join(f'- {issue["message"]} (in {issue["file"]})' for issue in last_attempt["issues"])}

Remember:
- Create ALL content (10 recipe cards means 10 ACTUAL cards with REAL recipes)
- No placeholders like "Recipe Title", "Ingredient 1", "Step 1"
- No HTML comments like "<!-- repeat this -->" or "<!-- add more -->"
- Every file must be complete and ready to sell

Try again with COMPLETE, SELLABLE content:
"""
                        current_prompt = feedback + task_prompt
                        logger.info(f"[Build] Regeneration attempt {regeneration_attempts}/{MAX_REGENERATION_ATTEMPTS}")
                    else:
                        current_prompt = task_prompt

                    # Run Tinker
                    mason_output = await agent_manager.mason.process(
                        current_prompt, context, previous_output=spec_output
                    )

                    # Track tokens
                    mason_tokens = mason_output.tokens_used
                    tokens["total"] += mason_tokens
                    tokens["by_agent"]["mason"] = tokens.get("by_agent", {}).get("mason", 0) + mason_tokens

                    # Extract and process files
                    extracted_files = parse_code_blocks(mason_output.content)
                    assembly_result = assemble_code(extracted_files)
                    assembled_files = assembly_result.files
                    assembled_files = expand_document_html(assembled_files)

                    # Validate
                    validation_result = validate_code(assembled_files, mason_output.content)

                    # Check for sellability errors specifically
                    sellability_errors = [
                        i for i in validation_result.issues
                        if i.severity == "error" and "SELLABILITY" in i.code
                    ]

                    if not sellability_errors:
                        # No sellability errors - we're done
                        logger.info(f"[Build] Passed validation on attempt {regeneration_attempts}")
                        break
                    else:
                        # Track this failed attempt
                        regeneration_history.append({
                            "attempt": regeneration_attempts,
                            "issues": [
                                {"file": i.file, "message": i.message, "code": i.code}
                                for i in sellability_errors
                            ]
                        })
                        logger.warning(f"[Build] Attempt {regeneration_attempts} failed sellability: {len(sellability_errors)} errors")

                # Store regeneration info
                if regeneration_attempts > 1:
                    logger.info(f"[Build] Completed after {regeneration_attempts} attempts")

            # Final assembly info (use last attempt's results)
            assembly_info = {
                "issues_fixed": assembly_result.issues_fixed,
                "remaining_issues": assembly_result.remaining_issues,
                "is_runnable": assembly_result.is_runnable,
                "regeneration_attempts": regeneration_attempts if 'regeneration_attempts' in dir() else 0,
            }

            # Final validation info
            validation_info = {
                "passed": validation_result.passed,
                "score": validation_result.score,
                "summary": validation_result.summary,
                "error_count": validation_result.error_count,
                "warning_count": validation_result.warning_count,
                "issues": [
                    {"severity": i.severity, "file": i.file, "message": i.message, "code": i.code}
                    for i in validation_result.issues
                ],
                "regeneration_attempts": regeneration_attempts if 'regeneration_attempts' in dir() else 0,
                "regeneration_history": regeneration_history if 'regeneration_history' in dir() else [],
            }

            # Generate build preview
            preview_generator = BuildPreviewGenerator()
            build_preview = preview_generator.generate_preview(
                mason_output.content,
                project_context=context
            )

            new_metadata["build"] = {
                "status": "complete",
                "progress": 100,
                "output": mason_output.content,
                "files": list(assembled_files.keys()),
                "extracted_files": extracted_files,  # Original extraction
                "assembled_files": assembled_files,  # Post-processed, runnable code
                "assembly": assembly_info,  # What was fixed by assembler
                "validation": validation_info,  # Code quality checks
                "is_runnable": assembly_result.is_runnable and validation_result.passed,
                "routing": routing_decision.to_dict(),
                "preview": build_preview.to_dict(),
                "agent_output": {
                    "content": mason_output.content,
                    "reasoning": mason_output.reasoning,
                    "tokens_used": mason_tokens,
                    "prompt_tokens": mason_output.prompt_tokens,
                    "completion_tokens": mason_output.completion_tokens,
                    "provider": mason_output.metadata.get("provider", "unknown"),
                }
            }

            # Collect training data for local LLM
            collector = get_collector()
            example_id = collector.add_example(
                system_prompt="You are Tinker, a master builder and implementation agent...",
                user_input=task_prompt,
                assistant_output=mason_output.content,
                agent="mason",
                task_type=routing_decision.task_type.value,
                complexity=routing_decision.complexity.value,
                source_model=routing_decision.model,
                source_provider=routing_decision.provider,
                prompt_tokens=mason_output.prompt_tokens,
                completion_tokens=mason_output.completion_tokens,
                project_id=str(project_id)
            )
            new_metadata["build"]["training_example_id"] = example_id

            new_metadata["tokens"] = tokens
            new_metadata["phase"] = "build_review"  # Move to review phase
            await project_manager.update_project(project_id, metadata=new_metadata)

        except Exception as e:
            new_metadata["build"]["error"] = str(e)
            await project_manager.update_project(project_id, metadata=new_metadata)
            # Notify via Buzz about the error
            buzz = get_buzz()
            await buzz.notify_error(
                project_id=project_id,
                project_name=project.name,
                agent="Tinker",
                error=str(e)
            )
    else:
        # Generate simulated build output (demo mode)
        # Following template: Implementation Summary, Files, Code, Usage
        plan = new_metadata.get("plan", {})
        features = plan.get("features", ["Core functionality"])
        guidance = get_guidance()

        simulated_build = f"""## 🛠️ Tinker's Implementation

### Implementation Summary
Built the core functionality based on the Architect's approved plan.

**Features implemented:**
{chr(10).join(f"- ✅ {f}" for f in features[:5])}

### Files
- `src/main.py` - Main entry point and application bootstrap
- `src/core/__init__.py` - Core module initialization
- `src/core/logic.py` - Business logic implementation
- `src/utils/helpers.py` - Utility functions
- `tests/test_main.py` - Unit tests
- `requirements.txt` - Project dependencies
- `README.md` - Documentation

### Code

**src/main.py**
```python
#!/usr/bin/env python3
\"\"\"Main entry point for the application.\"\"\"

from core.logic import main_handler

def main():
    \"\"\"Application entry point.\"\"\"
    print("Starting application...")
    result = main_handler()
    print(f"Result: {{result}}")
    return result

if __name__ == "__main__":
    main()
```

**src/core/logic.py**
```python
\"\"\"Core business logic.\"\"\"

def main_handler():
    \"\"\"Main handler function.\"\"\"
    # Implementation based on requirements
    return {{"status": "success", "message": "Implementation complete"}}
```

### Usage
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py

# Run tests
pytest tests/
```

### Notes
- Code follows PEP 8 style guidelines
- Type hints added for better IDE support
- Error handling included for edge cases

---
*Note: This is a simulated build. Configure AI providers for actual code generation.*
"""
        # Validate the output
        validation = guidance.validate("mason", simulated_build, context)

        # Generate build preview
        preview_generator = BuildPreviewGenerator()
        build_preview = preview_generator.generate_preview(
            simulated_build,
            project_context=context
        )

        new_metadata["build"] = {
            "status": "complete",
            "progress": 100,
            "output": simulated_build,
            "files": ["src/main.py", "src/core/logic.py", "src/utils/helpers.py", "tests/test_main.py"],
            "routing": routing_decision.to_dict(),
            "preview": build_preview.to_dict(),
            "agent_output": {
                "content": simulated_build,
                "reasoning": "Simulated build output (AI agents not configured)",
                "tokens_used": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "provider": "template",
                "validation": validation.to_dict(),
            }
        }
        new_metadata["tokens"] = tokens
        new_metadata["phase"] = "build_review"
        await project_manager.update_project(project_id, metadata=new_metadata)

    # Notify via Buzz that Tinker finished building
    buzz = get_buzz()
    files_count = len(new_metadata.get("build", {}).get("files", []))
    await buzz.notify_tinker_complete(
        project_id=project_id,
        project_name=project.name,
        tokens_used=tokens.get("by_agent", {}).get("mason", 0),
        files_generated=files_count
    )

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/approve-build", response_class=HTMLResponse)
async def approve_build(request: Request, project_id: int):
    """Approve the Mason's build and move to verification."""
    project_manager = request.app.state.project_manager
    agent_manager = request.app.state.agent_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}
    tokens = new_metadata.get("tokens", {"total": 0, "by_agent": {}})

    # Mark build as approved
    if "build" in new_metadata and "agent_output" in new_metadata["build"]:
        new_metadata["build"]["agent_output"]["approved"] = True

    # Get Governor routing decision for Oracle
    context = new_metadata.get("context", {})

    # Add project type info to context for Oracle
    context["project_type"] = new_metadata.get("project_type")
    context["project_category"] = new_metadata.get("project_category")
    context["project_type_config"] = new_metadata.get("project_type_config")

    governor = get_governor(
        budget_limit=5.0,
        budget_used=tokens.get("total", 0) * 0.00001,
        prefer_local=False,
    )

    routing_decision = governor.route(
        task=project.description or "Verify the implementation",
        agent_name="oracle",
        context=context,
    )

    # Store routing decision
    new_metadata["verification_routing"] = routing_decision.to_dict()

    # Run Oracle verification
    if agent_manager:
        try:
            build = new_metadata.get("build", {})

            task_prompt = f"""Verify this implementation:

Project: {project.description}

Implementation:
{build.get('output', 'No output available')}

Please verify:
1. Does it meet the requirements?
2. Is the code quality acceptable?
3. Are there any issues?

Provide your verdict: APPROVED or NEEDS_REVISION"""

            oracle_output = await agent_manager.oracle.process(task_prompt, context)

            # Update token counts
            oracle_tokens = oracle_output.tokens_used
            tokens["total"] += oracle_tokens
            tokens["by_agent"]["oracle"] = tokens.get("by_agent", {}).get("oracle", 0) + oracle_tokens

            verdict = oracle_output.metadata.get("verdict", "APPROVED")

            # Get validation results from artifacts
            validation = oracle_output.artifacts.get("validation")

            new_metadata["verification"] = {
                "verdict": verdict,
                "output": oracle_output.content,
                "validation": validation,  # Automated code analysis results
                "agent_output": {
                    "content": oracle_output.content,
                    "reasoning": oracle_output.reasoning,
                    "tokens_used": oracle_tokens,
                    "prompt_tokens": oracle_output.prompt_tokens,
                    "completion_tokens": oracle_output.completion_tokens,
                    "provider": oracle_output.metadata.get("provider", "unknown"),
                    "validation_score": oracle_output.metadata.get("validation_score", 0),
                    "validation_passed": oracle_output.metadata.get("validation_passed", True),
                }
            }

            # Collect training data for local LLM
            collector = get_collector()
            example_id = collector.add_example(
                system_prompt="You are Oracle, a quality verification and testing agent...",
                user_input=task_prompt,
                assistant_output=oracle_output.content,
                agent="oracle",
                task_type=routing_decision.task_type.value,
                complexity=routing_decision.complexity.value,
                source_model=routing_decision.model,
                source_provider=routing_decision.provider,
                prompt_tokens=oracle_output.prompt_tokens,
                completion_tokens=oracle_output.completion_tokens,
                project_id=str(project_id)
            )
            new_metadata["verification"]["training_example_id"] = example_id

            new_metadata["tokens"] = tokens
            new_metadata["phase"] = "verify_review"  # Move to verification review

        except Exception as e:
            new_metadata["verification"] = {"error": str(e)}
            new_metadata["phase"] = "verify_review"
            # Notify via Buzz about the error
            buzz = get_buzz()
            await buzz.notify_error(
                project_id=project_id,
                project_name=project.name,
                agent="Oracle",
                error=str(e)
            )

    else:
        # Generate simulated verification output (demo mode)
        # Following template: Summary, Checklist, Issues, Verdict
        build = new_metadata.get("build", {})
        plan = new_metadata.get("plan", {})
        features = plan.get("features", [])
        guidance = get_guidance()

        simulated_verification = f"""## 🔮 Oracle's Verification Report

### Summary
Comprehensive review of Tinker's implementation against Sketch's approved plan.

**Project:** {project.description or 'Unnamed project'}
**Files reviewed:** {len(build.get('files', []))}

### Checklist
✅ Code structure follows best practices
✅ Implementation matches the approved plan
✅ Error handling is in place
✅ Code is readable and maintainable
✅ No obvious security issues detected
✅ Dependencies are properly declared
{chr(10).join(f"✅ {f[:50]} implemented" for f in features[:3]) if features else ""}

### Issues
None - All checks passed.

### Recommendations
1. Add more comprehensive unit tests for edge cases
2. Consider adding API documentation (if applicable)
3. Performance profiling recommended for production

### Verdict
**APPROVED**

The implementation meets all requirements and is ready for delivery. Code quality is satisfactory and follows the approved plan.

---
*Note: This is a simulated verification. Configure AI providers for detailed code review.*
"""
        # Run code validator on the build output for real analysis
        from atlas.agents.code_validator import CodeValidator
        code_validator = CodeValidator()
        code_validation = code_validator.validate(build.get('output', ''), context)

        # Determine verdict based on code validation
        demo_verdict = "APPROVED" if code_validation.passed else "NEEDS_REVISION"

        # Update simulated verification with real issues if found
        if not code_validation.passed:
            issue_text = "\n".join([
                f"- [{i.severity.value.upper()}] {i.message}"
                for i in code_validation.issues[:5]
            ])
            simulated_verification = simulated_verification.replace(
                "### Issues\nNone - All checks passed.",
                f"### Issues Found by Automated Analysis\n{issue_text}"
            )
            simulated_verification = simulated_verification.replace(
                "**APPROVED**",
                f"**{demo_verdict}**"
            )

        new_metadata["verification"] = {
            "verdict": demo_verdict,
            "output": simulated_verification,
            "validation": code_validation.to_dict(),  # Real code analysis
            "agent_output": {
                "content": simulated_verification,
                "reasoning": "Simulated verification with real code analysis",
                "tokens_used": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "provider": "template",
                "validation_score": code_validation.score,
                "validation_passed": code_validation.passed,
            }
        }
        new_metadata["tokens"] = tokens
        new_metadata["phase"] = "verify_review"

    await project_manager.update_project(project_id, metadata=new_metadata)

    # Notify via Buzz about Oracle's verdict
    buzz = get_buzz()
    verdict = new_metadata.get("verification", {}).get("verdict", "UNKNOWN")
    await buzz.notify_oracle_verdict(
        project_id=project_id,
        project_name=project.name,
        verdict=verdict,
        tokens_used=tokens.get("by_agent", {}).get("oracle", 0)
    )

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/approve-verification", response_class=HTMLResponse)
async def approve_verification(request: Request, project_id: int):
    """Approve the Oracle's verification and move to delivery."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}

    # Mark verification as approved and update training quality
    if "verification" in new_metadata and "agent_output" in new_metadata["verification"]:
        new_metadata["verification"]["agent_output"]["approved"] = True
        # Update training data quality
        if "training_example_id" in new_metadata["verification"]:
            collector = get_collector()
            revision_count = new_metadata["verification"].get("revision_count", 0)
            collector.update_quality(
                new_metadata["verification"]["training_example_id"],
                approved=True,
                revision_count=revision_count
            )

    # Also update build training quality
    if "build" in new_metadata:
        if "training_example_id" in new_metadata["build"]:
            collector = get_collector()
            revision_count = new_metadata["build"].get("revision_count", 0)
            collector.update_quality(
                new_metadata["build"]["training_example_id"],
                approved=True,
                revision_count=revision_count
            )

    # Move to delivery
    build = new_metadata.get("build", {})
    verification = new_metadata.get("verification", {})

    new_metadata["phase"] = "deliver"
    new_metadata["delivery"] = {
        "summary": verification.get("output", "Verification complete"),
        "verdict": verification.get("verdict", "APPROVED"),
        "artifacts": build.get("files", [])
    }

    await project_manager.update_project(project_id, metadata=new_metadata)

    # Notify via Buzz that project is complete
    buzz = get_buzz()
    tokens = new_metadata.get("tokens", {})
    await buzz.notify_project_complete(
        project_id=project_id,
        project_name=project.name,
        total_tokens=tokens.get("total", 0),
        files_written=build.get("files", [])
    )

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/generate-deployment", response_class=HTMLResponse)
async def generate_deployment(request: Request, project_id: int):
    """Generate deployment instructions using Launch agent."""
    project_manager = request.app.state.project_manager
    agent_manager = request.app.state.agent_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}
    tokens = new_metadata.get("tokens", {"total": 0, "by_agent": {}})

    # Get build output for Launch to analyze
    build = new_metadata.get("build", {})
    build_output = build.get("output", "")

    if agent_manager and agent_manager.launch:
        try:
            # Create context with build information
            context = new_metadata.get("context", {})
            context["build_output"] = build_output

            # Create a mock previous output with build content
            from atlas.agents.base import AgentOutput
            previous_output = AgentOutput(content=build_output) if build_output else None

            # Run Launch agent
            launch_output = await agent_manager.launch.process(
                task=project.description or "Deploy this project",
                context=context,
                previous_output=previous_output
            )

            # Update token counts
            launch_tokens = launch_output.tokens_used
            tokens["total"] += launch_tokens
            tokens["by_agent"]["launch"] = tokens.get("by_agent", {}).get("launch", 0) + launch_tokens

            # Store deployment instructions
            new_metadata["deployment"] = {
                "instructions": launch_output.content,
                "platforms": launch_output.artifacts.get("platforms", []),
                "guides_used": launch_output.artifacts.get("guides_available", []),
                "agent_output": {
                    "content": launch_output.content,
                    "reasoning": launch_output.reasoning,
                    "tokens_used": launch_tokens,
                    "provider": launch_output.metadata.get("provider", "unknown"),
                }
            }
            new_metadata["tokens"] = tokens

        except Exception as e:
            new_metadata["deployment"] = {"error": str(e)}
            # Notify about error
            buzz = get_buzz()
            await buzz.notify_error(
                project_id=project_id,
                project_name=project.name,
                agent="Launch",
                error=str(e)
            )
    else:
        # Generate placeholder deployment instructions
        new_metadata["deployment"] = {
            "instructions": "Configure AI agents to generate detailed deployment instructions.",
            "platforms": [],
        }

    await project_manager.update_project(project_id, metadata=new_metadata)
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/revise-plan", response_class=HTMLResponse)
async def revise_plan(request: Request, project_id: int):
    """Request changes to the plan - go back to idea phase."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}
    new_metadata["phase"] = "idea"

    await project_manager.update_project(project_id, metadata=new_metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/respond-to-review", response_class=HTMLResponse)
async def respond_to_review(
    request: Request,
    project_id: int,
    agent: str = Form(...),
    response: str = Form(...),
):
    """Respond to an agent's review in the sprint meeting."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}

    # Store responses in the sprint meeting data
    sprint_meeting = new_metadata.get("sprint_meeting", {})
    if "user_responses" not in sprint_meeting:
        sprint_meeting["user_responses"] = {}

    sprint_meeting["user_responses"][agent] = {
        "response": response,
        "timestamp": datetime.now().isoformat(),
    }

    new_metadata["sprint_meeting"] = sprint_meeting
    await project_manager.update_project(project_id, metadata=new_metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/address-team-feedback", response_class=HTMLResponse)
async def address_team_feedback(
    request: Request,
    project_id: int,
    feedback: str = Form(...),
):
    """Address all team feedback and update the plan accordingly."""
    project_manager = request.app.state.project_manager
    agent_manager = request.app.state.agent_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}
    tokens = new_metadata.get("tokens", {"total": 0, "by_agent": {}})

    # Store the feedback
    sprint_meeting = new_metadata.get("sprint_meeting", {})
    sprint_meeting["user_feedback"] = {
        "feedback": feedback,
        "timestamp": datetime.now().isoformat(),
    }
    new_metadata["sprint_meeting"] = sprint_meeting

    # Re-generate the spec with the user feedback incorporated
    if agent_manager:
        try:
            # Get the brief for context
            smart_conv = new_metadata.get("smart_conversation", {})
            brief = smart_conv.get("brief", {})
            context = new_metadata.get("context", {})

            # Include team feedback in the context
            reviews = sprint_meeting.get("reviews", [])
            team_concerns = []
            for review in reviews:
                if review.get("concerns"):
                    team_concerns.extend([f"{review['agent_name']}: {c}" for c in review["concerns"]])
                if review.get("questions"):
                    team_concerns.extend([f"{review['agent_name']} asks: {q}" for q in review["questions"]])

            # Create a revised spec with feedback
            spec_generator = SpecGenerator(openai_api_key=_get_openai_key())
            updated_spec = await spec_generator.generate(
                brief=brief,
                context={
                    **context,
                    "team_concerns": team_concerns,
                    "user_response": feedback,
                    "revision_note": "Revised based on team feedback and user clarifications",
                }
            )

            new_metadata["spec"] = updated_spec.model_dump() if hasattr(updated_spec, 'model_dump') else updated_spec

            # Update tokens
            if hasattr(spec_generator, 'last_usage'):
                agent_tokens = spec_generator.last_usage.get("total_tokens", 0)
                tokens["total"] = tokens.get("total", 0) + agent_tokens
                tokens["by_agent"]["architect_revision"] = tokens.get("by_agent", {}).get("architect_revision", 0) + agent_tokens

            # Mark feedback as addressed and allow proceeding
            sprint_meeting["feedback_addressed"] = True
            sprint_meeting["can_proceed"] = True
            new_metadata["sprint_meeting"] = sprint_meeting
            new_metadata["tokens"] = tokens

        except Exception as e:
            logger.error(f"Error updating spec with feedback: {e}")
            # Still store the feedback even if spec generation fails
            sprint_meeting["feedback_addressed"] = True
            sprint_meeting["can_proceed"] = True
            new_metadata["sprint_meeting"] = sprint_meeting

    await project_manager.update_project(project_id, metadata=new_metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/verify", response_class=HTMLResponse)
async def verify_build(request: Request, project_id: int):
    """Legacy route - redirects to approve-build for new flow."""
    return RedirectResponse(url=f"/projects/{project_id}/approve-build", status_code=307)


@router.post("/{project_id}/request-revision", response_class=HTMLResponse)
async def request_revision(
    request: Request,
    project_id: int,
    agent: str = Form(""),
    feedback: str = Form(""),
):
    """Request changes from an agent - go back to previous phase."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}
    current_phase = new_metadata.get("phase", "idea")

    # Store the feedback
    new_metadata["revision_feedback"] = {
        "agent": agent,
        "feedback": feedback,
        "from_phase": current_phase,
    }

    # Go back to the appropriate phase
    if current_phase == "plan_review":
        new_metadata["phase"] = "idea"
    elif current_phase == "build_review":
        new_metadata["phase"] = "plan_review"  # Let them re-approve plan or go back
    elif current_phase == "verify_review":
        new_metadata["phase"] = "build_review"  # Let them re-approve build

    await project_manager.update_project(project_id, metadata=new_metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/revise-with-feedback", response_class=HTMLResponse)
async def revise_with_feedback(
    request: Request,
    project_id: int,
    agent: str = Form(...),
    feedback: str = Form(...),
):
    """Re-run an agent with user feedback to make specific changes."""
    project_manager = request.app.state.project_manager
    agent_manager = request.app.state.agent_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}
    context = new_metadata.get("context", {})
    tokens = new_metadata.get("tokens", {"total": 0, "by_agent": {}})

    # Track revision history
    if "revision_history" not in new_metadata:
        new_metadata["revision_history"] = []

    new_metadata["revision_history"].append({
        "agent": agent,
        "feedback": feedback,
        "timestamp": datetime.now().isoformat(),
    })

    if agent == "architect":
        # Re-run Architect with feedback
        from atlas.standards import CORE_PRINCIPLE

        plan = new_metadata.get("plan", {})
        original_plan = plan.get("raw_plan", "")

        revision_prompt = f"""The user has reviewed your plan and wants changes.

{CORE_PRINCIPLE}

REMEMBER: The plan must lead to a SELLABLE product. Every task, every requirement must be designed to produce something customers will pay for.

ORIGINAL PLAN:
{original_plan}

USER FEEDBACK - Please address these specific requests:
{feedback}

Revise the plan to address the feedback while maintaining sellability. Keep what works, improve what they asked for."""

        if agent_manager:
            try:
                architect_output = await agent_manager.architect.process(revision_prompt, context)

                if architect_output.content:
                    # Update token counts
                    architect_tokens = architect_output.tokens_used
                    tokens["total"] += architect_tokens
                    tokens["by_agent"]["architect"] = tokens.get("by_agent", {}).get("architect", 0) + architect_tokens

                    # Update plan with revision
                    plan["raw_plan"] = architect_output.content
                    plan["agent_output"] = {
                        "content": architect_output.content,
                        "reasoning": architect_output.reasoning,
                        "tokens_used": architect_tokens,
                        "prompt_tokens": architect_output.prompt_tokens,
                        "completion_tokens": architect_output.completion_tokens,
                        "provider": architect_output.metadata.get("provider", "unknown"),
                        "revised": True,
                        "revision_feedback": feedback,
                    }
                    plan["revision_count"] = plan.get("revision_count", 0) + 1

                    new_metadata["plan"] = plan
                    new_metadata["tokens"] = tokens
            except Exception as e:
                new_metadata["plan"]["revision_error"] = str(e)

        await project_manager.update_project(project_id, metadata=new_metadata)
        return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

    elif agent == "mason":
        # Re-run Mason with feedback
        from atlas.standards import CORE_PRINCIPLE

        build = new_metadata.get("build", {})
        original_build = build.get("output", "")
        plan = new_metadata.get("plan", {})

        revision_prompt = f"""The user has reviewed your implementation and wants changes.

{CORE_PRINCIPLE}

CRITICAL REMINDER:
- Every revision must maintain or IMPROVE sellability
- No shortcuts, no placeholders, no "repeat for X" abbreviations
- The revised output must be IMMEDIATELY sellable
- If it's a planner: every page must be complete with real content
- If it's an app: it must be fully functional
- If it's code: it must run without errors

ORIGINAL IMPLEMENTATION:
{original_build}

USER FEEDBACK - Please address these specific requests:
{feedback}

Revise the implementation to address the feedback while maintaining SELLABLE quality. Keep what works, improve what they asked for."""

        if agent_manager:
            try:
                # Pass the original plan as context
                from atlas.agents.base import AgentOutput
                architect_plan = plan.get('raw_plan', '')
                architect_output = AgentOutput(content=architect_plan) if architect_plan else None

                mason_output = await agent_manager.mason.process(
                    revision_prompt,
                    context,
                    previous_output=architect_output
                )

                if mason_output.content:
                    # Update token counts
                    mason_tokens = mason_output.tokens_used
                    tokens["total"] += mason_tokens
                    tokens["by_agent"]["mason"] = tokens.get("by_agent", {}).get("mason", 0) + mason_tokens

                    # Generate build preview
                    preview_generator = BuildPreviewGenerator()
                    build_preview = preview_generator.generate_preview(
                        mason_output.content,
                        project_context=context
                    )

                    # Update build with revision
                    build["output"] = mason_output.content
                    build["preview"] = build_preview.to_dict()
                    build["agent_output"] = {
                        "content": mason_output.content,
                        "reasoning": mason_output.reasoning,
                        "tokens_used": mason_tokens,
                        "prompt_tokens": mason_output.prompt_tokens,
                        "completion_tokens": mason_output.completion_tokens,
                        "provider": mason_output.metadata.get("provider", "unknown"),
                        "revised": True,
                        "revision_feedback": feedback,
                    }
                    build["revision_count"] = build.get("revision_count", 0) + 1

                    new_metadata["build"] = build
                    new_metadata["tokens"] = tokens
            except Exception as e:
                new_metadata["build"]["revision_error"] = str(e)

        await project_manager.update_project(project_id, metadata=new_metadata)
        return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

    # Default: just go back
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/apply-qc-fixes", response_class=HTMLResponse)
async def apply_qc_fixes(
    request: Request,
    project_id: int,
    qc_type: str = Form("build"),
    selected_fixes: list[str] = Form(default=[]),
):
    """Apply user-selected QC fixes by sending feedback to the appropriate agent."""
    from atlas.standards import CORE_PRINCIPLE

    project_manager = request.app.state.project_manager
    agent_manager = request.app.state.agent_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.metadata.copy() if project.metadata else {}
    context = metadata.get("context", {})
    tokens = metadata.get("tokens", {"total": 0, "by_agent": {}})

    # Get the QC report based on type
    if qc_type == "build":
        qc_report = metadata.get("build_qc_report", {})
        agent = "mason"
    elif qc_type == "plan":
        qc_report = metadata.get("plan_qc_report", {})
        agent = "architect"
    elif qc_type == "brief":
        qc_report = metadata.get("qc_report", {})
        agent = "analyst"
    else:
        qc_report = metadata.get("build_qc_report", {})
        agent = "mason"

    if not qc_report:
        return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

    # Get all issues from QC report
    all_issues = qc_report.get("issues", [])
    verdict_reason = qc_report.get("verdict_reason", "")

    # Filter to only selected issues
    selected_indices = [int(idx) for idx in selected_fixes if idx.isdigit()]
    selected_issues = [all_issues[i] for i in selected_indices if i < len(all_issues)]

    if not selected_issues:
        # No fixes selected, just redirect back
        return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

    # Build feedback from ONLY the selected issues
    issues_text = ""
    for issue in selected_issues:
        desc = issue.get('description', str(issue)) if isinstance(issue, dict) else str(issue)
        fix = issue.get('fix', '') if isinstance(issue, dict) else ''
        severity = issue.get('severity', 'warning') if isinstance(issue, dict) else 'warning'

        issues_text += f"\n[{severity.upper()}] {desc}"
        if fix:
            issues_text += f"\n   → FIX: {fix}"
        issues_text += "\n"

    feedback = f"""The user has reviewed QC results and selected {len(selected_issues)} issue(s) to fix:

{CORE_PRINCIPLE}

SELECTED ISSUES TO FIX:
{issues_text}

You MUST address ALL of the selected issues above. Make the specific changes requested.
The revised output must be SELLABLE and match the Business Brief."""

    # Track that this was a user-selected fix from QC
    if "revision_history" not in metadata:
        metadata["revision_history"] = []

    metadata["revision_history"].append({
        "agent": agent,
        "feedback": f"[QC FIX - {len(selected_issues)} issues selected] {issues_text[:300]}...",
        "timestamp": datetime.now().isoformat(),
        "source": "qc_selected_fix",
        "issues_fixed": len(selected_issues),
    })

    # Apply fixes based on agent type
    if agent == "mason" and agent_manager:
        build = metadata.get("build", {})
        original_build = build.get("output", "")
        plan = metadata.get("plan", {})

        revision_prompt = f"""QC has evaluated your work and found issues. You must fix them now.

{feedback}

ORIGINAL IMPLEMENTATION:
{original_build}

Revise the implementation to fix ALL QC issues while maintaining SELLABLE quality."""

        try:
            from atlas.agents.base import AgentOutput
            architect_plan = plan.get('raw_plan', '')
            architect_output = AgentOutput(content=architect_plan) if architect_plan else None

            mason_output = await agent_manager.mason.process(
                revision_prompt,
                context,
                previous_output=architect_output
            )

            if mason_output.content:
                mason_tokens = mason_output.tokens_used
                tokens["total"] += mason_tokens
                tokens["by_agent"]["mason"] = tokens.get("by_agent", {}).get("mason", 0) + mason_tokens

                # Extract and assemble files from the new output
                from ..utils import parse_code_blocks
                from atlas.assembly.code_assembler import assemble_code
                from atlas.assembly.validator import validate_code
                from atlas.assembly.html_expander import expand_document_html

                extracted_files = parse_code_blocks(mason_output.content)
                assembly_result = assemble_code(extracted_files)
                assembled_files = assembly_result.files
                assembled_files = expand_document_html(assembled_files)
                validation_result = validate_code(assembled_files, mason_output.content)

                # Generate build preview
                preview_generator = BuildPreviewGenerator()
                build_preview = preview_generator.generate_preview(
                    mason_output.content,
                    project_context=context
                )

                build["output"] = mason_output.content
                build["files"] = extracted_files
                build["extracted_files"] = extracted_files
                build["assembled_files"] = assembled_files
                build["assembly"] = {
                    "issues_fixed": assembly_result.issues_fixed,
                    "remaining_issues": assembly_result.remaining_issues,
                }
                build["validation"] = validation_result.to_dict()
                build["is_runnable"] = assembly_result.is_runnable
                build["preview"] = build_preview.to_dict()
                build["agent_output"] = {
                    "content": mason_output.content,
                    "reasoning": mason_output.reasoning,
                    "tokens_used": mason_tokens,
                    "prompt_tokens": mason_output.prompt_tokens,
                    "completion_tokens": mason_output.completion_tokens,
                    "provider": mason_output.metadata.get("provider", "unknown"),
                    "revised": True,
                    "revision_source": "qc_auto_fix",
                }
                build["revision_count"] = build.get("revision_count", 0) + 1

                metadata["build"] = build
                metadata["tokens"] = tokens

                # Clear the old QC report so user knows to re-run
                metadata["build_qc_report"]["applied"] = True

        except Exception as e:
            metadata["build"]["revision_error"] = str(e)
            logger.error(f"QC auto-fix failed: {e}")

    elif agent == "architect" and agent_manager:
        plan = metadata.get("plan", {})
        original_plan = plan.get("raw_plan", "")

        revision_prompt = f"""QC has evaluated your plan and found issues. You must fix them now.

{feedback}

ORIGINAL PLAN:
{original_plan}

Revise the plan to fix ALL QC issues while maintaining sellability."""

        try:
            architect_output = await agent_manager.architect.process(revision_prompt, context)

            if architect_output.content:
                architect_tokens = architect_output.tokens_used
                tokens["total"] += architect_tokens
                tokens["by_agent"]["architect"] = tokens.get("by_agent", {}).get("architect", 0) + architect_tokens

                plan["raw_plan"] = architect_output.content
                plan["agent_output"] = {
                    "content": architect_output.content,
                    "reasoning": architect_output.reasoning,
                    "tokens_used": architect_tokens,
                    "prompt_tokens": architect_output.prompt_tokens,
                    "completion_tokens": architect_output.completion_tokens,
                    "provider": architect_output.metadata.get("provider", "unknown"),
                    "revised": True,
                    "revision_source": "qc_auto_fix",
                }
                plan["revision_count"] = plan.get("revision_count", 0) + 1

                metadata["plan"] = plan
                metadata["tokens"] = tokens

                # Clear the old QC report
                metadata["plan_qc_report"]["applied"] = True

        except Exception as e:
            metadata["plan"]["revision_error"] = str(e)
            logger.error(f"QC auto-fix failed: {e}")

    elif agent == "analyst":
        # Fix Business Brief issues by re-running analyst with feedback
        from atlas.agents.analyst import AnalystAgent

        original_brief = metadata.get("business_brief", {})
        idea = project.description or metadata.get("idea", "")

        # Get idea type info if available
        idea_type = None
        if metadata.get("smart_conversation"):
            conv_data = metadata["smart_conversation"]
            if conv_data.get("brief"):
                conversation_brief = conv_data["brief"]
                idea = conversation_brief.get("description", idea)
            if conv_data.get("current_question", {}).get("idea_type"):
                idea_type = conv_data["current_question"]["idea_type"]

        if not idea_type and metadata.get("idea_type"):
            idea_type = metadata["idea_type"]

        # Build context with QC feedback
        if idea_type:
            context["product_type"] = idea_type.get("type", "unknown")
            context["product_type_name"] = idea_type.get("name", "Product")
            idea = f"[PRODUCT TYPE: {idea_type.get('name', 'Unknown')} - {idea_type.get('type', 'unknown').upper()}]\n\n{idea}"

        # Add QC feedback as revision instructions
        context["qc_feedback"] = feedback
        context["original_brief"] = original_brief

        revision_prompt = f"""You previously created a Business Brief that QC found issues with.

ORIGINAL BRIEF:
{original_brief.get('executive_summary', '')}

QC FEEDBACK - FIX THESE ISSUES:
{issues_text}

Re-analyze the idea and create an IMPROVED Business Brief that addresses ALL the QC issues above.
The revised brief must be more thorough, accurate, and sellable.

IDEA TO ANALYZE:
{idea}
"""

        try:
            analyst = AnalystAgent(
                router=request.app.state.router,
                memory=request.app.state.memory,
                providers=request.app.state.providers
            )

            output = await analyst.process(revision_prompt, context=context)

            if output.artifacts and "brief" in output.artifacts:
                brief_data = output.artifacts["brief"]

                # Track tokens
                analyst_tokens = output.tokens_used
                tokens["total"] += analyst_tokens
                tokens["by_agent"]["analyst"] = tokens.get("by_agent", {}).get("analyst", 0) + analyst_tokens

                # Update metadata
                metadata["business_brief"] = brief_data
                metadata["tokens"] = tokens

                # Mark old QC report as applied
                if "qc_report" in metadata:
                    metadata["qc_report"]["applied"] = True

                # Track revision
                brief_data["revision_count"] = original_brief.get("revision_count", 0) + 1
                brief_data["revision_source"] = "qc_fix"

                logger.info(f"[QC Fix] Analyst revised Business Brief for project {project_id}")

        except Exception as e:
            metadata["brief_revision_error"] = str(e)
            logger.error(f"QC auto-fix for analyst failed: {e}")

    await project_manager.update_project(project_id, metadata=metadata)
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/auto-fix-qc")
async def auto_fix_qc(
    request: Request,
    project_id: int,
    qc_type: str = Form("build"),
    max_attempts: int = Form(5),
):
    """Automatically apply all QC fixes in a loop until pass or max attempts.

    This endpoint:
    1. Runs QC check
    2. If needs_revision, applies ALL fixes
    3. Repeats until pass/pass_with_notes or max_attempts reached
    4. Returns JSON with final status
    """
    from atlas.agents.qc import QCAgent

    project_manager = request.app.state.project_manager
    agent_manager = request.app.state.agent_manager

    if not project_manager:
        return JSONResponse({"error": "Project manager not initialized"}, status_code=500)

    project = await project_manager.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    # Initialize QC agent
    qc_agent = QCAgent(
        router=request.app.state.router,
        memory=getattr(request.app.state, 'memory', None),
        providers=getattr(request.app.state, 'providers', {}),
    )

    results = {
        "project_id": project_id,
        "attempts": [],
        "final_verdict": None,
        "success": False,
        "stopped_reason": None,
    }

    previous_issues = set()  # Track issues to detect loops

    for attempt in range(1, max_attempts + 1):
        # Get fresh project data
        project = await project_manager.get_project(project_id)
        metadata = project.metadata.copy() if project.metadata else {}

        # Run QC check
        if qc_type == "build":
            build = metadata.get("build", {})
            brief = metadata.get("business_brief", {})
            qc_report = await qc_agent.check_build(build, brief, attempt=1)
        else:
            # For now, only support build QC auto-fix
            return JSONResponse({"error": f"Auto-fix not supported for qc_type: {qc_type}"}, status_code=400)

        qc_dict = qc_report.to_dict()
        verdict = qc_dict.get("verdict", "unknown")

        attempt_result = {
            "attempt": attempt,
            "verdict": verdict,
            "alignment": qc_dict.get("alignment_score", 0),
            "sellability": qc_dict.get("sellability_score", 0),
            "quality": qc_dict.get("quality_score", 0),
            "issues_count": len(qc_dict.get("issues", [])),
        }
        results["attempts"].append(attempt_result)

        # Check if we passed
        if verdict in ["pass", "pass_with_notes"]:
            results["final_verdict"] = verdict
            results["success"] = True
            results["stopped_reason"] = "QC passed"

            # Save the passing QC report
            metadata["build_qc_report"] = qc_dict
            await project_manager.update_project(project_id, metadata=metadata)
            break

        # Check for issue loops (same issues appearing repeatedly)
        current_issues = frozenset(
            issue.get("description", str(issue))[:100]
            for issue in qc_dict.get("issues", [])
        )

        if current_issues == previous_issues:
            results["final_verdict"] = verdict
            results["stopped_reason"] = "Same issues detected - cannot fix further"
            metadata["build_qc_report"] = qc_dict
            await project_manager.update_project(project_id, metadata=metadata)
            break

        previous_issues = current_issues

        # Apply ALL fixes
        all_issues = qc_dict.get("issues", [])
        if not all_issues:
            results["final_verdict"] = verdict
            results["stopped_reason"] = "No issues to fix"
            break

        # Build feedback from all issues
        from atlas.standards import CORE_PRINCIPLE

        issues_text = ""
        for issue in all_issues:
            desc = issue.get('description', str(issue)) if isinstance(issue, dict) else str(issue)
            fix = issue.get('fix', '') if isinstance(issue, dict) else ''
            severity = issue.get('severity', 'warning') if isinstance(issue, dict) else 'warning'
            issues_text += f"\n[{severity.upper()}] {desc}"
            if fix:
                issues_text += f"\n   → FIX: {fix}"
            issues_text += "\n"

        feedback = f"""QC Auto-Fix Attempt {attempt}/{max_attempts}

{CORE_PRINCIPLE}

ALL ISSUES TO FIX:
{issues_text}

You MUST address ALL issues above. Make the specific changes requested.
The revised output must be SELLABLE and match the Business Brief."""

        # Apply fixes (similar to apply_qc_fixes but inline)
        build = metadata.get("build", {})
        original_build = build.get("output", "")
        plan = metadata.get("plan", {})
        context = metadata.get("context", {})
        tokens = metadata.get("tokens", {"total": 0, "by_agent": {}})

        revision_prompt = f"""QC has evaluated your work and found issues. You must fix them now.

{feedback}

ORIGINAL IMPLEMENTATION:
{original_build}

Revise the implementation to fix ALL QC issues while maintaining SELLABLE quality."""

        try:
            from atlas.agents.base import AgentOutput
            architect_plan = plan.get('raw_plan', '')
            architect_output = AgentOutput(content=architect_plan) if architect_plan else None

            mason_output = await agent_manager.mason.process(
                revision_prompt,
                context,
                previous_output=architect_output
            )

            if mason_output.content:
                mason_tokens = mason_output.tokens_used
                tokens["total"] += mason_tokens
                tokens["by_agent"]["mason"] = tokens.get("by_agent", {}).get("mason", 0) + mason_tokens

                # Extract and assemble files
                from ..utils import parse_code_blocks
                from atlas.assembly.code_assembler import assemble_code
                from atlas.assembly.validator import validate_code
                from atlas.assembly.html_expander import expand_document_html

                extracted_files = parse_code_blocks(mason_output.content)
                assembly_result = assemble_code(extracted_files)
                assembled_files = assembly_result.files
                assembled_files = expand_document_html(assembled_files)
                validation_result = validate_code(assembled_files, mason_output.content)

                # Generate build preview
                preview_generator = BuildPreviewGenerator()
                build_preview = preview_generator.generate_preview(
                    mason_output.content,
                    project_context=context
                )

                build["output"] = mason_output.content
                build["files"] = extracted_files
                build["extracted_files"] = extracted_files
                build["assembled_files"] = assembled_files
                build["assembly"] = {
                    "issues_fixed": assembly_result.issues_fixed,
                    "remaining_issues": assembly_result.remaining_issues,
                }
                build["validation"] = validation_result.to_dict()
                build["is_runnable"] = assembly_result.is_runnable
                build["preview"] = build_preview.to_dict()
                build["agent_output"] = {
                    "content": mason_output.content,
                    "tokens_used": mason_tokens,
                    "provider": mason_output.metadata.get("provider", "unknown"),
                    "revised": True,
                    "revision_source": "qc_auto_fix",
                    "auto_fix_attempt": attempt,
                }
                build["revision_count"] = build.get("revision_count", 0) + 1

                metadata["build"] = build
                metadata["tokens"] = tokens
                metadata["build_qc_report"] = qc_dict

                await project_manager.update_project(project_id, metadata=metadata)

        except Exception as e:
            logger.error(f"Auto-fix attempt {attempt} failed: {e}")
            results["stopped_reason"] = f"Error during fix: {str(e)}"
            break

    # If we exhausted attempts without passing
    if not results["success"] and not results["stopped_reason"]:
        results["stopped_reason"] = f"Max attempts ({max_attempts}) reached"
        results["final_verdict"] = results["attempts"][-1]["verdict"] if results["attempts"] else "unknown"

    return JSONResponse(results)


@router.post("/{project_id}/complete", response_class=HTMLResponse)
async def complete_project(request: Request, project_id: int):
    """Mark project as complete."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    from atlas.projects.models import ProjectStatus

    await project_manager.update_project(
        project_id,
        status=ProjectStatus.COMPLETED
    )

    return RedirectResponse(url="/", status_code=303)


@router.post("/{project_id}/edit-project", response_class=HTMLResponse)
async def edit_project(
    request: Request,
    project_id: int,
    name: str = Form(...),
    description: str = Form(""),
    problem: str = Form(""),
    features: str = Form(""),
    technical: str = Form(""),
):
    """Edit project name, description, and context."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}

    # Update context
    if "context" not in new_metadata:
        new_metadata["context"] = {}

    feature_list = [f.strip() for f in features.split('\n') if f.strip()]

    new_metadata["context"]["description"] = description
    new_metadata["context"]["problem"] = problem
    new_metadata["context"]["features"] = feature_list
    new_metadata["context"]["technical"] = technical

    await project_manager.update_project(
        project_id,
        name=name,
        description=description,
        metadata=new_metadata
    )

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/edit-section", response_class=HTMLResponse)
async def edit_section(
    request: Request,
    project_id: int,
    section: str = Form(...),
    content: str = Form(...),
):
    """Edit a section's content (plan, build, verification)."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}

    # Track edit history
    if "edit_history" not in new_metadata:
        new_metadata["edit_history"] = []

    # Update the appropriate section
    if section == "plan":
        if "plan" not in new_metadata:
            new_metadata["plan"] = {}
        # Save previous version
        old_content = new_metadata["plan"].get("raw_plan", "")
        new_metadata["edit_history"].append({
            "section": "plan",
            "timestamp": datetime.now().isoformat(),
            "old_content_preview": old_content[:200] if old_content else "",
        })
        new_metadata["plan"]["raw_plan"] = content
        if "agent_output" in new_metadata["plan"]:
            new_metadata["plan"]["agent_output"]["content"] = content
            new_metadata["plan"]["agent_output"]["manually_edited"] = True

    elif section == "build":
        if "build" not in new_metadata:
            new_metadata["build"] = {}
        old_content = new_metadata["build"].get("output", "")
        new_metadata["edit_history"].append({
            "section": "build",
            "timestamp": datetime.now().isoformat(),
            "old_content_preview": old_content[:200] if old_content else "",
        })
        new_metadata["build"]["output"] = content
        if "agent_output" in new_metadata["build"]:
            new_metadata["build"]["agent_output"]["content"] = content
            new_metadata["build"]["agent_output"]["manually_edited"] = True

    elif section == "verification":
        if "verification" not in new_metadata:
            new_metadata["verification"] = {}
        old_content = new_metadata["verification"].get("output", "")
        new_metadata["edit_history"].append({
            "section": "verification",
            "timestamp": datetime.now().isoformat(),
            "old_content_preview": old_content[:200] if old_content else "",
        })
        new_metadata["verification"]["output"] = content
        if "agent_output" in new_metadata["verification"]:
            new_metadata["verification"]["agent_output"]["content"] = content
            new_metadata["verification"]["agent_output"]["manually_edited"] = True

    else:
        raise HTTPException(status_code=400, detail=f"Invalid section: {section}")

    # Keep only last 20 edit history entries
    new_metadata["edit_history"] = new_metadata["edit_history"][-20:]

    await project_manager.update_project(project_id, metadata=new_metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/goto-phase", response_class=HTMLResponse)
async def goto_phase(request: Request, project_id: int, phase: str = Form(...)):
    """Navigate to a specific phase in the pipeline."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Valid phases that can be navigated to
    valid_phases = ['idea', 'plan', 'plan_review', 'sprint_meeting', 'build', 'build_review', 'verify_review', 'deliver']
    if phase not in valid_phases:
        raise HTTPException(status_code=400, detail=f"Invalid phase: {phase}")

    new_metadata = project.metadata.copy() if project.metadata else {}

    # Track navigation history
    if "navigation_history" not in new_metadata:
        new_metadata["navigation_history"] = []

    new_metadata["navigation_history"].append({
        "from": new_metadata.get("phase", "unknown"),
        "to": phase,
        "timestamp": datetime.now().isoformat(),
    })

    # Keep only last 10 navigation entries
    new_metadata["navigation_history"] = new_metadata["navigation_history"][-10:]

    new_metadata["phase"] = phase

    await project_manager.update_project(project_id, metadata=new_metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/set-project-type", response_class=HTMLResponse)
async def set_project_type(
    request: Request,
    project_id: int,
    project_type: str = Form(...),
    project_category: str = Form(...),
):
    """Set or change the project type."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_metadata = project.metadata.copy() if project.metadata else {}

    # Get or create smart_conversation dict
    smart_conv = new_metadata.get("smart_conversation", {})
    brief = smart_conv.get("brief", {})

    # Update project type
    brief["project_type"] = project_type
    brief["project_category"] = project_category
    brief["project_type_confidence"] = 1.0  # User explicitly set it

    # Get suggested stack from project types
    try:
        from atlas.projects.project_types import ProjectTypeDetector, ProjectType
        detector = ProjectTypeDetector()
        config = detector.get_config(ProjectType(project_type))
        if config:
            brief["suggested_stack"] = config.suggested_stack
    except (ValueError, KeyError):
        pass

    smart_conv["brief"] = brief
    new_metadata["smart_conversation"] = smart_conv

    await project_manager.update_project(project_id, metadata=new_metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.get("/{project_id}/delete", response_class=HTMLResponse)
async def confirm_delete_project(request: Request, project_id: int):
    """Show delete confirmation page."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return templates.TemplateResponse(
        "delete_confirm.html",
        {
            "request": request,
            "project": project,
        }
    )


@router.post("/{project_id}/delete", response_class=HTMLResponse)
async def delete_project(request: Request, project_id: int, reason: str = Form("")):
    """Delete a project permanently."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Require a reason to confirm deletion
    if not reason.strip():
        raise HTTPException(status_code=400, detail="Please provide a reason for deletion.")

    # Log the deletion reason (could be stored for analytics)
    import logging
    logging.info(f"Project '{project.name}' (ID: {project_id}) deleted. Reason: {reason}")

    # Delete the project
    await project_manager.delete_project(project_id)

    return RedirectResponse(url="/", status_code=303)


@router.post("", response_class=HTMLResponse)
async def create_project(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
):
    """Create a new project (legacy form)."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    project = await project_manager.create_project(
        name=name,
        description=description,
        tags=tag_list,
        metadata={"phase": "idea"}
    )

    return RedirectResponse(url=f"/projects/{project.id}", status_code=303)


@router.post("/{project_id}/tasks", response_class=HTMLResponse)
async def add_task(
    request: Request,
    project_id: int,
    title: str = Form(...),
    description: str = Form(""),
    priority: int = Form(0),
):
    """Add a task to a project."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    task = await project_manager.add_task(
        project_id=project_id,
        title=title,
        description=description,
        priority=priority,
    )

    if not task:
        raise HTTPException(status_code=404, detail="Project not found")

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


# ================================================
# NEW FEATURES: Templates, Export, Files, Git, Feedback
# ================================================

@router.get("/templates", response_class=HTMLResponse)
async def list_templates(request: Request):
    """Show available project templates."""
    templates_jinja = request.app.state.templates

    from atlas.web.utils import get_templates
    project_templates = get_templates()

    return templates_jinja.TemplateResponse(
        "templates.html",
        {
            "request": request,
            "templates": project_templates,
        }
    )


@router.post("/from-template/{template_id}", response_class=HTMLResponse)
async def create_from_template(
    request: Request,
    template_id: str,
    name: str = Form(""),
):
    """Create a new project from a template."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    from atlas.web.utils import get_templates
    templates = get_templates()

    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")

    template = templates[template_id]
    defaults = template.get("defaults", {})

    project_name = name if name else f"New {template['name']} Project"

    project = await project_manager.create_project(
        name=project_name,
        description=f"{template['description']}",
        metadata={
            "phase": "idea",
            "template": template_id,
            "template_defaults": defaults,
        }
    )

    return RedirectResponse(url=f"/projects/{project.id}", status_code=303)


@router.post("/{project_id}/feedback", response_class=HTMLResponse)
async def submit_feedback(
    request: Request,
    project_id: int,
    agent: str = Form(...),
    rating: int = Form(...),
    comment: str = Form(""),
):
    """Submit feedback/rating for an agent's output."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from atlas.web.utils import add_feedback

    new_metadata = project.metadata.copy() if project.metadata else {}
    new_metadata = add_feedback(new_metadata, agent, rating, comment)

    await project_manager.update_project(project_id, metadata=new_metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/write-files", response_class=HTMLResponse)
async def write_files_to_disk(request: Request, project_id: int):
    """Write generated files to disk."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from atlas.web.utils import parse_code_blocks, write_project_files

    # Get build output
    build = project.metadata.get("build", {})
    output = build.get("output", "")

    if not output:
        raise HTTPException(status_code=400, detail="No build output to write")

    # Parse code blocks from output
    files = parse_code_blocks(output)

    if not files:
        raise HTTPException(status_code=400, detail="No code blocks found in output")

    # Write files
    result = write_project_files(project_id, files)

    # Update metadata with file info
    new_metadata = project.metadata.copy() if project.metadata else {}
    new_metadata["files_written"] = result

    await project_manager.update_project(project_id, metadata=new_metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/init-git", response_class=HTMLResponse)
async def initialize_git(request: Request, project_id: int):
    """Initialize git repository for project files."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from atlas.web.utils import init_git_repo

    files_written = project.metadata.get("files_written", {})
    project_dir = files_written.get("project_dir")

    if not project_dir:
        raise HTTPException(status_code=400, detail="No files written yet. Write files first.")

    # Initialize git
    result = init_git_repo(project_dir)

    # Update metadata
    new_metadata = project.metadata.copy() if project.metadata else {}
    new_metadata["git"] = result

    await project_manager.update_project(project_id, metadata=new_metadata)

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.get("/{project_id}/export")
async def export_project(request: Request, project_id: int):
    """Export project as ZIP file."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from fastapi.responses import StreamingResponse
    from atlas.web.utils import parse_code_blocks, create_project_zip

    # Get build output
    build = project.metadata.get("build", {})
    output = build.get("output", "")

    # Parse code blocks from output
    files = parse_code_blocks(output)

    # Add plan as markdown
    plan = project.metadata.get("plan", {})
    if plan.get("raw_plan"):
        files["PLAN.md"] = f"# Project Plan\n\n{plan['raw_plan']}"

    # Add verification report
    verification = project.metadata.get("verification", {})
    if verification.get("output"):
        files["VERIFICATION.md"] = f"# Verification Report\n\n{verification['output']}"

    # Create ZIP with comprehensive README
    project_name = project.name.replace(" ", "_").lower()[:30]
    zip_buffer = create_project_zip(project_name, files, metadata=project.metadata)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={project_name}.zip"
        }
    )


@router.get("/{project_id}/revisions", response_class=HTMLResponse)
async def view_revisions(request: Request, project_id: int):
    """View revision history for a project."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    revisions = project.metadata.get("revisions", [])

    return templates.TemplateResponse(
        "revisions.html",
        {
            "request": request,
            "project": project,
            "revisions": revisions,
        }
    )


@router.get("/{project_id}/changelog", response_class=HTMLResponse)
async def view_changelog(request: Request, project_id: int):
    """View changelog/version history for a project."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Extract changelog data from project metadata
    metadata = project.metadata or {}
    changelog_data = metadata.get("changelog", {})
    releases = changelog_data.get("releases", [])
    current_version = changelog_data.get("current_version", "1.0.0")
    raw_changelog = changelog_data.get("raw", "")

    # Parse releases into template-friendly format
    parsed_releases = []
    for release in releases:
        parsed = {
            "version": release.get("version", ""),
            "date": release.get("date", ""),
            "update_type": release.get("update_type", ""),
            "summary": release.get("summary", ""),
            "added": release.get("added", []),
            "changed": release.get("changed", []),
            "fixed": release.get("fixed", []),
            "removed": release.get("removed", []),
            "security": release.get("security", []),
            "deprecated": release.get("deprecated", []),
            "breaking_changes": release.get("breaking_changes", []),
        }
        parsed_releases.append(parsed)

    return templates.TemplateResponse(
        "changelog.html",
        {
            "request": request,
            "project": project,
            "project_id": project_id,
            "current_version": current_version,
            "last_updated": changelog_data.get("last_updated"),
            "releases": parsed_releases,
            "raw_changelog": raw_changelog,
        }
    )


@router.get("/{project_id}/cost", response_class=HTMLResponse)
async def view_cost(request: Request, project_id: int):
    """View cost breakdown for a project."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from atlas.web.utils import calculate_project_cost, get_feedback_summary

    costs = calculate_project_cost(project.metadata or {})
    feedback = get_feedback_summary(project.metadata or {})

    return templates.TemplateResponse(
        "cost.html",
        {
            "request": request,
            "project": project,
            "costs": costs,
            "feedback": feedback,
        }
    )


# ================================================
# DEPLOYMENT AUTOMATION ROUTES
# ================================================

# Platform configuration - Organized by category
PLATFORMS = {
    # ==================== Mobile App Stores ====================
    "ios": {
        "name": "Apple App Store",
        "icon": "🍎",
        "category": "mobile",
        "knowledge_id": "ios-deployment",
        "env_vars": [
            {"name": "APPLE_ID", "description": "Your Apple ID email", "secret": False, "required": True},
            {"name": "APP_SPECIFIC_PASSWORD", "description": "App-specific password from appleid.apple.com", "secret": True, "required": True},
        ],
    },
    "android": {
        "name": "Google Play Store",
        "icon": "🤖",
        "category": "mobile",
        "knowledge_id": "android-deployment",
        "env_vars": [
            {"name": "KEYSTORE_PASSWORD", "description": "Android keystore password", "secret": True, "required": True},
            {"name": "KEY_PASSWORD", "description": "Key alias password", "secret": True, "required": True},
        ],
    },
    "amazon-appstore": {
        "name": "Amazon Appstore",
        "icon": "📦",
        "category": "mobile",
        "knowledge_id": "amazon-appstore-deployment",
        "env_vars": [],
    },

    # ==================== Web Hosting ====================
    "vercel": {
        "name": "Vercel",
        "icon": "▲",
        "category": "web",
        "knowledge_id": "react-deployment",
        "env_vars": [
            {"name": "VERCEL_TOKEN", "description": "Vercel API token (optional)", "secret": True, "required": False},
        ],
    },
    "netlify": {
        "name": "Netlify",
        "icon": "◆",
        "category": "web",
        "knowledge_id": "react-deployment",
        "env_vars": [
            {"name": "NETLIFY_AUTH_TOKEN", "description": "Netlify auth token (optional)", "secret": True, "required": False},
        ],
    },
    "github-pages": {
        "name": "GitHub Pages",
        "icon": "📄",
        "category": "web",
        "knowledge_id": "react-deployment",
        "env_vars": [],
    },

    # ==================== Backend/Server ====================
    "docker": {
        "name": "Docker",
        "icon": "🐳",
        "category": "backend",
        "knowledge_id": "docker-deployment",
        "env_vars": [
            {"name": "DOCKER_REGISTRY", "description": "Docker registry URL (e.g., docker.io)", "secret": False, "required": False},
            {"name": "DOCKER_USERNAME", "description": "Docker registry username", "secret": False, "required": False},
            {"name": "DOCKER_PASSWORD", "description": "Docker registry password", "secret": True, "required": False},
        ],
    },
    "railway": {
        "name": "Railway",
        "icon": "🚂",
        "category": "backend",
        "knowledge_id": "python-deployment",
        "env_vars": [
            {"name": "RAILWAY_TOKEN", "description": "Railway API token (optional)", "secret": True, "required": False},
        ],
    },

    # ==================== Voice Assistants ====================
    "alexa": {
        "name": "Amazon Alexa Skills",
        "icon": "🔊",
        "category": "voice",
        "knowledge_id": "alexa-skill-deployment",
        "env_vars": [
            {"name": "ASK_ACCESS_TOKEN", "description": "ASK CLI access token", "secret": True, "required": False},
        ],
    },

    # ==================== Design & Creative ====================
    "figma": {
        "name": "Figma Plugins",
        "icon": "🎯",
        "category": "creative",
        "knowledge_id": "figma-plugin-deployment",
        "env_vars": [],
    },

    # ==================== Browser Extensions ====================
    "chrome": {
        "name": "Chrome Web Store",
        "icon": "🌐",
        "category": "browser",
        "knowledge_id": "chrome-extension-deployment",
        "env_vars": [],
    },

    # ==================== E-Commerce & Marketplaces ====================
    "shopify": {
        "name": "Shopify Apps",
        "icon": "🛒",
        "category": "ecommerce",
        "knowledge_id": "shopify-app-deployment",
        "env_vars": [
            {"name": "SHOPIFY_API_KEY", "description": "Shopify API key", "secret": True, "required": False},
            {"name": "SHOPIFY_API_SECRET", "description": "Shopify API secret", "secret": True, "required": False},
        ],
    },
    "wordpress": {
        "name": "WordPress Plugins",
        "icon": "📝",
        "category": "ecommerce",
        "knowledge_id": "wordpress-plugin-deployment",
        "env_vars": [
            {"name": "WP_SVN_USERNAME", "description": "WordPress.org SVN username", "secret": False, "required": True},
            {"name": "WP_SVN_PASSWORD", "description": "WordPress.org SVN password", "secret": True, "required": True},
        ],
    },

    # ==================== Package Registries ====================
    "npm": {
        "name": "npm Registry",
        "icon": "📦",
        "category": "packages",
        "knowledge_id": "npm-deployment",
        "env_vars": [
            {"name": "NPM_TOKEN", "description": "npm auth token", "secret": True, "required": False},
        ],
    },
    "pypi": {
        "name": "PyPI",
        "icon": "🐍",
        "category": "packages",
        "knowledge_id": "pypi-deployment",
        "env_vars": [
            {"name": "PYPI_TOKEN", "description": "PyPI API token", "secret": True, "required": False},
        ],
    },

    # ==================== Communication Platforms ====================
    "slack": {
        "name": "Slack Apps",
        "icon": "💬",
        "category": "communication",
        "knowledge_id": "slack-app-deployment",
        "env_vars": [
            {"name": "SLACK_BOT_TOKEN", "description": "Slack bot token (xoxb-...)", "secret": True, "required": True},
            {"name": "SLACK_SIGNING_SECRET", "description": "Slack signing secret", "secret": True, "required": True},
        ],
    },
    "discord": {
        "name": "Discord Bots",
        "icon": "🎮",
        "category": "communication",
        "knowledge_id": "discord-bot-deployment",
        "env_vars": [
            {"name": "DISCORD_TOKEN", "description": "Discord bot token", "secret": True, "required": True},
        ],
    },
}

# Category display names and icons
PLATFORM_CATEGORIES = {
    "mobile": {"name": "📱 Mobile App Stores", "order": 1},
    "web": {"name": "🌐 Web Hosting", "order": 2},
    "backend": {"name": "⚙️ Backend / API", "order": 3},
    "voice": {"name": "🔊 Voice Assistants", "order": 4},
    "creative": {"name": "🎨 Design & Creative", "order": 5},
    "browser": {"name": "🌐 Browser Extensions", "order": 6},
    "ecommerce": {"name": "🛒 E-Commerce", "order": 7},
    "packages": {"name": "📦 Package Registries", "order": 8},
    "communication": {"name": "💬 Communication", "order": 9},
}


@router.post("/{project_id}/deploy/{platform}/execute", response_class=HTMLResponse)
async def execute_deployment(
    request: Request,
    project_id: int,
    platform: str,
):
    """Create and optionally execute a deployment task."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get platform config (check built-in first, then custom)
    platform_config = PLATFORMS.get(platform)
    if not platform_config:
        custom_platforms = project.metadata.get("custom_platforms", {}) if project.metadata else {}
        if platform in custom_platforms:
            platform_config = custom_platforms[platform]
            platform_config["knowledge_id"] = platform_config.get("knowledge_id", f"{platform}-deployment")
        else:
            raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")

    # Get form data for environment variables
    form_data = await request.form()
    env_vars = {}
    for env_var in platform_config.get("env_vars", []):
        value = form_data.get(env_var["name"])
        if value:
            env_vars[env_var["name"]] = value

    # Get project directory
    files_written = project.metadata.get("files_written", {}) if project.metadata else {}
    project_dir = files_written.get("project_dir")

    if not project_dir:
        raise HTTPException(status_code=400, detail="No project files written yet")

    # Create automation task from knowledge
    from atlas.automation import AutomationManager

    am = AutomationManager()
    task = am.create_from_knowledge(
        knowledge_entry_id=platform_config["knowledge_id"],
        working_dir=project_dir,
        env_vars=env_vars,
    )

    if not task:
        # Fallback: create task with platform-specific commands
        from atlas.knowledge import KnowledgeManager
        km = KnowledgeManager()
        entry = km.get(platform_config["knowledge_id"])

        if entry and entry.commands:
            task = am.create_task(
                name=f"Deploy to {platform_config['name']}",
                commands=entry.commands,
                description=f"Deployment to {platform_config['name']} for project {project.name}",
                working_dir=project_dir,
                env_vars=env_vars,
                source=f"knowledge:{platform_config['knowledge_id']}",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"No deployment commands available for {platform}"
            )

    # Save task reference in project metadata
    new_metadata = project.metadata.copy() if project.metadata else {}
    if "deployments" not in new_metadata:
        new_metadata["deployments"] = []

    new_metadata["deployments"].append({
        "platform": platform,
        "task_id": task.id,
        "status": task.status.value,
        "created_at": task.created_at.isoformat(),
    })

    await project_manager.update_project(project_id, metadata=new_metadata)

    # If task needs approval, show approval page
    if not task.approved:
        return templates.TemplateResponse(
            "deploy_approve.html",
            {
                "request": request,
                "project": project,
                "platform": platform,
                "platform_name": platform_config["name"],
                "platform_icon": platform_config["icon"],
                "task": task,
            }
        )

    # Otherwise redirect to status page
    return RedirectResponse(
        url=f"/projects/{project_id}/deploy/{platform}/status?task_id={task.id}",
        status_code=303
    )


@router.post("/{project_id}/deploy/{platform}/approve", response_class=HTMLResponse)
async def approve_deployment(
    request: Request,
    project_id: int,
    platform: str,
    task_id: str = Form(...),
):
    """Approve a deployment task for execution."""
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Approve the task
    from atlas.automation import AutomationManager

    am = AutomationManager()
    success = am.approve_task(task_id, approved_by="web_user")

    if not success:
        raise HTTPException(status_code=400, detail="Could not approve task")

    # Redirect to execution/status
    return RedirectResponse(
        url=f"/projects/{project_id}/deploy/{platform}/status?task_id={task_id}&execute=1",
        status_code=303
    )


@router.get("/{project_id}/deploy/{platform}/status", response_class=HTMLResponse)
async def deployment_status(
    request: Request,
    project_id: int,
    platform: str,
    task_id: str = "",
    execute: int = 0,
):
    """Get deployment task status (for HTMX polling)."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not task_id:
        raise HTTPException(status_code=400, detail="No task_id provided")

    # Get platform config (check built-in first, then custom)
    platform_config = PLATFORMS.get(platform)
    if not platform_config:
        custom_platforms = project.metadata.get("custom_platforms", {}) if project.metadata else {}
        if platform in custom_platforms:
            platform_config = custom_platforms[platform]
        else:
            raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")

    from atlas.automation import AutomationManager

    am = AutomationManager()
    task = am.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # If execute flag set and task is pending, start execution
    if execute and task.status.value == "pending" and task.approved:
        # Start execution in background
        import asyncio

        async def run_task():
            await am.execute_task(task_id)

        asyncio.create_task(run_task())
        # Re-fetch task
        task = am.get_task(task_id)

    # Check if this is an HTMX request (polling for updates)
    is_htmx = request.headers.get("HX-Request") == "true"

    if is_htmx:
        # Return just the output terminal content
        output_lines = []
        for result in task.results:
            output_lines.append(f'<div class="output-command">$ {result.command}</div>')
            if result.stdout:
                output_lines.append(f'<div class="output-stdout">{result.stdout}</div>')
            if result.stderr:
                output_lines.append(f'<div class="output-stderr">{result.stderr}</div>')

        if task.status.value == "completed":
            output_lines.append('<div class="output-success">✅ Deployment completed successfully!</div>')
        elif task.status.value == "failed":
            output_lines.append(f'<div class="output-error">❌ Deployment failed: {task.error}</div>')
        elif task.status.value == "running":
            output_lines.append('<div class="output-loading"><span class="spinner"></span> Running...</div>')

        return HTMLResponse(content="\n".join(output_lines))

    # Full page response
    return templates.TemplateResponse(
        "deploy_status.html",
        {
            "request": request,
            "project": project,
            "platform": platform,
            "platform_name": platform_config["name"],
            "platform_icon": platform_config["icon"],
            "task": task,
        }
    )


# ================================================
# CUSTOM PLATFORM ROUTES
# ================================================

@router.get("/{project_id}/deploy/custom", response_class=HTMLResponse)
async def custom_platform_wizard(request: Request, project_id: int):
    """Show form to add a custom deployment platform."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return templates.TemplateResponse(
        "deploy_custom.html",
        {
            "request": request,
            "project": project,
            "platforms": PLATFORMS,
        }
    )


@router.post("/{project_id}/deploy/custom/save", response_class=HTMLResponse)
async def save_custom_platform(
    request: Request,
    project_id: int,
    data: str = Form(...),
):
    """Save a custom deployment platform configuration."""
    import json

    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        platform_data = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data")

    # Generate a slug for the platform
    platform_slug = platform_data["name"].lower().replace(" ", "-")[:30]
    platform_slug = "".join(c for c in platform_slug if c.isalnum() or c == "-")

    # Save to knowledge base if guide content provided
    if platform_data.get("guide_content"):
        from atlas.knowledge import KnowledgeManager
        from atlas.knowledge.models import KnowledgeEntry, KnowledgeCategory

        km = KnowledgeManager()
        entry = KnowledgeEntry(
            id=f"{platform_slug}-deployment",
            title=f"{platform_data['name']} Deployment Guide",
            category=KnowledgeCategory.DEPLOYMENT,
            content=platform_data.get("guide_content", ""),
            tags=[platform_slug, "deployment", "custom"],
            platform=platform_slug,
            prerequisites=platform_data.get("prerequisites", []),
            commands=platform_data.get("commands", []),
            source="user-defined",
        )
        km.add(entry)

    # Save custom platform to project metadata
    new_metadata = project.metadata.copy() if project.metadata else {}

    if "custom_platforms" not in new_metadata:
        new_metadata["custom_platforms"] = {}

    new_metadata["custom_platforms"][platform_slug] = {
        "name": platform_data["name"],
        "icon": platform_data.get("icon", "🚀"),
        "category": platform_data.get("category", "other"),
        "url": platform_data.get("url", ""),
        "prerequisites": platform_data.get("prerequisites", []),
        "commands": platform_data.get("commands", []),
        "env_vars": platform_data.get("env_vars", []),
        "knowledge_id": f"{platform_slug}-deployment" if platform_data.get("guide_content") else None,
    }

    await project_manager.update_project(project_id, metadata=new_metadata)

    # Redirect to the new platform's deploy page
    return RedirectResponse(
        url=f"/projects/{project_id}/deploy/{platform_slug}",
        status_code=303
    )


@router.get("/{project_id}/deploy/{platform}", response_class=HTMLResponse)
async def deploy_wizard_extended(request: Request, project_id: int, platform: str):
    """Extended deploy wizard that also checks custom platforms."""
    templates = request.app.state.templates
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=500, detail="Project manager not initialized")

    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check built-in platforms first
    platform_config = PLATFORMS.get(platform)

    # If not found, check custom platforms
    if not platform_config:
        custom_platforms = project.metadata.get("custom_platforms", {}) if project.metadata else {}
        if platform in custom_platforms:
            platform_config = custom_platforms[platform]
            platform_config["knowledge_id"] = platform_config.get("knowledge_id", f"{platform}-deployment")
        else:
            raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")

    # Get deployment guide from knowledge base
    from atlas.knowledge import KnowledgeManager
    import markdown

    km = KnowledgeManager()
    guide = km.get_deployment_guide(platform)

    # Get or fallback guide info
    if guide:
        guide_content = markdown.markdown(guide.content, extensions=['fenced_code', 'tables'])
        prerequisites = guide.prerequisites
        commands_raw = guide.commands
    else:
        # Try getting by knowledge ID
        knowledge_id = platform_config.get("knowledge_id", f"{platform}-deployment")
        entry = km.get(knowledge_id)
        if entry:
            guide_content = markdown.markdown(entry.content, extensions=['fenced_code', 'tables'])
            prerequisites = entry.prerequisites
            commands_raw = entry.commands
        else:
            # Fall back to platform config
            guide_content = "<p>No deployment guide available. Add custom deployment steps.</p>"
            prerequisites = platform_config.get("prerequisites", [])
            commands_raw = platform_config.get("commands", [])

    # Assess command risks
    from atlas.automation.executor import CommandExecutor
    executor = CommandExecutor()

    commands = []
    requires_approval = False
    for cmd in commands_raw:
        risk, reason = executor.assess_risk(cmd)
        commands.append({
            "command": cmd,
            "risk": risk.value,
            "reason": reason,
        })
        if risk.value in ("high", "critical"):
            requires_approval = True

    # Get project directory if files have been written
    files_written = project.metadata.get("files_written", {}) if project.metadata else {}
    project_dir = files_written.get("project_dir")

    return templates.TemplateResponse(
        "deploy.html",
        {
            "request": request,
            "project": project,
            "platform": platform,
            "platform_name": platform_config.get("name", platform.title()),
            "platform_icon": platform_config.get("icon", "🚀"),
            "guide_content": guide_content,
            "prerequisites": prerequisites,
            "commands": commands,
            "env_vars_required": platform_config.get("env_vars", []),
            "project_dir": project_dir,
            "requires_approval": requires_approval,
            "task_id": None,
        }
    )


# ============================================================================
# GitHub Integration Routes
# ============================================================================


@router.post("/{project_id}/github/create-repo")
async def create_github_repo(
    request: Request,
    project_id: int,
    private: bool = Form(False),
):
    """Create a GitHub repository for this project."""
    from atlas.projects.manager import ProjectManager
    from atlas.integrations.github.api import get_github_api

    pm = ProjectManager()
    project = pm.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate repo name from project name
    repo_name = re.sub(r'[^a-zA-Z0-9-]', '-', project.name.lower())
    repo_name = re.sub(r'-+', '-', repo_name).strip('-')

    # Get project description
    description = project.brief.get("description", "") if project.brief else ""
    if not description and project.metadata:
        description = project.metadata.get("description", "")
    description = description[:200] if description else f"Generated by ATLAS: {project.name}"

    # Determine gitignore template based on project type
    gitignore_map = {
        "web_spa": "Node",
        "web_static": "Node",
        "mobile_ios": "Swift",
        "mobile_android": "Android",
        "mobile_flutter": "Dart",
        "api_rest": "Python",
        "api_graphql": "Python",
        "cli_python": "Python",
        "cli_node": "Node",
        "lib_python": "Python",
        "lib_npm": "Node",
    }
    project_type = project.metadata.get("project_type", "") if project.metadata else ""
    gitignore = gitignore_map.get(project_type, "Python")

    try:
        github = get_github_api()

        # Get authenticated user to build repo URL
        user = await github.get_user()
        username = user["login"]

        # Create the repository
        repo_data = await github.create_repo(
            name=repo_name,
            description=description,
            private=private,
            auto_init=True,
            gitignore_template=gitignore,
        )

        # Store GitHub info in project metadata
        github_info = {
            "repo": repo_data["full_name"],
            "url": repo_data["html_url"],
            "clone_url": repo_data["clone_url"],
            "created_at": datetime.utcnow().isoformat(),
        }

        metadata = project.metadata or {}
        metadata["github"] = github_info
        pm.update(project_id, metadata=metadata)

        logger.info(f"Created GitHub repo {repo_data['full_name']} for project {project_id}")

        return JSONResponse({
            "success": True,
            "repo": repo_data["full_name"],
            "url": repo_data["html_url"],
            "clone_url": repo_data["clone_url"],
        })

    except Exception as e:
        logger.exception(f"Failed to create GitHub repo for project {project_id}: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/{project_id}/github/push")
async def push_to_github(
    request: Request,
    project_id: int,
):
    """Push project files to the GitHub repository."""
    from atlas.projects.manager import ProjectManager
    from atlas.integrations.github.api import get_github_api

    pm = ProjectManager()
    project = pm.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if project has GitHub repo
    github_info = (project.metadata or {}).get("github")
    if not github_info:
        return JSONResponse(
            {"success": False, "error": "No GitHub repository linked. Create one first."},
            status_code=400
        )

    # Get files that were written
    files_written = (project.metadata or {}).get("files_written", {})
    if not files_written:
        return JSONResponse(
            {"success": False, "error": "No files have been written for this project."},
            status_code=400
        )

    try:
        github = get_github_api()
        repo = github_info["repo"]

        # Collect files to push
        files_to_push = {}
        project_dir = files_written.get("project_dir", "")

        for filename, filepath in files_written.items():
            if filename == "project_dir":
                continue
            # Read file content
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    content = f.read()
                # Use relative path in repo
                rel_path = os.path.relpath(filepath, project_dir) if project_dir else filename
                files_to_push[rel_path] = content

        if not files_to_push:
            return JSONResponse(
                {"success": False, "error": "No files found to push."},
                status_code=400
            )

        # Push files
        results = await github.push_files(
            repo=repo,
            files=files_to_push,
            message=f"Update from ATLAS: {project.name}",
        )

        logger.info(f"Pushed {len(results)} files to {repo}")

        return JSONResponse({
            "success": True,
            "files_pushed": len(results),
            "repo": repo,
        })

    except Exception as e:
        logger.exception(f"Failed to push to GitHub for project {project_id}: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


# ============================================================================
# Platform Integration Routes
# ============================================================================


@router.get("/{project_id}/platforms")
async def get_project_platforms(request: Request, project_id: int):
    """Get available platforms for this project based on its type."""
    from atlas.projects.manager import ProjectManager
    from atlas.integrations.platforms import (
        get_platforms_for_type,
        list_platforms,
    )

    pm = ProjectManager()
    project = pm.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get project type from metadata
    brief = {}
    if project.metadata:
        smart_conv = project.metadata.get("smart_conversation", {})
        brief = smart_conv.get("brief", {})

    project_type = brief.get("project_type", "")
    project_category = brief.get("project_category", "")

    # Get platforms that support this project type
    if project_type:
        platforms = get_platforms_for_type(project_type)
    elif project_category:
        platforms = get_platforms_for_type(project_category)
    else:
        # Return all platforms if no type set
        platforms = [p for p in list_platforms()]

    # Build response with platform info and requirements
    platform_data = []
    for platform in platforms:
        if hasattr(platform, 'to_dict'):
            info = platform.to_dict()
            info["id"] = platform.name.lower().replace(" ", "_")
            info["requirements"] = [
                r.to_dict() for r in platform.get_requirements(project_type or project_category or "")
            ]
            platform_data.append(info)
        else:
            # Already a dict from list_platforms
            platform_data.append(platform)

    return JSONResponse({
        "project_id": project_id,
        "project_type": project_type,
        "project_category": project_category,
        "platforms": platform_data,
    })


@router.post("/{project_id}/platforms/{platform_id}/validate")
async def validate_for_platform(
    request: Request,
    project_id: int,
    platform_id: str,
):
    """Validate project against a platform's requirements."""
    from atlas.projects.manager import ProjectManager
    from atlas.integrations.platforms import get_platform

    pm = ProjectManager()
    project = pm.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    platform = get_platform(platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail=f"Platform '{platform_id}' not found")

    # Get project type
    brief = {}
    if project.metadata:
        smart_conv = project.metadata.get("smart_conversation", {})
        brief = smart_conv.get("brief", {})

    project_type = brief.get("project_type", brief.get("project_category", ""))

    # Build product dict from project data
    product = {
        "name": project.name,
        "metadata": {
            "title": project.name,
            "description": project.description or brief.get("description", ""),
            **brief,
        },
        "content": project.metadata.get("build", {}).get("content", {}),
        "assets": project.metadata.get("assets", {}),
        "files": project.metadata.get("files_written", {}),
    }

    # Validate
    result = platform.validate(product, project_type)

    return JSONResponse({
        "platform": platform.name,
        "platform_id": platform_id,
        "project_id": project_id,
        "validation": result.to_dict(),
    })


@router.post("/{project_id}/platforms/{platform_id}/publish")
async def publish_to_platform(
    request: Request,
    project_id: int,
    platform_id: str,
):
    """Publish project to a platform."""
    from atlas.projects.manager import ProjectManager
    from atlas.integrations.platforms import get_platform

    pm = ProjectManager()
    project = pm.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    platform = get_platform(platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail=f"Platform '{platform_id}' not found")

    # Authenticate first
    try:
        authenticated = await platform.authenticate()
        if not authenticated:
            return JSONResponse({
                "success": False,
                "error": f"Not authenticated with {platform.name}. Check your credentials.",
                "env_vars": platform.get_env_vars(),
            }, status_code=401)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": f"Authentication failed: {str(e)}",
        }, status_code=401)

    # Get project type
    brief = {}
    if project.metadata:
        smart_conv = project.metadata.get("smart_conversation", {})
        brief = smart_conv.get("brief", {})

    project_type = brief.get("project_type", brief.get("project_category", ""))

    # Build product dict
    product = {
        "name": project.name,
        "title": project.name,
        "metadata": {
            "title": project.name,
            "description": project.description or brief.get("description", ""),
            **brief,
        },
        "content": project.metadata.get("build", {}).get("content", {}),
        "assets": project.metadata.get("assets", {}),
        "files": project.metadata.get("files_written", {}),
    }

    # Publish
    try:
        result = await platform.publish(product, project_type)

        # Store submission info in project metadata
        if result.success and result.submission_id:
            metadata = project.metadata or {}
            submissions = metadata.get("platform_submissions", {})
            submissions[platform_id] = {
                "submission_id": result.submission_id,
                "status": result.status.value,
                "url": result.url,
                "submitted_at": datetime.utcnow().isoformat(),
            }
            metadata["platform_submissions"] = submissions
            pm.update(project_id, metadata=metadata)

        return JSONResponse({
            "success": result.success,
            "platform": platform.name,
            "result": result.to_dict(),
        })

    except Exception as e:
        logger.exception(f"Failed to publish to {platform.name}: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=500)


@router.get("/{project_id}/platforms/{platform_id}/status")
async def check_platform_status(
    request: Request,
    project_id: int,
    platform_id: str,
):
    """Check submission status on a platform."""
    from atlas.projects.manager import ProjectManager
    from atlas.integrations.platforms import get_platform

    pm = ProjectManager()
    project = pm.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    platform = get_platform(platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail=f"Platform '{platform_id}' not found")

    # Get submission ID from project metadata
    submissions = (project.metadata or {}).get("platform_submissions", {})
    submission = submissions.get(platform_id)

    if not submission or not submission.get("submission_id"):
        return JSONResponse({
            "platform": platform.name,
            "status": "not_submitted",
            "message": "Project has not been submitted to this platform",
        })

    # Check status
    try:
        await platform.authenticate()
        result = await platform.check_status(submission["submission_id"])

        # Update stored status
        submission["status"] = result.status.value
        if result.url:
            submission["url"] = result.url
        submission["checked_at"] = datetime.utcnow().isoformat()

        metadata = project.metadata or {}
        metadata["platform_submissions"][platform_id] = submission
        pm.update(project_id, metadata=metadata)

        return JSONResponse({
            "platform": platform.name,
            "result": result.to_dict(),
        })

    except Exception as e:
        logger.exception(f"Failed to check status on {platform.name}: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=500)


# ============================================
# PROJECT AGENT CONVERSATIONS
# ============================================

# In-memory storage for active project conversations
_project_conversations: dict = {}


def _get_project_conversation_key(project_id: int, agent_type: str) -> str:
    return f"project_{project_id}_{agent_type}"


@router.post("/{project_id}/agent-chat/start")
async def start_project_agent_chat(request: Request, project_id: int):
    """Start a conversational review with an agent."""
    from atlas.agents.spec_conversation import SpecRefinementConversation

    project_manager = request.app.state.project_manager

    if not project_manager:
        return JSONResponse({"error": "Project manager not initialized"}, status_code=500)

    # Parse request
    try:
        body = await request.json()
        agent_type = body.get("agent", "sketch")
    except Exception:
        agent_type = "sketch"

    # Get project
    project = await project_manager.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    # Build spec/plan content for the agent to review
    metadata = project.metadata or {}
    spec = metadata.get("spec", {})
    brief = metadata.get("smart_conversation", {}).get("brief", {})
    sprint_meeting = metadata.get("sprint_meeting", {})

    # Build content for review
    spec_content = f"""# Project: {project.name}

## Description
{project.description or brief.get('description', 'No description')}

## Problem
{brief.get('problem_statement', 'Not specified')}

## Target Users
{brief.get('target_users', 'Not specified')}

## Core Features
{chr(10).join('- ' + f for f in brief.get('core_features', []))}

"""

    # Add requirements if available
    requirements = spec.get("requirements", [])
    if requirements:
        spec_content += "## Requirements\n"
        for req in requirements[:10]:  # Limit to first 10
            spec_content += f"- **{req.get('id')}**: {req.get('title')} ({req.get('priority')})\n"
            if req.get('description'):
                spec_content += f"  {req.get('description')[:200]}\n"
        spec_content += "\n"

    # Add tasks if available
    tasks = spec.get("tasks", [])
    if tasks:
        spec_content += "## Tasks\n"
        for task in tasks[:10]:  # Limit to first 10
            spec_content += f"- **{task.get('id')}**: {task.get('title')} ({task.get('status', 'pending')})\n"
        spec_content += "\n"

    # Add previous agent reviews if in sprint meeting
    reviews = sprint_meeting.get("reviews", [])
    if reviews:
        spec_content += "## Previous Agent Reviews\n"
        for review in reviews:
            spec_content += f"### {review.get('agent_name', 'Unknown').title()} ({review.get('verdict', 'pending')})\n"
            spec_content += f"{review.get('summary', '')}\n"
            if review.get('concerns'):
                spec_content += "**Concerns:** " + ", ".join(review.get('concerns', [])[:3]) + "\n"
            spec_content += "\n"

    spec_metadata = {
        "status": metadata.get("phase", "unknown"),
        "task_count": len(tasks),
    }

    # Get OpenAI key
    openai_key = _get_openai_key()

    # Create conversation
    conversation = SpecRefinementConversation(
        agent_type=agent_type,
        openai_api_key=openai_key,
        openai_model="gpt-4o-mini",
    )

    # Start the conversation
    try:
        response = await conversation.start(
            spec_name=project.name,
            spec_content=spec_content,
            spec_metadata=spec_metadata,
        )

        # Store conversation
        key = _get_project_conversation_key(project_id, agent_type)
        _project_conversations[key] = conversation
        print(f"[Projects] Started conversation with key: {key}")

        return JSONResponse({
            "response": response,
            "state": conversation.get_state(),
            "agent": conversation.agent,
        })

    except Exception as e:
        logger.exception(f"Failed to start agent chat: {e}")
        return JSONResponse({
            "error": f"Failed to start conversation: {str(e)}"
        }, status_code=500)


@router.post("/{project_id}/agent-chat/respond")
async def continue_project_agent_chat(request: Request, project_id: int):
    """Continue a conversational review with an agent."""
    from atlas.agents.spec_conversation import SpecRefinementConversation

    # Parse request
    try:
        body = await request.json()
        message = body.get("message", "")
        agent_type = body.get("agent", "sketch")
        conversation_state = body.get("conversation_state")
    except Exception as e:
        logger.error(f"Error parsing request: {e}")
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    if not message.strip():
        return JSONResponse({"error": "Message is required"}, status_code=400)

    # Get or restore conversation
    key = _get_project_conversation_key(project_id, agent_type)
    print(f"[Projects] Looking for conversation: {key}")
    print(f"[Projects] Active conversations: {list(_project_conversations.keys())}")

    conversation = _project_conversations.get(key)

    if not conversation and conversation_state:
        # Restore from state
        print(f"[Projects] Restoring conversation from state")
        openai_key = _get_openai_key()
        conversation = SpecRefinementConversation.from_dict(
            conversation_state,
            openai_api_key=openai_key,
            openai_model="gpt-4o-mini",
        )
        _project_conversations[key] = conversation

    if not conversation:
        print(f"[Projects] No conversation found for key: {key}")
        return JSONResponse({
            "error": "No active conversation. Please start a new one."
        }, status_code=400)

    try:
        response = await conversation.respond(message)

        return JSONResponse({
            "response": response,
            "state": conversation.get_state(),
            "messages": conversation.get_messages(),
            "is_complete": conversation.is_complete,
            "spec_updates": conversation.spec_updates,
        })

    except Exception as e:
        logger.exception(f"Failed to process response: {e}")
        return JSONResponse({
            "error": f"Failed to process response: {str(e)}"
        }, status_code=500)


@router.get("/{project_id}/agent-chat/state")
async def get_project_agent_chat_state(request: Request, project_id: int, agent: str = "sketch"):
    """Get the current state of an agent conversation."""
    key = _get_project_conversation_key(project_id, agent)
    conversation = _project_conversations.get(key)

    if not conversation:
        return JSONResponse({
            "active": False,
            "message": "No active conversation"
        })

    return JSONResponse({
        "active": True,
        "state": conversation.get_state(),
        "messages": conversation.get_messages(),
        "conversation_data": conversation.to_dict(),
    })


@router.post("/{project_id}/agent-chat/reset")
async def reset_project_agent_chat(request: Request, project_id: int):
    """Reset an agent conversation."""
    try:
        body = await request.json()
        agent_type = body.get("agent", "sketch")
    except Exception:
        agent_type = "sketch"

    key = _get_project_conversation_key(project_id, agent_type)
    if key in _project_conversations:
        del _project_conversations[key]

    return JSONResponse({"success": True, "message": "Conversation reset"})


# ============================================
# TEAM CONVERSATION (Talk to the whole team)
# ============================================

_team_conversations: dict = {}


@router.post("/{project_id}/team-chat/start")
async def start_team_chat(request: Request, project_id: int):
    """Start a team conversation where all agents participate."""
    from atlas.agents.team_conversation import TeamConversation

    project_manager = request.app.state.project_manager

    if not project_manager:
        return JSONResponse({"error": "Project manager not initialized"}, status_code=500)

    project = await project_manager.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    # Check for mode parameter (default to round_table)
    try:
        body = await request.json()
        mode = body.get("mode", "round_table")
    except Exception:
        mode = "round_table"

    # Build spec content
    metadata = project.metadata or {}
    spec = metadata.get("spec", {})
    brief = metadata.get("smart_conversation", {}).get("brief", {})
    sprint_meeting = metadata.get("sprint_meeting", {})

    spec_content = f"""# Project: {project.name}

## Description
{project.description or brief.get('description', 'No description')}

## Problem
{brief.get('problem_statement', 'Not specified')}

## Target Users
{brief.get('target_users', 'Not specified')}

## Core Features
{chr(10).join('- ' + f for f in brief.get('core_features', []))}

"""

    # Add requirements
    requirements = spec.get("requirements", [])
    if requirements:
        spec_content += "## Requirements\n"
        for req in requirements[:10]:
            spec_content += f"- **{req.get('id')}**: {req.get('title')}\n"
        spec_content += "\n"

    # Add tasks
    tasks = spec.get("tasks", [])
    if tasks:
        spec_content += "## Tasks\n"
        for task in tasks[:10]:
            spec_content += f"- **{task.get('id')}**: {task.get('title')}\n"
        spec_content += "\n"

    # Get previous agent reviews
    previous_reviews = sprint_meeting.get("reviews", [])

    # Create team conversation with round-table mode
    openai_key = _get_openai_key()
    conversation = TeamConversation(
        openai_api_key=openai_key,
        openai_model="gpt-4o-mini",
        mode=mode,  # Use round_table by default
    )

    try:
        # Start the conversation
        messages = await conversation.start(
            project_name=project.name,
            spec_content=spec_content,
            previous_reviews=previous_reviews,
        )

        # Store conversation
        _team_conversations[project_id] = conversation
        print(f"[Projects] Started team conversation for project {project_id} (mode: {mode})")

        return JSONResponse({
            "messages": messages,
            "state": conversation.get_state(),
        })

    except Exception as e:
        logger.exception(f"Failed to start team chat: {e}")
        return JSONResponse({
            "error": f"Failed to start conversation: {str(e)}"
        }, status_code=500)


@router.post("/{project_id}/team-chat/respond")
async def continue_team_chat(request: Request, project_id: int):
    """Continue the team conversation."""
    from atlas.agents.team_conversation import TeamConversation

    try:
        body = await request.json()
        message = body.get("message", "")
        conversation_state = body.get("conversation_state")
    except Exception as e:
        logger.error(f"Error parsing request: {e}")
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    if not message.strip():
        return JSONResponse({"error": "Message is required"}, status_code=400)

    # Get or restore conversation
    conversation = _team_conversations.get(project_id)

    if not conversation and conversation_state:
        openai_key = _get_openai_key()
        conversation = TeamConversation.from_dict(
            conversation_state,
            openai_api_key=openai_key,
            openai_model="gpt-4o-mini",
        )
        _team_conversations[project_id] = conversation

    if not conversation:
        return JSONResponse({
            "error": "No active team conversation. Please start a new one."
        }, status_code=400)

    try:
        messages = await conversation.respond(message)

        # If conversation is complete, save clarifications to project metadata
        if conversation.is_complete:
            project_manager = request.app.state.project_manager
            if project_manager:
                project = await project_manager.get_project(project_id)
                if project:
                    new_metadata = project.metadata.copy() if project.metadata else {}
                    spec_update_data = conversation.get_spec_update_data()

                    # Store team chat data for agents to use
                    new_metadata["team_chat"] = {
                        "resolved_concerns": spec_update_data.get("resolved_concerns", []),
                        "user_clarifications": spec_update_data.get("user_clarifications", []),
                        "summary": spec_update_data.get("summary", ""),
                        "is_complete": True,
                    }

                    await project_manager.update_project(project_id, metadata=new_metadata)
                    logger.info(f"Saved team chat data to project {project_id}")

        return JSONResponse({
            "messages": messages,
            "state": conversation.get_state(),
            "is_complete": conversation.is_complete,
            "conversation_data": conversation.to_dict(),
        })

    except Exception as e:
        logger.exception(f"Failed to process response: {e}")
        return JSONResponse({
            "error": f"Failed to process response: {str(e)}"
        }, status_code=500)


@router.get("/{project_id}/team-chat/state")
async def get_team_chat_state(request: Request, project_id: int):
    """Get the current state of the team conversation."""
    conversation = _team_conversations.get(project_id)

    if not conversation:
        return JSONResponse({
            "active": False,
            "message": "No active team conversation"
        })

    return JSONResponse({
        "active": True,
        "state": conversation.get_state(),
        "messages": conversation.get_messages(),
        "conversation_data": conversation.to_dict(),
    })


@router.post("/{project_id}/team-chat/reset")
async def reset_team_chat(request: Request, project_id: int):
    """Reset the team conversation."""
    if project_id in _team_conversations:
        del _team_conversations[project_id]

    return JSONResponse({"success": True, "message": "Team conversation reset"})


# ============================================================================
# Director Agent - Real-time Agent Conversation (Phase 4)
# ============================================================================

@router.post("/{project_id}/start-director")
async def start_director_build(request: Request, project_id: int):
    """Start the Director agent to orchestrate the build.

    This kicks off the real-time agent conversation where:
    - Director analyzes the goal
    - Spawns appropriate team of agents
    - Agents discuss and build in real-time
    - Progress is streamed via WebSocket
    """
    import asyncio
    from atlas.agents.director import DirectorAgent
    from atlas.agents.analyst import BusinessBrief

    project_manager = request.app.state.project_manager
    if not project_manager:
        return JSONResponse({"error": "Project manager not available"}, status_code=500)

    project = await project_manager.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    # Get business brief if available
    metadata = project.metadata or {}
    brief = None

    brief_data = metadata.get("business_brief")
    if brief_data:
        try:
            # Filter to only valid BusinessBrief fields
            import dataclasses
            valid_fields = {f.name for f in dataclasses.fields(BusinessBrief)}
            filtered_data = {k: v for k, v in brief_data.items() if k in valid_fields}
            brief = BusinessBrief(**filtered_data)
        except Exception as e:
            logger.warning(f"Could not parse business brief: {e}")

    # Create and run director in background
    async def run_director():
        try:
            director = DirectorAgent(project)
            result = await director.run(brief=brief)
            logger.info(f"Director completed for project {project_id}: {result}")

            # Update project metadata with result
            new_metadata = dict(metadata)
            new_metadata["director_result"] = result
            new_metadata["phase"] = "review" if result.get("success") else "error"
            await project_manager.update_project(project_id, metadata=new_metadata)

        except Exception as e:
            logger.exception(f"Director error for project {project_id}: {e}")

    # Start in background
    asyncio.create_task(run_director())

    return JSONResponse({
        "success": True,
        "message": "Director started. Watch the conversation via WebSocket.",
        "websocket_url": f"/ws/projects/{project_id}/conversation"
    })


@router.get("/{project_id}/conversation-view", response_class=HTMLResponse)
async def get_conversation_view(request: Request, project_id: int):
    """Get the live conversation partial for a project."""
    templates = request.app.state.templates

    return templates.TemplateResponse(
        "partials/live_conversation.html",
        {
            "request": request,
            "project_id": project_id,
        }
    )


