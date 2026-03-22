"""Tests for egg_counter.logger and egg_counter.scheduler modules."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from egg_counter.logger import EggEventLogger


class TestEggEventLogger:
    """Tests for EggEventLogger class."""

    def test_log_egg_detected_writes_jsonl(self, tmp_log_dir):
        """log_egg_detected appends one line of valid JSON to the daily log file."""
        logger = EggEventLogger(tmp_log_dir)
        logger.log_egg_detected(
            track_id=1,
            size="large",
            confidence=0.95,
            bbox=[100.0, 100.0, 200.0, 200.0],
            size_method="bbox_ratio",
            raw_measurement_mm=58.3,
            frame_number=100,
        )

        # Find the log file
        log_files = list(Path(tmp_log_dir).glob("eggs-*.jsonl"))
        assert len(log_files) == 1

        with open(log_files[0]) as f:
            lines = f.readlines()
        assert len(lines) == 1

        event = json.loads(lines[0])
        assert event["track_id"] == 1
        assert event["size"] == "large"
        assert event["confidence"] == 0.95
        assert event["bbox"] == [100.0, 100.0, 200.0, 200.0]
        assert event["size_method"] == "bbox_ratio"
        assert event["raw_measurement_mm"] == 58.3
        assert event["frame_number"] == 100

    def test_log_egg_detected_type_field(self, tmp_log_dir):
        """Event type field should be 'egg_detected'."""
        logger = EggEventLogger(tmp_log_dir)
        event = logger.log_egg_detected(
            track_id=1,
            size="medium",
            confidence=0.8,
            bbox=[50.0, 50.0, 150.0, 150.0],
            size_method="bbox_ratio",
            raw_measurement_mm=45.0,
            frame_number=50,
        )
        assert event["type"] == "egg_detected"

    def test_log_eggs_collected(self, tmp_log_dir):
        """log_eggs_collected writes event with type='eggs_collected' and count."""
        logger = EggEventLogger(tmp_log_dir)
        event = logger.log_eggs_collected(count=5)
        assert event["type"] == "eggs_collected"
        assert event["count"] == 5

    def test_daily_rotation(self, tmp_log_dir):
        """Logging on different dates creates separate files."""
        logger = EggEventLogger(tmp_log_dir)

        with patch("egg_counter.logger.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            logger.log_egg_detected(
                track_id=1, size="large", confidence=0.9,
                bbox=[100.0, 100.0, 200.0, 200.0], size_method="bbox_ratio",
                raw_measurement_mm=55.0, frame_number=1,
            )

            mock_dt.now.return_value = datetime(2026, 3, 21, 12, 0, 0, tzinfo=timezone.utc)
            logger.log_egg_detected(
                track_id=2, size="medium", confidence=0.85,
                bbox=[150.0, 150.0, 250.0, 250.0], size_method="bbox_ratio",
                raw_measurement_mm=48.0, frame_number=2,
            )

        log_files = list(Path(tmp_log_dir).glob("eggs-*.jsonl"))
        assert len(log_files) == 2

    def test_required_fields_present(self, tmp_log_dir):
        """Every logged event contains all fields from D-15."""
        logger = EggEventLogger(tmp_log_dir)
        event = logger.log_egg_detected(
            track_id=42,
            size="jumbo",
            confidence=0.99,
            bbox=[10.0, 20.0, 30.0, 40.0],
            size_method="reference_object",
            raw_measurement_mm=65.0,
            frame_number=999,
        )

        required_fields = [
            "type", "timestamp", "track_id", "size", "confidence",
            "bbox", "size_method", "raw_measurement_mm", "frame_number",
        ]
        for field in required_fields:
            assert field in event, f"Missing required field: {field}"

    def test_stdout_summary(self, tmp_log_dir, capsys):
        """log_egg_detected prints human-readable line to stdout (D-16)."""
        logger = EggEventLogger(tmp_log_dir)
        logger.log_egg_detected(
            track_id=1, size="large", confidence=0.95,
            bbox=[100.0, 100.0, 200.0, 200.0], size_method="bbox_ratio",
            raw_measurement_mm=58.3, frame_number=100,
        )

        captured = capsys.readouterr()
        assert "New egg #1" in captured.out
        assert "large" in captured.out


class TestDaylightScheduler:
    """Tests for egg_counter.scheduler module."""

    def test_is_daylight_daytime(self):
        """is_daylight returns True when mocked time is noon local (16:00 UTC)."""
        from egg_counter.scheduler import is_daylight

        # Noon EDT = 16:00 UTC on June 21 at lat 40, lon -75
        noon_utc = datetime(2026, 6, 21, 16, 0, 0, tzinfo=timezone.utc)
        with patch("egg_counter.scheduler._utcnow", return_value=noon_utc):
            result = is_daylight(40.0, -75.0)
            assert result is True

    def test_is_daylight_nighttime(self):
        """is_daylight returns False when mocked time is midnight local (04:00 UTC)."""
        from egg_counter.scheduler import is_daylight

        # Midnight EDT = 04:00 UTC on June 21 at lat 40, lon -75
        midnight_utc = datetime(2026, 6, 21, 4, 0, 0, tzinfo=timezone.utc)
        with patch("egg_counter.scheduler._utcnow", return_value=midnight_utc):
            result = is_daylight(40.0, -75.0)
            assert result is False
