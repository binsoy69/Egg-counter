"""SQLite-backed event logger for egg detections and collections."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class EggDatabaseLogger:
    """Persist egg events in SQLite with the EggEventLogger interface."""

    def __init__(self, db_path: str = "data/eggs.db") -> None:
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        if db_file.exists() and not os.access(db_file, os.W_OK):
            raise PermissionError(f"Database not writable: {db_path}")
        if not db_file.exists() and not os.access(db_file.parent, os.W_OK):
            raise PermissionError(f"Database not writable: {db_path}")

        self.conn = sqlite3.connect(db_path)
        self._configure_pragmas()
        self._create_tables()
        self.egg_count = self._get_today_count()

    def _configure_pragmas(self) -> None:
        """Configure SQLite for durability on SD-card storage."""
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA foreign_keys=ON")

    def _create_tables(self) -> None:
        """Create required tables and indexes for egg persistence."""
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

            CREATE INDEX IF NOT EXISTS idx_egg_events_size
            ON egg_events(detected_date, size);

            CREATE INDEX IF NOT EXISTS idx_collection_date
            ON collection_events(collected_date);
            """
        )
        self.conn.execute("PRAGMA user_version = 1")

    def _get_today_count(self) -> int:
        """Restore the running count after the most recent same-day collection."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        latest_collection = self.conn.execute(
            "SELECT MAX(timestamp) FROM collection_events WHERE collected_date = ?",
            (today,),
        ).fetchone()[0]

        if latest_collection is None:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM egg_events WHERE detected_date = ?",
                (today,),
            ).fetchone()
            return row[0]

        row = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM egg_events
            WHERE detected_date = ? AND timestamp > ?
            """,
            (today, latest_collection),
        ).fetchone()
        return row[0]

    def log_egg_detected(
        self,
        track_id: int,
        size: str,
        confidence: float,
        bbox: list,
        size_method: str,
        raw_measurement_mm: float,
        frame_number: int,
    ) -> dict:
        """Persist an egg detection event and return the event payload."""
        self.egg_count += 1

        ts = datetime.now(timezone.utc).isoformat()
        detected_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rounded_confidence = round(confidence, 3)
        rounded_measurement = round(raw_measurement_mm, 1)

        with self.conn:
            self.conn.execute(
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
                    ts,
                    detected_date,
                    track_id,
                    size,
                    rounded_confidence,
                    bbox[0],
                    bbox[1],
                    bbox[2],
                    bbox[3],
                    size_method,
                    rounded_measurement,
                    frame_number,
                ),
            )

        event = {
            "type": "egg_detected",
            "timestamp": ts,
            "track_id": track_id,
            "size": size,
            "confidence": rounded_confidence,
            "bbox": bbox,
            "size_method": size_method,
            "raw_measurement_mm": rounded_measurement,
            "frame_number": frame_number,
        }
        print(f"New egg #{self.egg_count} -- {size}")
        return event

    def log_eggs_collected(self, count: int) -> dict:
        """Persist a collection event and reset the running count."""
        ts = datetime.now(timezone.utc).isoformat()
        collected_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        with self.conn:
            self.conn.execute(
                """
                INSERT INTO collection_events (
                    timestamp,
                    collected_date,
                    count
                )
                VALUES (?, ?, ?)
                """,
                (ts, collected_date, count),
            )

        self.egg_count = 0
        print(f"Eggs collected: {count}")
        return {"type": "eggs_collected", "timestamp": ts, "count": count}

    def close(self) -> None:
        """Close the SQLite connection."""
        self.conn.close()
