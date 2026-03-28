"""Tests for Kickoff Agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from atlas.agents.kickoff import KickoffAgent, KickoffPlan, BuildPhase
from atlas.agents.base import AgentStatus


class TestKickoffPlan:
    """Tests for KickoffPlan dataclass."""

    def test_kickoff_plan_to_dict(self):
        """Test KickoffPlan serialization."""
        plan = KickoffPlan(
            project_name="Test Project",
            product_type="web",
            brief_confidence=0.85,
            scope={
                "in_scope": ["Feature A", "Feature B"],
                "out_of_scope": ["Feature C"],
                "assumptions": ["Users have modern browsers"],
            },
            constraints=["Must work offline"],
            tech_stack={"framework": "React", "styling": "Tailwind"},
            tech_stack_reasoning="Modern stack for web apps",
            phases=[
                BuildPhase(
                    name="Setup",
                    description="Project scaffolding",
                    deliverables=["package.json", "vite.config.ts"],
                    qc_checkpoint=True,
                )
            ],
            qc_checkpoints=["After setup", "Final review"],
            architect_instructions="Focus on component structure",
            priority_features=["Feature A"],
            risk_areas=["Offline support"],
        )

        result = plan.to_dict()

        assert result["project_name"] == "Test Project"
        assert result["product_type"] == "web"
        assert result["brief_confidence"] == 0.85
        assert len(result["phases"]) == 1
        assert result["phases"][0]["name"] == "Setup"
        assert result["phases"][0]["qc_checkpoint"] is True
        assert len(result["qc_checkpoints"]) == 2

    def test_kickoff_plan_from_dict(self):
        """Test KickoffPlan deserialization."""
        data = {
            "project_name": "Test Project",
            "product_type": "printable",
            "brief_confidence": 0.9,
            "scope": {"in_scope": ["PDF generation"], "out_of_scope": []},
            "constraints": [],
            "tech_stack": {"format": "PDF"},
            "tech_stack_reasoning": "Standard for printables",
            "phases": [
                {
                    "name": "Design",
                    "description": "Create template",
                    "deliverables": ["template.pdf"],
                    "estimated_time": "2 hours",
                    "qc_checkpoint": True,
                }
            ],
            "qc_checkpoints": ["After design"],
            "architect_instructions": "Use clean layout",
            "priority_features": [],
            "risk_areas": [],
        }

        plan = KickoffPlan.from_dict(data)

        assert plan.project_name == "Test Project"
        assert plan.product_type == "printable"
        assert len(plan.phases) == 1
        assert plan.phases[0].name == "Design"
        assert plan.phases[0].qc_checkpoint is True

    def test_kickoff_plan_get_summary(self):
        """Test KickoffPlan summary generation."""
        plan = KickoffPlan(
            project_name="Test App",
            product_type="app",
            scope={"in_scope": ["Login", "Dashboard"], "out_of_scope": ["Admin panel"]},
            tech_stack={"framework": "React Native", "state": "Zustand"},
            tech_stack_reasoning="Cross-platform mobile",
            phases=[
                BuildPhase(name="Setup", description="Init", deliverables=[], qc_checkpoint=True),
                BuildPhase(name="Core", description="Build features", deliverables=[], qc_checkpoint=False),
                BuildPhase(name="Polish", description="Final touches", deliverables=[], qc_checkpoint=True),
            ],
            qc_checkpoints=["Setup check", "Final check"],
            priority_features=["Login", "Dashboard"],
            risk_areas=["Cross-platform compatibility"],
            architect_instructions="Focus on UX",
        )

        summary = plan.get_summary()

        assert "Test App" in summary
        assert "APP" in summary
        assert "Login" in summary
        assert "Dashboard" in summary
        assert "React Native" in summary
        assert "Setup check" in summary


class TestKickoffAgent:
    """Tests for KickoffAgent."""

    @pytest.fixture
    def mock_router(self):
        """Create a mock router."""
        router = MagicMock()
        router.route.return_value = {"provider": "openai"}
        return router

    @pytest.fixture
    def kickoff_agent(self, mock_router):
        """Create a KickoffAgent with mocked dependencies."""
        return KickoffAgent(router=mock_router, memory=None, providers={})

    def test_agent_name_and_description(self, kickoff_agent):
        """Test agent has correct name and description."""
        assert kickoff_agent.name == "kickoff"
        assert kickoff_agent.description == "Project kickoff and planning coordinator"
        assert kickoff_agent.icon == "🚀"

    def test_get_system_prompt(self, kickoff_agent):
        """Test system prompt contains key instructions."""
        prompt = kickoff_agent.get_system_prompt()

        assert "Kickoff Agent" in prompt
        assert "Tech Stack Guidelines" in prompt
        assert "PRINTABLE" in prompt
        assert "DOCUMENT" in prompt
        assert "WEB" in prompt
        assert "APP" in prompt
        assert "QC checkpoint" in prompt

    @pytest.mark.asyncio
    async def test_process_rejects_non_go_brief(self, kickoff_agent):
        """Test that process rejects briefs without 'go' recommendation."""
        context = {
            "brief": {
                "product_name": "Test Product",
                "product_type": "web",
                "recommendation": "no-go",
                "recommendation_reason": "Market too saturated",
            }
        }

        output = await kickoff_agent.process("Test task", context)

        assert "Cannot kickoff" in output.content
        assert output.artifacts.get("blocked") is True
        assert "no-go" in output.content

    @pytest.mark.asyncio
    async def test_process_rejects_needs_research_brief(self, kickoff_agent):
        """Test that process rejects briefs needing more research."""
        context = {
            "brief": {
                "product_name": "Test Product",
                "product_type": "app",
                "recommendation": "needs-more-research",
            }
        }

        output = await kickoff_agent.process("Test task", context)

        assert "Cannot kickoff" in output.content
        assert output.artifacts.get("blocked") is True

    @pytest.mark.asyncio
    async def test_process_requires_brief(self, kickoff_agent):
        """Test that process handles missing Brief gracefully."""
        # Process catches the ValueError and returns an error output
        output = await kickoff_agent.process("Test task", context={})

        assert output.status == AgentStatus.ERROR
        assert "Business Brief" in output.content

    @pytest.mark.asyncio
    async def test_process_with_approved_brief(self, kickoff_agent):
        """Test successful kickoff with approved brief."""
        # Mock the LLM response
        mock_response = """```json
{
    "project_name": "Test App",
    "product_type": "web",
    "brief_confidence": 0.85,
    "scope": {
        "in_scope": ["User dashboard", "Login system"],
        "out_of_scope": ["Admin panel"],
        "assumptions": ["Modern browsers only"]
    },
    "constraints": ["Must be responsive"],
    "tech_stack": {
        "framework": "React",
        "styling": "Tailwind CSS",
        "build": "Vite"
    },
    "tech_stack_reasoning": "Modern, fast, well-supported stack",
    "phases": [
        {
            "name": "Setup",
            "description": "Project scaffolding",
            "deliverables": ["package.json", "vite.config.ts"],
            "estimated_time": "1 hour",
            "qc_checkpoint": true
        },
        {
            "name": "Core Features",
            "description": "Build main functionality",
            "deliverables": ["Login component", "Dashboard component"],
            "estimated_time": "4 hours",
            "qc_checkpoint": false
        },
        {
            "name": "Polish",
            "description": "Final touches and testing",
            "deliverables": ["Responsive styles", "Error handling"],
            "estimated_time": "2 hours",
            "qc_checkpoint": true
        }
    ],
    "qc_checkpoints": ["After setup", "Final review"],
    "architect_instructions": "Focus on component reusability",
    "priority_features": ["Login", "Dashboard"],
    "risk_areas": ["Browser compatibility"],
    "notes": ""
}
```"""

        with patch.object(kickoff_agent, '_generate_with_provider', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = (mock_response, {"total_tokens": 500})

            context = {
                "brief": {
                    "product_name": "Test App",
                    "product_type": "web",
                    "recommendation": "go",
                    "confidence": 0.85,
                    "executive_summary": "A web dashboard for users",
                    "target_customer": {
                        "demographics": "Business professionals",
                        "pain_points": ["Data visualization needs"],
                    },
                    "success_criteria": [
                        {"criterion": "Fast load times", "importance": "critical"},
                    ],
                }
            }

            output = await kickoff_agent.process("Build a web dashboard", context)

            assert output.status == AgentStatus.COMPLETED
            assert output.next_agent == "architect"
            assert "kickoff_plan" in output.artifacts
            assert output.artifacts["type"] == "kickoff_plan"

            plan = output.artifacts["kickoff_plan"]
            assert plan["project_name"] == "Test App"
            assert plan["product_type"] == "web"
            assert len(plan["phases"]) == 3
            assert len(plan["qc_checkpoints"]) == 2

    def test_build_kickoff_prompt(self, kickoff_agent):
        """Test prompt building includes Brief data."""
        brief = {
            "product_name": "Daily Planner",
            "product_type": "printable",
            "confidence": 0.9,
            "executive_summary": "A daily planner for busy professionals",
            "target_customer": {
                "demographics": "Working professionals 25-45",
                "pain_points": ["Time management", "Task tracking"],
            },
            "success_criteria": [
                {"criterion": "Print quality", "importance": "critical"},
            ],
            "swot": {
                "strengths": ["Simple design"],
                "threats": ["Competitive market"],
            },
        }

        context = {
            "project_identity": {
                "product_type": "printable",
                "product_type_name": "Printable",
            }
        }

        prompt = kickoff_agent._build_kickoff_prompt(brief, context)

        assert "Daily Planner" in prompt
        assert "printable" in prompt.lower()
        assert "90%" in prompt  # confidence
        assert "busy professionals" in prompt
        assert "Project Identity" in prompt
        assert "LOCKED" in prompt

    def test_parse_kickoff_plan_valid_json(self, kickoff_agent):
        """Test parsing valid JSON response."""
        response = """{
            "project_name": "Test",
            "product_type": "document",
            "scope": {"in_scope": ["Writing"], "out_of_scope": []},
            "phases": [{"name": "Write", "description": "Content", "deliverables": [], "qc_checkpoint": true}],
            "qc_checkpoints": ["Review"],
            "architect_instructions": "Focus on structure",
            "priority_features": [],
            "risk_areas": []
        }"""

        plan = kickoff_agent._parse_kickoff_plan(response)

        assert plan.project_name == "Test"
        assert plan.product_type == "document"
        assert len(plan.phases) == 1

    def test_parse_kickoff_plan_with_markdown(self, kickoff_agent):
        """Test parsing JSON in markdown code block."""
        response = """Here's the kickoff plan:

