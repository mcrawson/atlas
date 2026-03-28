"""Finisher - Polish, completeness verification, and shipping readiness.

The perfectionist. Takes Oracle-approved work and ensures it's truly ready
to ship. Verifies all deliverables are present, polishes rough edges,
and creates the final shipping checklist. Nothing ships until Finisher
confirms it's customer-ready.
"""

from typing import Optional
from .base import BaseAgent, AgentOutput, AgentStatus
from atlas.projects.project_types import (
    ProjectTypeDetector, ProjectType, ProjectCategory, PROJECT_CONFIGS
)


# Type-specific deliverables that MUST be present
REQUIRED_DELIVERABLES = {
    ProjectCategory.APP: {
        "code": {
            "name": "Application Code",
            "description": "Complete, working application source code",
            "required": True,
        },
        "icon": {
            "name": "App Icon",
            "description": "1024x1024 PNG icon (no alpha for iOS)",
            "required": True,
        },
        "screenshots": {
            "name": "Store Screenshots",
            "description": "Screenshots for app store listing",
            "required": True,
        },
        "store_description": {
            "name": "Store Description",
            "description": "App name, subtitle, and full description",
            "required": True,
        },
        "privacy_policy": {
            "name": "Privacy Policy",
            "description": "Privacy policy URL or content",
            "required": True,
        },
    },

    ProjectCategory.WEB: {
        "code": {
            "name": "Website Code",
            "description": "Complete HTML/CSS/JS or framework code",
            "required": True,
        },
        "responsive": {
            "name": "Responsive Design",
            "description": "Mobile-friendly layout verified",
            "required": True,
        },
        "seo": {
            "name": "SEO Setup",
            "description": "Meta tags, titles, descriptions",
            "required": True,
        },
        "deployment_config": {
            "name": "Deployment Config",
            "description": "Configuration for hosting platform",
            "required": True,
        },
    },

    ProjectCategory.DOCUMENT: {
        "content": {
            "name": "Document Content",
            "description": "Complete manuscript/document text",
            "required": True,
        },
        "cover": {
            "name": "Cover Design",
            "description": "Cover image/design specifications",
            "required": True,
        },
        "formatting": {
            "name": "Interior Formatting",
            "description": "Page layout, fonts, margins defined",
            "required": True,
        },
        "metadata": {
            "name": "Publishing Metadata",
            "description": "Title, author, description, categories",
            "required": True,
        },
    },

    ProjectCategory.PRINTABLE: {
        "templates": {
            "name": "Print Templates",
            "description": "Complete HTML/PDF templates for all pages",
            "required": True,
        },
        "dimensions": {
            "name": "Print Specifications",
            "description": "Page size, margins, bleed areas defined",
            "required": True,
        },
        "cover": {
            "name": "Cover Design",
            "description": "Cover template with proper dimensions",
            "required": True,
        },
        "print_instructions": {
            "name": "Print Instructions",
            "description": "Instructions for printing/production",
            "required": True,
        },
    },

    ProjectCategory.API: {
        "code": {
            "name": "API Code",
            "description": "Complete, working API implementation",
            "required": True,
        },
        "documentation": {
            "name": "API Documentation",
            "description": "Endpoint docs with examples",
            "required": True,
        },
        "authentication": {
            "name": "Authentication",
            "description": "Auth mechanism implemented and documented",
            "required": True,
        },
        "deployment_config": {
            "name": "Deployment Config",
            "description": "Docker/deployment configuration",
            "required": True,
        },
    },

    ProjectCategory.CLI: {
        "code": {
            "name": "CLI Code",
            "description": "Complete command-line tool code",
            "required": True,
        },
        "help_text": {
            "name": "Help Documentation",
            "description": "--help output and usage examples",
            "required": True,
        },
        "installation": {
            "name": "Installation Instructions",
            "description": "How to install (pip, npm, binary, etc.)",
            "required": True,
        },
    },

    ProjectCategory.LIBRARY: {
        "code": {
            "name": "Library Code",
            "description": "Complete, working library code",
            "required": True,
        },
        "documentation": {
            "name": "API Documentation",
            "description": "Public API docs with examples",
            "required": True,
        },
        "package_config": {
            "name": "Package Configuration",
            "description": "package.json/pyproject.toml configured",
            "required": True,
        },
        "readme": {
            "name": "README",
            "description": "README with usage examples",
            "required": True,
        },
    },
}


