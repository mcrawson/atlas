"""Base class for all platform integrations.

Every external platform (Canva, Google Docs, App Store, etc.) implements
this interface to provide a consistent way to:
1. Check what's needed to publish
2. Validate if a product meets requirements
3. Publish to the platform
4. Check submission status
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class PlatformCategory(Enum):
    """Categories of platforms."""
    DESIGN = "design"           # Canva, Figma
    DOCUMENTS = "documents"     # Google Docs, Notion
    APP_STORES = "app_stores"   # App Store, Play Store
    PUBLISHING = "publishing"   # Amazon KDP, Gumroad
    HOSTING = "hosting"         # Vercel, Netlify, Railway
    PACKAGES = "packages"       # npm, PyPI, crates.io
    CODE = "code"               # GitHub, GitLab


class RequirementType(Enum):
    """Types of requirements."""
    FILE = "file"               # A file that must exist
    IMAGE = "image"             # An image with specific dimensions
    TEXT = "text"               # Text content (description, etc.)
    CREDENTIAL = "credential"   # API key, token, etc.
    CONFIG = "config"           # Configuration value
    APPROVAL = "approval"       # Human approval needed


@dataclass
class Requirement:
    """A single requirement for publishing."""
    name: str
    type: RequirementType
    description: str
    required: bool = True
    specs: dict = field(default_factory=dict)  # e.g., {"width": 1024, "height": 1024}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "required": self.required,
            "specs": self.specs,
        }


@dataclass
class ValidationResult:
    """Result of validating a product against platform requirements."""
    valid: bool
    missing: list[Requirement] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "missing": [r.to_dict() for r in self.missing],
            "warnings": self.warnings,
            "errors": self.errors,
        }


class SubmissionStatus(Enum):
    """Status of a submission to a platform."""
    PENDING = "pending"
    PROCESSING = "processing"
    REVIEW = "review"           # Under human review
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass
class SubmissionResult:
    """Result of submitting to a platform."""
    success: bool
    submission_id: Optional[str] = None
    status: SubmissionStatus = SubmissionStatus.PENDING
    url: Optional[str] = None
    message: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "submission_id": self.submission_id,
            "status": self.status.value,
            "url": self.url,
            "message": self.message,
            "metadata": self.metadata,
        }


class PlatformIntegration(ABC):
    """Abstract base class for platform integrations.

    Each platform (Canva, App Store, npm, etc.) implements this interface
    to provide a consistent way to publish products.
    """

    # Platform metadata - override in subclasses
    name: str = "Unknown Platform"
    icon: str = "🔌"
    category: PlatformCategory = PlatformCategory.HOSTING
    description: str = "A platform integration"
    docs_url: str = ""

    # What project types this platform supports
    supported_types: list[str] = []  # e.g., ["app", "web", "document"]

    def __init__(self, config: Optional[dict] = None):
        """Initialize the integration.

        Args:
            config: Platform-specific configuration (API keys, etc.)
        """
        self.config = config or {}
        self._authenticated = False

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid credentials."""
        return self._authenticated

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the platform.

        Returns:
            True if authentication successful
        """
        pass

    @abstractmethod
    def get_requirements(self, project_type: str) -> list[Requirement]:
        """Get requirements for publishing to this platform.

        Args:
            project_type: Type of project (e.g., "mobile_ios", "doc_book")

        Returns:
            List of requirements
        """
        pass

    @abstractmethod
    def validate(self, product: dict, project_type: str) -> ValidationResult:
        """Validate if a product meets platform requirements.

        Args:
            product: Product data (files, metadata, etc.)
            project_type: Type of project

        Returns:
            ValidationResult with any missing requirements
        """
        pass

    @abstractmethod
    async def publish(self, product: dict, project_type: str) -> SubmissionResult:
        """Publish a product to the platform.

        Args:
            product: Product data
            project_type: Type of project

        Returns:
            SubmissionResult with status and any URLs
        """
        pass

    @abstractmethod
    async def check_status(self, submission_id: str) -> SubmissionResult:
        """Check the status of a submission.

        Args:
            submission_id: ID from previous publish() call

        Returns:
            Updated SubmissionResult
        """
        pass

    async def create_asset(
        self,
        asset_type: str,
        specs: dict,
        content: Optional[dict] = None,
    ) -> Optional[dict]:
        """Create an asset (image, document, etc.) on the platform.

        Not all platforms support this. Override if supported.

        Args:
            asset_type: Type of asset (e.g., "app_icon", "book_cover")
            specs: Specifications (dimensions, format, etc.)
            content: Content to include (text, images, etc.)

        Returns:
            Asset data including URL/path, or None if not supported
        """
        logger.warning(f"{self.name} does not support create_asset")
        return None

    async def get_templates(self, asset_type: str) -> list[dict]:
        """Get available templates for an asset type.

        Not all platforms support this. Override if supported.

        Args:
            asset_type: Type of asset

        Returns:
            List of template metadata
        """
        return []

    def get_env_vars(self) -> list[str]:
        """Get required environment variable names.

        Returns:
            List of env var names needed for this integration
        """
        return []

    def to_dict(self) -> dict:
        """Serialize platform info."""
        return {
            "name": self.name,
            "icon": self.icon,
            "category": self.category.value,
            "description": self.description,
            "docs_url": self.docs_url,
            "supported_types": self.supported_types,
            "authenticated": self.is_authenticated,
            "env_vars": self.get_env_vars(),
        }
