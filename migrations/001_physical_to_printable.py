"""
Migration: Rename 'physical' terminology to 'printable'

This migration updates all projects that have old "physical_*" terminology
to use the correct "printable_*" terminology.

ATLAS creates digital PDFs that customers print themselves - not physical products.
The old "physical" naming was confusing.

Run with: python -m migrations.001_physical_to_printable
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime


def migrate_metadata(metadata: dict) -> tuple[dict, bool]:
    """
    Migrate a single project's metadata from physical to printable terminology.

    Returns:
        tuple: (updated_metadata, was_changed)
    """
    changed = False

    # Mappings for replacement
    type_mapping = {
        "physical_planner": "printable_planner",
        "physical_journal": "printable_journal",
        "physical_workbook": "printable_workbook",
        "physical_cards": "printable_cards",
        "physical_printable": "printable_other",
    }

    category_mapping = {
        "physical": "printable",
    }

    name_mapping = {
        "Physical Planner": "Printable Planner",
        "Physical Journal": "Printable Journal",
        "Physical Workbook": "Printable Workbook",
        "Physical Cards": "Printable Cards",
    }

    # Update smart_conversation.brief
    if "smart_conversation" in metadata:
        conv = metadata["smart_conversation"]
        if "brief" in conv:
            brief = conv["brief"]

            # Update project_type
            if brief.get("project_type") in type_mapping:
                old_val = brief["project_type"]
                brief["project_type"] = type_mapping[old_val]
                changed = True
                print(f"    - brief.project_type: {old_val} → {brief['project_type']}")

            # Update project_category
            if brief.get("project_category") in category_mapping:
                old_val = brief["project_category"]
                brief["project_category"] = category_mapping[old_val]
                changed = True
                print(f"    - brief.project_category: {old_val} → {brief['project_category']}")

    # Update project_type at root level
    if metadata.get("project_type") in type_mapping:
        old_val = metadata["project_type"]
        metadata["project_type"] = type_mapping[old_val]
        changed = True
        print(f"    - project_type: {old_val} → {metadata['project_type']}")

    # Update project_category at root level
    if metadata.get("project_category") in category_mapping:
        old_val = metadata["project_category"]
        metadata["project_category"] = category_mapping[old_val]
        changed = True
        print(f"    - project_category: {old_val} → {metadata['project_category']}")

    # Update project_type_config if present
    if "project_type_config" in metadata:
        config = metadata["project_type_config"]

        if config.get("type") in type_mapping:
            old_val = config["type"]
            config["type"] = type_mapping[old_val]
            changed = True
            print(f"    - project_type_config.type: {old_val} → {config['type']}")

        if config.get("category") in category_mapping:
            old_val = config["category"]
            config["category"] = category_mapping[old_val]
            changed = True
            print(f"    - project_type_config.category: {old_val} → {config['category']}")

        if config.get("name") in name_mapping:
            old_val = config["name"]
            config["name"] = name_mapping[old_val]
            changed = True
            print(f"    - project_type_config.name: {old_val} → {config['name']}")

    # Update business_brief if present
    if "business_brief" in metadata:
        brief = metadata["business_brief"]

        if brief.get("product_type") in type_mapping:
            old_val = brief["product_type"]
            brief["product_type"] = type_mapping[old_val]
            changed = True
            print(f"    - business_brief.product_type: {old_val} → {brief['product_type']}")

    # Update project_identity if somehow it has old values
    if "project_identity" in metadata:
        identity = metadata["project_identity"]

        if identity.get("product_type") in type_mapping:
            old_val = identity["product_type"]
            identity["product_type"] = type_mapping[old_val]
            changed = True
            print(f"    - project_identity.product_type: {old_val} → {identity['product_type']}")

        if identity.get("product_type_name") in name_mapping:
            old_val = identity["product_type_name"]
            identity["product_type_name"] = name_mapping[old_val]
            changed = True
            print(f"    - project_identity.product_type_name: {old_val} → {identity['product_type_name']}")

    return metadata, changed


def run_migration(db_path: str = "data/projects.db", dry_run: bool = False):
    """
    Run the migration on all projects.

    Args:
        db_path: Path to the projects database
        dry_run: If True, don't actually save changes
    """
    print(f"\n{'='*60}")
    print("Migration: physical → printable terminology")
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

    # Get all projects
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
            print(f"  WARNING: Could not parse metadata for project {project_id}")
            continue

        # Check if this project needs migration
        updated_metadata, was_changed = migrate_metadata(metadata)

        if was_changed:
            print(f"\n  Project {project_id}: {name}")
            updated_count += 1

            if not dry_run:
                # Save the updated metadata
                cursor.execute(
                    "UPDATE projects SET metadata = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(updated_metadata), datetime.now().isoformat(), project_id)
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

    # Check for --dry-run flag
    dry_run = "--dry-run" in sys.argv

    # Run migration
    run_migration(dry_run=dry_run)
