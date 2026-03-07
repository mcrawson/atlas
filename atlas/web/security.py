"""Security utilities for ATLAS Web.

Provides input sanitization and XSS prevention utilities.
"""

import html
import re
import logging
from typing import Any, Optional
from functools import lru_cache

logger = logging.getLogger("atlas.web.security")


# Patterns for dangerous content
SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
EVENT_HANDLER_PATTERN = re.compile(r"\bon\w+\s*=", re.IGNORECASE)
JAVASCRIPT_URL_PATTERN = re.compile(r"javascript:", re.IGNORECASE)
DATA_URL_PATTERN = re.compile(r"data:\s*text/html", re.IGNORECASE)
STYLE_EXPRESSION_PATTERN = re.compile(r"expression\s*\(", re.IGNORECASE)


def escape_html(text: str) -> str:
    """Escape HTML special characters.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for HTML rendering
    """
    if not isinstance(text, str):
        text = str(text)
    return html.escape(text, quote=True)


def sanitize_html(text: str, allow_basic_formatting: bool = False) -> str:
    """Sanitize HTML content, removing dangerous elements.

    Args:
        text: Text to sanitize
        allow_basic_formatting: If True, allow basic formatting tags (b, i, em, strong, code)

    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        text = str(text)

    # Remove script tags
    text = SCRIPT_PATTERN.sub("", text)

    # Remove event handlers
    text = EVENT_HANDLER_PATTERN.sub("", text)

    # Remove javascript: URLs
    text = JAVASCRIPT_URL_PATTERN.sub("", text)

    # Remove data: URLs with HTML
    text = DATA_URL_PATTERN.sub("", text)

    # Remove CSS expression()
    text = STYLE_EXPRESSION_PATTERN.sub("", text)

    if allow_basic_formatting:
        # Allow only safe tags by escaping everything else
        # This is a simple approach - for complex needs, use bleach library
        safe_tags = {"b", "i", "em", "strong", "code", "pre", "br"}
        # For now, just escape - proper allowlisting requires a parser
        text = escape_html(text)
    else:
        text = escape_html(text)

    return text


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal attacks.

    Args:
        filename: Filename to sanitize

    Returns:
        Safe filename
    """
    if not isinstance(filename, str):
        filename = str(filename)

    # Remove path separators and null bytes
    filename = filename.replace("/", "_")
    filename = filename.replace("\\", "_")
    filename = filename.replace("\x00", "")

    # Remove leading dots (prevent hidden files)
    filename = filename.lstrip(".")

    # Remove potentially dangerous extensions
    dangerous_extensions = {".exe", ".sh", ".bat", ".cmd", ".ps1", ".php", ".jsp"}
    lower_name = filename.lower()
    for ext in dangerous_extensions:
        if lower_name.endswith(ext):
            filename = filename[:-len(ext)] + ".txt"
            break

    # Limit length
    if len(filename) > 255:
        filename = filename[:255]

    # Default if empty
    if not filename:
        filename = "unnamed"

    return filename


def sanitize_url(url: str) -> Optional[str]:
    """Sanitize a URL, rejecting dangerous protocols.

    Args:
        url: URL to sanitize

    Returns:
        Sanitized URL or None if dangerous
    """
    if not isinstance(url, str):
        return None

    url = url.strip()

    # Reject javascript: and data: URLs
    lower_url = url.lower()
    if lower_url.startswith("javascript:"):
        logger.warning(f"Rejected javascript URL: {url[:50]}")
        return None
    if lower_url.startswith("data:"):
        logger.warning(f"Rejected data URL: {url[:50]}")
        return None
    if lower_url.startswith("vbscript:"):
        logger.warning(f"Rejected vbscript URL: {url[:50]}")
        return None

    # Allow http, https, mailto, tel, and relative URLs
    allowed_schemes = {"http://", "https://", "mailto:", "tel:", "/", "#"}
    if not any(lower_url.startswith(scheme) for scheme in allowed_schemes):
        # Check if it's a relative URL (no scheme)
        if "://" in url:
            logger.warning(f"Rejected URL with unknown scheme: {url[:50]}")
            return None

    return url


def sanitize_dict(data: dict[str, Any], keys_to_sanitize: Optional[set[str]] = None) -> dict[str, Any]:
    """Recursively sanitize string values in a dictionary.

    Args:
        data: Dictionary to sanitize
        keys_to_sanitize: Optional set of keys to sanitize (if None, sanitize all strings)

    Returns:
        Sanitized dictionary
    """
    result = {}

    for key, value in data.items():
        if isinstance(value, str):
            if keys_to_sanitize is None or key in keys_to_sanitize:
                result[key] = escape_html(value)
            else:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, keys_to_sanitize)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item, keys_to_sanitize) if isinstance(item, dict)
                else escape_html(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            result[key] = value

    return result


class ContentSecurityPolicy:
    """Helper for generating Content-Security-Policy headers."""

    def __init__(self):
        """Initialize with default secure policy."""
        self._directives = {
            "default-src": ["'self'"],
            "script-src": ["'self'"],
            "style-src": ["'self'", "'unsafe-inline'"],  # Required for HTMX
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'"],
            "connect-src": ["'self'", "ws:", "wss:"],  # WebSocket support
            "frame-ancestors": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
        }

    def add_source(self, directive: str, source: str) -> "ContentSecurityPolicy":
        """Add a source to a directive.

        Args:
            directive: CSP directive (e.g., 'script-src')
            source: Source to add (e.g., 'https://cdn.example.com')

        Returns:
            Self for chaining
        """
        if directive not in self._directives:
            self._directives[directive] = []
        if source not in self._directives[directive]:
            self._directives[directive].append(source)
        return self

    def to_header(self) -> str:
        """Generate the CSP header value.

        Returns:
            CSP header string
        """
        parts = []
        for directive, sources in self._directives.items():
            parts.append(f"{directive} {' '.join(sources)}")
        return "; ".join(parts)


# Default CSP instance
default_csp = ContentSecurityPolicy()


def get_security_headers() -> dict[str, str]:
    """Get recommended security headers for responses.

    Returns:
        Dictionary of security headers
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": default_csp.to_header(),
    }
