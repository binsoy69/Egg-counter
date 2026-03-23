"""CLI entry point for the egg counter application."""

from __future__ import annotations

import argparse
import subprocess
import sys

from egg_counter.config import load_settings, load_zone_config
from egg_counter.pipeline import EggCounterPipeline


def main() -> None:
    """Main CLI entry point for the egg-counter command."""
    parser = argparse.ArgumentParser(
        description="Egg Counter - YOLO-based egg detection and counting",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- run command ---
    run_parser = subparsers.add_parser("run", help="Start detection pipeline")
    run_parser.add_argument(
        "--model",
        required=True,
        help="Path to YOLO model (.pt file or NCNN model directory)",
    )
    run_parser.add_argument(
        "--camera",
        type=int,
        default=None,
        help="Camera index (default: from settings.yaml)",
    )
    run_parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to settings.yaml (default: config/settings.yaml)",
    )
    run_parser.add_argument(
        "--zone",
        default="config/zone.json",
        help="Path to zone.json (default: config/zone.json)",
    )
    run_parser.add_argument(
        "--video",
        default=None,
        help="Path to a video file (use instead of camera for testing)",
    )

    # --- setup-zone command ---
    zone_parser = subparsers.add_parser(
        "setup-zone", help="Run zone configuration tool"
    )
    zone_parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera index (default: 0)",
    )
    zone_parser.add_argument(
        "--output",
        default="config/zone.json",
        help="Output path (default: config/zone.json)",
    )

    args = parser.parse_args()

    if args.command == "run":
        settings = load_settings(args.config)
        zone_config = load_zone_config(args.zone)
        camera = (
            args.camera
            if args.camera is not None
            else settings.get("camera_index", 0)
        )
        pipeline = EggCounterPipeline(settings, zone_config)
        try:
            pipeline.run(args.model, camera, video_path=args.video)
        except KeyboardInterrupt:
            pipeline.stop()

    elif args.command == "setup-zone":
        subprocess.run(
            [
                sys.executable,
                "tools/setup_zone.py",
                "--camera",
                str(args.camera),
                "--output",
                args.output,
            ],
            check=True,
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
