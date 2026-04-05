"""Duplicate-file detection based on chunked content hashing."""

from __future__ import annotations

import hashlib
import os
from typing import Dict, List, Optional


CHUNK_SIZE = 8192
MIN_DUPLICATE_SIZE_BYTES = 1024


def get_file_hash(file_path: str) -> Optional[str]:
    """Return a SHA256 hash for a file by reading it in chunks.

    Hashing turns file content into a fixed fingerprint. Matching hashes
    suggest matching file contents, which this tool reports as duplicates.
    """
    hasher = hashlib.sha256()

    try:
        with open(file_path, "rb") as file_handle:
            while True:
                chunk = file_handle.read(CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
    except PermissionError:
        print(f"Warning: Permission denied while hashing: {file_path}")
        return None
    except FileNotFoundError:
        print(f"Warning: File not found during hashing: {file_path}")
        return None
    except OSError as error:
        print(f"Warning: Could not hash file {file_path}: {error}")
        return None

    return hasher.hexdigest()


def find_duplicates(file_paths: List[str]) -> Dict[str, List[str]]:
    """Return only hashes that map to two or more duplicate file paths."""
    hashed_files: Dict[str, List[str]] = {}

    for file_path in file_paths:
        try:
            if os.path.getsize(file_path) < MIN_DUPLICATE_SIZE_BYTES:
                continue
        except PermissionError:
            print(f"Warning: Permission denied while checking file size: {file_path}")
            continue
        except FileNotFoundError:
            print(f"Warning: File not found during duplicate check: {file_path}")
            continue
        except OSError as error:
            print(f"Warning: Could not inspect file {file_path}: {error}")
            continue

        file_hash = get_file_hash(file_path)
        if not file_hash:
            continue

        hashed_files.setdefault(file_hash, []).append(file_path)

    return {file_hash: paths for file_hash, paths in hashed_files.items() if len(paths) > 1}
