"""Shared utility helpers for formatting and path handling."""

from __future__ import annotations

import os
from typing import Iterable


SEPARATOR = "-" * 35


def format_size(size_in_bytes: int) -> str:
    """Convert bytes into a readable size string using KB, MB, or GB."""
    size = float(size_in_bytes)
    units = ["bytes", "KB", "MB", "GB", "TB"]

    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "bytes":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size_in_bytes} bytes"


def normalize_path(path: str) -> str:
    """Return a normalized absolute path for safe cross-platform comparisons."""
    return os.path.normcase(os.path.abspath(path))


def format_table(headers: list[str], rows: Iterable[Iterable[object]]) -> str:
    """Return a simple aligned text table for console output."""
    normalized_rows = [[str(cell) for cell in row] for row in rows]
    all_rows = [headers] + normalized_rows
    widths = [max(len(row[index]) for row in all_rows) for index in range(len(headers))]

    def build_line(row: list[str]) -> str:
        return "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))

    return "\n".join([build_line(headers), *[build_line(row) for row in normalized_rows]])