# Polish checklist items by category
POLISH_CHECKLIST = {
    ProjectCategory.APP: [
        "Error messages are user-friendly (no technical jargon)",
        "Loading states are present for async operations",
        "Empty states have helpful messaging",
        "All buttons and actions have clear labels",
        "Navigation is intuitive and consistent",
        "App handles edge cases gracefully",
        "Onboarding/first-run experience is smooth",
    ],

    ProjectCategory.WEB: [
        "404 page exists and is helpful",
        "Forms have validation with clear error messages",
        "Links open appropriately (new tab for external)",
        "Images have alt text",
        "Site works without JavaScript (graceful degradation)",
        "Contact/support information is visible",
        "Footer has essential links",
    ],

    ProjectCategory.DOCUMENT: [
        "Table of contents is accurate and linked",
        "Page numbers are correct",
        "Chapter headers are consistent",
        "No orphaned headings at page bottoms",
        "Images/figures are properly captioned",
        "Bibliography/references are formatted correctly",
        "Front matter (title, copyright) is complete",
    ],

    ProjectCategory.PRINTABLE: [
        "Page numbers don't appear on blank pages",
        "Bleed areas are properly defined",
        "Fonts are embedded or converted to outlines",
        "Color profiles are correct (CMYK for print)",
        "Binding margin is sufficient",
        "Cut marks are present if needed",
        "Proof copy instructions included",
    ],

    ProjectCategory.API: [
        "Error responses include helpful messages",
        "Rate limit headers are present",
        "CORS is configured correctly",
        "Health check endpoint exists",
        "Version is clearly indicated",
        "Deprecation notices for old endpoints",
        "Request/response examples are accurate",
    ],

    ProjectCategory.CLI: [
        "Version command works (--version)",
        "Help is comprehensive (--help)",
        "Exit codes are meaningful",
        "Progress indicators for long operations",
        "Colored output works and can be disabled",
        "Config file location is documented",
        "Error messages suggest fixes",
    ],

    ProjectCategory.LIBRARY: [
        "TypeScript types are exported (if applicable)",
        "Changelog is up to date",
        "Breaking changes are documented",
        "Examples are tested and working",
        "Dependencies are minimal and justified",
        "License file is present",
        "Contribution guidelines exist",
    ],
}


