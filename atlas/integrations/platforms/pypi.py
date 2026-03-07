"""PyPI (Python Package Index) integration.

PyPI allows:
- Publishing Python packages
- Managing package metadata
- Version management

Use cases in ATLAS:
- Publishing Python libraries
- Validating pyproject.toml/setup.py
- Version management
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


class PyPIIntegration(PlatformIntegration):
    """PyPI registry integration."""

    name = "PyPI"
    icon = "🐍"
    category = PlatformCategory.PACKAGES
    description = "Publish Python packages"
    docs_url = "https://packaging.python.org/"

    supported_types = ["library", "lib_python", "cli_python"]

    PYPI_URL = "https://pypi.org"
    TEST_PYPI_URL = "https://test.pypi.org"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.api_token = config.get("api_token") if config else os.getenv("PYPI_TOKEN")
        self.use_test_pypi = config.get("use_test_pypi", False) if config else os.getenv("USE_TEST_PYPI", "").lower() == "true"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def base_url(self) -> str:
        """Get PyPI URL based on configuration."""
        return self.TEST_PYPI_URL if self.use_test_pypi else self.PYPI_URL

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def get_env_vars(self) -> list[str]:
        return ["PYPI_TOKEN", "USE_TEST_PYPI"]

    async def authenticate(self) -> bool:
        """Verify PyPI API token exists.

        Note: PyPI doesn't have a token verification endpoint.
        We just check the token is set.
        """
        if not self.api_token:
            logger.warning("PYPI_TOKEN not set")
            return False

        self._authenticated = True
        logger.info(f"PyPI token configured for {'TestPyPI' if self.use_test_pypi else 'PyPI'}")
        return True

    def get_requirements(self, project_type: str) -> list[Requirement]:
        """Get PyPI publishing requirements."""
        requirements = [
            Requirement(
                name="pypi_token",
                type=RequirementType.CREDENTIAL,
                description="PyPI API token",
                required=True,
            ),
            Requirement(
                name="pyproject_toml",
                type=RequirementType.FILE,
                description="pyproject.toml with build configuration",
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
                description="Version string (PEP 440 compliant)",
                required=True,
            ),
            Requirement(
                name="python_source",
                type=RequirementType.FILE,
                description="Python source files",
                required=True,
            ),
        ]

        # Recommended
        requirements.extend([
            Requirement(
                name="readme",
                type=RequirementType.FILE,
                description="README.md or README.rst",
                required=False,
            ),
            Requirement(
                name="license",
                type=RequirementType.FILE,
                description="LICENSE file",
                required=False,
            ),
            Requirement(
                name="changelog",
                type=RequirementType.FILE,
                description="CHANGELOG.md",
                required=False,
            ),
        ])

        return requirements

    def validate(self, product: dict, project_type: str) -> ValidationResult:
        """Validate package for PyPI publishing."""
        missing = []
        warnings = []
        errors = []

        files = product.get("files", {})

        # Check credentials
        if not self.api_token:
            errors.append("PYPI_TOKEN not configured")

        # Check for pyproject.toml or setup.py
        has_pyproject = "pyproject.toml" in files
        has_setup_py = "setup.py" in files

        if not has_pyproject and not has_setup_py:
            missing.append(Requirement(
                name="pyproject_toml",
                type=RequirementType.FILE,
                description="pyproject.toml is required",
                required=True,
            ))
        elif has_pyproject:
            # Validate pyproject.toml
            pyproject = files["pyproject.toml"]
            try:
                import tomllib
                config = tomllib.loads(pyproject)

                # Check for required sections
                project = config.get("project", {})

                if not project.get("name"):
                    errors.append("pyproject.toml missing [project].name")

                if not project.get("version"):
                    errors.append("pyproject.toml missing [project].version")

                if not project.get("description"):
                    warnings.append("pyproject.toml missing [project].description")

                # Check build system
                build_system = config.get("build-system", {})
                if not build_system.get("requires"):
                    warnings.append("pyproject.toml missing [build-system].requires")

            except ImportError:
                # tomllib not available (Python < 3.11)
                warnings.append("Cannot validate pyproject.toml (tomllib not available)")
            except Exception as e:
                errors.append(f"Invalid pyproject.toml: {e}")

        elif has_setup_py:
            warnings.append("Using setup.py. Consider migrating to pyproject.toml")

        # Check README
        has_readme = any(
            f.lower() in ["readme.md", "readme.rst", "readme.txt", "readme"]
            for f in files.keys()
        )
        if not has_readme:
            warnings.append("No README found. Add one for PyPI listing.")

        # Check LICENSE
        has_license = any("license" in f.lower() for f in files.keys())
        if not has_license:
            warnings.append("No LICENSE file found")

        # Check for __init__.py in package
        has_init = any("__init__.py" in f for f in files.keys())
        if not has_init:
            warnings.append("No __init__.py found. Make sure it's a valid Python package.")

        return ValidationResult(
            valid=len(errors) == 0 and len(missing) == 0,
            missing=missing,
            warnings=warnings,
            errors=errors,
        )

    async def publish(self, product: dict, project_type: str) -> SubmissionResult:
        """Guide user through PyPI publishing.

        Note: Actual publishing requires twine and building a wheel.
        """
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

        # Extract package info
        package_name = "unknown"
        version = "0.0.0"

        if "pyproject.toml" in files:
            try:
                import tomllib
                config = tomllib.loads(files["pyproject.toml"])
                project = config.get("project", {})
                package_name = project.get("name", package_name)
                version = project.get("version", version)
            except (ImportError, Exception):
                pass

        # Check name availability
        is_available = await self._check_name_available(package_name)

        upload_url = f"https://{'test.' if self.use_test_pypi else ''}pypi.org/legacy/"

        return SubmissionResult(
            success=True,
            status=SubmissionStatus.PENDING,
            message=f"Package {package_name} v{version} ready for publishing",
            metadata={
                "validation": validation.to_dict(),
                "package_name": package_name,
                "version": version,
                "name_available": is_available,
                "upload_url": upload_url,
                "next_steps": [
                    "1. Install build tools: pip install build twine",
                    "2. Build distribution: python -m build",
                    f"3. Upload: twine upload {'--repository testpypi ' if self.use_test_pypi else ''}dist/*",
                ],
                "commands": {
                    "install_tools": "pip install build twine",
                    "build": "python -m build",
                    "check": "twine check dist/*",
                    "upload": f"twine upload {'--repository testpypi ' if self.use_test_pypi else ''}dist/*",
                },
                "pypirc_example": f"""
