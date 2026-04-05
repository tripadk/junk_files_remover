"""Console entry point for the junk-file remover demo application."""

from __future__ import annotations

import os
import platform
import sys
import time
from multiprocessing import Process, Queue
from typing import Dict, List, Optional, Tuple

from analyzer import analyze_junk_data
from cleaner import background_cleaner, perform_cleanup
from config_loader import load_config
from duplicate_finder import find_duplicates
from large_file_finder import (
    DEFAULT_LARGE_FILE_THRESHOLD_BYTES,
    get_large_files,
)
from linux_scheduler import add_cron_job
from linux_disk_space import get_disk_space
from linux_process_monitor import get_process_list
from linux_disk_usage import get_disk_usage
from log_viewer import show_last_n_entries
from scanner import scan_for_junk
from utils import SEPARATOR, format_size, format_table


DEMO_MODE = True


def print_separator() -> None:
    """Print a standard separator used by the console interface."""
    print(SEPARATOR)


def print_banner(config_status: str) -> None:
    """Print the application banner, config status, and runtime mode."""
    print_separator()
    print("JUNK FILE REMOVER SYSTEM")
    print("Cross-Platform (Windows + Linux)")
    print("Implements OS Concepts: File System, IPC, Synchronization")
    print_separator()

    # Accurate system feedback helps users understand whether runtime settings
    # came from config.json or from safe fallback defaults.
    if config_status == "loaded":
        print("Config Loaded Successfully")
    elif config_status == "default":
        print("Config file not found, using default settings")
    elif config_status == "invalid":
        print("Config had invalid values, defaults applied")

    print_separator()
    if DEMO_MODE:
        print("Running in Demo Mode")
        print("Running in Demo Mode (Safe Execution)")
        print_separator()


def print_menu() -> None:
    """Print the loop-based interactive menu.

    This menu models a simple system program interface: the operating-system
    concepts stay in the modules, while the user interacts through commands.
    """
    print("\nJUNK FILE REMOVER MENU")
    print_separator()
    print("1. Scan System")
    print("2. Analyze Junk Files")
    print("3. Clean Junk Files (Move to Trash)")
    print("4. Find Duplicate Files")
    print("5. Find Large Files")
    print("6. Show Hidden Files")
    print("7. View Cleaning Logs")
    print("8. Show Disk Usage (Linux Only)")
    print("9. Show Disk Space (Linux Only)")
    print("10. Show Running Processes (Linux Only)")
    print("11. Schedule Auto Cleaning (Linux Only)")
    print("12. Help / About")
    print("13. Exit")
    print_separator()


def print_processing() -> None:
    """Print a short processing message for clearer menu flow."""
    print("\nProcessing...")
    time.sleep(0.2)


def print_summary(summary: Dict[str, object]) -> None:
    """Print the analyzed junk-file summary in a readable report."""
    print("\nScan Results")
    print_separator()
    rows = [
        [f"{category_name} FILES", f"{summary['categories'][category_name]['count']} files", format_size(int(summary['categories'][category_name]['size']))]
        for category_name in ("TEMP", "LOG", "CACHE")
    ]
    print(format_table(["Category", "Count", "Size"], rows))
    print_separator()
    print(f"TOTAL JUNK FILES: {summary['total_files']}")
    print(f"TOTAL SIZE: {format_size(int(summary['total_size']))}")
    print(f"OLD FILES: {summary['old_files_count']}")
    print(f"OLD FILE SIZE: {format_size(int(summary['old_files_size']))}")
    print(
        f"HIDDEN FILES: {summary['hidden_files_count']} files  "
        f"{format_size(int(summary['hidden_files_size']))}"
    )
    print_separator()


def get_user_choice(prompt: str) -> str:
    """Return a normalized user choice string."""
    return input(prompt).strip().lower()


def get_minimum_age_days(default_age_days: int) -> int:
    """Return the minimum file age threshold in days, using config defaults."""
    age_input = input(
        f"Enter minimum age (in days) to consider junk (e.g., {default_age_days}): "
    ).strip()

    if not age_input:
        return default_age_days

    try:
        minimum_age_days = int(age_input)
    except ValueError:
        print(f"Warning: Invalid age input. Using default of {default_age_days} days.")
        return default_age_days

    if minimum_age_days < 0:
        print(f"Warning: Negative age is not allowed. Using default of {default_age_days} days.")
        return default_age_days

    return minimum_age_days


