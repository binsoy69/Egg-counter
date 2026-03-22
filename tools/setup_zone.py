"""Interactive zone configuration tool.

Captures a single frame from the camera, lets the user draw a rectangle
around the nest box region, and saves the zone configuration to JSON.

Usage:
    python tools/setup_zone.py
    python tools/setup_zone.py --camera-index 1 --output config/zone.json
"""

import argparse
import json
import sys
from pathlib import Path

import cv2


def get_camera_backend():
    """Return the appropriate OpenCV camera backend for the current platform."""
    if sys.platform == "win32":
        return cv2.CAP_DSHOW
    elif sys.platform.startswith("linux"):
        return cv2.CAP_V4L2
    return 0  # Default backend


def main():
    parser = argparse.ArgumentParser(
        description="Configure the egg-detection zone by drawing a rectangle on a camera frame."
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="Camera device index (default: 0)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="config/zone.json",
        help="Output path for zone config (default: config/zone.json)",
    )
    args = parser.parse_args()

    # Open camera
    backend = get_camera_backend()
    cap = cv2.VideoCapture(args.camera_index, backend)

    if not cap.isOpened():
        # Retry without explicit backend
        cap = cv2.VideoCapture(args.camera_index)

    if not cap.isOpened():
        print(f"Error: Could not open camera {args.camera_index}")
        sys.exit(1)

    # Capture a single frame
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Error: Could not read frame from camera")
        sys.exit(1)

    frame_height, frame_width = frame.shape[:2]

    # Let user draw the zone rectangle
    print("Draw a rectangle around the nest box zone, then press ENTER or SPACE.")
    print("Press 'c' to cancel.")
    roi = cv2.selectROI("Select Zone", frame, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    x, y, w, h = roi
    if w == 0 or h == 0:
        print("No zone selected. Exiting.")
        sys.exit(1)

    # Prompt for nest box width
    try:
        width_input = input("Enter nest box width in mm (default 300): ").strip()
        nest_box_width_mm = float(width_input) if width_input else 300.0
    except ValueError:
        nest_box_width_mm = 300.0

    zone_config = {
        "x1": int(x),
        "y1": int(y),
        "x2": int(x + w),
        "y2": int(y + h),
        "nest_box_width_mm": nest_box_width_mm,
        "frame_width": frame_width,
        "frame_height": frame_height,
    }

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(zone_config, f, indent=2)

    print(f"Zone saved to {output_path}")


if __name__ == "__main__":
    main()
