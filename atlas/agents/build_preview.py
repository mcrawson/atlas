"""
Build Preview Generator

Extracts preview-able content from Mason's build output and generates
visual representations for different types of projects.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class PreviewType(Enum):
    """Types of previews we can generate."""
    HTML = "html"           # Full HTML/CSS preview (iframe)
    COMPONENT_TREE = "tree" # UI component hierarchy
    ARCHITECTURE = "arch"   # ASCII architecture diagram
    API = "api"             # API endpoints table
    DATABASE = "db"         # Database schema
    TERMINAL = "terminal"   # CLI output simulation
    PRINTABLE = "printable" # Print-ready HTML (for physical products)
    NONE = "none"           # No preview available


@dataclass
class CodeBlock:
    """A code block extracted from output."""
    language: str
    code: str
    filename: Optional[str] = None


@dataclass
class BuildPreview:
    """Generated preview from build output."""
    preview_type: PreviewType
    title: str
    content: str  # HTML content for preview
    code_blocks: List[CodeBlock] = field(default_factory=list)
    files_list: List[str] = field(default_factory=list)
    component_tree: Optional[Dict] = None
    api_endpoints: List[Dict] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)  # Generated file paths (PDFs, etc.)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preview_type": self.preview_type.value,
            "title": self.title,
            "content": self.content,
            "code_blocks": [
                {"language": cb.language, "code": cb.code, "filename": cb.filename}
                for cb in self.code_blocks
            ],
            "files_list": self.files_list,
            "component_tree": self.component_tree,
            "api_endpoints": self.api_endpoints,
            "artifacts": self.artifacts,
        }


class BuildPreviewGenerator:
    """
    Generates visual previews from Mason's build output.

    Features:
    - Extracts code blocks (HTML, CSS, JS, Python, etc.)
    - Generates live HTML/CSS previews
    - Creates ASCII architecture diagrams
    - Builds component tree visualizations
    - Displays API endpoint tables
    """

    def __init__(self):
        self.code_block_pattern = re.compile(
            r'```(\w+)?\s*\n(.*?)```',
            re.DOTALL
        )
        self.file_header_pattern = re.compile(
            r'(?:###?\s*)?(?:`?([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)`?)\s*\n```'
        )

    def generate_preview(self, build_output: str, project_context: Optional[Dict] = None) -> BuildPreview:
        """
        Generate a preview from Mason's build output.

        Args:
            build_output: The raw output from Mason agent
            project_context: Optional context about the project type

        Returns:
            BuildPreview with appropriate visualization
        """
        # Extract all code blocks
        code_blocks = self._extract_code_blocks(build_output)
        files_list = self._extract_files_list(build_output)

        # Determine preview type based on code content
        preview_type = self._determine_preview_type(code_blocks, project_context)

        # Generate appropriate preview
        if preview_type == PreviewType.HTML:
            return self._generate_html_preview(code_blocks, files_list)
        elif preview_type == PreviewType.PRINTABLE:
            return self._generate_printable_preview(code_blocks, files_list, project_context)
        elif preview_type == PreviewType.COMPONENT_TREE:
            return self._generate_component_tree(code_blocks, files_list)
        elif preview_type == PreviewType.ARCHITECTURE:
            return self._generate_architecture_diagram(build_output, code_blocks, files_list)
        elif preview_type == PreviewType.API:
            return self._generate_api_preview(code_blocks, files_list)
        elif preview_type == PreviewType.DATABASE:
            return self._generate_db_preview(code_blocks, files_list)
        elif preview_type == PreviewType.TERMINAL:
            return self._generate_terminal_preview(code_blocks, files_list)
        else:
            return self._generate_code_only_preview(code_blocks, files_list)

    def _extract_code_blocks(self, text: str) -> List[CodeBlock]:
        """Extract all code blocks from the output."""
        blocks = []

        # Find file headers before code blocks
        lines = text.split('\n')
        current_filename = None

        for match in self.code_block_pattern.finditer(text):
            language = match.group(1) or "text"
            code = match.group(2).strip()

            # Try to find filename from context
            start_pos = match.start()
            preceding_text = text[max(0, start_pos - 200):start_pos]

            filename = None
            file_match = re.search(r'(?:###?\s*)?`([^`]+\.[a-zA-Z0-9]+)`', preceding_text)
            if file_match:
                filename = file_match.group(1)

            blocks.append(CodeBlock(
                language=language.lower(),
                code=code,
                filename=filename
            ))

        return blocks

    def _extract_files_list(self, text: str) -> List[str]:
        """Extract the list of files from Mason's output."""
        files = []

        # Look for "Files Modified" section
        if "## Files Modified" in text or "## Files Created" in text:
            section_pattern = re.compile(
                r'##\s*Files\s*(?:Modified|Created).*?\n(.*?)(?=\n##|\Z)',
                re.DOTALL | re.IGNORECASE
            )
            match = section_pattern.search(text)
            if match:
                section = match.group(1)
                for line in section.split('\n'):
                    # Match "- `path/to/file.py`" or "- path/to/file.py"
                    file_match = re.match(r'-\s*`?([^`\s]+\.[a-zA-Z0-9]+)`?', line.strip())
                    if file_match:
                        files.append(file_match.group(1))

        return files

    def _determine_preview_type(
        self,
        code_blocks: List[CodeBlock],
        context: Optional[Dict]
    ) -> PreviewType:
        """Determine the best preview type based on code content."""
        languages = {cb.language for cb in code_blocks}

        # Check context for physical product category
        if context:
            project_category = context.get("project_category", "")
            if project_category == "physical":
                return PreviewType.PRINTABLE

        # Check for printable content (HTML with @page rules or print-specific CSS)
        for cb in code_blocks:
            if cb.language in ['html', 'css']:
                if any(pattern in cb.code.lower() for pattern in
                       ['@page', '@media print', 'page-break', 'print-ready', 'printable']):
                    return PreviewType.PRINTABLE

        # Check for web frontend (HTML/CSS)
        if 'html' in languages or 'css' in languages:
            return PreviewType.HTML

        # Check for React/Vue/component-based
        if any(lang in languages for lang in ['jsx', 'tsx', 'vue', 'svelte']):
            return PreviewType.COMPONENT_TREE

        # Check for API/backend
        if any(lang in languages for lang in ['python', 'go', 'rust', 'java']):
            # Look for Flask/FastAPI/Express patterns
            for cb in code_blocks:
                if any(pattern in cb.code.lower() for pattern in
                       ['@app.route', '@router', 'app.get', 'app.post', 'endpoint', 'def get_', 'def post_']):
                    return PreviewType.API

        # Check for database/SQL
        if 'sql' in languages:
            return PreviewType.DATABASE

        # Check for CLI/shell
        if any(lang in languages for lang in ['bash', 'shell', 'sh', 'zsh']):
            return PreviewType.TERMINAL

        # Default: try to generate architecture from structure
        if len(code_blocks) > 2:
            return PreviewType.ARCHITECTURE

        return PreviewType.NONE

    def _generate_html_preview(
        self,
        code_blocks: List[CodeBlock],
        files_list: List[str]
    ) -> BuildPreview:
        """Generate an HTML/CSS preview that can be rendered in an iframe."""
        html_content = ""
        css_content = ""
        js_content = ""

        for cb in code_blocks:
            if cb.language == 'html':
                html_content += cb.code + "\n"
            elif cb.language == 'css':
                css_content += cb.code + "\n"
            elif cb.language in ['javascript', 'js']:
                js_content += cb.code + "\n"

        # Build complete HTML document for iframe
        preview_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            padding: 1rem;
        }}
        {css_content}
    </style>
