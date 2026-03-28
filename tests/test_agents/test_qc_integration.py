"""Tests for QC integration in AgentManager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from atlas.agents.manager import AgentManager, WorkflowMode
from atlas.agents.base import AgentOutput, AgentStatus
from atlas.agents.qc import QCReport, QCVerdict, IssueSeverity, QCIssue


class TestQCIntegration:
    """Tests for QC integration in AgentManager."""

    @pytest.fixture
    def mock_router(self):
        """Create a mock router."""
        router = MagicMock()
        router.route.return_value = {"provider": "openai"}
        return router

    @pytest.fixture
    def mock_memory(self):
        """Create a mock memory manager."""
        return MagicMock()

    @pytest.fixture
    def manager(self, mock_router, mock_memory):
        """Create an AgentManager with mocked dependencies."""
        with patch('atlas.agents.manager.ArchitectAgent'), \
             patch('atlas.agents.manager.MasonAgent'), \
             patch('atlas.agents.manager.OracleAgent'), \
             patch('atlas.agents.manager.FinisherAgent'), \
             patch('atlas.agents.manager.LaunchAgent'), \
             patch('atlas.agents.manager.HypeAgent'), \
             patch('atlas.agents.manager.QCAgent'), \
             patch('atlas.agents.manager.KickoffAgent'):
            manager = AgentManager(mock_router, mock_memory)
            return manager

    def test_manager_has_qc_agent(self, manager):
        """Test that AgentManager initializes QC agent."""
        assert hasattr(manager, 'qc')

    def test_manager_has_kickoff_agent(self, manager):
        """Test that AgentManager initializes Kickoff agent."""
        assert hasattr(manager, 'kickoff')

    def test_get_all_status_includes_qc(self, manager):
        """Test that get_all_status includes QC agent."""
        manager.qc.get_status_dict.return_value = {
            "name": "qc",
            "status": "idle",
        }

        status = manager.get_all_status()

        assert "qc" in status

    def test_get_all_status_includes_kickoff(self, manager):
        """Test that get_all_status includes Kickoff agent."""
        manager.kickoff.get_status_dict.return_value = {
            "name": "kickoff",
            "status": "idle",
        }

        status = manager.get_all_status()

        assert "kickoff" in status

    def test_workflow_mode_with_kickoff_exists(self):
        """Test that WITH_KICKOFF workflow mode exists."""
        assert WorkflowMode.WITH_KICKOFF.value == "with_kickoff"

    def test_workflow_mode_qc_build_exists(self):
        """Test that QC_BUILD workflow mode exists."""
        assert WorkflowMode.QC_BUILD.value == "qc_build"


class TestExecuteMasonWithQC:
    """Tests for _execute_mason_with_qc method."""

    @pytest.fixture
    def mock_router(self):
        """Create a mock router."""
        router = MagicMock()
        router.route.return_value = {"provider": "openai"}
        return router

    @pytest.fixture
    def manager(self, mock_router):
        """Create an AgentManager with mocked agents."""
        with patch('atlas.agents.manager.ArchitectAgent'), \
             patch('atlas.agents.manager.MasonAgent'), \
             patch('atlas.agents.manager.OracleAgent'), \
             patch('atlas.agents.manager.FinisherAgent'), \
             patch('atlas.agents.manager.LaunchAgent'), \
             patch('atlas.agents.manager.HypeAgent'), \
             patch('atlas.agents.manager.QCAgent'), \
             patch('atlas.agents.manager.KickoffAgent'):
            manager = AgentManager(mock_router, None)
            return manager

    @pytest.mark.asyncio
    async def test_qc_pass_on_first_attempt(self, manager):
        """Test QC passes build on first attempt."""
        # Mock Mason output
        mason_output = AgentOutput(
            content="Generated code",
            artifacts={"files": {"index.html": "<html></html>"}},
            status=AgentStatus.COMPLETED,
        )
        manager.mason.process = AsyncMock(return_value=mason_output)

        # Mock QC report - PASS
        qc_report = QCReport(
            verdict=QCVerdict.PASS,
            verdict_reason="Build looks good",
            attempt=1,
            alignment_score=90,
            sellability_score=85,
            quality_score=88,
        )
        manager.qc.check_build = AsyncMock(return_value=qc_report)

        brief = {"product_type": "web", "name": "Test"}
        context = {}

        outputs = await manager._execute_mason_with_qc(
            task="Build a website",
            context=context,
            previous_output=None,
            brief=brief,
        )

        # Should have mason and qc outputs
        assert "mason" in outputs
        assert "qc" in outputs
        assert "mason_1" in outputs
        assert "qc_1" in outputs

        # Should not have blocked
        assert "blocked" not in outputs

        # QC should show pass
        assert outputs["qc"].metadata["verdict"] == "pass"
        assert outputs["qc"].metadata["can_proceed"] is True

    @pytest.mark.asyncio
    async def test_qc_pass_with_notes_proceeds(self, manager):
        """Test QC with PASS_WITH_NOTES allows build to proceed."""
        mason_output = AgentOutput(
            content="Generated code",
            artifacts={"files": {}},
            status=AgentStatus.COMPLETED,
        )
        manager.mason.process = AsyncMock(return_value=mason_output)

        qc_report = QCReport(
            verdict=QCVerdict.PASS_WITH_NOTES,
            verdict_reason="Minor suggestions",
            attempt=1,
            issues=[
                QCIssue(
                    description="Could improve formatting",
                    severity=IssueSeverity.INFO,
                    fix="Add more whitespace",
                )
            ],
        )
        manager.qc.check_build = AsyncMock(return_value=qc_report)

        outputs = await manager._execute_mason_with_qc(
            task="Build",
            context={},
            previous_output=None,
            brief={"name": "Test"},
        )

        assert "blocked" not in outputs
        assert outputs["qc"].metadata["can_proceed"] is True

    @pytest.mark.asyncio
    async def test_qc_needs_revision_triggers_retry(self, manager):
        """Test QC NEEDS_REVISION triggers Mason retry."""
        mason_output_1 = AgentOutput(
            content="First attempt",
            artifacts={},
            status=AgentStatus.COMPLETED,
        )
        mason_output_2 = AgentOutput(
            content="Second attempt",
            artifacts={},
            status=AgentStatus.COMPLETED,
        )
        manager.mason.process = AsyncMock(side_effect=[mason_output_1, mason_output_2])

        # First QC: needs revision
        qc_report_1 = QCReport(
            verdict=QCVerdict.NEEDS_REVISION,
            verdict_reason="Missing features",
            attempt=1,
            fix_instructions="Add the login form",
            issues=[
                QCIssue(
                    description="Login form missing",
                    severity=IssueSeverity.CRITICAL,
                    fix="Add login form component",
                )
            ],
        )
        # Second QC: pass
        qc_report_2 = QCReport(
            verdict=QCVerdict.PASS,
            verdict_reason="Fixed",
            attempt=2,
        )
        manager.qc.check_build = AsyncMock(side_effect=[qc_report_1, qc_report_2])

        outputs = await manager._execute_mason_with_qc(
            task="Build",
            context={},
            previous_output=None,
            brief={"name": "Test"},
        )

        # Should have both attempts
        assert "mason_1" in outputs
        assert "mason_2" in outputs
        assert "qc_1" in outputs
        assert "qc_2" in outputs

        # Final outputs should be attempt 2
        assert outputs["mason"].content == "Second attempt"
        assert outputs["qc"].metadata["verdict"] == "pass"

        # Mason should have been called twice
        assert manager.mason.process.call_count == 2

    @pytest.mark.asyncio
    async def test_qc_blocks_after_max_attempts(self, manager):
        """Test QC blocks build after maximum retry attempts."""
        mason_output = AgentOutput(
            content="Still broken",
            artifacts={},
            status=AgentStatus.COMPLETED,
        )
        manager.mason.process = AsyncMock(return_value=mason_output)

        # Both QC attempts fail
        qc_report_1 = QCReport(
            verdict=QCVerdict.NEEDS_REVISION,
            verdict_reason="Missing features",
            attempt=1,
            fix_instructions="Add features",
        )
        qc_report_2 = QCReport(
            verdict=QCVerdict.BLOCKED,  # After retry, becomes BLOCKED
            verdict_reason="Still broken after retry",
            attempt=2,
        )
        manager.qc.check_build = AsyncMock(side_effect=[qc_report_1, qc_report_2])

        outputs = await manager._execute_mason_with_qc(
            task="Build",
            context={},
            previous_output=None,
            brief={"name": "Test"},
        )

        # Should be blocked
        assert "blocked" in outputs
        assert outputs["blocked"].metadata["blocked"] is True

        # Should have both attempts
        assert "mason_1" in outputs
        assert "mason_2" in outputs

    @pytest.mark.asyncio
    async def test_qc_feedback_passed_to_retry(self, manager):
        """Test that QC fix instructions are passed to Mason on retry."""
        mason_output = AgentOutput(
            content="Generated",
            artifacts={},
            status=AgentStatus.COMPLETED,
        )
        manager.mason.process = AsyncMock(return_value=mason_output)

        qc_report_1 = QCReport(
            verdict=QCVerdict.NEEDS_REVISION,
            verdict_reason="Needs work",
            attempt=1,
            fix_instructions="1. Add header\n2. Fix footer\n3. Add navigation",
        )
        qc_report_2 = QCReport(
            verdict=QCVerdict.PASS,
            verdict_reason="Fixed",
            attempt=2,
        )
        manager.qc.check_build = AsyncMock(side_effect=[qc_report_1, qc_report_2])

        context = {}
        outputs = await manager._execute_mason_with_qc(
            task="Build",
            context=context,
            previous_output=None,
            brief={"name": "Test"},
        )

        # Context should have qc_feedback after first attempt
        assert "qc_feedback" in context
        assert "Add header" in context["qc_feedback"]

    @pytest.mark.asyncio
    async def test_mason_error_stops_qc_loop(self, manager):
        """Test that Mason error stops the QC loop."""
        mason_output = AgentOutput(
            content="Error occurred",
            status=AgentStatus.ERROR,
            metadata={"error": "Generation failed"},
        )
        manager.mason.process = AsyncMock(return_value=mason_output)

        outputs = await manager._execute_mason_with_qc(
            task="Build",
            context={},
            previous_output=None,
            brief={"name": "Test"},
        )

        # Should have mason output with error
        assert "mason" in outputs
        assert outputs["mason"].status == AgentStatus.ERROR

        # QC should not have been called
        manager.qc.check_build.assert_not_called()


class TestExecuteWithKickoff:
    """Tests for _execute_with_kickoff workflow."""

    @pytest.fixture
    def manager(self):
        """Create an AgentManager with mocked agents."""
        with patch('atlas.agents.manager.ArchitectAgent'), \
             patch('atlas.agents.manager.MasonAgent'), \
             patch('atlas.agents.manager.OracleAgent'), \
             patch('atlas.agents.manager.FinisherAgent'), \
             patch('atlas.agents.manager.LaunchAgent'), \
             patch('atlas.agents.manager.HypeAgent'), \
             patch('atlas.agents.manager.QCAgent'), \
             patch('atlas.agents.manager.KickoffAgent'):
            manager = AgentManager(MagicMock(), None)
            return manager

    @pytest.mark.asyncio
    async def test_requires_brief(self, manager):
        """Test that workflow requires a Brief in context."""
        outputs = await manager._execute_with_kickoff("Build", context={})

        assert "error" in outputs
        assert "No Business Brief" in outputs["error"].content

    @pytest.mark.asyncio
    async def test_kickoff_blocked_stops_workflow(self, manager):
        """Test that blocked Kickoff stops the workflow."""
        manager.kickoff.process = AsyncMock(return_value=AgentOutput(
            content="Brief not approved",
            artifacts={"blocked": True, "reason": "no-go recommendation"},
            status=AgentStatus.COMPLETED,
        ))

        context = {
            "brief": {"recommendation": "no-go", "name": "Test"},
        }

        outputs = await manager._execute_with_kickoff("Build", context)

        assert "kickoff" in outputs
        assert outputs["kickoff"].artifacts.get("blocked") is True

        # Architect should not have been called
        manager.architect.process.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_workflow_success(self, manager):
        """Test successful full workflow with all agents."""
        # Mock Kickoff
        manager.kickoff.process = AsyncMock(return_value=AgentOutput(
            content="Kickoff complete",
            artifacts={"kickoff_plan": {"phases": []}},
            status=AgentStatus.COMPLETED,
        ))

        # Mock Architect
        manager.architect.process = AsyncMock(return_value=AgentOutput(
            content="Architecture complete",
            status=AgentStatus.COMPLETED,
        ))

        # Mock Mason
        manager.mason.process = AsyncMock(return_value=AgentOutput(
            content="Build complete",
            artifacts={"files": {}},
            status=AgentStatus.COMPLETED,
        ))

        # Mock QC
        manager.qc.check_build = AsyncMock(return_value=QCReport(
            verdict=QCVerdict.PASS,
            verdict_reason="All good",
        ))

        # Mock Oracle
        manager.oracle.process = AsyncMock(return_value=AgentOutput(
            content="Verification complete",
            metadata={"verdict": "APPROVED"},
            status=AgentStatus.COMPLETED,
        ))

        context = {
            "brief": {"recommendation": "go", "name": "Test", "product_type": "web"},
        }

        outputs = await manager._execute_with_kickoff("Build website", context)

        # All agents should have been called
        assert "kickoff" in outputs
        assert "architect" in outputs
        assert "mason" in outputs
        assert "qc" in outputs
        assert "oracle" in outputs


class TestExecuteQCBuild:
    """Tests for _execute_qc_build workflow."""

    @pytest.fixture
    def manager(self):
        """Create an AgentManager with mocked agents."""
        with patch('atlas.agents.manager.ArchitectAgent'), \
             patch('atlas.agents.manager.MasonAgent'), \
             patch('atlas.agents.manager.OracleAgent'), \
             patch('atlas.agents.manager.FinisherAgent'), \
             patch('atlas.agents.manager.LaunchAgent'), \
             patch('atlas.agents.manager.HypeAgent'), \
             patch('atlas.agents.manager.QCAgent'), \
             patch('atlas.agents.manager.KickoffAgent'):
            manager = AgentManager(MagicMock(), None)
            return manager

    @pytest.mark.asyncio
    async def test_requires_brief(self, manager):
        """Test that QC build requires a Brief."""
        outputs = await manager._execute_qc_build("Build", context={})

        assert "error" in outputs

    @pytest.mark.asyncio
    async def test_direct_mason_with_qc(self, manager):
        """Test direct Mason build with QC validation."""
        manager.mason.process = AsyncMock(return_value=AgentOutput(
            content="Built",
            artifacts={},
            status=AgentStatus.COMPLETED,
        ))

        manager.qc.check_build = AsyncMock(return_value=QCReport(
            verdict=QCVerdict.PASS,
        ))

        context = {"brief": {"name": "Test"}}

        outputs = await manager._execute_qc_build("Build", context)

        assert "mason" in outputs
        assert "qc" in outputs

        # Only Mason and QC should run (no Kickoff, Architect, or Oracle)
        manager.kickoff.process.assert_not_called()
        manager.architect.process.assert_not_called()
        manager.oracle.process.assert_not_called()
