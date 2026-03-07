"""Tests for the ATLAS Butler personality."""

import pytest
from atlas.core.butler import Butler


class TestButler:
    """Test suite for Butler class."""

    def test_butler_initialization(self):
        """Test that butler initializes with correct defaults."""
        butler = Butler()
        assert butler.name == "ATLAS"

    def test_butler_custom_name(self):
        """Test that butler accepts custom name."""
        butler = Butler(name="JARVIS")
        assert butler.name == "JARVIS"

    def test_greet_returns_string(self):
        """Test that greet returns a formatted string."""
        butler = Butler()
        greeting = butler.greet()

        assert isinstance(greeting, str)
        assert "[ATLAS]" in greeting

    def test_acknowledge_returns_string(self):
        """Test that acknowledge returns a formatted string."""
        butler = Butler()
        ack = butler.acknowledge()

        assert isinstance(ack, str)
        assert "[ATLAS]" in ack

    def test_thinking_returns_string(self):
        """Test that thinking returns a formatted string."""
        butler = Butler()
        thinking = butler.thinking()

        assert isinstance(thinking, str)
        assert "[ATLAS]" in thinking

    def test_farewell_returns_string(self):
        """Test that farewell returns a formatted string."""
        butler = Butler()
        farewell = butler.farewell()

        assert isinstance(farewell, str)
        assert "[ATLAS]" in farewell

    def test_error_formatting(self):
        """Test error message formatting."""
        butler = Butler()
        error = butler.error("Something went wrong")

        assert isinstance(error, str)
        assert "Something went wrong" in error

    def test_format_status(self):
        """Test status formatting."""
        butler = Butler()
        status = butler.format_status({
            "api_calls": 10,
            "tasks_completed": 5,
        })

        assert "Api Calls" in status
        assert "10" in status
        assert "Tasks Completed" in status
        assert "5" in status

    def test_time_period_greetings(self):
        """Test that different time periods have greetings."""
        butler = Butler()

        for period in ["morning", "afternoon", "evening", "night"]:
            assert period in butler.GREETINGS
            assert len(butler.GREETINGS[period]) > 0
