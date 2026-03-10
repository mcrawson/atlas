"""Versioning models for ATLAS product updates.

Handles semantic versioning, update types, and changelog entries.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class UpdateType(Enum):
    """Type of update being made to a product."""

    PATCH = "patch"      # Bug fixes, typos, minor corrections (1.0.0 → 1.0.1)
    MINOR = "minor"      # New features, backwards compatible (1.0.0 → 1.1.0)
    MAJOR = "major"      # Breaking changes, new edition (1.0.0 → 2.0.0)
    HOTFIX = "hotfix"    # Urgent security/critical fixes (treated as patch)

    @property
    def description(self) -> str:
        """Human-readable description of update type."""
        descriptions = {
            UpdateType.PATCH: "Bug fixes and minor corrections",
            UpdateType.MINOR: "New features (backwards compatible)",
            UpdateType.MAJOR: "Breaking changes or new edition",
            UpdateType.HOTFIX: "Urgent security or critical fix",
        }
        return descriptions[self]


class ChangeCategory(Enum):
    """Category of change for changelog organization."""

    ADDED = "Added"           # New features
    CHANGED = "Changed"       # Changes in existing functionality
    DEPRECATED = "Deprecated" # Soon-to-be removed features
    REMOVED = "Removed"       # Removed features
    FIXED = "Fixed"           # Bug fixes
    SECURITY = "Security"     # Security fixes

    @classmethod
    def from_update_type(cls, update_type: UpdateType) -> "ChangeCategory":
        """Get default category based on update type."""
        mapping = {
            UpdateType.PATCH: cls.FIXED,
            UpdateType.MINOR: cls.ADDED,
            UpdateType.MAJOR: cls.CHANGED,
            UpdateType.HOTFIX: cls.SECURITY,
        }
        return mapping.get(update_type, cls.CHANGED)


@dataclass
class Version:
    """Semantic version representation.

    Follows semver: MAJOR.MINOR.PATCH
    """

    major: int = 1
    minor: int = 0
    patch: int = 0
    prerelease: Optional[str] = None  # e.g., "alpha", "beta.1", "rc.2"
    build: Optional[str] = None       # e.g., "build.123"

    def __str__(self) -> str:
        """Format as version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __lt__(self, other: "Version") -> bool:
        """Compare versions for sorting."""
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        """Check version equality."""
        if not isinstance(other, Version):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    @classmethod
    def parse(cls, version_str: str) -> "Version":
        """Parse version string into Version object.

        Args:
            version_str: Version string like "1.2.3", "v1.2.3", "1.2.3-beta+build.1"

        Returns:
            Version object

        Raises:
            ValueError: If version string is invalid
        """
        # Remove leading 'v' if present
        version_str = version_str.lstrip('v').strip()

        # Handle empty or invalid input
        if not version_str:
            return cls()

        # Parse semver with optional prerelease and build
        pattern = r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$'
        match = re.match(pattern, version_str)

        if not match:
            raise ValueError(f"Invalid version string: {version_str}")

        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        patch = int(match.group(3)) if match.group(3) else 0
        prerelease = match.group(4)
        build = match.group(5)

        return cls(major=major, minor=minor, patch=patch, prerelease=prerelease, build=build)

    def bump(self, update_type: UpdateType) -> "Version":
        """Create a new version bumped according to update type.

        Args:
            update_type: Type of update (MAJOR, MINOR, PATCH, HOTFIX)

        Returns:
            New Version object with bumped version number
        """
        if update_type == UpdateType.MAJOR:
            return Version(major=self.major + 1, minor=0, patch=0)
        elif update_type == UpdateType.MINOR:
            return Version(major=self.major, minor=self.minor + 1, patch=0)
        elif update_type in (UpdateType.PATCH, UpdateType.HOTFIX):
            return Version(major=self.major, minor=self.minor, patch=self.patch + 1)
        else:
            return Version(major=self.major, minor=self.minor, patch=self.patch + 1)


