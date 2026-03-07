"""Request/response logging middleware for ATLAS Web."""

import logging
import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("atlas.web.middleware.logging")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses.

    Features:
    - Assigns unique request ID to each request
    - Logs request method, path, and timing
    - Logs response status code
    - Excludes sensitive headers and paths
    - Adds request ID to response headers
    """

    # Paths to exclude from detailed logging (high-frequency endpoints)
    EXCLUDED_PATHS = {
        "/health",
        "/api/health",
        "/static",
        "/favicon.ico",
    }

    # Headers to exclude from logging (sensitive data)
    EXCLUDED_HEADERS = {
        "authorization",
        "cookie",
        "x-api-key",
        "api-key",
    }

    def __init__(
        self,
        app,
        log_request_body: bool = False,
        log_response_body: bool = False,
        slow_request_threshold_ms: int = 1000,
    ):
        """Initialize logging middleware.

        Args:
            app: FastAPI application
            log_request_body: Whether to log request bodies (careful with sensitive data)
            log_response_body: Whether to log response bodies
            slow_request_threshold_ms: Threshold for logging slow requests as warnings
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.slow_request_threshold_ms = slow_request_threshold_ms

    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        return str(uuid.uuid4())[:8]

    def _should_log(self, path: str) -> bool:
        """Check if request should be logged."""
        for excluded in self.EXCLUDED_PATHS:
            if path.startswith(excluded):
                return False
        return True

    def _sanitize_headers(self, headers: dict) -> dict:
        """Remove sensitive headers from logging."""
        return {
            k: v for k, v in headers.items()
            if k.lower() not in self.EXCLUDED_HEADERS
        }

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, handling proxies."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = self._generate_request_id()

        # Store request ID in state for use by handlers
        request.state.request_id = request_id

        # Get request details
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""
        client_ip = self._get_client_ip(request)

        # Start timing
        start_time = time.time()

        # Log request if not excluded
        should_log = self._should_log(path)
        if should_log:
            log_data = {
                "request_id": request_id,
                "method": method,
                "path": path,
                "client_ip": client_ip,
            }
            if query:
                log_data["query"] = query

            logger.info(f"Request started: {method} {path}", extra=log_data)

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Request failed: {method} {path} - {e}",
                extra={
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log response
        if should_log:
            status_code = response.status_code
            log_level = logging.INFO

            # Use warning for slow requests
            if duration_ms > self.slow_request_threshold_ms:
                log_level = logging.WARNING

            # Use warning for client errors, error for server errors
            if 400 <= status_code < 500:
                log_level = logging.WARNING
            elif status_code >= 500:
                log_level = logging.ERROR

            logger.log(
                log_level,
                f"Request completed: {method} {path} - {status_code} ({duration_ms}ms)",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                },
            )

        return response


class StructuredLogger:
    """Helper for structured logging with context."""

    def __init__(self, request: Request):
        """Initialize with request context.

        Args:
            request: Current request
        """
        self.request = request
        self.request_id = getattr(request.state, "request_id", "unknown")

    def _log(self, level: int, message: str, **kwargs):
        """Log with request context."""
        extra = {"request_id": self.request_id, **kwargs}
        logger.log(level, message, extra=extra)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)


def get_logger(request: Request) -> StructuredLogger:
    """Get a structured logger for the current request.

    Args:
        request: Current request

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(request)
