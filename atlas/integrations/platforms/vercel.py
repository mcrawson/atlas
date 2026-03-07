"""Vercel integration for web app deployment.

Vercel API allows:
- Creating deployments
- Managing projects
- Environment variables
- Domain configuration
- Deployment status

Use cases in ATLAS:
- One-click web deployment
- Preview deployments
- Environment management
- Domain setup
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


class VercelIntegration(PlatformIntegration):
    """Vercel deployment integration."""

    name = "Vercel"
    icon = "▲"
    category = PlatformCategory.HOSTING
    description = "Deploy web apps with zero configuration"
    docs_url = "https://vercel.com/docs/rest-api"

    supported_types = ["web", "web_spa", "web_static", "web_fullstack", "web_landing"]

    BASE_URL = "https://api.vercel.com"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.api_token = config.get("api_token") if config else os.getenv("VERCEL_TOKEN")
        self.team_id = config.get("team_id") if config else os.getenv("VERCEL_TEAM_ID")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=60.0,  # Deployments can take time
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def get_env_vars(self) -> list[str]:
        return ["VERCEL_TOKEN", "VERCEL_TEAM_ID"]

    async def authenticate(self) -> bool:
        """Verify Vercel API token."""
        if not self.api_token:
            logger.warning("VERCEL_TOKEN not set")
            return False

        try:
            response = await self.client.get("/v2/user")
            if response.status_code == 200:
                self._authenticated = True
                user = response.json().get("user", {})
                logger.info(f"Authenticated with Vercel as {user.get('username', 'Unknown')}")
                return True
            else:
                logger.error(f"Vercel auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.exception(f"Vercel auth error: {e}")
            return False

    def get_requirements(self, project_type: str) -> list[Requirement]:
        """Get Vercel deployment requirements."""
        requirements = [
            Requirement(
                name="vercel_token",
                type=RequirementType.CREDENTIAL,
                description="Vercel API token",
                required=True,
            ),
            Requirement(
                name="project_files",
                type=RequirementType.FILE,
                description="Project source files",
                required=True,
            ),
        ]

        # Framework-specific requirements
        if project_type in ["web_spa", "web_fullstack"]:
            requirements.extend([
                Requirement(
                    name="package_json",
                    type=RequirementType.FILE,
                    description="package.json with build script",
                    required=True,
                ),
                Requirement(
                    name="build_command",
                    type=RequirementType.CONFIG,
                    description="Build command (e.g., 'npm run build')",
                    required=False,
                ),
                Requirement(
                    name="output_directory",
                    type=RequirementType.CONFIG,
                    description="Build output directory (e.g., 'dist', 'build')",
                    required=False,
                ),
            ])

        # Optional
        requirements.extend([
            Requirement(
                name="env_variables",
                type=RequirementType.CONFIG,
                description="Environment variables",
                required=False,
            ),
            Requirement(
                name="domain",
                type=RequirementType.CONFIG,
                description="Custom domain",
                required=False,
            ),
        ])

        return requirements

    def validate(self, product: dict, project_type: str) -> ValidationResult:
        """Validate project for Vercel deployment."""
        missing = []
        warnings = []
        errors = []

        files = product.get("files", {})
        config = product.get("config", {})

        # Check credentials
        if not self.api_token:
            errors.append("VERCEL_TOKEN not configured")

        # Check for basic project structure
        if not files:
            missing.append(Requirement(
                name="project_files",
                type=RequirementType.FILE,
                description="No project files found",
                required=True,
            ))

        # Check for package.json in JS projects
        if project_type in ["web_spa", "web_fullstack"]:
            if "package.json" not in files:
                warnings.append("No package.json found. Vercel may not detect framework.")

        # Check for index.html in static projects
        if project_type == "web_static":
            has_index = any("index.html" in f for f in files.keys())
            if not has_index:
                missing.append(Requirement(
                    name="index_html",
                    type=RequirementType.FILE,
                    description="index.html is required for static sites",
                    required=True,
                ))

        # Check for vercel.json (optional but recommended)
        if "vercel.json" not in files:
            warnings.append("No vercel.json found. Using default settings.")

        return ValidationResult(
            valid=len(errors) == 0 and len(missing) == 0,
            missing=missing,
            warnings=warnings,
            errors=errors,
        )

    async def publish(self, product: dict, project_type: str) -> SubmissionResult:
        """Deploy project to Vercel."""
        if not self._authenticated:
            await self.authenticate()

        if not self._authenticated:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="Not authenticated with Vercel",
            )

        # Get project name
        project_name = product.get("name", "atlas-project").lower()
        project_name = "".join(c if c.isalnum() or c == "-" else "-" for c in project_name)

        files = product.get("files", {})

        if not files:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="No files to deploy",
            )

        try:
            # Create deployment
            deployment_files = []
            for path, content in files.items():
                if isinstance(content, str):
                    deployment_files.append({
                        "file": path,
                        "data": content,
                    })

            payload = {
                "name": project_name,
                "files": deployment_files,
                "projectSettings": {
                    "framework": self._detect_framework(files),
                },
            }

            if self.team_id:
                payload["teamId"] = self.team_id

            response = await self.client.post("/v13/deployments", json=payload)

            if response.status_code in [200, 201]:
                deployment = response.json()
                deployment_url = f"https://{deployment.get('url')}"

                return SubmissionResult(
                    success=True,
                    submission_id=deployment.get("id"),
                    status=SubmissionStatus.PROCESSING,
                    url=deployment_url,
                    message=f"Deployment started: {deployment_url}",
                    metadata={
                        "deployment_id": deployment.get("id"),
                        "url": deployment_url,
                        "project_id": deployment.get("projectId"),
                    },
                )
            else:
                error_msg = response.json().get("error", {}).get("message", "Unknown error")
                return SubmissionResult(
                    success=False,
                    status=SubmissionStatus.FAILED,
                    message=f"Deployment failed: {error_msg}",
                )

        except Exception as e:
            logger.exception(f"Vercel deployment error: {e}")
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message=str(e),
            )

    async def check_status(self, submission_id: str) -> SubmissionResult:
        """Check deployment status."""
        try:
            response = await self.client.get(f"/v13/deployments/{submission_id}")

            if response.status_code == 200:
                deployment = response.json()
                state = deployment.get("readyState", "QUEUED")

                status_map = {
                    "QUEUED": SubmissionStatus.PENDING,
                    "BUILDING": SubmissionStatus.PROCESSING,
                    "READY": SubmissionStatus.PUBLISHED,
                    "ERROR": SubmissionStatus.FAILED,
                    "CANCELED": SubmissionStatus.FAILED,
                }

                return SubmissionResult(
                    success=state == "READY",
                    submission_id=submission_id,
                    status=status_map.get(state, SubmissionStatus.PROCESSING),
                    url=f"https://{deployment.get('url')}",
                    metadata=deployment,
                )
            else:
                return SubmissionResult(
                    success=False,
                    submission_id=submission_id,
                    status=SubmissionStatus.FAILED,
                    message=f"Deployment not found: {response.status_code}",
                )
        except Exception as e:
            return SubmissionResult(
                success=False,
                submission_id=submission_id,
                status=SubmissionStatus.FAILED,
                message=str(e),
            )

    def _detect_framework(self, files: dict) -> Optional[str]:
        """Detect framework from project files."""
        if "package.json" in files:
            try:
                import json
                pkg = json.loads(files["package.json"])
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                if "next" in deps:
                    return "nextjs"
                if "nuxt" in deps:
                    return "nuxtjs"
                if "gatsby" in deps:
                    return "gatsby"
                if "@sveltejs/kit" in deps:
                    return "sveltekit"
                if "svelte" in deps:
                    return "svelte"
                if "vue" in deps:
                    return "vue"
                if "react" in deps:
                    return "create-react-app"
                if "vite" in deps:
                    return "vite"
            except (json.JSONDecodeError, KeyError):
                pass

        # Check for static site
        if any("index.html" in f for f in files.keys()):
            return None  # Static, no framework

        return None

    async def get_projects(self) -> list[dict]:
        """Get all Vercel projects."""
        try:
            params = {}
            if self.team_id:
                params["teamId"] = self.team_id

            response = await self.client.get("/v9/projects", params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("projects", [])
            return []
        except Exception as e:
            logger.exception(f"Error fetching projects: {e}")
            return []

    async def set_env_vars(
        self,
        project_id: str,
        env_vars: dict[str, str],
        target: str = "production",
    ) -> bool:
        """Set environment variables for a project.

        Args:
            project_id: Vercel project ID
            env_vars: Dict of variable names to values
            target: Environment target (production, preview, development)

        Returns:
            True if successful
        """
        try:
            for key, value in env_vars.items():
                payload = {
                    "key": key,
                    "value": value,
                    "target": [target],
                    "type": "encrypted",
                }

                response = await self.client.post(
                    f"/v10/projects/{project_id}/env",
                    json=payload,
                )

                if response.status_code not in [200, 201]:
                    logger.error(f"Failed to set env var {key}: {response.status_code}")
                    return False

            return True

        except Exception as e:
            logger.exception(f"Error setting env vars: {e}")
            return False