@dataclass
class ChangelogEntry:
    """A single entry in a changelog."""

    category: ChangeCategory
    description: str
    issue_ref: Optional[str] = None    # e.g., "#123", "JIRA-456"
    breaking: bool = False              # Is this a breaking change?

    def to_markdown(self) -> str:
        """Format as markdown list item."""
        line = f"- {self.description}"
        if self.issue_ref:
            line += f" ({self.issue_ref})"
        if self.breaking:
            line += " **BREAKING**"
        return line


@dataclass
class ChangelogRelease:
    """A release in the changelog (collection of entries)."""

    version: Version
    date: datetime = field(default_factory=datetime.now)
    entries: list[ChangelogEntry] = field(default_factory=list)
    summary: Optional[str] = None  # Optional release summary

    def add_entry(
        self,
        description: str,
        category: ChangeCategory = ChangeCategory.CHANGED,
        issue_ref: Optional[str] = None,
        breaking: bool = False,
    ):
        """Add an entry to this release."""
        self.entries.append(ChangelogEntry(
            category=category,
            description=description,
            issue_ref=issue_ref,
            breaking=breaking,
        ))

    def to_markdown(self) -> str:
        """Format release as markdown section."""
        lines = []

        # Header
        date_str = self.date.strftime("%Y-%m-%d")
        lines.append(f"## [{self.version}] - {date_str}")
        lines.append("")

        # Summary if present
        if self.summary:
            lines.append(self.summary)
            lines.append("")

        # Group entries by category
        by_category: dict[ChangeCategory, list[ChangelogEntry]] = {}
        for entry in self.entries:
            if entry.category not in by_category:
                by_category[entry.category] = []
            by_category[entry.category].append(entry)

        # Output in standard order
        category_order = [
            ChangeCategory.ADDED,
            ChangeCategory.CHANGED,
            ChangeCategory.DEPRECATED,
            ChangeCategory.REMOVED,
            ChangeCategory.FIXED,
            ChangeCategory.SECURITY,
        ]

        for category in category_order:
            if category in by_category:
                lines.append(f"### {category.value}")
                for entry in by_category[category]:
                    lines.append(entry.to_markdown())
                lines.append("")

        return "\n".join(lines)


@dataclass
class UpdateContext:
    """Context for an update operation.

    Passed to agents so they know they're updating, not creating from scratch.
    """

    # What we're updating
    project_name: str
    current_version: Version

    # Type of update
    update_type: UpdateType

    # What to change
    change_description: str

    # Existing code/content (if available)
    existing_code: Optional[str] = None
    existing_files: Optional[dict[str, str]] = None  # filename -> content

    # Previous issues/feedback
    issues_to_fix: list[str] = field(default_factory=list)
    user_feedback: Optional[str] = None

    # Computed
    target_version: Optional[Version] = None

    def __post_init__(self):
        """Calculate target version if not provided."""
        if self.target_version is None:
            self.target_version = self.current_version.bump(self.update_type)

    def to_prompt_context(self) -> str:
        """Format as context string for agent prompts."""
        lines = [
            "## UPDATE CONTEXT",
            f"**Project:** {self.project_name}",
            f"**Current Version:** {self.current_version}",
            f"**Target Version:** {self.target_version}",
            f"**Update Type:** {self.update_type.value} - {self.update_type.description}",
            "",
            f"**Change Request:** {self.change_description}",
        ]

        if self.issues_to_fix:
            lines.append("")
            lines.append("**Issues to Address:**")
            for issue in self.issues_to_fix:
                lines.append(f"- {issue}")

        if self.user_feedback:
            lines.append("")
            lines.append(f"**User Feedback:** {self.user_feedback}")

        if self.existing_files:
            lines.append("")
            lines.append(f"**Existing Files:** {', '.join(self.existing_files.keys())}")

        lines.append("")
        lines.append("---")
        lines.append("You are UPDATING an existing product, not building from scratch.")
        lines.append("Preserve existing functionality unless explicitly changing it.")
        lines.append("Document all changes for the changelog.")

        return "\n".join(lines)
