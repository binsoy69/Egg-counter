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

    # --- preview command ---
    preview_parser = subparsers.add_parser(
        "preview", help="Run detection with live GUI overlay for visual verification"
    )
    preview_parser.add_argument(
        "--model",
        required=True,
        help="Path to YOLO model (.pt file or NCNN model directory)",
    )
    preview_parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera index (default: 0)",
    )
    preview_parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to settings.yaml (default: config/settings.yaml)",
    )
    preview_parser.add_argument(
        "--zone",
        default="config/zone.json",
        help="Path to zone.json (default: config/zone.json)",
    )
    preview_parser.add_argument(
        "--video",
        default=None,
        help="Path to a video file (use instead of camera for testing)",
    )

    # --- serve command ---
    serve_parser = subparsers.add_parser(
        "serve", help="Start web dashboard server with optional live detection"
    )
    serve_parser.add_argument(
        "--model",
        default=None,
        help="Path to YOLO model (enables live detection pipeline)",
    )
    serve_parser.add_argument(
        "--camera",
        type=int,
        default=None,
        help="Camera index (default: from settings.yaml)",
    )
    serve_parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to settings.yaml (default: config/settings.yaml)",
    )
    serve_parser.add_argument(
        "--zone",
        default="config/zone.json",
        help="Path to zone.json (default: config/zone.json)",
    )
    serve_parser.add_argument(
        "--video",
        default=None,
        help="Path to a video file (use instead of camera for testing)",
    )
    serve_parser.add_argument(
        "--host",
        default=None,
        help="Server host (default: from settings.yaml or 0.0.0.0)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Server port (default: from settings.yaml or 8000)",
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

    elif args.command == "preview":
        from egg_counter.preview import run_preview
        run_preview(
            model_path=args.model,
            camera_index=args.camera,
            video_path=args.video,
            config_path=args.config,
            zone_path=args.zone,
        )

    elif args.command == "serve":
        settings = load_settings(args.config)
        zone_config = load_zone_config(args.zone)
        host = args.host or settings.get("web_host", "0.0.0.0")
        port = args.port or settings.get("web_port", 8000)

        from egg_counter.web.server import create_app, make_event_bridge, run_server

        pipeline = None
        if args.model:
            event_bridge = None  # will be set after app creation
            pipeline = EggCounterPipeline(settings, zone_config)

        app = create_app(settings, zone_config, pipeline=pipeline)

        if pipeline is not None:
            event_bridge = make_event_bridge(app)
            pipeline.event_callback = event_bridge

        print(f"Starting EggSentry dashboard at http://{host}:{port}")
        run_server(app, host=host, port=port)

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