def filter_files_by_age(scan_data: Dict[str, object], minimum_age_days: int) -> Dict[str, object]:
    """Return only file metadata that meets the minimum age threshold.

    Derived metadata such as hidden files must be preserved after filtering,
    otherwise later summaries become inconsistent with the active result set.
    """
    filtered_files = [
        file_info
        for file_info in scan_data["files"]
        if int(file_info.get("age_days", 0)) >= minimum_age_days
    ]
    filtered_hidden_files = [
        file_info
        for file_info in scan_data.get("hidden_files", [])
        if int(file_info.get("age_days", 0)) >= minimum_age_days
    ]
    filtered_total_size = sum(int(file_info.get("size", 0)) for file_info in filtered_files)

    return {
        "files": filtered_files,
        "hidden_files": filtered_hidden_files,
        "total_size": filtered_total_size,
    }


def print_age_filtered_summary(summary: Dict[str, object], minimum_age_days: int) -> None:
    """Print the subset of junk files that are older than the chosen threshold."""
    print(f"\nFiles older than {minimum_age_days} days:")
    print_separator()
    rows = [
        [category_name, f"{summary['categories'][category_name]['count']} files", format_size(int(summary['categories'][category_name]['size']))]
        for category_name in ("TEMP", "LOG", "CACHE")
    ]
    print(format_table(["Category", "Count", "Size"], rows))
    print_separator()


def print_scan_only(scan_data: Dict[str, object]) -> None:
    """Print a compact scanner-only status without running analysis."""
    print("\nScanner completed.")
    print_separator()
    print(f"FILES FOUND: {len(scan_data['files'])}")
    print(f"TOTAL SIZE: {format_size(int(scan_data['total_size']))}")
    print(
        "SKIPPED FILES (PERMISSION): "
        f"{int(scan_data.get('permission_skipped_files', 0))}"
    )
    print_separator()


def print_duplicate_groups(duplicates: Dict[str, List[str]]) -> None:
    """Print duplicate groups without deleting any files."""
    if not duplicates:
        print("\nNo duplicate files found.")
        return

    print("\nDuplicate Files Found:")
    print_separator()
    print(f"Duplicate groups: {len(duplicates)}\n")

    for group_number, file_paths in enumerate(duplicates.values(), start=1):
        print(f"Group {group_number}:")
        for file_path in file_paths:
            print(file_path)
        print()

    print_separator()


def print_large_files(large_files: List[Dict[str, object]]) -> None:
    """Print large-file findings and their combined size."""
    if not large_files:
        print("\nNo large files found.")
        return

    total_size = sum(int(file_info["size"]) for file_info in large_files)

    print("\nLarge Files Found:")
    print_separator()
    print(format_table(["Path", "Size"], [[file_info["path"], format_size(int(file_info["size"]))] for file_info in large_files]))
    print_separator()
    print(f"TOTAL LARGE FILES: {len(large_files)}")
    print(f"TOTAL LARGE FILE SIZE: {format_size(total_size)}")
    print_separator()


def print_hidden_files(hidden_files: List[Dict[str, object]]) -> None:
    """Print hidden files found during scanning."""
    if not hidden_files:
        print("\nNo hidden files found.")
        return

    total_size = sum(int(file_info.get("size", 0)) for file_info in hidden_files)

    print("\nHidden Files Found:")
    print_separator()
    print(format_table(["Path", "Size"], [[file_info["path"], format_size(int(file_info.get("size", 0)))] for file_info in hidden_files]))
    print_separator()
    print(f"TOTAL HIDDEN FILES: {len(hidden_files)}")
    print(f"TOTAL HIDDEN FILE SIZE: {format_size(total_size)}")
    print_separator()


def run_duplicate_check(scan_data: Dict[str, object]) -> None:
    """Run duplicate detection on the scanned file paths and print the result."""
    file_paths = [str(file_info["path"]) for file_info in scan_data["files"]]
    duplicates = find_duplicates(file_paths)
    print_duplicate_groups(duplicates)


