"""Canva integration for creating designs, covers, and icons.

Canva Connect API allows:
- Creating designs from templates
- Uploading assets
- Exporting designs as images
- Brand kit management

Use cases in ATLAS:
- App icons (1024x1024 for App Store, 512x512 for Play Store)
- Book covers (various dimensions for KDP, etc.)
- Social media graphics
- Marketing materials
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


# Asset type specifications
ASSET_SPECS = {
    "app_icon_ios": {
        "name": "iOS App Icon",
        "width": 1024,
        "height": 1024,
        "format": "png",
        "template_search": "app icon",
    },
    "app_icon_android": {
        "name": "Android App Icon",
        "width": 512,
        "height": 512,
        "format": "png",
        "template_search": "app icon",
    },
    "book_cover_kindle": {
        "name": "Kindle Book Cover",
        "width": 1600,
        "height": 2560,
        "format": "jpg",
        "template_search": "book cover",
    },
    "book_cover_paperback_6x9": {
        "name": "Paperback Cover (6x9)",
        "width": 1800,  # 6" at 300dpi
        "height": 2700,  # 9" at 300dpi
        "format": "pdf",
        "template_search": "book cover",
    },
    "social_og": {
        "name": "Social Share Image",
        "width": 1200,
        "height": 630,
        "format": "png",
        "template_search": "social media",
    },
    "favicon": {
        "name": "Favicon",
        "width": 512,
        "height": 512,
        "format": "png",
        "template_search": "icon",
    },
}


class CanvaIntegration(PlatformIntegration):
    """Canva integration for design asset creation."""

    name = "Canva"
    icon = "🎨"
    category = PlatformCategory.DESIGN
    description = "Create app icons, book covers, and graphics"
    docs_url = "https://www.canva.dev/docs/connect/"

    supported_types = ["app", "document", "web"]

    BASE_URL = "https://api.canva.com/rest/v1"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.api_key = config.get("api_key") if config else os.getenv("CANVA_API_KEY")
        self.brand_id = config.get("brand_id") if config else os.getenv("CANVA_BRAND_ID")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
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
        return ["CANVA_API_KEY", "CANVA_BRAND_ID"]

    async def authenticate(self) -> bool:
        """Verify Canva API credentials."""
        if not self.api_key:
            logger.warning("CANVA_API_KEY not set")
            return False

        try:
            response = await self.client.get("/users/me")
            if response.status_code == 200:
                self._authenticated = True
                user = response.json()
                logger.info(f"Authenticated with Canva as {user.get('display_name', 'Unknown')}")
                return True
            else:
                logger.error(f"Canva auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.exception(f"Canva auth error: {e}")
            return False

    def get_requirements(self, project_type: str) -> list[Requirement]:
        """Get Canva requirements based on project type."""
        requirements = [
            Requirement(
                name="canva_api_key",
                type=RequirementType.CREDENTIAL,
                description="Canva Connect API key",
                required=True,
            ),
        ]

        if project_type in ["mobile_ios", "mobile_cross_platform"]:
            requirements.append(Requirement(
                name="app_icon",
                type=RequirementType.IMAGE,
                description="App icon (1024x1024 PNG)",
                specs=ASSET_SPECS["app_icon_ios"],
            ))

        if project_type in ["mobile_android", "mobile_cross_platform"]:
            requirements.append(Requirement(
                name="app_icon_android",
                type=RequirementType.IMAGE,
                description="App icon (512x512 PNG)",
                specs=ASSET_SPECS["app_icon_android"],
            ))

        if project_type in ["doc_book", "doc_ebook"]:
            requirements.append(Requirement(
                name="book_cover",
                type=RequirementType.IMAGE,
                description="Book cover image",
                specs=ASSET_SPECS["book_cover_kindle"],
            ))

        if project_type in ["web_spa", "web_static", "web_landing"]:
            requirements.extend([
                Requirement(
                    name="og_image",
                    type=RequirementType.IMAGE,
                    description="Social share image (1200x630)",
                    specs=ASSET_SPECS["social_og"],
                    required=False,
                ),
                Requirement(
                    name="favicon",
                    type=RequirementType.IMAGE,
                    description="Favicon (512x512 PNG)",
                    specs=ASSET_SPECS["favicon"],
                    required=False,
                ),
            ])

        return requirements

    def validate(self, product: dict, project_type: str) -> ValidationResult:
        """Validate product has required assets for Canva."""
        requirements = self.get_requirements(project_type)
        missing = []
        warnings = []
        errors = []

        assets = product.get("assets", {})

        for req in requirements:
            if req.type == RequirementType.CREDENTIAL:
                if not self.api_key:
                    if req.required:
                        errors.append(f"Missing {req.name}: {req.description}")
                        missing.append(req)
                continue

            if req.name not in assets:
                if req.required:
                    missing.append(req)
                else:
                    warnings.append(f"Optional asset missing: {req.name}")
                continue

            # Validate image specs if present
            asset = assets[req.name]
            if req.type == RequirementType.IMAGE and req.specs:
                expected_w = req.specs.get("width")
                expected_h = req.specs.get("height")
                actual_w = asset.get("width")
                actual_h = asset.get("height")

                if actual_w and actual_h:
                    if actual_w != expected_w or actual_h != expected_h:
                        warnings.append(
                            f"{req.name}: Expected {expected_w}x{expected_h}, "
                            f"got {actual_w}x{actual_h}"
                        )

        return ValidationResult(
            valid=len(errors) == 0 and len(missing) == 0,
            missing=missing,
            warnings=warnings,
            errors=errors,
        )

    async def publish(self, product: dict, project_type: str) -> SubmissionResult:
        """Create design assets in Canva.

        Note: Canva doesn't have a traditional "publish" flow.
        This creates designs that can be edited/exported.
        """
        if not self._authenticated:
            await self.authenticate()

        if not self._authenticated:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="Not authenticated with Canva",
            )

        # Determine what assets to create
        assets_to_create = []

        if project_type in ["mobile_ios", "mobile_cross_platform"]:
            assets_to_create.append(("app_icon_ios", product))
        if project_type in ["doc_book"]:
            assets_to_create.append(("book_cover_kindle", product))

        created_assets = []

        for asset_type, data in assets_to_create:
            result = await self.create_asset(asset_type, ASSET_SPECS[asset_type], data)
            if result:
                created_assets.append(result)

        if created_assets:
            return SubmissionResult(
                success=True,
                status=SubmissionStatus.PUBLISHED,
                message=f"Created {len(created_assets)} design(s) in Canva",
                metadata={"assets": created_assets},
            )
        else:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="No assets created",
            )

    async def check_status(self, submission_id: str) -> SubmissionResult:
        """Check design status in Canva."""
        try:
            response = await self.client.get(f"/designs/{submission_id}")
            if response.status_code == 200:
                design = response.json()
                return SubmissionResult(
                    success=True,
                    submission_id=submission_id,
                    status=SubmissionStatus.PUBLISHED,
                    url=design.get("urls", {}).get("edit_url"),
                    metadata=design,
                )
            else:
                return SubmissionResult(
                    success=False,
                    submission_id=submission_id,
                    status=SubmissionStatus.FAILED,
                    message=f"Design not found: {response.status_code}",
                )
        except Exception as e:
            return SubmissionResult(
                success=False,
                submission_id=submission_id,
                status=SubmissionStatus.FAILED,
                message=str(e),
            )

    async def create_asset(
        self,
        asset_type: str,
        specs: dict,
        content: Optional[dict] = None,
    ) -> Optional[dict]:
        """Create a design asset in Canva.

        Args:
            asset_type: Type from ASSET_SPECS
            specs: Dimensions and format
            content: Content to include (title, subtitle, etc.)

        Returns:
            Design metadata including edit URL
        """
        if not self._authenticated:
            await self.authenticate()

        if not self._authenticated:
            logger.error("Cannot create asset: not authenticated")
            return None

        try:
            # Create a new design
            payload = {
                "design_type": {
                    "width": specs.get("width", 1024),
                    "height": specs.get("height", 1024),
                },
                "title": content.get("name", f"ATLAS - {specs.get('name', asset_type)}") if content else f"ATLAS - {asset_type}",
            }

            response = await self.client.post("/designs", json=payload)

            if response.status_code in [200, 201]:
                design = response.json()
                logger.info(f"Created Canva design: {design.get('id')}")
                return {
                    "id": design.get("id"),
                    "type": asset_type,
                    "edit_url": design.get("urls", {}).get("edit_url"),
                    "view_url": design.get("urls", {}).get("view_url"),
                    "specs": specs,
                }
            else:
                logger.error(f"Failed to create design: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.exception(f"Error creating Canva asset: {e}")
            return None

    async def get_templates(self, asset_type: str) -> list[dict]:
        """Search for templates matching asset type."""
        if asset_type not in ASSET_SPECS:
            return []

        specs = ASSET_SPECS[asset_type]
        search_term = specs.get("template_search", asset_type)

        try:
            response = await self.client.get(
                "/templates",
                params={
                    "query": search_term,
                    "width": specs.get("width"),
                    "height": specs.get("height"),
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            return []

        except Exception as e:
            logger.exception(f"Error fetching templates: {e}")
            return []

    async def export_design(
        self,
        design_id: str,
        format: str = "png",
    ) -> Optional[str]:
        """Export a design to an image file.

        Args:
            design_id: Canva design ID
            format: Export format (png, jpg, pdf)

        Returns:
            URL to download the exported file
        """
        try:
            # Start export job
            response = await self.client.post(
                f"/designs/{design_id}/exports",
                json={"format": format}
            )

            if response.status_code in [200, 201, 202]:
                export = response.json()
                export_id = export.get("id")

                # Poll for completion (simplified - real impl would use webhooks)
                import asyncio
                for _ in range(30):  # Max 30 seconds
                    status_response = await self.client.get(
                        f"/designs/{design_id}/exports/{export_id}"
                    )
                    if status_response.status_code == 200:
                        status = status_response.json()
                        if status.get("status") == "completed":
                            return status.get("urls", {}).get("download")
                        elif status.get("status") == "failed":
                            logger.error(f"Export failed: {status}")
                            return None
                    await asyncio.sleep(1)

                logger.error("Export timed out")
                return None
            else:
                logger.error(f"Export request failed: {response.status_code}")
                return None

        except Exception as e:
            logger.exception(f"Error exporting design: {e}")
            return None
