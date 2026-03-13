"""Tinker - Implementation and building.

The maker of things. Takes blueprints and brings them to life,
one component at a time. Writes clean, maintainable code and
won't stop tweaking until it works just right.
"""

from typing import Optional
from .base import BaseAgent, AgentOutput, AgentStatus
from atlas.knowledge import get_knowledge_augmenter
from atlas.research import get_research_augmenter
from atlas.projects.project_types import (
    ProjectTypeDetector, ProjectType, ProjectCategory, PROJECT_CONFIGS
)
from atlas.standards import get_agent_philosophy, CORE_PRINCIPLE


# Type-specific deliverables that Tinker must produce
TYPE_DELIVERABLES = {
    ProjectCategory.APP: """
## Required Deliverables for App

### App Assets Checklist
- [ ] App Icon (provide specs: 1024x1024 for App Store, 512x512 for Play Store)
- [ ] Splash Screen design specs
- [ ] App Store Screenshots list (what screens to capture)
- [ ] App Store Description (short and long)
- [ ] Keywords/Tags for discoverability

### Code Deliverables
- Complete source code with all screens
- Navigation setup
- State management
- API integration (if applicable)
- Local storage setup (if applicable)

### External Tool Tasks
> These need to be done in external tools:
- **Canva/Figma**: Create app icon from specs above
- **Canva/Figma**: Create screenshot mockups for store listing
""",

    ProjectCategory.WEB: """
## Required Deliverables for Website

### Code Deliverables
- Complete source code
- Responsive design (mobile, tablet, desktop)
- SEO meta tags
- Favicon and social share images specs
- Analytics integration placeholder

### Deployment Config
- `vercel.json` or `netlify.toml` (if applicable)
- Environment variables list
- Build commands

### External Tool Tasks
> These need to be done in external tools:
- **Canva**: Create social share image (1200x630)
- **Canva**: Create favicon source (512x512)
""",

    ProjectCategory.DOCUMENT: """
## Required Deliverables for Document/Book

### Content Structure
- Complete chapter/section outline with word count targets
- Sample content for first chapter/section
- Table of contents

### Design Specs
- Page size and margins
- Font recommendations
- Chapter header style

### Cover Requirements
- Title and subtitle
- Author name
- Cover dimensions (6x9 for print, specific for ebook)
- Back cover content (blurb, author bio)
- Spine text (if applicable)

### External Tool Tasks
> These need to be done in external tools:
- **Canva**: Create book cover from specs above
- **Google Docs**: Write full content following outline
- **Canva**: Create interior page template (if custom design needed)

### Publishing Checklist
- [ ] ISBN (if needed)
- [ ] Copyright page content
- [ ] Amazon categories to target
- [ ] Keywords for discoverability
""",

    ProjectCategory.API: """
## Required Deliverables for API

### Code Deliverables
- Complete API implementation
- Database schema/migrations
- Authentication setup
- Input validation
- Error handling

### Documentation
- OpenAPI/Swagger spec
- Example requests/responses
- Authentication guide

### Deployment Config
- Dockerfile
- Environment variables list
- Database connection setup
""",

    ProjectCategory.CLI: """
## Required Deliverables for CLI Tool

### Code Deliverables
- Complete CLI implementation
- Help text for all commands
- Configuration file handling
- Error messages

### Documentation
- README with usage examples
- Man page content (if applicable)

### Distribution
- Package.json / pyproject.toml / go.mod
- Installation instructions
- Release process
""",

    ProjectCategory.LIBRARY: """
## Required Deliverables for Library

### Code Deliverables
- Complete library implementation
- Type definitions
- Unit tests

### Documentation
- API documentation
- Usage examples
- Migration guide (if replacing something)

### Publishing Config
- Package manifest (package.json, pyproject.toml, etc.)
- Build configuration
- CI/CD for releases
""",

    ProjectCategory.SCRIPT: """
## Required Deliverables for Script

### Code Deliverables
- Complete script
- Configuration file (if needed)
- Logging setup

### Documentation
- Usage instructions
- Input/output format
- Scheduling instructions (if applicable)
""",

    ProjectCategory.PHYSICAL: """
## Required Deliverables for Physical Product (Planner/Journal/Printable)

### CRITICAL: Generate ACTUAL Printable HTML/CSS Templates

You MUST generate complete, print-ready HTML files that can be converted to PDF.
Do NOT just describe layouts - CREATE the actual pages!

### Print Specifications
- Page size: Letter (8.5" x 11") or A4 (210mm x 297mm) or A5 (148mm x 210mm)
- Margins: 0.5 inch minimum on all sides (0.75 inch on binding edge)
- Bleed: None needed for home printing
- Colors: Use CSS that prints well (avoid very light colors)

### Required HTML Template Structure

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Planner Page</title>
    <style>
        @page {
            size: letter;
            margin: 0.5in;
        }
        @media print {
            .page { page-break-after: always; }
            .no-print { display: none; }
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.4;
            color: #333;
        }
        .page {
            width: 7.5in;
            min-height: 10in;
            padding: 0.25in;
            box-sizing: border-box;
        }
        /* Add specific styles for each section */
    </style>
</head>
<body>
    <div class="page">
        <!-- Actual page content here -->
    </div>
</body>
</html>
```

### Deliverables Checklist
- [ ] Complete HTML file(s) for each page type
- [ ] Print-optimized CSS with @page and @media print rules
- [ ] All sections filled with actual content (not placeholders like [Date])
- [ ] Lines, checkboxes, and writing areas properly styled
- [ ] Cover page design (if applicable)
- [ ] Instructions for printing (page range, duplex settings)

### File Structure
```
planner/
├── index.html          # Main file with all pages
├── cover.html          # Cover page
├── daily-page.html     # Daily planner template
├── weekly-page.html    # Weekly overview template
├── goals.html          # Goal tracking pages
├── notes.html          # Notes pages
├── styles.css          # Shared print styles
└── README.md           # Printing instructions
```

### External Tool Tasks
> After HTML generation:
- **Browser**: Open HTML and use Print > Save as PDF
- **Print Service**: Upload PDF to Amazon KDP, Lulu, or local print shop
""",
}