class FinisherAgent(BaseAgent):
    """Finisher: Polish and shipping readiness verification.

    The perfectionist. Takes Oracle-approved work and ensures it's truly
    customer-ready. Verifies deliverables, polishes rough edges, and
    creates the final shipping checklist.

    Output Format:
    - Deliverables Audit: What's present, what's missing
    - Polish Review: Refinements needed
    - Shipping Checklist: Final pre-launch checklist
    - Verdict: READY_TO_SHIP or NEEDS_POLISH
    """

    name = "finisher"
    description = "The perfectionist"
    icon = "✨"
    color = "#9B59B6"

    def get_system_prompt(self, project_category: ProjectCategory = None, project_config=None) -> str:
        """Get Finisher's system prompt, customized for project type."""

        # Get required deliverables for this category
        deliverables_text = ""
        if project_category and project_category in REQUIRED_DELIVERABLES:
            deliverables = REQUIRED_DELIVERABLES[project_category]
            deliverables_text = "\n## Required Deliverables\nThe following MUST be present:\n"
            for key, info in deliverables.items():
                required = "REQUIRED" if info["required"] else "Recommended"
                deliverables_text += f"- **{info['name']}** [{required}]: {info['description']}\n"

        # Get polish checklist for this category
        polish_text = ""
        if project_category and project_category in POLISH_CHECKLIST:
            items = POLISH_CHECKLIST[project_category]
            polish_text = "\n## Polish Checklist\nVerify these quality items:\n"
            for item in items:
                polish_text += f"- [ ] {item}\n"

        return f"""You are Finisher, the final quality gate in ATLAS before products ship.

PERSONALITY:
- Perfectionist with high standards
- Detail-oriented and thorough
- Customer-focused - you think like the end user
- Pragmatic - you know when "good enough" is actually good enough
- Constructive - you don't just criticize, you fix

YOUR ROLE:
You receive Oracle-approved work and ensure it's TRULY ready to ship. Oracle verified it works; you verify it's COMPLETE and POLISHED. Your job is to:
1. Audit all required deliverables - is everything present?
2. Review polish and quality - is it customer-ready?
3. Verify shipping requirements - can we actually launch this?
4. Create the final shipping checklist
5. Either approve for shipping OR specify exactly what needs finishing
{deliverables_text}
{polish_text}
OUTPUT FORMAT - Structure your response as:

## Deliverables Audit

### Present ✓
[List each deliverable that is complete with verification]

### Missing ✗
[List any missing deliverables - these BLOCK shipping]

### Incomplete ⚠
[List deliverables that exist but need work]

## Polish Review

### Quality Assessment
[Overall quality rating: Excellent / Good / Needs Work / Unacceptable]

### Polish Items Completed
[List polish items that are done]

### Polish Items Needed
[List specific polish work required, with actionable fixes]

## Shipping Readiness

### Pre-Launch Checklist
- [ ] All required deliverables present
- [ ] Code/content is complete
- [ ] No placeholder content remains
- [ ] Error handling is user-friendly
- [ ] Documentation is accurate
- [ ] Assets are production-ready
- [ ] Deployment configuration is correct

### Blockers
[List any issues that MUST be resolved before shipping]

### Recommendations
[Nice-to-haves that could be done post-launch]

## Verdict

**[READY_TO_SHIP / NEEDS_POLISH]**

[If NEEDS_POLISH: Provide specific, actionable list of what must be done]
[If READY_TO_SHIP: Confirm the product is customer-ready]

---

GUIDELINES:
- Be thorough but practical - don't demand perfection if good is sufficient
- Focus on customer experience - would YOU buy/use this?
- For NEEDS_POLISH, be specific: "Add error message to login form" not "improve error handling"
- Missing REQUIRED deliverables = automatic NEEDS_POLISH
- Placeholder content (lorem ipsum, TODO, etc.) = automatic NEEDS_POLISH
- Your job is to ensure customers get a quality product
- If you approve (READY_TO_SHIP), you're saying "I would sell this to a customer"
"""

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Process Oracle-approved work and verify shipping readiness.

        Args:
            task: The original task description
            context: Project context including mason output
            previous_output: Oracle's approval output

        Returns:
            AgentOutput with shipping readiness verdict
        """
        self.status = AgentStatus.THINKING
        self._current_task = task

        try:
            # Detect project type
            project_type = None
            project_category = None
            project_config = None

            detector = ProjectTypeDetector()

            if previous_output and previous_output.artifacts:
                type_str = previous_output.artifacts.get("project_type")
                if type_str:
                    try:
                        project_type = ProjectType(type_str)
                        project_config = detector.get_config(project_type)
                        project_category = project_config.category if project_config else None
                    except (ValueError, KeyError):
                        pass

            if not project_type:
                combined_text = task
                if context:
                    if context.get("description"):
                        combined_text += " " + context["description"]
                project_type, project_category, _ = detector.detect(combined_text)
                project_config = detector.get_config(project_type)

            print(f"[Finisher] Verifying shipping readiness for {project_type.value if project_type else 'unknown'}")

            # Build prompt
            prompt = f"Verify shipping readiness for the following product:\n\n## Task\n{task}\n"

            # Add Mason's output (what was built)
            if context and context.get("mason_output"):
                prompt += f"\n## What Was Built (Mason's Output)\n{context['mason_output']}\n"

            # Add Oracle's verification
            if previous_output:
                prompt += f"\n## Oracle's Verification\n{previous_output.content}\n"

            # Add deliverables from Mason if present
            if previous_output and previous_output.artifacts:
                deliverables = previous_output.artifacts.get("deliverables_completed", {})
                if deliverables:
                    prompt += "\n## Deliverables Claimed by Mason\n"
                    for key, status in deliverables.items():
                        checkmark = "✓" if status else "✗"
                        prompt += f"- [{checkmark}] {key}\n"

            # Add any files/artifacts
            if context and context.get("files"):
                prompt += "\n## Files Generated\n"
                for filename, content in context["files"].items():
                    preview = content[:500] + "..." if len(content) > 500 else content
                    prompt += f"\n### {filename}\n```\n{preview}\n```\n"

            prompt += "\n\nVerify this product is complete, polished, and ready to ship to customers."

            # Get system prompt
            system_prompt = self.get_system_prompt(project_category, project_config)

            # Route to AI provider
            self.status = AgentStatus.WORKING
            routing = self.router.route(prompt, preferred_provider="claude")

            # Generate response
            from atlas.routing.providers import get_provider
            provider = get_provider(routing["provider"], self.router)

            response = await provider.generate(
                prompt,
                system_prompt=system_prompt,
            )

            # Parse verdict
            verdict = "NEEDS_POLISH"
            if "READY_TO_SHIP" in response.upper():
                verdict = "READY_TO_SHIP"

            # Log completion
            self.router.log_completion(routing["provider"], "verification")

            self.status = AgentStatus.COMPLETED

            return AgentOutput(
                content=response,
                artifacts={
                    "verdict": verdict,
                    "project_type": project_type.value if project_type else None,
                    "shipping_ready": verdict == "READY_TO_SHIP",
                },
                next_agent="launch" if verdict == "READY_TO_SHIP" else "mason",
                metadata={
                    "provider": routing["provider"],
                    "project_type": project_type.value if project_type else "unknown",
                    "verdict": verdict,
                },
            )

        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Finisher verification failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )
