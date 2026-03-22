"""Integration-style tests for EggCounterPipeline with mocked components."""

from unittest.mock import MagicMock, patch

import pytest

from egg_counter.pipeline import EggCounterPipeline


# Shared test fixtures

def _make_settings():
    """Return minimal settings dict for testing."""
    return {
        "stability_seconds": 3,
        "log_dir": "logs",
        "frame_rate": 3,
        "confidence_threshold": 0.5,
        "bytetrack_config": "config/bytetrack_eggs.yaml",
    }


def _make_zone_config():
    """Return a zone config dict for testing."""
    return {
        "x1": 100,
        "y1": 100,
        "x2": 500,
        "y2": 400,
        "nest_box_width_mm": 300.0,
    }


@patch("egg_counter.pipeline.EggDetector")
def test_process_frame_new_egg(mock_detector_cls):
    """After stability period, a new egg in zone is logged as egg_detected."""
    settings = _make_settings()
    settings["stability_seconds"] = 0  # Instant stability for test
    zone_config = _make_zone_config()
    pipeline = EggCounterPipeline(settings, zone_config)

    # Create mock detector
    mock_detector = MagicMock()
    pipeline.detector = mock_detector

    # Detection inside zone (center at 300, 250 -- within 100-500, 100-400)
    mock_detector.detect_and_track.return_value = {
        "track_ids": [1],
        "boxes": [[200, 200, 400, 300]],
        "confidences": [0.85],
        "classes": [0],
        "frame_number": 1,
    }

    # First call starts the stability timer
    events = pipeline.process_frame(MagicMock(), 0.0)
    assert len(events) == 0  # Pending on first sight

    # Second call at same time: stability_seconds=0 met (0.0 - 0.0 >= 0)
    mock_detector.detect_and_track.return_value["frame_number"] = 2
    events = pipeline.process_frame(MagicMock(), 0.0)
    assert len(events) == 1
    assert events[0]["type"] == "egg_detected"
    assert events[0]["track_id"] == 1
    assert events[0]["size"] in ("small", "medium", "large", "jumbo")
    assert events[0]["size_method"] == "bbox_ratio"


@patch("egg_counter.pipeline.EggDetector")
def test_process_frame_out_of_zone(mock_detector_cls):
    """Detections outside the zone do not generate events."""
    settings = _make_settings()
    settings["stability_seconds"] = 0
    zone_config = _make_zone_config()
    pipeline = EggCounterPipeline(settings, zone_config)

    mock_detector = MagicMock()
    pipeline.detector = mock_detector

    # Detection outside zone (center at 50, 50 -- outside 100-500, 100-400)
    mock_detector.detect_and_track.return_value = {
        "track_ids": [1],
        "boxes": [[10, 10, 90, 90]],
        "confidences": [0.85],
        "classes": [0],
        "frame_number": 1,
    }

    events = pipeline.process_frame(MagicMock(), 0.0)
    assert len(events) == 0


@patch("egg_counter.pipeline.EggDetector")
def test_pipeline_restart_initialization(mock_detector_cls):
    """On restart, existing eggs are marked as counted without emitting events."""
    settings = _make_settings()
    zone_config = _make_zone_config()
    pipeline = EggCounterPipeline(settings, zone_config)

    mock_detector = MagicMock()
    pipeline.detector = mock_detector

    # detect_once returns eggs already in zone
    mock_detector.detect_once.return_value = {
        "track_ids": [1, 2],
        "boxes": [[200, 200, 400, 300], [250, 250, 350, 350]],
        "confidences": [0.9, 0.85],
        "classes": [0, 0],
        "frame_number": 1,
    }

    pipeline._initialize_existing_eggs(MagicMock())

    # Verify eggs were marked as counted
    assert pipeline.tracker.egg_count == 2
    assert 1 in pipeline.tracker.counted_ids
    assert 2 in pipeline.tracker.counted_ids


@patch("egg_counter.pipeline.EggDetector")
def test_process_frame_stability_timing(mock_detector_cls):
    """Egg must remain in zone for stability_seconds before being counted."""
    settings = _make_settings()
    settings["stability_seconds"] = 3
    zone_config = _make_zone_config()
    pipeline = EggCounterPipeline(settings, zone_config)

    mock_detector = MagicMock()
    pipeline.detector = mock_detector

    detection_result = {
        "track_ids": [1],
        "boxes": [[200, 200, 400, 300]],
        "confidences": [0.85],
        "classes": [0],
        "frame_number": 1,
    }
    mock_detector.detect_and_track.return_value = detection_result

    # First frame at t=0: no event yet (stability not met)
    events = pipeline.process_frame(MagicMock(), 0.0)
    assert len(events) == 0

    # Frame at t=2: still no event
    detection_result["frame_number"] = 2
    events = pipeline.process_frame(MagicMock(), 2.0)
    assert len(events) == 0

    # Frame at t=3: stability reached, egg counted
    detection_result["frame_number"] = 3
    events = pipeline.process_frame(MagicMock(), 3.0)
    assert len(events) == 1
    assert events[0]["type"] == "egg_detected"
