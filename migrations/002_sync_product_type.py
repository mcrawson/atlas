"""
Migration: Sync all product type fields to project_identity

The `project_identity` field is the canonical source of truth for what
type of product is being built. This migration ensures all other product
type fields match it.

Fields synced:
- project_type
- project_category
- smart_conversation.brief.project_type
- smart_conversation.brief.project_category
- business_brief.product_type
- project_type_config

Run with: python -m migrations.002_sync_product_type
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime


# Mapping from simple product_type to full details
PRODUCT_TYPE_INFO = {
    "printable": {
        "category": "printable",
        "config_name": "Printable",
        "project_type": "printable_planner",
    },
    "document": {
        "category": "document",
        "config_name": "Document",
        "project_type": "doc_book",
    },
    "web": {
        "category": "web",
        "config_name": "Web App",
        "project_type": "web_spa",
    },
    "app": {
        "category": "app",
        "config_name": "Mobile App",
        "project_type": "mobile_cross_platform",
    },
}


def sync_metadata(metadata: dict) -> tuple[dict, bool, list]:
    """
    Sync all product type fields to match project_identity.

    Returns:
        tuple: (updated_metadata, was_changed, changes_list)
    """
    changes = []

    # Check if project_identity exists
    identity = metadata.get("project_identity")
    if not identity:
        return metadata, False, ["No project_identity - skipping"]

    canonical_type = identity.get("product_type")
    if not canonical_type:
        return metadata, False, ["project_identity has no product_type - skipping"]

    # Get the expected values for this type
    type_info = PRODUCT_TYPE_INFO.get(canonical_type)
    if not type_info:
        return metadata, False, [f"Unknown product_type: {canonical_type} - skipping"]

    expected_category = type_info["category"]
    expected_project_type = type_info["project_type"]
    expected_config_name = identity.get("product_type_name", type_info["config_name"])

    changed = False

    # Sync root-level project_type
    if metadata.get("project_type") != expected_project_type:
        old = metadata.get("project_type")
        metadata["project_type"] = expected_project_type
        changes.append(f"project_type: {old} → {expected_project_type}")
        changed = True

    # Sync root-level project_category
    if metadata.get("project_category") != expected_category:
        old = metadata.get("project_category")
        metadata["project_category"] = expected_category
        changes.append(f"project_category: {old} → {expected_category}")
        changed = True

    # Sync smart_conversation.brief
    if "smart_conversation" in metadata:
        conv = metadata["smart_conversation"]
        if "brief" in conv:
            brief = conv["brief"]

            if brief.get("project_type") != expected_project_type:
                old = brief.get("project_type")
                brief["project_type"] = expected_project_type
                changes.append(f"brief.project_type: {old} → {expected_project_type}")
                changed = True

            if brief.get("project_category") != expected_category:
                old = brief.get("project_category")
                brief["project_category"] = expected_category
                changes.append(f"brief.project_category: {old} → {expected_category}")
                changed = True

    # Sync business_brief.product_type
    if "business_brief" in metadata:
        bb = metadata["business_brief"]
        if bb.get("product_type") != canonical_type:
            old = bb.get("product_type")
            bb["product_type"] = canonical_type
            changes.append(f"business_brief.product_type: {old} → {canonical_type}")
            changed = True

    # Sync project_type_config
    if "project_type_config" in metadata:
        config = metadata["project_type_config"]

        if config.get("category") != expected_category:
            old = config.get("category")
            config["category"] = expected_category
            changes.append(f"project_type_config.category: {old} → {expected_category}")
            changed = True

        if config.get("name") != expected_config_name:
            old = config.get("name")
            config["name"] = expected_config_name
            changes.append(f"project_type_config.name: {old} → {expected_config_name}")
            changed = True

    return metadata, changed, changes


def run_migration(db_path: str = "data/projects.db", dry_run: bool = False):
    """
    Run the migration on all projects.
    """
    print(f"\n{'='*60}")
    print("Migration: Sync product types to project_identity")
    print(f"{'='*60}")
    print(f"Database: {db_path}")
    print(f"Dry run: {dry_run}")
    print(f"Started: {datetime.now().isoformat()}")
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
    skipped_count = 0

    for project_id, name, metadata_json in projects:
        if not metadata_json:
            continue

        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError:
            print(f"  WARNING: Could not parse metadata for project {project_id}")
            continue

        updated_metadata, was_changed, changes = sync_metadata(metadata)

        if was_changed:
            print(f"\nProject {project_id}: {name[:50]}")
            print(f"  Source: project_identity.product_type = {metadata.get('project_identity', {}).get('product_type')}")
            for change in changes:
                print(f"    - {change}")
            updated_count += 1

            if not dry_run:
                cursor.execute(
                    "UPDATE projects SET metadata = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(updated_metadata), datetime.now().isoformat(), project_id)
                )
        elif changes and "skipping" in changes[0].lower():
            skipped_count += 1

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'='*60}")
    print(f"Migration complete!")
    print(f"Projects updated: {updated_count}")
    print(f"Projects skipped (no project_identity): {skipped_count}")
    if dry_run:
        print("(DRY RUN - no changes saved)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    run_migration(dry_run=dry_run)
