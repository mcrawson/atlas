"""Tests for changelog generator."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from atlas.versioning.models import (
    Version,
    UpdateType,
    ChangeCategory,
    UpdateContext,
)
from atlas.versioning.changelog import (
    ChangelogGenerator,
    get_changelog_generator,
)


class TestChangelogGenerator:
    """Test ChangelogGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create a changelog generator."""
        return ChangelogGenerator()

    def test_extract_added_changes(self, generator):
        """Test extracting 'added' changes from text."""
        output = """
        ## Changes
        - Added new login feature
        - Implemented user dashboard
        - Created settings page
        """
        entries = generator.extract_changes_from_output(output)

        added = [e for e in entries if e.category == ChangeCategory.ADDED]
        assert len(added) > 0

    def test_extract_fixed_changes(self, generator):
        """Test extracting 'fixed' changes from text."""
        output = """
        ## Bug Fixes
        - Fixed login crash on iOS
        - Resolved memory leak in dashboard
        - Bug fix: corrected date formatting
        """
        entries = generator.extract_changes_from_output(output)

        fixed = [e for e in entries if e.category == ChangeCategory.FIXED]
        assert len(fixed) > 0

    def test_extract_from_files_modified(self, generator):
        """Test extracting changes from Files Modified section."""
        output = """
        ## Files Modified
        - `src/login.py` - Fixed authentication bug
        - `src/dashboard.py` - Added new charts feature
        - `src/api.py` - Updated endpoint responses
        """
        entries = generator.extract_changes_from_output(output)

        assert len(entries) >= 3

    def test_detect_breaking_changes(self, generator):
        """Test detection of breaking changes."""
        output = """
        ## Changes
        - Breaking change: removed old API endpoint
        - **BREAKING** Changed authentication method
        - Migration required for database schema
        """
        entries = generator.extract_changes_from_output(output)

        breaking = [e for e in entries if e.breaking]
        assert len(breaking) > 0

    def test_explicit_changelog_section(self, generator):
        """Test parsing explicit changelog section."""
        output = """
        ## Implementation
        Some code here...

        ## Changelog
        ### Added
        - New feature A
        - New feature B

        ### Fixed
        - Bug fix 1

        ## Notes
        More text...
        """
        entries = generator.extract_changes_from_output(output)

        added = [e for e in entries if e.category == ChangeCategory.ADDED]
        fixed = [e for e in entries if e.category == ChangeCategory.FIXED]

        assert len(added) >= 2
        assert len(fixed) >= 1

    def test_extract_issue_references(self, generator):
        """Test extracting issue references from changelog."""
        output = """
        ## Changelog
        ### Fixed
        - Fixed crash on startup (#123)
        - Resolved memory leak (JIRA-456)
        """
        entries = generator.extract_changes_from_output(output)

        with_refs = [e for e in entries if e.issue_ref]
        assert len(with_refs) >= 1

    def test_generate_release(self, generator):
        """Test generating a release from update context."""
        ctx = UpdateContext(
            project_name="TestApp",
            current_version=Version(1, 0, 0),
            update_type=UpdateType.MINOR,
            change_description="Added new dashboard feature",
        )

        agent_outputs = {
            "mason": """
            ## Files Modified
            - `src/dashboard.py` - Added chart components
            - `src/api.py` - Added dashboard endpoint
            """
        }

        release = generator.generate_release(ctx, agent_outputs)

        assert release.version == Version(1, 1, 0)
        assert len(release.entries) > 0
        assert any("dashboard" in e.description.lower() for e in release.entries)

    def test_generate_release_sets_breaking_for_major(self, generator):
        """Test that major updates are marked as breaking."""
        ctx = UpdateContext(
            project_name="TestApp",
            current_version=Version(1, 0, 0),
            update_type=UpdateType.MAJOR,
            change_description="Redesigned API",
        )

        release = generator.generate_release(ctx, {})

        # First entry should be marked as breaking
        assert release.entries[0].breaking

    def test_format_changelog(self, generator):
        """Test formatting multiple releases as CHANGELOG.md."""
        from atlas.versioning.models import ChangelogRelease
        from datetime import datetime

        releases = [
            ChangelogRelease(
                version=Version(1, 1, 0),
                date=datetime(2024, 2, 1),
            ),
            ChangelogRelease(
                version=Version(1, 0, 0),
                date=datetime(2024, 1, 1),
            ),
        ]
        releases[0].add_entry("New feature", ChangeCategory.ADDED)
        releases[1].add_entry("Initial release", ChangeCategory.ADDED)

        changelog = generator.format_changelog(releases, "My Project")

        assert "# Changelog" in changelog
        assert "My Project" in changelog
        assert "[1.1.0]" in changelog
        assert "[1.0.0]" in changelog
        assert "Keep a Changelog" in changelog

    def test_append_to_changelog_new_file(self, generator):
        """Test appending to a new changelog file."""
        from atlas.versioning.models import ChangelogRelease
        from datetime import datetime

        with TemporaryDirectory() as tmpdir:
            changelog_path = Path(tmpdir) / "CHANGELOG.md"

            release = ChangelogRelease(
                version=Version(1, 0, 0),
                date=datetime(2024, 1, 1),
            )
            release.add_entry("Initial release", ChangeCategory.ADDED)

            result = generator.append_to_changelog(changelog_path, release)

            assert "# Changelog" in result
            assert "[1.0.0]" in result

    def test_append_to_changelog_existing_file(self, generator):
        """Test appending to an existing changelog file."""
        from atlas.versioning.models import ChangelogRelease
        from datetime import datetime

        with TemporaryDirectory() as tmpdir:
            changelog_path = Path(tmpdir) / "CHANGELOG.md"

            # Create existing changelog
            existing = """# Changelog

All notable changes will be documented here.

## [1.0.0] - 2024-01-01

### Added
- Initial release
"""
            changelog_path.write_text(existing)

            # Add new release
            release = ChangelogRelease(
                version=Version(1, 1, 0),
                date=datetime(2024, 2, 1),
            )
            release.add_entry("New feature", ChangeCategory.ADDED)

            result = generator.append_to_changelog(changelog_path, release)

            # New version should come before old version
            pos_110 = result.find("[1.1.0]")
            pos_100 = result.find("[1.0.0]")
            assert pos_110 < pos_100
            assert "# Changelog" in result

    def test_no_duplicate_entries(self, generator):
        """Test that duplicate entries are not created."""
        output = """
        ## Changes
        - Added new login feature
        - Added new login feature
        - added new login feature
        """
        entries = generator.extract_changes_from_output(output)

        # Should deduplicate (case-insensitive)
        descriptions = [e.description.lower() for e in entries]
        # Allow some variation but not exact duplicates
        assert len(set(descriptions)) == len(descriptions)

    def test_clean_description(self, generator):
        """Test description cleaning."""
        output = """
        ## Changes
        - Added **bold feature**
        - Fixed `code` issue
        - Updated *italic* text,
        """
        entries = generator.extract_changes_from_output(output)

        for entry in entries:
            # No markdown formatting
            assert "**" not in entry.description
            assert "`" not in entry.description
            assert "*" not in entry.description
            # No trailing punctuation
            assert not entry.description.endswith(",")

    def test_category_detection(self, generator):
        """Test automatic category detection."""
        output = """
        - Fixed a nasty bug
        - Added new endpoint
        - Removed deprecated code
        - Security patch for XSS
        """
        entries = generator.extract_changes_from_output(output)

        categories = {e.category for e in entries}
        # Should detect multiple categories
        assert len(categories) > 1


class TestGetChangelogGenerator:
    """Test the singleton factory function."""

    def test_returns_same_instance(self):
        """Test that factory returns the same instance."""
        gen1 = get_changelog_generator()
        gen2 = get_changelog_generator()
        assert gen1 is gen2

    def test_returns_changelog_generator(self):
        """Test that factory returns a ChangelogGenerator."""
        gen = get_changelog_generator()
        assert isinstance(gen, ChangelogGenerator)
