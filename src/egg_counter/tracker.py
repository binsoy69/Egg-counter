"""Egg tracking engine with de-duplication, stability timer, and restart handling.

Manages ByteTrack-assigned track IDs to ensure each physical egg is counted
exactly once. Implements:
- Stability timer: egg must be in-zone for N seconds before counting (D-04)
- De-duplication: counted track IDs are never re-counted (D-02)
- Occlusion handling: count preserved when eggs disappear temporarily (D-06)
- Restart safety: existing eggs marked as counted without new events (D-08)
- Collection detection: all eggs leaving triggers collection event (D-09)
"""

from __future__ import annotations


class EggTracker:
    """Tracks eggs in the nest box zone and manages counting logic.

    Each egg is identified by a ByteTrack track ID. The tracker ensures
    each physical egg is counted exactly once after remaining in the zone
    for the required stability period.
    """

    def __init__(
        self,
        stability_seconds: float = 3.0,
        collection_timeout: float = 5.0,
    ) -> None:
        """Initialize the tracker.

        Args:
            stability_seconds: Seconds an egg must remain in-zone before counting.
            collection_timeout: Seconds with no detections before triggering
                collection event. Prevents brief occlusions from clearing counts.
        """
        self.stability_seconds = stability_seconds
        self.collection_timeout = collection_timeout
        self.counted_ids: set[int] = set()
        self.pending_tracks: dict[int, float] = {}  # track_id -> first_seen_timestamp
        self.active_tracks: set[int] = set()
        self.had_eggs: bool = False
        self._last_detection_timestamp: float | None = None

    @property
    def egg_count(self) -> int:
        """Number of eggs that have been counted."""
        return len(self.counted_ids)

    def process_detections(
        self,
        track_ids: list[int],
        boxes: list,
        in_zone_flags: list[bool],
        timestamp: float,
    ) -> list[dict]:
        """Process a frame's detections and return any new events.

        Args:
            track_ids: List of ByteTrack track IDs for detected eggs.
            boxes: Parallel list of bounding boxes in [x1, y1, x2, y2] format.
            in_zone_flags: Parallel list of booleans indicating zone containment.
            timestamp: Current frame timestamp in seconds.

        Returns:
            List of event dicts. Possible actions:
            - {"action": "count", "track_id": int, "bbox": list}
            - {"action": "collected", "count": int}
        """
        events: list[dict] = []
        current_in_zone_ids: set[int] = set()

        for track_id, box, in_zone in zip(track_ids, boxes, in_zone_flags):
            if in_zone:
                current_in_zone_ids.add(track_id)

                if track_id not in self.counted_ids:
                    if track_id not in self.pending_tracks:
                        # First time seeing this track in zone
                        self.pending_tracks[track_id] = timestamp
                    elif timestamp - self.pending_tracks[track_id] >= self.stability_seconds:
                        # Stability period elapsed -- count this egg
                        self.counted_ids.add(track_id)
                        del self.pending_tracks[track_id]
                        events.append({
                            "action": "count",
                            "track_id": track_id,
                            "bbox": box,
                        })
            else:
                # Track is outside zone -- reset stability timer if pending
                if track_id in self.pending_tracks:
                    del self.pending_tracks[track_id]

        # Update active tracks: in-zone tracks plus counted (for occlusion D-06)
        self.active_tracks = current_in_zone_ids | self.counted_ids

        # Track last time we saw any detection (for collection timeout)
        if len(track_ids) > 0:
            self._last_detection_timestamp = timestamp

        # Check for collection event (D-09):
        # All eggs have left when no tracks are detected for collection_timeout
        # seconds. This prevents brief occlusions from triggering collection.
        if (
            self.had_eggs
            and len(current_in_zone_ids) == 0
            and len(track_ids) == 0
            and len(self.counted_ids) > 0
            and self._last_detection_timestamp is not None
            and (timestamp - self._last_detection_timestamp) >= self.collection_timeout
        ):
            events.append({
                "action": "collected",
                "count": len(self.counted_ids),
            })
            self.counted_ids.clear()
            self.pending_tracks.clear()
            self.active_tracks.clear()
            self.had_eggs = False
            self._last_detection_timestamp = None

        # Track whether we've seen eggs (for collection detection)
        if current_in_zone_ids:
            self.had_eggs = True

        return events

    def initialize_from_existing(self, track_ids: list[int]) -> None:
        """Mark existing visible eggs as already counted on restart.

        Per D-08: On system restart, eggs already in the zone should be
        added to the counted set without emitting count events.

        Args:
            track_ids: List of track IDs for eggs currently visible.
        """
        for track_id in track_ids:
            self.counted_ids.add(track_id)
        if track_ids:
            self.had_eggs = True
