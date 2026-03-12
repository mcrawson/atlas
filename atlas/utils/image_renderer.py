"""Image Renderer Utility for HTML to Image Conversion.

Uses Playwright to render HTML content to PNG images.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("atlas.utils.image_renderer")


class ImageRenderer:
    """Render HTML content to images using Playwright."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize image renderer.

        Args:
            output_dir: Directory for output images. Defaults to ~/atlas-output/images
        """
        if output_dir is None:
            output_dir = Path.home() / "atlas-output" / "images"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def render_html_to_images(
        self,
        html_files: list[dict],
        width: int = 816,
        height: int = 1056,
        scale: float = 2.0,
    ) -> list[Path]:
        """Render HTML content to PNG images.

        Args:
            html_files: List of dicts with 'filename' and 'content' keys
                        (from extract_html_from_build())
            width: Viewport width in pixels (default 816 for letter at 96 DPI)
            height: Viewport height in pixels (default 1056 for letter at 96 DPI)
            scale: Device scale factor for higher resolution (default 2.0 for retina)

        Returns:
            List of paths to generated PNG images
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("playwright not installed. Install with: pip install playwright && playwright install chromium")
            raise ImportError("playwright is required for image rendering")

        output_paths = []

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=scale,
            )

            for i, html_file in enumerate(html_files):
                filename = html_file.get("filename", f"page_{i+1}.html")
                content = html_file.get("content", "")

                if not content:
                    logger.warning(f"Empty content for {filename}, skipping")
                    continue

                # Ensure it's a complete HTML document
                if not content.strip().startswith("<!DOCTYPE") and not content.strip().startswith("<html"):
                    content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{filename}</title>
    <style>
        @page {{ size: letter; margin: 0; }}
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, sans-serif; }}
        * {{ box-sizing: border-box; }}
    </style>
</head>
<body>
{content}
</body>
</html>"""

                page = await context.new_page()

                # Create a temporary HTML file to load
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".html", delete=False, encoding="utf-8"
                ) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                try:
                    # Load the HTML
                    await page.goto(f"file://{tmp_path}", wait_until="networkidle")

                    # Wait for any fonts to load
                    await page.wait_for_timeout(500)

                    # Generate output filename
                    base_name = filename.replace(".html", "")
                    output_path = self.output_dir / f"{base_name}.png"

                    # Take screenshot
                    await page.screenshot(
                        path=str(output_path),
                        full_page=False,
                        type="png",
                    )

                    output_paths.append(output_path)
                    logger.info(f"Rendered image: {output_path}")

                finally:
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)
                    await page.close()

            await browser.close()

        return output_paths

    async def render_single_html(
        self,
        html_content: str,
        output_name: str,
        width: int = 816,
        height: int = 1056,
        scale: float = 2.0,
    ) -> Optional[Path]:
        """Render a single HTML string to an image.

        Args:
            html_content: HTML content to render
            output_name: Name for output file (without extension)
            width: Viewport width
            height: Viewport height
            scale: Device scale factor

        Returns:
            Path to generated PNG, or None if failed
        """
        html_files = [{"filename": f"{output_name}.html", "content": html_content}]

        try:
            paths = await self.render_html_to_images(
                html_files, width=width, height=height, scale=scale
            )
            return paths[0] if paths else None
        except Exception as e:
            logger.exception(f"Failed to render HTML: {e}")
            return None


async def render_html_to_images(
    html_files: list[dict],
    output_dir: Optional[Path] = None,
    width: int = 816,
    height: int = 1056,
) -> list[Path]:
    """Convenience function to render HTML files to images.

    Args:
        html_files: List of dicts with 'filename' and 'content' keys
        output_dir: Optional output directory
        width: Viewport width (default 816 for letter size at 96 DPI)
        height: Viewport height (default 1056 for letter size at 96 DPI)

    Returns:
        List of paths to generated images
    """
    renderer = ImageRenderer(output_dir)
    return await renderer.render_html_to_images(html_files, width, height)


def get_image_renderer(output_dir: Optional[Path] = None) -> ImageRenderer:
    """Get an image renderer instance."""
    return ImageRenderer(output_dir)
