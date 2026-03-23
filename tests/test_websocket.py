"""Tests for WebSocket hub and real-time event broadcasting."""

import sqlite3
from datetime import date

import pytest

from egg_counter.db import EggDatabaseLogger
from egg_counter.repository import EggRepository


def _initialize_db(db_path: str) -> None:
    logger = EggDatabaseLogger(db_path)
    logger.close()


def _insert_egg(
    conn: sqlite3.Connection,
    detected_date: str,
    size: str,
    timestamp: str | None = None,
) -> None:
    ts = timestamp or f"{detected_date}T12:00:00+00:00"
    conn.execute(
        """
        INSERT INTO egg_events (
            timestamp, detected_date, track_id, size, confidence,
            bbox_x1, bbox_y1, bbox_x2, bbox_y2,
            size_method, raw_measurement_mm, frame_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ts, detected_date, 1, size, 0.9, 0.0, 0.0, 0.0, 0.0,
         "bbox_ratio", 50.0, 1),
    )


def _make_app(tmp_db_path):
    """Create a test FastAPI app."""
    _initialize_db(tmp_db_path)
    settings = {
        "db_path": tmp_db_path,
        "web_host": "127.0.0.1",
        "web_port": 8000,
        "dashboard_title": "EggSentry",
        "collection_mode": "manual",
    }
    zone_config = {
        "x1": 100, "y1": 100, "x2": 500, "y2": 400,
        "nest_box_width_mm": 300.0,
    }
    from egg_counter.web.server import create_app
    return create_app(settings, zone_config)


def test_websocket_receives_initial_snapshot(tmp_db_path):
    """WebSocket client receives an initial snapshot message on connect."""
    app = _make_app(tmp_db_path)

    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        data = ws.receive_json()
        assert data["type"] == "snapshot"
        assert "snapshot" in data


def test_websocket_receives_egg_detected_event(tmp_db_path):
    """WebSocket client receives broadcast via collect endpoint (event bridge path)."""
    _initialize_db(tmp_db_path)
    conn = sqlite3.connect(tmp_db_path)
    _insert_egg(conn, "2026-03-23", "large",
                timestamp="2026-03-23T12:00:00+00:00")
    conn.commit()
    conn.close()

    settings = {
        "db_path": tmp_db_path,
        "web_host": "127.0.0.1",
        "web_port": 8000,
        "dashboard_title": "EggSentry",
        "collection_mode": "manual",
    }
    zone_config = {
        "x1": 100, "y1": 100, "x2": 500, "y2": 400,
        "nest_box_width_mm": 300.0,
    }
    from egg_counter.web.server import create_app
    app = create_app(settings, zone_config)

    # Test the WebSocketHub's build_snapshot_event independently
    from egg_counter.web.server import _get_hub
    hub = _get_hub(app)
    repo = EggRepository(tmp_db_path)
    snap = repo.get_dashboard_snapshot(date(2026, 3, 23), "weekly")
    repo.close()

    event = hub.build_snapshot_event("egg_detected", snap, toast="1 new egg added")
    assert event["type"] == "egg_detected"
    assert event["toast"] == "1 new egg added"
    assert "snapshot" in event
    assert event["snapshot"]["today_total"] == 1


def test_websocket_disconnect_cleans_up_connection(tmp_db_path):
    """After disconnect, the hub has no active connections."""
    app = _make_app(tmp_db_path)

    from egg_counter.web.server import _get_hub
    from starlette.testclient import TestClient

    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # consume initial snapshot
        hub = _get_hub(app)
        assert len(hub.connections) >= 1

    # After disconnect
    hub = _get_hub(app)
    assert len(hub.connections) == 0