class MasonAgent(BaseAgent):
    """Tinker: Master builder and implementer.

    The maker of things. Takes Sketch's blueprints and brings them
    to life, one component at a time. Writes clean, maintainable
    code and won't stop tweaking until it works just right.

    Output Format:
    - Acknowledging Plan: What was received from Sketch
    - Implementation: The actual code/solution
    - Files Modified: List of changes made
    - Notes for Oracle: Testing considerations
    """

    name = "tinker"
    description = "The maker of things"
    icon = "🛠️"
    color = "#E67E22"

    def get_system_prompt(self, project_category: ProjectCategory = None, project_config=None) -> str:
        """Get Tinker's system prompt - focused and bulletproof."""

        # Get stack guidance from config
        stack_guidance = ""
        if project_config:
            stack_guidance = f"""
TECH STACK (use this): {', '.join(project_config.suggested_stack[:2])}
Build approach: {project_config.build_approach}"""

        # Get agent-specific philosophy
        philosophy = get_agent_philosophy("tinker")

        return f"""You are Tinker, a master craftsman who builds SELLABLE, PRODUCTION-READY products.

{philosophy}

Your output must be ready to sell/publish immediately - no placeholders, no TODOs, no shortcuts.
If it's a planner, every page must be complete with real content.
If it's an API, every endpoint must work with real logic.
If it's an app, it must be fully functional.
If visual polish is needed, request Canva/Figma integration.

{stack_guidance}

═══════════════════════════════════════════════════════════════════════
                    CRITICAL: FILE FORMAT REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

You MUST format each file EXACTLY like this:

### `filename.ext`
```language
[complete code here]
```

EXAMPLE (follow this EXACTLY):

### `main.py`
```python
import click
import json

@click.command()
def main():
    print("Hello")

if __name__ == "__main__":
    main()
```

### `config.json`
```json
{{"key": "value"}}
```

═══════════════════════════════════════════════════════════════════════
                    CRITICAL: CODE QUALITY REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

Every code file MUST be:
1. COMPLETE - Include ALL imports at the top
2. RUNNABLE - Can execute without errors
3. SELF-CONTAINED - Don't reference undefined variables
4. HAVE AN ENTRY POINT - Include `if __name__ == "__main__":` for Python,
   or equivalent for other languages

DO NOT:
- Use TODO, FIXME, or placeholder comments - implement EVERYTHING
- Write "# TO DO: ..." or "pass" - write actual working code
- Return dummy/hardcoded data - implement real logic
- Split one file across multiple code blocks
- Reference variables defined in other code blocks
- Use @app.get() without defining 'app' in the same file
- Leave out imports

CRITICAL: Every function must have REAL implementation, not placeholders.
If the spec says "use SQLite", write actual SQLite code with tables and queries.
If the spec says "10 seed quotes", include 10 actual quotes in the code.

═══════════════════════════════════════════════════════════════════════

OUTPUT STRUCTURE (follow this exactly):

1. Start with "## Summary" - 2-3 sentences about what you built

2. Then "## Files" - Output each file with:
   ### `filename.ext`
   ```language
   <actual code here>
   ```

   Output ALL files here. Do NOT repeat files or show them again later.

3. Then "## How to Run" - The exact commands to run the project

4. Finally "## Notes" - Any testing/verification info

IMPORTANT: Only output each file ONCE under "## Files". Do not show files anywhere else."""

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Implement based on Architect's plan.

        Args:
            task: The original task (for reference)
            context: Optional context (project info, codebase details)
            previous_output: Sketch's plan

        Returns:
            AgentOutput with implementation and handoff to Oracle
        """
        self.status = AgentStatus.THINKING
        self._current_task = task

        try:
            # Extract project type from context, Sketch's output, or detect
            project_type = None
            project_category = None
            project_config = None
            detector = ProjectTypeDetector()

            # First, try to get from context (passed from project metadata)
            if context:
                type_str = context.get("project_type")
                cat_str = context.get("project_category")
                if type_str:
                    try:
                        project_type = ProjectType(type_str)
                        project_config = detector.get_config(project_type)
                        project_category = project_config.category if project_config else None
                    except (ValueError, KeyError):
                        pass
                elif cat_str:
                    try:
                        project_category = ProjectCategory(cat_str)
                    except (ValueError, KeyError):
                        pass

            # Second, try to get from Sketch's artifacts
            if not project_type and previous_output and previous_output.artifacts:
                type_str = previous_output.artifacts.get("project_type")
                cat_str = previous_output.artifacts.get("project_category")
                if type_str:
                    try:
                        project_type = ProjectType(type_str)
                        project_config = detector.get_config(project_type)
                        project_category = project_config.category if project_config else None
                    except (ValueError, KeyError):
                        pass
                elif cat_str:
                    try:
                        project_category = ProjectCategory(cat_str)
                    except (ValueError, KeyError):
                        pass

            # Fallback: detect from task/context
            if not project_type:
                combined_text = task
                if context and context.get("description"):
                    combined_text += " " + context["description"]
                project_type, project_category, _ = detector.detect(combined_text)
                project_config = detector.get_config(project_type)

            print(f"[Tinker] Building {project_type.value if project_type else 'unknown'} ({project_category.value if project_category else 'unknown'})")

            # Build prompt incorporating Architect's plan
            if previous_output and previous_output.content:
                print(f"[Tinker] Received Sketch plan ({len(previous_output.content)} chars)")
                prompt = f"""Sketch has provided this plan:

