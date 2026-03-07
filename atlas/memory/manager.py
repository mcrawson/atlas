"""Markdown-based memory management for ATLAS."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dateutil import parser as date_parser


class MemoryManager:
    """Manages persistent memory storage in Markdown format."""

    def __init__(self, memory_dir: Path):
        """Initialize memory manager.

        Args:
            memory_dir: Base directory for memory storage
        """
        self.memory_dir = memory_dir
        self.conversations_dir = memory_dir / "conversations"
        self.decisions_dir = memory_dir / "decisions"
        self.projects_dir = memory_dir / "projects"
        self.briefings_dir = memory_dir / "briefings"

        # Ensure directories exist
        for directory in [
            self.conversations_dir,
            self.decisions_dir,
            self.projects_dir,
            self.briefings_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def _get_conversation_path(self, date: Optional[datetime] = None) -> Path:
        """Get path for a conversation file by date."""
        date = date or datetime.now()
        return self.conversations_dir / f"{date.strftime('%Y-%m-%d')}.md"

    def save_conversation(
        self,
        user_message: str,
        assistant_response: str,
        model: str = "unknown",
        task_type: Optional[str] = None,
    ) -> None:
        """Save a conversation exchange to memory.

        Args:
            user_message: The user's input
            assistant_response: ATLAS's response
            model: The model used for the response
            task_type: Optional task classification
        """
        path = self._get_conversation_path()
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Create header if file is new
        if not path.exists():
            header = f"# Conversations - {datetime.now().strftime('%Y-%m-%d')}\n\n"
            path.write_text(header)

        # Append conversation
        entry = f"""
## {timestamp} [{model}]
{f'*Task: {task_type}*' if task_type else ''}

**User:** {user_message}

**ATLAS:** {assistant_response}

---
"""
        with open(path, "a") as f:
            f.write(entry)

    def get_recent_conversations(self, days: int = 1) -> list[dict]:
        """Get recent conversation entries.

        Args:
            days: Number of days to look back

        Returns:
            List of conversation dictionaries
        """
        conversations = []
        cutoff = datetime.now() - timedelta(days=days)

        for conv_file in sorted(self.conversations_dir.glob("*.md"), reverse=True):
            try:
                date_str = conv_file.stem
                file_date = date_parser.parse(date_str)
                if file_date.date() < cutoff.date():
                    break

                content = conv_file.read_text()
                conversations.append(
                    {"date": date_str, "content": content, "path": str(conv_file)}
                )
            except (ValueError, Exception):
                continue

        return conversations

    def save_decision(
        self,
        title: str,
        context: str,
        decision: str,
        reasoning: str,
        alternatives: Optional[list[str]] = None,
    ) -> Path:
        """Save an important decision to memory.

        Args:
            title: Brief title for the decision
            context: What prompted the decision
            decision: The decision made
            reasoning: Why this decision was made
            alternatives: Other options considered

        Returns:
            Path to the saved decision file
        """
        timestamp = datetime.now()
        filename = f"{timestamp.strftime('%Y-%m-%d_%H%M%S')}_{self._slugify(title)}.md"
        path = self.decisions_dir / filename

        content = f"""# {title}

**Date:** {timestamp.strftime('%Y-%m-%d %H:%M')}

## Context

{context}

## Decision

{decision}

## Reasoning

