"""Unit tests for EggDetector with mocked YOLO model."""

from unittest.mock import MagicMock, patch

import pytest


def _make_mock_boxes(track_ids=None, xyxy=None, conf=None, cls=None):
    """Create a mock ultralytics boxes object with chained tensor methods."""
    boxes = MagicMock()
    boxes.__len__ = MagicMock(return_value=len(xyxy) if xyxy else 0)

    if track_ids is not None:
        id_tensor = MagicMock()
        id_tensor.int.return_value.cpu.return_value.tolist.return_value = track_ids
        boxes.id = id_tensor
    else:
        boxes.id = None

    if xyxy is not None:
        xyxy_tensor = MagicMock()
        xyxy_tensor.cpu.return_value.numpy.return_value.tolist.return_value = xyxy
        boxes.xyxy = xyxy_tensor
    else:
        boxes.xyxy = MagicMock()
        boxes.xyxy.cpu.return_value.numpy.return_value.tolist.return_value = []

    if conf is not None:
        conf_tensor = MagicMock()
        conf_tensor.cpu.return_value.tolist.return_value = conf
        boxes.conf = conf_tensor
    else:
        boxes.conf = MagicMock()
        boxes.conf.cpu.return_value.tolist.return_value = []

    if cls is not None:
        cls_tensor = MagicMock()
        cls_tensor.int.return_value.cpu.return_value.tolist.return_value = cls
        boxes.cls = cls_tensor
    else:
        boxes.cls = MagicMock()
        boxes.cls.int.return_value.cpu.return_value.tolist.return_value = []

    return boxes


def _make_mock_result(boxes):
    """Create a mock ultralytics Result object."""
    result = MagicMock()
    result.boxes = boxes
    return result


@patch("egg_counter.detector.YOLO")
def test_egg_detector_initializes(mock_yolo_cls):
    """EggDetector creates a YOLO model with correct attributes."""
    from egg_counter.detector import EggDetector

    detector = EggDetector("best.pt")

    mock_yolo_cls.assert_called_once_with("best.pt")
    assert detector.tracker_config == "config/bytetrack_eggs.yaml"
    assert detector.confidence == 0.5
    assert detector.frame_count == 0


@patch("egg_counter.detector.YOLO")
def test_detect_and_track_returns_expected_shape(mock_yolo_cls):
    """detect_and_track returns dict with all required keys."""
    from egg_counter.detector import EggDetector

    mock_model = MagicMock()
    mock_yolo_cls.return_value = mock_model

    boxes = _make_mock_boxes(
        track_ids=[1, 2],
        xyxy=[[10, 20, 50, 60], [100, 200, 150, 260]],
        conf=[0.85, 0.72],
        cls=[0, 0],
    )
    mock_model.track.return_value = [_make_mock_result(boxes)]

    detector = EggDetector("best.pt")
    result = detector.detect_and_track(MagicMock())

    assert isinstance(result["track_ids"], list)
    assert isinstance(result["boxes"], list)
    assert isinstance(result["confidences"], list)
    assert isinstance(result["classes"], list)
    assert isinstance(result["frame_number"], int)
    assert result["track_ids"] == [1, 2]
    assert len(result["boxes"]) == 2
    assert result["frame_number"] == 1


@patch("egg_counter.detector.YOLO")
def test_detect_and_track_no_detections(mock_yolo_cls):
    """detect_and_track returns empty lists when no detections."""
    from egg_counter.detector import EggDetector

    mock_model = MagicMock()
    mock_yolo_cls.return_value = mock_model

    boxes = _make_mock_boxes()  # No detections
    mock_model.track.return_value = [_make_mock_result(boxes)]

    detector = EggDetector("best.pt")
    result = detector.detect_and_track(MagicMock())

    assert result["track_ids"] == []
    assert result["boxes"] == []
    assert result["confidences"] == []
    assert result["classes"] == []
    assert result["frame_number"] == 1


@patch("egg_counter.detector.YOLO")
def test_detect_and_track_increments_frame_count(mock_yolo_cls):
    """Frame count increments with each detect_and_track call."""
    from egg_counter.detector import EggDetector

    mock_model = MagicMock()
    mock_yolo_cls.return_value = mock_model

    boxes = _make_mock_boxes()
    mock_model.track.return_value = [_make_mock_result(boxes)]

    detector = EggDetector("best.pt")
    r1 = detector.detect_and_track(MagicMock())
    r2 = detector.detect_and_track(MagicMock())

    assert r1["frame_number"] == 1
    assert r2["frame_number"] == 2
    assert detector.frame_count == 2


@patch("egg_counter.detector.YOLO")
def test_detect_once_uses_predict_not_track(mock_yolo_cls):
    """detect_once calls model.predict, not model.track."""
    from egg_counter.detector import EggDetector

    mock_model = MagicMock()
    mock_yolo_cls.return_value = mock_model

    boxes = _make_mock_boxes(
        track_ids=[1],
        xyxy=[[10, 20, 50, 60]],
        conf=[0.9],
        cls=[0],
    )
    mock_model.predict.return_value = [_make_mock_result(boxes)]

    detector = EggDetector("best.pt")
    result = detector.detect_once(MagicMock())

    mock_model.predict.assert_called_once()
    mock_model.track.assert_not_called()
    assert result["frame_number"] == 1


@patch("egg_counter.detector.YOLO")
def test_detect_and_track_passes_tracker_config(mock_yolo_cls):
    """detect_and_track passes tracker config and persist=True to model.track."""
    from egg_counter.detector import EggDetector

    mock_model = MagicMock()
    mock_yolo_cls.return_value = mock_model

    boxes = _make_mock_boxes()
    mock_model.track.return_value = [_make_mock_result(boxes)]

    detector = EggDetector("best.pt", tracker_config="custom_tracker.yaml")
    detector.detect_and_track(MagicMock())

    call_kwargs = mock_model.track.call_args
    assert call_kwargs.kwargs.get("persist") is True or call_kwargs[1].get("persist") is True
    assert call_kwargs.kwargs.get("tracker") == "custom_tracker.yaml" or call_kwargs[1].get("tracker") == "custom_tracker.yaml"
    assert call_kwargs.kwargs.get("verbose") is False or call_kwargs[1].get("verbose") is False
