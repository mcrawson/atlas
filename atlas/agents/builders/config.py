"""Configuration for builders.

Settings that change often are kept here, separate from code.
This allows tweaking behavior without touching builder implementations.
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class BuilderConfig:
    """Global configuration for all builders."""

    # Model settings
    default_model: str = "gpt-4o"
    fast_model: str = "gpt-4o-mini"

    # Quality settings
    max_retries: int = 3
    quality_threshold: float = 0.8  # Minimum QC score to pass

    # Output settings
    include_source_code: bool = True  # Include source alongside rendered output
    generate_readme: bool = True

    # Preview settings
    enable_live_preview: bool = True
    preview_port: int = 3000

    @classmethod
    def from_env(cls) -> "BuilderConfig":
        """Load configuration from environment variables."""
        return cls(
            default_model=os.getenv("ATLAS_BUILDER_MODEL", "gpt-4o"),
            fast_model=os.getenv("ATLAS_BUILDER_FAST_MODEL", "gpt-4o-mini"),
            max_retries=int(os.getenv("ATLAS_BUILDER_MAX_RETRIES", "3")),
            quality_threshold=float(os.getenv("ATLAS_BUILDER_QUALITY_THRESHOLD", "0.8")),
            include_source_code=os.getenv("ATLAS_BUILDER_INCLUDE_SOURCE", "true").lower() == "true",
            generate_readme=os.getenv("ATLAS_BUILDER_GENERATE_README", "true").lower() == "true",
            enable_live_preview=os.getenv("ATLAS_BUILDER_LIVE_PREVIEW", "true").lower() == "true",
            preview_port=int(os.getenv("ATLAS_BUILDER_PREVIEW_PORT", "3000")),
        )


@dataclass
class PrintableConfig:
    """Configuration specific to PrintableBuilder."""

    # Page settings
    default_page_size: str = "letter"  # letter, a4, a5
    default_orientation: str = "portrait"  # portrait, landscape

    # Style settings
    default_font_family: str = "Inter"
    default_font_size: int = 12
    accent_color: str = "#3B82F6"  # Blue

    # Output settings
    pdf_quality: str = "high"  # low, medium, high
    embed_fonts: bool = True


@dataclass
class DocumentConfig:
    """Configuration specific to DocumentBuilder."""

    # Document settings
    default_format: str = "pdf"  # pdf, epub
    include_toc: bool = True
    include_index: bool = False

    # Style settings
    chapter_style: str = "modern"  # classic, modern, minimal
    default_font_family: str = "Georgia"
    body_font_size: int = 11
    heading_font_family: str = "Inter"


@dataclass
class WebConfig:
    """Configuration specific to WebBuilder."""

    # Framework settings
    default_framework: str = "vanilla"  # vanilla, react, vue, svelte
    use_typescript: bool = True
    use_tailwind: bool = True

    # Build settings
    minify_output: bool = True
    generate_sourcemaps: bool = False

    # Hosting suggestions
    recommended_host: str = "vercel"


@dataclass
class AppConfig:
    """Configuration specific to AppBuilder."""

    # Framework settings
    framework: str = "react-native"  # Always React Native for cross-platform
    use_expo: bool = True  # Use Expo for easier development

    # Target platforms
    target_ios: bool = True
    target_android: bool = True

    # UI settings
    default_navigation: str = "stack"  # stack, tab, drawer
    use_native_components: bool = True


# Global builder config instance
_builder_config: Optional[BuilderConfig] = None


def get_builder_config() -> BuilderConfig:
    """Get the global builder configuration."""
    global _builder_config
    if _builder_config is None:
        _builder_config = BuilderConfig.from_env()
    return _builder_config


def get_printable_config() -> PrintableConfig:
    """Get PrintableBuilder configuration."""
    return PrintableConfig()


def get_document_config() -> DocumentConfig:
    """Get DocumentBuilder configuration."""
    return DocumentConfig()


def get_web_config() -> WebConfig:
    """Get WebBuilder configuration."""
    return WebConfig()


def get_app_config() -> AppConfig:
    """Get AppBuilder configuration."""
    return AppConfig()
