"""Shared test fixtures for egg_counter tests."""

import json
import os
import tempfile

import pytest
import yaml


@pytest.fixture
def sample_zone_rect():
    """A sample zone rectangle for testing."""
    return {
        "x1": 100,
        "y1": 100,
        "x2": 500,
        "y2": 400,
        "nest_box_width_mm": 300.0,
        "frame_width": 1280,
        "frame_height": 720,
    }


@pytest.fixture
def sample_bbox_inside():
    """A bounding box with center (250, 250) -- inside sample_zone_rect."""
    return [200, 200, 300, 300]


@pytest.fixture
def sample_bbox_outside():
    """A bounding box with center (30, 30) -- outside sample_zone_rect."""
    return [10, 10, 50, 50]


@pytest.fixture
def tmp_log_dir(tmp_path):
    """Provide a temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return str(log_dir)


@pytest.fixture
def tmp_settings_file(tmp_path):
    """Write a sample settings.yaml to a temp directory and return its path."""
    settings = {
        "camera_index": 0,
        "confidence_threshold": 0.5,
        "stability_seconds": 3,
        "log_dir": "logs",
        "frame_rate": 3,
        "bytetrack_config": "config/bytetrack_eggs.yaml",
        "location": {"lat": 40.0, "lon": -75.0},
    }
    settings_path = tmp_path / "settings.yaml"
    with open(settings_path, "w") as f:
        yaml.dump(settings, f)
    return str(settings_path)


@pytest.fixture
def tmp_zone_file(tmp_path):
    """Write a sample zone.json to a temp directory and return its path."""
    zone = {
        "x1": 100,
        "y1": 100,
        "x2": 500,
        "y2": 400,
        "nest_box_width_mm": 300.0,
        "frame_width": 1280,
        "frame_height": 720,
    }
    zone_path = tmp_path / "zone.json"
    with open(zone_path, "w") as f:
        json.dump(zone, f)
    return str(zone_path)
