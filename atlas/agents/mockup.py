"""Mockup Agent - Visual Preview Creation for ATLAS.

The Mockup agent creates polished visual previews BEFORE building begins.
This ensures the user sees and approves what they're getting before
committing to the build phase.

Mockups should be:
- Polished, not rough sketches
- Close to final appearance
- Detailed enough to judge sellability
- Interactive where appropriate (web/app)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from atlas.agents.base import BaseAgent


class MockupType(Enum):
    """Types of mockups based on product type."""
    STATIC_IMAGE = "static_image"      # For printables, documents
    INTERACTIVE_HTML = "interactive_html"  # For web products
    APP_SCREENS = "app_screens"        # For mobile apps
    VIDEO = "video"                    # For complex interactions


@dataclass
class MockupOutput:
    """Output from the Mockup agent."""

    # Type of mockup
    mockup_type: MockupType

    # Content based on type
    images: list[str] = field(default_factory=list)  # Base64 or URLs
    html: str = ""  # For interactive mockups
    screens: list[dict] = field(default_factory=list)  # For app mockups

    # Preview
    preview_url: str = ""
    preview_html: str = ""

    # Design details
    color_palette: list[str] = field(default_factory=list)
    typography: dict[str, str] = field(default_factory=dict)
    layout_description: str = ""

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "mockup_type": self.mockup_type.value,
            "images": self.images,
            "html": self.html,
            "screens": self.screens,
            "preview_url": self.preview_url,
            "preview_html": self.preview_html,
            "color_palette": self.color_palette,
            "typography": self.typography,
            "layout_description": self.layout_description,
            "created_at": self.created_at.isoformat(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MockupOutput":
        return cls(
            mockup_type=MockupType(data.get("mockup_type", "static_image")),
            images=data.get("images", []),
            html=data.get("html", ""),
            screens=data.get("screens", []),
            preview_url=data.get("preview_url", ""),
            preview_html=data.get("preview_html", ""),
            color_palette=data.get("color_palette", []),
            typography=data.get("typography", {}),
            layout_description=data.get("layout_description", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            notes=data.get("notes", ""),
        )


class MockupAgent(BaseAgent):
    """Mockup agent for ATLAS.

    Creates polished visual previews before building begins.
    The user must approve the mockup before the build phase starts.
    """

    name = "mockup"
    description = "Visual preview creator"
    icon = "🎨"
    color = "#9C27B0"

    async def process(self, task, context=None, previous_output=None):
        """Process is required by BaseAgent but Mockup uses create_mockup()."""
        raise NotImplementedError("Use create_mockup() or revise_mockup() methods")

    def get_system_prompt(self) -> str:
        """Get the system prompt for Mockup."""
        return """ATLAS is a product studio that combines human creativity with ethical AI
to build transformative solutions for our clients and the public.

You are the Mockup Agent - the visual preview creator. Your job is to create
POLISHED visual mockups BEFORE any building begins. The user must see and
approve what they're getting before committing to the build phase.

Your responsibilities:
1. Create high-fidelity visual mockups based on the Business Brief and plan
2. Show what the final product will look like (not rough sketches)
3. Include design details: colors, typography, layout
4. For interactive products (web/app), create clickable prototypes
5. Provide multiple views/pages as needed

Key principles:
- POLISHED, not rough - this is what the user is committing to
- SELLABLE appearance - would a customer pay for something that looks like this?
- ACCURATE representation - don't promise what can't be built
- DETAILED enough to judge - include real content, not lorem ipsum

Output format varies by product type:
- Printables: High-quality images of each page
- Documents: Cover + sample pages
- Web: Interactive HTML preview
- Apps: Screen mockups with navigation flow

The user MUST approve this mockup before building begins."""

    async def create_mockup(
        self,
        brief: dict,
        plan: dict,
        product_type: str,
    ) -> MockupOutput:
        """Create a polished mockup for user approval.

        Args:
            brief: The Business Brief
            plan: The build plan
            product_type: Type of product (planner, web_spa, etc.)

        Returns:
            MockupOutput with visual preview
        """
        # TODO: Implement in Phase 3/4
        # This will:
        # 1. Determine appropriate mockup type based on product
        # 2. Generate visual mockup using design templates
        # 3. Create preview (images, HTML, or app screens)
        # 4. Include design specifications
        raise NotImplementedError("Mockup.create_mockup() will be implemented in Phase 3/4")

    async def revise_mockup(
        self,
        current_mockup: MockupOutput,
        feedback: str,
        brief: dict,
    ) -> MockupOutput:
        """Revise a mockup based on user feedback.

        Args:
            current_mockup: The current mockup to revise
            feedback: User feedback on what to change
            brief: The Business Brief for context

        Returns:
            Revised MockupOutput
        """
        # TODO: Implement in Phase 3/4
        raise NotImplementedError("Mockup.revise_mockup() will be implemented in Phase 3/4")

    def get_mockup_type_for_product(self, product_type: str) -> MockupType:
        """Determine the appropriate mockup type for a product.

        Args:
            product_type: Type of product

        Returns:
            MockupType to use
        """
        product_type = product_type.lower()

        # Printables and documents -> static images
        if any(t in product_type for t in ["planner", "card", "worksheet", "book", "guide", "manual", "document"]):
            return MockupType.STATIC_IMAGE

        # Web products -> interactive HTML
        if any(t in product_type for t in ["web", "landing", "spa", "dashboard", "site"]):
            return MockupType.INTERACTIVE_HTML

        # Mobile apps -> app screens
        if any(t in product_type for t in ["mobile", "ios", "android", "app"]):
            return MockupType.APP_SCREENS

        # Default to static
        return MockupType.STATIC_IMAGE
