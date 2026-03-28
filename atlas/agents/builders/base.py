"""Base builder class for all specialized builders.

All builders inherit from this class and implement product-specific logic.
Shared functionality lives here - change once, affects all builders.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from atlas.agents.base import BaseAgent


class BuilderType(Enum):
    """Types of specialized builders."""
    PRINTABLE = "printable"      # Planners, cards, worksheets
    DOCUMENT = "document"        # Books, guides, manuals
    WEB = "web"                  # Landing pages, SPAs, dashboards
    APP = "app"                  # Mobile apps (React Native)


class OutputFormat(Enum):
    """Output formats for built products."""
    PDF = "pdf"
    HTML = "html"
    EPUB = "epub"
    REACT_NATIVE = "react_native"
    JSON = "json"


@dataclass
class BuildOutput:
    """Output from a builder."""
    content: str
    format: OutputFormat
    files: dict[str, str] = field(default_factory=dict)  # filename -> content
    preview_url: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "format": self.format.value,
            "files": self.files,
            "preview_url": self.preview_url,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class BuildContext:
    """Context passed to builders containing all necessary information."""
    project_name: str
    project_description: str
    business_brief: dict[str, Any]
    mockup: Optional[dict[str, Any]] = None
    plan: Optional[dict[str, Any]] = None
    user_preferences: dict[str, Any] = field(default_factory=dict)
    previous_outputs: list[dict] = field(default_factory=list)
    debate_summary: Optional[str] = None  # Summary from agent debate

    @classmethod
    def from_project(cls, project, business_brief: dict) -> "BuildContext":
        """Create context from a project and its business brief."""
        return cls(
            project_name=project.name,
            project_description=project.description,
            business_brief=business_brief,
            mockup=project.metadata.get("mockup") if project.metadata else None,
            plan=project.metadata.get("plan") if project.metadata else None,
        )


class BaseBuilder(BaseAgent, ABC):
    """Base class for all specialized builders.

    Builders are responsible for creating actual products from plans and mockups.
    Each builder type (Printable, Document, Web, App) extends this class.

    Key responsibilities:
    - Build products based on approved mockups
    - Follow the business brief requirements
    - Produce sellable output, not just working code
    - Generate preview-able results
    """

    builder_type: BuilderType
    supported_formats: list[OutputFormat]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._validate_config()

    def _validate_config(self):
        """Validate builder configuration."""
        if not hasattr(self, 'builder_type'):
            raise ValueError(f"{self.__class__.__name__} must define builder_type")
        if not hasattr(self, 'supported_formats'):
            raise ValueError(f"{self.__class__.__name__} must define supported_formats")

    @abstractmethod
    async def build(self, context: BuildContext) -> BuildOutput:
        """Build the product.

        Args:
            context: All information needed to build the product

        Returns:
            BuildOutput with the built product
        """
        pass

    @abstractmethod
    async def generate_preview(self, output: BuildOutput) -> str:
        """Generate a preview URL or HTML for the built product.

        Args:
            output: The build output to preview

        Returns:
            URL or HTML string for preview
        """
        pass

    async def validate_output(self, output: BuildOutput, context: BuildContext) -> dict:
        """Validate the build output against the business brief.

        Args:
            output: The build output to validate
            context: The build context with requirements

        Returns:
            Validation result with pass/fail and details
        """
        # Default validation - builders can override for specific checks
        issues = []

        if not output.content:
            issues.append("No content generated")

        if output.format not in self.supported_formats:
            issues.append(f"Unsupported format: {output.format}")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "checked_at": datetime.now().isoformat(),
        }

    def get_system_prompt(self) -> str:
        """Get the system prompt for this builder.

        Includes the mission and builder-specific context.
        """
        mission = """ATLAS is a product studio that combines human creativity with ethical AI
to build transformative solutions for our clients and the public.

You are a specialized builder. Your job is to create SELLABLE products, not just working code.
Every output must be something a customer would pay for."""

        builder_context = self._get_builder_context()

        return f"{mission}\n\n{builder_context}"

    @abstractmethod
    def _get_builder_context(self) -> str:
        """Get builder-specific context for the system prompt."""
        pass
