"""User preferences for ATLAS - persistent memory of user details."""

import json
import logging
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

logger = logging.getLogger("atlas.core.preferences")


class UserPreferences:
    """Manages persistent user preferences that ATLAS should always remember."""

    def __init__(self, data_dir: Path):
        """Initialize user preferences.

        Args:
            data_dir: Directory for storing preferences
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.prefs_file = self.data_dir / "user_preferences.json"
        self._prefs = self._load()

    def _load(self) -> dict:
        """Load preferences from file."""
        if self.prefs_file.exists():
            try:
                return json.loads(self.prefs_file.read_text())
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load user preferences: {e}")
        return {
            "title": "sir",  # Default title
            "name": None,
            "preferences": {},
            "facts": [],  # Things to remember about the user
            "updated_at": None,
        }

    def _save(self):
        """Save preferences to file."""
        self._prefs["updated_at"] = datetime.now().isoformat()
        self.prefs_file.write_text(json.dumps(self._prefs, indent=2))

    @property
    def title(self) -> str:
        """Get user's preferred title (sir, ma'am, etc.)."""
        return self._prefs.get("title", "sir")

    @title.setter
    def title(self, value: str):
        """Set user's preferred title."""
        self._prefs["title"] = value
        self._save()

    @property
    def name(self) -> Optional[str]:
        """Get user's name if known."""
        return self._prefs.get("name")

    @name.setter
    def name(self, value: str):
        """Set user's name."""
        self._prefs["name"] = value
        self._save()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        return self._prefs.get("preferences", {}).get(key, default)

    def set(self, key: str, value: Any):
        """Set a preference value."""
        if "preferences" not in self._prefs:
            self._prefs["preferences"] = {}
        self._prefs["preferences"][key] = value
        self._save()

    def add_fact(self, fact: str):
        """Add a fact to remember about the user."""
        if "facts" not in self._prefs:
            self._prefs["facts"] = []
        # Avoid duplicates
        if fact not in self._prefs["facts"]:
            self._prefs["facts"].append(fact)
            self._save()

    def remove_fact(self, fact: str):
        """Remove a remembered fact."""
        if "facts" in self._prefs and fact in self._prefs["facts"]:
            self._prefs["facts"].remove(fact)
            self._save()

    def get_facts(self) -> list:
        """Get all remembered facts about the user."""
        return self._prefs.get("facts", [])

    def get_context_prompt(self) -> str:
        """Generate a context prompt with user preferences for the AI.

        Returns:
            String to include in system prompt
        """
        lines = []

        # Title
        title = self.title
        lines.append(f"Always address the user as '{title}'.")

        # Name
        name = self.name
        if name:
            lines.append(f"The user's name is {name}.")

        # Facts
        facts = self.get_facts()
        if facts:
            lines.append("Remember these facts about the user:")
            for fact in facts:
                lines.append(f"  - {fact}")

        return "\n".join(lines)

    def get_all(self) -> dict:
        """Get all preferences."""
        return self._prefs.copy()
