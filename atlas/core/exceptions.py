"""ATLAS Exception Hierarchy.

Provides a structured exception hierarchy for better error handling,
logging, and debugging across the ATLAS system.

Exception Hierarchy:
    ATLASException (base)
    ├── ConfigurationException
    │   ├── MissingConfigException
    │   └── InvalidConfigException
    ├── ProviderException
    │   ├── ProviderUnavailableException
    │   ├── ProviderRateLimitException
    │   ├── ProviderAuthException
    │   └── ProviderResponseException
    ├── AgentException
    │   ├── AgentTimeoutException
    │   └── AgentWorkflowException
    ├── ProjectException
    │   ├── ProjectNotFoundException
    │   └── ProjectValidationException
    ├── ValidationException
    │   └── InputValidationException
    └── ResourceException
        ├── ResourceNotFoundException
        └── ResourceExhaustedException
"""

from typing import Any, Optional


class ATLASException(Exception):
    """Base exception for all ATLAS errors.

    Attributes:
        message: Human-readable error message
        code: Optional error code for programmatic handling
        details: Optional dict with additional context
        recoverable: Whether the error might be resolved by retrying
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        recoverable: bool = False,
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.recoverable = recoverable
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
        }

    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} - {self.details}"
        return f"[{self.code}] {self.message}"


# --- Configuration Exceptions ---

class ConfigurationException(ATLASException):
    """Base exception for configuration errors."""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, details=details, **kwargs)


class MissingConfigException(ConfigurationException):
    """Raised when a required configuration is missing."""

    def __init__(self, config_key: str, message: Optional[str] = None):
        message = message or f"Missing required configuration: {config_key}"
        super().__init__(message, config_key=config_key, code="MISSING_CONFIG")


class InvalidConfigException(ConfigurationException):
    """Raised when a configuration value is invalid."""

    def __init__(self, config_key: str, value: Any, reason: str):
        message = f"Invalid configuration for {config_key}: {reason}"
        super().__init__(
            message,
            config_key=config_key,
            code="INVALID_CONFIG",
            details={"value": str(value), "reason": reason},
        )


# --- Provider Exceptions ---

class ProviderException(ATLASException):
    """Base exception for AI provider errors."""

    def __init__(self, message: str, provider: str, **kwargs):
        details = kwargs.pop("details", {})
        details["provider"] = provider
        super().__init__(message, details=details, **kwargs)
        self.provider = provider


class ProviderUnavailableException(ProviderException):
    """Raised when a provider is not available."""

    def __init__(self, provider: str, reason: Optional[str] = None):
        message = f"Provider {provider} is unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(
            message,
            provider=provider,
            code="PROVIDER_UNAVAILABLE",
            recoverable=True,
        )


class ProviderRateLimitException(ProviderException):
    """Raised when provider rate limit is exceeded."""

    def __init__(
        self,
        provider: str,
        retry_after: Optional[int] = None,
    ):
        message = f"Rate limit exceeded for {provider}"
        details = {}
        if retry_after:
            message += f", retry after {retry_after}s"
            details["retry_after"] = retry_after
        super().__init__(
            message,
            provider=provider,
            code="RATE_LIMIT",
            details=details,
            recoverable=True,
        )
        self.retry_after = retry_after


class ProviderAuthException(ProviderException):
    """Raised when provider authentication fails."""

    def __init__(self, provider: str, reason: Optional[str] = None):
        message = f"Authentication failed for {provider}"
        if reason:
            message += f": {reason}"
        super().__init__(
            message,
            provider=provider,
            code="AUTH_FAILED",
            recoverable=False,
        )


class ProviderResponseException(ProviderException):
    """Raised when provider returns an invalid response."""

    def __init__(
        self,
        provider: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
    ):
        message = f"Invalid response from {provider}"
        details = {}
        if status_code:
            message += f" (status {status_code})"
            details["status_code"] = status_code
        if response_text:
            details["response"] = response_text[:500]  # Truncate
        super().__init__(
            message,
            provider=provider,
            code="INVALID_RESPONSE",
            details=details,
            recoverable=True,
        )


# --- Agent Exceptions ---

class AgentException(ATLASException):
    """Base exception for agent errors."""

    def __init__(self, message: str, agent: str, **kwargs):
        details = kwargs.pop("details", {})
        details["agent"] = agent
        super().__init__(message, details=details, **kwargs)
        self.agent = agent


class AgentTimeoutException(AgentException):
    """Raised when an agent operation times out."""

    def __init__(self, agent: str, timeout_seconds: int):
        message = f"Agent {agent} timed out after {timeout_seconds}s"
        super().__init__(
            message,
            agent=agent,
            code="AGENT_TIMEOUT",
            details={"timeout_seconds": timeout_seconds},
            recoverable=True,
        )


class AgentWorkflowException(AgentException):
    """Raised when an agent workflow fails."""

    def __init__(
        self,
        agent: str,
        workflow_stage: str,
        reason: str,
    ):
        message = f"Workflow failed at {workflow_stage} ({agent}): {reason}"
        super().__init__(
            message,
            agent=agent,
            code="WORKFLOW_FAILED",
            details={"stage": workflow_stage, "reason": reason},
            recoverable=False,
        )


# --- Project Exceptions ---

class ProjectException(ATLASException):
    """Base exception for project-related errors."""

    def __init__(self, message: str, project_id: Optional[int] = None, **kwargs):
        details = kwargs.pop("details", {})
        if project_id:
            details["project_id"] = project_id
        super().__init__(message, details=details, **kwargs)
        self.project_id = project_id


class ProjectNotFoundException(ProjectException):
    """Raised when a project is not found."""

    def __init__(self, project_id: int):
        message = f"Project {project_id} not found"
        super().__init__(
            message,
            project_id=project_id,
            code="PROJECT_NOT_FOUND",
            recoverable=False,
        )


class ProjectValidationException(ProjectException):
    """Raised when project validation fails."""

    def __init__(self, project_id: Optional[int], errors: list[str]):
        message = "Project validation failed"
        super().__init__(
            message,
            project_id=project_id,
            code="PROJECT_VALIDATION_FAILED",
            details={"errors": errors},
            recoverable=False,
        )


# --- Validation Exceptions ---

class ValidationException(ATLASException):
    """Base exception for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        code = kwargs.pop("code", "VALIDATION_ERROR")
        super().__init__(message, code=code, details=details, **kwargs)


