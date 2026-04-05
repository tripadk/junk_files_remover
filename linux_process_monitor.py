"""Linux process monitoring helpers built on top of the `ps` command."""

from __future__ import annotations

import subprocess

from utils import format_table


def get_process_list() -> str:
    """Return a readable subset of the `ps aux` process list.

    Process management is a core OS concept: the scheduler allocates CPU time
    across running programs, and `ps` provides a snapshot of those processes.
    """
    try:
        completed_process = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        print("Error fetching process list")
        return ""

    output_lines = completed_process.stdout.strip().splitlines()
    if not output_lines:
        return ""

    formatted_rows = []

    for line in output_lines[1:]:
        columns = line.split(None, 10)
        if len(columns) < 11:
            continue

        user, pid, cpu_percent, mem_percent = columns[0], columns[1], columns[2], columns[3]
        command = columns[10]
        formatted_rows.append([user, pid, cpu_percent, mem_percent, command])

    return format_table(["USER", "PID", "CPU%", "MEM%", "COMMAND"], formatted_rows)
