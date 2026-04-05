"""Linux disk-space helpers built on top of the `df` system command."""

from __future__ import annotations

import subprocess

from utils import format_table


def get_disk_space() -> str:
    """Return formatted disk-space information from `df -h`.

    Disk space output describes filesystem structure and capacity, and this
    function uses a native OS command through subprocess to retrieve it.
    """
    try:
        completed_process = subprocess.run(
            ["df", "-h"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        print("Error fetching disk space info")
        return ""

    output_lines = completed_process.stdout.strip().splitlines()
    if not output_lines:
        return ""

    formatted_rows = []
    for index, line in enumerate(output_lines):
        columns = line.split()
        if index == 0 and len(columns) >= 6:
            continue

        if len(columns) >= 6:
            formatted_rows.append([columns[0], columns[1], columns[2], columns[3], columns[4]])

    return format_table(["Filesystem", "Size", "Used", "Avail", "Use%"], formatted_rows)