def run_large_file_check(scan_data: Dict[str, object]) -> None:
    """Report files larger than the configured threshold without deleting them."""
    threshold = int(scan_data.get("large_file_threshold", DEFAULT_LARGE_FILE_THRESHOLD_BYTES))
    large_files = get_large_files(scan_data["files"], threshold)
    print_large_files(large_files)


def run_hidden_file_check(scan_data: Dict[str, object]) -> None:
    """Display hidden files captured by the scanner."""
    print_hidden_files(scan_data.get("hidden_files", []))


def run_cleanup(scan_data: Dict[str, object], minimum_age_days: int) -> None:
    """Start the background cleaner process, send cleanup work, and stop it cleanly."""
    queue = Queue()
    cleaner_process = Process(target=background_cleaner, args=(queue,))

    try:
        cleaner_process.start()
        queue.put(("clean", scan_data["files"], minimum_age_days, DEMO_MODE))
        queue.put("exit")
        cleaner_process.join()
    except PermissionError:
        print("Warning: Permission denied while starting the cleaner process.")
    except FileNotFoundError:
        print("Warning: Cleaner process resources were not available.")
    except Exception as error:
        print(f"Warning: Could not complete cleanup: {error}")
    finally:
        if cleaner_process.is_alive():
            queue.put("exit")
            cleaner_process.join()


def perform_scan(config: Dict[str, object]) -> Optional[Dict[str, object]]:
    """Run the scanner and return its raw results."""
    print_processing()
    try:
        large_file_threshold_mb = int(config.get("large_file_threshold_mb", 100))
        large_file_threshold = large_file_threshold_mb * 1024 * 1024
        junk_extensions = config.get("junk_extensions", [".tmp", ".log", ".cache"])
        return scan_for_junk(
            demo_mode=DEMO_MODE,
            large_file_threshold=large_file_threshold,
            junk_extensions=list(junk_extensions),
            include_hidden=bool(config.get("include_hidden_files", True)),
        )
    except PermissionError:
        print("Warning: Permission denied during scan.")
    except FileNotFoundError:
        print("Warning: A scan directory was not found.")
    except Exception as error:
        print(f"Warning: Unexpected scan error: {error}")

    return None


def ensure_scan_data(
    scan_data: Optional[Dict[str, object]],
    config: Dict[str, object],
) -> Optional[Dict[str, object]]:
    """Return cached scan data or run a new scan when required."""
    if scan_data is not None:
        return scan_data

    print("No scan data available. Running scanner first.")
    return perform_scan(config)


def build_filtered_results(
    scan_data: Dict[str, object],
    minimum_age_days: int,
) -> Tuple[Dict[str, object], Dict[str, object]]:
    """Return age-filtered scan data together with its analysis summary."""
    filtered_scan_data = filter_files_by_age(scan_data, minimum_age_days)
    summary = analyze_junk_data(filtered_scan_data)
    return filtered_scan_data, summary


def handle_scan_option(config: Dict[str, object]) -> Optional[Dict[str, object]]:
    """Execute menu option 1 and return fresh scan data."""
    scan_data = perform_scan(config)
    if scan_data is not None:
        print_scan_only(scan_data)
    return scan_data


def handle_analyze_option(
    scan_data: Optional[Dict[str, object]],
    config: Dict[str, object],
) -> Optional[Dict[str, object]]:
    """Execute menu option 2 and return the current raw scan state."""
    current_scan_data = ensure_scan_data(scan_data, config)
    if current_scan_data is None:
        return None

    minimum_age_days = get_minimum_age_days(int(config.get("min_age_days", 7)))
    filtered_scan_data, summary = build_filtered_results(current_scan_data, minimum_age_days)

    print_summary(summary)
    print_age_filtered_summary(summary, minimum_age_days)

    return current_scan_data


