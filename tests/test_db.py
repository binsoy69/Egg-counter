"""Tests for the SQLite-backed egg event logger."""

import sqlite3
import stat
import sys
from datetime import datetime

import pytest

from egg_counter.db import EggDatabaseLogger


class TestEggDatabaseLogger:
    """Tests for EggDatabaseLogger."""

    def test_log_egg_detected_persists(self, tmp_db_path):
        """log_egg_detected writes a durable row to egg_events."""
        logger = EggDatabaseLogger(tmp_db_path)

        try:
            logger.log_egg_detected(
                track_id=1,
                size="large",
                confidence=0.95,
                bbox=[100.0, 100.0, 200.0, 200.0],
                size_method="bbox_ratio",
                raw_measurement_mm=58.3,
                frame_number=100,
            )
        finally:
            logger.close()

        conn = sqlite3.connect(tmp_db_path)
        try:
            row = conn.execute(
                """
                SELECT
                    track_id,
                    size,
                    confidence,
                    bbox_x1,
                    bbox_y1,
                    bbox_x2,
                    bbox_y2,
                    size_method,
                    raw_measurement_mm,
                    frame_number
                FROM egg_events
                """
            ).fetchone()
        finally:
            conn.close()

        assert row == (
            1,
            "large",
            0.95,
            100.0,
            100.0,
            200.0,
            200.0,
            "bbox_ratio",
            58.3,
            100,
        )

    def test_log_egg_detected_returns_event_dict(self, tmp_db_path):
        """log_egg_detected returns the expected event payload."""
        logger = EggDatabaseLogger(tmp_db_path)

        try:
            event = logger.log_egg_detected(
                track_id=1,
                size="large",
                confidence=0.95,
                bbox=[100.0, 100.0, 200.0, 200.0],
                size_method="bbox_ratio",
                raw_measurement_mm=58.3,
                frame_number=100,
            )
        finally:
            logger.close()

        assert event["type"] == "egg_detected"
        assert datetime.fromisoformat(event["timestamp"])
        assert event["track_id"] == 1
        assert event["size"] == "large"
        assert event["confidence"] == 0.95
        assert event["bbox"] == [100.0, 100.0, 200.0, 200.0]
        assert event["size_method"] == "bbox_ratio"
        assert event["raw_measurement_mm"] == 58.3
        assert event["frame_number"] == 100

    def test_count_restores_on_restart_without_collection(self, tmp_db_path):
        """A fresh logger restores today's count from persisted eggs."""
        logger = EggDatabaseLogger(tmp_db_path)

        try:
            for track_id in range(1, 4):
                logger.log_egg_detected(
                    track_id=track_id,
                    size="large",
                    confidence=0.95,
                    bbox=[100.0, 100.0, 200.0, 200.0],
                    size_method="bbox_ratio",
                    raw_measurement_mm=58.3,
                    frame_number=100 + track_id,
                )
        finally:
            logger.close()

        new_logger = EggDatabaseLogger(tmp_db_path)
        try:
            assert new_logger.egg_count == 3
        finally:
            new_logger.close()

    def test_count_restores_after_collection_and_new_egg(self, tmp_db_path):
        """Only eggs after the last same-day collection count toward restart state."""
        logger = EggDatabaseLogger(tmp_db_path)

        try:
            for track_id in range(1, 4):
                logger.log_egg_detected(
                    track_id=track_id,
                    size="large",
                    confidence=0.95,
                    bbox=[100.0, 100.0, 200.0, 200.0],
                    size_method="bbox_ratio",
                    raw_measurement_mm=58.3,
                    frame_number=100 + track_id,
                )
            logger.log_eggs_collected(count=3)
            logger.log_egg_detected(
                track_id=4,
                size="large",
                confidence=0.95,
                bbox=[100.0, 100.0, 200.0, 200.0],
                size_method="bbox_ratio",
                raw_measurement_mm=58.3,
                frame_number=104,
            )
        finally:
            logger.close()

        new_logger = EggDatabaseLogger(tmp_db_path)
        try:
            assert new_logger.egg_count == 1
        finally:
            new_logger.close()

    def test_log_eggs_collected(self, tmp_db_path):
        """Collection events persist and reset the running count."""
        logger = EggDatabaseLogger(tmp_db_path)

        try:
            for track_id in range(1, 3):
                logger.log_egg_detected(
                    track_id=track_id,
                    size="medium",
                    confidence=0.9,
                    bbox=[50.0, 50.0, 150.0, 150.0],
                    size_method="bbox_ratio",
                    raw_measurement_mm=52.5,
                    frame_number=track_id,
                )

            assert logger.egg_count == 2
            event = logger.log_eggs_collected(count=2)
            assert logger.egg_count == 0
        finally:
            logger.close()

        conn = sqlite3.connect(tmp_db_path)
        try:
            row = conn.execute(
                "SELECT count FROM collection_events"
            ).fetchone()
        finally:
            conn.close()

        assert event["type"] == "eggs_collected"
        assert datetime.fromisoformat(event["timestamp"])
        assert event["count"] == 2
        assert row == (2,)

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="os.access unreliable on Windows",
    )
    def test_fail_fast_unwritable(self, tmp_path):
        """Logger initialization fails immediately for an unwritable database path."""
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(stat.S_IREAD | stat.S_IEXEC)
        db_path = readonly_dir / "eggs.db"

        try:
            with pytest.raises(PermissionError):
                EggDatabaseLogger(str(db_path))
        finally:
            readonly_dir.chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)

    def test_wal_mode_enabled(self, tmp_db_path):
        """The database is configured to use WAL journaling."""
        logger = EggDatabaseLogger(tmp_db_path)

        try:
            journal_mode = logger.conn.execute(
                "PRAGMA journal_mode"
            ).fetchone()[0]
        finally:
            logger.close()

        assert journal_mode.lower() == "wal"

    def test_schema_version_set(self, tmp_db_path):
        """Schema version is recorded in SQLite user_version."""
        logger = EggDatabaseLogger(tmp_db_path)

        try:
            user_version = logger.conn.execute(
                "PRAGMA user_version"
            ).fetchone()[0]
        finally:
            logger.close()

        assert user_version == 1

    def test_stdout_output(self, tmp_db_path, capsys):
        """Logging a new egg emits a human-readable stdout summary."""
        logger = EggDatabaseLogger(tmp_db_path)

        try:
            logger.log_egg_detected(
                track_id=1,
                size="large",
                confidence=0.95,
                bbox=[100.0, 100.0, 200.0, 200.0],
                size_method="bbox_ratio",
                raw_measurement_mm=58.3,
                frame_number=100,
            )
        finally:
            logger.close()

        captured = capsys.readouterr()
        assert "New egg #1" in captured.out
        assert "large" in captured.out
