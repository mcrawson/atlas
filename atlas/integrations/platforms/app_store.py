"""Apple App Store Connect integration.

App Store Connect API allows:
- Managing app metadata
- Uploading builds (via Transporter)
- Managing TestFlight
- Viewing analytics

Use cases in ATLAS:
- Preparing app submissions
- Validating App Store requirements
- Managing app metadata
- Tracking review status

Note: Actual binary upload requires Apple's Transporter tool.
This integration handles metadata and validation.
"""

import os
import logging
from typing import Optional
import jwt
import time

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


# App Store requirements
APP_STORE_REQUIREMENTS = {
    "icon": {
        "size": 1024,
        "format": "png",
        "no_alpha": True,
        "no_rounded_corners": True,  # iOS rounds them
    },
    "screenshots": {
        "iphone_6_5": {"width": 1284, "height": 2778, "required": True},
        "iphone_5_5": {"width": 1242, "height": 2208, "required": True},
        "ipad_12_9": {"width": 2048, "height": 2732, "required": False},
    },
    "metadata": {
        "name": {"max_length": 30},
        "subtitle": {"max_length": 30},
        "description": {"max_length": 4000},
        "keywords": {"max_length": 100},
        "support_url": {"required": True},
        "privacy_policy_url": {"required": True},
    },
}


