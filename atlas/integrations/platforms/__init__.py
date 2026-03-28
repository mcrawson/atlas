"""Platform integrations for ATLAS.

This module provides a unified interface for publishing to various platforms:
- Design: Figma
- Documents: Google Docs
- App Stores: Apple App Store, Google Play
- Publishing: Amazon KDP
- Hosting: Vercel
- Packages: npm, PyPI
- Code: GitHub (in ../github/)

Usage:
    from atlas.integrations.platforms import get_platform, list_platforms

    # Get a specific platform
    figma = get_platform("figma")
    await figma.authenticate()

    # List all available platforms
    platforms = list_platforms()

    # Get platforms by category
    app_stores = list_platforms(category="app_stores")

    # Get platforms for a project type
    platforms = get_platforms_for_type("mobile_ios")
"""

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

from .google_docs import GoogleDocsIntegration
from .figma import FigmaIntegration
from .app_store import AppStoreIntegration
from .play_store import PlayStoreIntegration
from .amazon_kdp import AmazonKDPIntegration
from .vercel import VercelIntegration
from .npm import NpmIntegration
from .pypi import PyPIIntegration


# Registry of all platform integrations
PLATFORM_REGISTRY: dict[str, type[PlatformIntegration]] = {
    "google_docs": GoogleDocsIntegration,
    "figma": FigmaIntegration,
    "app_store": AppStoreIntegration,
    "play_store": PlayStoreIntegration,
    "amazon_kdp": AmazonKDPIntegration,
    "vercel": VercelIntegration,
    "npm": NpmIntegration,
    "pypi": PyPIIntegration,
}

# Cache of instantiated platforms
_platform_instances: dict[str, PlatformIntegration] = {}


def get_platform(
    name: str,
    config: Optional[dict] = None,
    cached: bool = True,
) -> Optional[PlatformIntegration]:
    """Get a platform integration by name.

    Args:
        name: Platform name (e.g., "canva", "vercel")
        config: Optional configuration dict
        cached: Whether to return cached instance

    Returns:
        Platform integration instance or None if not found
    """
    name = name.lower().replace(" ", "_").replace("-", "_")

    if name not in PLATFORM_REGISTRY:
        return None

    if cached and name in _platform_instances and config is None:
        return _platform_instances[name]

    platform_class = PLATFORM_REGISTRY[name]
    instance = platform_class(config)

    if cached and config is None:
        _platform_instances[name] = instance

    return instance


def list_platforms(
    category: Optional[str] = None,
    project_type: Optional[str] = None,
) -> list[dict]:
    """List available platform integrations.

    Args:
        category: Filter by category (e.g., "design", "hosting")
        project_type: Filter by supported project type

    Returns:
        List of platform info dicts
    """
    platforms = []

    for name, platform_class in PLATFORM_REGISTRY.items():
        instance = get_platform(name)
        if instance is None:
            continue

        # Filter by category
        if category:
            if isinstance(category, str):
                category = PlatformCategory(category)
            if instance.category != category:
                continue

        # Filter by project type
        if project_type:
            if project_type not in instance.supported_types:
                # Check for partial matches
                if not any(project_type in t or t in project_type for t in instance.supported_types):
                    continue

        platforms.append({
            "id": name,
            **instance.to_dict(),
        })

    return platforms


def get_platforms_for_type(project_type: str) -> list[PlatformIntegration]:
    """Get all platforms that support a project type.

    Args:
        project_type: Project type (e.g., "mobile_ios", "web_spa")

    Returns:
        List of platform instances
    """
    platforms = []

    for name in PLATFORM_REGISTRY:
        instance = get_platform(name)
        if instance is None:
            continue

        # Check direct match
        if project_type in instance.supported_types:
            platforms.append(instance)
            continue

        # Check category match (e.g., "mobile_ios" matches "app")
        type_category = project_type.split("_")[0] if "_" in project_type else project_type
        if type_category in instance.supported_types:
            platforms.append(instance)

    return platforms


def get_platforms_by_category(category: PlatformCategory) -> list[PlatformIntegration]:
    """Get all platforms in a category.

    Args:
        category: Platform category

    Returns:
        List of platform instances
    """
    platforms = []

    for name in PLATFORM_REGISTRY:
        instance = get_platform(name)
        if instance and instance.category == category:
            platforms.append(instance)

    return platforms


async def validate_all(product: dict, project_type: str) -> dict[str, ValidationResult]:
    """Validate a product against all relevant platforms.

    Args:
        product: Product data
        project_type: Project type

    Returns:
        Dict of platform_name -> ValidationResult
    """
    results = {}
    platforms = get_platforms_for_type(project_type)

    for platform in platforms:
        results[platform.name] = platform.validate(product, project_type)

    return results


def get_all_requirements(project_type: str) -> dict[str, list[Requirement]]:
    """Get requirements from all relevant platforms.

    Args:
        project_type: Project type

    Returns:
        Dict of platform_name -> list of Requirements
    """
    requirements = {}
    platforms = get_platforms_for_type(project_type)

    for platform in platforms:
        reqs = platform.get_requirements(project_type)
        if reqs:
            requirements[platform.name] = reqs

    return requirements


def get_required_env_vars(project_type: Optional[str] = None) -> dict[str, list[str]]:
    """Get all required environment variables.

    Args:
        project_type: Optional filter by project type

    Returns:
        Dict of platform_name -> list of env var names
    """
    env_vars = {}

    if project_type:
        platforms = get_platforms_for_type(project_type)
    else:
        platforms = [get_platform(name) for name in PLATFORM_REGISTRY]

    for platform in platforms:
        if platform:
            vars = platform.get_env_vars()
            if vars:
                env_vars[platform.name] = vars

    return env_vars


__all__ = [
    # Base classes
    "PlatformIntegration",
    "PlatformCategory",
    "Requirement",
    "RequirementType",
    "ValidationResult",
    "SubmissionResult",
    "SubmissionStatus",
    # Platform implementations
    "GoogleDocsIntegration",
    "FigmaIntegration",
    "AppStoreIntegration",
    "PlayStoreIntegration",
    "AmazonKDPIntegration",
    "VercelIntegration",
    "NpmIntegration",
    "PyPIIntegration",
    # Registry functions
    "get_platform",
    "list_platforms",
    "get_platforms_for_type",
    "get_platforms_by_category",
    "validate_all",
    "get_all_requirements",
    "get_required_env_vars",
    "PLATFORM_REGISTRY",
]
