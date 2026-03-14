"""ATLAS Product Standards - Core philosophy for all agents.

This module provides the central quality standards that all ATLAS agents
must follow. Every agent should import and reference these standards.
"""

from pathlib import Path

# Load the philosophy document
_PHILOSOPHY_PATH = Path(__file__).parent / "PHILOSOPHY.md"
PHILOSOPHY = _PHILOSOPHY_PATH.read_text() if _PHILOSOPHY_PATH.exists() else ""

# Core principle - embed in all agent prompts
CORE_PRINCIPLE = """
ATLAS produces SELLABLE PRODUCTS. Not demos. Not scaffolds. Not MVPs.

Before completing ANY work, ask: "Would a customer pay $10+ for this right now?"
- NO → Not done. Keep working.
- MAYBE → Identify what's missing. Fix it.
- YES → Ship it.
"""

# Quality checklist for Oracle validation
SELLABILITY_CHECKLIST = {
    "completeness": [
        "Zero TODOs, FIXMEs, or placeholder comments",
        "Zero abbreviations like '<!-- Repeat for other days -->'",
        "Every feature mentioned is fully implemented",
        "All sample data is real and substantial",
    ],
    "polish": [
        "Professional visual design (not developer defaults)",
        "Consistent styling throughout",
        "Proper typography, spacing, colors",
        "Print-ready for physical products / Store-ready for apps",
    ],
    "functionality": [
        "Works completely out of the box",
        "No configuration required to use",
        "Handles edge cases gracefully",
        "Includes clear instructions if needed",
    ],
}

# Product type to integration mapping
# Keys match ProjectType enum values from atlas.projects.project_types
PRODUCT_INTEGRATIONS = {
    # Document types - all visual products use Canva
    "doc_book": {
        "design": ["canva"],
        "publish": ["amazon_kdp"],
        "needs_cover": True,
    },
    "doc_guide": {
        "design": ["canva"],
        "publish": ["etsy", "gumroad"],
        "needs_cover": True,
    },
    "doc_technical": {
        "design": ["canva"],
        "publish": ["github"],
        "needs_cover": False,
    },
    "doc_proposal": {
        "design": ["canva"],
        "publish": [],
        "needs_cover": True,
    },
    "doc_report": {
        "design": ["canva"],
        "publish": [],
        "needs_cover": True,
    },
    # Printables (planners, cards, worksheets, etc.)
    "printable": {
        "design": ["canva"],
        "publish": ["etsy", "gumroad"],
        "needs_cover": True,
    },
    "planner": {
        "design": ["canva"],
        "publish": ["etsy", "gumroad"],
        "needs_cover": True,
    },
    "physical_planner": {
        "design": ["canva"],
        "publish": ["etsy", "gumroad"],
        "needs_cover": True,
    },
    "physical_cards": {
        "design": ["canva"],
        "publish": ["etsy", "gumroad"],
        "needs_cover": False,
    },
    "physical_worksheet": {
        "design": ["canva"],
        "publish": ["etsy", "gumroad"],
        "needs_cover": False,
    },
    "physical_journal": {
        "design": ["canva"],
        "publish": ["etsy", "gumroad", "amazon_kdp"],
        "needs_cover": True,
    },
    # Mobile apps
    "mobile_ios": {
        "design": ["canva", "figma"],
        "publish": ["app_store"],
        "needs_icon": True,
    },
    "mobile_android": {
        "design": ["canva", "figma"],
        "publish": ["play_store"],
        "needs_icon": True,
    },
    "mobile_cross_platform": {
        "design": ["canva", "figma"],
        "publish": ["app_store", "play_store"],
        "needs_icon": True,
    },
    # Web
    "web_spa": {
        "design": ["figma"],
        "publish": ["vercel", "netlify"],
        "needs_icon": True,
    },
    "web_fullstack": {
        "design": ["figma"],
        "publish": ["vercel", "netlify"],
        "needs_icon": True,
    },
    "web_static": {
        "design": ["canva"],
        "publish": ["vercel", "netlify"],
        "needs_icon": True,
    },
    "web_landing": {
        "design": ["canva", "figma"],
        "publish": ["vercel", "netlify"],
        "needs_icon": True,
    },
    # APIs and libraries
    "api_rest": {
        "design": [],
        "publish": ["github", "vercel"],
        "needs_docs": True,
    },
    "api_graphql": {
        "design": [],
        "publish": ["github", "vercel"],
        "needs_docs": True,
    },
    "library_pypi": {
        "design": [],
        "publish": ["pypi", "github"],
        "needs_docs": True,
    },
    "library_npm": {
        "design": [],
        "publish": ["npm", "github"],
        "needs_docs": True,
    },
}