[pypi]
username = __token__
password = {self.api_token or 'YOUR_PYPI_TOKEN'}
""" if not self.use_test_pypi else f"""
[testpypi]
username = __token__
password = {self.api_token or 'YOUR_TESTPYPI_TOKEN'}
""",
            },
        )

    async def check_status(self, submission_id: str) -> SubmissionResult:
        """Check if package exists on PyPI."""
        try:
            # submission_id is package name
            response = await self.client.get(f"/pypi/{submission_id}/json")

            if response.status_code == 200:
                package_data = response.json()
                info = package_data.get("info", {})

                return SubmissionResult(
                    success=True,
                    submission_id=submission_id,
                    status=SubmissionStatus.PUBLISHED,
                    url=info.get("project_url", f"{self.base_url}/project/{submission_id}/"),
                    metadata={
                        "version": info.get("version"),
                        "summary": info.get("summary"),
                        "author": info.get("author"),
                        "releases": list(package_data.get("releases", {}).keys()),
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
            response = await self.client.get(f"/pypi/{name}/json")
            return response.status_code == 404
        except Exception:
            return False

    async def get_package_info(self, name: str) -> Optional[dict]:
        """Get package information from PyPI."""
        try:
            response = await self.client.get(f"/pypi/{name}/json")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.exception(f"Error fetching package info: {e}")
            return None

    def generate_pyproject_toml(
        self,
        name: str,
        version: str = "0.1.0",
        description: str = "",
        author_name: str = "",
        author_email: str = "",
        license: str = "MIT",
        python_requires: str = ">=3.8",
        dependencies: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None,
    ) -> str:
        """Generate a pyproject.toml template.

        Returns:
            pyproject.toml content as string
        """
        deps = "\n".join(f'    "{d}",' for d in (dependencies or []))
        kw = ", ".join(f'"{k}"' for k in (keywords or []))

        return f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "{version}"
description = "{description}"
readme = "README.md"
license = "{license}"
requires-python = "{python_requires}"
authors = [
    {{ name = "{author_name}", email = "{author_email}" }},
]
keywords = [{kw}]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
{deps}
]

[project.urls]
Homepage = "https://github.com/yourusername/{name}"
Documentation = "https://github.com/yourusername/{name}#readme"
Repository = "https://github.com/yourusername/{name}"
'''
