"""Configuration loader for user-customizable runtime settings."""

from __future__ import annotations

import json
import os
from typing import Dict, Tuple


DEFAULT_CONFIG = {
    "junk_extensions": [".tmp", ".log", ".cache"],
    "min_age_days": 7,
    "large_file_threshold_mb": 100,
    "demo_mode": True,
    "include_hidden_files": True,
}
CONFIG_FILE_NAME = "config.json"


def validate_junk_extensions(value: object) -> tuple[list[str], bool]:
    """Return validated junk extensions or a safe default.

    Config validation is important because user-edited config files can easily
    contain the wrong types, and runtime code should not trust raw JSON input.
    """
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value, False

    print("Invalid config for junk_extensions, using default value")
    return list(DEFAULT_CONFIG["junk_extensions"]), True


def validate_min_age_days(value: object) -> tuple[int, bool]:
    """Return a validated minimum age in days or the safe default."""
    if isinstance(value, int) and value >= 0:
        return value, False

    print("Invalid config for min_age_days, using default value")
    return int(DEFAULT_CONFIG["min_age_days"]), True


def validate_large_file_threshold(value: object) -> tuple[int, bool]:
    """Return a validated large-file threshold or the safe default."""
    if isinstance(value, int) and value > 0:
        return value, False

    print("Invalid config for large_file_threshold_mb, using default value")
    return int(DEFAULT_CONFIG["large_file_threshold_mb"]), True


def validate_boolean(value: object, field_name: str) -> tuple[bool, bool]:
    """Return a validated boolean config field or the matching safe default."""
    if isinstance(value, bool):
        return value, False

    print(f"Invalid config for {field_name}, using default value")
    return bool(DEFAULT_CONFIG[field_name]), True


def load_config() -> Tuple[Dict[str, object], str]:
    """Load config.json and fall back to defaults when needed.

    Configuration management lets a system tool keep runtime behavior flexible
    without changing code for every customization. Accurate status reporting
    is also important so the system can tell the user whether config values
    were loaded as-is or corrected to safe defaults.
    """
    if not os.path.exists(CONFIG_FILE_NAME):
        return dict(DEFAULT_CONFIG), "default"

    try:
        with open(CONFIG_FILE_NAME, "r", encoding="utf-8") as config_file:
            loaded_config = json.load(config_file)
    except json.JSONDecodeError:
        print("Warning: Invalid config.json. Using default configuration.")
        return dict(DEFAULT_CONFIG), "invalid"
    except OSError:
        print("Warning: Could not read config.json. Using default configuration.")
        return dict(DEFAULT_CONFIG), "invalid"

    if not isinstance(loaded_config, dict):
        print("Warning: Invalid config.json structure. Using default configuration.")
        return dict(DEFAULT_CONFIG), "invalid"

    invalid_values_found = False

    junk_extensions, field_invalid = validate_junk_extensions(loaded_config.get("junk_extensions"))
    invalid_values_found = invalid_values_found or field_invalid

    min_age_days, field_invalid = validate_min_age_days(loaded_config.get("min_age_days"))
    invalid_values_found = invalid_values_found or field_invalid

    large_file_threshold_mb, field_invalid = validate_large_file_threshold(
        loaded_config.get("large_file_threshold_mb")
    )
    invalid_values_found = invalid_values_found or field_invalid

    demo_mode, field_invalid = validate_boolean(loaded_config.get("demo_mode"), "demo_mode")
    invalid_values_found = invalid_values_found or field_invalid

    include_hidden_files, field_invalid = validate_boolean(
        loaded_config.get("include_hidden_files"),
        "include_hidden_files",
    )
    invalid_values_found = invalid_values_found or field_invalid

    config = {
        "junk_extensions": junk_extensions,
        "min_age_days": min_age_days,
        "large_file_threshold_mb": large_file_threshold_mb,
        "demo_mode": demo_mode,
        "include_hidden_files": include_hidden_files,
    }

    status = "invalid" if invalid_values_found else "loaded"
    return config, status
