"""Safe cleanup helpers and background IPC worker for junk files."""

from __future__ import annotations

import logging
import os
import platform
import shutil
from multiprocessing import Queue
from typing import Dict, List

from utils import format_size, normalize_path


LOG_FILE_NAME = "cleaner.log"
LINUX_PROTECTED_DIRECTORIES = ["/bin", "/usr", "/etc", "/lib"]
WINDOWS_PROTECTED_DIRECTORIES = [r"C:\Windows", r"C:\Program Files"]

logging.basicConfig(
    filename=LOG_FILE_NAME,
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_protected_directories() -> List[str]:
    """Return the OS-specific directories that must never be modified."""
    system_name = platform.system()

    if system_name == "Linux":
        return LINUX_PROTECTED_DIRECTORIES

    if system_name == "Windows":
        return WINDOWS_PROTECTED_DIRECTORIES

    return []

def get_trash_directory() -> str:
    """Return the platform-specific Trash directory used for soft deletion."""
    if platform.system() == "Linux":
        return os.path.expanduser("~/.local/share/Trash/files")

    project_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(project_directory, "Trash")


def ensure_trash_directory() -> str:
    """Create the Trash directory if needed and return its path."""
    trash_directory = get_trash_directory()
    os.makedirs(trash_directory, exist_ok=True)
    return trash_directory

def is_protected_path(file_path: str) -> bool:
    """Return True when a file is inside a protected system directory."""
    normalized_file_path = normalize_path(file_path)

    for protected_directory in get_protected_directories():
        try:
            if os.path.commonpath([normalized_file_path, normalize_path(protected_directory)]) == normalize_path(protected_directory):
                return True
        except ValueError:
            continue

    return False


def log_cleanup_event(message: str, level: int = logging.INFO) -> None:
    """Write a cleanup event or error to cleaner.log."""
    if level >= logging.ERROR and not message.startswith("ERROR:"):
        message = f"ERROR: {message}"
    logging.log(level, message)


def get_unique_trash_path(file_path: str, trash_directory: str) -> str:
    """Return a unique destination path inside Trash to avoid name conflicts."""
    file_name = os.path.basename(file_path)
    base_name, extension = os.path.splitext(file_name)
    candidate_path = os.path.join(trash_directory, file_name)
    suffix = 1

    while os.path.exists(candidate_path):
        candidate_path = os.path.join(trash_directory, f"{base_name}_{suffix}{extension}")
        suffix += 1

    return candidate_path


def move_file_to_trash(file_path: str, trash_directory: str) -> str:
    """Soft delete a file by moving it to Trash instead of deleting it permanently."""
    destination_path = get_unique_trash_path(file_path, trash_directory)
    shutil.move(file_path, destination_path)
    return destination_path


def passes_age_filter(file_info: Dict[str, object], minimum_age_days: int) -> bool:
    """Return True when a file record is older than the configured age threshold."""
    return int(file_info.get("age_days", 0)) >= minimum_age_days


def has_write_permission(file_path: str) -> bool:
    """Return True when the current user can modify a file.

    Write permission is checked again before cleanup so protected or locked
    files are skipped instead of causing unsafe deletion attempts.
    """
    return os.access(file_path, os.W_OK)


def perform_cleanup(
    junk_files: List[Dict[str, object]],
    minimum_age_days: int,
    demo_mode: bool = False,
) -> Dict[str, int]:
    """Move approved junk files to Trash and return cleanup statistics."""
    moved_files = 0
    recovered_space = 0
    permission_skipped_files = 0
    cleanup_limit = 20 if demo_mode else None

    try:
        trash_directory = ensure_trash_directory()
    except PermissionError:
        print("Warning: Permission denied while preparing Trash.")
        log_cleanup_event("Permission denied while preparing Trash.", logging.ERROR)
        return {"moved_files": 0, "recovered_space": 0, "permission_skipped_files": 0}
    except OSError as error:
        print(f"Warning: Could not prepare Trash: {error}")
        log_cleanup_event(f"Could not prepare Trash: {error}", logging.ERROR)
        return {"moved_files": 0, "recovered_space": 0, "permission_skipped_files": 0}

    print("\nMoving files to Trash...\n")

    for file_info in junk_files:
        if cleanup_limit is not None and moved_files >= cleanup_limit:
            print("Demo Mode: trash-move limit reached.")
            break

        file_path = str(file_info.get("path", ""))
        file_size = int(file_info.get("size", 0))

        if not file_path:
            continue

        if not passes_age_filter(file_info, minimum_age_days):
            continue

        if is_protected_path(file_path):
            warning_message = f"Skipping protected path: {file_path}"
            print(f"Warning: {warning_message}")
            log_cleanup_event(warning_message, logging.WARNING)
            continue

        if not has_write_permission(file_path):
            permission_skipped_files += 1
            warning_message = f"Cannot delete (permission denied): {file_path}"
            print(warning_message)
            log_cleanup_event(warning_message, logging.WARNING)
            continue

        try:
            destination_path = move_file_to_trash(file_path, trash_directory)
            moved_files += 1
            recovered_space += file_size
            log_cleanup_event(f"Moved file to Trash: {file_path} -> {destination_path}")
        except PermissionError:
            error_message = f"Permission denied while moving to Trash: {file_path}"
            print(f"Warning: {error_message}")
            log_cleanup_event(error_message, logging.ERROR)
        except FileNotFoundError:
            error_message = f"File not found during Trash move: {file_path}"
            print(f"Warning: {error_message}")
            log_cleanup_event(error_message, logging.ERROR)
        except OSError as error:
            error_message = f"Could not move file to Trash {file_path}: {error}"
            print(f"Warning: {error_message}")
            log_cleanup_event(error_message, logging.ERROR)
        except Exception as error:
            error_message = f"Unexpected Trash move error for {file_path}: {error}"
            print(f"Warning: {error_message}")
            log_cleanup_event(error_message, logging.ERROR)

    return {
        "moved_files": moved_files,
        "recovered_space": recovered_space,
        "permission_skipped_files": permission_skipped_files,
    }


def background_cleaner(queue: Queue) -> None:
    """Process cleanup commands received from the main process through IPC.

    The Queue provides message passing between processes. The main process
    sends commands, and this worker process performs soft delete by moving
    files into Trash instead of permanently removing them.
    """
    print("Background cleaner process started")
    log_cleanup_event("Background cleaner process started")

    try:
        while True:
            message = queue.get()

            if message == "exit":
                break

            if isinstance(message, tuple) and len(message) == 4:
                command, junk_files, minimum_age_days, demo_mode = message
                if command == "clean":
                    result = perform_cleanup(
                        junk_files,
                        minimum_age_days=int(minimum_age_days),
                        demo_mode=bool(demo_mode),
                    )
                    print(f"Moved {result['moved_files']} files to Trash")
                    print(f"Recovered space: {format_size(result['recovered_space'])}")
                    print(
                        "Skipped "
                        f"{result['permission_skipped_files']} files due to permission restrictions"
                    )
                    log_cleanup_event(
                        f"Cleanup completed: {result['moved_files']} files moved, "
                        f"{result['recovered_space']} bytes recovered, "
                        f"{result['permission_skipped_files']} permission skips"
                    )
    except Exception as error:
        print(f"Warning: Cleaner process failed: {error}")
        log_cleanup_event(f"Cleaner process failed: {error}", logging.ERROR)
    finally:
        print("Background cleaner process stopped")
        log_cleanup_event("Background cleaner process stopped")
