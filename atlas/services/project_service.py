"""Project service - business logic for project management."""

import os
import logging
from typing import Optional, Any
from pathlib import Path

logger = logging.getLogger("atlas.services.project")


class ProjectService:
    """Service layer for project-related business logic.

    Separates business logic from HTTP route handlers for better
    testability and code organization.
    """

    def __init__(self, project_manager, agent_manager=None):
        """Initialize project service.

        Args:
            project_manager: ProjectManager instance for data access
            agent_manager: Optional AgentManager for AI operations
        """
        self.project_manager = project_manager
        self.agent_manager = agent_manager

    @staticmethod
    def get_openai_key() -> Optional[str]:
        """Get OpenAI API key from environment or config.

        Returns:
            API key string or None if not found
        """
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
            logger.debug("OpenAI API key not found in config")
            return None

    async def get_project(self, project_id: int) -> Optional[dict]:
        """Get a project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project dict or None if not found
        """
        if not self.project_manager:
            return None

        try:
            return await self.project_manager.get_project(project_id)
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            return None

    async def list_projects(self, include_tasks: bool = True) -> list[dict]:
        """List all projects.

        Args:
            include_tasks: Whether to include task counts

        Returns:
            List of project dicts
        """
        if not self.project_manager:
            return []

        try:
            return await self.project_manager.get_projects(include_tasks=include_tasks)
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return []

    async def get_stats(self) -> dict:
        """Get project statistics.

        Returns:
            Statistics dict
        """
        if not self.project_manager:
            return {}

        try:
            return await self.project_manager.get_stats()
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    async def create_project(
        self,
        name: str,
        description: str = "",
        idea: str = "",
    ) -> Optional[int]:
        """Create a new project.

        Args:
            name: Project name
            description: Project description
            idea: Original idea text

        Returns:
            Project ID or None on failure
        """
        if not self.project_manager:
            logger.error("No project manager available")
            return None

        try:
            project_id = await self.project_manager.create_project(
                name=name,
                description=description,
                idea=idea,
            )
            logger.info(f"Created project {project_id}: {name}")
            return project_id
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return None

    async def update_project(
        self,
        project_id: int,
        **updates: Any,
    ) -> bool:
        """Update a project.

        Args:
            project_id: Project ID
            **updates: Fields to update

        Returns:
            True on success
        """
        if not self.project_manager:
            return False

        try:
            await self.project_manager.update_project(project_id, **updates)
            logger.info(f"Updated project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}")
            return False

    async def delete_project(self, project_id: int, reason: str = "") -> bool:
        """Delete a project.

        Args:
            project_id: Project ID
            reason: Optional deletion reason

        Returns:
            True on success
        """
        if not self.project_manager:
            return False

        try:
            await self.project_manager.delete_project(project_id)
            logger.info(f"Deleted project {project_id}. Reason: {reason or 'Not specified'}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            return False

    async def get_conversation(self, project_id: int) -> Optional[list]:
        """Get conversation history for a project.

        Args:
            project_id: Project ID

        Returns:
            List of conversation messages or None
        """
        if not self.project_manager:
            return None

        try:
            return await self.project_manager.get_conversation(project_id)
        except Exception as e:
            logger.error(f"Failed to get conversation for project {project_id}: {e}")
            return None

    async def add_conversation_message(
        self,
        project_id: int,
        role: str,
        content: str,
    ) -> bool:
        """Add a message to project conversation.

        Args:
            project_id: Project ID
            role: Message role (user/assistant)
            content: Message content

        Returns:
            True on success
        """
        if not self.project_manager:
            return False

        try:
            await self.project_manager.add_conversation_message(
                project_id, role, content
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add message to project {project_id}: {e}")
            return False

    def calculate_cost(self, project: dict) -> dict:
        """Calculate cost breakdown for a project.

        Args:
            project: Project dict with token usage data

        Returns:
            Cost breakdown dict
        """
        # Token pricing (approximate, in USD per 1K tokens)
        pricing = {
            "gpt-4o": {"input": 0.0025, "output": 0.01},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "gemini-pro": {"input": 0.00025, "output": 0.0005},
            "ollama": {"input": 0, "output": 0},  # Local, no cost
        }

        phases = project.get("phases", {})
        total_input = 0
        total_output = 0
        total_cost = 0.0

        phase_costs = {}

        for phase_name, phase_data in phases.items():
            if isinstance(phase_data, dict):
                input_tokens = phase_data.get("input_tokens", 0)
                output_tokens = phase_data.get("output_tokens", 0)
                model = phase_data.get("model", "gpt-4o-mini")

                model_pricing = pricing.get(model, pricing["gpt-4o-mini"])
                phase_cost = (
                    (input_tokens / 1000) * model_pricing["input"] +
                    (output_tokens / 1000) * model_pricing["output"]
                )

                phase_costs[phase_name] = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "model": model,
                    "cost": round(phase_cost, 4),
                }

                total_input += input_tokens
                total_output += output_tokens
                total_cost += phase_cost

        return {
            "phases": phase_costs,
            "totals": {
                "input_tokens": total_input,
                "output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "cost_usd": round(total_cost, 4),
            },
            "pricing": pricing,
        }
