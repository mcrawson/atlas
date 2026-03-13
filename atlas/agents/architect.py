"""Sketch - Strategic planning and risk analysis.

The idea whisperer. Takes rough concepts and turns them into detailed blueprints.
Analyzes requirements, identifies risks, and draws up the master plan.
"""

from typing import Optional
from .base import BaseAgent, AgentOutput, AgentStatus
from atlas.specs import SpecGenerator, Spec
from atlas.knowledge import get_knowledge_augmenter
from atlas.research import get_research_augmenter
from atlas.projects.project_types import (
    ProjectTypeDetector, ProjectType, ProjectCategory, PROJECT_CONFIGS
)
from atlas.standards import get_agent_philosophy, PRODUCT_INTEGRATIONS


# Type-specific output formats for Sketch
TYPE_SPECIFIC_FORMATS = {
    ProjectCategory.APP: """
## App Screens & Features
[List each screen with its purpose]
- **Screen Name**: Description and key elements
- Include navigation flow between screens

## Technical Architecture
- Platform: [iOS/Android/Cross-platform]
- Framework: [Recommended framework]
- State Management: [Approach]
- Data Storage: [Local/Cloud/Hybrid]

## App Store Requirements
- App Name & Subtitle
- Category
- Age Rating considerations
- Required permissions (camera, location, etc.)
- Privacy policy needs

## Assets Needed
- [ ] App Icon (1024x1024)
- [ ] Screenshots for store listing
- [ ] App Store description
- [ ] Privacy policy URL
""",

    ProjectCategory.WEB: """
## Pages & Components
[List each page/route]
- **Page Name** (`/route`): Purpose and key components
- Include user flow between pages

## Technical Architecture
- Framework: [Recommended framework]
- Styling: [CSS approach]
- State Management: [If needed]
- Backend needs: [API/Database requirements]

## Deployment Plan
- Hosting: [Vercel/Netlify/etc.]
- Domain requirements
- Environment variables needed
- CI/CD approach

## SEO & Performance
- Meta tags strategy
- Performance targets
- Analytics setup
""",

    ProjectCategory.DOCUMENT: """
## Document Structure
### Outline
[Chapter/Section breakdown with descriptions]

### Chapter Details
For each chapter:
- **Chapter Title**
  - Key points to cover
  - Estimated word count
  - Research needed

## Formatting & Style
- Target total word count: [X words]
- Tone: [Professional/Casual/Academic/etc.]
- Target audience: [Description]
- Style guide notes

## Publishing Requirements
- Format: [Ebook/Print/Both]
- Platform: [Amazon KDP/etc.]
- ISBN needs
- Cover requirements (dimensions, style)

## Assets Needed
- [ ] Book cover design
- [ ] Interior formatting template
- [ ] Author bio
- [ ] Book description/blurb
""",

    ProjectCategory.API: """
## API Endpoints
[List each endpoint]
- **METHOD /path**: Description
  - Request body/params
  - Response format
  - Auth requirements

## Data Models
[List each model/table]
- **ModelName**
  - field: type (constraints)
  - Relationships

## Authentication & Security
- Auth method: [JWT/OAuth/API Key/etc.]
- Rate limiting
- Input validation approach
- Security considerations

## Deployment Plan
- Hosting: [Railway/Fly.io/AWS/etc.]
- Database: [PostgreSQL/MongoDB/etc.]
- Environment configuration
- Monitoring setup
""",

    ProjectCategory.CLI: """
## Commands & Usage
```
toolname <command> [options]
```

### Commands
- **command1**: Description
  - `--flag`: What it does
  - Example usage

## Implementation Approach
- Language: [Python/Node/Go/etc.]
- Argument parsing: [Library]
- Configuration: [How config is handled]

## Distribution
- Installation method (pip/npm/brew/binary)
- Dependencies
- Platform support (Linux/Mac/Windows)
""",

    ProjectCategory.LIBRARY: """
## API Design
### Public Interface
```
function/class signatures with descriptions
```

### Usage Examples
```
Example code showing how to use the library
```

## Implementation Approach
- Language: [TypeScript/Python/etc.]
- Dependencies: [Minimal deps]
- Testing strategy

## Publishing Plan
- Package registry: [npm/PyPI/etc.]
- Versioning strategy
- Documentation site
- CI/CD for releases
""",

    ProjectCategory.SCRIPT: """
## Script Purpose
What this script automates/processes

## Input/Output
- **Input**: [Format and source]
- **Output**: [Format and destination]
- **Side effects**: [Files created, APIs called, etc.]

## Implementation
- Language: [Python/Bash/etc.]
- Dependencies needed
- Error handling approach
- Logging strategy

## Usage
```
How to run the script with examples
```

## Scheduling (if applicable)
- Frequency: [How often it runs]
- Trigger: [Cron/manual/event-based]
""",
}