def get_integrations_for_product(product_type: str) -> dict:
    """Get recommended integrations for a product type."""
    return PRODUCT_INTEGRATIONS.get(product_type, {
        "design": [],
        "publish": [],
    })

def get_agent_philosophy(agent_name: str) -> str:
    """Get the philosophy section relevant to a specific agent."""
    agent_sections = {
        "sketch": """
### Your Role: Sketch (Planning)
- Define what "sellable" means for THIS specific product
- Identify which integrations/tools will be needed
- Set explicit quality criteria in the spec
- Include acceptance criteria that verify sellability
""",
        "mason": """
### Your Role: Mason/Tinker (Building)
- Build to SELLABLE quality, not just "working" quality
- Use real data, complete implementations
- Request design assets from Canva/Figma when needed
- NEVER abbreviate or shortcut repetitive content
- Every file must be production-ready
""",
        "tinker": """
### Your Role: Mason/Tinker (Building)
- Build to SELLABLE quality, not just "working" quality
- Use real data, complete implementations
- Request design assets from Canva/Figma when needed
- NEVER abbreviate or shortcut repetitive content
- Every file must be production-ready
""",
        "oracle": """
### Your Role: Oracle (Verification)
- Verify SELLABILITY, not just functionality
- Check against product type standards
- REJECT work that isn't ready to sell
- Recommend specific improvements needed
- Suggest integrations that would improve quality
""",
        "governor": """
### Your Role: Governor (Routing)
- Route to appropriate tools based on product needs
- Escalate to better models when quality requires it
- Connect to publishing platforms when product is ready
- Use Canva for visual products, Figma for UI/UX
""",
        "buzz": """
### Your Role: Buzz (Communication)
- Only announce genuinely sellable products
- Include marketplace-ready descriptions
- Generate listing copy that could go directly on Etsy/App Store
- Be honest about quality - don't hype incomplete work
""",
    }

    return CORE_PRINCIPLE + agent_sections.get(agent_name.lower(), "")


# Sellability validation prompts for Oracle
SELLABILITY_VALIDATION_PROMPT = """
You are validating whether this product is SELLABLE - ready to list on a marketplace for real money.

Check against these criteria:

## Completeness
- Are there ANY TODOs, FIXMEs, or placeholders? (FAIL if yes)
- Are there ANY abbreviations like "repeat for other days"? (FAIL if yes)
- Is every feature fully implemented? (FAIL if shortcuts taken)
- Is sample data real and substantial? (FAIL if dummy/lorem ipsum)

## Polish
- Does it look professional? (Not like a developer prototype)
- Is styling consistent throughout?
- Would it fit alongside premium products on Etsy/App Store?

## Functionality
- Does it work out of the box?
- Are there clear instructions?

## Integration Needs
- Does it need a professional cover/icon? (Recommend Canva)
- Does it need UI/UX polish? (Recommend Figma)
- Is it ready for a specific platform? (Recommend publishing integration)

RESPOND WITH:
1. SELLABLE: YES / NO / NEEDS_WORK
2. If not sellable, list specific issues
3. Recommended integrations to improve quality
4. Specific next steps to reach sellable status
"""
