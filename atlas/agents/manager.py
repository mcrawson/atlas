"""Agent Manager - Coordinates agent workflows."""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional

from .base import AgentOutput, AgentStatus
from ..tools.file_writer import FileWriter, WriteResult
from ..versioning import (
    Version,
    UpdateType,
    UpdateContext,
    ChangelogRelease,
    get_changelog_generator,
)

logger = logging.getLogger("atlas.agents.manager")
from .architect import ArchitectAgent
from .mason import MasonAgent
from .oracle import OracleAgent
from .finisher import FinisherAgent
from .launch import LaunchAgent
from .hype import HypeAgent


class WorkflowMode(Enum):
    """Workflow execution modes."""
    # Creation modes
    SEQUENTIAL = "sequential"  # Sketch -> Tinker -> Oracle
    DIRECT_BUILD = "direct_build"  # Tinker only (simple tasks)
    VERIFY_ONLY = "verify_only"  # Oracle only (review existing code)
    SPEC_DRIVEN = "spec_driven"  # Generate spec, then execute tasks
    FULL_DEPLOY = "full_deploy"  # Sketch -> Tinker -> Oracle -> Launch
    DEPLOY_ONLY = "deploy_only"  # Launch only (for existing builds)
    FULL_POLISH = "full_polish"  # Sketch -> Tinker -> Oracle -> Finisher (ready to sell)
    FULL_CAMPAIGN = "full_campaign"  # Sketch -> Tinker -> Oracle -> Finisher -> Launch -> Hype
    PROMOTE_ONLY = "promote_only"  # Hype only (for existing products)

    # Update modes - for modifying existing products
    UPDATE = "update"          # Update existing product (auto-detect update type)
    UPDATE_PATCH = "update_patch"  # Bug fix update (1.0.0 -> 1.0.1)
    UPDATE_MINOR = "update_minor"  # Feature update (1.0.0 -> 1.1.0)
    UPDATE_MAJOR = "update_major"  # Major/breaking update (1.0.0 -> 2.0.0)
    HOTFIX = "hotfix"          # Urgent fix (minimal review, fast track)