def handle_clean_option(scan_data: Optional[Dict[str, object]], config: Dict[str, object]) -> None:
    """Execute menu option 3 by scanning if needed, filtering, and moving files to Trash."""
    current_scan_data = ensure_scan_data(scan_data, config)
    if current_scan_data is None:
        return

    minimum_age_days = get_minimum_age_days(int(config.get("min_age_days", 7)))
    filtered_scan_data, summary = build_filtered_results(current_scan_data, minimum_age_days)

    print_summary(summary)
    print_age_filtered_summary(summary, minimum_age_days)

    if int(summary["total_files"]) == 0:
        print("No age-matched junk files available for cleanup.")
        return

    print("\nYou are about to move junk files to Trash")
    print_separator()
    clean_choice = get_user_choice("\nDo you want to move junk files to Trash? (y/n): ")
    if clean_choice != "y":
        print("Cleanup cancelled.")
        return

    print_processing()
    run_cleanup(filtered_scan_data, minimum_age_days)


def handle_duplicate_option(scan_data: Optional[Dict[str, object]], config: Dict[str, object]) -> None:
    """Execute menu option 4 by scanning if needed, filtering, and finding duplicates."""
    current_scan_data = ensure_scan_data(scan_data, config)
    if current_scan_data is None:
        return

    minimum_age_days = get_minimum_age_days(int(config.get("min_age_days", 7)))
    filtered_scan_data, summary = build_filtered_results(current_scan_data, minimum_age_days)

    print_summary(summary)
    print_age_filtered_summary(summary, minimum_age_days)

    if int(summary["total_files"]) == 0:
        print("No age-matched junk files available for duplicate checking.")
        return

    print_processing()
    run_duplicate_check(filtered_scan_data)


def handle_large_file_option(
    scan_data: Optional[Dict[str, object]],
    config: Dict[str, object],
) -> Optional[Dict[str, object]]:
    """Execute menu option 5 by scanning if needed and listing large files."""
    current_scan_data = ensure_scan_data(scan_data, config)
    if current_scan_data is None:
        return None

    print_processing()
    run_large_file_check(current_scan_data)
    return current_scan_data


def get_log_entry_limit() -> int:
    """Return how many recent log entries should be displayed."""
    raw_value = input("Show last how many entries? (default 10): ").strip()
    if not raw_value:
        return 10

    try:
        entry_limit = int(raw_value)
    except ValueError:
        print("Warning: Invalid number. Using default of 10.")
        return 10

    if entry_limit <= 0:
        print("Warning: Entry count must be positive. Using default of 10.")
        return 10

    return entry_limit


def handle_log_view_option() -> None:
    """Execute menu option 7 by showing recent cleanup log entries."""
    entry_limit = get_log_entry_limit()
    print_processing()
    show_last_n_entries(entry_limit)


def handle_linux_disk_usage_option() -> None:
    """Execute menu option 8 by querying Linux disk usage with system commands."""
    if platform.system() != "Linux":
        print("This feature is only available on Linux")
        return

    print_processing()

    disk_usage_paths = ["/tmp", os.path.expanduser("~/.cache")]
    print("\nDisk Usage:")
    print_separator()

    rows: list[list[str]] = []
    for disk_usage_path in disk_usage_paths:
        usage_output = get_disk_usage(disk_usage_path)
        if usage_output:
            parts = usage_output.split(maxsplit=1)
            if len(parts) == 2:
                rows.append([parts[1], parts[0]])
            else:
                rows.append([disk_usage_path, usage_output])

    if rows:
        print(format_table(["Path", "Usage"], rows))
    print_separator()


def handle_linux_disk_space_option() -> None:
    """Execute menu option 9 by querying Linux disk space with `df -h`."""
    if platform.system() != "Linux":
        print("This feature is only available on Linux")
        return

    print_processing()

    disk_space_output = get_disk_space()
    if not disk_space_output:
        return

    print("\nDisk Space:")
    print_separator()
    print(disk_space_output)
    print_separator()


def get_schedule_time() -> Optional[str]:
    """Prompt for hour and minute and return a cron schedule fragment."""
    hour_input = input("Enter hour (0-23): ").strip()
    minute_input = input("Enter minute (0-59): ").strip()

    try:
        hour = int(hour_input)
        minute = int(minute_input)
    except ValueError:
        print("Invalid schedule time")
        return None

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        print("Invalid schedule time")
        return None

    return f"{minute} {hour} * * *"


