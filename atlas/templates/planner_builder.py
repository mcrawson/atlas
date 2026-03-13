"""Planner Builder - Uses templates + LLM customization for high-quality output.

This module handles the generation of printable planners by:
1. Having the LLM analyze the request and select customizations
2. Applying those customizations to professional templates
3. Guaranteeing sellable-quality output every time
"""

import json
import logging
import re
from typing import Optional

from .engine import render_planner, COLOR_SCHEMES, QUOTES, DEFAULT_HABITS

logger = logging.getLogger("atlas.templates.planner_builder")


# Prompt for LLM to customize the planner
CUSTOMIZATION_PROMPT = """You are customizing a premium weekly planner based on the user's request.

USER REQUEST:
{request}

Available color schemes:
- pastel_pink: Soft pink/rose tones
- pastel_blue: Calm blue tones
- pastel_green: Fresh green tones
- pastel_lavender: Elegant purple tones
- pastel_peach: Warm peach tones
- minimalist: Clean black/gray
- ocean: Deep blue tones
- forest: Natural green tones
- sunset: Warm orange tones
- midnight: Deep navy tones

Respond with a JSON object containing your customization choices:

```json
{{
    "title": "The planner title",
    "subtitle": "A motivating subtitle",
    "color_scheme": "one of the scheme names above",
    "quote_text": "An inspiring quote that fits the theme",
    "quote_author": "The quote's author",
    "habits": [
        "Habit 1 to track",
        "Habit 2 to track",
        "Habit 3 to track",
        "Habit 4 to track",
        "Habit 5 to track",
        "Habit 6 to track",
        "Habit 7 to track"
    ]
}}
```

Make the customizations match the user's request. If they mention:
- A specific theme/aesthetic, choose matching colors
- Specific goals, suggest relevant habits
- A particular audience, tailor the title/subtitle

Return ONLY the JSON, no other text.
"""


def extract_customization_json(llm_response: str) -> dict:
    """Extract JSON customization from LLM response."""
    # Try to find JSON in code block
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON
    json_match = re.search(r'\{[^{}]*"title"[^{}]*\}', llm_response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Return defaults
    logger.warning("Could not extract customization JSON, using defaults")
    return {}


async def build_planner_with_llm(
    request: str,
    llm_provider,
    year: str = "2026",
) -> tuple[str, dict]:
    """Build a planner using LLM for customization and templates for structure.

    Args:
        request: User's description of what they want
        llm_provider: The LLM provider to use for customization
        year: Year for the planner cover

    Returns:
        Tuple of (html_content, customization_used)
    """
    # Get LLM to customize
    prompt = CUSTOMIZATION_PROMPT.format(request=request)

    try:
        response = await llm_provider.generate(
            prompt,
            system_prompt="You are a planner design expert. Respond only with JSON.",
            temperature=0.7,
        )
        customization = extract_customization_json(response)
    except Exception as e:
        logger.warning(f"LLM customization failed: {e}, using defaults")
        customization = {}

    # Apply customization with fallbacks
    title = customization.get("title", "Weekly Planner")
    color_scheme = customization.get("color_scheme", "pastel_blue")
    habits = customization.get("habits", DEFAULT_HABITS)
    quote_text = customization.get("quote_text", QUOTES[0][0])
    quote_author = customization.get("quote_author", QUOTES[0][1])

    # Validate color scheme
    if color_scheme not in COLOR_SCHEMES:
        logger.warning(f"Unknown color scheme '{color_scheme}', using pastel_blue")
        color_scheme = "pastel_blue"

    # Ensure we have 7 habits
    while len(habits) < 7:
        habits.append(DEFAULT_HABITS[len(habits) % len(DEFAULT_HABITS)])

    # Generate using template
    html = render_planner(
        title=title,
        color_scheme=color_scheme,
        quote=(quote_text, quote_author),
        habits=habits[:7],
        year=year,
    )

    final_customization = {
        "title": title,
        "subtitle": customization.get("subtitle", "Plan Your Week, Achieve Your Goals"),
        "color_scheme": color_scheme,
        "quote_text": quote_text,
        "quote_author": quote_author,
        "habits": habits[:7],
        "year": year,
    }

    logger.info(f"Built planner: {title} with {color_scheme} scheme")

    return html, final_customization


def build_planner_direct(
    title: str = "Weekly Planner",
    color_scheme: str = "pastel_blue",
    quote: Optional[tuple[str, str]] = None,
    habits: Optional[list[str]] = None,
    year: str = "2026",
) -> str:
    """Build a planner directly without LLM (for testing or preset configs).

    Args:
        title: Planner title
        color_scheme: Color scheme name
        quote: (text, author) tuple
        habits: List of habits to track
        year: Year for cover

    Returns:
        HTML string
    """
    if quote is None:
        quote = QUOTES[0]
    if habits is None:
        habits = DEFAULT_HABITS

    return render_planner(
        title=title,
        color_scheme=color_scheme,
        quote=quote,
        habits=habits,
        year=year,
    )


# Product type detection
def is_planner_request(text: str) -> bool:
    """Check if a request is specifically for a planner/journal product.

    Be specific - don't catch generic 'printable' products like recipe cards.
    Only match when it's clearly a planner, journal, or tracker.
    """
    # Must contain one of these specific planner terms
    planner_keywords = [
        "weekly planner", "daily planner", "monthly planner",
        "planner", "journal", "bullet journal",
        "habit tracker", "goal tracker", "mood tracker",
        "schedule planner", "organizer planner",
    ]

    # Exclude if it contains these (not a planner)
    exclude_keywords = [
        "recipe", "coloring", "flashcard", "worksheet",
        "invitation", "card set", "cards",
    ]

    text_lower = text.lower()

    # Check exclusions first
    if any(kw in text_lower for kw in exclude_keywords):
        return False

    # Then check for planner keywords
    return any(kw in text_lower for kw in planner_keywords)