{previous_output.content}

Original Task: {task}

Now implement this plan. Create the actual code and implementation."""
            else:
                # Direct implementation without Architect (for simple tasks)
                print(f"[Tinker] No Sketch plan received - implementing directly")
                prompt = f"""Implement the following task directly:

{task}

Create clean, working code that solves this problem."""

            # Add project type context and deliverables
            if project_config:
                prompt += f"\n\nPROJECT TYPE: {project_config.name}"
                prompt += f"\nBuild Approach: {project_config.build_approach}"

            # Add type-specific deliverables (CRITICAL for quality)
            if project_category and project_category in TYPE_DELIVERABLES:
                prompt += f"\n\n{TYPE_DELIVERABLES[project_category]}"
                prompt += "\n\nIMPORTANT: Follow ALL requirements above. The output must be SELLABLE QUALITY - ready to publish/sell without modifications."

            if context:
                # Check if this is an update workflow
                if context.get("is_update") and context.get("update_prompt"):
                    prompt += f"\n\n{context['update_prompt']}"
                    print(f"[Tinker] UPDATE MODE - modifying existing product")

                if "existing_code" in context:
                    prompt += f"\n\nExisting Code to Modify:\n{context['existing_code']}"
                if "existing_files" in context and context["existing_files"]:
                    prompt += "\n\n## Existing Files"
                    for filename, content in context["existing_files"].items():
                        # Truncate large files
                        preview = content[:2000] + "..." if len(content) > 2000 else content
                        prompt += f"\n\n### `{filename}`\n```\n{preview}\n```"
                if "style_guide" in context:
                    prompt += f"\n\nCode Style Guide:\n{context['style_guide']}"

                # Include spec data if available (requirements, design)
                if "spec" in context:
                    spec = context["spec"]
                    if spec.get("requirements"):
                        prompt += "\n\n## Requirements from Spec"
                        for req in spec["requirements"][:10]:  # Limit to top 10
                            prompt += f"\n- {req.get('id', 'REQ')}: {req.get('title', '')} - {req.get('description', '')}"
                    if spec.get("design", {}).get("overview"):
                        prompt += f"\n\n## Design Overview\n{spec['design']['overview']}"

                # Include tech stack decision from spec
                if "tech_stack" in context:
                    ts = context["tech_stack"]
                    prompt += f"\n\n## REQUIRED TECH STACK (from spec)"
                    prompt += f"\n- Language: {ts.get('language', 'Python')}"
                    prompt += f"\n- Framework: {ts.get('framework', 'None')}"
                    if ts.get('reasoning'):
                        prompt += f"\n- Reasoning: {ts.get('reasoning')}"
                    prompt += "\n\nYou MUST use this tech stack. Do not switch to a different language or framework."

                # Include team chat resolved concerns if available
                if "team_chat_summary" in context:
                    prompt += f"\n\n## Team Feedback (Already Addressed)\n{context['team_chat_summary']}"
                    print(f"[Tinker] Including team chat context")

                # Include any clarifications from user
                if "user_clarifications" in context:
                    prompt += "\n\n## User Clarifications"
                    for clarification in context["user_clarifications"]:
                        prompt += f"\n- {clarification}"

            # Augment with relevant knowledge from the knowledge base
            # This gives Tinker access to deployment guides and platform-specific info
            augmenter = get_knowledge_augmenter()
            knowledge_context = augmenter.augment_prompt(task, context, max_entries=2)
            if knowledge_context:
                prompt += f"\n\n{knowledge_context}"

            # Augment with live web research for current best practices
            research_augmenter = get_research_augmenter()
            research_context = await research_augmenter.augment_prompt(task, context)
            if research_context:
                prompt += f"\n\n{research_context}"

            self.status = AgentStatus.WORKING

            # Generate implementation with type-aware system prompt
            response, token_info = await self._generate_with_provider(
                prompt,
                system_prompt=self.get_system_prompt(project_category, project_config),
                temperature=0.4,  # Lower temperature for more precise code
            )

            # Extract reasoning section if present
            reasoning = ""
            if "## My Reasoning" in response:
                parts = response.split("## My Reasoning")
                if len(parts) > 1:
                    reasoning_end = parts[1].find("\n## ")
                    if reasoning_end > 0:
                        reasoning = parts[1][:reasoning_end].strip()
                    else:
                        reasoning = parts[1].strip()

            # Log to memory
            if self.memory:
                self.memory.save_conversation(
                    user_message=f"[Mason Building] {task}",
                    assistant_response=response,
                    model="mason",
                    task_type="implementation"
                )

            # Extract file artifacts from response
            artifacts = {
                "task": task,
                "type": "implementation",
                "has_code": "```" in response,
                "project_type": project_type.value if project_type else None,
                "project_category": project_category.value if project_category else None,
            }

            # Parse file modifications if present
            if "## Files Modified" in response:
                files_section = response.split("## Files Modified")[1].split("##")[0]
                files = []
                for line in files_section.strip().split("\n"):
                    if line.startswith("- `"):
                        file_path = line.split("`")[1]
                        files.append(file_path)
                artifacts["files_modified"] = files

            # Parse deliverables checklist if present
            deliverables_completed = {}
            if "## Deliverables Checklist" in response:
                checklist_section = response.split("## Deliverables Checklist")[1].split("## ")[0]
                for line in checklist_section.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("- [x]") or line.startswith("- [X]") or "✓" in line:
                        # Extract deliverable name
                        item = line.replace("- [x]", "").replace("- [X]", "").replace("✓", "").strip()
                        if item:
                            deliverables_completed[item[:50]] = True
                    elif line.startswith("- [ ]") or "⬜" in line:
                        item = line.replace("- [ ]", "").replace("⬜", "").strip()
                        if item:
                            deliverables_completed[item[:50]] = False

            artifacts["deliverables_completed"] = deliverables_completed
            artifacts["deliverables_count"] = len(deliverables_completed)
            artifacts["deliverables_done"] = sum(1 for v in deliverables_completed.values() if v)

            self.status = AgentStatus.COMPLETED

            return AgentOutput(
                content=response,
                reasoning=reasoning,
                tokens_used=token_info.get("total_tokens", 0),
                prompt_tokens=token_info.get("prompt_tokens", 0),
                completion_tokens=token_info.get("completion_tokens", 0),
                artifacts=artifacts,
                next_agent="oracle",
                metadata={
                    "agent": self.name,
                    "had_plan": previous_output is not None,
                    "provider": token_info.get("provider", "unknown"),
                    "project_type": project_type.value if project_type else "unknown",
                    "project_category": project_category.value if project_category else "unknown",
                },
            )

        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Implementation failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )
        finally:
            self._current_task = None
