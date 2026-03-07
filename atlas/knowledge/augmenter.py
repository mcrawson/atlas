"""Knowledge Augmenter - Injects relevant knowledge into agent context.

Analyzes tasks to find relevant knowledge base entries and formats them
for agent consumption. Makes agents smarter by giving them access to
deployment guides, best practices, and platform-specific knowledge.
"""

import re
from typing import Optional
from .manager import KnowledgeManager
from .models import KnowledgeEntry, SearchResult


# Platform detection patterns
PLATFORM_PATTERNS = {
    "ios": [r"\bios\b", r"\biphone\b", r"\bipad\b", r"\bswift\b", r"\bxcode\b", r"\bapp\s*store\b"],
    "android": [r"\bandroid\b", r"\bkotlin\b", r"\bjava\b", r"\bplay\s*store\b", r"\bapk\b"],
    "flutter": [r"\bflutter\b", r"\bdart\b"],
    "react": [r"\breact\b", r"\breactjs\b", r"\bnext\.?js\b", r"\bvite\b", r"\bjsx\b"],
    "web": [r"\bwebsite\b", r"\bweb\s*app\b", r"\bhtml\b", r"\bcss\b", r"\bfrontend\b"],
    "python": [r"\bpython\b", r"\bpip\b", r"\bdjango\b", r"\bflask\b", r"\bfastapi\b", r"\bpypi\b"],
    "node": [r"\bnode\.?js\b", r"\bnpm\b", r"\bexpress\b", r"\bnestjs\b"],
    "docker": [r"\bdocker\b", r"\bcontainer\b", r"\bkubernetes\b", r"\bk8s\b"],
    "slack": [r"\bslack\b", r"\bslack\s*app\b", r"\bslack\s*bot\b"],
    "discord": [r"\bdiscord\b", r"\bdiscord\s*bot\b"],
    "chrome": [r"\bchrome\s*extension\b", r"\bbrowser\s*extension\b"],
    "shopify": [r"\bshopify\b", r"\bshopify\s*app\b"],
    "wordpress": [r"\bwordpress\b", r"\bwp\b", r"\bplugin\b"],
    "alexa": [r"\balexa\b", r"\balexa\s*skill\b", r"\bvoice\s*assistant\b"],
}


class KnowledgeAugmenter:
    """Augments agent prompts with relevant knowledge base entries."""

    def __init__(self, knowledge_manager: Optional[KnowledgeManager] = None):
        """Initialize the augmenter.

        Args:
            knowledge_manager: Optional KnowledgeManager instance.
                               Creates one if not provided.
        """
        self._manager = knowledge_manager

    @property
    def manager(self) -> KnowledgeManager:
        """Get or create the knowledge manager."""
        if self._manager is None:
            self._manager = KnowledgeManager()
        return self._manager

    def detect_platforms(self, text: str) -> list[str]:
        """Detect platforms/technologies mentioned in text.

        Args:
            text: The text to analyze (task description, context, etc.)

        Returns:
            List of detected platform identifiers
        """
        text_lower = text.lower()
        detected = []

        for platform, patterns in PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    detected.append(platform)
                    break  # One match per platform is enough

        return detected

    def get_relevant_knowledge(
        self,
        task: str,
        context: Optional[dict] = None,
        max_entries: int = 3,
    ) -> list[KnowledgeEntry]:
        """Find relevant knowledge entries for a task.

        Args:
            task: The task description
            context: Optional context dict with additional info
            max_entries: Maximum entries to return

        Returns:
            List of relevant KnowledgeEntry objects
        """
        entries = []
        seen_ids = set()

        # Build search text from task and context
        search_text = task
        if context:
            if context.get("description"):
                search_text += " " + context["description"]
            if context.get("technical"):
                search_text += " " + context["technical"]
            if context.get("features"):
                if isinstance(context["features"], list):
                    search_text += " " + " ".join(context["features"])
                else:
                    search_text += " " + context["features"]

        # 1. Detect platforms and get deployment guides
        platforms = self.detect_platforms(search_text)
        for platform in platforms[:2]:  # Limit to top 2 platforms
            guide = self.manager.get_deployment_guide(platform)
            if guide and guide.id not in seen_ids:
                entries.append(guide)
                seen_ids.add(guide.id)

        # 2. Search for additional relevant entries
        if len(entries) < max_entries:
            # Extract key terms for search
            search_results = self.manager.search(task[:100], limit=5)
            for result in search_results:
                if result.entry.id not in seen_ids:
                    entries.append(result.entry)
                    seen_ids.add(result.entry.id)
                    if len(entries) >= max_entries:
                        break

        return entries[:max_entries]

    def format_knowledge_context(
        self,
        entries: list[KnowledgeEntry],
        include_commands: bool = True,
        include_prerequisites: bool = True,
        max_content_length: int = 1500,
    ) -> str:
        """Format knowledge entries as context for an agent prompt.

        Args:
            entries: List of knowledge entries to format
            include_commands: Whether to include command lists
            include_prerequisites: Whether to include prerequisites
            max_content_length: Max chars per entry's content

        Returns:
            Formatted knowledge context string
        """
        if not entries:
            return ""

        sections = ["## Relevant Knowledge Base Entries\n"]
        sections.append("*The following guides from the ATLAS knowledge base may be helpful:*\n")

        for entry in entries:
            sections.append(f"### {entry.title}")
            sections.append(f"*Platform: {entry.platform} | Category: {entry.category.value}*\n")

            # Truncated content
            content = entry.content
            if len(content) > max_content_length:
                content = content[:max_content_length] + "...\n[Content truncated - see full guide in knowledge base]"
            sections.append(content)

            if include_prerequisites and entry.prerequisites:
                sections.append("\n**Prerequisites:**")
                for prereq in entry.prerequisites[:5]:
                    sections.append(f"- {prereq}")

            if include_commands and entry.commands:
                sections.append("\n**Key Commands:**")
                for cmd in entry.commands[:5]:
                    sections.append(f"```\n{cmd}\n```")

            sections.append("")  # Blank line between entries

        return "\n".join(sections)

    def augment_prompt(
        self,
        task: str,
        context: Optional[dict] = None,
        max_entries: int = 2,
    ) -> str:
        """Get knowledge augmentation text to add to an agent prompt.

        Args:
            task: The task description
            context: Optional context dict
            max_entries: Max knowledge entries to include

        Returns:
            Knowledge context string to append to prompt, or empty string
        """
        entries = self.get_relevant_knowledge(task, context, max_entries)
        if not entries:
            return ""

        return self.format_knowledge_context(
            entries,
            include_commands=True,
            include_prerequisites=True,
        )


# Singleton instance
_augmenter: Optional[KnowledgeAugmenter] = None


def get_knowledge_augmenter() -> KnowledgeAugmenter:
    """Get or create the global KnowledgeAugmenter instance."""
    global _augmenter
    if _augmenter is None:
        _augmenter = KnowledgeAugmenter()
    return _augmenter
