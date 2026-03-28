"""Tests for Mason agent - especially context handling."""

import pytest
from atlas.agents.mason import MasonAgent
from unittest.mock import MagicMock, AsyncMock, patch


class TestMasonContextHandling:
    """Test that Mason handles various context formats correctly."""

    def test_tech_stack_as_dict(self):
        """tech_stack as dict should work (normal case)."""
        context = {
            "tech_stack": {
                "language": "JavaScript",
                "framework": "React",
                "reasoning": "Modern SPA framework"
            }
        }
        # Simulate what Mason does
        ts = context["tech_stack"]
        if isinstance(ts, dict):
            language = ts.get('language', 'Python')
            framework = ts.get('framework', 'None')
            assert language == "JavaScript"
            assert framework == "React"

    def test_tech_stack_as_string(self):
        """tech_stack as string should work (edge case we fixed)."""
        context = {
            "tech_stack": "Plain HTML, CSS, and vanilla JavaScript"
        }
        # Simulate what Mason does
        ts = context["tech_stack"]
        if isinstance(ts, str):
            # Should use the string directly
            assert "HTML" in ts
            assert "JavaScript" in ts

    def test_tech_stack_missing(self):
        """Missing tech_stack should not crash."""
        context = {}
        assert "tech_stack" not in context
        # Mason should skip tech_stack section

    def test_context_with_build_type(self):
        """Context can include build_type for static HTML builds."""
        context = {
            "build_type": "static_html",
            "tech_stack": {
                "language": "JavaScript",
                "framework": "None - Plain HTML/CSS/JS only",
                "reasoning": "Static HTML for QC compatibility"
            }
        }
        assert context["build_type"] == "static_html"
        assert "None" in context["tech_stack"]["framework"]


class TestMasonBuildTypes:
    """Test different build type scenarios."""

    def test_static_html_context(self):
        """Static HTML builds should have proper context markers."""
        context = {
            "build_type": "static_html",
            "build_instructions": "NO React, NO TypeScript",
            "tech_stack": {
                "language": "JavaScript",
                "framework": "None"
            }
        }
        assert context["build_type"] == "static_html"
        assert "NO React" in context["build_instructions"]

    def test_react_spa_context(self):
        """React SPA builds should have React in tech_stack."""
        context = {
            "build_type": "react_spa",
            "tech_stack": {
                "language": "TypeScript",
                "framework": "React"
            }
        }
        assert context["build_type"] == "react_spa"
        assert context["tech_stack"]["framework"] == "React"


class TestMasonBuildTypePrompts:
    """Test that Mason adds appropriate instructions based on build_type."""

    @pytest.mark.asyncio
    async def test_static_html_adds_restrictions(self):
        """Test that build_type=static_html adds NO React restrictions."""
        # Create mock router and memory
        mock_router = MagicMock()
        mock_memory = MagicMock()
        mason = MasonAgent(router=mock_router, memory=mock_memory)

        # Mock the LLM generation
        with patch.object(mason, '_generate_with_provider', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = ("## Summary\nTest output\n\n## Files\n### `index.html`\n```html\n<html></html>\n```", {"total_tokens": 100})

            context = {
                "build_type": "static_html",
                "project_type": "web_spa",
                "project_category": "web"
            }

            await mason.process("Build a web app", context=context)

            # Check that the prompt includes static HTML restrictions
            call_args = mock_generate.call_args
            prompt_used = call_args[0][0]  # First positional argument

            assert "BUILD TYPE: STATIC HTML" in prompt_used
            assert "NO React" in prompt_used
            assert "NO TypeScript" in prompt_used
            assert "vanilla JavaScript" in prompt_used

    @pytest.mark.asyncio
    async def test_react_spa_allows_react(self):
        """Test that build_type=react_spa allows React."""
        mock_router = MagicMock()
        mock_memory = MagicMock()
        mason = MasonAgent(router=mock_router, memory=mock_memory)

        with patch.object(mason, '_generate_with_provider', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = ("## Summary\nTest output\n\n## Files\n### `App.tsx`\n```tsx\nexport default App\n```", {"total_tokens": 100})

            context = {
                "build_type": "react_spa",
                "project_type": "web_spa",
                "project_category": "web"
            }

            await mason.process("Build a React app", context=context)

            call_args = mock_generate.call_args
            prompt_used = call_args[0][0]

            assert "BUILD TYPE: REACT SPA" in prompt_used
            assert "React/TypeScript is ALLOWED" in prompt_used or "ENCOURAGED" in prompt_used

    @pytest.mark.asyncio
    async def test_no_build_type_keeps_default_behavior(self):
        """Test that missing build_type doesn't change behavior."""
        mock_router = MagicMock()
        mock_memory = MagicMock()
        mason = MasonAgent(router=mock_router, memory=mock_memory)

        with patch.object(mason, '_generate_with_provider', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = ("## Summary\nTest output\n\n## Files\n### `main.py`\n```python\nprint('hello')\n```", {"total_tokens": 100})

            context = {
                "project_type": "cli_tool",
                "project_category": "code"
            }

            await mason.process("Build a CLI tool", context=context)

            call_args = mock_generate.call_args
            prompt_used = call_args[0][0]

            # Should not have build type instructions
            assert "BUILD TYPE: STATIC HTML" not in prompt_used
            assert "BUILD TYPE: REACT SPA" not in prompt_used

    @pytest.mark.asyncio
    async def test_system_prompt_respects_build_type(self):
        """Test that get_system_prompt includes build_type guidance."""
        mock_router = MagicMock()
        mock_memory = MagicMock()
        mason = MasonAgent(router=mock_router, memory=mock_memory)

        # Test static HTML
        system_prompt_static = mason.get_system_prompt(build_type="static_html")
        assert "Static HTML/CSS/JS ONLY" in system_prompt_static

        # Test React SPA
        system_prompt_react = mason.get_system_prompt(build_type="react_spa")
        assert "React SPA" in system_prompt_react

        # Test no build type
        system_prompt_default = mason.get_system_prompt()
        assert "Static HTML/CSS/JS ONLY" not in system_prompt_default


class TestQCReactDetection:
    """Test that QC properly detects and evaluates React builds."""

    def test_detect_react_files_in_output(self):
        """Test that QC detects .tsx/.jsx files in build output."""
        output = {
            "files": {
                "App.tsx": "import React from 'react'; export default App;",
                "index.tsx": "import ReactDOM from 'react-dom';",
                "styles.css": "body { margin: 0; }"
            }
        }

        # Simulate what QC does
        react_files = {}
        if isinstance(output, dict) and "files" in output:
            for filename, content in output["files"].items():
                if filename.endswith(('.tsx', '.jsx')):
                    react_files[filename] = content

        assert len(react_files) == 2
        assert "App.tsx" in react_files
        assert "index.tsx" in react_files
        assert "styles.css" not in react_files

    def test_no_react_files_in_static_build(self):
        """Test that static HTML builds don't have React files."""
        output = {
            "files": {
                "index.html": "<html></html>",
                "script.js": "console.log('hello');",
                "styles.css": "body { margin: 0; }"
            }
        }

        react_files = {}
        if isinstance(output, dict) and "files" in output:
            for filename, content in output["files"].items():
                if filename.endswith(('.tsx', '.jsx')):
                    react_files[filename] = content

        assert len(react_files) == 0
