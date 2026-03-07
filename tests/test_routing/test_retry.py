"""Tests for retry logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from atlas.routing.retry import (
    RetryConfig,
    RetryError,
    calculate_delay,
    is_retryable,
    retry_async,
    with_retry,
)


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.5,
            max_delay=30.0,
        )

        assert config.max_retries == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 30.0


class TestCalculateDelay:
    """Test calculate_delay function."""

    def test_exponential_backoff(self):
        """Test that delay increases exponentially."""
        config = RetryConfig(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            jitter=False,
        )

        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 4.0
        assert calculate_delay(3, config) == 8.0

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            initial_delay=1.0,
            backoff_multiplier=10.0,
            max_delay=5.0,
            jitter=False,
        )

        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 5.0  # Capped
        assert calculate_delay(2, config) == 5.0  # Capped

    def test_jitter_adds_variation(self):
        """Test that jitter adds variation to delay."""
        config = RetryConfig(
            initial_delay=1.0,
            jitter=True,
            jitter_range=0.25,
        )

        # Get multiple delays
        delays = [calculate_delay(0, config) for _ in range(10)]

        # They should not all be the same
        assert len(set(delays)) > 1

        # They should be within the jitter range
        for delay in delays:
            assert 0.75 <= delay <= 1.25


class TestIsRetryable:
    """Test is_retryable function."""

    @pytest.fixture
    def config(self):
        """Create default config."""
        return RetryConfig()

    def test_connection_error_is_retryable(self, config):
        """Test that ConnectionError is retryable."""
        assert is_retryable(ConnectionError("Connection refused"), config) is True

    def test_timeout_error_is_retryable(self, config):
        """Test that TimeoutError is retryable."""
        assert is_retryable(TimeoutError("Request timed out"), config) is True

    def test_rate_limit_message_is_retryable(self, config):
        """Test that rate limit errors are retryable."""
        assert is_retryable(Exception("Rate limit exceeded"), config) is True
        assert is_retryable(Exception("Too many requests"), config) is True

    def test_value_error_is_not_retryable(self, config):
        """Test that ValueError is not retryable."""
        assert is_retryable(ValueError("Invalid input"), config) is False

    def test_generic_error_is_not_retryable(self, config):
        """Test that generic errors are not retryable."""
        assert is_retryable(Exception("Something went wrong"), config) is False


class TestRetryAsync:
    """Test retry_async function."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """Test successful execution on first try."""
        func = AsyncMock(return_value="success")

        result = await retry_async(func)

        assert result == "success"
        assert func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry after failure."""
        func = AsyncMock(side_effect=[
            ConnectionError("Connection refused"),
            "success",
        ])

        config = RetryConfig(initial_delay=0.01)
        result = await retry_async(func, config=config)

        assert result == "success"
        assert func.call_count == 2

    @pytest.mark.asyncio
    async def test_exhaust_retries(self):
        """Test that RetryError is raised when retries are exhausted."""
        func = AsyncMock(side_effect=ConnectionError("Connection refused"))

        config = RetryConfig(max_retries=2, initial_delay=0.01)

        with pytest.raises(RetryError) as exc_info:
            await retry_async(func, config=config)

        assert func.call_count == 3  # Initial + 2 retries
        assert exc_info.value.last_exception is not None

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(self):
        """Test that non-retryable errors are raised immediately."""
        func = AsyncMock(side_effect=ValueError("Invalid input"))

        config = RetryConfig(initial_delay=0.01)

        with pytest.raises(ValueError):
            await retry_async(func, config=config)

        assert func.call_count == 1

    @pytest.mark.asyncio
    async def test_on_retry_callback(self):
        """Test that on_retry callback is called."""
        func = AsyncMock(side_effect=[
            ConnectionError("Connection refused"),
            "success",
        ])
        on_retry = MagicMock()

        config = RetryConfig(initial_delay=0.01)
        await retry_async(func, config=config, on_retry=on_retry)

        assert on_retry.call_count == 1
        call_args = on_retry.call_args[0]
        assert call_args[0] == 0  # First retry attempt
        assert isinstance(call_args[1], ConnectionError)


class TestWithRetryDecorator:
    """Test with_retry decorator."""

    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Test decorator with successful function."""
        @with_retry()
        async def my_func():
            return "success"

        result = await my_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_with_retry(self):
        """Test decorator retries on failure."""
        call_count = 0

        @with_retry(config=RetryConfig(initial_delay=0.01))
        async def my_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Failed")
            return "success"

        result = await my_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_name(self):
        """Test that decorator preserves function name."""
        @with_retry()
        async def my_named_function():
            return "success"

        assert my_named_function.__name__ == "my_named_function"
