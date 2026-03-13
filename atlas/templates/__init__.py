"""Template system for ATLAS product generation."""

from .engine import (
    render_template,
    render_planner,
    get_available_templates,
    TemplateResult,
    TemplateConfig,
    COLOR_SCHEMES,
    QUOTES,
    DEFAULT_HABITS,
)

__all__ = [
    "render_template",
    "render_planner",
    "get_available_templates",
    "TemplateResult",
    "TemplateConfig",
    "COLOR_SCHEMES",
    "QUOTES",
    "DEFAULT_HABITS",
]
