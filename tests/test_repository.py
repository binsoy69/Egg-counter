"""Tests for the EggRepository query interface."""

import sqlite3
from datetime import date

from egg_counter.db import EggDatabaseLogger
from egg_counter.repository import EggRepository


def _initialize_db(tmp_db_path: str) -> None:
    logger = EggDatabaseLogger(tmp_db_path)
    logger.close()


def _insert_egg(conn: sqlite3.Connection, detected_date: str, size: str) -> None:
    conn.execute(
        """
        INSERT INTO egg_events (
            timestamp,
            detected_date,
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
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"{detected_date}T12:00:00+00:00",
            detected_date,
            1,
            size,
            0.9,
            0.0,
            0.0,
            0.0,
            0.0,
            "bbox_ratio",
            50.0,
            1,
        ),
    )


class TestEggRepository:
    """Tests for EggRepository."""

    def test_get_daily_summary(self, tmp_db_path):
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            _insert_egg(conn, "2026-03-20", "large")
            _insert_egg(conn, "2026-03-20", "large")
            _insert_egg(conn, "2026-03-20", "medium")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            summary = repo.get_daily_summary(date(2026, 3, 20))
        finally:
            repo.close()

        assert summary == {
            "date": "2026-03-20",
            "total": 3,
            "by_size": {"large": 2, "medium": 1},
        }

    def test_get_daily_summary_empty_date(self, tmp_db_path):
        _initialize_db(tmp_db_path)

        repo = EggRepository(tmp_db_path)
        try:
            summary = repo.get_daily_summary(date(2026, 3, 20))
        finally:
            repo.close()

        assert summary == {
            "date": "2026-03-20",
            "total": 0,
            "by_size": {},
        }

    def test_get_eggs_by_date_range(self, tmp_db_path):
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            _insert_egg(conn, "2026-03-18", "large")
            _insert_egg(conn, "2026-03-18", "medium")
            _insert_egg(conn, "2026-03-19", "large")
            _insert_egg(conn, "2026-03-19", "large")
            _insert_egg(conn, "2026-03-19", "jumbo")
            _insert_egg(conn, "2026-03-20", "medium")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            results = repo.get_eggs_by_date_range(
                date(2026, 3, 18),
                date(2026, 3, 20),
            )
        finally:
            repo.close()

        assert results == [
            {"date": "2026-03-18", "total": 2},
            {"date": "2026-03-19", "total": 3},
            {"date": "2026-03-20", "total": 1},
        ]

    def test_get_eggs_by_date_range_empty(self, tmp_db_path):
        _initialize_db(tmp_db_path)

        repo = EggRepository(tmp_db_path)
        try:
            results = repo.get_eggs_by_date_range(
                date(2026, 3, 18),
                date(2026, 3, 20),
            )
        finally:
            repo.close()

        assert results == []

    def test_get_size_breakdown(self, tmp_db_path):
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            _insert_egg(conn, "2026-03-18", "large")
            _insert_egg(conn, "2026-03-18", "large")
            _insert_egg(conn, "2026-03-19", "medium")
            _insert_egg(conn, "2026-03-19", "medium")
            _insert_egg(conn, "2026-03-20", "jumbo")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            results = repo.get_size_breakdown(
                date(2026, 3, 18),
                date(2026, 3, 20),
            )
        finally:
            repo.close()

        assert results == {"large": 2, "medium": 2, "jumbo": 1}

    def test_get_size_breakdown_empty(self, tmp_db_path):
        _initialize_db(tmp_db_path)

        repo = EggRepository(tmp_db_path)
        try:
            results = repo.get_size_breakdown(
                date(2026, 3, 18),
                date(2026, 3, 20),
            )
        finally:
            repo.close()

        assert results == {}
