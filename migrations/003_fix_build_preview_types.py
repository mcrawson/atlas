"""
Migration: Fix cached build preview types

Build previews are generated once and cached. Projects that were built
before the physical→printable rename have stale preview_type values.

This migration updates:
- build.preview.preview_type: "printable" → "html" for web/app projects

Run with: python -m migrations.003_fix_build_preview_types
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime


def run_migration(db_path: str = "data/projects.db", dry_run: bool = False):
    """Fix cached build preview types."""
    print(f"\n{'='*60}")
    print("Migration: Fix cached build preview types")
    print(f"{'='*60}")
    print(f"Database: {db_path}")
    print(f"Dry run: {dry_run}")
    print()

    if not Path(db_path).exists():
        print(f"ERROR: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, metadata FROM projects")
    projects = cursor.fetchall()

    print(f"Found {len(projects)} projects to check\n")

    updated_count = 0

    for project_id, name, metadata_json in projects:
        if not metadata_json:
            continue

        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError:
            continue

        # Get the canonical product type
        identity = metadata.get("project_identity", {})
        product_type = identity.get("product_type", "")

        # Get the cached build preview
        build = metadata.get("build", {})
        preview = build.get("preview", {})
        cached_preview_type = preview.get("preview_type", "")

        # Check for mismatch
        needs_fix = False
        new_preview_type = cached_preview_type

        if product_type in ["web", "app"]:
            # Web/app should use "html" preview, not "printable"
            if cached_preview_type == "printable":
                new_preview_type = "html"
                needs_fix = True
        elif product_type == "printable":
            # Printable should use "printable" preview
            if cached_preview_type == "html":
                new_preview_type = "printable"
                needs_fix = True

        if needs_fix:
            print(f"Project {project_id}: {name[:40]}")
            print(f"  product_type: {product_type}")
            print(f"  preview_type: {cached_preview_type} → {new_preview_type}")

            # Update the preview type
            metadata["build"]["preview"]["preview_type"] = new_preview_type
            updated_count += 1

            if not dry_run:
                cursor.execute(
                    "UPDATE projects SET metadata = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(metadata), datetime.now().isoformat(), project_id)
                )

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'='*60}")
    print(f"Migration complete!")
    print(f"Projects updated: {updated_count}")
    if dry_run:
        print("(DRY RUN - no changes saved)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    run_migration(dry_run=dry_run)
