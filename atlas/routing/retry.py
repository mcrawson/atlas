"""Retry logic with exponential backoff for provider calls."""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional, Set, Type, TypeVar

logger = logging.getLogger("atlas.routing.retry")

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    # Maximum number of retry attempts
    max_retries: int = 3

    # Initial delay between retries (seconds)
    initial_delay: float = 1.0

    # Maximum delay between retries (seconds)
    max_delay: float = 60.0

    # Multiplier for exponential backoff
    backoff_multiplier: float = 2.0

    # Add random jitter to prevent thundering herd
    jitter: bool = True

    # Jitter range (0.0 to 1.0)
    jitter_range: float = 0.25

    # Exception types that should trigger a retry
    retryable_exceptions: Set[Type[Exception]] = field(default_factory=lambda: {
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    })

    # HTTP status codes that should trigger a retry
    retryable_status_codes: Set[int] = field(default_factory=lambda: {
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    })


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


def calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """Calculate delay for the next retry attempt.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    # Exponential backoff
    delay = config.initial_delay * (config.backoff_multiplier ** attempt)

    # Cap at maximum delay
    delay = min(delay, config.max_delay)

    # Add jitter
    if config.jitter:
        jitter_amount = delay * config.jitter_range
        delay = delay + random.uniform(-jitter_amount, jitter_amount)

    return max(0, delay)


def is_retryable(
    exception: Exception,
    config: RetryConfig,
) -> bool:
    """Check if an exception should trigger a retry.

    Args:
        exception: The exception that occurred
        config: Retry configuration

    Returns:
        True if the exception is retryable
    """
    # Check exception type
    for exc_type in config.retryable_exceptions:
        if isinstance(exception, exc_type):
            return True

    # Check for rate limit in message
    error_msg = str(exception).lower()
    if "rate limit" in error_msg or "too many requests" in error_msg:
        return True

    # Check for timeout in message
    if "timeout" in error_msg or "timed out" in error_msg:
        return True

    # Check for connection errors
    if "connection" in error_msg and ("refused" in error_msg or "reset" in error_msg):
        return True

    return False


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    **kwargs,
) -> T:
    """Execute an async function with retry logic.

    Args:
        func: Async function to execute
        *args: Positional arguments for the function
        config: Retry configuration
        on_retry: Optional callback called on each retry (attempt, exception, delay)
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function

    Raises:
        RetryError: When all retry attempts are exhausted
    """
    config = config or RetryConfig()
    last_exception: Optional[Exception] = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            # Check if we should retry
            if attempt >= config.max_retries:
                logger.error(
                    f"All {config.max_retries + 1} attempts failed for {func.__name__}: {e}"
                )
                raise RetryError(
                    f"All retry attempts exhausted: {e}",
                    last_exception=e,
                )

            if not is_retryable(e, config):
                logger.debug(f"Exception is not retryable: {type(e).__name__}: {e}")
                raise

            # Calculate delay
            delay = calculate_delay(attempt, config)

            logger.warning(
                f"Attempt {attempt + 1}/{config.max_retries + 1} failed for {func.__name__}: {e}. "
                f"Retrying in {delay:.2f}s..."
            )

            # Call retry callback if provided
            if on_retry:
                on_retry(attempt, e, delay)

            # Wait before retry
            await asyncio.sleep(delay)

    # This should never be reached, but just in case
    raise RetryError(
        "Unexpected retry loop exit",
        last_exception=last_exception,
    )


def with_retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
):
    """Decorator to add retry logic to an async function.

    Args:
        config: Retry configuration
        on_retry: Optional callback called on each retry

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(
                func,
                *args,
                config=config,
                on_retry=on_retry,
                **kwargs,
            )
        return wrapper
    return decorator


class RetryableProvider:
    """Mixin to add retry logic to providers."""

    retry_config: RetryConfig = RetryConfig()

    async def _with_retry(
        self,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """Execute a function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of the function
        """
        return await retry_async(
            func,
            *args,
            config=self.retry_config,
            on_retry=self._on_retry,
            **kwargs,
        )

    def _on_retry(self, attempt: int, exception: Exception, delay: float) -> None:
        """Called on each retry attempt.

        Override in subclasses for custom behavior.

        Args:
            attempt: Current attempt number
            exception: The exception that triggered the retry
            delay: Delay before next attempt
        """
        pass
