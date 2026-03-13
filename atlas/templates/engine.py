"""Template Engine for ATLAS product generation.

Instead of having LLMs generate complete HTML/CSS (which they abbreviate),
we use professional templates and have LLMs customize them.

This guarantees:
- Proper print CSS (@page, @media print)
- Complete structure (all days, all habits)
- Professional design
- Consistent quality
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("atlas.templates.engine")

TEMPLATES_DIR = Path(__file__).parent / "products"


@dataclass
class TemplateConfig:
    """Configuration for a template."""
    name: str
    template_file: str
    description: str
    variables: dict[str, str]  # variable_name -> description
    defaults: dict[str, str]  # variable_name -> default_value
    color_schemes: dict[str, dict[str, str]]  # scheme_name -> {var: color}


# Pre-defined color schemes
COLOR_SCHEMES = {
    "pastel_pink": {
        "primary_color": "#E8B4B8",
        "secondary_color": "#EED6D3",
        "bg_light": "#FFF5F5",
    },
    "pastel_blue": {
        "primary_color": "#A8D5E5",
        "secondary_color": "#D4EBF2",
        "bg_light": "#F0F8FF",
    },
    "pastel_green": {
        "primary_color": "#B5D8B5",
        "secondary_color": "#D4EAD4",
        "bg_light": "#F0FFF0",
    },
    "pastel_lavender": {
        "primary_color": "#C9B8D9",
        "secondary_color": "#E8DDF0",
        "bg_light": "#F8F4FC",
    },
    "pastel_peach": {
        "primary_color": "#F5C6A5",
        "secondary_color": "#FAE5D3",
        "bg_light": "#FFF8F0",
    },
    "minimalist": {
        "primary_color": "#4A4A4A",
        "secondary_color": "#6A6A6A",
        "bg_light": "#F5F5F5",
    },
    "ocean": {
        "primary_color": "#2E86AB",
        "secondary_color": "#5DA9C2",
        "bg_light": "#E8F4F8",
    },
    "forest": {
        "primary_color": "#4A7C59",
        "secondary_color": "#6B9B7A",
        "bg_light": "#F0F5F1",
    },
    "sunset": {
        "primary_color": "#E07A5F",
        "secondary_color": "#F2A488",
        "bg_light": "#FDF4F0",
    },
    "midnight": {
        "primary_color": "#3D405B",
        "secondary_color": "#5C5F7E",
        "bg_light": "#EEEEF2",
    },
}


# Motivational quotes for planners
QUOTES = [
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("Your time is limited, don't waste it living someone else's life.", "Steve Jobs"),
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    ("Start where you are. Use what you have. Do what you can.", "Arthur Ashe"),
    ("The future depends on what you do today.", "Mahatma Gandhi"),
    ("Don't watch the clock; do what it does. Keep going.", "Sam Levenson"),
    ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
    ("What you get by achieving your goals is not as important as what you become.", "Zig Ziglar"),
    ("The only limit to our realization of tomorrow is our doubts of today.", "Franklin D. Roosevelt"),
]


# Default habit suggestions
DEFAULT_HABITS = [
    "Exercise",
    "Read 30 min",
    "Drink 8 glasses water",
    "Meditate",
    "No social media before noon",
    "Journal",
    "Sleep by 10pm",
]


@dataclass
class TemplateResult:
    """Result of template rendering."""
    html: str
    variables_used: dict[str, str]
    template_name: str


def get_available_templates() -> dict[str, TemplateConfig]:
    """Get all available product templates."""
    templates = {}

    # Weekly Planner
    templates["weekly_planner"] = TemplateConfig(
        name="Weekly Planner",
        template_file="planner/weekly.html",
        description="Premium weekly planner with daily tasks, habit tracker, goals, and notes",
        variables={
            "title": "Main title on cover",
            "subtitle": "Subtitle on cover",
            "year": "Year displayed on cover",
            "primary_color": "Main accent color (hex)",
            "secondary_color": "Secondary/gradient color (hex)",
            "bg_light": "Light background color (hex)",
            "quote_text": "Motivational quote",
            "quote_author": "Quote author",
            "habit_1": "First habit to track",
            "habit_2": "Second habit to track",
            "habit_3": "Third habit to track",
            "habit_4": "Fourth habit to track",
            "habit_5": "Fifth habit to track",
            "habit_6": "Sixth habit to track",
            "habit_7": "Seventh habit to track",
        },
        defaults={
            "title": "Weekly Planner",
            "subtitle": "Plan Your Week, Achieve Your Goals",
            "year": "2026",
            "primary_color": "#A8D5E5",
            "secondary_color": "#D4EBF2",
            "bg_light": "#F0F8FF",
            "quote_text": QUOTES[0][0],
            "quote_author": QUOTES[0][1],
            "habit_1": DEFAULT_HABITS[0],
            "habit_2": DEFAULT_HABITS[1],
            "habit_3": DEFAULT_HABITS[2],
            "habit_4": DEFAULT_HABITS[3],
            "habit_5": DEFAULT_HABITS[4],
            "habit_6": DEFAULT_HABITS[5],
            "habit_7": DEFAULT_HABITS[6],
        },
        color_schemes=COLOR_SCHEMES,
    )

    return templates


def render_template(
    template_name: str,
    variables: Optional[dict[str, str]] = None,
    color_scheme: Optional[str] = None,
) -> TemplateResult:
    """Render a product template with custom variables.

    Args:
        template_name: Name of the template (e.g., "weekly_planner")
        variables: Custom variables to apply
        color_scheme: Name of a pre-defined color scheme

    Returns:
        TemplateResult with rendered HTML
    """
    templates = get_available_templates()

    if template_name not in templates:
        raise ValueError(f"Unknown template: {template_name}. Available: {list(templates.keys())}")

    config = templates[template_name]
    template_path = TEMPLATES_DIR / config.template_file

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    # Read template
    with open(template_path, 'r') as f:
        html = f.read()

    # Start with defaults
    final_vars = dict(config.defaults)

    # Apply color scheme if specified
    if color_scheme and color_scheme in COLOR_SCHEMES:
        final_vars.update(COLOR_SCHEMES[color_scheme])
        logger.info(f"Applied color scheme: {color_scheme}")

    # Override with custom variables
    if variables:
        final_vars.update(variables)

    # Replace all {{variable}} placeholders
    for var_name, var_value in final_vars.items():
        placeholder = "{{" + var_name + "}}"
        html = html.replace(placeholder, str(var_value))

    # Check for any remaining placeholders
    remaining = re.findall(r'\{\{(\w+)\}\}', html)
    if remaining:
        logger.warning(f"Unresolved template variables: {remaining}")
        # Fill with defaults or empty
        for var in remaining:
            html = html.replace("{{" + var + "}}", config.defaults.get(var, ""))

    logger.info(f"Rendered template '{template_name}' with {len(final_vars)} variables")

    return TemplateResult(
        html=html,
        variables_used=final_vars,
        template_name=template_name,
    )


def render_planner(
    title: str = "Weekly Planner",
    color_scheme: str = "pastel_blue",
    quote: Optional[tuple[str, str]] = None,
    habits: Optional[list[str]] = None,
    year: str = "2026",
) -> str:
    """Convenience function to render a weekly planner.

    Args:
        title: Planner title
        color_scheme: Color scheme name
        quote: (quote_text, quote_author) tuple
        habits: List of 7 habits to track
        year: Year for cover

    Returns:
        Rendered HTML string
    """
    variables = {
        "title": title,
        "year": year,
    }

    if quote:
        variables["quote_text"] = quote[0]
        variables["quote_author"] = quote[1]

    if habits:
        for i, habit in enumerate(habits[:7], 1):
            variables[f"habit_{i}"] = habit

    result = render_template("weekly_planner", variables, color_scheme)
    return result.html


# Quick test
if __name__ == "__main__":
    html = render_planner(
        title="My 2026 Planner",
        color_scheme="pastel_lavender",
        quote=("Dream big, start small, act now.", "Robin Sharma"),
        habits=["Morning workout", "Read 1 chapter", "No phone in bed", "Meal prep", "Gratitude journal", "Walk 10k steps", "Learn something new"],
    )
    print(f"Generated {len(html)} chars of HTML")
    with open("/tmp/test-planner.html", "w") as f:
        f.write(html)
    print("Saved to /tmp/test-planner.html")
