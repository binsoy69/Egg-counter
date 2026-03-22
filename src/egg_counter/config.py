"""Configuration loading for egg counter settings and zone."""

import json
from pathlib import Path

import yaml


def load_settings(path: str = "config/settings.yaml") -> dict:
    """Load application settings from a YAML file.

    Args:
        path: Path to the settings YAML file.

    Returns:
        Dict with keys: camera_index, confidence_threshold, stability_seconds,
        log_dir, location, frame_rate, bytetrack_config.
    """
    with open(path, "r") as f:
        return yaml.safe_load(f)


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
