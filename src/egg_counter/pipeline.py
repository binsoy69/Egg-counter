"""Main detection pipeline orchestrating all components.

Wires together: detector, tracker, size classifier, logger, zone filter,
and daylight scheduler into a single frame-processing loop.
"""

from __future__ import annotations

import sys
import time

import cv2

from egg_counter.config import load_settings, load_zone_config
from egg_counter.detector import EggDetector
from egg_counter.logger import EggEventLogger
from egg_counter.scheduler import is_daylight, wait_for_daylight
from egg_counter.size_classifier import SizeClassifier
from egg_counter.tracker import EggTracker
from egg_counter.zone import is_in_zone


class EggCounterPipeline:
    """Main detection loop orchestrating all egg counting components.

    Captures frames from camera, runs YOLO+ByteTrack detection, applies
    zone filtering, stability timing, size classification, and event logging.
    """

    def __init__(self, settings: dict, zone_config: dict) -> None:
        """Initialize the pipeline with settings and zone configuration.

        Args:
            settings: Application settings dict from settings.yaml.
            zone_config: Zone configuration dict from zone.json.
        """
        self.settings = settings
        self.zone_config = zone_config
        self.detector: EggDetector | None = None
        self.tracker = EggTracker(
            stability_seconds=settings.get("stability_seconds", 3),
        )
        self.classifier = SizeClassifier(zone_config)
        self.logger = EggEventLogger(settings.get("log_dir", "logs"))
        self.running = False
        self.frame_rate = settings.get("frame_rate", 3)

    def setup(self, model_path: str) -> None:
        """Initialize the YOLO detector.

        Args:
            model_path: Path to the YOLO model file.
        """
        self.detector = EggDetector(
            model_path,
            tracker_config=self.settings.get(
                "bytetrack_config", "config/bytetrack_eggs.yaml"
            ),
            confidence=self.settings.get("confidence_threshold", 0.5),
        )

    def _initialize_existing_eggs(self, frame) -> None:
        """Detect and mark existing eggs on startup (D-08).

        Runs a single prediction (no tracking state) to identify eggs
        already in the zone, then marks them as counted so they are not
        re-counted after a restart.

        Args:
            frame: First captured frame.
        """
        result = self.detector.detect_once(frame)
        in_zone_track_ids = []

        for track_id, box in zip(result["track_ids"], result["boxes"]):
            if is_in_zone(box, self.zone_config):
                in_zone_track_ids.append(track_id)

        if in_zone_track_ids:
            self.tracker.initialize_from_existing(in_zone_track_ids)
            print(
                f"Startup: {len(in_zone_track_ids)} existing eggs detected, "
                f"marked as already counted"
            )

    def process_frame(self, frame, timestamp: float) -> list[dict]:
        """Process a single frame through the detection pipeline.

        Args:
            frame: Input image frame (numpy array from cv2).
            timestamp: Current time in seconds (time.time()).

        Returns:
            List of logged event dicts (egg_detected or eggs_collected).
        """
        detector_result = self.detector.detect_and_track(frame)

        track_ids = detector_result["track_ids"]
        boxes = detector_result["boxes"]
        confidences = detector_result["confidences"]

        # Compute zone containment for each detection
        in_zone_flags = [
            is_in_zone(box, self.zone_config) for box in boxes
        ]

        # Run tracker to get events
        tracker_events = self.tracker.process_detections(
            track_ids, boxes, in_zone_flags, timestamp
        )

        logged_events = []

        for event in tracker_events:
            if event["action"] == "count":
                # Classify egg size
                size, raw_mm = self.classifier.classify(event["bbox"])

                # Find matching confidence from detector results
                confidence = 0.0
                for tid, conf in zip(track_ids, confidences):
                    if tid == event["track_id"]:
                        confidence = conf
                        break

                log_entry = self.logger.log_egg_detected(
                    track_id=event["track_id"],
                    size=size,
                    confidence=confidence,
                    bbox=event["bbox"],
                    size_method="bbox_ratio",
                    raw_measurement_mm=raw_mm,
                    frame_number=detector_result["frame_number"],
                )
                logged_events.append(log_entry)

            elif event["action"] == "collected":
                log_entry = self.logger.log_eggs_collected(
                    count=event["count"],
                )
                logged_events.append(log_entry)

        return logged_events

    def run(self, model_path: str, camera_index: int = 0) -> None:
        """Start the main detection loop.

        Args:
            model_path: Path to the YOLO model file.
            camera_index: Camera device index.
        """
        self.setup(model_path)

        # Open camera with platform-appropriate backend
        if sys.platform == "linux":
            cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
        else:
            cap = cv2.VideoCapture(camera_index)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        print("Egg Counter started. Press Ctrl+C to stop.")

        # Read first frame and initialize existing eggs
        ret, frame = cap.read()
        if ret:
            self._initialize_existing_eggs(frame)

        self.running = True

        # Get location for daylight scheduling (optional)
        location = self.settings.get("location", {})
        lat = location.get("latitude")
        lon = location.get("longitude")
        use_daylight = lat is not None and lon is not None

        try:
            while self.running and cap.isOpened():
                # Check daylight if location configured
                if use_daylight and not is_daylight(lat, lon):
                    wait_for_daylight(lat, lon)
                    continue

                ret, frame = cap.read()
                if not ret:
                    print("Warning: failed to read frame, retrying...")
                    time.sleep(1.0)
                    continue

                self.process_frame(frame, time.time())

                # Maintain target frame rate
                time.sleep(1.0 / self.frame_rate)
        finally:
            cap.release()
            print("Egg Counter stopped.")

    def stop(self) -> None:
        """Signal the pipeline to stop."""
        self.running = False
