"""Tests for security utilities."""

import pytest

from atlas.web.security import (
    escape_html,
    sanitize_html,
    sanitize_filename,
    sanitize_url,
    sanitize_dict,
    ContentSecurityPolicy,
    get_security_headers,
)


class TestEscapeHtml:
    """Test escape_html function."""

    def test_escapes_angle_brackets(self):
        """Test that angle brackets are escaped."""
        assert escape_html("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

    def test_escapes_quotes(self):
        """Test that quotes are escaped."""
        assert escape_html('"test"') == "&quot;test&quot;"
        assert escape_html("'test'") == "&#x27;test&#x27;"

    def test_escapes_ampersand(self):
        """Test that ampersand is escaped."""
        assert escape_html("foo & bar") == "foo &amp; bar"

    def test_handles_non_string(self):
        """Test that non-strings are converted."""
        assert escape_html(123) == "123"
        assert escape_html(None) == "None"


class TestSanitizeHtml:
    """Test sanitize_html function."""

    def test_removes_script_tags(self):
        """Test that script tags are removed."""
        result = sanitize_html("<script>alert('xss')</script>Hello")
        assert "script" not in result.lower()
        assert "Hello" in result

    def test_removes_event_handlers(self):
        """Test that event handlers are removed."""
        result = sanitize_html('<img src="x" onerror="alert(1)">')
        assert "onerror" not in result.lower()

    def test_removes_javascript_urls(self):
        """Test that javascript: URLs are removed."""
        result = sanitize_html('<a href="javascript:alert(1)">click</a>')
        assert "javascript:" not in result.lower()

    def test_escapes_remaining_html(self):
        """Test that remaining HTML is escaped."""
        result = sanitize_html("<div>Hello</div>")
        assert "&lt;div&gt;" in result


class TestSanitizeFilename:
    """Test sanitize_filename function."""

    def test_removes_path_separators(self):
        """Test that path separators are replaced."""
        assert "/" not in sanitize_filename("../../../etc/passwd")
        assert "\\" not in sanitize_filename("..\\..\\windows\\system32")

    def test_removes_leading_dots(self):
        """Test that leading dots are removed."""
        result = sanitize_filename("...htaccess")
        assert not result.startswith(".")

    def test_replaces_dangerous_extensions(self):
        """Test that dangerous extensions are replaced."""
        assert sanitize_filename("malware.exe").endswith(".txt")
        assert sanitize_filename("script.sh").endswith(".txt")
        assert sanitize_filename("normal.pdf").endswith(".pdf")

    def test_limits_length(self):
        """Test that filename length is limited."""
        long_name = "a" * 500 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_handles_empty_filename(self):
        """Test that empty filename gets default."""
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("...") == "unnamed"


class TestSanitizeUrl:
    """Test sanitize_url function."""

    def test_allows_http_urls(self):
        """Test that HTTP URLs are allowed."""
        assert sanitize_url("http://example.com") == "http://example.com"
        assert sanitize_url("https://example.com") == "https://example.com"

    def test_allows_relative_urls(self):
        """Test that relative URLs are allowed."""
        assert sanitize_url("/path/to/page") == "/path/to/page"
        assert sanitize_url("#section") == "#section"

    def test_rejects_javascript_urls(self):
        """Test that javascript: URLs are rejected."""
        assert sanitize_url("javascript:alert(1)") is None
        assert sanitize_url("JAVASCRIPT:alert(1)") is None

    def test_rejects_data_urls(self):
        """Test that data: URLs are rejected."""
        assert sanitize_url("data:text/html,<script>alert(1)</script>") is None

    def test_rejects_unknown_schemes(self):
        """Test that unknown schemes are rejected."""
        assert sanitize_url("file:///etc/passwd") is None
        assert sanitize_url("ftp://example.com") is None


class TestSanitizeDict:
    """Test sanitize_dict function."""

    def test_sanitizes_string_values(self):
        """Test that string values are sanitized."""
        data = {"name": "<script>alert(1)</script>"}
        result = sanitize_dict(data)
        assert "script" not in result["name"].lower() or "&lt;" in result["name"]

    def test_handles_nested_dicts(self):
        """Test that nested dicts are sanitized."""
        data = {"user": {"name": "<b>Test</b>"}}
        result = sanitize_dict(data)
        assert "&lt;" in result["user"]["name"]

    def test_handles_lists(self):
        """Test that lists are sanitized."""
        data = {"tags": ["<script>", "normal"]}
        result = sanitize_dict(data)
        assert "&lt;" in result["tags"][0]
        assert result["tags"][1] == "normal"

    def test_preserves_non_strings(self):
        """Test that non-string values are preserved."""
        data = {"count": 42, "active": True, "price": 19.99}
        result = sanitize_dict(data)
        assert result["count"] == 42
        assert result["active"] is True
        assert result["price"] == 19.99

    def test_selective_sanitization(self):
        """Test that only specified keys are sanitized."""
        data = {"name": "<b>Test</b>", "code": "<html>"}
        result = sanitize_dict(data, keys_to_sanitize={"name"})
        assert "&lt;" in result["name"]
        assert result["code"] == "<html>"


class TestContentSecurityPolicy:
    """Test ContentSecurityPolicy class."""

    def test_default_policy(self):
        """Test default CSP has secure defaults."""
        csp = ContentSecurityPolicy()
        header = csp.to_header()

        assert "default-src 'self'" in header
        assert "frame-ancestors 'none'" in header

    def test_add_source(self):
        """Test adding sources to directives."""
        csp = ContentSecurityPolicy()
        csp.add_source("script-src", "https://cdn.example.com")

        header = csp.to_header()
        assert "https://cdn.example.com" in header

    def test_chaining(self):
        """Test that add_source supports chaining."""
        csp = ContentSecurityPolicy()
        result = csp.add_source("script-src", "https://a.com").add_source("style-src", "https://b.com")
        assert result is csp


class TestGetSecurityHeaders:
    """Test get_security_headers function."""

    def test_includes_required_headers(self):
        """Test that all required security headers are included."""
        headers = get_security_headers()

        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Content-Security-Policy" in headers

    def test_header_values(self):
        """Test that header values are correct."""
        headers = get_security_headers()

        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
