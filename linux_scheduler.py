"""Linux cron scheduling helpers for automated junk-file runs."""

from __future__ import annotations

import shlex
import subprocess


def add_cron_job(script_path: str, schedule_time: str) -> bool:
    """Append a cron job safely without overwriting existing entries.

    Cron is a standard Linux scheduling service for background process
    automation. The scheduled command must be non-interactive, so this uses
    the application's auto-clean mode instead of the menu-based entry point.
    """
    quoted_script_path = shlex.quote(script_path)
    cron_entry = f"{schedule_time} python3 {quoted_script_path} --auto-clean"

    try:
        existing_result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        print("Cron service not available")
        return False

    if existing_result.returncode not in (0, 1):
        print("Cron service not available")
        return False

    existing_cron = existing_result.stdout.strip()
    existing_lines = existing_cron.splitlines() if existing_cron else []

    if cron_entry in existing_lines:
        return True

    updated_lines = existing_lines + [cron_entry]
    updated_cron = "\n".join(updated_lines) + "\n"

    try:
        subprocess.run(
            ["crontab", "-"],
            input=updated_cron,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        print("Cron service not available")
        return False

    return True
