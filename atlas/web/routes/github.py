"""GitHub sync API routes for ATLAS Transporter.

Provides endpoints for:
- Syncing tasks to/from GitHub
- Linking tasks to issues
- Checking sync status
- Webhook handling
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class SyncRequest(BaseModel):
    """Request model for sync operations."""
    repo: Optional[str] = None
    issue_number: Optional[int] = None
    project_id: Optional[int] = None


class LinkRequest(BaseModel):
    """Request model for linking task to issue."""
    repo: str
    issue_number: int


class SyncResponse(BaseModel):
    """Response model for sync operations."""
    success: bool
    message: str
    task_id: Optional[int] = None
    issue_number: Optional[int] = None
    repo: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None


def _get_transporter(request: Request):
    """Get transporter from app state."""
    transporter = getattr(request.app.state, "transporter", None)
    if not transporter:
        raise HTTPException(
            status_code=503,
            detail="GitHub Transporter not initialized. Set ATLAS_GITHUB_TOKEN environment variable.",
        )
    return transporter


@router.get("/status")
async def get_sync_status(request: Request):
    """Get overall sync status.

    Returns:
        Sync state with counts
    """
    transporter = _get_transporter(request)

    try:
        state = await transporter.get_sync_status()
        return {
            "status": "ok",
            "configured": transporter.config.is_configured,
            "default_repo": transporter.config.default_repo,
            "sync_state": state.to_dict(),
        }
    except Exception as e:
        logger.exception(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/task/{task_id}")
async def sync_task_to_github(
    request: Request,
    task_id: int,
    repo: Optional[str] = Query(None, description="Repository in owner/repo format"),
):
    """Sync an ATLAS task to GitHub as an issue.

    Args:
        task_id: ATLAS task ID
        repo: Repository in owner/repo format (uses default if not provided)

    Returns:
        SyncResponse with result
    """
    transporter = _get_transporter(request)

    try:
        result = await transporter.sync_task_to_github(
            task_id=task_id,
            repo=repo,
        )

        return SyncResponse(
            success=result.success,
            message=result.message,
            task_id=result.atlas_task_id,
            issue_number=result.github_issue_number,
            repo=result.github_repo,
            url=result.url,
            error=result.error,
        )
    except Exception as e:
        logger.exception(f"Error syncing task {task_id} to GitHub: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/issue")
async def sync_issue_to_atlas(
    request: Request,
    repo: str = Query(..., description="Repository in owner/repo format"),
    issue_number: int = Query(..., description="GitHub issue number"),
    project_id: Optional[int] = Query(None, description="ATLAS project ID"),
):
    """Sync a GitHub issue to ATLAS as a task.

    Args:
        repo: Repository in owner/repo format
        issue_number: GitHub issue number
        project_id: Optional ATLAS project ID

    Returns:
        SyncResponse with result
    """
    transporter = _get_transporter(request)

    try:
        result = await transporter.sync_issue_to_atlas(
            repo=repo,
            issue_number=issue_number,
            project_id=project_id,
        )

        return SyncResponse(
            success=result.success,
            message=result.message,
            task_id=result.atlas_task_id,
            issue_number=result.github_issue_number,
            repo=result.github_repo,
            url=result.url,
            error=result.error,
        )
    except Exception as e:
        logger.exception(f"Error syncing issue {repo}#{issue_number} to ATLAS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/link/task/{task_id}")
async def link_task_to_issue(
    request: Request,
    task_id: int,
    repo: str = Query(..., description="Repository in owner/repo format"),
    issue_number: int = Query(..., description="GitHub issue number"),
):
    """Link an existing ATLAS task to a GitHub issue.

    Args:
        task_id: ATLAS task ID
        repo: Repository in owner/repo format
        issue_number: GitHub issue number

    Returns:
        SyncResponse with result
    """
    transporter = _get_transporter(request)

    try:
        result = await transporter.link_task_to_issue(
            task_id=task_id,
            repo=repo,
            issue_number=issue_number,
        )

        return SyncResponse(
            success=result.success,
            message=result.message,
            task_id=result.atlas_task_id,
            issue_number=result.github_issue_number,
            repo=result.github_repo,
            url=result.url,
            error=result.error,
        )
    except Exception as e:
        logger.exception(f"Error linking task {task_id} to issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/all")
async def sync_all(request: Request):
    """Sync all linked tasks/issues.

    Returns:
        List of sync results
    """
    transporter = _get_transporter(request)

    try:
        results = await transporter.sync_all()

        return {
            "success": True,
            "total": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "results": [r.to_dict() for r in results],
        }
    except Exception as e:
        logger.exception(f"Error syncing all: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapping/task/{task_id}")
async def get_task_mapping(request: Request, task_id: int):
    """Get GitHub mapping for a task.

    Args:
        task_id: ATLAS task ID

    Returns:
        Mapping info or 404
    """
    transporter = _get_transporter(request)

    try:
        mapping = await transporter.get_mapping_by_task(task_id)
        if not mapping:
            raise HTTPException(
                status_code=404,
                detail=f"No GitHub mapping found for task {task_id}",
            )

        return mapping.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting mapping for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapping/issue")
async def get_issue_mapping(
    request: Request,
    repo: str = Query(..., description="Repository in owner/repo format"),
    issue_number: int = Query(..., description="GitHub issue number"),
):
    """Get ATLAS mapping for a GitHub issue.

    Args:
        repo: Repository in owner/repo format
        issue_number: GitHub issue number

    Returns:
        Mapping info or 404
    """
    transporter = _get_transporter(request)

    try:
        mapping = await transporter.get_mapping_by_issue(repo, issue_number)
        if not mapping:
            raise HTTPException(
                status_code=404,
                detail=f"No ATLAS mapping found for issue {repo}#{issue_number}",
            )

        return mapping.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting mapping for issue {repo}#{issue_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def handle_github_webhook(request: Request):
    """Handle incoming GitHub webhook events.

    This endpoint processes GitHub webhook events for sync.
    Configure in GitHub repo settings:
    - Payload URL: https://your-atlas-url/github/webhook
    - Content type: application/json
    - Secret: ATLAS_GITHUB_WEBHOOK_SECRET
    - Events: Issues, Issue comments

    Returns:
        Webhook processing result
    """
    transporter = _get_transporter(request)

    # Get event type from header
    event_type = request.headers.get("X-GitHub-Event", "")
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header")

    # Get signature for verification
    signature = request.headers.get("X-Hub-Signature-256", "")

    # Get payload
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {e}")

    # Get action to form full event type
    action = payload.get("action", "")
    full_event_type = f"{event_type}.{action}" if action else event_type

    # Process through sync handler
    try:
        from atlas.integrations.github import get_github_sync_handler

        handler = get_github_sync_handler(transporter)
        results = await handler.handle_event(full_event_type, payload)

        return {
            "success": True,
            "event": full_event_type,
            "results": [r.to_dict() for r in results],
        }
    except Exception as e:
        logger.exception(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/output/task/{task_id}")
async def post_agent_output(
    request: Request,
    task_id: int,
    summary: Optional[str] = Query(None, description="Summary to include"),
):
    """Post agent output to linked GitHub issue as a comment.

    Args:
        task_id: ATLAS task ID
        summary: Optional summary

    Returns:
        SyncResponse with result
    """
    transporter = _get_transporter(request)
    project_manager = request.app.state.project_manager

    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")

    try:
        # Get task with outputs
        task = await project_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Build output dict from agent_outputs
        output = {}
        for agent_output in task.agent_outputs:
            output[agent_output.agent_name] = {
                "content": agent_output.content,
                "metadata": agent_output.metadata,
            }

        if not output:
            raise HTTPException(
                status_code=400,
                detail="Task has no agent outputs to post",
            )

        result = await transporter.post_agent_output(
            task_id=task_id,
            output=output,
            summary=summary,
        )

        return SyncResponse(
            success=result.success,
            message=result.message,
            task_id=result.atlas_task_id,
            issue_number=result.github_issue_number,
            repo=result.github_repo,
            url=result.url,
            error=result.error,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error posting agent output for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
