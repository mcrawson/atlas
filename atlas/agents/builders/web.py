"""WebBuilder - Creates web applications and landing pages.

This builder specializes in creating web products from landing pages to SPAs.
Output is modern, responsive HTML/CSS/JS ready for deployment.

Products:
- Landing pages
- Single Page Applications (SPAs)
- Dashboards
- Marketing websites
"""

import json
import logging
from typing import Optional

from atlas.agents.base import AgentOutput, AgentStatus
from .base import BaseBuilder, BuilderType, BuildOutput, BuildContext, OutputFormat
from .config import get_web_config, WebConfig

logger = logging.getLogger("atlas.builders.web")


class WebBuilder(BaseBuilder):
    """Builder for web applications and sites.

    Creates modern, responsive web products ready for deployment.
    Output is clean HTML/CSS/JS that works out of the box.
    """

    name = "web_builder"
    description = "Web application specialist"
    icon = "🌐"
    color = "#FF9800"

    builder_type = BuilderType.WEB
    supported_formats = [OutputFormat.HTML]

    def __init__(self, router=None, memory=None, **kwargs):
        self.router = router
        self.memory = memory
        self.options = kwargs
        self._status = AgentStatus.IDLE
        self._current_task = None
        self._callbacks = []
        self.config: WebConfig = get_web_config()

    def _get_builder_context(self) -> str:
        """Get WebBuilder-specific context."""
        return """You are the WebBuilder - expert in creating modern web applications.

YOUR SPECIALIZATION:
- Landing pages (marketing, product, startup)
- Single Page Applications (SPAs)
- Dashboards and admin panels
- Marketing and portfolio websites

OUTPUT REQUIREMENTS:
- Generate complete, functional HTML/CSS/JavaScript
- Use modern, responsive design
- Ensure mobile-first approach
- Include all interactive elements
- No external dependencies (all self-contained)

TECH STACK:
- HTML5 semantic markup
- Modern CSS (flexbox, grid, custom properties)
- Vanilla JavaScript (or minimal framework)
- Tailwind CSS utility classes (inline styles OK)

DESIGN PRINCIPLES:
1. RESPONSIVE: Works on all screen sizes
2. FAST: Minimal dependencies, optimized code
3. ACCESSIBLE: Proper ARIA labels, semantic HTML
4. PROFESSIONAL: Clean, modern aesthetics
5. FUNCTIONAL: All interactions work

OUTPUT FORMAT:
Generate a complete HTML file with embedded CSS and JS that:
- Works when opened directly in a browser
- Has all styles inline or in <style> tags
- Has all scripts inline or in <script> tags
- Is responsive and mobile-friendly
- Is ready to deploy as-is"""

    def get_system_prompt(self) -> str:
        """Get the full system prompt."""
        mission = """ATLAS is a product studio that combines human creativity with ethical AI
to build transformative solutions for our clients and the public.

Your job is to create SELLABLE web products. Every output must be something
professional and ready for deployment on Vercel, Netlify, or similar platforms."""

        return f"{mission}\n\n{self._get_builder_context()}"

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Process a build request."""
        self.status = AgentStatus.THINKING
        self._current_task = task

        try:
            build_context = BuildContext(
                project_name=context.get("name", "Web App") if context else "Web App",
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
            logger.error(f"[WebBuilder] Build failed: {e}")
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Build failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )
        finally:
            self._current_task = None

    async def build(self, context: BuildContext) -> BuildOutput:
        """Build a web application.

        Args:
            context: Build context with all necessary information

        Returns:
            BuildOutput with HTML/CSS/JS ready for deployment
        """
        logger.info(f"[WebBuilder] Building: {context.project_name}")

        # Determine web product type
        web_type = self._detect_web_type(context)
        web_config = self._get_web_settings(context, web_type)

        # Build the prompt
        prompt = self._build_generation_prompt(context, web_type, web_config)

        response, token_info = await self._generate_with_provider(
            prompt,
            temperature=0.7,
        )

        # Extract HTML
        html_content = self._extract_html(response)

        # Generate preview (same as content for web)
        preview_html = html_content

        return BuildOutput(
            content=html_content,
            format=OutputFormat.HTML,
            files={
                "index.html": html_content,
            },
            metadata={
                "web_type": web_type,
                "config": web_config,
                "tokens_used": token_info.get("total_tokens", 0),
            },
        )

    async def generate_preview(self, output: BuildOutput) -> str:
        """Generate a preview - for web, the content IS the preview."""
        return output.content

    def _detect_web_type(self, context: BuildContext) -> str:
        """Detect the type of web product."""
        description = context.project_description.lower()
        brief = context.business_brief

        if brief.get("product_type"):
            return brief["product_type"]

        if any(word in description for word in ["landing", "marketing", "product page"]):
            return "landing_page"
        if any(word in description for word in ["dashboard", "admin", "panel"]):
            return "dashboard"
        if any(word in description for word in ["spa", "application", "app"]):
            return "spa"
        if any(word in description for word in ["portfolio", "personal"]):
            return "portfolio"
        if any(word in description for word in ["blog", "news"]):
            return "blog"

        return "landing_page"

    def _get_web_settings(self, context: BuildContext, web_type: str) -> dict:
        """Get web-specific settings."""
        brief = context.business_brief

        settings = {
            "use_tailwind": self.config.use_tailwind,
            "framework": self.config.default_framework,
            "minify": self.config.minify_output,
        }

        # Type-specific settings
        if web_type == "dashboard":
            settings["layout"] = "sidebar"
            settings["theme"] = "professional"
        elif web_type == "landing_page":
            settings["layout"] = "single_page"
            settings["theme"] = "modern"
        elif web_type == "portfolio":
            settings["layout"] = "minimal"
            settings["theme"] = "creative"

        return settings

    def _build_generation_prompt(
        self,
        context: BuildContext,
        web_type: str,
        settings: dict,
    ) -> str:
        """Build the prompt for generating the web app."""
        brief = context.business_brief

        prompt_parts = [
            f"Create a complete {web_type} based on these specifications:",
            "",
            f"## Project: {context.project_name}",
            f"Description: {context.project_description}",
            "",
        ]

        # Add business brief context
        if brief:
            if brief.get("target_customer"):
                prompt_parts.append("## Target User:")
                prompt_parts.append(str(brief["target_customer"]))
                prompt_parts.append("")

            if brief.get("success_criteria"):
                prompt_parts.append("## Success Criteria:")
                for criterion in brief.get("success_criteria", []):
                    prompt_parts.append(f"- {criterion.get('criterion', criterion)}")
                prompt_parts.append("")

        # Type-specific requirements
        prompt_parts.extend(self._get_type_requirements(web_type))

        prompt_parts.extend([
            "",
            "## Technical Requirements:",
            "- Single HTML file with embedded CSS and JavaScript",
            "- Responsive design (mobile-first)",
            "- Modern CSS (flexbox, grid, custom properties)",
            "- Clean, semantic HTML5",
            "- All functionality working (no TODO comments)",
            "- Professional color scheme and typography",
            "- Smooth animations and transitions",
            "",
            "## Design Style:",
            "- Clean and modern aesthetic",
            "- Plenty of whitespace",
            "- Clear visual hierarchy",
            "- Consistent spacing (8px grid)",
            "- Professional but approachable",
            "",
            "Generate complete HTML code only. No explanations.",
            "The output must work when opened in a browser as-is.",
        ])

        return "\n".join(prompt_parts)

    def _get_type_requirements(self, web_type: str) -> list[str]:
        """Get type-specific requirements."""
        requirements = {
            "landing_page": [
                "## Landing Page Requirements:",
                "- Hero section with headline and CTA",
                "- Features/benefits section",
                "- Social proof (testimonials or logos)",
                "- Pricing or key information",
                "- Final CTA section",
                "- Footer with links",
                "- Sticky header navigation",
            ],
            "dashboard": [
                "## Dashboard Requirements:",
                "- Sidebar navigation",
                "- Header with user info",
                "- Summary cards/stats",
                "- Main content area with charts/tables",
                "- Responsive collapse for mobile",
                "- Interactive elements (buttons, dropdowns)",
            ],
            "spa": [
                "## SPA Requirements:",
                "- Client-side routing (hash-based)",
                "- Multiple views/pages",
                "- State management",
                "- Navigation menu",
                "- Loading states",
                "- Error handling",
            ],
            "portfolio": [
                "## Portfolio Requirements:",
                "- About/intro section",
                "- Work/projects gallery",
                "- Skills or services",
                "- Contact section",
                "- Smooth scroll navigation",
                "- Image hover effects",
            ],
            "blog": [
                "## Blog Requirements:",
                "- Post listing page",
                "- Post detail view",
                "- Categories/tags",
                "- Search functionality",
                "- Responsive typography",
                "- Reading time estimate",
            ],
        }

        return requirements.get(web_type, [
            "## General Web Requirements:",
            "- Clear navigation",
            "- Hero section",
            "- Main content area",
            "- Footer",
        ])

    def _extract_html(self, response: str) -> str:
        """Extract HTML from LLM response."""
        if "```html" in response:
            start = response.find("```html") + 7
            end = response.find("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            return response[start:end].strip()

        if "<!DOCTYPE" in response:
            start = response.find("<!DOCTYPE")
            return response[start:].strip()

        if "<html" in response:
            start = response.find("<html")
            return response[start:].strip()

        return response.strip()
