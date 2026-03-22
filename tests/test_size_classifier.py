"""Tests for egg size classification via bounding box ratio method."""

import pytest

from src.egg_counter.size_classifier import (
    SIZE_THRESHOLDS,
    SizeClassifier,
    classify_by_ratio,
    classify_size_from_mm,
)


# --- Direct mm classification tests ---


@pytest.mark.parametrize(
    "height_mm, expected_size",
    [
        (65.0, "jumbo"),
        (59.0, "large"),
        (53.0, "medium"),
        (45.0, "small"),
    ],
    ids=["jumbo", "large", "medium", "small"],
)
def test_classify_basic_sizes(height_mm: float, expected_size: str) -> None:
    """Standard heights map to correct size categories."""
    assert classify_size_from_mm(height_mm) == expected_size


# --- Boundary tests ---


@pytest.mark.parametrize(
    "height_mm, expected_size",
    [
        (63.1, "jumbo"),
        (56.1, "large"),
        (50.1, "medium"),
        (50.0, "small"),
    ],
    ids=["boundary_jumbo", "boundary_large", "boundary_medium", "boundary_small"],
)
def test_classify_boundary(height_mm: float, expected_size: str) -> None:
    """Boundary values classified correctly (thresholds are exclusive >)."""
    assert classify_size_from_mm(height_mm) == expected_size


# --- Ratio conversion test ---


def test_ratio_conversion() -> None:
    """Given zone_width_px=400, nest_box_width_mm=300, egg height 80px -> 60mm -> large."""
    zone_rect = {"x1": 100, "y1": 50, "x2": 500, "y2": 400}  # width = 400px
    egg_bbox = [200, 100, 250, 180]  # height = 80px
    size, mm = classify_by_ratio(egg_bbox, zone_rect, nest_box_width_mm=300.0)
    assert size == "large"
    assert mm == 60.0


# --- Return type test ---


def test_classify_returns_tuple() -> None:
    """classify_by_ratio returns (size_str, raw_mm) tuple."""
    zone_rect = {"x1": 0, "y1": 0, "x2": 400, "y2": 300}
    egg_bbox = [100, 50, 150, 130]  # height = 80px
    result = classify_by_ratio(egg_bbox, zone_rect, nest_box_width_mm=300.0)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], float)


# --- SizeClassifier class tests ---


def test_size_classifier_class() -> None:
    """SizeClassifier wraps classify_by_ratio using zone config."""
    zone_config = {
        "x1": 0,
        "y1": 0,
        "x2": 400,
        "y2": 300,
        "nest_box_width_mm": 300.0,
    }
    classifier = SizeClassifier(zone_config)
    egg_bbox = [100, 50, 150, 180]  # height = 130px -> 130/(400/300) = 97.5mm -> jumbo
    size, mm = classifier.classify(egg_bbox)
    assert size == "jumbo"
    assert mm == 97.5


def test_size_classifier_default_nest_box_width() -> None:
    """SizeClassifier defaults to 300mm nest box width if not in config."""
    zone_config = {"x1": 0, "y1": 0, "x2": 300, "y2": 200}
    classifier = SizeClassifier(zone_config)
    # zone width = 300px, default nest_box_width_mm = 300
    # px_per_mm = 1.0, egg height 55px -> 55mm -> medium
    egg_bbox = [50, 50, 100, 105]  # height = 55px
    size, mm = classifier.classify(egg_bbox)
    assert size == "medium"
    assert mm == 55.0


# --- Thresholds constant test ---


def test_size_thresholds_defined() -> None:
    """SIZE_THRESHOLDS contains correct threshold values."""
    assert SIZE_THRESHOLDS["jumbo"] == 63.0
    assert SIZE_THRESHOLDS["large"] == 56.0
    assert SIZE_THRESHOLDS["medium"] == 50.0
