"""
Code Assembler - Post-processes Mason output to create runnable code.

Fixes common issues:
- Merges code fragments into complete files
- Adds missing imports
- Creates entry points
- Fixes undefined references
"""

import re
import ast
from typing import Optional
from dataclasses import dataclass, field


# Common imports that should be added when certain patterns are detected
IMPORT_PATTERNS = {
    # Python patterns
    "python": {
        "@app.": ["from fastapi import FastAPI", "app = FastAPI()"],
        "click.": ["import click"],
        "@click.": ["import click"],
        "requests.": ["import requests"],
        "json.": ["import json"],
        "os.": ["import os"],
        "sys.": ["import sys"],
        "Path(": ["from pathlib import Path"],
        "datetime": ["from datetime import datetime"],
        "typing": ["from typing import Optional, List, Dict"],
        "BaseModel": ["from pydantic import BaseModel"],
        "JSONResponse": ["from fastapi.responses import JSONResponse"],
        "Form(": ["from fastapi import Form"],
        "HTTPException": ["from fastapi import HTTPException"],
        "asyncio": ["import asyncio"],
        "aiohttp": ["import aiohttp"],
    },
    # JavaScript patterns
    "javascript": {
        "express()": ["const express = require('express');", "const app = express();"],
        "useState": ["import { useState } from 'react';"],
        "useEffect": ["import { useEffect } from 'react';"],
        "axios.": ["import axios from 'axios';"],
        "fetch(": [],  # Built-in, no import needed
    }
}

# Entry point templates
ENTRY_POINTS = {
    "python": '''
if __name__ == "__main__":
    {entry_call}
''',
    "python_fastapi": '''
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''',
    "python_click": '''
if __name__ == "__main__":
    main()
'''
}


@dataclass
class FileAnalysis:
    """Analysis of a single code file."""
    filename: str
    language: str
    content: str
    imports: list[str] = field(default_factory=list)
    definitions: list[str] = field(default_factory=list)  # Functions, classes defined
    references: list[str] = field(default_factory=list)  # Variables/functions used
    undefined: list[str] = field(default_factory=list)  # References without definitions
    has_entry_point: bool = False
    is_fragment: bool = False
    syntax_valid: bool = True
    syntax_error: Optional[str] = None


@dataclass
class AssemblyResult:
    """Result of code assembly."""
    files: dict[str, str]  # filename -> assembled code
    issues_fixed: list[str]
    remaining_issues: list[str]
    is_runnable: bool


