"""Linux disk-usage helpers built on top of native system commands."""

from __future__ import annotations

import subprocess


def get_disk_usage(path: str) -> str:
    """Return human-readable disk usage for a path using `du -sh`.

    This uses subprocess to ask the operating system to run a native command,
    which is a common pattern when a system utility needs shell-level data.
    """
    try:
        completed_process = subprocess.run(
            ["du", "-sh", path],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        print("Error fetching disk usage")
        return ""

    return completed_process.stdout.strip()
