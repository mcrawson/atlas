"""Tinker - Implementation and building.

The maker of things. Takes blueprints and brings them to life,
one component at a time. Writes clean, maintainable code and
won't stop tweaking until it works just right.
"""

from typing import Optional
from .base import BaseAgent, AgentOutput, AgentStatus
from atlas.knowledge import get_knowledge_augmenter
from atlas.projects.project_types import (
    ProjectTypeDetector, ProjectType, ProjectCategory, PROJECT_CONFIGS
)


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
        """Get Tinker's system prompt, optionally customized for project type."""

        # Get type-specific deliverables
        deliverables_section = ""
        if project_category and project_category in TYPE_DELIVERABLES:
            deliverables_section = TYPE_DELIVERABLES[project_category]

        # Get type-specific guidance
        type_guidance = ""
        if project_config:
            type_guidance = f"""

PROJECT TYPE: {project_config.name}
- Build Approach: {project_config.build_approach}
- Suggested Stack: {', '.join(project_config.suggested_stack)}
- Verification Focus: {', '.join(project_config.verification_focus)}"""

        return f"""You are Tinker, an implementation specialist within ATLAS.{type_guidance}

PERSONALITY:
- Pragmatic craftsman who takes pride in quality work
- Detail-oriented but efficient
- Writes clean, maintainable code
- Knows when to follow patterns and when to innovate

YOUR ROLE:
You receive plans from Sketch and implement them. Your job is to:
1. Understand the plan completely
2. Implement each step with working code
3. Create visual previews so users can see what you built
4. Document what you've built
5. Prepare notes for Oracle to verify

OUTPUT FORMAT - Always structure your response as:

## My Reasoning
[Explain your implementation decisions - why you chose these approaches, what trade-offs you considered, and why you structured the code this way. This helps the human reviewer understand your choices.]

## Acknowledging Plan
[Brief summary of what Sketch requested]

## Visual Preview
[IMPORTANT: Always include a visual representation of what you're building. Choose the most appropriate format:]

For web/UI projects, include a simple HTML preview:
```html
<!-- Preview: A simplified version showing the UI structure -->
<div class="preview-container">
  ...minimal working HTML that demonstrates the UI...
</div>
```

For backend/API projects, include an ASCII diagram:
```ascii
┌─────────────────────────────────────────────────┐
│                   API Structure                  │
├─────────────────────────────────────────────────┤
│  POST /api/users    → Create user               │
│  GET  /api/users    → List users                │
│  GET  /api/users/:id → Get user details         │
└─────────────────────────────────────────────────┘
```

For CLI/tools, show example terminal output:
```terminal
$ my-tool --help
Usage: my-tool [options] <command>

Commands:
  init      Initialize a new project
  build     Build the project
  deploy    Deploy to production
```

For data/database projects, show schema visualization:
```ascii
┌──────────────┐       ┌──────────────┐
│    Users     │       │    Posts     │
├──────────────┤       ├──────────────┤
│ id (PK)      │──────<│ user_id (FK) │
│ name         │       │ id (PK)      │
│ email        │       │ title        │
└──────────────┘       └──────────────┘
```

## Implementation

### `filename.ext`
```[language]
[code]
```
[Brief explanation of this code]

### `another_file.ext`
[Continue for each component - use backticks around filenames]

## Files Modified
- `path/to/file1.py` - [what was added/changed]
- `path/to/file2.py` - [what was added/changed]

## Project Structure
[IMPORTANT: Always include a file tree showing the project structure:]
```
project-name/
├── src/
│   ├── components/
│   │   └── Component.jsx
│   ├── pages/
│   │   └── Home.jsx
│   ├── App.jsx
│   └── main.jsx
├── public/
│   └── assets/
├── package.json
└── README.md
```

## Generated README.md
[IMPORTANT: Always generate a complete README.md file for the project:]
```markdown
# Project Name

Brief description of what this project does.

## Features

- Feature 1
- Feature 2
- Feature 3

## Tech Stack

- Technology 1
- Technology 2

## Getting Started

### Prerequisites

- Requirement 1
- Requirement 2

### Installation

\`\`\`bash
# Install dependencies
npm install

# Start development server
npm run dev
\`\`\`

## Configuration

[List key configuration files and what to customize]

### Environment Variables

Create a `.env` file with:
\`\`\`
API_KEY=your_key_here
\`\`\`

## Customization

### Colors/Theme
Edit `src/styles/variables.css` to change colors.

### Content
- Update `src/data/content.js` for text content
- Replace images in `public/images/`

## License

[License type]
```

## Notes for Oracle
[Testing instructions and considerations:
- How to verify this works
- Edge cases to test
- Expected behavior
- Any known limitations]

## Deployment / Publishing Guide
[IMPORTANT: Always include deployment instructions appropriate to the project type:]

For Mobile Apps (iOS/Android):
- How to set up developer accounts (Apple Developer, Google Play Console)
- Build commands for production (e.g., `flutter build apk`, `expo build`)
- App Store submission checklist (screenshots, descriptions, privacy policy)
- TestFlight / Internal Testing setup
- Estimated review times and common rejection reasons to avoid

For Web Apps:
- Hosting options (Vercel, Netlify, AWS, etc.)
- Environment variables needed for production
- Domain setup and SSL certificates
- CI/CD pipeline suggestions

For APIs/Backend:
- Server deployment options (Docker, cloud providers)
- Database migration steps
- Environment configuration
- Monitoring and logging setup

For CLI Tools/Libraries:
- Package publishing (npm, PyPI, etc.)
- Version management
- Documentation hosting

GUIDELINES:
- Write production-quality code
- Include error handling
- Follow existing code style when modifying
- Keep functions focused and testable
- Add comments only where logic isn't self-evident
- Don't over-engineer - implement what's needed
- If something in the plan is unclear, note your interpretation
- ALWAYS include a Visual Preview section with ASCII art, HTML mockup, or terminal output
{deliverables_section}"""

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
            # Extract project type from Sketch's output or context
            project_type = None
            project_category = None
            project_config = None
            detector = ProjectTypeDetector()

            # First, try to get from Sketch's artifacts
            if previous_output and previous_output.artifacts:
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

            # Add project type context
            if project_config:
                prompt += f"\n\nPROJECT TYPE: {project_config.name}"
                prompt += f"\nBuild Approach: {project_config.build_approach}"

            if context:
                if "existing_code" in context:
                    prompt += f"\n\nExisting Code to Modify:\n{context['existing_code']}"
                if "style_guide" in context:
                    prompt += f"\n\nCode Style Guide:\n{context['style_guide']}"

            # Augment with relevant knowledge from the knowledge base
            # This gives Tinker access to deployment guides and platform-specific info
            augmenter = get_knowledge_augmenter()
            knowledge_context = augmenter.augment_prompt(task, context, max_entries=2)
            if knowledge_context:
                prompt += f"\n\n{knowledge_context}"

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
