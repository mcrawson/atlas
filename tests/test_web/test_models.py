"""Tests for ATLAS Web API models."""

import pytest
from pydantic import ValidationError

from atlas.web.models import (
    TaskRequest,
    ProjectCreateRequest,
    TaskCreateRequest,
    IdeaConversationRequest,
    FeedbackRequest,
    WorkflowModeEnum,
    TaskPriorityEnum,
)


class TestTaskRequest:
    """Test TaskRequest validation."""

    def test_valid_task(self):
        """Test creating a valid task request."""
        req = TaskRequest(task="Build a fibonacci function")
        assert req.task == "Build a fibonacci function"
        assert req.mode == WorkflowModeEnum.SEQUENTIAL
        assert req.context is None

    def test_task_with_mode(self):
        """Test task with specific mode."""
        req = TaskRequest(task="Test", mode=WorkflowModeEnum.DIRECT_BUILD)
        assert req.mode == WorkflowModeEnum.DIRECT_BUILD

    def test_task_with_context(self):
        """Test task with context."""
        req = TaskRequest(task="Test", context={"key": "value"})
        assert req.context == {"key": "value"}

    def test_empty_task_rejected(self):
        """Test that empty task is rejected."""
        with pytest.raises(ValidationError):
            TaskRequest(task="")

    def test_whitespace_task_rejected(self):
        """Test that whitespace-only task is rejected."""
        with pytest.raises(ValidationError):
            TaskRequest(task="   ")

    def test_task_whitespace_stripped(self):
        """Test that task whitespace is stripped."""
        req = TaskRequest(task="  hello world  ")
        assert req.task == "hello world"


class TestProjectCreateRequest:
    """Test ProjectCreateRequest validation."""

    def test_valid_project(self):
        """Test creating a valid project."""
        req = ProjectCreateRequest(name="My Project")
        assert req.name == "My Project"
        assert req.description == ""
        assert req.tags == []

    def test_project_with_all_fields(self):
        """Test project with all fields."""
        req = ProjectCreateRequest(
            name="Test",
            description="A test project",
            tags=["python", "web"],
            idea="Original idea text"
        )
        assert req.name == "Test"
        assert req.description == "A test project"
        assert req.tags == ["python", "web"]
        assert req.idea == "Original idea text"

    def test_empty_name_rejected(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError):
            ProjectCreateRequest(name="")

    def test_name_whitespace_stripped(self):
        """Test that name whitespace is stripped."""
        req = ProjectCreateRequest(name="  My Project  ")
        assert req.name == "My Project"

    def test_tags_normalized(self):
        """Test that tags are normalized."""
        req = ProjectCreateRequest(name="Test", tags=["Python", "  WEB  ", ""])
        assert req.tags == ["python", "web"]


class TestTaskCreateRequest:
    """Test TaskCreateRequest validation."""

    def test_valid_task(self):
        """Test creating a valid task."""
        req = TaskCreateRequest(title="Implement feature")
        assert req.title == "Implement feature"
        assert req.description == ""
        assert req.priority == TaskPriorityEnum.MEDIUM

    def test_task_with_priority(self):
        """Test task with priority."""
        req = TaskCreateRequest(title="Test", priority=TaskPriorityEnum.HIGH)
        assert req.priority == TaskPriorityEnum.HIGH

    def test_empty_title_rejected(self):
        """Test that empty title is rejected."""
        with pytest.raises(ValidationError):
            TaskCreateRequest(title="")


class TestIdeaConversationRequest:
    """Test IdeaConversationRequest validation."""

    def test_valid_message(self):
        """Test creating a valid message."""
        req = IdeaConversationRequest(message="I want to build an app")
        assert req.message == "I want to build an app"

    def test_empty_message_rejected(self):
        """Test that empty message is rejected."""
        with pytest.raises(ValidationError):
            IdeaConversationRequest(message="")


class TestFeedbackRequest:
    """Test FeedbackRequest validation."""

    def test_valid_feedback(self):
        """Test creating valid feedback."""
        req = FeedbackRequest(feedback_type="thumbs_up")
        assert req.feedback_type == "thumbs_up"

    def test_feedback_with_content(self):
        """Test feedback with content."""
        req = FeedbackRequest(feedback_type="comment", content="Great feature!")
        assert req.content == "Great feature!"

    def test_invalid_feedback_type_rejected(self):
        """Test that invalid feedback type is rejected."""
        with pytest.raises(ValidationError):
            FeedbackRequest(feedback_type="invalid_type")

    def test_feedback_type_case_insensitive(self):
        """Test that feedback type is case insensitive."""
        req = FeedbackRequest(feedback_type="THUMBS_UP")
        assert req.feedback_type == "thumbs_up"


class TestEnums:
    """Test enum values."""

    def test_workflow_modes(self):
        """Test all workflow modes exist."""
        assert WorkflowModeEnum.SEQUENTIAL.value == "sequential"
        assert WorkflowModeEnum.DIRECT_BUILD.value == "direct_build"
        assert WorkflowModeEnum.VERIFY_ONLY.value == "verify_only"
        assert WorkflowModeEnum.SPEC_DRIVEN.value == "spec_driven"

    def test_task_priorities(self):
        """Test all task priorities exist."""
        assert TaskPriorityEnum.LOW.value == 0
        assert TaskPriorityEnum.MEDIUM.value == 1
        assert TaskPriorityEnum.HIGH.value == 2
        assert TaskPriorityEnum.CRITICAL.value == 3
