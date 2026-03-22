"""YOLO model wrapper for egg detection and ByteTrack tracking."""

from __future__ import annotations

from ultralytics import YOLO


class EggDetector:
    """Wraps an ultralytics YOLO model for egg detection with ByteTrack tracking.

    Provides two detection modes:
    - detect_and_track: persistent tracking across frames (main loop)
    - detect_once: single-frame prediction without tracking state (restart init)
    """

    def __init__(
        self,
        model_path: str,
        tracker_config: str = "config/bytetrack_eggs.yaml",
        confidence: float = 0.5,
    ) -> None:
        """Initialize the detector with a YOLO model.

        Args:
            model_path: Path to the YOLO model file (.pt or NCNN directory).
            tracker_config: Path to ByteTrack tracker configuration YAML.
            confidence: Minimum confidence threshold for detections.
        """
        self.model = YOLO(model_path)
        self.tracker_config = tracker_config
        self.confidence = confidence
        self.frame_count = 0

    def detect_and_track(self, frame) -> dict:
        """Run detection with persistent ByteTrack tracking.

        Args:
            frame: Input image frame (numpy array from cv2).

        Returns:
            Dict with keys: track_ids, boxes, confidences, classes, frame_number.
        """
        self.frame_count += 1

        results = self.model.track(
            frame,
            persist=True,
            tracker=self.tracker_config,
            conf=self.confidence,
            verbose=False,
        )

        return self._parse_results(results)

    def detect_once(self, frame) -> dict:
        """Run single-frame detection without tracking state.

        Used for restart initialization (D-08) to identify existing eggs
        without initializing persistent tracking state.

        Args:
            frame: Input image frame (numpy array from cv2).

        Returns:
            Dict with keys: track_ids, boxes, confidences, classes, frame_number.
        """
        self.frame_count += 1

        results = self.model.predict(
            frame,
            conf=self.confidence,
            verbose=False,
        )

        return self._parse_results(results)

    def reset_tracker(self) -> None:
        """Reset tracking state by forcing re-initialization on next track call."""
        self.model.predictor = None

    def _parse_results(self, results) -> dict:
        """Extract detection data from ultralytics results.

        Args:
            results: List of ultralytics Results objects.

        Returns:
            Dict with track_ids, boxes, confidences, classes, frame_number.
        """
        if results and results[0].boxes is not None and len(results[0].boxes) > 0:
            boxes_obj = results[0].boxes

            if boxes_obj.id is not None:
                track_ids = boxes_obj.id.int().cpu().tolist()
            else:
                track_ids = []

            boxes = boxes_obj.xyxy.cpu().numpy().tolist()
            confidences = boxes_obj.conf.cpu().tolist()
            classes = boxes_obj.cls.int().cpu().tolist()
        else:
            track_ids = []
            boxes = []
            confidences = []
            classes = []

        return {
            "track_ids": track_ids,
            "boxes": boxes,
            "confidences": confidences,
            "classes": classes,
            "frame_number": self.frame_count,
        }
