"""Tests for the ATLAS Router."""

import pytest
from atlas.routing.router import Router


class TestRouter:
    """Test suite for Router class."""

    def test_classify_task_code(self):
        """Test that code-related prompts are classified correctly."""
        router = Router()

        code_prompts = [
            "Write a Python function",
            "Debug this JavaScript code",
            "Fix the SQL query",
            "Implement a class for user management",
        ]

        for prompt in code_prompts:
            task_type = router.classify_task(prompt)
            assert task_type == "code", f"'{prompt}' should be classified as 'code', got '{task_type}'"

    def test_classify_task_research(self):
        """Test that research-related prompts are classified correctly."""
        router = Router()

        research_prompts = [
            "What is machine learning?",
            "Explain how Docker works",
            "Research the latest AI trends",
            "Find information about Python 3.12",
        ]

        for prompt in research_prompts:
            task_type = router.classify_task(prompt)
            assert task_type == "research", f"'{prompt}' should be classified as 'research', got '{task_type}'"

    def test_classify_task_draft(self):
        """Test that drafting prompts are classified correctly."""
        router = Router()

        draft_prompts = [
            "Write an email to the team",
            "Draft a project proposal",
            "Compose a message for the client",
        ]

        for prompt in draft_prompts:
            task_type = router.classify_task(prompt)
            assert task_type == "draft", f"'{prompt}' should be classified as 'draft', got '{task_type}'"

    def test_classify_task_default(self):
        """Test that unrecognized prompts get default classification."""
        router = Router()

        # Very generic prompt with no keywords
        task_type = router.classify_task("hello there")
        assert task_type == "default"

    def test_routing_table_exists(self):
        """Test that routing table has expected task types."""
        expected_types = ["research", "code", "review", "draft", "default"]

        for task_type in expected_types:
            assert task_type in Router.ROUTING_TABLE, f"Missing task type: {task_type}"

    def test_routing_table_has_providers(self):
        """Test that each routing entry has provider fallbacks."""
        for task_type, providers in Router.ROUTING_TABLE.items():
            assert isinstance(providers, list), f"{task_type} should have list of providers"
            assert len(providers) > 0, f"{task_type} should have at least one provider"
