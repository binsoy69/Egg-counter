"""Tests for WebSocket hub and real-time event broadcasting."""

import asyncio
import sqlite3

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


@pytest.fixture
def app_client(tmp_db_path):
    """Create a test client for the FastAPI app."""
    from httpx import ASGITransport, AsyncClient

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
    app = create_app(settings, zone_config)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_websocket_receives_initial_snapshot(tmp_db_path):
    """WebSocket client receives an initial snapshot message on connect."""
    from httpx import ASGITransport, AsyncClient

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
    app = create_app(settings, zone_config)

    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        data = ws.receive_json()
        assert data["type"] == "snapshot"
        assert "snapshot" in data


@pytest.mark.asyncio
async def test_websocket_receives_egg_detected_event(tmp_db_path):
    """WebSocket client receives broadcast when event bridge fires."""
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
    app = create_app(settings, zone_config)

    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        # Consume initial snapshot
        ws.receive_json()

        # Simulate an egg detection through the event bridge
        from egg_counter.web.server import _get_hub
        hub = _get_hub(app)

        # Insert an egg into the DB to make the snapshot non-empty
        conn = sqlite3.connect(tmp_db_path)
        _insert_egg(conn, "2026-03-23", "large",
                    timestamp="2026-03-23T12:00:00+00:00")
        conn.commit()
        conn.close()

        # Build and broadcast an event
        from egg_counter.web.realtime import WebSocketHub
        repo = EggRepository(tmp_db_path)
        from datetime import date
        snap = repo.get_dashboard_snapshot(date(2026, 3, 23), "weekly")
        repo.close()
        event = hub.build_snapshot_event("egg_detected", snap, toast="1 new egg added")
        hub.broadcast_json(event)

        data = ws.receive_json()
        assert data["type"] == "egg_detected"
        assert data["toast"] == "1 new egg added"
        assert "snapshot" in data


@pytest.mark.asyncio
async def test_websocket_disconnect_cleans_up_connection(tmp_db_path):
    """After disconnect, the hub has no active connections."""
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

    from egg_counter.web.server import create_app, _get_hub
    app = create_app(settings, zone_config)

    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # consume initial snapshot
        hub = _get_hub(app)
        assert len(hub.connections) >= 1

    # After disconnect
    hub = _get_hub(app)
    assert len(hub.connections) == 0