class InputValidationException(ValidationException):
    """Raised when user input validation fails."""

    def __init__(self, field: str, value: Any, reason: str):
        message = f"Invalid input for {field}: {reason}"
        super().__init__(
            message,
            field=field,
            code="INVALID_INPUT",
            details={"value": str(value)[:100], "reason": reason},
        )


# --- Resource Exceptions ---

class ResourceException(ATLASException):
    """Base exception for resource-related errors."""

    def __init__(self, message: str, resource_type: str, **kwargs):
        details = kwargs.pop("details", {})
        details["resource_type"] = resource_type
        super().__init__(message, details=details, **kwargs)


class ResourceNotFoundException(ResourceException):
    """Raised when a resource is not found."""

    def __init__(self, resource_type: str, resource_id: Any):
        message = f"{resource_type} not found: {resource_id}"
        super().__init__(
            message,
            resource_type=resource_type,
            code="RESOURCE_NOT_FOUND",
            details={"resource_id": str(resource_id)},
            recoverable=False,
        )


class ResourceExhaustedException(ResourceException):
    """Raised when a resource limit is reached."""

    def __init__(
        self,
        resource_type: str,
        limit: int,
        current: int,
    ):
        message = f"{resource_type} limit exhausted ({current}/{limit})"
        super().__init__(
            message,
            resource_type=resource_type,
            code="RESOURCE_EXHAUSTED",
            details={"limit": limit, "current": current},
            recoverable=True,
        )


# --- Legacy compatibility ---
# Keep ProviderError for backwards compatibility with existing code

class ProviderError(ProviderException):
    """Legacy exception for provider errors.

    Deprecated: Use ProviderException or its subclasses instead.
    """

    def __init__(self, message: str, provider: str, recoverable: bool = True):
        super().__init__(
            message,
            provider=provider,
            code="PROVIDER_ERROR",
            recoverable=recoverable,
        )
