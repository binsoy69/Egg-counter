"""GUI preview mode for visual verification of egg detection.

Provides frame annotation overlays (bounding boxes, size labels, zone
rectangle, egg count) and a live display loop for camera or video input.
"""

from __future__ import annotations

import sys

import cv2
import numpy as np

from egg_counter.config import load_settings, load_zone_config
from egg_counter.detector import EggDetector
from egg_counter.size_classifier import SizeClassifier
from egg_counter.zone import is_in_zone


# Overlay colours (BGR)
_COLOR_ZONE = (0, 255, 0)       # green
_COLOR_IN_ZONE = (0, 165, 255)  # orange-blue (in-zone bbox)
_COLOR_OUT_ZONE = (128, 128, 128)  # gray (out-of-zone bbox)
_COLOR_TEXT = (255, 255, 255)    # white
_COLOR_OUTLINE = (0, 0, 0)      # black outline for readability


def draw_detections(
    frame: np.ndarray,
    detector_result: dict,
    zone_config: dict,
    classifier: SizeClassifier,
    egg_count: int,
) -> np.ndarray:
    """Annotate a frame with detection overlays.

    Draws zone rectangle, bounding boxes with size/confidence labels,
    and an egg count overlay in the top-left corner.

    Args:
        frame: BGR image (numpy array, modified in-place).
        detector_result: Dict with track_ids, boxes, confidences, classes.
        zone_config: Zone rectangle dict with x1, y1, x2, y2.
        classifier: SizeClassifier instance for size labelling.
        egg_count: Running total of eggs counted.

    Returns:
        The annotated frame (same array, modified in-place).
    """
    # Draw zone rectangle
    cv2.rectangle(
        frame,
        (int(zone_config["x1"]), int(zone_config["y1"])),
        (int(zone_config["x2"]), int(zone_config["y2"])),
        _COLOR_ZONE,
        thickness=2,
    )

    # Draw each detection
    track_ids = detector_result.get("track_ids", [])
    boxes = detector_result.get("boxes", [])
    confidences = detector_result.get("confidences", [])

    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])

        # Colour based on zone containment
        in_zone = is_in_zone(box, zone_config)
        color = _COLOR_IN_ZONE if in_zone else _COLOR_OUT_ZONE

        # Bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness=2)

        # Size classification
        size, height_mm = classifier.classify(list(box))

        # Track ID (may be shorter than boxes list for detect_once results)
        tid = track_ids[i] if i < len(track_ids) else "?"

        # Confidence
        conf = confidences[i] if i < len(confidences) else 0.0

        # Label above box
        label = f"#{tid} {size} {conf:.0%}"
        _draw_text_with_outline(frame, label, (x1, y1 - 8), scale=0.6)

        # Height below box
        mm_label = f"{height_mm:.1f}mm"
        _draw_text_with_outline(frame, mm_label, (x1, y2 + 18), scale=0.5)

    # Egg count overlay in top-left
    count_text = f"Eggs: {egg_count}"
    _draw_text_with_outline(frame, count_text, (15, 45), scale=1.2, thickness=2)

    return frame


def _draw_text_with_outline(
    frame: np.ndarray,
    text: str,
    org: tuple[int, int],
    scale: float = 0.6,
    thickness: int = 1,
) -> None:
    """Draw white text with black outline for readability."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    # Black outline
    cv2.putText(frame, text, org, font, scale, _COLOR_OUTLINE, thickness + 2, cv2.LINE_AA)
    # White text
    cv2.putText(frame, text, org, font, scale, _COLOR_TEXT, thickness, cv2.LINE_AA)


def run_preview(
    model_path: str,
    camera_index: int = 0,
    video_path: str | None = None,
    config_path: str = "config/settings.yaml",
    zone_path: str = "config/zone.json",
) -> None:
    """Run the live GUI preview with detection overlays.

    Opens an OpenCV window showing bounding boxes, confidence scores,
    size classifications, zone rectangle, and running egg count.

    Args:
        model_path: Path to YOLO model (.pt or NCNN directory).
        camera_index: Camera device index (default 0).
        video_path: Path to video file. If set, uses file instead of camera.
        config_path: Path to settings.yaml.
        zone_path: Path to zone.json.
    """
    settings = load_settings(config_path)
    zone_config = load_zone_config(zone_path)

    detector = EggDetector(
        model_path,
        tracker_config=settings.get("bytetrack_config", "config/bytetrack_eggs.yaml"),
        confidence=settings.get("confidence_threshold", 0.5),
    )
    classifier = SizeClassifier(zone_config)

    # Open video source
    if video_path:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: cannot open video file '{video_path}'")
            return
        source_fps = cap.get(cv2.CAP_PROP_FPS) or settings.get("frame_rate", 3)
        delay = int(1000 / source_fps)
        print(f"Preview: playing video {video_path} @ {source_fps:.1f} fps")
    else:
        # Platform-aware camera backend
        if sys.platform == "linux":
            cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
        else:
            cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        delay = 1  # minimal delay for camera (real-time)
        print(f"Preview: camera {camera_index}")

    if not cap.isOpened():
        print("Error: cannot open video source")
        return

    egg_count = 0
    seen_track_ids: set[int] = set()

    print("Preview started. Press 'q' or ESC to exit.")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                if video_path:
                    print("Video ended.")
                break

            # Detect and track
            result = detector.detect_and_track(frame)

            # Count new eggs entering the zone
            for i, box in enumerate(result["boxes"]):
                if i < len(result["track_ids"]):
                    tid = result["track_ids"][i]
                    if is_in_zone(box, zone_config) and tid not in seen_track_ids:
                        seen_track_ids.add(tid)
                        egg_count += 1

            # Annotate and display
            annotated = draw_detections(frame, result, zone_config, classifier, egg_count)
            cv2.imshow("Egg Counter Preview", annotated)

            key = cv2.waitKey(delay) & 0xFF
            if key == ord("q") or key == 27:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    print(f"Preview ended. Total eggs seen: {egg_count}")