class AppStoreIntegration(PlatformIntegration):
    """Apple App Store Connect integration."""

    name = "App Store"
    icon = "🍎"
    category = PlatformCategory.APP_STORES
    description = "Publish iOS and macOS apps to the App Store"
    docs_url = "https://developer.apple.com/documentation/appstoreconnectapi"

    supported_types = ["app", "mobile_ios", "mobile_cross_platform", "desktop_macos"]

    BASE_URL = "https://api.appstoreconnect.apple.com/v1"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.issuer_id = config.get("issuer_id") if config else os.getenv("APP_STORE_ISSUER_ID")
        self.key_id = config.get("key_id") if config else os.getenv("APP_STORE_KEY_ID")
        self.private_key_path = config.get("private_key_path") if config else os.getenv("APP_STORE_PRIVATE_KEY_PATH")
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None
        self._token_expiry: float = 0

    def _generate_token(self) -> Optional[str]:
        """Generate JWT for App Store Connect API."""
        if not all([self.issuer_id, self.key_id, self.private_key_path]):
            return None

        try:
            with open(self.private_key_path, 'r') as f:
                private_key = f.read()

            now = time.time()
            expiry = now + 1200  # 20 minutes

            payload = {
                "iss": self.issuer_id,
                "iat": int(now),
                "exp": int(expiry),
                "aud": "appstoreconnect-v1",
            }

            token = jwt.encode(
                payload,
                private_key,
                algorithm="ES256",
                headers={"kid": self.key_id}
            )

            self._token = token
            self._token_expiry = expiry
            return token

        except Exception as e:
            logger.exception(f"Error generating App Store token: {e}")
            return None

    @property
    def token(self) -> Optional[str]:
        """Get valid JWT token."""
        if not self._token or time.time() >= self._token_expiry - 60:
            self._generate_token()
        return self._token

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.token}",
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
        return [
            "APP_STORE_ISSUER_ID",
            "APP_STORE_KEY_ID",
            "APP_STORE_PRIVATE_KEY_PATH",
        ]

    async def authenticate(self) -> bool:
        """Verify App Store Connect credentials."""
        if not self.token:
            logger.warning("Cannot generate App Store Connect token")
            return False

        try:
            response = await self.client.get("/apps", params={"limit": 1})
            if response.status_code == 200:
                self._authenticated = True
                logger.info("Authenticated with App Store Connect")
                return True
            else:
                logger.error(f"App Store auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.exception(f"App Store auth error: {e}")
            return False

    def get_requirements(self, project_type: str) -> list[Requirement]:
        """Get App Store requirements."""
        requirements = [
            Requirement(
                name="app_store_credentials",
                type=RequirementType.CREDENTIAL,
                description="App Store Connect API credentials",
                required=True,
            ),
            Requirement(
                name="apple_developer_account",
                type=RequirementType.CREDENTIAL,
                description="Apple Developer Program membership ($99/year)",
                required=True,
            ),
            Requirement(
                name="app_icon",
                type=RequirementType.IMAGE,
                description="App icon (1024x1024 PNG, no alpha)",
                required=True,
                specs=APP_STORE_REQUIREMENTS["icon"],
            ),
            Requirement(
                name="app_name",
                type=RequirementType.TEXT,
                description="App name (max 30 characters)",
                required=True,
                specs={"max_length": 30},
            ),
            Requirement(
                name="app_description",
                type=RequirementType.TEXT,
                description="App description (max 4000 characters)",
                required=True,
                specs={"max_length": 4000},
            ),
            Requirement(
                name="privacy_policy_url",
                type=RequirementType.TEXT,
                description="Privacy policy URL",
                required=True,
            ),
            Requirement(
                name="support_url",
                type=RequirementType.TEXT,
                description="Support URL",
                required=True,
            ),
            Requirement(
                name="screenshots_iphone",
                type=RequirementType.IMAGE,
                description="iPhone screenshots (6.5\" and 5.5\" displays)",
                required=True,
                specs=APP_STORE_REQUIREMENTS["screenshots"],
            ),
            Requirement(
                name="app_binary",
                type=RequirementType.FILE,
                description="Signed .ipa file",
                required=True,
            ),
        ]

        return requirements

    def validate(self, product: dict, project_type: str) -> ValidationResult:
        """Validate product against App Store requirements."""
        missing = []
        warnings = []
        errors = []

        metadata = product.get("metadata", {})
        assets = product.get("assets", {})

        # Check credentials
        if not self.token:
            errors.append("App Store Connect credentials not configured")

        # Check app name
        app_name = metadata.get("name", "")
        if not app_name:
            missing.append(Requirement(
                name="app_name",
                type=RequirementType.TEXT,
                description="App name is required",
                required=True,
            ))
        elif len(app_name) > 30:
            errors.append(f"App name too long: {len(app_name)}/30 characters")

        # Check description
        description = metadata.get("description", "")
        if not description:
            missing.append(Requirement(
                name="app_description",
                type=RequirementType.TEXT,
                description="App description is required",
                required=True,
            ))
        elif len(description) > 4000:
            errors.append(f"Description too long: {len(description)}/4000 characters")

        # Check privacy policy
        if not metadata.get("privacy_policy_url"):
            missing.append(Requirement(
                name="privacy_policy_url",
                type=RequirementType.TEXT,
                description="Privacy policy URL is required",
                required=True,
            ))

        # Check icon
        if "app_icon" not in assets:
            missing.append(Requirement(
                name="app_icon",
                type=RequirementType.IMAGE,
                description="App icon (1024x1024) is required",
                required=True,
            ))

        # Check screenshots
        if "screenshots" not in assets or not assets["screenshots"]:
            warnings.append("Screenshots recommended for App Store listing")

        # Check binary
        if "app_binary" not in product:
            missing.append(Requirement(
                name="app_binary",
                type=RequirementType.FILE,
                description="Signed .ipa file is required for submission",
                required=True,
            ))

        return ValidationResult(
            valid=len(errors) == 0 and len(missing) == 0,
            missing=missing,
            warnings=warnings,
            errors=errors,
        )

    async def publish(self, product: dict, project_type: str) -> SubmissionResult:
        """Submit app to App Store.

        Note: This creates/updates app metadata. Actual binary upload
        requires Apple's Transporter tool.
        """
        if not self._authenticated:
            await self.authenticate()

        if not self._authenticated:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="Not authenticated with App Store Connect",
            )

        # Validate first
        validation = self.validate(product, project_type)
        if not validation.valid:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="Validation failed",
                metadata={"validation": validation.to_dict()},
            )

        # For now, return guidance on completing submission
        return SubmissionResult(
            success=True,
            status=SubmissionStatus.PENDING,
            message="App metadata validated. Use Xcode or Transporter to upload the binary.",
            metadata={
                "next_steps": [
                    "1. Build and archive your app in Xcode",
                    "2. Upload using Xcode Organizer or Transporter",
                    "3. Complete App Store listing in App Store Connect",
                    "4. Submit for review",
                ],
                "review_guidelines": "https://developer.apple.com/app-store/review/guidelines/",
            },
        )

    async def check_status(self, submission_id: str) -> SubmissionResult:
        """Check app review status."""
        try:
            response = await self.client.get(f"/apps/{submission_id}")
            if response.status_code == 200:
                app = response.json().get("data", {})
                attributes = app.get("attributes", {})

                return SubmissionResult(
                    success=True,
                    submission_id=submission_id,
                    status=SubmissionStatus.PUBLISHED if attributes.get("isAvailableInNewTerritories") else SubmissionStatus.REVIEW,
                    url=f"https://appstoreconnect.apple.com/apps/{submission_id}",
                    metadata=attributes,
                )
            else:
                return SubmissionResult(
                    success=False,
                    submission_id=submission_id,
                    status=SubmissionStatus.FAILED,
                    message=f"App not found: {response.status_code}",
                )
        except Exception as e:
            return SubmissionResult(
                success=False,
                submission_id=submission_id,
                status=SubmissionStatus.FAILED,
                message=str(e),
            )

    async def get_apps(self) -> list[dict]:
        """Get all apps in the account."""
        try:
            response = await self.client.get("/apps")
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []
        except Exception as e:
            logger.exception(f"Error fetching apps: {e}")
            return []
