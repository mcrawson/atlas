"""Figma integration for UI/UX design management.

Figma API allows:
- Reading design files and components
- Exporting images from designs
- Creating design tokens
- Managing comments and feedback

Use cases in ATLAS:
- UI component inspection
- Design system integration
- Exporting assets from designs
- Design-to-code workflows
"""

import os
import logging
from typing import Optional

import httpx

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


class FigmaIntegration(PlatformIntegration):
    """Figma integration for UI design management."""

    name = "Figma"
    icon = "🖼️"
    category = PlatformCategory.DESIGN
    description = "Export UI designs and components"
    docs_url = "https://www.figma.com/developers/api"

    supported_types = ["app", "web"]

    BASE_URL = "https://api.figma.com/v1"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.api_token = config.get("api_token") if config else os.getenv("FIGMA_API_TOKEN")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "X-Figma-Token": self.api_token,
            }
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def get_env_vars(self) -> list[str]:
        return ["FIGMA_API_TOKEN"]

    async def authenticate(self) -> bool:
        """Verify Figma API credentials."""
        if not self.api_token:
            logger.warning("FIGMA_API_TOKEN not set")
            return False

        try:
            response = await self.client.get("/me")
            if response.status_code == 200:
                self._authenticated = True
                user = response.json()
                logger.info(f"Authenticated with Figma as {user.get('handle', 'Unknown')}")
                return True
            else:
                logger.error(f"Figma auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.exception(f"Figma auth error: {e}")
            return False

    def get_requirements(self, project_type: str) -> list[Requirement]:
        """Get Figma requirements based on project type."""
        requirements = [
            Requirement(
                name="figma_api_token",
                type=RequirementType.CREDENTIAL,
                description="Figma API token",
                required=True,
            ),
        ]

        if project_type in ["app", "web", "mobile_ios", "mobile_android", "web_spa"]:
            requirements.append(Requirement(
                name="figma_file_url",
                type=RequirementType.CONFIG,
                description="Figma file URL with designs",
                required=False,  # Can work without existing designs
            ))

        return requirements

    def validate(self, product: dict, project_type: str) -> ValidationResult:
        """Validate Figma requirements."""
        requirements = self.get_requirements(project_type)
        missing = []
        warnings = []
        errors = []

        for req in requirements:
            if req.type == RequirementType.CREDENTIAL:
                if not self.api_token:
                    if req.required:
                        errors.append(f"Missing {req.name}")
                        missing.append(req)

        return ValidationResult(
            valid=len(errors) == 0 and len(missing) == 0,
            missing=missing,
            warnings=warnings,
            errors=errors,
        )

    async def publish(self, product: dict, project_type: str) -> SubmissionResult:
        """Figma doesn't support direct publishing.

        This exports assets from a Figma file instead.
        """
        figma_url = product.get("figma_file_url")
        if not figma_url:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="No Figma file URL provided",
            )

        # Extract file key from URL
        file_key = self._extract_file_key(figma_url)
        if not file_key:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="Invalid Figma URL",
            )

        # Get file info and export components
        try:
            file_info = await self.get_file(file_key)
            if file_info:
                return SubmissionResult(
                    success=True,
                    submission_id=file_key,
                    status=SubmissionStatus.PUBLISHED,
                    url=figma_url,
                    message="Figma file accessed successfully",
                    metadata={"file_name": file_info.get("name")},
                )
        except Exception as e:
            logger.exception(f"Error accessing Figma file: {e}")

        return SubmissionResult(
            success=False,
            status=SubmissionStatus.FAILED,
            message="Failed to access Figma file",
        )

    async def check_status(self, submission_id: str) -> SubmissionResult:
        """Check if Figma file is accessible."""
        file_info = await self.get_file(submission_id)
        if file_info:
            return SubmissionResult(
                success=True,
                submission_id=submission_id,
                status=SubmissionStatus.PUBLISHED,
                metadata=file_info,
            )
        return SubmissionResult(
            success=False,
            submission_id=submission_id,
            status=SubmissionStatus.FAILED,
        )

    def _extract_file_key(self, url: str) -> Optional[str]:
        """Extract file key from Figma URL."""
        # URLs look like: https://www.figma.com/file/ABC123/FileName
        import re
        match = re.search(r'figma\.com/(?:file|design)/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        return None

    async def get_file(self, file_key: str) -> Optional[dict]:
        """Get Figma file information."""
        try:
            response = await self.client.get(f"/files/{file_key}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.exception(f"Error getting Figma file: {e}")
            return None

    async def get_components(self, file_key: str) -> list[dict]:
        """Get all components from a Figma file."""
        try:
            response = await self.client.get(f"/files/{file_key}/components")
            if response.status_code == 200:
                data = response.json()
                return data.get("meta", {}).get("components", [])
            return []
        except Exception as e:
            logger.exception(f"Error getting components: {e}")
            return []

    async def export_images(
        self,
        file_key: str,
        node_ids: list[str],
        format: str = "png",
        scale: float = 2.0,
    ) -> dict[str, str]:
        """Export nodes as images.

        Args:
            file_key: Figma file key
            node_ids: List of node IDs to export
            format: Image format (png, jpg, svg, pdf)
            scale: Export scale

        Returns:
            Dict of node_id -> image URL
        """
        try:
            response = await self.client.get(
                f"/images/{file_key}",
                params={
                    "ids": ",".join(node_ids),
                    "format": format,
                    "scale": scale,
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("images", {})
            return {}

        except Exception as e:
            logger.exception(f"Error exporting images: {e}")
            return {}

    async def create_asset(
        self,
        asset_type: str,
        specs: dict,
        content: Optional[dict] = None,
    ) -> Optional[dict]:
        """Export asset from Figma.

        Requires a Figma file URL and node ID in content.
        """
        if not content:
            return None

        file_url = content.get("figma_file_url")
        node_id = content.get("node_id")

        if not file_url or not node_id:
            logger.warning("Figma export requires figma_file_url and node_id")
            return None

        file_key = self._extract_file_key(file_url)
        if not file_key:
            return None

        images = await self.export_images(
            file_key,
            [node_id],
            format=specs.get("format", "png"),
            scale=specs.get("scale", 2.0),
        )

        if node_id in images:
            return {
                "type": asset_type,
                "url": images[node_id],
                "file_key": file_key,
                "node_id": node_id,
            }

        return None
