"""Simple log viewer utilities for cleanup operation history."""

from __future__ import annotations

import os
from typing import List

from utils import SEPARATOR


LOG_FILE_NAME = "cleaner.log"


def read_log_entries() -> List[str]:
    """Return all log lines from cleaner.log.

    Log files are a common operating-system concept for recording background
    activity, errors, and state changes for later inspection.
    """
    if not os.path.exists(LOG_FILE_NAME):
        return []

    try:
        with open(LOG_FILE_NAME, "r", encoding="utf-8") as log_file:
            return [line.rstrip() for line in log_file.readlines()]
    except OSError:
        return []


def view_logs() -> None:
    """Print the full contents of cleaner.log in a readable format."""
    entries = read_log_entries()

    if not os.path.exists(LOG_FILE_NAME):
        print("No logs found")
        return

    if not entries:
        print("Log is empty")
        return

    print("\nCleaning Logs")
    print(SEPARATOR)
    for entry in entries:
        print(entry)
    print(SEPARATOR)


def show_last_n_entries(n: int) -> None:
    """Print the last N log entries from cleaner.log."""
    entries = read_log_entries()

    if not os.path.exists(LOG_FILE_NAME):
        print("No logs found")
        return

    if not entries:
        print("Log is empty")
        return

    print("\nRecent Cleaning Logs")
    print(SEPARATOR)
    for entry in entries[-n:]:
        print(entry)
    print(SEPARATOR)