class CodeAssembler:
    """Assembles code fragments into complete, runnable files."""

    def __init__(self):
        self.analyses: dict[str, FileAnalysis] = {}

    def analyze_file(self, filename: str, content: str) -> FileAnalysis:
        """Analyze a single file for completeness."""
        language = self._detect_language(filename)
        analysis = FileAnalysis(
            filename=filename,
            language=language,
            content=content
        )

        if language == "python":
            self._analyze_python(analysis)
        elif language in ("javascript", "typescript"):
            self._analyze_javascript(analysis)

        return analysis

    def _detect_language(self, filename: str) -> str:
        """Detect language from filename."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "jsx": "javascript",
            "tsx": "typescript",
            "json": "json",
            "html": "html",
            "css": "css",
            "sh": "bash",
            "md": "markdown",
        }.get(ext, "unknown")

    def _analyze_python(self, analysis: FileAnalysis):
        """Analyze Python code."""
        content = analysis.content

        # Check syntax
        try:
            tree = ast.parse(content)
            analysis.syntax_valid = True
        except SyntaxError as e:
            analysis.syntax_valid = False
            analysis.syntax_error = f"Line {e.lineno}: {e.msg}"
            return

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    analysis.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    analysis.imports.append(node.module)

        # Extract definitions (functions, classes)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                analysis.definitions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                analysis.definitions.append(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        analysis.definitions.append(target.id)

        # Check for entry point
        analysis.has_entry_point = '__name__' in content and '__main__' in content

        # Detect undefined references
        # Check for common patterns that indicate fragments
        if "@app." in content:
            if "app" not in analysis.definitions and "fastapi" not in " ".join(analysis.imports).lower():
                analysis.undefined.append("app (FastAPI instance)")
                analysis.is_fragment = True

        # Check for requests usage - look for actual import statement
        if "requests." in content or "requests.get" in content:
            has_requests_import = any(
                "import requests" in line
                for line in content.split("\n")
            )
            if not has_requests_import:
                analysis.undefined.append("requests")
                analysis.is_fragment = True

        if "click." in content and "click" not in analysis.imports:
            analysis.undefined.append("click")
            analysis.is_fragment = True

        # Check for JSONResponse - look for actual import statement
        if "JSONResponse" in content:
            has_jsonresponse_import = any(
                "JSONResponse" in line
                for line in content.split("\n")
                if "import" in line
            )
            if not has_jsonresponse_import:
                analysis.undefined.append("JSONResponse")
                analysis.is_fragment = True

    def _analyze_javascript(self, analysis: FileAnalysis):
        """Analyze JavaScript code (basic analysis)."""
        content = analysis.content

        # Extract imports (basic regex)
        import_patterns = [
            r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'require\([\'"]([^\'"]+)[\'"]\)',
        ]
        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                analysis.imports.append(match.group(1))

        # Check for common undefined references
        if "express()" in content and "express" not in " ".join(analysis.imports):
            analysis.undefined.append("express")
            analysis.is_fragment = True

    def assemble(self, files: dict[str, str]) -> AssemblyResult:
        """Assemble multiple files into complete, runnable code."""
        issues_fixed = []
        remaining_issues = []
        assembled_files = {}

        # Analyze all files
        for filename, content in files.items():
            self.analyses[filename] = self.analyze_file(filename, content)

        # Find Python files that need assembly
        python_files = {k: v for k, v in self.analyses.items() if v.language == "python"}

        # Check for fragmented FastAPI app
        fastapi_fragments = [f for f, a in python_files.items() if "@app." in a.content and a.is_fragment]
        fastapi_main = [f for f, a in python_files.items() if "app = FastAPI" in a.content or "app=FastAPI" in a.content]

        if fastapi_fragments and not fastapi_main:
            # Need to create a main.py that combines fragments
            main_content = self._create_fastapi_main(fastapi_fragments)
            assembled_files["main.py"] = main_content
            issues_fixed.append(f"Created main.py combining {len(fastapi_fragments)} FastAPI fragments")

        # Process each file
        for filename, analysis in self.analyses.items():
            if filename in assembled_files:
                continue  # Already handled

            content = analysis.content

            # Fix missing imports
            if analysis.language == "python":
                content, fixed = self._fix_python_imports(content, analysis)
                issues_fixed.extend(fixed)

            # Add entry point if missing
            if analysis.language == "python" and not analysis.has_entry_point:
                if "click" in " ".join(analysis.imports) and "main" in analysis.definitions:
                    content += ENTRY_POINTS["python_click"]
                    issues_fixed.append(f"{filename}: Added click entry point")
                elif "@app." in content or "FastAPI" in content:
                    content += ENTRY_POINTS["python_fastapi"]
                    issues_fixed.append(f"{filename}: Added FastAPI entry point")

            assembled_files[filename] = content

            # Re-analyze assembled content to check remaining issues
            assembled_analysis = self.analyze_file(filename, content)
            if not assembled_analysis.syntax_valid:
                remaining_issues.append(f"{filename}: Syntax error - {assembled_analysis.syntax_error}")
            if assembled_analysis.undefined:
                for undef in assembled_analysis.undefined:
                    remaining_issues.append(f"{filename}: Still undefined - {undef}")

        # Determine if runnable - check assembled files, not original analyses
        has_entry = any(
            "__main__" in content
            for content in assembled_files.values()
        )
        is_runnable = len(remaining_issues) == 0 and has_entry

        return AssemblyResult(
            files=assembled_files,
            issues_fixed=issues_fixed,
            remaining_issues=remaining_issues,
            is_runnable=is_runnable
        )

    def _fix_python_imports(self, content: str, analysis: FileAnalysis) -> tuple[str, list[str]]:
        """Add missing imports to Python code."""
        fixed = []
        imports_to_add = []

        for pattern, imports in IMPORT_PATTERNS["python"].items():
            if pattern in content:
                for imp in imports:
                    # Check if import already exists in the import section
                    # Look for actual import statement, not just the name in code
                    imp_name = imp.split()[-1] if "import" in imp else imp
                    already_imported = any(
                        f"import {imp_name}" in line or f"from {imp_name}" in line
                        for line in content.split("\n")
                        if line.strip().startswith(("import ", "from "))
                    )
                    if not already_imported and imp not in imports_to_add:
                        imports_to_add.append(imp)
                        fixed.append(f"{analysis.filename}: Added '{imp}'")

        if imports_to_add:
            # Insert imports at the top (after any existing imports or docstrings)
            lines = content.split("\n")
            insert_pos = 0

            # Find where imports end
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    insert_pos = i + 1
                elif stripped.startswith('"""') or stripped.startswith("'''"):
                    # Skip docstrings
                    if i == 0:
                        insert_pos = 1

            # Insert new imports
            for imp in imports_to_add:
                lines.insert(insert_pos, imp)
                insert_pos += 1

            content = "\n".join(lines)

        return content, fixed

    def _create_fastapi_main(self, fragment_files: list[str]) -> str:
        """Create a main.py that combines FastAPI fragments."""
        imports = [
            "from fastapi import FastAPI, HTTPException, Form",
            "from fastapi.responses import JSONResponse",
            "from pydantic import BaseModel",
            "import requests",
            "import json",
        ]

        main_content = "\n".join(imports) + "\n\n"
        main_content += "app = FastAPI()\n\n"

        # Extract route handlers from fragments
        for filename in fragment_files:
            analysis = self.analyses[filename]
            content = analysis.content

            # Extract function definitions (routes)
            lines = content.split("\n")
            in_function = False
            function_lines = []

            for line in lines:
                if line.strip().startswith("@app."):
                    in_function = True
                    function_lines.append(line)
                elif in_function:
                    if line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                        in_function = False
                        main_content += "\n".join(function_lines) + "\n\n"
                        function_lines = []
                    else:
                        function_lines.append(line)

            if function_lines:
                main_content += "\n".join(function_lines) + "\n\n"

        main_content += ENTRY_POINTS["python_fastapi"]

        return main_content


def assemble_code(files: dict[str, str]) -> AssemblyResult:
    """Convenience function to assemble code files."""
    assembler = CodeAssembler()
    return assembler.assemble(files)
