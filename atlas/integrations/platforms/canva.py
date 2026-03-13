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
from pathlib import Path
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

    TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        # Support both direct API key and OAuth client credentials
        self.api_key = config.get("api_key") if config else os.getenv("CANVA_API_KEY")
        self.client_id = config.get("client_id") if config else os.getenv("CANVA_CLIENT_ID")
        self.client_secret = config.get("client_secret") if config else os.getenv("CANVA_CLIENT_SECRET")
        self.brand_id = config.get("brand_id") if config else os.getenv("CANVA_BRAND_ID")
        self._access_token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        token = self._access_token or self.api_key
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    def _reset_client(self):
        """Reset client to pick up new token."""
        if self._client and not self._client.is_closed:
            # Don't await here, just mark for recreation
            self._client = None

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def get_env_vars(self) -> list[str]:
        return ["CANVA_CLIENT_ID", "CANVA_CLIENT_SECRET", "CANVA_API_KEY", "CANVA_BRAND_ID"]

    async def _get_oauth_token(self) -> Optional[str]:
        """Exchange client credentials for access token."""
        if not self.client_id or not self.client_secret:
            return None

        try:
            import base64
            # Create Basic auth header
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded = base64.b64encode(credentials.encode()).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {encoded}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "client_credentials",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data.get("access_token")
                    logger.info("[Canva] OAuth token obtained successfully")
                    return self._access_token
                else:
                    logger.error(f"[Canva] OAuth token request failed: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.exception(f"[Canva] OAuth token error: {e}")
            return None

    async def authenticate(self) -> bool:
        """Verify Canva API credentials using OAuth or direct API key."""
        # Try OAuth first if client credentials are available
        if self.client_id and self.client_secret:
            token = await self._get_oauth_token()
            if token:
                self._reset_client()  # Reset to use new token
                try:
                    response = await self.client.get("/users/me")
                    if response.status_code == 200:
                        self._authenticated = True
                        user = response.json()
                        logger.info(f"Authenticated with Canva as {user.get('display_name', 'Unknown')}")
                        return True
                except Exception as e:
                    logger.error(f"Canva auth verification failed: {e}")

        # Fall back to direct API key
        if not self.api_key and not self._access_token:
            logger.warning("CANVA_CLIENT_ID/SECRET or CANVA_API_KEY not set")
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

    async def upload_asset(
        self,
        image_path: Path,
        name: Optional[str] = None,
    ) -> Optional[dict]:
        """Upload an image asset to Canva.

        Uses the Canva Asset Upload API to upload an image that can be
        used in designs.

        Args:
            image_path: Path to the image file
            name: Optional name for the asset (defaults to filename)

        Returns:
            Asset metadata including ID, or None if failed
        """
        if not self._authenticated:
            await self.authenticate()

        if not self._authenticated:
            logger.error("Cannot upload asset: not authenticated")
            return None

        image_path = Path(image_path)
        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return None

        if name is None:
            name = image_path.stem

        try:
            # Step 1: Create upload job
            create_response = await self.client.post(
                "/asset-uploads",
                json={
                    "name": name,
                }
            )

            if create_response.status_code not in [200, 201]:
                logger.error(f"Failed to create upload job: {create_response.status_code} - {create_response.text}")
                return None

            upload_job = create_response.json()
            upload_url = upload_job.get("upload_url")
            job_id = upload_job.get("id")

            if not upload_url:
                logger.error("No upload URL in response")
                return None

            # Step 2: Upload the actual file
            with open(image_path, "rb") as f:
                file_content = f.read()

            # Determine content type
            suffix = image_path.suffix.lower()
            content_type = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }.get(suffix, "image/png")

            async with httpx.AsyncClient() as upload_client:
                upload_response = await upload_client.put(
                    upload_url,
                    content=file_content,
                    headers={"Content-Type": content_type},
                )

            if upload_response.status_code not in [200, 201, 204]:
                logger.error(f"Failed to upload file: {upload_response.status_code}")
                return None

            # Step 3: Poll for completion
            import asyncio
            for _ in range(30):  # Max 30 seconds
                status_response = await self.client.get(f"/asset-uploads/{job_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    if status.get("status") == "completed":
                        asset = status.get("asset", {})
                        logger.info(f"Uploaded asset: {asset.get('id')}")
                        return {
                            "id": asset.get("id"),
                            "name": name,
                            "thumbnail_url": asset.get("thumbnail", {}).get("url"),
                        }
                    elif status.get("status") == "failed":
                        logger.error(f"Upload failed: {status}")
                        return None
                await asyncio.sleep(1)

            logger.error("Upload timed out")
            return None

        except Exception as e:
            logger.exception(f"Error uploading asset: {e}")
            return None

    async def create_multi_page_design(
        self,
        asset_ids: list[str],
        title: str = "ATLAS Planner",
        width: int = 816,
        height: int = 1056,
    ) -> Optional[dict]:
        """Create a multi-page design from uploaded assets.

        Each asset becomes a page in the design, with the image as a
        full-page background.

        Args:
            asset_ids: List of asset IDs from upload_asset()
            title: Title for the design
            width: Design width in pixels
            height: Design height in pixels

        Returns:
            Design metadata including edit URL, or None if failed
        """
        if not self._authenticated:
            await self.authenticate()

        if not self._authenticated:
            logger.error("Cannot create design: not authenticated")
            return None

        if not asset_ids:
            logger.error("No asset IDs provided")
            return None

        try:
            # Build pages array - each page has the asset as background
            pages = []
            for i, asset_id in enumerate(asset_ids):
                pages.append({
                    "elements": [
                        {
                            "type": "image",
                            "asset_id": asset_id,
                            "position": {
                                "x": 0,
                                "y": 0,
                            },
                            "size": {
                                "width": width,
                                "height": height,
                            },
                        }
                    ]
                })

            # Create the design
            payload = {
                "design_type": {
                    "width": width,
                    "height": height,
                },
                "title": title,
                "pages": pages,
            }

            response = await self.client.post("/designs", json=payload)

            if response.status_code in [200, 201]:
                design = response.json()
                design_data = design.get("design", design)
                logger.info(f"Created multi-page design: {design_data.get('id')}")
                return {
                    "id": design_data.get("id"),
                    "title": title,
                    "page_count": len(asset_ids),
                    "edit_url": design_data.get("urls", {}).get("edit_url"),
                    "view_url": design_data.get("urls", {}).get("view_url"),
                }
            else:
                logger.error(f"Failed to create design: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.exception(f"Error creating multi-page design: {e}")
            return None

    async def create_planner_from_html(
        self,
        html_files: list[dict],
        title: str = "ATLAS Planner",
    ) -> Optional[dict]:
        """Create a Canva design from HTML planner pages.

        This is a high-level method that:
        1. Renders HTML to images using Playwright
        2. Uploads images as assets to Canva
        3. Creates a multi-page design

        Args:
            html_files: List of dicts with 'filename' and 'content' keys
            title: Title for the Canva design

        Returns:
            Design metadata including edit URL, or None if failed
        """
        from atlas.utils.image_renderer import get_image_renderer

        if not html_files:
            logger.error("No HTML files provided")
            return None

        # Step 1: Render HTML to images
        logger.info(f"Rendering {len(html_files)} HTML pages to images...")
        renderer = get_image_renderer()
        image_paths = await renderer.render_html_to_images(html_files)

        if not image_paths:
            logger.error("Failed to render any images")
            return None

        # Step 2: Upload images as assets
        logger.info(f"Uploading {len(image_paths)} images to Canva...")
        asset_ids = []
        for i, image_path in enumerate(image_paths):
            asset = await self.upload_asset(
                image_path,
                name=f"{title} - Page {i + 1}",
            )
            if asset:
                asset_ids.append(asset["id"])
            else:
                logger.warning(f"Failed to upload {image_path}")

        if not asset_ids:
            logger.error("Failed to upload any assets")
            return None

        # Step 3: Create multi-page design
        logger.info(f"Creating design with {len(asset_ids)} pages...")
        design = await self.create_multi_page_design(
            asset_ids,
            title=title,
        )

        if design:
            logger.info(f"Created Canva design: {design.get('edit_url')}")

        return design
