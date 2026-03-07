"""Tests for rate limiting middleware."""

import pytest
from unittest.mock import MagicMock
import time

from atlas.web.middleware.rate_limit import (
    RateLimiter,
    RateLimitConfig,
)


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.fixture
    def limiter(self):
        """Create a rate limiter with low limits for testing."""
        config = RateLimitConfig(
            requests_per_minute=5,
            requests_per_hour=100,
            burst_size=2,
            excluded_paths=["/health"],
            strict_paths={"/api/task": 2},
        )
        return RateLimiter(config)

    def _make_request(self, path: str = "/api/test", client_ip: str = "127.0.0.1"):
        """Create a mock request."""
        request = MagicMock()
        request.url.path = path
        request.headers.get.return_value = None
        request.client.host = client_ip
        return request

    def test_allows_requests_under_limit(self, limiter):
        """Test that requests under limit are allowed."""
        request = self._make_request()

        for _ in range(5):
            is_allowed, headers = limiter.check_rate_limit(request)
            assert is_allowed is True
            assert "X-RateLimit-Limit" in headers

    def test_blocks_requests_over_limit(self, limiter):
        """Test that requests over limit are blocked."""
        request = self._make_request()

        # Use up the limit (5) + burst (2)
        for _ in range(7):
            limiter.check_rate_limit(request)

        # This should be blocked
        is_allowed, headers = limiter.check_rate_limit(request)
        assert is_allowed is False
        assert "Retry-After" in headers

    def test_excludes_configured_paths(self, limiter):
        """Test that excluded paths bypass rate limiting."""
        request = self._make_request(path="/health")

        # Should always be allowed
        for _ in range(100):
            is_allowed, headers = limiter.check_rate_limit(request)
            assert is_allowed is True
            assert headers == {}

    def test_strict_paths_have_lower_limits(self, limiter):
        """Test that strict paths have lower limits."""
        request = self._make_request(path="/api/task")

        # Use up the strict limit (2) + burst (2)
        for _ in range(4):
            limiter.check_rate_limit(request)

        # This should be blocked
        is_allowed, _ = limiter.check_rate_limit(request)
        assert is_allowed is False

    def test_different_clients_have_separate_limits(self, limiter):
        """Test that different clients have separate limits."""
        request1 = self._make_request(client_ip="192.168.1.1")
        request2 = self._make_request(client_ip="192.168.1.2")

        # Use up limit for client 1
        for _ in range(7):
            limiter.check_rate_limit(request1)

        # Client 2 should still be allowed
        is_allowed, _ = limiter.check_rate_limit(request2)
        assert is_allowed is True

        # Client 1 should be blocked
        is_allowed, _ = limiter.check_rate_limit(request1)
        assert is_allowed is False

    def test_rate_limit_headers(self, limiter):
        """Test that rate limit headers are correct."""
        request = self._make_request()

        is_allowed, headers = limiter.check_rate_limit(request)

        assert headers["X-RateLimit-Limit"] == "5"
        assert headers["X-RateLimit-Remaining"] == "4"
        assert "X-RateLimit-Reset" in headers

    def test_forwarded_header_used_for_client_key(self, limiter):
        """Test that X-Forwarded-For header is used for client identification."""
        request = MagicMock()
        request.url.path = "/api/test"
        request.headers.get.return_value = "10.0.0.1, 192.168.1.1"
        request.client.host = "127.0.0.1"

        key = limiter._get_client_key(request)
        assert key == "10.0.0.1"


class TestRateLimitConfig:
    """Test RateLimitConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig()

        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.burst_size == 10
        assert "/health" in config.excluded_paths

    def test_custom_config(self):
        """Test custom configuration."""
        config = RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=500,
            burst_size=5,
        )

        assert config.requests_per_minute == 30
        assert config.requests_per_hour == 500
        assert config.burst_size == 5
