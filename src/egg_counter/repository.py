"""Read-only query helpers for persisted egg data."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta


class EggRepository:
    """Expose dashboard-friendly queries over the egg event database."""

    def __init__(self, db_path: str = "data/eggs.db") -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist (handles pre-Phase-2 databases)."""
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS egg_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                detected_date TEXT NOT NULL,
                track_id INTEGER NOT NULL,
                size TEXT NOT NULL,
                confidence REAL NOT NULL,
                bbox_x1 REAL NOT NULL,
                bbox_y1 REAL NOT NULL,
                bbox_x2 REAL NOT NULL,
                bbox_y2 REAL NOT NULL,
                size_method TEXT NOT NULL,
                raw_measurement_mm REAL NOT NULL,
                frame_number INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS collection_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                collected_date TEXT NOT NULL,
                count INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_egg_events_date
            ON egg_events(detected_date);
            CREATE INDEX IF NOT EXISTS idx_collection_date
            ON collection_events(collected_date);
            """
        )

    def get_daily_summary(self, target_date: date) -> dict:
        """Return the total eggs and size breakdown for one day."""
        rows = self.conn.execute(
            """
            SELECT size, COUNT(*) AS count
            FROM egg_events
            WHERE detected_date = ?
            GROUP BY size
            """,
            (target_date.isoformat(),),
        ).fetchall()
        by_size = {row["size"]: row["count"] for row in rows}
        return {
            "date": target_date.isoformat(),
            "total": sum(by_size.values()),
            "by_size": by_size,
        }

    def get_eggs_by_date_range(self, start: date, end: date) -> list[dict]:
        """Return daily totals across an inclusive date range."""
        rows = self.conn.execute(
            """
            SELECT detected_date, COUNT(*) AS total
            FROM egg_events
            WHERE detected_date BETWEEN ? AND ?
            GROUP BY detected_date
            ORDER BY detected_date
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [
            {"date": row["detected_date"], "total": row["total"]}
            for row in rows
        ]

    def get_size_breakdown(self, start: date, end: date) -> dict:
        """Return aggregate size counts across an inclusive date range."""
        rows = self.conn.execute(
            """
            SELECT size, COUNT(*) AS count
            FROM egg_events
            WHERE detected_date BETWEEN ? AND ?
            GROUP BY size
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return {row["size"]: row["count"] for row in rows}

    def get_history_records(
        self,
        start: date | None = None,
        end: date | None = None,
        size: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        """Return individual egg events, newest first, with optional filters."""
        clauses: list[str] = []
        params: list[str | int] = []

        if start is not None:
            clauses.append("detected_date >= ?")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("detected_date <= ?")
            params.append(end.isoformat())
        if size is not None:
            clauses.append("size = ?")
            params.append(size)

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        rows = self.conn.execute(
            f"""
            SELECT id, timestamp, detected_date, track_id, size, confidence,
                   bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                   size_method, raw_measurement_mm, frame_number
            FROM egg_events
            {where}
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_best_day(self) -> dict:
        """Return the date with the highest egg count."""
        row = self.conn.execute(
            """
            SELECT detected_date, COUNT(*) AS total
            FROM egg_events
            GROUP BY detected_date
            ORDER BY total DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return {"date": None, "total": 0}
        return {"date": row["detected_date"], "total": row["total"]}

    def get_all_time_totals(self) -> dict:
        """Return all-time aggregate counts."""
        row = self.conn.execute(
            "SELECT COUNT(*) AS total FROM egg_events"
        ).fetchone()
        return {"total": row["total"]}

    def get_top_size(self) -> dict:
        """Return the size classification with the highest count."""
        row = self.conn.execute(
            """
            SELECT size, COUNT(*) AS total
            FROM egg_events
            GROUP BY size
            ORDER BY total DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return {"size": None, "total": 0}
        return {"size": row["size"], "total": row["total"]}

    def get_dashboard_snapshot(self, target_date: date, period: str) -> dict:
        """Build a complete dashboard snapshot for the given date.

        The running count reflects only eggs detected after the most recent
        same-day collection event (if any).
        """
        today_iso = target_date.isoformat()

        # Find latest same-day collection timestamp
        latest_collection = self.conn.execute(
            "SELECT MAX(timestamp) FROM collection_events WHERE collected_date = ?",
            (today_iso,),
        ).fetchone()[0]

        # Count today's eggs (post-collection only if collection exists)
        if latest_collection is not None:
            today_rows = self.conn.execute(
                """
                SELECT size, COUNT(*) AS count
                FROM egg_events
                WHERE detected_date = ? AND timestamp > ?
                GROUP BY size
                """,
                (today_iso, latest_collection),
            ).fetchall()
        else:
            today_rows = self.conn.execute(
                """
                SELECT size, COUNT(*) AS count
                FROM egg_events
                WHERE detected_date = ?
                GROUP BY size
                """,
                (today_iso,),
            ).fetchall()

        today_by_size = {
            s: 0 for s in ("small", "medium", "large", "jumbo")
        }
        for row in today_rows:
            today_by_size[row["size"]] = row["count"]
        # Remove zero-valued sizes for cleaner output
        today_by_size = {k: v for k, v in today_by_size.items() if v > 0}
        today_total = sum(today_by_size.values())

        # Period range
        if period == "monthly":
            range_start = target_date.replace(day=1)
        elif period == "yearly":
            range_start = target_date.replace(month=1, day=1)
        else:  # weekly (default)
            range_start = target_date - timedelta(days=6)

        production_series = self.get_eggs_by_date_range(range_start, target_date)
        size_breakdown_raw = self.get_size_breakdown(range_start, target_date)
        size_breakdown = {
            s: size_breakdown_raw.get(s, 0)
            for s in ("small", "medium", "large", "jumbo")
        }

        return {
            "date": today_iso,
            "today_total": today_total,
            "today_by_size": today_by_size,
            "all_time_total": self.get_all_time_totals()["total"],
            "best_day": self.get_best_day(),
            "top_size": self.get_top_size(),
            "period": period,
            "production_series": production_series,
            "size_breakdown": size_breakdown,
        }

    def close(self) -> None:
        """Close the SQLite connection."""
        self.conn.close()