</head>
<body>
{html_content if html_content else '<div style="text-align:center;color:#666;padding:2rem;">HTML Preview</div>'}
<script>
{js_content}
</script>
</body>
</html>"""

        return BuildPreview(
            preview_type=PreviewType.HTML,
            title="Live Preview",
            content=preview_html,
            code_blocks=code_blocks,
            files_list=files_list,
        )

    def _generate_printable_preview(
        self,
        code_blocks: List[CodeBlock],
        files_list: List[str],
        context: Optional[Dict] = None
    ) -> BuildPreview:
        """Generate a printable preview for physical products (planners, journals, etc.)."""
        html_blocks = [cb for cb in code_blocks if cb.language == 'html']
        css_blocks = [cb for cb in code_blocks if cb.language == 'css']

        # Combine all HTML content
        all_html = "\n".join(cb.code for cb in html_blocks)
        all_css = "\n".join(cb.code for cb in css_blocks)

        # Generate PDF artifacts if possible
        artifacts = []
        try:
            from atlas.utils.pdf_generator import get_pdf_generator

            project_name = "planner"
            if context and context.get("name"):
                project_name = context["name"].lower().replace(" ", "-")

            pdf_gen = get_pdf_generator()

            # Save each HTML block as a separate file
            for i, cb in enumerate(html_blocks):
                filename = cb.filename or f"page_{i+1}"
                if not filename.endswith('.html'):
                    filename = filename.replace('.html', '') + '.html'

                # Ensure complete HTML document
                html_content = cb.code
                if not html_content.strip().startswith("<!DOCTYPE"):
                    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{filename}</title>
    <style>
        @page {{ size: letter; margin: 0.5in; }}
        @media print {{ .page {{ page-break-after: always; }} }}
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; }}
        {all_css}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""

                output_path = pdf_gen.html_to_pdf(html_content, f"{project_name}_{filename.replace('.html', '')}")
                if output_path:
                    artifacts.append(str(output_path))

        except ImportError:
            pass  # PDF generation not available
        except Exception as e:
            print(f"[BuildPreview] PDF generation failed: {e}")

        # Build preview HTML with print styling
        preview_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #e0e0e0;
            padding: 20px;
        }}
        .print-preview-container {{
            max-width: 850px;
            margin: 0 auto;
        }}
        .print-header {{
            background: #333;
            color: white;
            padding: 10px 20px;
            border-radius: 8px 8px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .print-header h3 {{ margin: 0; font-size: 14px; }}
        .print-actions {{
            display: flex;
            gap: 10px;
        }}
        .print-btn {{
            background: #4CAF50;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }}
        .print-btn:hover {{ background: #45a049; }}
        .page-container {{
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }}
        .page {{
            width: 8.5in;
            min-height: 11in;
            padding: 0.5in;
            background: white;
            position: relative;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .print-header, .print-actions {{ display: none; }}
            .page-container {{ box-shadow: none; margin: 0; }}
            .page {{ page-break-after: always; }}
        }}
        {all_css}
    </style>
</head>
<body>
    <div class="print-preview-container">
        <div class="print-header">
            <h3>🖨️ Print Preview - Physical Product</h3>
            <div class="print-actions">
                <button class="print-btn" onclick="window.print()">Print / Save PDF</button>
            </div>
        </div>
        <div class="page-container">
{all_html if all_html else '<div class="page"><p style="text-align:center;color:#999;padding-top:4in;">Printable content will appear here</p></div>'}
        </div>
    </div>
</body>
</html>"""

        # Add artifact info to preview
        artifact_info = ""
        if artifacts:
            artifact_info = f"<p><strong>Generated files:</strong> {', '.join(artifacts)}</p>"

        return BuildPreview(
            preview_type=PreviewType.PRINTABLE,
            title="Print Preview",
            content=preview_html,
            code_blocks=code_blocks,
            files_list=files_list,
            artifacts=artifacts,
        )

    def _generate_component_tree(
        self,
        code_blocks: List[CodeBlock],
        files_list: List[str]
    ) -> BuildPreview:
        """Generate a component tree visualization for React/Vue projects."""
        components = []

        for cb in code_blocks:
            if cb.language in ['jsx', 'tsx', 'javascript', 'typescript', 'vue']:
                # Extract component names
                patterns = [
                    r'function\s+(\w+)\s*\(',  # function Component()
                    r'const\s+(\w+)\s*=\s*\(',  # const Component = ()
                    r'export\s+(?:default\s+)?(?:function|const)\s+(\w+)',  # export
                    r'class\s+(\w+)\s+extends',  # class Component extends
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, cb.code)
                    for match in matches:
                        if match[0].isupper():  # Component names start with uppercase
                            components.append({
                                "name": match,
                                "file": cb.filename or "unknown",
                            })

        # Build tree HTML
        tree_html = '<div class="component-tree">\n'
        tree_html += '  <div class="tree-header">Component Structure</div>\n'
        tree_html += '  <div class="tree-body">\n'

        for comp in components:
            tree_html += f'    <div class="tree-node">\n'
            tree_html += f'      <span class="node-icon">📦</span>\n'
            tree_html += f'      <span class="node-name">{comp["name"]}</span>\n'
            tree_html += f'      <span class="node-file">{comp["file"]}</span>\n'
            tree_html += f'    </div>\n'

        if not components:
            tree_html += '    <div class="tree-empty">No components detected</div>\n'

        tree_html += '  </div>\n'
        tree_html += '</div>'

        return BuildPreview(
            preview_type=PreviewType.COMPONENT_TREE,
            title="Component Tree",
            content=tree_html,
            code_blocks=code_blocks,
            files_list=files_list,
            component_tree={"components": components},
        )

    def _generate_architecture_diagram(
        self,
        build_output: str,
        code_blocks: List[CodeBlock],
        files_list: List[str]
    ) -> BuildPreview:
        """Generate an ASCII-style architecture diagram."""
        # Try to extract existing ASCII diagrams from output
        ascii_pattern = re.compile(r'```(?:ascii|text|diagram)?\s*\n([^`]*?[─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬\+\-\|][^`]*?)```', re.DOTALL)
        ascii_match = ascii_pattern.search(build_output)

        if ascii_match:
            diagram = ascii_match.group(1)
        else:
            # Generate a simple file structure diagram
            diagram = self._generate_file_structure_diagram(files_list, code_blocks)

        diagram_html = f'<pre class="architecture-diagram">{diagram}</pre>'

        return BuildPreview(
            preview_type=PreviewType.ARCHITECTURE,
            title="Architecture Overview",
            content=diagram_html,
            code_blocks=code_blocks,
            files_list=files_list,
        )

    def _generate_file_structure_diagram(
        self,
        files_list: List[str],
        code_blocks: List[CodeBlock]
    ) -> str:
        """Generate a file tree diagram."""
        files = files_list or [cb.filename for cb in code_blocks if cb.filename]

        if not files:
            return """
┌─────────────────────────────────────┐
│           Project Structure          │
├─────────────────────────────────────┤
│  (Files will appear here after      │
│   Mason generates the build)        │
└─────────────────────────────────────┘
"""

        # Build tree structure
        tree = {}
        for filepath in files:
            parts = filepath.split('/')
            current = tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = None  # File (leaf)

        lines = ["📁 Project Root"]
        self._render_tree(tree, lines, "")

        return "\n".join(lines)

    def _render_tree(self, tree: Dict, lines: List[str], prefix: str):
        """Recursively render tree structure."""
        items = list(tree.items())
        for i, (name, subtree) in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "

            if subtree is None:  # File
                icon = self._get_file_icon(name)
                lines.append(f"{prefix}{connector}{icon} {name}")
            else:  # Directory
                lines.append(f"{prefix}{connector}📁 {name}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._render_tree(subtree, lines, new_prefix)

    def _get_file_icon(self, filename: str) -> str:
        """Get an icon for a file based on extension."""
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        icons = {
            'py': '🐍',
            'js': '📜',
            'ts': '📘',
            'jsx': '⚛️',
            'tsx': '⚛️',
            'html': '🌐',
            'css': '🎨',
            'json': '📋',
            'yaml': '📋',
            'yml': '📋',
            'md': '📝',
            'sql': '🗃️',
            'sh': '🔧',
            'bash': '🔧',
        }
        return icons.get(ext, '📄')

    def _generate_api_preview(
        self,
        code_blocks: List[CodeBlock],
        files_list: List[str]
    ) -> BuildPreview:
        """Generate an API endpoints preview."""
        endpoints = []

        for cb in code_blocks:
            # FastAPI/Flask patterns
            route_patterns = [
                r'@(?:app|router)\.(\w+)\([\'"]([^\'"]+)[\'"]',  # @app.get("/path")
                r'@(?:app|router)\.route\([\'"]([^\'"]+)[\'"].*methods\s*=\s*\[([^\]]+)\]',  # Flask
                r'def\s+(get|post|put|delete|patch)_(\w+)',  # def get_users()
            ]

            for pattern in route_patterns:
                matches = re.findall(pattern, cb.code, re.IGNORECASE)
                for match in matches:
                    if len(match) == 2:
                        method, path = match
                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                            endpoints.append({
                                "method": method.upper(),
                                "path": path,
                                "file": cb.filename
                            })

        # Build table HTML
        table_html = '''
<div class="api-preview">
    <div class="api-header">API Endpoints</div>
    <table class="api-table">
        <thead>
            <tr>
                <th>Method</th>
                <th>Path</th>
                <th>File</th>
            </tr>
        </thead>
        <tbody>
'''
        for ep in endpoints:
            method_class = ep['method'].lower()
            table_html += f'''
            <tr>
                <td><span class="method-badge {method_class}">{ep['method']}</span></td>
                <td><code>{ep['path']}</code></td>
                <td>{ep.get('file', '-')}</td>
            </tr>
'''

        if not endpoints:
            table_html += '''
            <tr>
                <td colspan="3" class="no-data">No API endpoints detected</td>
            </tr>
'''

        table_html += '''
        </tbody>
    </table>
</div>
'''

        return BuildPreview(
            preview_type=PreviewType.API,
            title="API Endpoints",
            content=table_html,
            code_blocks=code_blocks,
            files_list=files_list,
            api_endpoints=endpoints,
        )

    def _generate_db_preview(
        self,
        code_blocks: List[CodeBlock],
        files_list: List[str]
    ) -> BuildPreview:
        """Generate a database schema preview."""
        tables = []

        for cb in code_blocks:
            if cb.language == 'sql':
                # Extract CREATE TABLE statements
                create_pattern = re.compile(
                    r'CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);',
                    re.IGNORECASE | re.DOTALL
                )
                for match in create_pattern.finditer(cb.code):
                    table_name = match.group(1)
                    columns_text = match.group(2)

                    columns = []
                    for line in columns_text.split(','):
                        line = line.strip()
                        if line and not line.upper().startswith(('PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK', 'CONSTRAINT')):
                            parts = line.split()
                            if len(parts) >= 2:
                                columns.append({
                                    "name": parts[0],
                                    "type": parts[1],
                                    "constraints": ' '.join(parts[2:]) if len(parts) > 2 else ''
                                })

                    tables.append({
                        "name": table_name,
                        "columns": columns
                    })

        # Build schema HTML
        schema_html = '<div class="db-preview">\n'
        schema_html += '<div class="db-header">Database Schema</div>\n'

        for table in tables:
            schema_html += f'<div class="db-table">\n'
            schema_html += f'  <div class="table-name">🗃️ {table["name"]}</div>\n'
            schema_html += f'  <div class="table-columns">\n'
            for col in table['columns']:
                pk_badge = '🔑 ' if 'PRIMARY' in col['constraints'].upper() else ''
                schema_html += f'    <div class="column">{pk_badge}{col["name"]} <span class="col-type">{col["type"]}</span></div>\n'
            schema_html += f'  </div>\n'
            schema_html += f'</div>\n'

        if not tables:
            schema_html += '<div class="no-data">No tables detected in SQL</div>\n'

        schema_html += '</div>'

        return BuildPreview(
            preview_type=PreviewType.DATABASE,
            title="Database Schema",
            content=schema_html,
            code_blocks=code_blocks,
            files_list=files_list,
        )

    def _generate_terminal_preview(
        self,
        code_blocks: List[CodeBlock],
        files_list: List[str]
    ) -> BuildPreview:
        """Generate a terminal/CLI preview."""
        commands = []

        for cb in code_blocks:
            if cb.language in ['bash', 'shell', 'sh', 'zsh']:
                for line in cb.code.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        commands.append(line)

        terminal_html = '''
<div class="terminal-preview">
    <div class="terminal-header">
        <span class="terminal-dot red"></span>
        <span class="terminal-dot yellow"></span>
        <span class="terminal-dot green"></span>
        <span class="terminal-title">Terminal</span>
    </div>
    <div class="terminal-body">
'''
        for cmd in commands:
            terminal_html += f'<div class="terminal-line"><span class="prompt">$</span> {cmd}</div>\n'

        if not commands:
            terminal_html += '<div class="terminal-line"><span class="prompt">$</span> <span class="cursor">▋</span></div>\n'

        terminal_html += '''
    </div>
</div>
'''

        return BuildPreview(
            preview_type=PreviewType.TERMINAL,
            title="Terminal Commands",
            content=terminal_html,
            code_blocks=code_blocks,
            files_list=files_list,
        )

    def _generate_code_only_preview(
        self,
        code_blocks: List[CodeBlock],
        files_list: List[str]
    ) -> BuildPreview:
        """Generate a simple code overview when no visual preview is possible."""
        summary_html = '<div class="code-summary">\n'
        summary_html += '<div class="summary-header">Build Summary</div>\n'

        if files_list:
            summary_html += '<div class="summary-section">\n'
            summary_html += '  <h4>📁 Files</h4>\n'
            summary_html += '  <ul>\n'
            for f in files_list[:10]:
                summary_html += f'    <li><code>{f}</code></li>\n'
            if len(files_list) > 10:
                summary_html += f'    <li class="more">+{len(files_list) - 10} more</li>\n'
            summary_html += '  </ul>\n'
            summary_html += '</div>\n'

        if code_blocks:
            summary_html += '<div class="summary-section">\n'
            summary_html += '  <h4>📝 Code Blocks</h4>\n'
            summary_html += '  <div class="language-pills">\n'
            lang_counts = {}
            for cb in code_blocks:
                lang_counts[cb.language] = lang_counts.get(cb.language, 0) + 1
            for lang, count in sorted(lang_counts.items()):
                summary_html += f'    <span class="lang-pill">{lang}: {count}</span>\n'
            summary_html += '  </div>\n'
            summary_html += '</div>\n'

        summary_html += '</div>'

        return BuildPreview(
            preview_type=PreviewType.NONE,
            title="Build Summary",
            content=summary_html,
            code_blocks=code_blocks,
            files_list=files_list,
        )
