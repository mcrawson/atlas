"""Amazon Kindle Direct Publishing (KDP) integration.

KDP allows self-publishing:
- Ebooks (Kindle)
- Paperbacks
- Hardcovers

Note: KDP doesn't have a public API for publishing.
This integration provides validation and guidance.

Use cases in ATLAS:
- Validating book requirements
- Generating KDP-ready files
- Cover dimension calculations
- ISBN management guidance
"""

import os
import logging
from typing import Optional

from .base import (
    PlatformIntegration,
    PlatformCategory,
    Requirement,
    RequirementType,
    ValidationResult,
    SubmissionResult,
    SubmissionStatus,
)

logger = logging.getLogger(__name__)


# KDP specifications
KDP_SPECS = {
    "ebook": {
        "formats": ["epub", "mobi", "kpf", "doc", "docx", "pdf"],
        "cover": {
            "width": 1600,
            "height": 2560,
            "min_width": 625,
            "min_height": 1000,
            "max_size_mb": 50,
            "format": ["jpg", "tiff"],
            "dpi": 300,
        },
    },
    "paperback": {
        "trim_sizes": [
            {"width": 5, "height": 8, "name": "5x8"},
            {"width": 5.25, "height": 8, "name": "5.25x8"},
            {"width": 5.5, "height": 8.5, "name": "5.5x8.5"},
            {"width": 6, "height": 9, "name": "6x9"},
            {"width": 6.14, "height": 9.21, "name": "6.14x9.21"},
            {"width": 6.69, "height": 9.61, "name": "6.69x9.61"},
            {"width": 7, "height": 10, "name": "7x10"},
            {"width": 7.44, "height": 9.69, "name": "7.44x9.69"},
            {"width": 7.5, "height": 9.25, "name": "7.5x9.25"},
            {"width": 8, "height": 10, "name": "8x10"},
            {"width": 8.25, "height": 6, "name": "8.25x6"},
            {"width": 8.25, "height": 8.25, "name": "8.25x8.25"},
            {"width": 8.5, "height": 8.5, "name": "8.5x8.5"},
            {"width": 8.5, "height": 11, "name": "8.5x11"},
        ],
        "bleed": 0.125,  # inches
        "spine_width_per_page": 0.0025,  # inches per page (white paper)
        "cover_format": "pdf",
        "interior_format": "pdf",
        "dpi": 300,
    },
    "hardcover": {
        "trim_sizes": [
            {"width": 5.5, "height": 8.5, "name": "5.5x8.5"},
            {"width": 6, "height": 9, "name": "6x9"},
            {"width": 6.14, "height": 9.21, "name": "6.14x9.21"},
            {"width": 7, "height": 10, "name": "7x10"},
            {"width": 8.25, "height": 11, "name": "8.25x11"},
        ],
        "case_laminate_wrap": 0.625,  # inches wrap around
    },
}


def calculate_spine_width(page_count: int, paper_type: str = "white") -> float:
    """Calculate spine width based on page count.

    Args:
        page_count: Number of pages (must be even)
        paper_type: "white" or "cream"

    Returns:
        Spine width in inches
    """
    if paper_type == "cream":
        return page_count * 0.0025
    return page_count * 0.002252  # white paper


def calculate_cover_dimensions(
    trim_width: float,
    trim_height: float,
    page_count: int,
    paper_type: str = "white",
    bleed: float = 0.125,
) -> dict:
    """Calculate full cover dimensions including spine.

    Args:
        trim_width: Book width in inches
        trim_height: Book height in inches
        page_count: Number of pages
        paper_type: "white" or "cream"
        bleed: Bleed in inches

    Returns:
        Dict with cover dimensions
    """
    spine_width = calculate_spine_width(page_count, paper_type)

    cover_width = (trim_width * 2) + spine_width + (bleed * 2)
    cover_height = trim_height + (bleed * 2)

    return {
        "width_inches": round(cover_width, 3),
        "height_inches": round(cover_height, 3),
        "width_pixels": int(cover_width * 300),
        "height_pixels": int(cover_height * 300),
        "spine_width_inches": round(spine_width, 3),
        "spine_width_pixels": int(spine_width * 300),
        "bleed_inches": bleed,
        "dpi": 300,
    }


