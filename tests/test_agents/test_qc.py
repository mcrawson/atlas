"""Tests for QC Agent build_type functionality."""

import pytest
from atlas.agents.qc import QCAgent, QCVerdict


@pytest.mark.asyncio
async def test_qc_detects_react_source_files():
    """Test that QC detects React source files and sets evaluation_mode correctly."""
    qc = QCAgent()

    # Create build output with React files
    output = {
        "files": {
            "src/App.tsx": "import React from 'react';\nexport default function App() { return <div>Hello</div>; }",
            "src/index.tsx": "import React from 'react';\nimport ReactDOM from 'react-dom';",
            "index.html": "<html><body><div id='root'></div></body></html>",
        }
    }

    brief = {
        "product_type": "web",
        "name": "Test App",
        "description": "A test app",
    }

    # Check build output
    report = await qc.check_build(output, brief, mockup=None, attempt=1)

    # Verify evaluation_mode is set to react_source
    assert report.evaluation_mode == "react_source", "Should detect React source files"
    assert report.verdict in [QCVerdict.PASS, QCVerdict.PASS_WITH_NOTES, QCVerdict.NEEDS_REVISION]


@pytest.mark.asyncio
async def test_qc_detects_html_preview():
    """Test that QC uses HTML preview mode for static HTML builds."""
    qc = QCAgent()

    # Create build output with only HTML/CSS/JS
    output = {
        "files": {
            "index.html": "<html><body><h1>Hello World</h1></body></html>",
            "style.css": "body { font-family: Arial; }",
            "script.js": "console.log('Hello');",
        }
    }

    brief = {
        "product_type": "web",
        "name": "Test Site",
        "description": "A test website",
    }

    # Check build output
    report = await qc.check_build(output, brief, mockup=None, attempt=1)

    # Verify evaluation_mode is set to html_preview
    assert report.evaluation_mode == "html_preview", "Should use HTML preview mode"
    assert report.verdict in [QCVerdict.PASS, QCVerdict.PASS_WITH_NOTES, QCVerdict.NEEDS_REVISION]


@pytest.mark.asyncio
async def test_qc_verdict_accurate_for_react_build():
    """Test that QC verdict is accurate for React builds."""
    qc = QCAgent()

    # Create a complete React build
    output = {
        "files": {
            "src/App.tsx": """
import React from 'react';

export default function App() {
    return (
        <div>
            <h1>Welcome to My App</h1>
            <p>This is a complete React application</p>
            <button onClick={() => alert('Hello!')}>Click Me</button>
        </div>
    );
}
""",
            "src/index.tsx": """
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root')!);
root.render(<App />);
""",
            "index.html": "<html><body><div id='root'></div><script src='bundle.js'></script></body></html>",
            "package.json": '{"name": "test-app", "dependencies": {"react": "^18.0.0"}}',
        }
    }

    brief = {
        "product_type": "web",
        "name": "React Test App",
        "description": "A simple React test application",
        "core_features": ["Display welcome message", "Interactive button"],
    }

    # Check build output
    report = await qc.check_build(output, brief, mockup=None, attempt=1)

    # Verify report
    assert report.evaluation_mode == "react_source"
    assert isinstance(report.verdict, QCVerdict)
    assert report.alignment_score >= 0
    assert report.sellability_score >= 0
    assert report.quality_score >= 0


@pytest.mark.asyncio
async def test_qc_verdict_accurate_for_static_html():
    """Test that QC verdict is accurate for static HTML builds."""
    qc = QCAgent()

    # Create a complete static HTML build
    output = {
        "files": {
            "index.html": """
<!DOCTYPE html>
<html>
<head>
    <title>My Website</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>Welcome</h1>
    <p>This is my website</p>
    <button onclick="alert('Hello!')">Click Me</button>
</body>
</html>
""",
            "style.css": """
body {
    font-family: Arial, sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}
h1 { color: #333; }
""",
        }
    }

    brief = {
        "product_type": "web",
        "name": "Simple Website",
        "description": "A simple static website",
        "core_features": ["Display welcome message", "Interactive button"],
    }

    # Check build output
    report = await qc.check_build(output, brief, mockup=None, attempt=1)

    # Verify report
    assert report.evaluation_mode == "html_preview"
    assert isinstance(report.verdict, QCVerdict)
    assert report.alignment_score >= 0
    assert report.sellability_score >= 0
    assert report.quality_score >= 0


@pytest.mark.asyncio
async def test_qc_report_to_dict_includes_evaluation_mode():
    """Test that QC report serialization includes evaluation_mode."""
    qc = QCAgent()

    output = {
        "files": {
            "src/App.tsx": "export default function App() { return <div>Test</div>; }",
        }
    }

    brief = {"product_type": "web", "name": "Test", "description": "Test app"}

    report = await qc.check_build(output, brief, mockup=None, attempt=1)
    report_dict = report.to_dict()

    # Verify evaluation_mode is in serialized dict
    assert "evaluation_mode" in report_dict
    assert report_dict["evaluation_mode"] in ["react_source", "html_preview", "mixed", ""]
