"""Tests for request logging middleware."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from atlas.web.app import create_app
from atlas.web.middleware.logging import (
    RequestLoggingMiddleware,
    StructuredLogger,
    get_logger,
)


class TestRequestLoggingMiddleware:
    """Test RequestLoggingMiddleware class."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_adds_request_id_header(self, client):
        """Test that request ID is added to response headers."""
        response = client.get("/api/status")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 8

    def test_request_id_is_unique(self, client):
        """Test that each request gets a unique ID."""
        response1 = client.get("/api/status")
        response2 = client.get("/api/status")

        id1 = response1.headers["X-Request-ID"]
        id2 = response2.headers["X-Request-ID"]

        assert id1 != id2

    def test_excluded_paths_still_work(self, client):
        """Test that excluded paths still function normally."""
        response = client.get("/api/health")
        assert response.status_code == 200


class TestRequestLoggingMiddlewareHelpers:
    """Test helper functions in logging middleware."""

    def test_should_log_regular_path(self):
        """Test that regular paths should be logged."""
        middleware = RequestLoggingMiddleware(MagicMock())
        assert middleware._should_log("/api/tasks") is True
        assert middleware._should_log("/projects/1") is True

    def test_should_not_log_excluded_paths(self):
        """Test that excluded paths are not logged."""
        middleware = RequestLoggingMiddleware(MagicMock())
        assert middleware._should_log("/health") is False
        assert middleware._should_log("/static/js/app.js") is False
        assert middleware._should_log("/api/health") is False

    def test_sanitize_headers(self):
        """Test that sensitive headers are removed."""
        middleware = RequestLoggingMiddleware(MagicMock())

        headers = {
            "content-type": "application/json",
            "authorization": "Bearer secret-token",
            "x-api-key": "secret-key",
            "user-agent": "test-client",
        }

        sanitized = middleware._sanitize_headers(headers)

        assert "content-type" in sanitized
        assert "user-agent" in sanitized
        assert "authorization" not in sanitized
        assert "x-api-key" not in sanitized

    def test_generate_request_id(self):
        """Test request ID generation."""
        middleware = RequestLoggingMiddleware(MagicMock())

        id1 = middleware._generate_request_id()
        id2 = middleware._generate_request_id()

        assert len(id1) == 8
        assert len(id2) == 8
        assert id1 != id2

    def test_get_client_ip_direct(self):
        """Test getting client IP from direct connection."""
        middleware = RequestLoggingMiddleware(MagicMock())

        request = MagicMock()
        request.headers.get.return_value = None
        request.client.host = "192.168.1.100"

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_forwarded(self):
        """Test getting client IP from forwarded header."""
        middleware = RequestLoggingMiddleware(MagicMock())

        request = MagicMock()
        request.headers.get.return_value = "10.0.0.1, 192.168.1.1"

        ip = middleware._get_client_ip(request)
        assert ip == "10.0.0.1"


class TestStructuredLogger:
    """Test StructuredLogger class."""

    def test_creates_with_request_id(self):
        """Test logger creation with request ID."""
        request = MagicMock()
        request.state.request_id = "abc12345"

        slogger = StructuredLogger(request)
        assert slogger.request_id == "abc12345"

    def test_handles_missing_request_id(self):
        """Test logger handles missing request ID."""
        request = MagicMock(spec=[])
        request.state = MagicMock(spec=[])

        slogger = StructuredLogger(request)
        assert slogger.request_id == "unknown"


class TestGetLogger:
    """Test get_logger function."""

    def test_returns_structured_logger(self):
        """Test that get_logger returns a StructuredLogger."""
        request = MagicMock()
        request.state.request_id = "test123"

        slogger = get_logger(request)

        assert isinstance(slogger, StructuredLogger)
        assert slogger.request_id == "test123"