class ArchitectAgent(BaseAgent):
    """Sketch: Strategic planner and risk analyst.

    The idea whisperer. Takes rough concepts and turns them into
    detailed blueprints. Analyzes requirements, identifies risks,
    and draws up the master plan before a single line of code is written.

    Output Format:
    - Understanding: Restates the task
    - Risks: Potential issues and considerations
    - Approach: High-level strategy
    - Implementation Plan: Step-by-step breakdown
    - Handoff: Instructions for Tinker
    """

    name = "sketch"
    description = "The idea whisperer"
    icon = "💡"
    color = "#4A90D9"

    def get_system_prompt(self, project_category: ProjectCategory = None, project_config=None) -> str:
        """Get Sketch's system prompt, optionally customized for project type."""

        # Get type-specific output format
        type_format = ""
        if project_category and project_category in TYPE_SPECIFIC_FORMATS:
            type_format = f"""

## Type-Specific Sections
For this {project_category.value.upper()} project, also include:
{TYPE_SPECIFIC_FORMATS[project_category]}"""

        # Get type-specific guidance from config
        type_guidance = ""
        if project_config:
            type_guidance = f"""

PROJECT TYPE: {project_config.name}
- Build Approach: {project_config.build_approach}
- Suggested Stack: {', '.join(project_config.suggested_stack)}
- Key Verification Points: {', '.join(project_config.verification_focus)}"""

        # Get agent-specific philosophy
        philosophy = get_agent_philosophy("sketch")

        return f"""You are Sketch, a strategic planning agent within ATLAS.

{philosophy}

PERSONALITY:
- Methodical and thorough in analysis
- Strategic thinker who sees the big picture
- Risk-aware but not risk-averse
- Clear communicator who breaks down complexity

YOUR ROLE:
You are the first agent in the workflow. Your job is to:
1. Understand the task completely
2. Define what "SELLABLE" means for this specific product
3. Identify which integrations/tools will be needed (Canva, Figma, KDP, etc.)
4. Design a clear approach with quality standards
5. Create an actionable implementation plan for Tinker that produces sellable output
{type_guidance}

OUTPUT FORMAT - Always structure your response as:

## My Reasoning
[Explain your thought process - why you're approaching it this way, what alternatives you considered, and why you chose this path. This helps the human reviewer understand your decisions.]

## Understanding
[Restate the task in your own words to confirm understanding]

## Risk Analysis
- [Risk 1]: [Mitigation strategy]
- [Risk 2]: [Mitigation strategy]
[Include technical risks, scope risks, and dependency risks]

## Approach
[High-level strategy for solving this task]

## Implementation Plan
1. [Step 1 with clear deliverable]
2. [Step 2 with clear deliverable]
3. [Continue as needed]
{type_format}
## Handoff to Tinker
[Specific instructions for Tinker, including:
- What to build first
- Key files/components to create or modify
- Testing considerations for Oracle]

GUIDELINES:
- Be thorough but concise
- Focus on actionable steps
- Consider testability from the start
- Flag any assumptions you're making
- If the task is unclear, note what clarification is needed"""

    async def process(
        self,
        task: str,
        context: Optional[dict] = None,
        previous_output: Optional[AgentOutput] = None,
    ) -> AgentOutput:
        """Process a task and create an implementation plan.

        Args:
            task: The task to plan
            context: Optional context (project info, codebase details)
            previous_output: Not typically used (Architect is first)

        Returns:
            AgentOutput with plan and handoff to Mason
        """
        self.status = AgentStatus.THINKING
        self._current_task = task

        try:
            # Detect project type from task and context
            detector = ProjectTypeDetector()
            combined_text = task
            if context:
                if context.get("description"):
                    combined_text += " " + context["description"]
                if context.get("brief"):
                    combined_text += " " + str(context["brief"])
                # Check if project type is already set in context
                if context.get("project_type"):
                    try:
                        project_type = ProjectType(context["project_type"])
                        project_config = detector.get_config(project_type)
                        project_category = project_config.category if project_config else None
                    except (ValueError, KeyError):
                        project_type, project_category, _ = detector.detect(combined_text)
                        project_config = detector.get_config(project_type)
                else:
                    project_type, project_category, _ = detector.detect(combined_text)
                    project_config = detector.get_config(project_type)
            else:
                project_type, project_category, _ = detector.detect(combined_text)
                project_config = detector.get_config(project_type)

            print(f"[Sketch] Detected project type: {project_type.value} ({project_category.value})")

            # Build prompt with context
            prompt = f"Plan the following task:\n\n{task}"

            # Add project type context
            if project_config:
                prompt += f"\n\nPROJECT TYPE: {project_config.name}"
                prompt += f"\nDescription: {project_config.description}"
                prompt += f"\nSuggested Stack: {', '.join(project_config.suggested_stack)}"

            if context:
                if "codebase" in context:
                    prompt += f"\n\nCodebase Context:\n{context['codebase']}"
                if "constraints" in context:
                    prompt += f"\n\nConstraints:\n{context['constraints']}"
                if "existing_files" in context:
                    prompt += f"\n\nRelevant Files:\n{context['existing_files']}"

            # Augment with relevant knowledge from the knowledge base
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

            # Generate plan using type-aware system prompt
            response, token_info = await self._generate_with_provider(
                prompt,
                system_prompt=self.get_system_prompt(project_category, project_config),
                temperature=0.7,  # Balanced for planning
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

            # Log to memory if available
            if self.memory:
                self.memory.save_conversation(
                    user_message=f"[Architect Planning] {task}",
                    assistant_response=response,
                    model="architect",
                    task_type="planning"
                )

            self.status = AgentStatus.COMPLETED

            return AgentOutput(
                content=response,
                reasoning=reasoning,
                tokens_used=token_info.get("total_tokens", 0),
                prompt_tokens=token_info.get("prompt_tokens", 0),
                completion_tokens=token_info.get("completion_tokens", 0),
                artifacts={
                    "task": task,
                    "type": "plan",
                    "project_type": project_type.value if project_type else None,
                    "project_category": project_category.value if project_category else None,
                    "suggested_stack": project_config.suggested_stack if project_config else [],
                },
                next_agent="mason",
                metadata={
                    "agent": self.name,
                    "context_used": bool(context),
                    "provider": token_info.get("provider", "unknown"),
                    "project_type": project_type.value if project_type else "unknown",
                    "project_category": project_category.value if project_category else "unknown",
                },
            )

        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Planning failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )
        finally:
            self._current_task = None

    async def generate_spec(
        self,
        idea: str,
        context: Optional[dict] = None,
        output_dir: Optional[str] = None,
    ) -> tuple[Spec, AgentOutput]:
        """Generate a Kiro-style spec from an idea.

        Uses the SpecGenerator to create requirements, design, and tasks,
        then wraps the result in an AgentOutput for workflow integration.

        Args:
            idea: Natural language description of the project/feature
            context: Optional context (features, constraints, etc.)
            output_dir: If provided, writes spec files to this directory

        Returns:
            Tuple of (Spec object, AgentOutput with spec summary)
        """
        self.status = AgentStatus.THINKING
        self._current_task = f"Generating spec: {idea[:50]}..."

        try:
            # Initialize spec generator
            generator = SpecGenerator()

            self.status = AgentStatus.WORKING

            # Generate spec using AI
            spec = await generator.generate_from_idea(idea, context)

            # Write files if output_dir provided
            files_written = {}
            if output_dir:
                result = generator.write_spec_files(spec, output_dir)
                files_written = result.get("files", {})

            # Build summary for AgentOutput
            summary = f"""## Spec Generated: {spec.name}

### Requirements ({len(spec.requirements)})
"""
            for req in spec.requirements[:5]:  # Show first 5
                summary += f"- **{req.id}**: {req.title}\n"
            if len(spec.requirements) > 5:
                summary += f"- ... and {len(spec.requirements) - 5} more\n"

            if spec.design:
                summary += f"""
### Design Overview
{spec.design.overview[:500]}{'...' if len(spec.design.overview) > 500 else ''}

### Components ({len(spec.design.components)})
"""
                for comp in spec.design.components[:3]:
                    summary += f"- **{comp.name}**: {comp.description[:100]}\n"

            if spec.tasks:
                summary += f"""
### Implementation Tasks ({len(spec.tasks.tasks)})
"""
                for task in spec.tasks.tasks[:5]:
                    summary += f"- **{task.id}**: {task.title}\n"
                if len(spec.tasks.tasks) > 5:
                    summary += f"- ... and {len(spec.tasks.tasks) - 5} more\n"

            if files_written:
                summary += f"""
### Files Written
"""
                for name, path in files_written.items():
                    summary += f"- `{path}`\n"

            summary += """
## Handoff to Mason

The spec has been generated with requirements, design, and tasks.
Execute tasks sequentially, starting with the highest priority items.
Each task includes requirement IDs for traceability.
"""

            self.status = AgentStatus.COMPLETED

            output = AgentOutput(
                content=summary,
                artifacts={
                    "spec": spec.to_dict(),
                    "files_written": files_written,
                    "type": "spec",
                },
                next_agent="mason",
                metadata={
                    "agent": self.name,
                    "spec_name": spec.name,
                    "requirements_count": len(spec.requirements),
                    "tasks_count": len(spec.tasks.tasks) if spec.tasks else 0,
                },
            )

            return spec, output

        except Exception as e:
            self.status = AgentStatus.ERROR
            error_output = AgentOutput(
                content=f"Spec generation failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )
            return None, error_output
        finally:
            self._current_task = None
