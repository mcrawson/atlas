"""Tests for ATLAS exception hierarchy."""

import pytest
from atlas.core.exceptions import (
    ATLASException,
    ConfigurationException,
    MissingConfigException,
    InvalidConfigException,
    ProviderException,
    ProviderUnavailableException,
    ProviderRateLimitException,
    ProviderAuthException,
    ProviderResponseException,
    AgentException,
    AgentTimeoutException,
    AgentWorkflowException,
    ProjectException,
    ProjectNotFoundException,
    ProjectValidationException,
    ValidationException,
    InputValidationException,
    ResourceException,
    ResourceNotFoundException,
    ResourceExhaustedException,
    ProviderError,
)


class TestATLASException:
    """Test base ATLAS exception."""

    def test_basic_exception(self):
        """Test creating a basic exception."""
        exc = ATLASException("Something went wrong")
        assert exc.message == "Something went wrong"
        assert exc.code == "ATLASException"
        assert exc.details == {}
        assert exc.recoverable is False

    def test_exception_with_code(self):
        """Test exception with custom code."""
        exc = ATLASException("Error", code="CUSTOM_ERROR")
        assert exc.code == "CUSTOM_ERROR"

    def test_exception_with_details(self):
        """Test exception with details."""
        exc = ATLASException("Error", details={"key": "value"})
        assert exc.details == {"key": "value"}

    def test_to_dict(self):
        """Test converting exception to dict."""
        exc = ATLASException(
            "Error message",
            code="TEST_ERROR",
            details={"foo": "bar"},
            recoverable=True,
        )
        result = exc.to_dict()

        assert result["error"] == "TEST_ERROR"
        assert result["message"] == "Error message"
        assert result["details"] == {"foo": "bar"}
        assert result["recoverable"] is True

    def test_str_representation(self):
        """Test string representation."""
        exc = ATLASException("Error", code="CODE")
        assert "[CODE] Error" in str(exc)


class TestConfigurationExceptions:
    """Test configuration exceptions."""

    def test_missing_config(self):
        """Test MissingConfigException."""
        exc = MissingConfigException("api_key")
        assert "api_key" in exc.message
        assert exc.code == "MISSING_CONFIG"
        assert exc.details["config_key"] == "api_key"

    def test_invalid_config(self):
        """Test InvalidConfigException."""
        exc = InvalidConfigException("timeout", -1, "must be positive")
        assert "timeout" in exc.message
        assert exc.code == "INVALID_CONFIG"
        assert exc.details["reason"] == "must be positive"


class TestProviderExceptions:
    """Test provider exceptions."""

    def test_provider_unavailable(self):
        """Test ProviderUnavailableException."""
        exc = ProviderUnavailableException("openai", "API down")
        assert exc.provider == "openai"
        assert "unavailable" in exc.message.lower()
        assert exc.recoverable is True

    def test_rate_limit_with_retry(self):
        """Test ProviderRateLimitException with retry_after."""
        exc = ProviderRateLimitException("claude", retry_after=60)
        assert exc.provider == "claude"
        assert exc.retry_after == 60
        assert exc.details["retry_after"] == 60
        assert exc.recoverable is True

    def test_auth_exception(self):
        """Test ProviderAuthException."""
        exc = ProviderAuthException("gemini", "Invalid API key")
        assert exc.provider == "gemini"
        assert exc.recoverable is False

    def test_response_exception(self):
        """Test ProviderResponseException."""
        exc = ProviderResponseException("ollama", status_code=500)
        assert exc.provider == "ollama"
        assert exc.details["status_code"] == 500

    def test_legacy_provider_error(self):
        """Test legacy ProviderError compatibility."""
        exc = ProviderError("Failed", "test_provider", recoverable=True)
        assert exc.provider == "test_provider"
        assert exc.recoverable is True
        assert isinstance(exc, ProviderException)


class TestAgentExceptions:
    """Test agent exceptions."""

    def test_agent_timeout(self):
        """Test AgentTimeoutException."""
        exc = AgentTimeoutException("architect", 30)
        assert exc.agent == "architect"
        assert exc.details["timeout_seconds"] == 30
        assert exc.recoverable is True

    def test_workflow_exception(self):
        """Test AgentWorkflowException."""
        exc = AgentWorkflowException("mason", "build", "Compilation failed")
        assert exc.agent == "mason"
        assert exc.details["stage"] == "build"
        assert exc.details["reason"] == "Compilation failed"


class TestProjectExceptions:
    """Test project exceptions."""

    def test_project_not_found(self):
        """Test ProjectNotFoundException."""
        exc = ProjectNotFoundException(42)
        assert exc.project_id == 42
        assert "42" in exc.message
        assert exc.code == "PROJECT_NOT_FOUND"

    def test_project_validation(self):
        """Test ProjectValidationException."""
        errors = ["Name too short", "Invalid status"]
        exc = ProjectValidationException(1, errors)
        assert exc.details["errors"] == errors


class TestValidationExceptions:
    """Test validation exceptions."""

    def test_input_validation(self):
        """Test InputValidationException."""
        exc = InputValidationException("email", "notanemail", "Invalid format")
        assert exc.details["field"] == "email"
        assert exc.details["reason"] == "Invalid format"


class TestResourceExceptions:
    """Test resource exceptions."""

    def test_resource_not_found(self):
        """Test ResourceNotFoundException."""
        exc = ResourceNotFoundException("task", 123)
        assert exc.details["resource_type"] == "task"
        assert exc.details["resource_id"] == "123"

    def test_resource_exhausted(self):
        """Test ResourceExhaustedException."""
        exc = ResourceExhaustedException("api_calls", limit=100, current=100)
        assert exc.details["limit"] == 100
        assert exc.details["current"] == 100
        assert exc.recoverable is True


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_all_inherit_from_base(self):
        """Test all exceptions inherit from ATLASException."""
        exceptions = [
            ConfigurationException("test"),
            ProviderException("test", "provider"),
            AgentException("test", "agent"),
            ProjectException("test"),
            ValidationException("test"),
            ResourceException("test", "type"),
        ]

        for exc in exceptions:
            assert isinstance(exc, ATLASException)

    def test_provider_subclasses(self):
        """Test provider exception inheritance."""
        exceptions = [
            ProviderUnavailableException("test"),
            ProviderRateLimitException("test"),
            ProviderAuthException("test"),
            ProviderResponseException("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, ProviderException)
            assert isinstance(exc, ATLASException)

    def test_can_catch_by_base(self):
        """Test catching exceptions by base class."""
        try:
            raise ProviderRateLimitException("test")
        except ATLASException as e:
            assert e.recoverable is True
