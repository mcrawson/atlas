"""npm (Node Package Manager) integration.

npm Registry API allows:
- Publishing packages
- Managing package metadata
- Version management
- Access control

Use cases in ATLAS:
- Publishing JavaScript/TypeScript libraries
- Validating package.json
- Version bumping
- README generation
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


class NpmIntegration(PlatformIntegration):
    """npm registry integration."""

    name = "npm"
    icon = "📦"
    category = PlatformCategory.PACKAGES
    description = "Publish JavaScript and TypeScript packages"
    docs_url = "https://docs.npmjs.com/"

    supported_types = ["library", "lib_npm", "cli_node"]

    REGISTRY_URL = "https://registry.npmjs.org"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.auth_token = config.get("auth_token") if config else os.getenv("NPM_TOKEN")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
            }
            self._client = httpx.AsyncClient(
                base_url=self.REGISTRY_URL,
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
        return ["NPM_TOKEN"]

    async def authenticate(self) -> bool:
        """Verify npm authentication."""
        if not self.auth_token:
            logger.warning("NPM_TOKEN not set")
            return False

        try:
            # Check token by getting user info
            response = await self.client.get("/-/npm/v1/user")
            if response.status_code == 200:
                self._authenticated = True
                user = response.json()
                logger.info(f"Authenticated with npm as {user.get('name', 'Unknown')}")
                return True
            else:
                logger.error(f"npm auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.exception(f"npm auth error: {e}")
            return False

    def get_requirements(self, project_type: str) -> list[Requirement]:
        """Get npm publishing requirements."""
        requirements = [
            Requirement(
                name="npm_token",
                type=RequirementType.CREDENTIAL,
                description="npm authentication token",
                required=True,
            ),
            Requirement(
                name="package_json",
                type=RequirementType.FILE,
                description="package.json with name, version, and main",
                required=True,
            ),
            Requirement(
                name="package_name",
                type=RequirementType.TEXT,
                description="Unique package name",
                required=True,
            ),
            Requirement(
                name="package_version",
                type=RequirementType.TEXT,
                description="Semantic version (e.g., 1.0.0)",
                required=True,
            ),
            Requirement(
                name="main_entry",
                type=RequirementType.FILE,
                description="Main entry point file",
                required=True,
            ),
        ]

        # TypeScript packages
        if "typescript" in project_type or "ts" in project_type:
            requirements.append(Requirement(
                name="type_definitions",
                type=RequirementType.FILE,
                description="TypeScript type definitions (.d.ts)",
                required=False,
            ))

        # Recommended but optional
        requirements.extend([
            Requirement(
                name="readme",
                type=RequirementType.FILE,
                description="README.md file",
                required=False,
            ),
            Requirement(
                name="license",
                type=RequirementType.FILE,
                description="LICENSE file",
                required=False,
            ),
            Requirement(
                name="repository",
                type=RequirementType.CONFIG,
                description="Repository URL in package.json",
                required=False,
            ),
        ])

        return requirements

    def validate(self, product: dict, project_type: str) -> ValidationResult:
        """Validate package for npm publishing."""
        missing = []
        warnings = []
        errors = []

        files = product.get("files", {})
        package_json = None

        # Check credentials
        if not self.auth_token:
            errors.append("NPM_TOKEN not configured")

        # Check package.json
        if "package.json" not in files:
            missing.append(Requirement(
                name="package_json",
                type=RequirementType.FILE,
                description="package.json is required",
                required=True,
            ))
        else:
            try:
                import json
                package_json = json.loads(files["package.json"])

                # Check required fields
                if not package_json.get("name"):
                    errors.append("package.json missing 'name' field")

                if not package_json.get("version"):
                    errors.append("package.json missing 'version' field")
                else:
                    version = package_json["version"]
                    if not self._is_valid_semver(version):
                        errors.append(f"Invalid version format: {version}")

                if not package_json.get("main") and not package_json.get("exports"):
                    warnings.append("package.json missing 'main' or 'exports' field")

                # Check for private flag
                if package_json.get("private"):
                    errors.append("Package is marked as private. Remove 'private: true' to publish.")

                # Check optional but recommended fields
                if not package_json.get("description"):
                    warnings.append("Missing description in package.json")

                if not package_json.get("repository"):
                    warnings.append("Missing repository URL in package.json")

                if not package_json.get("keywords"):
                    warnings.append("No keywords specified (helps discoverability)")

            except json.JSONDecodeError:
                errors.append("Invalid JSON in package.json")

        # Check README
        has_readme = any(f.lower() in ["readme.md", "readme"] for f in files.keys())
        if not has_readme:
            warnings.append("No README.md found. Add one for npm listing.")

        # Check LICENSE
        has_license = any("license" in f.lower() for f in files.keys())
        if not has_license:
            warnings.append("No LICENSE file found")

        # Check main entry point
        if package_json:
            main = package_json.get("main", "index.js")
            if main not in files and not any(f.endswith(main) for f in files.keys()):
                warnings.append(f"Main entry point '{main}' not found in files")

        return ValidationResult(
            valid=len(errors) == 0 and len(missing) == 0,
            missing=missing,
            warnings=warnings,
            errors=errors,
        )

    def _is_valid_semver(self, version: str) -> bool:
        """Check if version follows semver format."""
        import re
        pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$"
        return bool(re.match(pattern, version))

    async def publish(self, product: dict, project_type: str) -> SubmissionResult:
        """Publish package to npm.

        Note: Full npm publish requires creating a tarball.
        This provides guidance for using npm CLI.
        """
        if not self._authenticated:
            await self.authenticate()

        # Validate first
        validation = self.validate(product, project_type)
        if not validation.valid:
            return SubmissionResult(
                success=False,
                status=SubmissionStatus.FAILED,
                message="Validation failed",
                metadata={"validation": validation.to_dict()},
            )

        files = product.get("files", {})
        try:
            import json
            package_json = json.loads(files.get("package.json", "{}"))
            package_name = package_json.get("name", "unknown")
            version = package_json.get("version", "0.0.0")
        except (json.JSONDecodeError, KeyError):
            package_name = "unknown"
            version = "0.0.0"

        # Check if package name is available
        is_available = await self._check_name_available(package_name)

        return SubmissionResult(
            success=True,
            status=SubmissionStatus.PENDING,
            message=f"Package {package_name}@{version} ready for publishing",
            metadata={
                "validation": validation.to_dict(),
                "package_name": package_name,
                "version": version,
                "name_available": is_available,
                "next_steps": [
                    "1. Ensure you're logged in: npm login",
                    f"2. Check name availability: npm view {package_name}",
                    "3. Test locally: npm pack",
                    "4. Publish: npm publish" + (" --access public" if "@" in package_name else ""),
                ],
                "commands": {
                    "login": "npm login",
                    "test": "npm pack --dry-run",
                    "publish": "npm publish" + (" --access public" if "@" in package_name else ""),
                    "unpublish": f"npm unpublish {package_name}@{version}",
                },
            },
        )

    async def check_status(self, submission_id: str) -> SubmissionResult:
        """Check if package exists on npm."""
        try:
            # submission_id is package name
            response = await self.client.get(f"/{submission_id}")

            if response.status_code == 200:
                package_data = response.json()
                latest = package_data.get("dist-tags", {}).get("latest", "unknown")

                return SubmissionResult(
                    success=True,
                    submission_id=submission_id,
                    status=SubmissionStatus.PUBLISHED,
                    url=f"https://www.npmjs.com/package/{submission_id}",
                    metadata={
                        "latest_version": latest,
                        "versions": list(package_data.get("versions", {}).keys()),
                    },
                )
            elif response.status_code == 404:
                return SubmissionResult(
                    success=False,
                    submission_id=submission_id,
                    status=SubmissionStatus.PENDING,
                    message="Package not yet published",
                )
            else:
                return SubmissionResult(
                    success=False,
                    submission_id=submission_id,
                    status=SubmissionStatus.FAILED,
                    message=f"Error checking package: {response.status_code}",
                )
        except Exception as e:
            return SubmissionResult(
                success=False,
                submission_id=submission_id,
                status=SubmissionStatus.FAILED,
                message=str(e),
            )

    async def _check_name_available(self, name: str) -> bool:
        """Check if a package name is available."""
        try:
            response = await self.client.get(f"/{name}")
            return response.status_code == 404
        except Exception:
            return False

    async def get_package_info(self, name: str) -> Optional[dict]:
        """Get package information from npm registry."""
        try:
            response = await self.client.get(f"/{name}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.exception(f"Error fetching package info: {e}")
            return None

    def generate_package_json(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        main: str = "index.js",
        author: str = "",
        license: str = "MIT",
        repository: Optional[str] = None,
        keywords: Optional[list[str]] = None,
    ) -> dict:
        """Generate a package.json template.

        Args:
            name: Package name
            version: Semantic version
            description: Package description
            main: Main entry point
            author: Author name/email
            license: License type
            repository: Repository URL
            keywords: Search keywords

        Returns:
            package.json as dict
        """
        pkg = {
            "name": name,
            "version": version,
            "description": description,
            "main": main,
            "scripts": {
                "test": "echo \"Error: no test specified\" && exit 1",
            },
            "keywords": keywords or [],
            "author": author,
            "license": license,
        }

        if repository:
            pkg["repository"] = {
                "type": "git",
                "url": repository,
            }

        return pkg
