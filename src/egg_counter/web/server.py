"""FastAPI application for the egg counter dashboard.

Provides JSON API routes, WebSocket endpoint, and HTML page placeholders.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from egg_counter.db import EggDatabaseLogger
from egg_counter.repository import EggRepository
from egg_counter.web.realtime import WebSocketHub

if TYPE_CHECKING:
    from egg_counter.pipeline import EggCounterPipeline


def _get_hub(app: FastAPI) -> WebSocketHub:
    """Retrieve the WebSocketHub from the app state."""
    return app.state.hub


def create_app(
    settings: dict,
    zone_config: dict,
    pipeline: "EggCounterPipeline | None" = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Application settings dict.
        zone_config: Zone configuration dict.
        pipeline: Optional pipeline instance for live detection mode.

    Returns:
        Configured FastAPI app.
    """
    title = settings.get("dashboard_title", "EggSentry")
    app = FastAPI(title=title)
    app.state.settings = settings
    app.state.zone_config = zone_config
    app.state.pipeline = pipeline
    app.state.hub = WebSocketHub()

    db_path = settings.get("db_path", "data/eggs.db")

    # --- HTML routes (placeholders for Plan 02 template wiring) ---

    @app.get("/", response_class=HTMLResponse)
    async def dashboard_page():
        return HTMLResponse("<html><body><h1>EggSentry Dashboard</h1></body></html>")

    @app.get("/history", response_class=HTMLResponse)
    async def history_page():
        return HTMLResponse("<html><body><h1>EggSentry History</h1></body></html>")

    # --- JSON API routes ---

    @app.get("/api/dashboard")
    async def api_dashboard(
        period: str = Query("weekly", pattern="^(weekly|monthly|yearly)$"),
    ):
        repo = EggRepository(db_path)
        try:
            snapshot = repo.get_dashboard_snapshot(date.today(), period)
        finally:
            repo.close()
        return snapshot

    @app.get("/api/history")
    async def api_history(
        size: str | None = Query(None),
        start: str | None = Query(None, alias="from"),
        end: str | None = Query(None, alias="to"),
        limit: int = Query(200, ge=1, le=1000),
    ):
        start_date = date.fromisoformat(start) if start else None
        end_date = date.fromisoformat(end) if end else None
        repo = EggRepository(db_path)
        try:
            records = repo.get_history_records(
                start=start_date,
                end=end_date,
                size=size,
                limit=limit,
            )
        finally:
            repo.close()
        return records

    @app.post("/api/collect")
    async def api_collect():
        # Get current running count from snapshot
        repo = EggRepository(db_path)
        try:
            snapshot = repo.get_dashboard_snapshot(date.today(), "weekly")
            current_count = snapshot["today_total"]
        finally:
            repo.close()

        # Persist collection
        if current_count > 0:
            logger = EggDatabaseLogger(db_path)
            logger.log_eggs_collected(current_count)
            logger.close()

        # Rebuild snapshot after collection
        repo = EggRepository(db_path)
        try:
            updated_snapshot = repo.get_dashboard_snapshot(date.today(), "weekly")
        finally:
            repo.close()

        # Broadcast to WebSocket clients
        hub = _get_hub(app)
        event = hub.build_snapshot_event(
            "eggs_collected", updated_snapshot,
            toast=f"{current_count} eggs collected",
        )
        await hub.broadcast_json(event)

        return {
            "message": f"Collected {current_count} eggs",
            "collected_count": current_count,
            "snapshot": updated_snapshot,
        }

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/ws-meta")
    async def ws_meta():
        hub = _get_hub(app)
        return {
            "active_connections": len(hub.connections),
        }

    # --- WebSocket ---

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        hub = _get_hub(app)
        await hub.connect(websocket)
        try:
            # Send initial snapshot
            repo = EggRepository(db_path)
            try:
                snapshot = repo.get_dashboard_snapshot(date.today(), "weekly")
            finally:
                repo.close()

            event = hub.build_snapshot_event("snapshot", snapshot)
            await websocket.send_json(event)

            # Keep connection alive
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            hub.disconnect(websocket)
        except Exception:
            hub.disconnect(websocket)

    return app
