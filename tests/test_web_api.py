"""Tests for web API: repository-backed dashboard, history, and collection."""

import sqlite3
from datetime import date, datetime, timezone

import pytest

from egg_counter.db import EggDatabaseLogger
from egg_counter.repository import EggRepository


def _initialize_db(db_path: str) -> None:
    """Initialize database schema using EggDatabaseLogger."""
    logger = EggDatabaseLogger(db_path)
    logger.close()


def _insert_egg(
    conn: sqlite3.Connection,
    detected_date: str,
    size: str,
    timestamp: str | None = None,
    track_id: int = 1,
) -> None:
    """Insert a test egg event."""
    ts = timestamp or f"{detected_date}T12:00:00+00:00"
    conn.execute(
        """
        INSERT INTO egg_events (
            timestamp, detected_date, track_id, size, confidence,
            bbox_x1, bbox_y1, bbox_x2, bbox_y2,
            size_method, raw_measurement_mm, frame_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ts, detected_date, track_id, size, 0.9, 0.0, 0.0, 0.0, 0.0,
         "bbox_ratio", 50.0, 1),
    )


def _insert_collection(
    conn: sqlite3.Connection,
    collected_date: str,
    count: int,
    timestamp: str | None = None,
) -> None:
    """Insert a test collection event."""
    ts = timestamp or f"{collected_date}T14:00:00+00:00"
    conn.execute(
        """
        INSERT INTO collection_events (timestamp, collected_date, count)
        VALUES (?, ?, ?)
        """,
        (ts, collected_date, count),
    )


class TestDashboardSnapshot:
    """Tests for EggRepository.get_dashboard_snapshot."""

    def test_dashboard_snapshot(self, tmp_db_path):
        """Snapshot returns today's totals, all-time stats, and production series."""
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            _insert_egg(conn, "2026-03-20", "large")
            _insert_egg(conn, "2026-03-20", "medium")
            _insert_egg(conn, "2026-03-20", "large")
            _insert_egg(conn, "2026-03-21", "jumbo")
            _insert_egg(conn, "2026-03-23", "large",
                        timestamp="2026-03-23T10:00:00+00:00")
            _insert_egg(conn, "2026-03-23", "small",
                        timestamp="2026-03-23T11:00:00+00:00")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            snap = repo.get_dashboard_snapshot(date(2026, 3, 23), "weekly")
        finally:
            repo.close()

        assert snap["date"] == "2026-03-23"
        assert snap["today_total"] == 2
        assert snap["today_by_size"]["large"] == 1
        assert snap["today_by_size"]["small"] == 1
        assert snap["all_time_total"] == 6
        assert snap["period"] == "weekly"
        assert "best_day" in snap
        assert "top_size" in snap
        assert "production_series" in snap
        assert "size_breakdown" in snap

    def test_dashboard_snapshot_excludes_pre_collection_eggs(self, tmp_db_path):
        """After a same-day collection, only post-collection eggs appear."""
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            # Pre-collection eggs
            _insert_egg(conn, "2026-03-23", "large",
                        timestamp="2026-03-23T08:00:00+00:00")
            _insert_egg(conn, "2026-03-23", "medium",
                        timestamp="2026-03-23T09:00:00+00:00")
            # Collection at 10:00
            _insert_collection(conn, "2026-03-23", 2,
                               timestamp="2026-03-23T10:00:00+00:00")
            # Post-collection egg
            _insert_egg(conn, "2026-03-23", "jumbo",
                        timestamp="2026-03-23T11:00:00+00:00")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            snap = repo.get_dashboard_snapshot(date(2026, 3, 23), "weekly")
        finally:
            repo.close()

        assert snap["today_total"] == 1
        assert snap["today_by_size"] == {"jumbo": 1}


class TestHistoryRecords:
    """Tests for EggRepository.get_history_records."""

    def test_history_records_default_newest_first(self, tmp_db_path):
        """History records return newest first by default."""
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            _insert_egg(conn, "2026-03-18", "large",
                        timestamp="2026-03-18T12:00:00+00:00")
            _insert_egg(conn, "2026-03-20", "medium",
                        timestamp="2026-03-20T12:00:00+00:00")
            _insert_egg(conn, "2026-03-19", "small",
                        timestamp="2026-03-19T12:00:00+00:00")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            records = repo.get_history_records()
        finally:
            repo.close()

        assert len(records) == 3
        # Newest first
        assert records[0]["detected_date"] == "2026-03-20"
        assert records[1]["detected_date"] == "2026-03-19"
        assert records[2]["detected_date"] == "2026-03-18"

    def test_history_records_filters_by_size_and_date_range(self, tmp_db_path):
        """History records can be filtered by size and date range."""
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            _insert_egg(conn, "2026-03-18", "large")
            _insert_egg(conn, "2026-03-19", "medium")
            _insert_egg(conn, "2026-03-19", "large")
            _insert_egg(conn, "2026-03-20", "large")
            _insert_egg(conn, "2026-03-21", "large")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            records = repo.get_history_records(
                start=date(2026, 3, 19),
                end=date(2026, 3, 20),
                size="large",
            )
        finally:
            repo.close()

        assert len(records) == 2
        for r in records:
            assert r["size"] == "large"


class TestAggregates:
    """Tests for best_day and top_size roll-ups."""

    def test_best_day_and_top_size_roll_up(self, tmp_db_path):
        """Best day and top size compute correctly from all data."""
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            _insert_egg(conn, "2026-03-18", "large")
            _insert_egg(conn, "2026-03-18", "large")
            _insert_egg(conn, "2026-03-18", "large")
            _insert_egg(conn, "2026-03-19", "medium")
            _insert_egg(conn, "2026-03-20", "medium")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            best = repo.get_best_day()
            top = repo.get_top_size()
        finally:
            repo.close()

        assert best["date"] == "2026-03-18"
        assert best["total"] == 3
        assert top["size"] == "large"
        assert top["total"] == 3
