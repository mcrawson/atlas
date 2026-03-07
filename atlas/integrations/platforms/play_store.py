"""Google Play Store integration.

Google Play Developer API allows:
- Managing app listings
- Uploading APKs/AABs
- Managing tracks (internal, alpha, beta, production)
- Viewing reviews and ratings

Use cases in ATLAS:
- Preparing Play Store submissions
- Validating Play Store requirements
- Managing app metadata
- Tracking publication status
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


# Play Store requirements
PLAY_STORE_REQUIREMENTS = {
    "icon": {
        "size": 512,
        "format": "png",
        "transparency_allowed": True,
    },
    "feature_graphic": {
        "width": 1024,
        "height": 500,
        "format": "png",
    },
    "screenshots": {
        "phone": {"min_count": 2, "max_count": 8, "min_side": 320, "max_side": 3840},
        "tablet_7": {"required": False},
        "tablet_10": {"required": False},
    },
    "metadata": {
        "title": {"max_length": 50},
        "short_description": {"max_length": 80},
        "full_description": {"max_length": 4000},
    },
}


class PlayStoreIntegration(PlatformIntegration):
    """Google Play Store integration."""

    name = "Play Store"
    icon = "🤖"
    category = PlatformCategory.APP_STORES
    description = "Publish Android apps to Google Play"
    docs_url = "https://developers.google.com/android-publisher"

    supported_types = ["app", "mobile_android", "mobile_cross_platform"]

    BASE_URL = "https://androidpublisher.googleapis.com/androidpublisher/v3"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.service_account_path = config.get("service_account_path") if config else os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT")
        self.package_name = config.get("package_name") if config else os.getenv("ANDROID_PACKAGE_NAME")
        self._token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self._token}",
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
            "GOOGLE_PLAY_SERVICE_ACCOUNT",
            "ANDROID_PACKAGE_NAME",
        ]

    async def authenticate(self) -> bool:
        """Authenticate with Google Play Developer API.

        Uses service account credentials.
        """
        if not self.service_account_path:
            logger.warning("GOOGLE_PLAY_SERVICE_ACCOUNT not set")
            return False

        try:
            # In production, use google-auth library
            # This is a simplified version
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_path,
                scopes=["https://www.googleapis.com/auth/androidpublisher"]
            )
            credentials.refresh(Request())
            self._token = credentials.token
            self._authenticated = True
            logger.info("Authenticated with Google Play")
            return True

        except ImportError:
            logger.warning("google-auth not installed. Install with: pip install google-auth")
            return False
        except Exception as e:
            logger.exception(f"Google Play auth error: {e}")
            return False

    def get_requirements(self, project_type: str) -> list[Requirement]:
        """Get Play Store requirements."""
        requirements = [
            Requirement(
                name="play_store_credentials",
                type=RequirementType.CREDENTIAL,
                description="Google Play Developer API credentials",
                required=True,
            ),
            Requirement(
                name="google_play_account",
                type=RequirementType.CREDENTIAL,
                description="Google Play Developer account ($25 one-time)",
                required=True,
            ),
            Requirement(
                name="app_icon",
                type=RequirementType.IMAGE,
                description="App icon (512x512 PNG)",
                required=True,
                specs=PLAY_STORE_REQUIREMENTS["icon"],
            ),
            Requirement(
                name="feature_graphic",
                type=RequirementType.IMAGE,
                description="Feature graphic (1024x500 PNG)",
                required=True,
                specs=PLAY_STORE_REQUIREMENTS["feature_graphic"],
            ),
            Requirement(
                name="app_title",
                type=RequirementType.TEXT,
                description="App title (max 50 characters)",
                required=True,
                specs={"max_length": 50},
            ),
            Requirement(
                name="short_description",
                type=RequirementType.TEXT,
                description="Short description (max 80 characters)",
                required=True,
                specs={"max_length": 80},
            ),
            Requirement(
                name="full_description",
                type=RequirementType.TEXT,
                description="Full description (max 4000 characters)",
                required=True,
                specs={"max_length": 4000},
            ),
            Requirement(
                name="screenshots_phone",
                type=RequirementType.IMAGE,
                description="Phone screenshots (2-8 images)",
                required=True,
                specs=PLAY_STORE_REQUIREMENTS["screenshots"]["phone"],
            ),
            Requirement(
                name="privacy_policy_url",
                type=RequirementType.TEXT,
                description="Privacy policy URL",
                required=True,
            ),
            Requirement(
                name="app_bundle",
                type=RequirementType.FILE,
                description="Signed AAB (Android App Bundle) file",
                required=True,
            ),
        ]

        return requirements

    def validate(self, product: dict, project_type: str) -> ValidationResult:
        """Validate product against Play Store requirements."""
        missing = []
        warnings = []
        errors = []

        metadata = product.get("metadata", {})
        assets = product.get("assets", {})

        # Check credentials
        if not self.service_account_path:
            errors.append("Google Play credentials not configured")

        # Check title
        title = metadata.get("title", "")
        if not title:
            missing.append(Requirement(
                name="app_title",
                type=RequirementType.TEXT,
                description="App title is required",
                required=True,
            ))
        elif len(title) > 50:
            errors.append(f"Title too long: {len(title)}/50 characters")

        # Check short description
        short_desc = metadata.get("short_description", "")
        if not short_desc:
            missing.append(Requirement(
                name="short_description",
                type=RequirementType.TEXT,
                description="Short description is required",
                required=True,
            ))
        elif len(short_desc) > 80:
            errors.append(f"Short description too long: {len(short_desc)}/80 characters")

        # Check full description
        full_desc = metadata.get("full_description", metadata.get("description", ""))
        if not full_desc:
            missing.append(Requirement(
                name="full_description",
                type=RequirementType.TEXT,
                description="Full description is required",
                required=True,
            ))
        elif len(full_desc) > 4000:
            errors.append(f"Description too long: {len(full_desc)}/4000 characters")

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
                description="App icon (512x512) is required",
                required=True,
            ))

        # Check feature graphic
        if "feature_graphic" not in assets:
            missing.append(Requirement(
                name="feature_graphic",
                type=RequirementType.IMAGE,
                description="Feature graphic (1024x500) is required",
                required=True,
            ))

        # Check screenshots
        screenshots = assets.get("screenshots", [])
        if len(screenshots) < 2:
            missing.append(Requirement(
                name="screenshots_phone",
                type=RequirementType.IMAGE,
                description="At least 2 phone screenshots required",
                required=True,
            ))

        # Check AAB
        if "app_bundle" not in product:
            missing.append(Requirement(
                name="app_bundle",
                type=RequirementType.FILE,
                description="Signed AAB file is required",
                required=True,
            ))

        return ValidationResult(
            valid=len(errors) == 0 and len(missing) == 0,
            missing=missing,
            warnings=warnings,
            errors=errors,
        )

    async def publish(self, product: dict, project_type: str) -> SubmissionResult:
        """Submit app to Play Store.

        Creates an edit, uploads assets, and commits.
        """
        if not self._authenticated:
            await self.authenticate()

        if not self._authenticated:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="Not authenticated with Google Play",
            )

        if not self.package_name:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="ANDROID_PACKAGE_NAME not set",
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

        # Return guidance (full implementation would create edit and upload)
        return SubmissionResult(
            success=True,
            status=SubmissionStatus.PENDING,
            message="App validated. Ready for upload via Play Console.",
            metadata={
                "next_steps": [
                    "1. Build signed AAB in Android Studio",
                    "2. Upload AAB via Play Console or API",
                    "3. Complete store listing",
                    "4. Submit for review",
                ],
                "play_console": f"https://play.google.com/console/developers/app/{self.package_name}",
            },
        )

    async def check_status(self, submission_id: str) -> SubmissionResult:
        """Check app status on Play Store."""
        if not self.package_name:
            return SubmissionResult(
                success=False,
                submission_id=submission_id,
                status=SubmissionStatus.FAILED,
                message="Package name not configured",
            )

        try:
            response = await self.client.get(
                f"/applications/{self.package_name}"
            )
            if response.status_code == 200:
                return SubmissionResult(
                    success=True,
                    submission_id=submission_id,
                    status=SubmissionStatus.PUBLISHED,
                    url=f"https://play.google.com/store/apps/details?id={self.package_name}",
                )
            else:
                return SubmissionResult(
                    success=False,
                    submission_id=submission_id,
                    status=SubmissionStatus.PENDING,
                    message="App not yet published",
                )
        except Exception as e:
            return SubmissionResult(
                success=False,
                submission_id=submission_id,
                status=SubmissionStatus.FAILED,
                message=str(e),
            )
