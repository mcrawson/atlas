"""
Builder Mode Handler for ATLAS product building.

Orchestrates ATLAS agents (Analyst, Mason, QC) to build complete
products overnight.
"""

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from atlas.operator.config import OvernightConfig

logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    """Result from builder mode processing."""
    success: bool
    project_name: str
    project_path: Optional[Path]
    brief_summary: str
    qc_status: str  # PASS, PASS_WITH_NOTES, FAIL
    qc_notes: Optional[str]
    iterations: int
    error: Optional[str]
    timestamp: datetime


class BuilderMode:
    """
    Orchestrates ATLAS to build products overnight.

    Workflow:
    1. Run Analyst to generate Business Brief
    2. Run Mason to build the product
    3. Run QC to verify quality
    4. Retry with QC feedback if needed
    5. Save completed project
    """

    def __init__(self, config: OvernightConfig, provider=None):
        self.config = config
        self._provider = provider
        self._claude_provider = None

        # Lazy-loaded ATLAS components
        self._analyst = None
        self._mason = None
        self._qc = None
        self._router = None

    async def _get_provider(self):
        """Lazy-load the Claude provider."""
        if self._provider:
            return self._provider
        if self._claude_provider is None:
            from atlas.routing.providers.claude import ClaudeProvider
            self._claude_provider = ClaudeProvider()
        return self._claude_provider

    async def _get_router(self):
        """Lazy-load the ATLAS router."""
        if self._router is None:
            from atlas.routing.router import Router
            self._router = Router()
        return self._router

    async def _get_analyst(self):
        """Lazy-load the Analyst agent."""
        if self._analyst is None:
            from atlas.agents.analyst import AnalystAgent
            router = await self._get_router()
            self._analyst = AnalystAgent(router=router, memory=None)
        return self._analyst

    async def _get_mason(self):
        """Lazy-load the Mason agent."""
        if self._mason is None:
            from atlas.agents.mason import MasonAgent
            router = await self._get_router()
            self._mason = MasonAgent(router=router, memory=None)
        return self._mason

    async def _get_qc(self):
        """Lazy-load the QC agent."""
        if self._qc is None:
            from atlas.agents.qc import QCAgent
            router = await self._get_router()
            self._qc = QCAgent(router=router, memory=None)
        return self._qc

    async def execute(self, task: dict) -> BuildResult:
        """
        Execute an ATLAS product build task.

        Args:
            task: Task dict with 'prompt' describing what to build

        Returns:
            BuildResult with project status and path
        """
        prompt = task.get("prompt", "")
        metadata = task.get("metadata", {}) or {}
        timestamp = datetime.now()

        try:
            # 1. Run Analyst for business brief
            logger.info("Running Analyst to generate business brief...")
            brief = await self._run_analyst(prompt)

            if not brief:
                return BuildResult(
                    success=False,
                    project_name="unknown",
                    project_path=None,
                    brief_summary="",
                    qc_status="FAIL",
                    qc_notes=None,
                    iterations=1,
                    error="Failed to generate business brief",
                    timestamp=timestamp,
                )

            project_name = brief.get("product_name", "untitled-project")
            brief_summary = f"{project_name}: {brief.get('description', '')[:100]}"
            logger.info(f"Generated brief: {brief_summary}")

            # 2. Run Mason to build
            logger.info("Running Mason to build product...")
            build_output = await self._run_mason(brief)

            if not build_output:
                return BuildResult(
                    success=False,
                    project_name=project_name,
                    project_path=None,
                    brief_summary=brief_summary,
                    qc_status="FAIL",
                    qc_notes=None,
                    iterations=1,
                    error="Mason failed to build product",
                    timestamp=timestamp,
                )

            # 3. Run QC to verify
            logger.info("Running QC to verify build...")
            qc_result = await self._run_qc(build_output, brief)

            iterations = 1
            max_iterations = 2

            # 4. Handle QC feedback
            while qc_result.get("verdict") in ("NEEDS_REVISION", "FAIL") and iterations < max_iterations:
                logger.info(f"QC returned {qc_result.get('verdict')}, attempting revision...")
                iterations += 1

                # Rebuild with QC feedback
                build_output = await self._run_mason(
                    brief,
                    qc_feedback=qc_result.get("fix_instructions"),
                )

                if build_output:
                    qc_result = await self._run_qc(build_output, brief)

            # 5. Save output
            qc_status = qc_result.get("verdict", "UNKNOWN")
            success = qc_status in ("PASS", "PASS_WITH_NOTES")

            project_path = None
            if success and build_output:
                project_path = await self._save_project(
                    project_name,
                    build_output,
                    brief,
                    qc_result,
                )

            return BuildResult(
                success=success,
                project_name=project_name,
                project_path=project_path,
                brief_summary=brief_summary,
                qc_status=qc_status,
                qc_notes=qc_result.get("fix_instructions"),
                iterations=iterations,
                error=None if success else f"QC failed: {qc_status}",
                timestamp=timestamp,
            )

        except Exception as e:
            logger.exception("Error in builder mode")
            return BuildResult(
                success=False,
                project_name="unknown",
                project_path=None,
                brief_summary="",
                qc_status="FAIL",
                qc_notes=None,
                iterations=0,
                error=str(e),
                timestamp=timestamp,
            )

    async def _run_analyst(self, prompt: str) -> Optional[dict]:
        """Run the Analyst agent to generate a business brief."""
        try:
            analyst = await self._get_analyst()

            # Create a task context
            from atlas.agents.base import AgentOutput

            result: AgentOutput = await analyst.process(
                task=prompt,
                context={},
                previous_output=None,
            )

            # Parse the brief from artifacts or content
            if result.artifacts and "business_brief" in result.artifacts:
                return result.artifacts["business_brief"]

            # Try to parse from content if structured
            if result.content:
                try:
                    return json.loads(result.content)
                except json.JSONDecodeError:
                    # Return a basic brief structure
                    return {
                        "product_name": "Generated Product",
                        "description": result.content[:500],
                        "type": "web",
                    }

            return None

        except Exception as e:
            logger.error(f"Analyst failed: {e}")
            # Fallback: generate a basic brief using the provider directly
            return await self._generate_basic_brief(prompt)

    async def _generate_basic_brief(self, prompt: str) -> dict:
        """Generate a basic brief when Analyst agent isn't available."""
        provider = await self._get_provider()

        brief_prompt = f"""Generate a product brief for this request:

{prompt}

Respond with JSON containing:
- product_name: string
- description: string (1-2 sentences)
- type: one of "web", "app", "printable", "document"
- key_features: list of 3-5 features
- target_audience: string

JSON only, no markdown:"""

        response = await provider.generate(
            prompt=brief_prompt,
            system_prompt="You are a product analyst. Generate structured product briefs.",
            max_tokens=1000,
            temperature=0.5,
        )

        try:
            # Try to extract JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback
        return {
            "product_name": "Custom Product",
            "description": prompt[:200],
            "type": "web",
            "key_features": ["Feature 1", "Feature 2", "Feature 3"],
            "target_audience": "General users",
        }

    async def _run_mason(
        self,
        brief: dict,
        qc_feedback: Optional[str] = None,
    ) -> Optional[dict]:
        """Run the Mason agent to build the product."""
        try:
            mason = await self._get_mason()

            task = f"Build: {brief.get('product_name', 'Product')}"
            context = {
                "business_brief": brief,
            }

            if qc_feedback:
                context["qc_feedback"] = qc_feedback
                task += f"\n\nQC Feedback to address:\n{qc_feedback}"

            result = await mason.process(
                task=task,
                context=context,
                previous_output=None,
            )

            return {
                "content": result.content,
                "artifacts": result.artifacts,
                "files": result.artifacts.get("files", {}),
            }

        except Exception as e:
            logger.error(f"Mason failed: {e}")
            # Fallback: generate basic HTML
            return await self._generate_basic_build(brief, qc_feedback)

    async def _generate_basic_build(
        self,
        brief: dict,
        qc_feedback: Optional[str] = None,
    ) -> dict:
        """Generate a basic build when Mason agent isn't available."""
        provider = await self._get_provider()

        build_prompt = f"""Build a complete, production-ready web page for this product:

Product: {brief.get('product_name', 'Product')}
Description: {brief.get('description', '')}
Features: {', '.join(brief.get('key_features', []))}
Target Audience: {brief.get('target_audience', 'General users')}
"""

        if qc_feedback:
            build_prompt += f"\n\nPrevious QC feedback to address:\n{qc_feedback}"

        build_prompt += """

Create a complete HTML file with embedded CSS and JavaScript.
Make it professional, polished, and ready to use.
Return ONLY the HTML code, no explanations."""

        response = await provider.generate(
            prompt=build_prompt,
            system_prompt="You are a senior web developer. Create beautiful, functional, production-ready web pages.",
            max_tokens=8000,
            temperature=0.7,
        )

        # Extract HTML
        import re
        html_match = re.search(r'<!DOCTYPE html>.*</html>', response, re.DOTALL | re.IGNORECASE)
        if html_match:
            html_content = html_match.group()
        else:
            html_content = response

        return {
            "content": html_content,
            "artifacts": {},
            "files": {"index.html": html_content},
        }

    async def _run_qc(self, build_output: dict, brief: dict) -> dict:
        """Run the QC agent to verify the build."""
        try:
            qc = await self._get_qc()

            context = {
                "business_brief": brief,
                "build_output": build_output,
            }

            result = await qc.process(
                task="Evaluate this build against the business brief",
                context=context,
                previous_output=None,
            )

            if result.artifacts and "qc_report" in result.artifacts:
                return result.artifacts["qc_report"]

            # Parse from content
            return {
                "verdict": "PASS_WITH_NOTES" if result.content else "FAIL",
                "fix_instructions": result.content,
            }

        except Exception as e:
            logger.error(f"QC failed: {e}")
            # Fallback: basic QC
            return await self._basic_qc(build_output, brief)

    async def _basic_qc(self, build_output: dict, brief: dict) -> dict:
        """Basic QC when QC agent isn't available."""
        provider = await self._get_provider()

        files = build_output.get("files", {})
        content = build_output.get("content", "")

        qc_prompt = f"""Evaluate this build:

Product: {brief.get('product_name', '')}
Expected: {brief.get('description', '')}

Build Output:
{content[:3000]}

Does this build meet the requirements? Is it complete and professional?

Respond with:
VERDICT: PASS, PASS_WITH_NOTES, or FAIL
NOTES: Brief feedback
FIX_INSTRUCTIONS: What needs to be fixed (if FAIL)"""

        response = await provider.generate(
            prompt=qc_prompt,
            system_prompt="You are a quality assurance expert. Be thorough but fair.",
            max_tokens=1000,
            temperature=0.3,
        )

        # Parse response
        verdict = "PASS_WITH_NOTES"
        notes = ""
        fix_instructions = ""

        if "VERDICT:" in response:
            for line in response.split("\n"):
                if line.startswith("VERDICT:"):
                    v = line.replace("VERDICT:", "").strip().upper()
                    if v in ("PASS", "PASS_WITH_NOTES", "FAIL"):
                        verdict = v
                elif line.startswith("NOTES:"):
                    notes = line.replace("NOTES:", "").strip()
                elif line.startswith("FIX_INSTRUCTIONS:"):
                    fix_instructions = line.replace("FIX_INSTRUCTIONS:", "").strip()

        return {
            "verdict": verdict,
            "notes": notes,
            "fix_instructions": fix_instructions,
        }

    async def _save_project(
        self,
        project_name: str,
        build_output: dict,
        brief: dict,
        qc_result: dict,
    ) -> Path:
        """Save the completed project to disk."""
        # Clean project name for filesystem
        clean_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in project_name.lower())
        clean_name = clean_name[:50]  # Limit length

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        project_dir = self.config.atlas.projects_output / f"{clean_name}-{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)

        # Save files
        files = build_output.get("files", {})
        if files:
            for filename, content in files.items():
                file_path = project_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
        elif build_output.get("content"):
            # Single file output
            (project_dir / "index.html").write_text(build_output["content"])

        # Save brief
        brief_path = project_dir / "brief.json"
        brief_path.write_text(json.dumps(brief, indent=2))

        # Save QC report
        qc_path = project_dir / "qc-report.json"
        qc_path.write_text(json.dumps(qc_result, indent=2))

        # Create README
        readme = f"""# {project_name}

Generated by ATLAS Overnight Builder on {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Description
{brief.get('description', 'No description')}

## QC Status
{qc_result.get('verdict', 'Unknown')}

## Files
{chr(10).join(f'- {f}' for f in files.keys()) if files else '- index.html'}
"""
        (project_dir / "README.md").write_text(readme)

        logger.info(f"Saved project to: {project_dir}")
        return project_dir