class AmazonKDPIntegration(PlatformIntegration):
    """Amazon Kindle Direct Publishing integration."""

    name = "Amazon KDP"
    icon = "📚"
    category = PlatformCategory.PUBLISHING
    description = "Publish ebooks and paperbacks on Amazon"
    docs_url = "https://kdp.amazon.com/help"

    supported_types = ["document", "doc_book", "doc_ebook"]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        # KDP doesn't have a public API, but we track user's account status
        self.has_account = config.get("has_kdp_account", False) if config else False

    def get_env_vars(self) -> list[str]:
        return []  # No API credentials needed

    async def authenticate(self) -> bool:
        """KDP doesn't have API auth.

        Returns True to indicate we can provide guidance.
        """
        self._authenticated = True
        return True

    def get_requirements(self, project_type: str) -> list[Requirement]:
        """Get KDP requirements based on book type."""
        requirements = [
            Requirement(
                name="kdp_account",
                type=RequirementType.CREDENTIAL,
                description="Amazon KDP account (free to create)",
                required=True,
            ),
            Requirement(
                name="book_title",
                type=RequirementType.TEXT,
                description="Book title",
                required=True,
            ),
            Requirement(
                name="book_description",
                type=RequirementType.TEXT,
                description="Book description (max 4000 characters)",
                required=True,
                specs={"max_length": 4000},
            ),
            Requirement(
                name="author_name",
                type=RequirementType.TEXT,
                description="Author name",
                required=True,
            ),
            Requirement(
                name="book_content",
                type=RequirementType.FILE,
                description="Book manuscript (DOCX, PDF, or EPUB)",
                required=True,
            ),
            Requirement(
                name="book_cover",
                type=RequirementType.IMAGE,
                description="Book cover image",
                required=True,
                specs=KDP_SPECS["ebook"]["cover"],
            ),
        ]

        if project_type in ["doc_book"]:
            # Paperback-specific requirements
            requirements.extend([
                Requirement(
                    name="trim_size",
                    type=RequirementType.CONFIG,
                    description="Book trim size (e.g., 6x9)",
                    required=True,
                    specs={"options": [s["name"] for s in KDP_SPECS["paperback"]["trim_sizes"]]},
                ),
                Requirement(
                    name="page_count",
                    type=RequirementType.CONFIG,
                    description="Page count (must be 24-828 pages)",
                    required=True,
                    specs={"min": 24, "max": 828},
                ),
                Requirement(
                    name="interior_pdf",
                    type=RequirementType.FILE,
                    description="Interior PDF (print-ready)",
                    required=True,
                ),
                Requirement(
                    name="cover_pdf",
                    type=RequirementType.FILE,
                    description="Cover PDF with spine (print-ready)",
                    required=True,
                ),
            ])

        # Optional but recommended
        requirements.extend([
            Requirement(
                name="isbn",
                type=RequirementType.TEXT,
                description="ISBN (KDP can provide free one)",
                required=False,
            ),
            Requirement(
                name="keywords",
                type=RequirementType.TEXT,
                description="Search keywords (up to 7)",
                required=False,
                specs={"max_count": 7},
            ),
            Requirement(
                name="categories",
                type=RequirementType.CONFIG,
                description="BISAC categories (up to 2)",
                required=False,
                specs={"max_count": 2},
            ),
        ])

        return requirements

    def validate(self, product: dict, project_type: str) -> ValidationResult:
        """Validate book against KDP requirements."""
        missing = []
        warnings = []
        errors = []

        metadata = product.get("metadata", {})
        content = product.get("content", {})
        assets = product.get("assets", {})

        # Check title
        if not metadata.get("title"):
            missing.append(Requirement(
                name="book_title",
                type=RequirementType.TEXT,
                description="Book title is required",
                required=True,
            ))

        # Check description
        description = metadata.get("description", "")
        if not description:
            missing.append(Requirement(
                name="book_description",
                type=RequirementType.TEXT,
                description="Book description is required",
                required=True,
            ))
        elif len(description) > 4000:
            errors.append(f"Description too long: {len(description)}/4000 characters")

        # Check author
        if not metadata.get("author"):
            missing.append(Requirement(
                name="author_name",
                type=RequirementType.TEXT,
                description="Author name is required",
                required=True,
            ))

        # Check content
        if not content.get("manuscript") and not content.get("chapters"):
            missing.append(Requirement(
                name="book_content",
                type=RequirementType.FILE,
                description="Book manuscript is required",
                required=True,
            ))

        # Check cover
        if "cover" not in assets:
            missing.append(Requirement(
                name="book_cover",
                type=RequirementType.IMAGE,
                description="Book cover image is required",
                required=True,
            ))
        else:
            cover = assets["cover"]
            # Validate cover dimensions
            width = cover.get("width", 0)
            height = cover.get("height", 0)
            specs = KDP_SPECS["ebook"]["cover"]

            if width < specs["min_width"] or height < specs["min_height"]:
                errors.append(
                    f"Cover too small: {width}x{height}. "
                    f"Minimum: {specs['min_width']}x{specs['min_height']}"
                )

            # Check aspect ratio (should be ~1:1.6)
            if width > 0 and height > 0:
                ratio = height / width
                if ratio < 1.4 or ratio > 1.8:
                    warnings.append(
                        f"Cover aspect ratio ({ratio:.2f}) may not display well. "
                        "Recommended: 1.6 (e.g., 1600x2560)"
                    )

        # Paperback-specific checks
        if project_type == "doc_book":
            page_count = metadata.get("page_count", 0)
            if page_count < 24:
                errors.append(f"Page count too low: {page_count}. Minimum: 24 pages")
            elif page_count > 828:
                errors.append(f"Page count too high: {page_count}. Maximum: 828 pages")

            if not metadata.get("trim_size"):
                warnings.append("Trim size not specified. Default: 6x9")

        return ValidationResult(
            valid=len(errors) == 0 and len(missing) == 0,
            missing=missing,
            warnings=warnings,
            errors=errors,
        )

    async def publish(self, product: dict, project_type: str) -> SubmissionResult:
        """Guide user through KDP publishing.

        KDP doesn't have a public API, so we provide guidance.
        """
        # Validate first
        validation = self.validate(product, project_type)

        metadata = product.get("metadata", {})
        page_count = metadata.get("page_count", 200)
        trim_size = metadata.get("trim_size", "6x9")

        # Parse trim size
        try:
            width, height = map(float, trim_size.lower().replace("x", " ").split())
        except ValueError:
            width, height = 6, 9

        # Calculate cover dimensions
        cover_dims = calculate_cover_dimensions(
            trim_width=width,
            trim_height=height,
            page_count=page_count,
        )

        return SubmissionResult(
            success=True,
            status=SubmissionStatus.PENDING,
            message="Book validated. Ready for KDP upload.",
            url="https://kdp.amazon.com/",
            metadata={
                "validation": validation.to_dict(),
                "cover_dimensions": cover_dims,
                "next_steps": [
                    "1. Go to kdp.amazon.com and sign in",
                    "2. Click 'Create New Title'",
                    "3. Choose 'Kindle eBook' or 'Paperback'",
                    "4. Enter book details (title, author, description)",
                    "5. Upload manuscript file",
                    f"6. Upload cover ({cover_dims['width_pixels']}x{cover_dims['height_pixels']}px)",
                    "7. Set pricing and territories",
                    "8. Publish!",
                ],
                "cover_specs": {
                    "ebook": f"{KDP_SPECS['ebook']['cover']['width']}x{KDP_SPECS['ebook']['cover']['height']}px",
                    "paperback": f"{cover_dims['width_pixels']}x{cover_dims['height_pixels']}px",
                    "spine_width": f"{cover_dims['spine_width_inches']}in ({cover_dims['spine_width_pixels']}px)",
                },
                "tips": [
                    "Use KDP's Cover Creator for simple covers",
                    "Request a proof copy before publishing",
                    "Enable KDP Select for Kindle Unlimited (90-day exclusive)",
                    "Set up Author Central for better book pages",
                ],
            },
        )

    async def check_status(self, submission_id: str) -> SubmissionResult:
        """Check book status.

        Since there's no API, just return guidance.
        """
        return SubmissionResult(
            success=True,
            submission_id=submission_id,
            status=SubmissionStatus.PENDING,
            message="Check status at kdp.amazon.com",
            url="https://kdp.amazon.com/bookshelf",
        )

    def get_cover_dimensions(
        self,
        trim_size: str = "6x9",
        page_count: int = 200,
        paper_type: str = "white",
    ) -> dict:
        """Helper to get cover dimensions for a book.

        Args:
            trim_size: Book size (e.g., "6x9")
            page_count: Number of pages
            paper_type: "white" or "cream"

        Returns:
            Cover dimension specifications
        """
        try:
            width, height = map(float, trim_size.lower().replace("x", " ").split())
        except ValueError:
            width, height = 6, 9

        return calculate_cover_dimensions(
            trim_width=width,
            trim_height=height,
            page_count=page_count,
            paper_type=paper_type,
        )
