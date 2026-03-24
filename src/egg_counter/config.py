"""Configuration loading for egg counter settings and zone."""

import json
import os
from pathlib import Path

import yaml


_ENV_SETTING_MAP = {
    "EGG_COUNTER_AUTH_USERNAME": "auth_username",
    "EGG_COUNTER_AUTH_PASSWORD_HASH": "auth_password_hash",
    "EGG_COUNTER_SESSION_SECRET": "session_secret",
}


def load_settings(path: str = "config/settings.yaml") -> dict:
    """Load application settings from a YAML file.

    Args:
        path: Path to the settings YAML file.

    Returns:
        Dict with keys: camera_index, confidence_threshold, stability_seconds,
        log_dir, db_path, location, frame_rate, bytetrack_config.
    """
    with open(path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f) or {}

    for env_key, setting_key in _ENV_SETTING_MAP.items():
        value = os.getenv(env_key)
        if value is not None:
            settings[setting_key] = value

    session_max_age = os.getenv("EGG_COUNTER_SESSION_MAX_AGE")
    if session_max_age is not None:
        settings["session_max_age"] = int(session_max_age)

    return settings


def load_zone_config(path: str = "config/zone.json") -> dict:
    """Load zone configuration from a JSON file.

    Args:
        path: Path to the zone JSON file.

    Returns:
        Dict with keys: x1, y1, x2, y2, nest_box_width_mm, frame_width,
        frame_height.

    Raises:
        FileNotFoundError: If the zone config file does not exist.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            "Zone not configured. Run: python tools/setup_zone.py"
        )

    with open(config_path, "r") as f:
        return json.load(f)
