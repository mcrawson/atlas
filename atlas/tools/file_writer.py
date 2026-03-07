"""File Writer - Parses Mason output and writes actual files."""

import re
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ParsedFile:
    """A file parsed from Mason's output."""
    path: str
    content: str
    language: str = ""
    description: str = ""


@dataclass
class WriteResult:
    """Result of writing files."""
    success: bool
    files_written: list[str] = field(default_factory=list)
    files_failed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    project_dir: str = ""


class FileWriter:
    """Parses Mason output and writes files to disk."""

    def __init__(self, base_dir: Optional[str] = None):
        """Initialize file writer.

        Args:
            base_dir: Base directory for writing files. If None, uses ~/atlas-projects/
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.home() / "atlas-projects"

        self.base_dir.mkdir(parents=True, exist_ok=True)

    def parse_mason_output(self, output: str) -> list[ParsedFile]:
        """Parse Mason's output to extract files.

        Looks for patterns like:
        ### `filename.ext`
        ```language
        code content
        ```

        Args:
            output: Mason's full output text

        Returns:
            List of ParsedFile objects
        """
        files = []

        # Pattern to match file blocks
        # Matches: ### `filename.ext` or ### filename.ext
        # Followed by ```language ... ```
        pattern = r'###\s*`?([^`\n]+)`?\s*\n```(\w*)\n(.*?)```'

        matches = re.finditer(pattern, output, re.DOTALL)

        for match in matches:
            filepath = match.group(1).strip()
            language = match.group(2).strip()
            content = match.group(3)

            # Skip preview/example blocks
            if any(skip in filepath.lower() for skip in ['preview', 'example', 'output', 'terminal']):
                continue

            # Clean up the filepath
            filepath = filepath.strip('`').strip()

            # Skip if it doesn't look like a real file path
            if not filepath or '/' not in filepath and '.' not in filepath:
                continue

            files.append(ParsedFile(
                path=filepath,
                content=content,
                language=language,
            ))

        # Also try to parse README.md from the Generated README section
        readme_pattern = r'## Generated README\.md\s*\n```markdown\n(.*?)```'
        readme_match = re.search(readme_pattern, output, re.DOTALL)
        if readme_match:
            files.append(ParsedFile(
                path="README.md",
                content=readme_match.group(1),
                language="markdown",
            ))

        return files

    def create_project_dir(self, project_name: str) -> Path:
        """Create a project directory.

        Args:
            project_name: Name of the project

        Returns:
            Path to the project directory
        """
        # Sanitize project name
        safe_name = re.sub(r'[^\w\-]', '-', project_name.lower())
        safe_name = re.sub(r'-+', '-', safe_name).strip('-')

        # Add timestamp if directory exists
        project_dir = self.base_dir / safe_name
        if project_dir.exists():
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            project_dir = self.base_dir / f"{safe_name}-{timestamp}"

        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def write_files(
        self,
        files: list[ParsedFile],
        project_dir: Path,
        overwrite: bool = True,
    ) -> WriteResult:
        """Write parsed files to disk.

        Args:
            files: List of ParsedFile objects
            project_dir: Directory to write files to
            overwrite: Whether to overwrite existing files

        Returns:
            WriteResult with status
        """
        result = WriteResult(success=True, project_dir=str(project_dir))

        for file in files:
            try:
                # Construct full path
                file_path = project_dir / file.path

                # Create parent directories
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Check if file exists
                if file_path.exists() and not overwrite:
                    result.files_failed.append(file.path)
                    result.errors.append(f"File exists: {file.path}")
                    continue

                # Write the file
                file_path.write_text(file.content)
                result.files_written.append(file.path)

            except Exception as e:
                result.success = False
                result.files_failed.append(file.path)
                result.errors.append(f"{file.path}: {str(e)}")

        return result

    def write_from_mason_output(
        self,
        output: str,
        project_name: str,
        project_dir: Optional[Path] = None,
    ) -> WriteResult:
        """Parse Mason output and write all files.

        Args:
            output: Mason's full output text
            project_name: Name for the project directory
            project_dir: Optional specific directory (otherwise creates new)

        Returns:
            WriteResult with status
        """
        # Parse files from output
        files = self.parse_mason_output(output)

        if not files:
            return WriteResult(
                success=False,
                errors=["No files found in Mason output"],
            )

        # Create or use project directory
        if project_dir is None:
            project_dir = self.create_project_dir(project_name)

        # Write files
        return self.write_files(files, project_dir)

    def get_project_structure(self, project_dir: Path) -> str:
        """Generate a tree view of the project structure.

        Args:
            project_dir: Project directory path

        Returns:
            ASCII tree representation
        """
        def build_tree(path: Path, prefix: str = "") -> list[str]:
            lines = []
            entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))

            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{entry.name}")

                if entry.is_dir() and not entry.name.startswith('.'):
                    extension = "    " if is_last else "│   "
                    lines.extend(build_tree(entry, prefix + extension))

            return lines

        tree_lines = [project_dir.name + "/"]
        tree_lines.extend(build_tree(project_dir))
        return "\n".join(tree_lines)
