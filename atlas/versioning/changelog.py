"""Changelog generator for ATLAS products.

Generates and manages CHANGELOG.md files based on agent outputs and updates.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import (
    Version,
    UpdateType,
    ChangeCategory,
    ChangelogEntry,
    ChangelogRelease,
    UpdateContext,
)


class ChangelogGenerator:
    """Generates changelog entries from agent outputs and update context."""

    # Patterns to detect change types in agent output
    CHANGE_PATTERNS = {
        ChangeCategory.ADDED: [
            r'(?:added|new|created|implemented|introduced)\s+(.+)',
            r'add(?:ed|ing)?\s+(.+)',
            r'(?:new feature|feature):\s*(.+)',
        ],
        ChangeCategory.FIXED: [
            r'(?:fixed|resolved|repaired|corrected)\s+(.+)',
            r'fix(?:ed|ing)?\s+(.+)',
            r'bug\s*fix:\s*(.+)',
        ],
        ChangeCategory.CHANGED: [
            r'(?:changed|updated|modified|refactored)\s+(.+)',
            r'update(?:d|ing)?\s+(.+)',
            r'refactor(?:ed|ing)?\s+(.+)',
        ],
        ChangeCategory.REMOVED: [
            r'(?:removed|deleted|dropped)\s+(.+)',
            r'remove(?:d|ing)?\s+(.+)',
        ],
        ChangeCategory.DEPRECATED: [
            r'(?:deprecated|deprecating)\s+(.+)',
            r'marked?\s+(.+)\s+as\s+deprecated',
        ],
        ChangeCategory.SECURITY: [
            r'(?:security|vulnerability|cve)\s+(.+)',
            r'(?:patched|secured)\s+(.+)',
        ],
    }

    # Breaking change indicators
    BREAKING_PATTERNS = [
        r'breaking\s*change',
        r'breaking:',
        r'\*\*breaking\*\*',
        r'incompatible',
        r'migration\s+required',
    ]

    def __init__(self):
        """Initialize the changelog generator."""
        pass

    def extract_changes_from_output(
        self,
        agent_output: str,
        default_category: ChangeCategory = ChangeCategory.CHANGED,
    ) -> list[ChangelogEntry]:
        """Extract changelog entries from agent output text.

        Args:
            agent_output: The raw output from an agent (Mason, etc.)
            default_category: Category to use if none detected

        Returns:
            List of ChangelogEntry objects
        """
        entries = []
        seen_descriptions = set()  # Avoid duplicates

        # Look for explicit changelog sections
        changelog_section = self._extract_changelog_section(agent_output)
        if changelog_section:
            section_entries = self._parse_changelog_section(changelog_section)
            for e in section_entries:
                if e.description.lower() not in seen_descriptions:
                    entries.append(e)
                    seen_descriptions.add(e.description.lower())

        # Look for "Files Modified" section for additional changes
        if "## Files Modified" in agent_output:
            files_section = agent_output.split("## Files Modified")[1].split("##")[0]
            for line in files_section.strip().split("\n"):
                if line.startswith("- "):
                    # Extract description after the filename
                    parts = line.split(" - ", 1)
                    if len(parts) > 1:
                        desc = parts[1].strip()
                        if desc.lower() not in seen_descriptions:
                            entries.append(ChangelogEntry(
                                category=self._detect_category(desc, default_category),
                                description=desc,
                                breaking=self._is_breaking(desc),
                            ))
                            seen_descriptions.add(desc.lower())

        # Scan for pattern matches in the full output
        for category, patterns in self.CHANGE_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, agent_output, re.IGNORECASE)
                for match in matches:
                    desc = match.group(1).strip()
                    # Clean up the description
                    desc = self._clean_description(desc)
                    if desc and len(desc) > 5 and desc.lower() not in seen_descriptions:
                        entries.append(ChangelogEntry(
                            category=category,
                            description=desc,
                            breaking=self._is_breaking(desc),
                        ))
                        seen_descriptions.add(desc.lower())

        return entries

    def _extract_changelog_section(self, text: str) -> Optional[str]:
        """Extract explicit changelog section if present."""
        patterns = [
            r'##\s*Changelog\s*\n(.*?)(?=\n##|\Z)',
            r'##\s*Changes\s*\n(.*?)(?=\n##|\Z)',
            r'##\s*What\'s Changed\s*\n(.*?)(?=\n##|\Z)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return None

    def _parse_changelog_section(self, section: str) -> list[ChangelogEntry]:
        """Parse an explicit changelog section."""
        entries = []
        current_category = ChangeCategory.CHANGED

        for line in section.split("\n"):
            line = line.strip()

            # Check for category headers
            if line.startswith("### "):
                category_name = line[4:].strip()
                try:
                    current_category = ChangeCategory(category_name)
                except ValueError:
                    # Try matching by name
                    for cat in ChangeCategory:
                        if cat.value.lower() == category_name.lower():
                            current_category = cat
                            break

            # Parse list items
            elif line.startswith("- "):
                desc = line[2:].strip()
                # Extract issue reference if present
                issue_ref = None
                issue_match = re.search(r'\(([#A-Z]+-?\d+)\)\s*$', desc)
                if issue_match:
                    issue_ref = issue_match.group(1)
                    desc = desc[:issue_match.start()].strip()

                # Clean markdown formatting
                desc = self._clean_description(desc)

                entries.append(ChangelogEntry(
                    category=current_category,
                    description=desc,
                    issue_ref=issue_ref,
                    breaking=self._is_breaking(desc),
                ))

        return entries

    def _detect_category(self, text: str, default: ChangeCategory) -> ChangeCategory:
        """Detect category from text content."""
        text_lower = text.lower()

        if any(word in text_lower for word in ['fix', 'bug', 'issue', 'error', 'crash']):
            return ChangeCategory.FIXED
        elif any(word in text_lower for word in ['add', 'new', 'create', 'implement']):
            return ChangeCategory.ADDED
        elif any(word in text_lower for word in ['remove', 'delete', 'drop']):
            return ChangeCategory.REMOVED
        elif any(word in text_lower for word in ['deprecate']):
            return ChangeCategory.DEPRECATED
        elif any(word in text_lower for word in ['security', 'vulnerab', 'cve']):
            return ChangeCategory.SECURITY

        return default

    def _is_breaking(self, text: str) -> bool:
        """Check if text indicates a breaking change."""
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in self.BREAKING_PATTERNS)

    def _clean_description(self, desc: str) -> str:
        """Clean up a description string."""
        # Remove markdown formatting
        desc = re.sub(r'\*\*([^*]+)\*\*', r'\1', desc)
        desc = re.sub(r'\*([^*]+)\*', r'\1', desc)
        desc = re.sub(r'`([^`]+)`', r'\1', desc)

        # Remove trailing punctuation from incomplete sentences
        desc = desc.rstrip('.,;:')

        # Capitalize first letter
        if desc:
            desc = desc[0].upper() + desc[1:]

        # Limit length
        if len(desc) > 100:
            desc = desc[:97] + "..."

        return desc.strip()

    def generate_release(
        self,
        update_context: UpdateContext,
        agent_outputs: dict[str, str],
    ) -> ChangelogRelease:
        """Generate a changelog release from update context and agent outputs.

        Args:
            update_context: The update context with version info
            agent_outputs: Dictionary of agent_name -> output content

        Returns:
            ChangelogRelease ready to be written
        """
        default_category = ChangeCategory.from_update_type(update_context.update_type)

        release = ChangelogRelease(
            version=update_context.target_version,
            date=datetime.now(),
        )

        # Add the main change from the update request
        release.add_entry(
            description=update_context.change_description,
            category=default_category,
            breaking=(update_context.update_type == UpdateType.MAJOR),
        )

        # Extract additional changes from agent outputs
        seen = {update_context.change_description.lower()}

        for agent_name, output in agent_outputs.items():
            entries = self.extract_changes_from_output(output, default_category)
            for entry in entries:
                if entry.description.lower() not in seen:
                    release.entries.append(entry)
                    seen.add(entry.description.lower())

        return release

    def format_changelog(
        self,
        releases: list[ChangelogRelease],
        project_name: str = "Project",
    ) -> str:
        """Format multiple releases as a full CHANGELOG.md.

        Args:
            releases: List of releases (newest first)
            project_name: Name of the project

        Returns:
            Complete CHANGELOG.md content
        """
        lines = [
            f"# Changelog",
            "",
            f"All notable changes to {project_name} will be documented in this file.",
            "",
            "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),",
            "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).",
            "",
        ]

        for release in releases:
            lines.append(release.to_markdown())

        return "\n".join(lines)

    def append_to_changelog(
        self,
        changelog_path: Path,
        release: ChangelogRelease,
    ) -> str:
        """Append a new release to an existing changelog file.

        Args:
            changelog_path: Path to existing CHANGELOG.md
            release: New release to add

        Returns:
            Updated changelog content
        """
        if changelog_path.exists():
            existing = changelog_path.read_text()

            # Find where to insert (after header, before first release)
            insert_pattern = r'(#\s*Changelog.*?\n\n(?:.*?adheres to.*?\n\n)?)'
            match = re.match(insert_pattern, existing, re.DOTALL)

            if match:
                header = match.group(1)
                rest = existing[match.end():]
                return header + release.to_markdown() + "\n" + rest
            else:
                # No header found, prepend release
                return release.to_markdown() + "\n\n" + existing
        else:
            # Create new changelog
            return self.format_changelog([release])


# Singleton instance
_changelog_generator: Optional[ChangelogGenerator] = None


def get_changelog_generator() -> ChangelogGenerator:
    """Get the global changelog generator instance."""
    global _changelog_generator
    if _changelog_generator is None:
        _changelog_generator = ChangelogGenerator()
    return _changelog_generator
