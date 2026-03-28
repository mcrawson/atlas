"""Specialized builders for ATLAS product creation.

Each builder is an expert in its domain:
- PrintableBuilder: Planners, cards, worksheets (digital PDF that customers print)
- DocumentBuilder: Books, guides, manuals (PDF/EPUB output)
- WebBuilder: Landing pages, SPAs, dashboards (HTML/CSS/JS output)
- AppBuilder: Mobile apps (React Native output)

Usage:
    from atlas.agents.builders import get_builder, BUILDERS

    # Get a builder by product type
    builder = get_builder("printable_planner")
    output = await builder.build(context)

    # List all available builders
    print(BUILDERS.keys())
"""

from typing import Optional, Type

from .base import (
    BaseBuilder,
    BuilderType,
    BuildOutput,
    BuildContext,
    OutputFormat,
)
from .config import (
    BuilderConfig,
    get_builder_config,
    get_printable_config,
    get_document_config,
    get_web_config,
    get_app_config,
)
from .printable import PrintableBuilder
from .document import DocumentBuilder
from .web import WebBuilder
from .app import AppBuilder


# Builder registry - maps product types to builder classes
BUILDERS: dict[str, Type[BaseBuilder]] = {
    # Printable products (digital PDFs customers print themselves) ✅
    "printable_planner": PrintableBuilder,
    "printable_cards": PrintableBuilder,
    "printable_worksheets": PrintableBuilder,
    "printable": PrintableBuilder,
    "planner": PrintableBuilder,
    "cards": PrintableBuilder,
    "worksheet": PrintableBuilder,
    "journal": PrintableBuilder,
    "tracker": PrintableBuilder,

    # Document products ✅
    "doc_book": DocumentBuilder,
    "doc_guide": DocumentBuilder,
    "doc_manual": DocumentBuilder,
    "book": DocumentBuilder,
    "guide": DocumentBuilder,
    "manual": DocumentBuilder,
    "ebook": DocumentBuilder,
    "handbook": DocumentBuilder,

    # Web products ✅
    "web_landing": WebBuilder,
    "web_spa": WebBuilder,
    "web_dashboard": WebBuilder,
    "landing_page": WebBuilder,
    "spa": WebBuilder,
    "dashboard": WebBuilder,
    "website": WebBuilder,
    "portfolio": WebBuilder,

    # App products ✅
    "mobile_ios": AppBuilder,
    "mobile_android": AppBuilder,
    "mobile_cross_platform": AppBuilder,
    "ios": AppBuilder,
    "android": AppBuilder,
    "mobile": AppBuilder,
    "app": AppBuilder,
}

# Cache of instantiated builders
_builder_instances: dict[str, BaseBuilder] = {}


def get_builder(
    product_type: str,
    config: Optional[dict] = None,
    cached: bool = True,
) -> Optional[BaseBuilder]:
    """Get a builder for a specific product type.

    Args:
        product_type: Type of product (e.g., "printable_planner", "web_spa")
        config: Optional configuration dict
        cached: Whether to return cached instance

    Returns:
        Builder instance or None if no builder for this type
    """
    product_type = product_type.lower().replace(" ", "_").replace("-", "_")

    if product_type not in BUILDERS:
        return None

    if cached and product_type in _builder_instances and config is None:
        return _builder_instances[product_type]

    builder_class = BUILDERS[product_type]
    instance = builder_class(config)

    if cached and config is None:
        _builder_instances[product_type] = instance

    return instance


def get_builder_for_type(project_type: str) -> Optional[BaseBuilder]:
    """Get the appropriate builder for a project type.

    This handles mapping from project metadata types to builders.

    Args:
        project_type: Project type from metadata

    Returns:
        Builder instance or None
    """
    # Map common project type variations to builder types
    type_mappings = {
        # Printables (digital PDFs customers print themselves)
        "planner": "printable_planner",
        "weekly_planner": "printable_planner",
        "daily_planner": "printable_planner",
        "cards": "printable_cards",
        "recipe_cards": "printable_cards",
        "flash_cards": "printable_cards",
        "worksheet": "printable_worksheets",
        "worksheets": "printable_worksheets",
        "printable": "printable_planner",

        # Documents
        "book": "doc_book",
        "ebook": "doc_book",
        "guide": "doc_guide",
        "manual": "doc_manual",
        "handbook": "doc_manual",

        # Apps
        "ios": "mobile_ios",
        "android": "mobile_android",
        "mobile": "mobile_cross_platform",
        "app": "mobile_cross_platform",

        # Web
        "landing": "web_landing",
        "landing_page": "web_landing",
        "spa": "web_spa",
        "dashboard": "web_dashboard",
        "web": "web_spa",
        "website": "web_spa",
    }

    normalized_type = project_type.lower().replace(" ", "_").replace("-", "_")

    # Direct match
    if normalized_type in BUILDERS:
        return get_builder(normalized_type)

    # Mapped match
    if normalized_type in type_mappings:
        return get_builder(type_mappings[normalized_type])

    return None


def list_builders() -> list[dict]:
    """List all available builders with their info."""
    builders = []
    for product_type, builder_class in BUILDERS.items():
        builders.append({
            "product_type": product_type,
            "builder_class": builder_class.__name__,
            "builder_type": builder_class.builder_type.value if hasattr(builder_class, 'builder_type') else None,
        })
    return builders


def register_builder(product_type: str, builder_class: Type[BaseBuilder]):
    """Register a new builder for a product type.

    Args:
        product_type: The product type key
        builder_class: The builder class to register
    """
    BUILDERS[product_type] = builder_class


__all__ = [
    # Base classes
    "BaseBuilder",
    "BuilderType",
    "BuildOutput",
    "BuildContext",
    "OutputFormat",
    # Builders
    "PrintableBuilder",
    "DocumentBuilder",
    "WebBuilder",
    "AppBuilder",
    # Config
    "BuilderConfig",
    "get_builder_config",
    "get_printable_config",
    "get_document_config",
    "get_web_config",
    "get_app_config",
    # Registry
    "BUILDERS",
    "get_builder",
    "get_builder_for_type",
    "list_builders",
    "register_builder",
]
