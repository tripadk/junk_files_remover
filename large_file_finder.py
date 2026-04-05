"""Helpers for reporting unusually large files from scan results."""

from __future__ import annotations

from typing import Dict, List


DEFAULT_LARGE_FILE_THRESHOLD_BYTES = 100 * 1024 * 1024


def get_large_files(file_list: List[Dict[str, object]], threshold: int) -> List[Dict[str, object]]:
    """Return files larger than the configured threshold.

    Large-file reporting helps with disk-usage optimization by highlighting
    files that consume significant storage and may deserve review.
    """
    return [
        {"path": str(file_info.get("path", "")), "size": int(file_info.get("size", 0))}
        for file_info in file_list
        if int(file_info.get("size", 0)) > threshold
    ]