def handle_linux_scheduler_option() -> None:
    """Execute menu option 11 by adding a cron job for automated runs."""
    if platform.system() != "Linux":
        print("This feature is only available on Linux")
        return

    schedule_time = get_schedule_time()
    if not schedule_time:
        return

    script_path = os.path.abspath(__file__)
    if add_cron_job(script_path, schedule_time):
        print("Auto-clean scheduled successfully")


def handle_hidden_file_option(
    scan_data: Optional[Dict[str, object]],
    config: Dict[str, object],
) -> Optional[Dict[str, object]]:
    """Execute menu option 6 by scanning if needed and listing hidden files."""
    current_scan_data = ensure_scan_data(scan_data, config)
    if current_scan_data is None:
        return None

    print_processing()
    run_hidden_file_check(current_scan_data)
    return current_scan_data


def handle_linux_process_option() -> None:
    """Execute menu option 10 by querying the Linux process list."""
    if platform.system() != "Linux":
        print("This feature is only available on Linux")
        return

    print_processing()

    process_output = get_process_list()
    if not process_output:
        return

    print("\nRunning Processes:")
    print_separator()
    print(process_output)
    print_separator()


def handle_help_option() -> None:
    """Show a short help/about summary of the application."""
    print("\nHelp / About")
    print_separator()
    print("Core features: scanning, analysis, safe Trash cleanup, duplicate detection")
    print("Advanced features: config loading, age filtering, large-file detection, logging")
    print("Linux concepts: disk usage, disk space, process monitoring, cron scheduling")
    print("OS concepts used: file system traversal, IPC, synchronization, process automation")
    print_separator()


def run_auto_clean_mode() -> int:
    """Run non-interactive cleanup for scheduled jobs such as cron.

    Cron jobs cannot answer prompts, so this mode skips the menu and executes
    the configured scan, age filter, and cleanup steps directly.
    """
    global DEMO_MODE

    print("Running in auto-clean mode...")
    config, _ = load_config()
    DEMO_MODE = bool(config.get("demo_mode", True))

    scan_data = perform_scan(config)
    if scan_data is None:
        print("Cleaning completed")
        return 1

    minimum_age_days = int(config.get("min_age_days", 7))
    filtered_scan_data, summary = build_filtered_results(scan_data, minimum_age_days)

    if int(summary["total_files"]) == 0:
        print("Cleaning completed")
        return 0

    perform_cleanup(
        filtered_scan_data["files"],
        minimum_age_days=minimum_age_days,
        demo_mode=DEMO_MODE,
    )
    print("Cleaning completed")
    return 0


def main() -> None:
    """Run the interactive system menu until the user exits safely."""
    global DEMO_MODE

    if "--auto-clean" in sys.argv:
        raise SystemExit(run_auto_clean_mode())

    scan_data: Optional[Dict[str, object]] = None
    config, config_status = load_config()
    DEMO_MODE = bool(config.get("demo_mode", True))

    print_banner(config_status)

    while True:
        try:
            print_menu()
            choice = input("Select an option (1-13): ").strip()

            if choice == "1":
                scan_data = handle_scan_option(config)
            elif choice == "2":
                scan_data = handle_analyze_option(scan_data, config)
            elif choice == "3":
                handle_clean_option(scan_data, config)
            elif choice == "4":
                handle_duplicate_option(scan_data, config)
            elif choice == "5":
                scan_data = handle_large_file_option(scan_data, config)
            elif choice == "6":
                scan_data = handle_hidden_file_option(scan_data, config)
            elif choice == "7":
                handle_log_view_option()
            elif choice == "8":
                handle_linux_disk_usage_option()
            elif choice == "9":
                handle_linux_disk_space_option()
            elif choice == "10":
                handle_linux_process_option()
            elif choice == "11":
                handle_linux_scheduler_option()
            elif choice == "12":
                handle_help_option()
            elif choice == "13":
                print("\nExiting safely.")
                break
            else:
                print("Invalid choice, try again")
        except Exception as error:
            print(f"Warning: Operation failed: {error}")


if __name__ == "__main__":
    main()
