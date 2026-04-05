"""Threaded scanner for safe junk-file locations on Windows and Linux."""

from __future__ import annotations

import os
import platform
import tempfile
import threading
import time
from typing import Dict, List

from utils import normalize_path


DEFAULT_JUNK_FILE_TYPES = {
    ".tmp": "TEMP",
    ".log": "LOG",
    ".cache": "CACHE",
}
LINUX_SAFE_DIRECTORIES = ["/tmp", os.path.expanduser("~/.cache")]
LINUX_UNSAFE_DIRECTORIES = ["/bin", "/usr", "/etc", "/lib"]
WINDOWS_UNSAFE_DIRECTORIES = [r"C:\Windows", r"C:\Program Files"]
DEMO_MAX_RESULTS_PER_DIRECTORY = 100
PROGRESS_BAR_WIDTH = 20
DEFAULT_LARGE_FILE_THRESHOLD_BYTES = 100 * 1024 * 1024


def build_extension_map(junk_extensions: List[str]) -> Dict[str, str]:
    """Return the extension-to-type mapping used by the scanner."""
    extension_map: Dict[str, str] = {}

    for extension in junk_extensions:
        normalized_extension = extension.lower()
        if not normalized_extension.startswith("."):
            normalized_extension = f".{normalized_extension}"

        extension_map[normalized_extension] = DEFAULT_JUNK_FILE_TYPES.get(
            normalized_extension,
            normalized_extension.lstrip(".").upper() or "UNKNOWN",
        )

    return extension_map


def get_safe_directories() -> List[str]:
    """Return the OS-specific directories that this project is allowed to scan."""
    system_name = platform.system()

    if system_name == "Linux":
        return LINUX_SAFE_DIRECTORIES

    if system_name == "Windows":
        temp_directories = []
        for candidate in (tempfile.gettempdir(), os.environ.get("TEMP"), os.environ.get("TMP")):
            if candidate and candidate not in temp_directories:
                temp_directories.append(candidate)
        return temp_directories

    return []


def get_unsafe_directories() -> List[str]:
    """Return directories that should never be scanned or cleaned."""
    system_name = platform.system()

    if system_name == "Linux":
        return LINUX_UNSAFE_DIRECTORIES

    if system_name == "Windows":
        return WINDOWS_UNSAFE_DIRECTORIES

    return []


def is_within_directory(file_path: str, parent_directory: str) -> bool:
    """Return True when a path is inside a parent directory."""
    try:
        return os.path.commonpath([normalize_path(file_path), normalize_path(parent_directory)]) == normalize_path(parent_directory)
    except ValueError:
        return False


def validate_safe_directory(directory: str) -> bool:
    """Validate that a directory is explicitly allowed for scanning."""
    if not directory:
        return False

    if any(is_within_directory(directory, unsafe_directory) for unsafe_directory in get_unsafe_directories()):
        print(f"Warning: Unsafe path skipped: {directory}")
        return False

    safe_directories = get_safe_directories()
    if not any(normalize_path(directory) == normalize_path(safe_directory) for safe_directory in safe_directories):
        print(f"Warning: Path is outside approved scan locations: {directory}")
        return False

    if not os.path.isdir(directory):
        print(f"Warning: Scan directory not available: {directory}")
        return False

    return True


def count_directories_in_path(directory: str) -> int:
    """Return the number of directories that will contribute to scan progress."""
    if not validate_safe_directory(directory):
        return 0

    directory_count = 0

    try:
        for _, subdirectories, _ in os.walk(directory):
            directory_count += 1
            for subdirectory in subdirectories:
                _ = subdirectory
    except PermissionError:
        print(f"Warning: Permission denied while counting directories: {directory}")
    except FileNotFoundError:
        print(f"Warning: Directory unavailable during counting: {directory}")
    except OSError as error:
        print(f"Warning: Could not count directories in {directory}: {error}")

    return directory_count


def render_progress_bar(processed_directories: int, total_directories: int) -> int:
    """Print a single-line progress bar that updates during scanning.

    Progress tracking compares processed directories with the total directory
    count, which gives a lightweight view of scan completion in real time.
    """
    if total_directories <= 0:
        total_directories = 1

    progress_ratio = min(processed_directories / total_directories, 1.0)
    filled_length = int(PROGRESS_BAR_WIDTH * progress_ratio)
    bar = "#" * filled_length + "-" * (PROGRESS_BAR_WIDTH - filled_length)
    percentage = int(progress_ratio * 100)
    print(f"Scanning... [{bar}] {percentage}%", end="\r", flush=True)
    return percentage


def update_progress_display(progress: Dict[str, int]) -> None:
    """Refresh the progress bar only when the visible percentage changes enough."""
    percentage = int(
        min(progress["processed_directories"] / max(progress["total_directories"], 1), 1.0) * 100
    )
    last_percentage = progress.get("last_percentage", -1)

    if percentage == last_percentage:
        return

    if percentage in (0, 100) or percentage - last_percentage >= 5:
        progress["last_percentage"] = render_progress_bar(
            progress["processed_directories"],
            progress["total_directories"],
        )


def count_total_directories(directories: List[str]) -> int:
    """Return the total number of approved directories that will be scanned."""
    total_directories = sum(count_directories_in_path(directory) for directory in directories)
    return max(total_directories, 1)


