"""Tests for egg tracking, de-duplication, stability timer, and restart handling."""

import pytest

from src.egg_counter.tracker import EggTracker


class TestNewTrackNotImmediatelyCounted:
    """A new track ID should not be counted on first detection."""

    def test_new_track_not_immediately_counted(self) -> None:
        tracker = EggTracker(stability_seconds=3.0)
        events = tracker.process_detections(
            track_ids=[1],
            boxes=[[100, 50, 200, 150]],
            in_zone_flags=[True],
            timestamp=0.0,
        )
        assert events == []
        assert tracker.egg_count == 0


class TestStabilityTimer:
    """Track must remain in-zone for stability_seconds before counting."""

    def test_track_counted_after_stability(self) -> None:
        tracker = EggTracker(stability_seconds=3.0)
        box = [100, 50, 200, 150]

        # Frame at t=0: first seen
        tracker.process_detections([1], [box], [True], 0.0)
        assert tracker.egg_count == 0

        # Frame at t=1: still pending
        tracker.process_detections([1], [box], [True], 1.0)
        assert tracker.egg_count == 0

        # Frame at t=2: still pending
        tracker.process_detections([1], [box], [True], 2.0)
        assert tracker.egg_count == 0

        # Frame at t=3.0: exactly at threshold -- not yet (needs >= 3.0 elapsed)
        events = tracker.process_detections([1], [box], [True], 3.0)
        assert len(events) == 1
        assert events[0]["action"] == "count"
        assert events[0]["track_id"] == 1
        assert tracker.egg_count == 1

    def test_track_leaves_zone_resets_timer(self) -> None:
        tracker = EggTracker(stability_seconds=3.0)
        box = [100, 50, 200, 150]

        # Enter zone at t=0
        tracker.process_detections([1], [box], [True], 0.0)

        # Leave zone at t=2 (before stability)
        tracker.process_detections([1], [box], [False], 2.0)

        # Re-enter zone at t=5 -- timer should restart
        tracker.process_detections([1], [box], [True], 5.0)

        # At t=7 (only 2s since re-entry) -- should NOT be counted
        events = tracker.process_detections([1], [box], [True], 7.0)
        assert events == []
        assert tracker.egg_count == 0

        # At t=8 (3s since re-entry at t=5) -- NOW counted
        events = tracker.process_detections([1], [box], [True], 8.0)
        assert len(events) == 1
        assert tracker.egg_count == 1


class TestDeduplication:
    """A counted track ID must never be counted again."""

    def test_track_counted_exactly_once(self) -> None:
        tracker = EggTracker(stability_seconds=3.0)
        box = [100, 50, 200, 150]

        # Count the egg (t=0 to t=3)
        tracker.process_detections([1], [box], [True], 0.0)
        tracker.process_detections([1], [box], [True], 3.0)
        assert tracker.egg_count == 1

        # Continue detecting same track -- no new events
        events = tracker.process_detections([1], [box], [True], 4.0)
        assert events == []
        assert tracker.egg_count == 1

        events = tracker.process_detections([1], [box], [True], 10.0)
        assert events == []
        assert tracker.egg_count == 1


class TestMultipleEggs:
    """Multiple eggs get independent track IDs and timers."""

    def test_multiple_eggs_independent(self) -> None:
        tracker = EggTracker(stability_seconds=3.0)
        box1 = [100, 50, 200, 150]
        box2 = [300, 50, 400, 150]

        # Both enter at t=0
        tracker.process_detections([1, 2], [box1, box2], [True, True], 0.0)
        assert tracker.egg_count == 0

        # Egg 1 leaves at t=1, egg 2 stays
        tracker.process_detections([1, 2], [box1, box2], [False, True], 1.0)

        # At t=3: egg 2 should be counted (3s in zone), egg 1 should not (timer reset)
        events = tracker.process_detections([1, 2], [box1, box2], [False, True], 3.0)
        assert len(events) == 1
        assert events[0]["track_id"] == 2
        assert tracker.egg_count == 1


class TestOcclusion:
    """Occlusion (hen sitting on egg) should not decrease count."""

    def test_occlusion_preserves_count(self) -> None:
        tracker = EggTracker(stability_seconds=3.0)
        box = [100, 50, 200, 150]

        # Count the egg
        tracker.process_detections([1], [box], [True], 0.0)
        tracker.process_detections([1], [box], [True], 3.0)
        assert tracker.egg_count == 1

        # Egg disappears (occluded by hen) -- no detections at all
        # But we still pass empty lists (no tracks visible)
        # Count must NOT decrease
        tracker.process_detections([], [], [], 5.0)
        assert tracker.egg_count == 1

        # Egg reappears
        tracker.process_detections([1], [box], [True], 8.0)
        assert tracker.egg_count == 1  # Still 1, not re-counted


class TestRestart:
    """On restart, visible eggs are marked as already-counted."""

    def test_restart_marks_existing_as_counted(self) -> None:
        tracker = EggTracker(stability_seconds=3.0)

        # Simulate restart: 2 eggs already visible
        tracker.initialize_from_existing([10, 20])

        assert tracker.egg_count == 2

        # These eggs should NOT trigger new count events
        box = [100, 50, 200, 150]
        events = tracker.process_detections(
            [10, 20],
            [box, box],
            [True, True],
            0.0,
        )
        assert events == []
        assert tracker.egg_count == 2


class TestCollection:
    """When all tracked eggs leave the zone, emit eggs_collected event."""

    def test_all_eggs_leave_triggers_collection(self) -> None:
        tracker = EggTracker(stability_seconds=3.0, collection_timeout=5.0)
        box = [100, 50, 200, 150]

        # Count an egg
        tracker.process_detections([1], [box], [True], 0.0)
        tracker.process_detections([1], [box], [True], 3.0)
        assert tracker.egg_count == 1

        # All eggs disappear (farmer collected them) -- wait beyond collection timeout
        # Last detection was at t=3.0, so t=8.0 is 5s later (>= collection_timeout)
        events = tracker.process_detections([], [], [], 8.0)
        collected_events = [e for e in events if e["action"] == "collected"]
        assert len(collected_events) == 1
        assert collected_events[0]["count"] == 1

    def test_counted_ids_pruned_after_collection(self) -> None:
        tracker = EggTracker(stability_seconds=3.0, collection_timeout=5.0)
        box = [100, 50, 200, 150]

        # Count an egg
        tracker.process_detections([1], [box], [True], 0.0)
        tracker.process_detections([1], [box], [True], 3.0)
        assert tracker.egg_count == 1

        # Collection event (last detection at t=3, empty at t=8 = 5s gap)
        tracker.process_detections([], [], [], 8.0)
        assert tracker.egg_count == 0

        # New egg should start fresh
        events = tracker.process_detections([2], [box], [True], 15.0)
        assert events == []  # Pending (stability timer)
        events = tracker.process_detections([2], [box], [True], 18.0)
        assert len(events) == 1
        assert events[0]["track_id"] == 2
        assert tracker.egg_count == 1
