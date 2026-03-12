"""PDF Generation Utility for Physical Products.

Converts HTML templates to print-ready PDFs.
"""

import logging
import os
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("atlas.utils.pdf_generator")


class PDFGenerator:
    """Generate PDFs from HTML templates."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize PDF generator.

        Args:
            output_dir: Directory for output PDFs. Defaults to ~/atlas-output/pdfs
        """
        if output_dir is None:
            output_dir = Path.home() / "atlas-output" / "pdfs"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def html_to_pdf(self, html_content: str, output_name: str) -> Optional[Path]:
        """Convert HTML string to PDF.

        Args:
            html_content: HTML content to convert
            output_name: Name for output PDF (without extension)

        Returns:
            Path to generated PDF, or None if failed
        """
        try:
            from weasyprint import HTML, CSS
        except ImportError:
            logger.warning("weasyprint not installed. Install with: pip install weasyprint")
            return self._fallback_save_html(html_content, output_name)

        try:
            output_path = self.output_dir / f"{output_name}.pdf"

            # Create PDF from HTML
            html = HTML(string=html_content)
            html.write_pdf(output_path)

            logger.info(f"Generated PDF: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return self._fallback_save_html(html_content, output_name)

    def _fallback_save_html(self, html_content: str, output_name: str) -> Path:
        """Save HTML file as fallback when PDF generation fails.

        Args:
            html_content: HTML content
            output_name: Name for output file

        Returns:
            Path to saved HTML file
        """
        output_path = self.output_dir / f"{output_name}.html"
        output_path.write_text(html_content)
        logger.info(f"Saved HTML (open in browser and print to PDF): {output_path}")
        return output_path

    def extract_html_from_build(self, build_output: str) -> List[dict]:
        """Extract HTML code blocks from Tinker's build output.

        Args:
            build_output: Tinker's build output containing HTML code blocks

        Returns:
            List of dicts with 'filename' and 'content' keys
        """
        html_files = []
        import re

        # Pattern to match HTML code blocks with optional filename
        # Matches: ### `filename.html` or ```html or ```HTML
        pattern = r'(?:###\s*`([^`]+\.html)`\s*\n)?```(?:html|HTML)\n(.*?)```'

        matches = re.findall(pattern, build_output, re.DOTALL | re.IGNORECASE)

        for i, (filename, content) in enumerate(matches):
            if not filename:
                filename = f"page_{i+1}.html"
            html_files.append({
                "filename": filename,
                "content": content.strip()
            })

        return html_files

    def generate_all_pdfs(self, build_output: str, project_name: str = "planner") -> List[Path]:
        """Generate PDFs from all HTML in build output.

        Args:
            build_output: Tinker's build output
            project_name: Name for the project (used in filenames)

        Returns:
            List of paths to generated PDFs/HTMLs
        """
        html_files = self.extract_html_from_build(build_output)
        output_paths = []

        if not html_files:
            logger.warning("No HTML code blocks found in build output")
            return output_paths

        # Create project subdirectory
        project_dir = self.output_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        for html_file in html_files:
            filename = html_file["filename"].replace(".html", "")
            content = html_file["content"]

            # Ensure it's a complete HTML document
            if not content.strip().startswith("<!DOCTYPE") and not content.strip().startswith("<html"):
                content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{filename}</title>
    <style>
        @page {{ size: letter; margin: 0.5in; }}
        @media print {{ .page {{ page-break-after: always; }} }}
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; }}
    </style>
</head>
<body>
{content}
</body>
</html>"""

            # Save to project directory
            output_path = project_dir / f"{filename}.html"
            output_path.write_text(content)
            output_paths.append(output_path)

            # Try PDF conversion
            try:
                from weasyprint import HTML
                pdf_path = project_dir / f"{filename}.pdf"
                HTML(string=content).write_pdf(pdf_path)
                output_paths.append(pdf_path)
                logger.info(f"Generated: {pdf_path}")
            except ImportError:
                logger.info(f"Saved HTML (use browser Print > Save as PDF): {output_path}")
            except Exception as e:
                logger.warning(f"PDF conversion failed for {filename}: {e}")

        return output_paths


def get_pdf_generator(output_dir: Optional[Path] = None) -> PDFGenerator:
    """Get a PDF generator instance."""
    return PDFGenerator(output_dir)
