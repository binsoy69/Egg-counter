"""Tests for egg_counter.zone module."""

import pytest

from egg_counter.zone import is_in_zone


class TestIsInZone:
    """Tests for is_in_zone function."""

    def test_is_in_zone_center_inside(self):
        """Box center (150, 150) is inside zone (50..250, 50..250)."""
        box = [100, 100, 200, 200]
        zone = {"x1": 50, "y1": 50, "x2": 250, "y2": 250}
        assert is_in_zone(box, zone) is True

    def test_is_in_zone_center_outside(self):
        """Box center (25, 25) is outside zone (100..300, 100..300)."""
        box = [10, 10, 40, 40]
        zone = {"x1": 100, "y1": 100, "x2": 300, "y2": 300}
        assert is_in_zone(box, zone) is False

    def test_is_in_zone_edge_case(self):
        """Box center (100, 100) is on boundary -- treat as inside (inclusive)."""
        box = [50, 50, 150, 150]
        zone = {"x1": 100, "y1": 100, "x2": 300, "y2": 300}
        assert is_in_zone(box, zone) is True

    def test_is_in_zone_with_fixture(self, sample_zone_rect, sample_bbox_inside):
        """Box center (250, 250) is inside sample zone (100..500, 100..400)."""
        assert is_in_zone(sample_bbox_inside, sample_zone_rect) is True

    def test_is_in_zone_outside_with_fixture(self, sample_zone_rect, sample_bbox_outside):
        """Box center (30, 30) is outside sample zone (100..500, 100..400)."""
        assert is_in_zone(sample_bbox_outside, sample_zone_rect) is False


class TestConfig:
    """Tests for egg_counter.config module."""

    def test_load_settings_returns_defaults(self, tmp_settings_file):
        from egg_counter.config import load_settings

        settings = load_settings(tmp_settings_file)
        assert "camera_index" in settings
        assert "confidence_threshold" in settings
        assert "log_dir" in settings
        assert "location" in settings
        assert settings["confidence_threshold"] == 0.5

    def test_load_zone_config(self, tmp_zone_file):
        from egg_counter.config import load_zone_config

        zone = load_zone_config(tmp_zone_file)
        assert zone["x1"] == 100
        assert zone["y1"] == 100
        assert zone["x2"] == 500
        assert zone["y2"] == 400
        assert zone["nest_box_width_mm"] == 300.0

    def test_load_zone_config_missing_file(self, tmp_path):
        from egg_counter.config import load_zone_config

        with pytest.raises(FileNotFoundError, match="Zone not configured"):
            load_zone_config(str(tmp_path / "nonexistent.json"))
