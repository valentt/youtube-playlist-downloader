#!/usr/bin/env python3
"""
Migration script to rename playlist folders to human-friendly names.

Usage:
    python migrate_folders.py
    OR
    python -m migrate_folders
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import ytpl_downloader
sys.path.insert(0, str(Path(__file__).parent))

from ytpl_downloader.core.storage import PlaylistStorage


def main():
    """Run the migration."""
    print("\n" + "="*60)
    print("YouTube Playlist Downloader - Folder Migration")
    print("="*60)
    print("\nThis will rename all playlist folders from playlist IDs")
    print("to human-friendly 'Channel - PlaylistName' format.")
    print("\nExample:")
    print("  Before: PL0DH5xkJlZAb8wjrDGkOzv3UNA2ANdly1/")
    print("  After:  Valent Turkovic - Thyroid/")
    print("\n" + "="*60 + "\n")

    response = input("Continue with migration? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\nMigration cancelled.")
        return

    # Initialize storage
    storage = PlaylistStorage()

    # Run migration
    storage.migrate_to_human_friendly_names()

    print("\n✅ Migration completed!")
    print("\nYour playlist folders have been renamed.")
    print("You can now delete this script if you wish.\n")


if __name__ == '__main__':
    main()
