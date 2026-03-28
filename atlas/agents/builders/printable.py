"""PrintableBuilder - Creates printable products like planners, cards, worksheets.

This builder specializes in creating PDF-ready products for marketplaces like Etsy.
Output is polished, print-ready HTML/CSS that converts cleanly to PDF.

Products:
- Planners (weekly, monthly, daily)
- Cards (recipe, flash, greeting)
- Worksheets (educational, organizational)
- Journals and trackers
"""

import json
import logging
from typing import Optional

from atlas.agents.base import AgentOutput, AgentStatus
from .base import BaseBuilder, BuilderType, BuildOutput, BuildContext, OutputFormat
from .config import get_printable_config, PrintableConfig

logger = logging.getLogger("atlas.builders.printable")


# Page size dimensions (in CSS units)
PAGE_SIZES = {
    "letter": {"width": "8.5in", "height": "11in"},
    "a4": {"width": "210mm", "height": "297mm"},
    "a5": {"width": "148mm", "height": "210mm"},
    "half_letter": {"width": "5.5in", "height": "8.5in"},
}


class PrintableBuilder(BaseBuilder):
    """Builder for printable products (planners, cards, worksheets).

    Creates polished, print-ready output that customers would pay for.
    Output is HTML/CSS designed for PDF conversion.
    """

    name = "printable_builder"
    description = "Printable product specialist"
    icon = "📄"
    color = "#4CAF50"

    builder_type = BuilderType.PRINTABLE
    supported_formats = [OutputFormat.PDF, OutputFormat.HTML]

    def __init__(self, router=None, memory=None, **kwargs):
        # Don't call super().__init__ with config validation for now
        self.router = router
        self.memory = memory
        self.options = kwargs
        self._status = AgentStatus.IDLE
        self._current_task = None
        self._callbacks = []
        self.config: PrintableConfig = get_printable_config()

    def _get_builder_context(self) -> str:
        """Get PrintableBuilder-specific context."""
        return """You are the PrintableBuilder - expert in creating print-ready products.

YOUR SPECIALIZATION:
- Planners (weekly, monthly, daily, habit trackers)
- Cards (recipe cards, flash cards, greeting cards)
- Worksheets (educational, organizational, tracking)
- Journals and logs

OUTPUT REQUIREMENTS:
- Generate complete, print-ready HTML/CSS
- Design for PDF conversion (use print media queries)
- Include all pages/cards as separate sections
- Use professional typography and spacing
- Consider print margins and bleed areas

DESIGN PRINCIPLES:
1. CLEAN: Minimal clutter, purposeful whitespace
2. FUNCTIONAL: Every element serves a purpose
3. PROFESSIONAL: Would look good printed and sold
4. CONSISTENT: Unified style across all pages
5. PRINT-READY: Works when printed, not just on screen

OUTPUT FORMAT:
Generate a complete HTML document with embedded CSS that:
- Uses @page rules for print layout
- Has page-break controls between sections
- Uses appropriate fonts (web-safe or embedded)
- Includes all content, not placeholders
- Is ready to convert to PDF as-is"""

    def get_system_prompt(self) -> str:
        """Get the full system prompt."""
        mission = """ATLAS is a product studio that combines human creativity with ethical AI
to build transformative solutions for our clients and the public.

Your job is to create SELLABLE printable products. Every output must be something
a customer would pay for on Etsy or similar marketplaces."""

        return f"{mission}\n\n{self._get_builder_context()}"

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Process a build request.

        This is the BaseAgent interface. It wraps build() for compatibility.
        """
        self.status = AgentStatus.THINKING
        self._current_task = task

        try:
            # Build context from task and context dict
            build_context = BuildContext(
                project_name=context.get("name", "Printable Product") if context else "Printable Product",
                project_description=task,
                business_brief=context.get("business_brief", {}) if context else {},
                mockup=context.get("mockup") if context else None,
                plan=context.get("plan") if context else None,
            )

            self.status = AgentStatus.WORKING
            output = await self.build(build_context)

            self.status = AgentStatus.COMPLETED

            return AgentOutput(
                content=output.content,
                artifacts={
                    "build_output": output.to_dict(),
                    "files": output.files,
                    "format": output.format.value,
                },
                metadata={
                    "agent": self.name,
                    "builder_type": self.builder_type.value,
                },
            )

        except Exception as e:
            logger.error(f"[PrintableBuilder] Build failed: {e}")
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Build failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )
        finally:
            self._current_task = None

    async def build(self, context: BuildContext) -> BuildOutput:
        """Build a printable product.

        Args:
            context: Build context with all necessary information

        Returns:
            BuildOutput with HTML/CSS ready for PDF conversion
        """
        logger.info(f"[PrintableBuilder] Building: {context.project_name}")

        # Determine product subtype from brief or description
        product_type = self._detect_product_type(context)
        page_config = self._get_page_config(context, product_type)

        # Build the prompt for the LLM
        prompt = self._build_generation_prompt(context, product_type, page_config)

        # Generate the printable content
        response, token_info = await self._generate_with_provider(
            prompt,
            temperature=0.7,
        )

        # Parse and validate the response
        html_content = self._extract_html(response)

        # Wrap in proper document structure if needed
        if not html_content.strip().startswith("<!DOCTYPE"):
            html_content = self._wrap_html(html_content, context, page_config)

        # Generate preview
        preview_html = self._generate_preview_html(html_content, context)

        return BuildOutput(
            content=html_content,
            format=OutputFormat.HTML,
            files={
                "index.html": html_content,
                "preview.html": preview_html,
            },
            preview_url=None,  # Set by preview server
            metadata={
                "product_type": product_type,
                "page_config": page_config,
                "tokens_used": token_info.get("total_tokens", 0),
            },
        )

    async def generate_preview(self, output: BuildOutput) -> str:
        """Generate a preview for the printable.

        Returns HTML that can be displayed in an iframe.
        """
        if "preview.html" in output.files:
            return output.files["preview.html"]
        return output.content

    def _detect_product_type(self, context: BuildContext) -> str:
        """Detect the specific type of printable."""
        description = context.project_description.lower()
        brief = context.business_brief

        # Check business brief first
        if brief.get("product_type"):
            return brief["product_type"]

        # Detect from description
        if any(word in description for word in ["planner", "schedule", "calendar"]):
            if "weekly" in description:
                return "weekly_planner"
            elif "monthly" in description:
                return "monthly_planner"
            elif "daily" in description:
                return "daily_planner"
            return "planner"

        if any(word in description for word in ["recipe", "card", "flash"]):
            if "recipe" in description:
                return "recipe_cards"
            elif "flash" in description:
                return "flash_cards"
            return "cards"

        if any(word in description for word in ["worksheet", "exercise", "practice"]):
            return "worksheet"

        if any(word in description for word in ["journal", "diary", "log"]):
            return "journal"

        if any(word in description for word in ["tracker", "habit", "goal"]):
            return "tracker"

        return "printable"

    def _get_page_config(self, context: BuildContext, product_type: str) -> dict:
        """Get page configuration for the product type."""
        # Use config defaults
        size = self.config.default_page_size
        orientation = self.config.default_orientation

        # Override based on product type
        if product_type in ["recipe_cards", "flash_cards"]:
            size = "half_letter"

        if product_type == "weekly_planner":
            orientation = "landscape"

        # Check business brief for preferences
        brief = context.business_brief
        if brief.get("preferences", {}).get("page_size"):
            size = brief["preferences"]["page_size"]
        if brief.get("preferences", {}).get("orientation"):
            orientation = brief["preferences"]["orientation"]

        page_dims = PAGE_SIZES.get(size, PAGE_SIZES["letter"])

        return {
            "size": size,
            "orientation": orientation,
            "width": page_dims["width"],
            "height": page_dims["height"],
            "margins": "0.5in",
            "font_family": self.config.default_font_family,
            "font_size": self.config.default_font_size,
            "accent_color": self.config.accent_color,
        }

    def _build_generation_prompt(
        self,
        context: BuildContext,
        product_type: str,
        page_config: dict,
    ) -> str:
        """Build the prompt for generating the printable."""
        brief = context.business_brief

        prompt_parts = [
            f"Create a {product_type} based on the following specifications:",
            "",
            f"## Product: {context.project_name}",
            f"Description: {context.project_description}",
            "",
        ]

        # Add business brief details
        if brief:
            if brief.get("target_customer"):
                prompt_parts.append(f"## Target Customer")
                prompt_parts.append(str(brief["target_customer"]))
                prompt_parts.append("")

            if brief.get("success_criteria"):
                prompt_parts.append("## Success Criteria")
                for criterion in brief.get("success_criteria", []):
                    prompt_parts.append(f"- {criterion.get('criterion', criterion)}")
                prompt_parts.append("")

        # Page configuration
        prompt_parts.extend([
            "## Page Configuration",
            f"- Size: {page_config['size']} ({page_config['width']} x {page_config['height']})",
            f"- Orientation: {page_config['orientation']}",
            f"- Margins: {page_config['margins']}",
            f"- Primary Font: {page_config['font_family']}",
            f"- Accent Color: {page_config['accent_color']}",
            "",
        ])

        # Product-specific instructions
        prompt_parts.extend(self._get_product_instructions(product_type))

        prompt_parts.extend([
            "",
            "## Output Requirements",
            "Generate a COMPLETE HTML document with embedded CSS that:",
            "1. Is ready to print or convert to PDF",
            "2. Uses @page CSS rules for proper print layout",
            "3. Has page-break-after between logical sections",
            "4. Uses the specified fonts and colors",
            "5. Includes ALL content - no placeholders like [Add content here]",
            "6. Is professionally designed and sellable",
            "",
            "Output the complete HTML code only, no explanations.",
        ])

        return "\n".join(prompt_parts)

    def _get_product_instructions(self, product_type: str) -> list[str]:
        """Get product-specific generation instructions."""
        instructions = {
            "weekly_planner": [
                "## Weekly Planner Requirements",
                "- Create pages for 4-6 weeks",
                "- Each week should have:",
                "  - Week number and date range header",
                "  - Days Monday through Sunday",
                "  - Space for tasks/goals for each day",
                "  - Weekly notes or reflection section",
                "- Include a cover page with title",
            ],
            "monthly_planner": [
                "## Monthly Planner Requirements",
                "- Create pages for 12 months",
                "- Each month should have:",
                "  - Month name and year header",
                "  - Calendar grid with day numbers",
                "  - Space for notes or goals",
                "- Include a year-at-a-glance page",
                "- Include a cover page",
            ],
            "daily_planner": [
                "## Daily Planner Requirements",
                "- Create a daily page template",
                "- Include sections for:",
                "  - Date header",
                "  - Schedule/timeline (hourly or blocks)",
                "  - Priority tasks (top 3)",
                "  - To-do list",
                "  - Notes section",
                "- Create 7 sample pages (one week)",
            ],
            "recipe_cards": [
                "## Recipe Card Requirements",
                "- Create 6-8 recipe cards",
                "- Each card should have:",
                "  - Recipe title",
                "  - Prep time, cook time, servings",
                "  - Ingredients list",
                "  - Step-by-step instructions",
                "  - Space for notes",
                "- Design for 4x6 or 5x7 inch cards",
                "- Two cards per page for printing",
            ],
            "flash_cards": [
                "## Flash Card Requirements",
                "- Create 20-30 flash cards",
                "- Each card has front (question/term) and back (answer/definition)",
                "- Design for 3x5 inch cards",
                "- Multiple cards per page with cut lines",
                "- Include a cover page with instructions",
            ],
            "worksheet": [
                "## Worksheet Requirements",
                "- Create 5-10 worksheet pages",
                "- Include clear instructions at the top",
                "- Leave appropriate space for answers",
                "- Include answer key as final pages",
                "- Use consistent formatting throughout",
            ],
            "journal": [
                "## Journal Requirements",
                "- Create 30-50 journal pages",
                "- Include dated entry sections",
                "- Add optional prompts or quotes",
                "- Include a cover page",
                "- Add index or contents page",
            ],
            "tracker": [
                "## Tracker Requirements",
                "- Create tracking pages for 30 days",
                "- Include clear tracking grid/chart",
                "- Add space for goals and notes",
                "- Include instructions page",
                "- Add summary/review page",
            ],
        }

        return instructions.get(product_type, [
            "## General Printable Requirements",
            "- Create a professional, print-ready document",
            "- Include a cover page",
            "- Use consistent styling throughout",
            "- Make it functional and attractive",
        ])

    def _extract_html(self, response: str) -> str:
        """Extract HTML from LLM response."""
        # Check for code blocks
        if "```html" in response:
            start = response.find("```html") + 7
            end = response.find("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            return response[start:end].strip()

        # Check for DOCTYPE
        if "<!DOCTYPE" in response:
            start = response.find("<!DOCTYPE")
            return response[start:].strip()

        # Check for html tag
        if "<html" in response:
            start = response.find("<html")
            return response[start:].strip()

        # Return as-is, will be wrapped
        return response.strip()

    def _wrap_html(self, content: str, context: BuildContext, page_config: dict) -> str:
        """Wrap content in a complete HTML document."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{context.project_name}</title>
    <style>
        @page {{
            size: {page_config['width']} {page_config['height']};
            margin: {page_config['margins']};
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: {page_config['font_family']}, -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: {page_config['font_size']}pt;
            line-height: 1.5;
            color: #333;
        }}

        .page {{
            width: {page_config['width']};
            min-height: {page_config['height']};
            padding: {page_config['margins']};
            page-break-after: always;
        }}

        .page:last-child {{
            page-break-after: auto;
        }}

        h1, h2, h3 {{
            color: {page_config['accent_color']};
        }}

        @media print {{
            body {{
                print-color-adjust: exact;
                -webkit-print-color-adjust: exact;
            }}
        }}
    </style>
</head>
<body>
{content}
</body>
</html>"""

    def _generate_preview_html(self, html_content: str, context: BuildContext) -> str:
        """Generate preview HTML with navigation controls."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preview: {context.project_name}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        .preview-header {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .preview-title {{
            font-size: 18px;
            font-weight: 600;
        }}
        .preview-actions button {{
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-left: 10px;
        }}
        .btn-print {{
            background: #1976d2;
            color: white;
        }}
        .preview-frame {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            overflow: auto;
            max-height: 80vh;
        }}
        .preview-content {{
            transform-origin: top left;
            transform: scale(0.8);
            width: 125%;
        }}
    </style>
</head>
<body>
    <div class="preview-header">
        <span class="preview-title">{context.project_name}</span>
        <div class="preview-actions">
            <button class="btn-print" onclick="window.frames['content'].print()">Print / Save PDF</button>
        </div>
    </div>
    <div class="preview-frame">
        <iframe name="content" srcdoc="{html_content.replace('"', '&quot;')}"
                style="width: 100%; height: 800px; border: none;"></iframe>
    </div>
</body>
</html>"""
