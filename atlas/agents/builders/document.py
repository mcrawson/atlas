"""DocumentBuilder - Creates long-form documents like books, guides, manuals.

This builder specializes in creating structured documents for platforms like Amazon KDP.
Output is professionally formatted HTML/CSS ready for PDF or EPUB conversion.

Products:
- Books (fiction, non-fiction, guides)
- Manuals (technical, user, how-to)
- Guides (educational, instructional)
- Ebooks
"""

import json
import logging
from typing import Optional

from atlas.agents.base import AgentOutput, AgentStatus
from .base import BaseBuilder, BuilderType, BuildOutput, BuildContext, OutputFormat
from .config import get_document_config, DocumentConfig

logger = logging.getLogger("atlas.builders.document")


class DocumentBuilder(BaseBuilder):
    """Builder for long-form documents (books, guides, manuals).

    Creates professionally structured documents suitable for publishing.
    Output is HTML/CSS designed for PDF/EPUB conversion.
    """

    name = "document_builder"
    description = "Document and book specialist"
    icon = "📚"
    color = "#2196F3"

    builder_type = BuilderType.DOCUMENT
    supported_formats = [OutputFormat.PDF, OutputFormat.EPUB, OutputFormat.HTML]

    def __init__(self, router=None, memory=None, **kwargs):
        self.router = router
        self.memory = memory
        self.options = kwargs
        self._status = AgentStatus.IDLE
        self._current_task = None
        self._callbacks = []
        self.config: DocumentConfig = get_document_config()

    def _get_builder_context(self) -> str:
        """Get DocumentBuilder-specific context."""
        return """You are the DocumentBuilder - expert in creating professional documents.

YOUR SPECIALIZATION:
- Books (non-fiction, guides, how-to books)
- Manuals (technical documentation, user guides)
- Ebooks (formatted for digital reading)
- Comprehensive guides and handbooks

OUTPUT REQUIREMENTS:
- Generate complete, professionally formatted HTML/CSS
- Structure with proper chapters and sections
- Include table of contents
- Use appropriate typography for long-form reading
- Design for both screen and print

DOCUMENT STRUCTURE:
1. TITLE PAGE: Book title, subtitle, author
2. COPYRIGHT PAGE: Standard publishing info
3. TABLE OF CONTENTS: Linked chapters
4. CHAPTERS: Numbered with clear headings
5. BACK MATTER: About author, resources (optional)

DESIGN PRINCIPLES:
1. READABLE: Optimized typography for long reading
2. STRUCTURED: Clear hierarchy and navigation
3. PROFESSIONAL: Publication-ready appearance
4. CONSISTENT: Unified formatting throughout
5. ACCESSIBLE: Good contrast, clear fonts

OUTPUT FORMAT:
Generate a complete HTML document with embedded CSS that:
- Has proper heading hierarchy (h1 > h2 > h3)
- Uses print-friendly page breaks
- Includes linked table of contents
- Has chapter titles and page numbers
- Is ready for PDF/EPUB conversion"""

    def get_system_prompt(self) -> str:
        """Get the full system prompt."""
        mission = """ATLAS is a product studio that combines human creativity with ethical AI
to build transformative solutions for our clients and the public.

Your job is to create SELLABLE documents and books. Every output must be something
a customer would pay for on Amazon KDP or similar platforms."""

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
                project_name=context.get("name", "Document") if context else "Document",
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
            logger.error(f"[DocumentBuilder] Build failed: {e}")
            self.status = AgentStatus.ERROR
            return AgentOutput(
                content=f"Build failed: {str(e)}",
                status=AgentStatus.ERROR,
                metadata={"error": str(e)},
            )
        finally:
            self._current_task = None

    async def build(self, context: BuildContext) -> BuildOutput:
        """Build a document.

        Args:
            context: Build context with all necessary information

        Returns:
            BuildOutput with HTML ready for PDF/EPUB conversion
        """
        logger.info(f"[DocumentBuilder] Building: {context.project_name}")

        # Determine document type
        doc_type = self._detect_document_type(context)
        doc_config = self._get_document_settings(context, doc_type)

        # Build the outline first
        outline = await self._generate_outline(context, doc_type)

        # Generate full document content
        prompt = self._build_generation_prompt(context, doc_type, doc_config, outline)

        response, token_info = await self._generate_with_provider(
            prompt,
            temperature=0.7,
        )

        # Parse and structure the response
        html_content = self._extract_html(response)

        # Wrap in proper document structure if needed
        if not html_content.strip().startswith("<!DOCTYPE"):
            html_content = self._wrap_html(html_content, context, doc_config)

        # Generate preview
        preview_html = self._generate_preview_html(html_content, context)

        return BuildOutput(
            content=html_content,
            format=OutputFormat.HTML,
            files={
                "book.html": html_content,
                "preview.html": preview_html,
                "outline.json": json.dumps(outline, indent=2),
            },
            metadata={
                "document_type": doc_type,
                "outline": outline,
                "tokens_used": token_info.get("total_tokens", 0),
            },
        )

    async def generate_preview(self, output: BuildOutput) -> str:
        """Generate a preview for the document."""
        if "preview.html" in output.files:
            return output.files["preview.html"]
        return output.content

    def _detect_document_type(self, context: BuildContext) -> str:
        """Detect the type of document."""
        description = context.project_description.lower()
        brief = context.business_brief

        if brief.get("product_type"):
            return brief["product_type"]

        if any(word in description for word in ["book", "novel", "story"]):
            return "book"
        if any(word in description for word in ["manual", "documentation", "technical"]):
            return "manual"
        if any(word in description for word in ["guide", "how-to", "tutorial"]):
            return "guide"
        if any(word in description for word in ["ebook", "e-book"]):
            return "ebook"
        if any(word in description for word in ["handbook", "reference"]):
            return "handbook"

        return "guide"

    def _get_document_settings(self, context: BuildContext, doc_type: str) -> dict:
        """Get document-specific settings."""
        brief = context.business_brief

        settings = {
            "format": self.config.default_format,
            "include_toc": self.config.include_toc,
            "chapter_style": self.config.chapter_style,
            "font_family": self.config.default_font_family,
            "heading_font": self.config.heading_font_family,
            "body_font_size": self.config.body_font_size,
        }

        # Override from brief preferences
        prefs = brief.get("preferences", {})
        if prefs.get("format"):
            settings["format"] = prefs["format"]
        if prefs.get("style"):
            settings["chapter_style"] = prefs["style"]

        return settings

    async def _generate_outline(self, context: BuildContext, doc_type: str) -> dict:
        """Generate document outline first."""
        prompt = f"""Create a detailed outline for a {doc_type}:

Title: {context.project_name}
Description: {context.project_description}

Generate a JSON outline with this structure:
{{
    "title": "Book Title",
    "subtitle": "Optional subtitle",
    "chapters": [
        {{
            "number": 1,
            "title": "Chapter Title",
            "sections": ["Section 1", "Section 2"],
            "summary": "Brief description of chapter content"
        }}
    ],
    "estimated_pages": 50,
    "target_word_count": 15000
}}

Create 5-10 chapters that comprehensively cover the topic.
Output valid JSON only."""

        response, _ = await self._generate_with_provider(prompt, temperature=0.5)

        # Parse outline
        try:
            # Extract JSON
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end]
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end]
            elif "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                response = response[start:end]

            return json.loads(response)
        except json.JSONDecodeError:
            # Return basic outline
            return {
                "title": context.project_name,
                "chapters": [
                    {"number": 1, "title": "Introduction", "sections": []},
                    {"number": 2, "title": "Main Content", "sections": []},
                    {"number": 3, "title": "Conclusion", "sections": []},
                ],
                "estimated_pages": 30,
            }

    def _build_generation_prompt(
        self,
        context: BuildContext,
        doc_type: str,
        settings: dict,
        outline: dict,
    ) -> str:
        """Build the prompt for generating the document."""
        brief = context.business_brief

        prompt_parts = [
            f"Create a complete {doc_type} based on this outline:",
            "",
            f"## Title: {outline.get('title', context.project_name)}",
            f"Subtitle: {outline.get('subtitle', '')}",
            "",
            "## Outline:",
        ]

        # Add chapters from outline
        for chapter in outline.get("chapters", []):
            prompt_parts.append(f"### Chapter {chapter.get('number', '')}: {chapter.get('title', '')}")
            if chapter.get("summary"):
                prompt_parts.append(f"   {chapter['summary']}")
            for section in chapter.get("sections", []):
                prompt_parts.append(f"   - {section}")
            prompt_parts.append("")

        # Add business brief context
        if brief:
            if brief.get("target_customer"):
                prompt_parts.append("## Target Reader:")
                prompt_parts.append(str(brief["target_customer"]))
                prompt_parts.append("")

        prompt_parts.extend([
            "## Document Requirements:",
            f"- Style: {settings['chapter_style']}",
            f"- Estimated length: {outline.get('estimated_pages', 30)} pages",
            "- Include ALL chapter content, not summaries",
            "- Write actual content for each section",
            "- Use professional, engaging language",
            "",
            "## Structure:",
            "1. Title page with title and subtitle",
            "2. Table of contents with linked chapters",
            "3. All chapters with full content",
            "4. Each chapter should be 1000-2000 words",
            "",
            "Generate complete HTML with embedded CSS.",
            "Use <div class='chapter'> for each chapter.",
            "Use proper heading hierarchy (h1 for title, h2 for chapters, h3 for sections).",
            "Output HTML code only, no explanations.",
        ])

        return "\n".join(prompt_parts)

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

    def _wrap_html(self, content: str, context: BuildContext, settings: dict) -> str:
        """Wrap content in a complete HTML document."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{context.project_name}</title>
    <style>
        @page {{
            size: 6in 9in;
            margin: 0.75in 0.75in 1in 0.75in;
            @bottom-center {{
                content: counter(page);
            }}
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: {settings['font_family']}, Georgia, serif;
            font-size: {settings['body_font_size']}pt;
            line-height: 1.6;
            color: #333;
            max-width: 6in;
            margin: 0 auto;
            padding: 1in;
        }}

        h1, h2, h3 {{
            font-family: {settings['heading_font']}, -apple-system, sans-serif;
            line-height: 1.2;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}

        h1 {{
            font-size: 28pt;
            text-align: center;
            page-break-before: always;
            page-break-after: avoid;
        }}

        h2 {{
            font-size: 20pt;
            border-bottom: 1px solid #ddd;
            padding-bottom: 0.3em;
        }}

        h3 {{
            font-size: 14pt;
            color: #555;
        }}

        p {{
            margin-bottom: 1em;
            text-align: justify;
            text-indent: 1.5em;
        }}

        p:first-of-type {{
            text-indent: 0;
        }}

        .title-page {{
            text-align: center;
            padding-top: 3in;
            page-break-after: always;
        }}

        .title-page h1 {{
            font-size: 36pt;
            margin-bottom: 0.5em;
            page-break-before: auto;
        }}

        .title-page .subtitle {{
            font-size: 18pt;
            color: #666;
            margin-bottom: 2em;
        }}

        .toc {{
            page-break-after: always;
        }}

        .toc h2 {{
            text-align: center;
            border: none;
        }}

        .toc ul {{
            list-style: none;
            padding: 0;
        }}

        .toc li {{
            margin: 0.5em 0;
            display: flex;
            justify-content: space-between;
        }}

        .toc a {{
            color: inherit;
            text-decoration: none;
        }}

        .chapter {{
            page-break-before: always;
        }}

        @media print {{
            body {{
                print-color-adjust: exact;
            }}
        }}
    </style>
</head>
<body>
{content}
</body>
</html>"""

    def _generate_preview_html(self, html_content: str, context: BuildContext) -> str:
        """Generate preview HTML with reader-like interface."""
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
            background: #2c2c2c;
            font-family: -apple-system, sans-serif;
            min-height: 100vh;
        }}
        .reader-header {{
            background: #1a1a1a;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: white;
        }}
        .reader-title {{
            font-size: 16px;
            font-weight: 500;
        }}
        .reader-actions button {{
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-left: 10px;
            background: #4CAF50;
            color: white;
        }}
        .reader-frame {{
            background: white;
            max-width: 700px;
            margin: 0 auto;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        iframe {{
            width: 100%;
            height: 85vh;
            border: none;
        }}
    </style>
</head>
<body>
    <div class="reader-header">
        <span class="reader-title">{context.project_name}</span>
        <div class="reader-actions">
            <button onclick="window.frames['content'].print()">Export PDF</button>
        </div>
    </div>
    <div class="reader-frame">
        <iframe name="content" srcdoc="{html_content.replace('"', '&quot;')}"></iframe>
    </div>
</body>
</html>"""
