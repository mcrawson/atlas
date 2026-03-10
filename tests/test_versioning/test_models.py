"""Tests for versioning models."""

import pytest
from datetime import datetime

from atlas.versioning.models import (
    Version,
    UpdateType,
    ChangeCategory,
    ChangelogEntry,
    ChangelogRelease,
    UpdateContext,
)


class TestVersion:
    """Test Version class."""

    def test_create_default_version(self):
        """Test creating a default version."""
        v = Version()
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert str(v) == "1.0.0"

    def test_create_version_with_values(self):
        """Test creating a version with specific values."""
        v = Version(major=2, minor=5, patch=3)
        assert str(v) == "2.5.3"

    def test_version_with_prerelease(self):
        """Test version with prerelease tag."""
        v = Version(major=1, minor=0, patch=0, prerelease="beta.1")
        assert str(v) == "1.0.0-beta.1"

    def test_version_with_build(self):
        """Test version with build metadata."""
        v = Version(major=1, minor=0, patch=0, build="build.123")
        assert str(v) == "1.0.0+build.123"

    def test_version_with_prerelease_and_build(self):
        """Test version with both prerelease and build."""
        v = Version(major=1, minor=0, patch=0, prerelease="rc.1", build="abc123")
        assert str(v) == "1.0.0-rc.1+abc123"

    def test_parse_simple_version(self):
        """Test parsing a simple version string."""
        v = Version.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_version_with_v_prefix(self):
        """Test parsing version with 'v' prefix."""
        v = Version.parse("v2.0.1")
        assert v.major == 2
        assert v.minor == 0
        assert v.patch == 1

    def test_parse_version_without_patch(self):
        """Test parsing version without patch number."""
        v = Version.parse("1.2")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 0

    def test_parse_version_major_only(self):
        """Test parsing major version only."""
        v = Version.parse("3")
        assert v.major == 3
        assert v.minor == 0
        assert v.patch == 0

    def test_parse_version_with_prerelease(self):
        """Test parsing version with prerelease."""
        v = Version.parse("1.0.0-alpha.1")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert v.prerelease == "alpha.1"

    def test_parse_version_with_build(self):
        """Test parsing version with build metadata."""
        v = Version.parse("1.0.0+build.456")
        assert v.build == "build.456"

    def test_parse_invalid_version(self):
        """Test parsing invalid version raises error."""
        with pytest.raises(ValueError):
            Version.parse("not-a-version")

    def test_parse_empty_version(self):
        """Test parsing empty version returns default."""
        v = Version.parse("")
        assert v == Version()

    def test_bump_patch(self):
        """Test bumping patch version."""
        v = Version(major=1, minor=2, patch=3)
        new_v = v.bump(UpdateType.PATCH)
        assert str(new_v) == "1.2.4"

    def test_bump_minor(self):
        """Test bumping minor version resets patch."""
        v = Version(major=1, minor=2, patch=3)
        new_v = v.bump(UpdateType.MINOR)
        assert str(new_v) == "1.3.0"

    def test_bump_major(self):
        """Test bumping major version resets minor and patch."""
        v = Version(major=1, minor=2, patch=3)
        new_v = v.bump(UpdateType.MAJOR)
        assert str(new_v) == "2.0.0"

    def test_bump_hotfix(self):
        """Test hotfix bumps patch."""
        v = Version(major=1, minor=2, patch=3)
        new_v = v.bump(UpdateType.HOTFIX)
        assert str(new_v) == "1.2.4"

    def test_version_comparison(self):
        """Test version comparison."""
        v1 = Version(major=1, minor=0, patch=0)
        v2 = Version(major=1, minor=0, patch=1)
        v3 = Version(major=1, minor=1, patch=0)
        v4 = Version(major=2, minor=0, patch=0)

        assert v1 < v2
        assert v2 < v3
        assert v3 < v4
        assert v1 == Version(major=1, minor=0, patch=0)

    def test_version_equality(self):
        """Test version equality."""
        v1 = Version(major=1, minor=2, patch=3)
        v2 = Version(major=1, minor=2, patch=3)
        v3 = Version(major=1, minor=2, patch=4)

        assert v1 == v2
        assert v1 != v3
        assert v1 != "not a version"


class TestUpdateType:
    """Test UpdateType enum."""

    def test_update_type_values(self):
        """Test update type enum values."""
        assert UpdateType.PATCH.value == "patch"
        assert UpdateType.MINOR.value == "minor"
        assert UpdateType.MAJOR.value == "major"
        assert UpdateType.HOTFIX.value == "hotfix"

    def test_update_type_descriptions(self):
        """Test update type descriptions."""
        assert "Bug fixes" in UpdateType.PATCH.description
        assert "New features" in UpdateType.MINOR.description
        assert "Breaking" in UpdateType.MAJOR.description
        assert "Urgent" in UpdateType.HOTFIX.description


class TestChangeCategory:
    """Test ChangeCategory enum."""

    def test_category_values(self):
        """Test category enum values."""
        assert ChangeCategory.ADDED.value == "Added"
        assert ChangeCategory.FIXED.value == "Fixed"
        assert ChangeCategory.SECURITY.value == "Security"

    def test_from_update_type(self):
        """Test getting default category from update type."""
        assert ChangeCategory.from_update_type(UpdateType.PATCH) == ChangeCategory.FIXED
        assert ChangeCategory.from_update_type(UpdateType.MINOR) == ChangeCategory.ADDED
        assert ChangeCategory.from_update_type(UpdateType.MAJOR) == ChangeCategory.CHANGED
        assert ChangeCategory.from_update_type(UpdateType.HOTFIX) == ChangeCategory.SECURITY


