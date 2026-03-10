"""ATLAS Versioning Module.

Handles semantic versioning, update types, and changelog generation
for product updates.
"""

from .models import (
    Version,
    UpdateType,
    ChangeCategory,
    ChangelogEntry,
    ChangelogRelease,
    UpdateContext,
)
from .changelog import (
    ChangelogGenerator,
    get_changelog_generator,
)

__all__ = [
    # Models
    "Version",
    "UpdateType",
    "ChangeCategory",
    "ChangelogEntry",
    "ChangelogRelease",
    "UpdateContext",
    # Changelog
    "ChangelogGenerator",
    "get_changelog_generator",
]