```json
{
    "project_name": "Markdown Test",
    "product_type": "web",
    "scope": {"in_scope": ["UI"], "out_of_scope": []},
    "phases": [],
    "qc_checkpoints": [],
    "architect_instructions": "Build it",
    "priority_features": [],
    "risk_areas": []
}
```

This plan covers everything."""

        plan = kickoff_agent._parse_kickoff_plan(response)

        assert plan.project_name == "Markdown Test"
        assert plan.product_type == "web"

    def test_parse_kickoff_plan_invalid_json(self, kickoff_agent):
        """Test parsing handles invalid JSON gracefully."""
        response = "This is not valid JSON at all"

        plan = kickoff_agent._parse_kickoff_plan(response)

        # Should return a minimal fallback plan
        assert plan.project_name == "Unknown"
        assert plan.product_type == "unknown"
        assert "parsing failed" in plan.architect_instructions.lower()


class TestBuildPhase:
    """Tests for BuildPhase dataclass."""

    def test_build_phase_to_dict(self):
        """Test BuildPhase serialization."""
        phase = BuildPhase(
            name="Development",
            description="Build core features",
            deliverables=["Component A", "Component B"],
            estimated_time="4 hours",
            qc_checkpoint=True,
        )

        result = phase.to_dict()

        assert result["name"] == "Development"
        assert result["description"] == "Build core features"
        assert len(result["deliverables"]) == 2
        assert result["estimated_time"] == "4 hours"
        assert result["qc_checkpoint"] is True

    def test_build_phase_from_dict(self):
        """Test BuildPhase deserialization."""
        data = {
            "name": "Testing",
            "description": "Run tests",
            "deliverables": ["Test results"],
            "estimated_time": "1 hour",
            "qc_checkpoint": False,
        }

        phase = BuildPhase.from_dict(data)

        assert phase.name == "Testing"
        assert phase.qc_checkpoint is False

    def test_build_phase_defaults(self):
        """Test BuildPhase default values."""
        phase = BuildPhase(name="Minimal", description="Just a phase")

        assert phase.deliverables == []
        assert phase.estimated_time == ""
        assert phase.qc_checkpoint is False
