"""Tests for preview module - frame annotation overlay logic."""

import numpy as np
import pytest

from egg_counter.preview import draw_detections
from egg_counter.size_classifier import SizeClassifier


@pytest.fixture
def blank_frame():
    """Create a blank 480x640 BGR frame."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def zone_config():
    """Zone config covering centre of frame."""
    return {"x1": 100, "y1": 100, "x2": 500, "y2": 400, "nest_box_width_mm": 300}


@pytest.fixture
def classifier(zone_config):
    return SizeClassifier(zone_config)


@pytest.fixture
def single_detection():
    """One detection result inside the zone."""
    return {
        "track_ids": [1],
        "boxes": [[200, 200, 300, 300]],
        "confidences": [0.85],
        "classes": [0],
        "frame_number": 1,
    }


@pytest.fixture
def empty_detection():
    """No detections."""
    return {
        "track_ids": [],
        "boxes": [],
        "confidences": [],
        "classes": [],
        "frame_number": 1,
    }


class TestDrawDetectionsEmpty:
    """draw_detections with empty detections should not crash."""

    def test_empty_returns_same_shape(self, blank_frame, empty_detection, zone_config, classifier):
        result = draw_detections(blank_frame, empty_detection, zone_config, classifier, egg_count=0)
        assert result.shape == blank_frame.shape

    def test_empty_frame_dtype_preserved(self, blank_frame, empty_detection, zone_config, classifier):
        result = draw_detections(blank_frame, empty_detection, zone_config, classifier, egg_count=0)
        assert result.dtype == np.uint8


class TestDrawDetectionsWithDetection:
    """draw_detections with one detection draws overlays."""

    def test_draws_label_text(self, blank_frame, single_detection, zone_config, classifier):
        original = blank_frame.copy()
        result = draw_detections(blank_frame, single_detection, zone_config, classifier, egg_count=1)
        # Bounding box region and label area should have changed pixels
        bbox_region_before = original[180:310, 190:310]
        bbox_region_after = result[180:310, 190:310]
        assert not np.array_equal(bbox_region_before, bbox_region_after), \
            "Expected pixels to change in the bounding box / label region"


class TestDrawDetectionsZone:
    """draw_detections draws zone rectangle."""

    def test_zone_rectangle_drawn(self, blank_frame, empty_detection, zone_config, classifier):
        original = blank_frame.copy()
        result = draw_detections(blank_frame, empty_detection, zone_config, classifier, egg_count=0)
        # Check green pixels at zone boundary (x1=100 column, between y1=100 and y2=400)
        zone_edge = result[100:400, 100]
        # Green channel should be 255 at zone boundary
        assert np.any(zone_edge[:, 1] == 255), \
            "Expected green pixels along zone left edge"


class TestDrawDetectionsEggCount:
    """draw_detections draws egg count overlay."""

    def test_egg_count_overlay(self, blank_frame, empty_detection, zone_config, classifier):
        original = blank_frame.copy()
        result = draw_detections(blank_frame, empty_detection, zone_config, classifier, egg_count=5)
        # Top-left corner region should have text drawn
        top_left_before = original[10:60, 10:250]
        top_left_after = result[10:60, 10:250]
        assert not np.array_equal(top_left_before, top_left_after), \
            "Expected egg count text in top-left corner"
