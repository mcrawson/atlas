"""Knowledge Base Manager - CRUD and search operations."""

import json
import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime

from .models import KnowledgeEntry, KnowledgeCategory, SearchResult


class KnowledgeManager:
    """Manages the knowledge base with SQLite storage."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the knowledge manager.

        Args:
            db_path: Path to SQLite database. Defaults to data/knowledge.db
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "knowledge.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._load_base_knowledge()

    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,
                    platform TEXT,
                    prerequisites TEXT,
                    related_entries TEXT,
                    commands TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    source TEXT
                )
            """)
            # Full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    id,
                    title,
                    content,
                    tags,
                    platform,
                    content='knowledge',
                    content_rowid='rowid'
                )
            """)
            # Triggers to keep FTS in sync
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
                    INSERT INTO knowledge_fts(rowid, id, title, content, tags, platform)
                    VALUES (new.rowid, new.id, new.title, new.content, new.tags, new.platform);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
                    INSERT INTO knowledge_fts(knowledge_fts, rowid, id, title, content, tags, platform)
                    VALUES ('delete', old.rowid, old.id, old.title, old.content, old.tags, old.platform);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
                    INSERT INTO knowledge_fts(knowledge_fts, rowid, id, title, content, tags, platform)
                    VALUES ('delete', old.rowid, old.id, old.title, old.content, old.tags, old.platform);
                    INSERT INTO knowledge_fts(rowid, id, title, content, tags, platform)
                    VALUES (new.rowid, new.id, new.title, new.content, new.tags, new.platform);
                END
            """)
            conn.commit()

    def _load_base_knowledge(self):
        """Load base knowledge if not already present."""
        from .base_knowledge import BASE_KNOWLEDGE

        for entry_data in BASE_KNOWLEDGE:
            entry = KnowledgeEntry.from_dict(entry_data)
            if not self.get(entry.id):
                self.add(entry)

    def add(self, entry: KnowledgeEntry) -> bool:
        """Add a knowledge entry.

        Args:
            entry: The knowledge entry to add

        Returns:
            True if added successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO knowledge
                    (id, title, category, content, tags, platform, prerequisites,
                     related_entries, commands, created_at, updated_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.id,
                    entry.title,
                    entry.category.value,
                    entry.content,
                    json.dumps(entry.tags),
                    entry.platform,
                    json.dumps(entry.prerequisites),
                    json.dumps(entry.related_entries),
                    json.dumps(entry.commands),
                    entry.created_at.isoformat(),
                    entry.updated_at.isoformat(),
                    entry.source,
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error adding knowledge entry: {e}")
            return False

    def get(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get a knowledge entry by ID.

        Args:
            entry_id: The entry ID

        Returns:
            The knowledge entry or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM knowledge WHERE id = ?",
                (entry_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entry(row)
        return None

    def get_by_platform(self, platform: str) -> list[KnowledgeEntry]:
        """Get all entries for a platform.

        Args:
            platform: The platform (ios, android, web, etc.)

        Returns:
            List of matching entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM knowledge WHERE platform = ? ORDER BY category, title",
                (platform.lower(),)
            )
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get_by_category(self, category: KnowledgeCategory) -> list[KnowledgeEntry]:
        """Get all entries in a category.

        Args:
            category: The category

        Returns:
            List of matching entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM knowledge WHERE category = ? ORDER BY title",
                (category.value,)
            )
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search the knowledge base.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of search results with relevance scores
        """
        results = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # FTS search
            try:
                cursor = conn.execute("""
                    SELECT k.*, bm25(knowledge_fts) as score
                    FROM knowledge k
                    JOIN knowledge_fts ON k.id = knowledge_fts.id
                    WHERE knowledge_fts MATCH ?
                    ORDER BY score
                    LIMIT ?
                """, (query, limit))

                for row in cursor.fetchall():
                    entry = self._row_to_entry(row)
                    score = -row["score"]  # bm25 returns negative scores
                    matched_on = self._find_matches(entry, query)
                    results.append(SearchResult(
                        entry=entry,
                        relevance_score=score,
                        matched_on=matched_on,
                    ))
            except sqlite3.OperationalError:
                # Fallback to LIKE search
                cursor = conn.execute("""
                    SELECT * FROM knowledge
                    WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))

                for row in cursor.fetchall():
                    entry = self._row_to_entry(row)
                    matched_on = self._find_matches(entry, query)
                    results.append(SearchResult(
                        entry=entry,
                        relevance_score=1.0,
                        matched_on=matched_on,
                    ))

        return results

    def get_deployment_guide(self, platform: str) -> Optional[KnowledgeEntry]:
        """Get the deployment guide for a platform.

        Args:
            platform: The platform (ios, android, web, etc.)

        Returns:
            The deployment guide entry or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM knowledge
                WHERE platform = ? AND category = ?
                LIMIT 1
            """, (platform.lower(), KnowledgeCategory.DEPLOYMENT.value))
            row = cursor.fetchone()
            if row:
                return self._row_to_entry(row)
        return None

    def get_all(self) -> list[KnowledgeEntry]:
        """Get all knowledge entries.

        Returns:
            List of all entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM knowledge ORDER BY category, title")
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def delete(self, entry_id: str) -> bool:
        """Delete a knowledge entry.

        Args:
            entry_id: The entry ID to delete

        Returns:
            True if deleted
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM knowledge WHERE id = ?", (entry_id,))
                conn.commit()
            return True
        except Exception:
            return False

    def _row_to_entry(self, row: sqlite3.Row) -> KnowledgeEntry:
        """Convert a database row to a KnowledgeEntry."""
        return KnowledgeEntry(
            id=row["id"],
            title=row["title"],
            category=KnowledgeCategory(row["category"]),
            content=row["content"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            platform=row["platform"],
            prerequisites=json.loads(row["prerequisites"]) if row["prerequisites"] else [],
            related_entries=json.loads(row["related_entries"]) if row["related_entries"] else [],
            commands=json.loads(row["commands"]) if row["commands"] else [],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
            source=row["source"],
        )

    def _find_matches(self, entry: KnowledgeEntry, query: str) -> list[str]:
        """Find which fields matched the query."""
        matches = []
        query_lower = query.lower()

        if query_lower in entry.title.lower():
            matches.append("title")
        if query_lower in entry.content.lower():
            matches.append("content")
        if any(query_lower in tag.lower() for tag in entry.tags):
            matches.append("tags")
        if entry.platform and query_lower in entry.platform.lower():
            matches.append("platform")

        return matches
