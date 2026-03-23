"""Read-only query helpers for persisted egg data."""

import sqlite3
from datetime import date


class EggRepository:
    """Expose dashboard-friendly queries over the egg event database."""

    def __init__(self, db_path: str = "data/eggs.db") -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

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

    def close(self) -> None:
        """Close the SQLite connection."""
        self.conn.close()