def get_file_age_in_days(file_path: str) -> int:
    """Return the age of a file in days using its last modified timestamp.

    File metadata such as modification time helps classify which junk files
    are old enough to be considered safer candidates for cleanup.
    """
    modified_timestamp = os.path.getmtime(file_path)
    age_in_seconds = time.time() - modified_timestamp
    return max(0, int(age_in_seconds // 86400))


def has_required_permissions(file_path: str) -> bool:
    """Return True when a file is both readable and writable.

    File permissions are an OS protection mechanism. This scanner only works
    with files that can be read and later cleaned safely by the current user.
    """
    return os.access(file_path, os.R_OK) and os.access(file_path, os.W_OK)


def is_hidden_file(file_path: str) -> bool:
    """Return True when a file uses the dot-prefix hidden-file convention.

    Hidden files are commonly represented on Linux by names that start with
    a dot, which keeps configuration and background data out of normal views.
    """
    return os.path.basename(file_path).startswith(".")


def scan_folder(
    directory: str,
    files: List[Dict[str, object]],
    large_files: List[Dict[str, object]],
    hidden_files: List[Dict[str, object]],
    totals: Dict[str, int],
    lock: threading.Lock,
    progress: Dict[str, int],
    demo_mode: bool,
    large_file_threshold: int,
    extension_map: Dict[str, str],
    include_hidden: bool,
) -> None:
    """Scan one approved directory and add junk files to shared results."""
    if not validate_safe_directory(directory):
        return

    results_in_directory = 0

    try:
        for root, _, file_names in os.walk(directory):
            for file_name in file_names:
                _, extension = os.path.splitext(file_name)
                file_type = extension_map.get(extension.lower())
                if not file_type:
                    continue

                file_path = os.path.join(root, file_name)

                if is_hidden_file(file_path):
                    if not include_hidden:
                        continue

                    try:
                        hidden_file_size = os.path.getsize(file_path)
                        hidden_last_modified = os.path.getmtime(file_path)
                        hidden_age_days = get_file_age_in_days(file_path)
                    except (PermissionError, FileNotFoundError, OSError):
                        hidden_file_size = 0
                        hidden_last_modified = 0.0
                        hidden_age_days = 0

                    with lock:
                        hidden_files.append(
                            {
                                "path": file_path,
                                "size": hidden_file_size,
                                "last_modified": hidden_last_modified,
                                "age_days": hidden_age_days,
                            }
                        )

                if not has_required_permissions(file_path):
                    print(f"Skipping file (no permission): {file_path}")
                    with lock:
                        totals["permission_skipped_files"] += 1
                    continue

                try:
                    file_size = os.path.getsize(file_path)
                    last_modified = os.path.getmtime(file_path)
                    age_in_days = get_file_age_in_days(file_path)
                except PermissionError:
                    print(f"Warning: Permission denied while scanning: {file_path}")
                    continue
                except FileNotFoundError:
                    print(f"Warning: File disappeared during scan: {file_path}")
                    continue
                except OSError as error:
                    print(f"Warning: Could not read file size for {file_path}: {error}")
                    continue

                file_data = {
                    "path": file_path,
                    "size": file_size,
                    "type": file_type,
                    "last_modified": last_modified,
                    "age_days": age_in_days,
                }

                # This is the critical section. Multiple threads update the same
                # shared list and total-size counter, so the lock prevents races.
                with lock:
                    files.append(file_data)
                    totals["total_size"] += file_size
                    if file_size > large_file_threshold:
                        large_files.append({"path": file_path, "size": file_size})

                results_in_directory += 1
                if demo_mode and results_in_directory >= DEMO_MAX_RESULTS_PER_DIRECTORY:
                    with lock:
                        progress["processed_directories"] += 1
                        update_progress_display(progress)
                    return
            with lock:
                progress["processed_directories"] += 1
                update_progress_display(progress)
    except PermissionError:
        print(f"Warning: Permission denied while traversing: {directory}")
    except FileNotFoundError:
        print(f"Warning: Directory unavailable during scan: {directory}")
    except OSError as error:
        print(f"Warning: Could not scan directory {directory}: {error}")


def scan_for_junk(
    demo_mode: bool = False,
    large_file_threshold: int = DEFAULT_LARGE_FILE_THRESHOLD_BYTES,
    junk_extensions: List[str] | None = None,
    include_hidden: bool = True,
) -> Dict[str, object]:
    """Scan all approved directories in parallel and return structured results."""
    files: List[Dict[str, object]] = []
    large_files: List[Dict[str, object]] = []
    hidden_files: List[Dict[str, object]] = []
    extension_map = build_extension_map(junk_extensions or [".tmp", ".log", ".cache"])
    safe_directories = get_safe_directories()
    totals = {"total_size": 0, "permission_skipped_files": 0}
    progress = {
        "processed_directories": 0,
        "total_directories": count_total_directories(safe_directories),
        "last_percentage": -1,
    }
    lock = threading.Lock()
    threads: List[threading.Thread] = []

    update_progress_display(progress)

    for index, directory in enumerate(safe_directories, start=1):
        thread = threading.Thread(
            target=scan_folder,
            args=(
                directory,
                files,
                large_files,
                hidden_files,
                totals,
                lock,
                progress,
                demo_mode,
                large_file_threshold,
                extension_map,
                include_hidden,
            ),
            name=f"scanner-thread-{index}",
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    progress["processed_directories"] = progress["total_directories"]
    update_progress_display(progress)
    print("\nScanning Complete!")

    return {
        "files": files,
        "total_size": totals["total_size"],
        "permission_skipped_files": totals["permission_skipped_files"],
        "large_files": large_files,
        "hidden_files": hidden_files,
        "large_file_threshold": large_file_threshold,
    }