class TestChangelogEntry:
    """Test ChangelogEntry dataclass."""

    def test_create_entry(self):
        """Test creating a changelog entry."""
        entry = ChangelogEntry(
            category=ChangeCategory.FIXED,
            description="Fixed login bug",
        )
        assert entry.category == ChangeCategory.FIXED
        assert entry.description == "Fixed login bug"
        assert entry.issue_ref is None
        assert entry.breaking is False

    def test_entry_with_issue_ref(self):
        """Test entry with issue reference."""
        entry = ChangelogEntry(
            category=ChangeCategory.FIXED,
            description="Fixed crash",
            issue_ref="#123",
        )
        assert entry.issue_ref == "#123"

    def test_entry_to_markdown(self):
        """Test formatting entry as markdown."""
        entry = ChangelogEntry(
            category=ChangeCategory.ADDED,
            description="New feature",
        )
        assert entry.to_markdown() == "- New feature"

    def test_entry_to_markdown_with_issue(self):
        """Test markdown with issue reference."""
        entry = ChangelogEntry(
            category=ChangeCategory.FIXED,
            description="Bug fix",
            issue_ref="#456",
        )
        assert "(#456)" in entry.to_markdown()

    def test_entry_to_markdown_breaking(self):
        """Test markdown with breaking indicator."""
        entry = ChangelogEntry(
            category=ChangeCategory.CHANGED,
            description="API change",
            breaking=True,
        )
        assert "**BREAKING**" in entry.to_markdown()


class TestChangelogRelease:
    """Test ChangelogRelease dataclass."""

    def test_create_release(self):
        """Test creating a release."""
        release = ChangelogRelease(version=Version(1, 0, 0))
        assert release.version == Version(1, 0, 0)
        assert len(release.entries) == 0

    def test_add_entry(self):
        """Test adding entries to a release."""
        release = ChangelogRelease(version=Version(1, 0, 0))
        release.add_entry("New feature", ChangeCategory.ADDED)
        release.add_entry("Bug fix", ChangeCategory.FIXED)

        assert len(release.entries) == 2
        assert release.entries[0].description == "New feature"

    def test_release_to_markdown(self):
        """Test formatting release as markdown."""
        release = ChangelogRelease(
            version=Version(1, 1, 0),
            date=datetime(2024, 1, 15),
        )
        release.add_entry("Added feature X", ChangeCategory.ADDED)
        release.add_entry("Fixed bug Y", ChangeCategory.FIXED)

        md = release.to_markdown()

        assert "[1.1.0]" in md
        assert "2024-01-15" in md
        assert "### Added" in md
        assert "### Fixed" in md
        assert "Added feature X" in md
        assert "Fixed bug Y" in md

    def test_release_with_summary(self):
        """Test release with summary."""
        release = ChangelogRelease(
            version=Version(2, 0, 0),
            summary="Major release with breaking changes",
        )
        release.add_entry("New API", ChangeCategory.CHANGED, breaking=True)

        md = release.to_markdown()
        assert "Major release with breaking changes" in md


class TestUpdateContext:
    """Test UpdateContext dataclass."""

    def test_create_context(self):
        """Test creating update context."""
        ctx = UpdateContext(
            project_name="MyApp",
            current_version=Version(1, 0, 0),
            update_type=UpdateType.PATCH,
            change_description="Fix login bug",
        )

        assert ctx.project_name == "MyApp"
        assert ctx.current_version == Version(1, 0, 0)
        assert ctx.target_version == Version(1, 0, 1)  # Auto-calculated

    def test_context_with_existing_code(self):
        """Test context with existing code."""
        ctx = UpdateContext(
            project_name="MyApp",
            current_version=Version(1, 0, 0),
            update_type=UpdateType.MINOR,
            change_description="Add new feature",
            existing_code="def old_function(): pass",
        )

        assert ctx.existing_code == "def old_function(): pass"
        assert ctx.target_version == Version(1, 1, 0)

    def test_context_with_issues(self):
        """Test context with issues to fix."""
        ctx = UpdateContext(
            project_name="MyApp",
            current_version=Version(1, 0, 0),
            update_type=UpdateType.PATCH,
            change_description="Fix issues",
            issues_to_fix=["Bug 1", "Bug 2"],
        )

        assert len(ctx.issues_to_fix) == 2

    def test_context_to_prompt(self):
        """Test converting context to prompt string."""
        ctx = UpdateContext(
            project_name="MyApp",
            current_version=Version(1, 0, 0),
            update_type=UpdateType.MINOR,
            change_description="Add feature X",
            user_feedback="Please make it faster",
        )

        prompt = ctx.to_prompt_context()

        assert "MyApp" in prompt
        assert "1.0.0" in prompt
        assert "1.1.0" in prompt  # Target version
        assert "Add feature X" in prompt
        assert "Please make it faster" in prompt
        assert "UPDATE CONTEXT" in prompt
        assert "UPDATING an existing product" in prompt

    def test_context_with_explicit_target(self):
        """Test context with explicit target version."""
        ctx = UpdateContext(
            project_name="MyApp",
            current_version=Version(1, 0, 0),
            update_type=UpdateType.MINOR,
            change_description="Update",
            target_version=Version(2, 0, 0),  # Explicit override
        )

        assert ctx.target_version == Version(2, 0, 0)
