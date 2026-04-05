"""Summary helpers for scanned junk-file data."""

from __future__ import annotations

from typing import Dict


def create_category_summary() -> Dict[str, Dict[str, int]]:
    """Return the empty category summary structure used by the analyzer."""
    return {
        "TEMP": {"count": 0, "size": 0},
        "LOG": {"count": 0, "size": 0},
        "CACHE": {"count": 0, "size": 0},
    }


def analyze_junk_data(scan_data: Dict[str, object]) -> Dict[str, object]:
    """Calculate counts and sizes for each junk-file category."""
    categories = create_category_summary()
    old_files_count = 0
    old_files_size = 0
    hidden_files = scan_data.get("hidden_files", [])
    hidden_files_count = len(hidden_files)
    hidden_files_size = sum(int(file_info.get("size", 0)) for file_info in hidden_files)

    for file_info in scan_data.get("files", []):
        file_type = file_info.get("type")
        file_size = int(file_info.get("size", 0))

        if file_type not in categories:
            continue

        categories[file_type]["count"] += 1
        categories[file_type]["size"] += file_size
        old_files_count += 1
        old_files_size += file_size

    total_files = sum(category["count"] for category in categories.values())
    total_size = int(scan_data.get("total_size", 0))

    return {
        "categories": categories,
        "total_files": total_files,
        "total_size": total_size,
        "old_files_count": old_files_count,
        "old_files_size": old_files_size,
        "hidden_files_count": hidden_files_count,
        "hidden_files_size": hidden_files_size,
    }