@dataclass
class WorkflowEvent:
    """Event emitted during workflow execution."""
    event_type: str  # "agent_start", "agent_complete", "workflow_complete", "error"
    agent_name: Optional[str]
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for WebSocket transmission."""
        return {
            "event_type": self.event_type,
            "agent_name": self.agent_name,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class AgentManager:
    """Coordinates agent workflows for ATLAS.

    Supports multiple workflow modes:
    - Sequential: Sketch -> Tinker -> Oracle (full workflow)
    - Direct Build: Tinker only (for simple implementation tasks)
    - Verify Only: Oracle only (for code review)

    Features:
    - Event broadcasting for real-time updates
    - Revision loops when Oracle rejects
    - Maximum revision limit to prevent infinite loops
    """

    MAX_REVISIONS = 3  # Maximum times Tinker can revise before failing

    def __init__(self, router, memory, providers: dict = None, output_dir: str = None):
        """Initialize agent manager.

        Args:
            router: ATLAS Router for AI provider access
            memory: ATLAS MemoryManager for context
            providers: Dictionary of initialized providers
            output_dir: Base directory for writing generated files
        """
        self.router = router
        self.memory = memory
        self.providers = providers or {}

        # Initialize agents with shared router and memory
        agent_kwargs = {"providers": self.providers}
        self.architect = ArchitectAgent(router, memory, **agent_kwargs)
        self.mason = MasonAgent(router, memory, **agent_kwargs)
        self.oracle = OracleAgent(router, memory, **agent_kwargs)
        self.finisher = FinisherAgent(router, memory, **agent_kwargs)
        self.launch = LaunchAgent(router, memory, **agent_kwargs)
        self.hype = HypeAgent(router, memory, **agent_kwargs)

        # File writer for saving generated code
        self.file_writer = FileWriter(base_dir=output_dir)
        self.auto_write_files = True  # Enable automatic file writing

        # Event callbacks for WebSocket broadcasting
        self._event_callbacks: list[Callable[[WorkflowEvent], None]] = []

        # Workflow completion callbacks (for GitHub sync, etc.)
        self._completion_callbacks: list[Callable] = []

        # Register status callbacks from agents
        for agent in [self.architect, self.mason, self.oracle, self.finisher, self.launch, self.hype]:
            agent.register_callback(self._on_agent_status_change)

    def register_event_callback(self, callback: Callable[[WorkflowEvent], None]):
        """Register a callback for workflow events.

        Args:
            callback: Function to call with WorkflowEvent
        """
        self._event_callbacks.append(callback)

    def unregister_event_callback(self, callback: Callable[[WorkflowEvent], None]):
        """Remove an event callback."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    def register_completion_callback(self, callback: Callable):
        """Register a callback for workflow completion.

        Callback signature: async def callback(task_id: int, outputs: dict) -> None

        Args:
            callback: Async function to call after workflow completes
        """
        self._completion_callbacks.append(callback)

    def unregister_completion_callback(self, callback: Callable):
        """Remove a completion callback."""
        if callback in self._completion_callbacks:
            self._completion_callbacks.remove(callback)

    async def _run_completion_callbacks(self, task_id: Optional[int], outputs: dict[str, AgentOutput]):
        """Run all completion callbacks.

        Args:
            task_id: ATLAS task ID if available
            outputs: Workflow outputs
        """
        if not task_id:
            return

        for callback in self._completion_callbacks:
            try:
                await callback(task_id, outputs)
            except Exception as e:
                logger.warning(f"Completion callback failed: {e}")

    def _emit_event(self, event: WorkflowEvent):
        """Emit an event to all registered callbacks."""
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.debug(f"Event callback failed: {e}")

    def _on_agent_status_change(self, agent_name: str, status: AgentStatus, task: Optional[str]):
        """Handle agent status changes."""
        self._emit_event(WorkflowEvent(
            event_type="agent_status",
            agent_name=agent_name,
            data={
                "status": status.value,
                "task": task,
            }
        ))

    def _extract_project_name(self, task: str) -> str:
        """Extract a project name from the task description.

        Args:
            task: Task description

        Returns:
            Sanitized project name
        """
        # Try to extract key nouns from the task
        # Remove common words and take first meaningful phrase
        task_lower = task.lower()

        # Remove common prefixes
        for prefix in ["build ", "create ", "make ", "implement ", "develop ", "write "]:
            if task_lower.startswith(prefix):
                task = task[len(prefix):]
                break

        # Take first 4 words max
        words = task.split()[:4]
        name = "-".join(words)

        # Sanitize
        name = re.sub(r'[^\w\-]', '-', name.lower())
        name = re.sub(r'-+', '-', name).strip('-')

        return name or "atlas-project"

    def _write_generated_files(
        self,
        task: str,
        mason_output: AgentOutput,
        project_dir: Optional[Path] = None,
    ) -> Optional[WriteResult]:
        """Write files from Mason's output to disk.

        Args:
            task: Original task description (used for project name)
            mason_output: Mason's output containing generated code
            project_dir: Optional specific directory to write to

        Returns:
            WriteResult if files were written, None otherwise
        """
        if not mason_output or not mason_output.content:
            return None

        project_name = self._extract_project_name(task)

        self._emit_event(WorkflowEvent(
            event_type="files_writing",
            agent_name="system",
            data={"project_name": project_name}
        ))

        result = self.file_writer.write_from_mason_output(
            output=mason_output.content,
            project_name=project_name,
            project_dir=project_dir,
        )

        self._emit_event(WorkflowEvent(
            event_type="files_written",
            agent_name="system",
            data={
                "success": result.success,
                "project_dir": result.project_dir,
                "files_written": result.files_written,
                "files_failed": result.files_failed,
                "errors": result.errors,
            }
        ))

        return result

    def get_all_status(self) -> dict[str, dict]:
        """Get status of all agents.

        Returns:
            Dictionary of agent statuses
        """
        return {
            "architect": self.architect.get_status_dict(),
            "mason": self.mason.get_status_dict(),
            "oracle": self.oracle.get_status_dict(),
            "finisher": self.finisher.get_status_dict(),
            "launch": self.launch.get_status_dict(),
            "hype": self.hype.get_status_dict(),
        }

    async def execute_workflow(
        self,
        task: str,
        mode: WorkflowMode = WorkflowMode.SEQUENTIAL,
        context: Optional[dict] = None,
        task_id: Optional[int] = None,
    ) -> dict[str, AgentOutput]:
        """Execute a complete agent workflow.

        Args:
            task: The task to execute
            mode: Workflow mode to use
            context: Optional context for agents
            task_id: Optional ATLAS task ID for GitHub sync

        Returns:
            Dictionary mapping agent names to their outputs
        """
        outputs: dict[str, AgentOutput] = {}
        context = context or {}

        self._emit_event(WorkflowEvent(
            event_type="workflow_start",
            agent_name=None,
            data={"task": task, "mode": mode.value}
        ))

        try:
            if mode == WorkflowMode.SEQUENTIAL:
                outputs = await self._execute_sequential(task, context)
            elif mode == WorkflowMode.DIRECT_BUILD:
                outputs = await self._execute_direct_build(task, context)
            elif mode == WorkflowMode.VERIFY_ONLY:
                outputs = await self._execute_verify_only(task, context)
            elif mode == WorkflowMode.SPEC_DRIVEN:
                outputs = await self._execute_spec_driven(task, context)
            elif mode == WorkflowMode.FULL_DEPLOY:
                outputs = await self._execute_full_deploy(task, context)
            elif mode == WorkflowMode.DEPLOY_ONLY:
                outputs = await self._execute_deploy_only(task, context)
            elif mode == WorkflowMode.FULL_POLISH:
                outputs = await self._execute_full_polish(task, context)
            elif mode == WorkflowMode.FULL_CAMPAIGN:
                outputs = await self._execute_full_campaign(task, context)
            elif mode == WorkflowMode.PROMOTE_ONLY:
                outputs = await self._execute_promote_only(task, context)

            # Update modes
            elif mode == WorkflowMode.UPDATE:
                outputs = await self._execute_update(task, context, UpdateType.MINOR)
            elif mode == WorkflowMode.UPDATE_PATCH:
                outputs = await self._execute_update(task, context, UpdateType.PATCH)
            elif mode == WorkflowMode.UPDATE_MINOR:
                outputs = await self._execute_update(task, context, UpdateType.MINOR)
            elif mode == WorkflowMode.UPDATE_MAJOR:
                outputs = await self._execute_update(task, context, UpdateType.MAJOR)
            elif mode == WorkflowMode.HOTFIX:
                outputs = await self._execute_hotfix(task, context)

            # Write files to disk if approved
            # For polish modes, check Finisher verdict; otherwise check Oracle
            write_result = None
            final_verdict = "N/A"
            needs_revision = False

            # Determine final verdict based on workflow
            if "finisher" in outputs:
                final_verdict = outputs["finisher"].artifacts.get("verdict", "N/A")
                needs_revision = final_verdict == "NEEDS_POLISH"
            elif "oracle" in outputs:
                final_verdict = outputs["oracle"].metadata.get("verdict", "N/A")
                needs_revision = outputs["oracle"].metadata.get("needs_revision", False)

            # Write files if approved
            if self.auto_write_files and "mason" in outputs and not needs_revision:
                project_dir = Path(context.get("project_dir")) if context.get("project_dir") else None
                write_result = self._write_generated_files(
                    task=task,
                    mason_output=outputs["mason"],
                    project_dir=project_dir,
                )
                if write_result:
                    outputs["files"] = write_result

            self._emit_event(WorkflowEvent(
                event_type="workflow_complete",
                agent_name=None,
                data={
                    "task": task,
                    "mode": mode.value,
                    "success": True,
                    "final_verdict": final_verdict,
                    "files_written": write_result.files_written if write_result else [],
                    "project_dir": write_result.project_dir if write_result else None,
                }
            ))

            # Run completion callbacks (GitHub sync, etc.)
            await self._run_completion_callbacks(task_id, outputs)

        except Exception as e:
            self._emit_event(WorkflowEvent(
                event_type="workflow_error",
                agent_name=None,
                data={"task": task, "error": str(e)}
            ))
            raise

        return outputs

    async def _execute_sequential(
        self,
        task: str,
        context: dict,
    ) -> dict[str, AgentOutput]:
        """Execute full sequential workflow: Sketch -> Tinker -> Oracle.

        Includes revision loop if Oracle rejects.
        """
        outputs = {}
        revision_count = 0

        # Phase 1: Architect plans
        self._emit_event(WorkflowEvent(
            event_type="agent_start",
            agent_name="architect",
            data={"task": task, "phase": "planning"}
        ))

        architect_output = await self.architect.process(task, context)
        outputs["architect"] = architect_output

        self._emit_event(WorkflowEvent(
            event_type="agent_complete",
            agent_name="architect",
            data={"task": task, "phase": "planning"}
        ))

        if architect_output.status == AgentStatus.ERROR:
            return outputs

        # Phase 2 & 3: Mason builds, Oracle verifies (with revision loop)
        mason_output = None
        oracle_output = None
        previous_output = architect_output

        while revision_count <= self.MAX_REVISIONS:
            # Mason builds
            self._emit_event(WorkflowEvent(
                event_type="agent_start",
                agent_name="mason",
                data={"task": task, "phase": "building", "revision": revision_count}
            ))

            mason_output = await self.mason.process(task, context, previous_output)
            outputs[f"mason_{revision_count}"] = mason_output

            self._emit_event(WorkflowEvent(
                event_type="agent_complete",
                agent_name="mason",
                data={"task": task, "phase": "building", "revision": revision_count}
            ))

            if mason_output.status == AgentStatus.ERROR:
                break

            # Oracle verifies
            self._emit_event(WorkflowEvent(
                event_type="agent_start",
                agent_name="oracle",
                data={"task": task, "phase": "verifying", "revision": revision_count}
            ))

            oracle_output = await self.oracle.process(task, context, mason_output)
            outputs[f"oracle_{revision_count}"] = oracle_output

            self._emit_event(WorkflowEvent(
                event_type="agent_complete",
                agent_name="oracle",
                data={
                    "task": task,
                    "phase": "verifying",
                    "revision": revision_count,
                    "verdict": oracle_output.metadata.get("verdict", "UNKNOWN")
                }
            ))

            # Check verdict
            if not oracle_output.metadata.get("needs_revision", False):
                break

            # Needs revision - prepare for next loop
            revision_count += 1
            previous_output = oracle_output

            if revision_count > self.MAX_REVISIONS:
                oracle_output.metadata["max_revisions_reached"] = True

        # Store final outputs
        outputs["mason"] = mason_output
        outputs["oracle"] = oracle_output

        return outputs

    async def _execute_direct_build(
        self,
        task: str,
        context: dict,
    ) -> dict[str, AgentOutput]:
        """Execute direct build: Tinker -> Oracle (skip planning)."""
        outputs = {}

        # Mason builds directly
        self._emit_event(WorkflowEvent(
            event_type="agent_start",
            agent_name="mason",
            data={"task": task, "phase": "direct_build"}
        ))

        mason_output = await self.mason.process(task, context)
        outputs["mason"] = mason_output

        self._emit_event(WorkflowEvent(
            event_type="agent_complete",
            agent_name="mason",
            data={"task": task, "phase": "direct_build"}
        ))

        if mason_output.status == AgentStatus.ERROR:
            return outputs

        # Oracle verifies
        self._emit_event(WorkflowEvent(
            event_type="agent_start",
            agent_name="oracle",
            data={"task": task, "phase": "verifying"}
        ))

        oracle_output = await self.oracle.process(task, context, mason_output)
        outputs["oracle"] = oracle_output

        self._emit_event(WorkflowEvent(
            event_type="agent_complete",
            agent_name="oracle",
            data={
                "task": task,
                "phase": "verifying",
                "verdict": oracle_output.metadata.get("verdict", "UNKNOWN")
            }
        ))

        return outputs

    async def _execute_verify_only(
        self,
        task: str,
        context: dict,
    ) -> dict[str, AgentOutput]:
        """Execute verification only: Oracle reviews existing code."""
        outputs = {}

        self._emit_event(WorkflowEvent(
            event_type="agent_start",
            agent_name="oracle",
            data={"task": task, "phase": "review"}
        ))

        # Oracle reviews the task/code directly
        oracle_output = await self.oracle.process(task, context)
        outputs["oracle"] = oracle_output

        self._emit_event(WorkflowEvent(
            event_type="agent_complete",
            agent_name="oracle",
            data={
                "task": task,
                "phase": "review",
                "verdict": oracle_output.metadata.get("verdict", "UNKNOWN")
            }
        ))

        return outputs

    async def _execute_spec_driven(
        self,
        task: str,
        context: dict,
    ) -> dict[str, AgentOutput]:
        """Execute spec-driven workflow: Generate spec then execute each task.

        1. Sketch generates a complete spec (requirements, design, tasks)
        2. For each task in the spec, runs Tinker -> Oracle
        3. Returns all outputs including the spec
        """
        outputs = {}

        # Phase 1: Architect generates spec
        self._emit_event(WorkflowEvent(
            event_type="agent_start",
            agent_name="architect",
            data={"task": task, "phase": "spec_generation"}
        ))

        output_dir = context.get("output_dir")
        spec_context = {
            "features": context.get("features", []),
            "technical": context.get("technical", ""),
            "constraints": context.get("constraints", ""),
        }

        spec, architect_output = await self.architect.generate_spec(
            task, spec_context, output_dir
        )
        outputs["architect"] = architect_output
        outputs["spec"] = spec

        self._emit_event(WorkflowEvent(
            event_type="agent_complete",
            agent_name="architect",
            data={
                "task": task,
                "phase": "spec_generation",
                "requirements_count": len(spec.requirements) if spec else 0,
                "tasks_count": len(spec.tasks.tasks) if spec and spec.tasks else 0,
            }
        ))

        if not spec or architect_output.status == AgentStatus.ERROR:
            return outputs

        # Phase 2: Execute each task through Mason -> Oracle
        if spec.tasks:
            for i, spec_task in enumerate(spec.tasks.tasks):
                task_context = {
                    **context,
                    "spec_name": spec.name,
                    "task_id": spec_task.id,
                    "task_title": spec_task.title,
                    "requirement_ids": spec_task.requirement_ids,
                    "design": spec.design.to_markdown() if spec.design else "",
                }

                task_prompt = f"""Execute spec task {spec_task.id}:

Task: {spec_task.title}
Description: {spec_task.description}
Priority: {spec_task.priority.value}
Requirements: {', '.join(spec_task.requirement_ids)}

Files to modify: {', '.join(spec_task.files_to_modify) if spec_task.files_to_modify else 'TBD'}
"""

                # Mason builds
                self._emit_event(WorkflowEvent(
                    event_type="agent_start",
                    agent_name="mason",
                    data={"task": spec_task.title, "phase": "building", "task_id": spec_task.id}
                ))

                mason_output = await self.mason.process(task_prompt, task_context, architect_output)
                outputs[f"mason_task_{spec_task.id}"] = mason_output

                self._emit_event(WorkflowEvent(
                    event_type="agent_complete",
                    agent_name="mason",
                    data={"task": spec_task.title, "phase": "building", "task_id": spec_task.id}
                ))

                if mason_output.status == AgentStatus.ERROR:
                    continue

                # Oracle verifies
                self._emit_event(WorkflowEvent(
                    event_type="agent_start",
                    agent_name="oracle",
                    data={"task": spec_task.title, "phase": "verifying", "task_id": spec_task.id}
                ))

                oracle_output = await self.oracle.process(task_prompt, task_context, mason_output)
                outputs[f"oracle_task_{spec_task.id}"] = oracle_output

                self._emit_event(WorkflowEvent(
                    event_type="agent_complete",
                    agent_name="oracle",
                    data={
                        "task": spec_task.title,
                        "phase": "verifying",
                        "task_id": spec_task.id,
                        "verdict": oracle_output.metadata.get("verdict", "UNKNOWN")
                    }
                ))

        return outputs

    async def _execute_full_deploy(
        self,
        task: str,
        context: dict,
    ) -> dict[str, AgentOutput]:
        """Execute full deployment workflow: Sketch -> Tinker -> Oracle -> Launch.

        Same as sequential but adds Launch at the end to generate deployment instructions.
        """
        # First run the standard sequential workflow
        outputs = await self._execute_sequential(task, context)

        # Only run Launch if Oracle approved
        if "oracle" in outputs:
            needs_revision = outputs["oracle"].metadata.get("needs_revision", False)
            if not needs_revision:
                # Get the latest mason output
                mason_output = outputs.get("mason") or outputs.get("mason_0")

                self._emit_event(WorkflowEvent(
                    event_type="agent_start",
                    agent_name="launch",
                    data={"task": task, "phase": "deployment"}
                ))

                launch_output = await self.launch.process(task, context, mason_output)
                outputs["launch"] = launch_output

                self._emit_event(WorkflowEvent(
                    event_type="agent_complete",
                    agent_name="launch",
                    data={
                        "task": task,
                        "phase": "deployment",
                        "platforms": launch_output.artifacts.get("platforms", [])
                    }
                ))

        return outputs

    async def _execute_deploy_only(
        self,
        task: str,
        context: dict,
    ) -> dict[str, AgentOutput]:
        """Execute deployment only: Launch generates deployment instructions.

        Use this when you have an existing build and just need deployment guidance.
        Pass the build output in context['build_output'] or as the task.
        """
        outputs = {}

        self._emit_event(WorkflowEvent(
            event_type="agent_start",
            agent_name="launch",
            data={"task": task, "phase": "deployment"}
        ))

        # Create a mock previous output if build_output provided in context
        previous_output = None
        if context.get("build_output"):
            previous_output = AgentOutput(content=context["build_output"])

        launch_output = await self.launch.process(task, context, previous_output)
        outputs["launch"] = launch_output

        self._emit_event(WorkflowEvent(
            event_type="agent_complete",
            agent_name="launch",
            data={
                "task": task,
                "phase": "deployment",
                "platforms": launch_output.artifacts.get("platforms", [])
            }
        ))

        return outputs

    async def _execute_full_polish(
        self,
        task: str,
        context: dict,
    ) -> dict[str, AgentOutput]:
        """Execute full polish workflow: Sketch -> Tinker -> Oracle -> Finisher.

        Same as sequential but adds Finisher at the end to verify shipping readiness.
        Products that pass Finisher are ready to sell.
        """
        # First run the standard sequential workflow
        outputs = await self._execute_sequential(task, context)

        # Only run Finisher if Oracle approved
        if "oracle" in outputs:
            needs_revision = outputs["oracle"].metadata.get("needs_revision", False)
            if not needs_revision:
                # Get the latest mason output
                mason_output = outputs.get("mason") or outputs.get("mason_0")

                self._emit_event(WorkflowEvent(
                    event_type="agent_start",
                    agent_name="finisher",
                    data={"task": task, "phase": "polish_verification"}
                ))

                # Build context for Finisher with Mason's output
                finisher_context = {
                    **context,
                    "mason_output": mason_output.content if mason_output else None,
                }

                finisher_output = await self.finisher.process(
                    task, finisher_context, outputs["oracle"]
                )
                outputs["finisher"] = finisher_output

                self._emit_event(WorkflowEvent(
                    event_type="agent_complete",
                    agent_name="finisher",
                    data={
                        "task": task,
                        "phase": "polish_verification",
                        "verdict": finisher_output.artifacts.get("verdict", "UNKNOWN"),
                        "shipping_ready": finisher_output.artifacts.get("shipping_ready", False),
                    }
                ))

        return outputs

    async def _execute_full_campaign(
        self,
        task: str,
        context: dict,
    ) -> dict[str, AgentOutput]:
        """Execute full campaign workflow: Sketch -> Tinker -> Oracle -> Finisher -> Launch -> Hype.

        The complete workflow for creating, polishing, deploying, and promoting a product.
        Only proceeds to Launch and Hype if Finisher approves.
        """
        # First run the polish workflow
        outputs = await self._execute_full_polish(task, context)

        # Only run Launch + Hype if Finisher approved (ready to ship)
        if "finisher" in outputs:
            shipping_ready = outputs["finisher"].artifacts.get("shipping_ready", False)
            if shipping_ready:
                # Get the latest mason output
                mason_output = outputs.get("mason") or outputs.get("mason_0")

                # Launch: Generate deployment instructions
                self._emit_event(WorkflowEvent(
                    event_type="agent_start",
                    agent_name="launch",
                    data={"task": task, "phase": "deployment"}
                ))

                launch_output = await self.launch.process(task, context, mason_output)
                outputs["launch"] = launch_output

                self._emit_event(WorkflowEvent(
                    event_type="agent_complete",
                    agent_name="launch",
                    data={
                        "task": task,
                        "phase": "deployment",
                        "platforms": launch_output.artifacts.get("platforms", [])
                    }
                ))

                # Hype: Generate marketing and promotion
                self._emit_event(WorkflowEvent(
                    event_type="agent_start",
                    agent_name="hype",
                    data={"task": task, "phase": "promotion"}
                ))

                hype_output = await self.hype.process(task, context, launch_output)
                outputs["hype"] = hype_output

                self._emit_event(WorkflowEvent(
                    event_type="agent_complete",
                    agent_name="hype",
                    data={
                        "task": task,
                        "phase": "promotion",
                    }
                ))

        return outputs

    async def _execute_promote_only(
        self,
        task: str,
        context: dict,
    ) -> dict[str, AgentOutput]:
        """Execute promotion only: Hype generates marketing content.

        Use this when you have an existing product and just need marketing materials.
        Pass product info in context['product_info'] or as the task.
        """
        outputs = {}

        self._emit_event(WorkflowEvent(
            event_type="agent_start",
            agent_name="hype",
            data={"task": task, "phase": "promotion"}
        ))

        # Create a mock previous output if product_info provided in context
        previous_output = None
        if context.get("product_info"):
            previous_output = AgentOutput(content=context["product_info"])

        hype_output = await self.hype.process(task, context, previous_output)
        outputs["hype"] = hype_output

        self._emit_event(WorkflowEvent(
            event_type="agent_complete",
            agent_name="hype",
            data={
                "task": task,
                "phase": "promotion",
            }
        ))

        return outputs

    async def _execute_update(
        self,
        task: str,
        context: dict,
        update_type: UpdateType = UpdateType.MINOR,
    ) -> dict[str, AgentOutput]:
        """Execute an update workflow for an existing product.

        This workflow:
        1. Creates update context from existing product info
        2. Runs Mason with update-aware prompting
        3. Runs Oracle to verify the update
        4. Generates changelog entry
        5. Optionally runs Finisher for polish updates

        Args:
            task: Description of what to update
            context: Must contain 'current_version' and optionally 'existing_code'
            update_type: Type of update (PATCH, MINOR, MAJOR)

        Returns:
            Outputs including changelog
        """
        outputs = {}

        # Build update context
        current_version = Version.parse(context.get("current_version", "1.0.0"))
        project_name = context.get("project_name", self._extract_project_name(task))

        update_context = UpdateContext(
            project_name=project_name,
            current_version=current_version,
            update_type=update_type,
            change_description=task,
            existing_code=context.get("existing_code"),
            existing_files=context.get("existing_files"),
            issues_to_fix=context.get("issues", []),
            user_feedback=context.get("feedback"),
        )

        # Store update context for agents
        context["update_context"] = update_context
        context["is_update"] = True
        context["update_prompt"] = update_context.to_prompt_context()

        self._emit_event(WorkflowEvent(
            event_type="workflow_start",
            agent_name=None,
            data={
                "task": task,
                "mode": f"update_{update_type.value}",
                "current_version": str(current_version),
                "target_version": str(update_context.target_version),
            }
        ))

        # For MAJOR updates, run planning first
        if update_type == UpdateType.MAJOR:
            self._emit_event(WorkflowEvent(
                event_type="agent_start",
                agent_name="architect",
                data={"task": task, "phase": "update_planning"}
            ))

            architect_output = await self.architect.process(task, context)
            outputs["architect"] = architect_output

            self._emit_event(WorkflowEvent(
                event_type="agent_complete",
                agent_name="architect",
                data={"task": task, "phase": "update_planning"}
            ))

            if architect_output.status == AgentStatus.ERROR:
                return outputs

            previous_output = architect_output
        else:
            previous_output = None

        # Mason implements the update
        self._emit_event(WorkflowEvent(
            event_type="agent_start",
            agent_name="mason",
            data={"task": task, "phase": "updating", "update_type": update_type.value}
        ))

        mason_output = await self.mason.process(task, context, previous_output)
        outputs["mason"] = mason_output

        self._emit_event(WorkflowEvent(
            event_type="agent_complete",
            agent_name="mason",
            data={"task": task, "phase": "updating"}
        ))

        if mason_output.status == AgentStatus.ERROR:
            return outputs

        # Oracle verifies the update
        self._emit_event(WorkflowEvent(
            event_type="agent_start",
            agent_name="oracle",
            data={"task": task, "phase": "verifying_update"}
        ))

        oracle_output = await self.oracle.process(task, context, mason_output)
        outputs["oracle"] = oracle_output

        self._emit_event(WorkflowEvent(
            event_type="agent_complete",
            agent_name="oracle",
            data={
                "task": task,
                "phase": "verifying_update",
                "verdict": oracle_output.metadata.get("verdict", "UNKNOWN")
            }
        ))

        # Run Finisher for MINOR and MAJOR updates (not PATCH - those are quick fixes)
        if not oracle_output.metadata.get("needs_revision", False):
            if update_type in (UpdateType.MINOR, UpdateType.MAJOR):
                self._emit_event(WorkflowEvent(
                    event_type="agent_start",
                    agent_name="finisher",
                    data={"task": task, "phase": "update_polish"}
                ))

                # Build context for Finisher with Mason's output
                finisher_context = {
                    **context,
                    "mason_output": mason_output.content if mason_output else None,
                }

                finisher_output = await self.finisher.process(
                    task, finisher_context, oracle_output
                )
                outputs["finisher"] = finisher_output

                self._emit_event(WorkflowEvent(
                    event_type="agent_complete",
                    agent_name="finisher",
                    data={
                        "task": task,
                        "phase": "update_polish",
                        "verdict": finisher_output.artifacts.get("verdict", "UNKNOWN"),
                        "shipping_ready": finisher_output.artifacts.get("shipping_ready", False),
                    }
                ))

                # If Finisher says needs polish, don't generate changelog yet
                if finisher_output.artifacts.get("verdict") == "NEEDS_POLISH":
                    return outputs

        # Generate changelog if approved (by Oracle for PATCH, by Finisher for MINOR/MAJOR)
        if not oracle_output.metadata.get("needs_revision", False):
            changelog_gen = get_changelog_generator()
            agent_outputs_content = {
                name: output.content for name, output in outputs.items()
                if hasattr(output, 'content')
            }
            changelog_release = changelog_gen.generate_release(
                update_context, agent_outputs_content
            )

            outputs["changelog"] = AgentOutput(
                content=changelog_release.to_markdown(),
                artifacts={
                    "version": str(update_context.target_version),
                    "previous_version": str(current_version),
                    "update_type": update_type.value,
                    "entries_count": len(changelog_release.entries),
                },
                metadata={"type": "changelog"},
            )

            self._emit_event(WorkflowEvent(
                event_type="changelog_generated",
                agent_name="system",
                data={
                    "version": str(update_context.target_version),
                    "entries": len(changelog_release.entries),
                }
            ))

        return outputs

    async def _execute_hotfix(
        self,
        task: str,
        context: dict,
    ) -> dict[str, AgentOutput]:
        """Execute a hotfix workflow - fast-tracked urgent fix.

        Hotfixes skip planning and use minimal verification for speed.
        Use for critical security fixes or breaking bugs in production.

        Args:
            task: Description of the urgent fix needed
            context: Should contain 'current_version' and 'existing_code'

        Returns:
            Outputs including changelog
        """
        outputs = {}

        # Build hotfix context
        current_version = Version.parse(context.get("current_version", "1.0.0"))
        project_name = context.get("project_name", self._extract_project_name(task))

        update_context = UpdateContext(
            project_name=project_name,
            current_version=current_version,
            update_type=UpdateType.HOTFIX,
            change_description=f"[HOTFIX] {task}",
            existing_code=context.get("existing_code"),
            existing_files=context.get("existing_files"),
            issues_to_fix=[task],
        )

        context["update_context"] = update_context
        context["is_update"] = True
        context["is_hotfix"] = True
        context["update_prompt"] = update_context.to_prompt_context()

        self._emit_event(WorkflowEvent(
            event_type="workflow_start",
            agent_name=None,
            data={
                "task": task,
                "mode": "hotfix",
                "current_version": str(current_version),
                "target_version": str(update_context.target_version),
                "urgent": True,
            }
        ))

        # Direct to Mason - no planning for hotfixes
        self._emit_event(WorkflowEvent(
            event_type="agent_start",
            agent_name="mason",
            data={"task": task, "phase": "hotfix", "urgent": True}
        ))

        mason_output = await self.mason.process(task, context)
        outputs["mason"] = mason_output

        self._emit_event(WorkflowEvent(
            event_type="agent_complete",
            agent_name="mason",
            data={"task": task, "phase": "hotfix"}
        ))

        if mason_output.status == AgentStatus.ERROR:
            return outputs

        # Quick Oracle verification (still needed for safety)
        self._emit_event(WorkflowEvent(
            event_type="agent_start",
            agent_name="oracle",
            data={"task": task, "phase": "hotfix_verify"}
        ))

        oracle_output = await self.oracle.process(task, context, mason_output)
        outputs["oracle"] = oracle_output

        self._emit_event(WorkflowEvent(
            event_type="agent_complete",
            agent_name="oracle",
            data={
                "task": task,
                "phase": "hotfix_verify",
                "verdict": oracle_output.metadata.get("verdict", "UNKNOWN")
            }
        ))

        # Generate changelog for hotfix
        if not oracle_output.metadata.get("needs_revision", False):
            changelog_gen = get_changelog_generator()
            agent_outputs_content = {
                name: output.content for name, output in outputs.items()
                if hasattr(output, 'content')
            }
            changelog_release = changelog_gen.generate_release(
                update_context, agent_outputs_content
            )

            outputs["changelog"] = AgentOutput(
                content=changelog_release.to_markdown(),
                artifacts={
                    "version": str(update_context.target_version),
                    "previous_version": str(current_version),
                    "update_type": "hotfix",
                    "entries_count": len(changelog_release.entries),
                    "urgent": True,
                },
                metadata={"type": "changelog"},
            )

        return outputs

    async def stream_workflow(
        self,
        task: str,
        mode: WorkflowMode = WorkflowMode.SEQUENTIAL,
        context: Optional[dict] = None,
    ) -> AsyncIterator[tuple[str, str]]:
        """Stream workflow execution, yielding agent outputs as they complete.

        Args:
            task: The task to execute
            mode: Workflow mode to use
            context: Optional context for agents

        Yields:
            Tuples of (agent_name, content_chunk)
        """
        context = context or {}

        if mode == WorkflowMode.SEQUENTIAL:
            # Stream Architect
            yield ("architect", "## Sketch - Planning\n\n")
            async for chunk in self.architect.stream_process(task, context):
                yield ("architect", chunk)

            # Get full output for next agent
            architect_output = await self.architect.process(task, context)

            # Stream Mason
            yield ("mason", "\n\n## Tinker - Building\n\n")
            async for chunk in self.mason.stream_process(task, context, architect_output):
                yield ("mason", chunk)

            mason_output = await self.mason.process(task, context, architect_output)

            # Stream Oracle
            yield ("oracle", "\n\n## Oracle - Verifying\n\n")
            async for chunk in self.oracle.stream_process(task, context, mason_output):
                yield ("oracle", chunk)

        elif mode == WorkflowMode.DIRECT_BUILD:
            # Stream Mason
            yield ("mason", "## Tinker - Building\n\n")
            async for chunk in self.mason.stream_process(task, context):
                yield ("mason", chunk)

            mason_output = await self.mason.process(task, context)

            # Stream Oracle
            yield ("oracle", "\n\n## Oracle - Verifying\n\n")
            async for chunk in self.oracle.stream_process(task, context, mason_output):
                yield ("oracle", chunk)

        elif mode == WorkflowMode.VERIFY_ONLY:
            # Stream Oracle only
            yield ("oracle", "## Oracle - Review\n\n")
            async for chunk in self.oracle.stream_process(task, context):
                yield ("oracle", chunk)
