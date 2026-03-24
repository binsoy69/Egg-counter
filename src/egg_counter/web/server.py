"""FastAPI application for the egg counter dashboard."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

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
    web_root = Path(__file__).resolve().parent
    templates = Jinja2Templates(directory=str(web_root / "templates"))
    app.mount(
        "/static",
        StaticFiles(directory=str(web_root / "static")),
        name="static",
    )

    def _template_context(request: Request, page: str) -> dict:
        return {
            "request": request,
            "title": title,
            "active_page": page,
        }

    # --- HTML routes ---

    @app.get("/", response_class=HTMLResponse)
    async def dashboard_root(request: Request):
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            _template_context(request, "dashboard"),
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_page(request: Request):
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            _template_context(request, "dashboard"),
        )

    @app.get("/history", response_class=HTMLResponse)
    async def history_page(request: Request):
        return templates.TemplateResponse(
            request,
            "history.html",
            _template_context(request, "history"),
        )

    # --- JSON API routes ---

    def _load_snapshot(period: str = "weekly") -> dict:
        repo = EggRepository(db_path)
        try:
            return repo.get_dashboard_snapshot(date.today(), period)
        finally:
            repo.close()

    @app.get("/api/dashboard")
    @app.get("/api/dashboard/snapshot")
    async def api_dashboard(
        period: str = Query("weekly", pattern="^(weekly|monthly|yearly)$"),
    ):
        return _load_snapshot(period)

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
    @app.post("/api/dashboard/collect")
    async def api_collect():
        # Get current running count from snapshot
        snapshot = _load_snapshot("weekly")
        current_count = snapshot["today_total"]

        # Persist collection
        if current_count > 0:
            logger = EggDatabaseLogger(db_path)
            logger.log_eggs_collected(current_count)
            logger.close()

        # Rebuild snapshot after collection
        updated_snapshot = _load_snapshot("weekly")

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
    @app.websocket("/ws/dashboard")
    async def websocket_endpoint(websocket: WebSocket):
        hub = _get_hub(app)
        await hub.connect(websocket)
        try:
            # Send initial snapshot
            snapshot = _load_snapshot("weekly")

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


def make_event_bridge(app: FastAPI) -> callable:
    """Create a callback that forwards pipeline events to WebSocket clients.

    Returns a synchronous function suitable for use as EggCounterPipeline's
    event_callback parameter. Each call rebuilds the dashboard snapshot
    and broadcasts the event to all connected WebSocket clients.
    """
    hub = _get_hub(app)
    db_path = app.state.settings.get("db_path", "data/eggs.db")

    def bridge(log_entry: dict) -> None:
        repo = EggRepository(db_path)
        try:
            snapshot = repo.get_dashboard_snapshot(date.today(), "weekly")
        finally:
            repo.close()

        event_type = log_entry.get("type", "unknown")
        toast = None
        if event_type == "egg_detected":
            toast = "1 new egg added"
        elif event_type == "eggs_collected":
            count = log_entry.get("count", 0)
            toast = f"{count} eggs collected"

        event = hub.build_snapshot_event(event_type, snapshot, toast=toast)
        hub.broadcast_json_sync(event)

    return bridge


def run_server(app: FastAPI, host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the uvicorn server with the given app."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
