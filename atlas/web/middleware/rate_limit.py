"""Rate limiting middleware for ATLAS API."""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("atlas.web.middleware.rate_limit")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Requests per window
    requests_per_minute: int = 120
    requests_per_hour: int = 3000

    # Burst allowance (extra requests allowed in short bursts)
    burst_size: int = 30

    # Paths to exclude from rate limiting
    excluded_paths: list[str] = field(default_factory=lambda: [
        "/health",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
        "/static",
        "/projects",  # Exclude project pages during development
        "/ws",        # Exclude WebSocket connections
    ])

    # Paths with stricter limits (expensive operations)
    strict_paths: dict[str, int] = field(default_factory=lambda: {
        "/api/task": 10,  # 10 per minute for task execution
    })


@dataclass
class ClientState:
    """Track rate limit state for a client."""

    minute_requests: int = 0
    minute_window_start: float = 0.0
    hour_requests: int = 0
    hour_window_start: float = 0.0
    burst_tokens: float = 0.0
    last_request: float = 0.0


class RateLimiter:
    """In-memory rate limiter using sliding window."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self._clients: dict[str, ClientState] = defaultdict(ClientState)
        self._cleanup_interval = 300  # Clean up stale entries every 5 minutes
        self._last_cleanup = time.time()

    def _get_client_key(self, request: Request) -> str:
        """Get unique identifier for the client.

        Args:
            request: The incoming request

        Returns:
            Client identifier (IP address or forwarded header)
        """
        # Check for forwarded header (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Fall back to client host
        if request.client:
            return request.client.host

        return "unknown"

    def _cleanup_stale_clients(self) -> None:
        """Remove stale client entries to prevent memory growth."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        stale_threshold = 3600  # 1 hour

        stale_clients = [
            key for key, state in self._clients.items()
            if now - state.last_request > stale_threshold
        ]

        for key in stale_clients:
            del self._clients[key]

        if stale_clients:
            logger.debug(f"Cleaned up {len(stale_clients)} stale rate limit entries")

    def _is_excluded(self, path: str) -> bool:
        """Check if path is excluded from rate limiting."""
        for excluded in self.config.excluded_paths:
            if path.startswith(excluded):
                return True
        return False

    def _get_path_limit(self, path: str) -> int:
        """Get the per-minute limit for a path."""
        for strict_path, limit in self.config.strict_paths.items():
            if path.startswith(strict_path):
                return limit
        return self.config.requests_per_minute

    def check_rate_limit(self, request: Request) -> tuple[bool, dict]:
        """Check if request should be rate limited.

        Args:
            request: The incoming request

        Returns:
            Tuple of (is_allowed, headers)
        """
        path = request.url.path

        # Skip excluded paths
        if self._is_excluded(path):
            return True, {}

        now = time.time()
        client_key = self._get_client_key(request)
        state = self._clients[client_key]

        # Cleanup occasionally
        self._cleanup_stale_clients()

        # Reset minute window if needed
        if now - state.minute_window_start >= 60:
            state.minute_requests = 0
            state.minute_window_start = now
            state.burst_tokens = min(
                self.config.burst_size,
                state.burst_tokens + self.config.burst_size
            )

        # Reset hour window if needed
        if now - state.hour_window_start >= 3600:
            state.hour_requests = 0
            state.hour_window_start = now

        # Get limit for this path
        minute_limit = self._get_path_limit(path)

        # Check limits
        is_allowed = True
        state.last_request = now

        # Check minute limit (allow burst)
        if state.minute_requests >= minute_limit:
            if state.burst_tokens > 0:
                state.burst_tokens -= 1
            else:
                is_allowed = False

        # Check hour limit
        if state.hour_requests >= self.config.requests_per_hour:
            is_allowed = False

        # Update counters if allowed
        if is_allowed:
            state.minute_requests += 1
            state.hour_requests += 1

        # Build rate limit headers
        headers = {
            "X-RateLimit-Limit": str(minute_limit),
            "X-RateLimit-Remaining": str(max(0, minute_limit - state.minute_requests)),
            "X-RateLimit-Reset": str(int(state.minute_window_start + 60)),
        }

        if not is_allowed:
            retry_after = int(state.minute_window_start + 60 - now)
            headers["Retry-After"] = str(max(1, retry_after))

        return is_allowed, headers


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, config: Optional[RateLimitConfig] = None):
        """Initialize middleware.

        Args:
            app: FastAPI application
            config: Rate limit configuration
        """
        super().__init__(app)
        self.limiter = RateLimiter(config)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through rate limiter.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response (either from handler or 429 error)
        """
        is_allowed, headers = self.limiter.check_rate_limit(request)

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {self.limiter._get_client_key(request)} "
                f"on {request.url.path}"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please slow down.",
                    "code": "RATE_LIMIT_EXCEEDED",
                },
                headers=headers,
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response