{reasoning}
"""

        if alternatives:
            content += "\n## Alternatives Considered\n\n"
            for alt in alternatives:
                content += f"- {alt}\n"

        path.write_text(content)
        return path

    def get_recent_decisions(self, limit: int = 5) -> list[dict]:
        """Get recent decisions.

        Args:
            limit: Maximum number of decisions to return

        Returns:
            List of decision summaries
        """
        decisions = []

        for dec_file in sorted(self.decisions_dir.glob("*.md"), reverse=True)[:limit]:
            content = dec_file.read_text()
            # Extract title from first line
            lines = content.strip().split("\n")
            title = lines[0].lstrip("# ") if lines else dec_file.stem

            decisions.append(
                {"title": title, "date": dec_file.stem[:10], "path": str(dec_file)}
            )

        return decisions

    def save_project_note(self, project_name: str, note: str, category: str = "general") -> None:
        """Save a note about a project.

        Args:
            project_name: Name of the project
            note: The note content
            category: Category of note (general, todo, issue, etc.)
        """
        project_dir = self.projects_dir / self._slugify(project_name)
        project_dir.mkdir(parents=True, exist_ok=True)

        notes_file = project_dir / f"{category}.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        if not notes_file.exists():
            notes_file.write_text(f"# {project_name} - {category.title()}\n\n")

        with open(notes_file, "a") as f:
            f.write(f"## {timestamp}\n\n{note}\n\n---\n\n")

    def save_briefing(self, briefing_data: dict) -> Path:
        """Save a session briefing.

        Args:
            briefing_data: Dictionary containing briefing information

        Returns:
            Path to saved briefing
        """
        timestamp = datetime.now()
        filename = f"{timestamp.strftime('%Y-%m-%d_%H%M%S')}_briefing.md"
        path = self.briefings_dir / filename

        content = f"""# Session Briefing - {timestamp.strftime('%Y-%m-%d %H:%M')}

## Summary

"""
        for key, value in briefing_data.items():
            if isinstance(value, dict):
                content += f"\n### {key.replace('_', ' ').title()}\n\n"
                for k, v in value.items():
                    content += f"- {k}: {v}\n"
            elif isinstance(value, list):
                content += f"\n### {key.replace('_', ' ').title()}\n\n"
                for item in value:
                    content += f"- {item}\n"
            else:
                content += f"- **{key.replace('_', ' ').title()}:** {value}\n"

        path.write_text(content)
        return path

    def get_recent_exchanges(self, limit: int = 10) -> list[dict]:
        """Get the most recent conversation exchanges parsed from markdown.

        Args:
            limit: Maximum number of exchanges to return

        Returns:
            List of dicts with 'user' and 'assistant' keys
        """
        import re
        exchanges = []

        # Check today's and yesterday's conversations
        for days_ago in range(2):
            date = datetime.now() - timedelta(days=days_ago)
            path = self._get_conversation_path(date)
            if not path.exists():
                continue

            content = path.read_text()

            # Parse exchanges using regex
            # Format: **User:** message ... **ATLAS:** response
            pattern = r'\*\*User:\*\*\s*(.*?)\n\n\*\*ATLAS:\*\*\s*(.*?)(?=\n---|\Z)'
            matches = re.findall(pattern, content, re.DOTALL)

            for user_msg, assistant_msg in matches:
                exchanges.append({
                    'user': user_msg.strip()[:500],  # Limit length
                    'assistant': assistant_msg.strip()[:500],
                })

            if len(exchanges) >= limit:
                break

        # Return most recent first, limited
        return exchanges[-limit:]

    def get_context_for_prompt(self, max_tokens: int = 2000) -> str:
        """Get relevant memory context for including in prompts.

        Args:
            max_tokens: Approximate maximum tokens of context

        Returns:
            Formatted context string
        """
        context_parts = []

        # Recent decisions
        decisions = self.get_recent_decisions(limit=3)
        if decisions:
            context_parts.append("Recent Decisions:")
            for dec in decisions:
                context_parts.append(f"  - [{dec['date']}] {dec['title']}")

        # Today's conversation summary
        today_path = self._get_conversation_path()
        if today_path.exists():
            content = today_path.read_text()
            # Count exchanges (rough estimate)
            exchanges = content.count("**User:**")
            if exchanges > 0:
                context_parts.append(f"\nToday's Conversations: {exchanges} exchanges")

        return "\n".join(context_parts) if context_parts else ""

    def cleanup_old_conversations(self, retention_days: int = 30) -> int:
        """Remove conversations older than retention period.

        Args:
            retention_days: Number of days to retain

        Returns:
            Number of files deleted
        """
        cutoff = datetime.now() - timedelta(days=retention_days)
        deleted = 0

        for conv_file in self.conversations_dir.glob("*.md"):
            try:
                date_str = conv_file.stem
                file_date = date_parser.parse(date_str)
                if file_date.date() < cutoff.date():
                    conv_file.unlink()
                    deleted += 1
            except (ValueError, Exception):
                continue

        return deleted

    def _slugify(self, text: str) -> str:
        """Convert text to a filesystem-safe slug."""
        return "".join(c if c.isalnum() else "_" for c in text.lower()).strip("_")[:50]
