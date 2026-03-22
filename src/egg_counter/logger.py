"""JSONL event logger with daily rotation for egg detection events."""

import json
from datetime import datetime, timezone
from pathlib import Path


class EggEventLogger:
    """Logs egg detection events to daily JSONL files.

    Each day's events are written to a separate file named
    ``eggs-YYYY-MM-DD.jsonl`` inside the configured log directory.
    """

    def __init__(self, log_dir: str = "logs") -> None:
        self.log_dir = log_dir
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        self.egg_count = 0

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
        """Log a single egg detection event.

        Returns:
            The event dict that was written.
        """
        self.egg_count += 1

        event = {
            "type": "egg_detected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "track_id": track_id,
            "size": size,
            "confidence": round(confidence, 3),
            "bbox": bbox,
            "size_method": size_method,
            "raw_measurement_mm": round(raw_measurement_mm, 1),
            "frame_number": frame_number,
        }

        self._write_event(event)
        print(f"New egg #{self.egg_count} -- {size}")
        return event

    def log_eggs_collected(self, count: int) -> dict:
        """Log an eggs-collected event and reset the running count.

        Returns:
            The event dict that was written.
        """
        event = {
            "type": "eggs_collected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": count,
        }

        self._write_event(event)
        self.egg_count = 0
        print(f"Eggs collected: {count}")
        return event

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_event(self, event: dict) -> None:
        """Append *event* as a single JSON line to today's log file."""
        log_path = self._get_log_path()
        with open(log_path, "a") as f:
            f.write(json.dumps(event) + "\n")

    def _get_log_path(self) -> Path:
        """Return the path to today's JSONL log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        return Path(self.log_dir) / f"eggs-{today}.jsonl"
