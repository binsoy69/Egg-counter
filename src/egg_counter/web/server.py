"""FastAPI application for the egg counter dashboard."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from egg_counter.auth import (
    build_session_middleware_config,
    is_authenticated,
    verify_password,
)
from egg_counter.db import EggDatabaseLogger
from egg_counter.repository import EggRepository
from egg_counter.web.realtime import WebSocketHub

if TYPE_CHECKING:
    from egg_counter.pipeline import EggCounterPipeline


def _get_hub(app: FastAPI) -> WebSocketHub:
    """Retrieve the WebSocketHub from the app state."""
    return app.state.hub


def _auth_enabled(settings: dict) -> bool:
    """Return whether application auth is enabled."""
    return bool(settings.get("auth_enabled", False))


def _ensure_auth_configured(settings: dict) -> None:
    """Validate auth settings before enabling session middleware."""
    if not _auth_enabled(settings):
        return

    required_keys = ["auth_username", "auth_password_hash", "session_secret"]
    missing = [key for key in required_keys if not settings.get(key)]
    if missing:
        raise ValueError(
            f"Missing required auth settings: {', '.join(missing)}"
        )


def create_app(
    settings: dict,
    zone_config: dict,
    pipeline: "EggCounterPipeline | None" = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    title = settings.get("dashboard_title", "EggSentry")
    _ensure_auth_configured(settings)
    app = FastAPI(title=title)
    if _auth_enabled(settings):
        app.add_middleware(
            SessionMiddleware,
            **build_session_middleware_config(settings),
        )
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

    def _redirect_to_login() -> RedirectResponse:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    def _require_html_auth(request: Request) -> RedirectResponse | None:
        if _auth_enabled(settings) and not is_authenticated(request):
            return _redirect_to_login()
        return None

    def _require_api_auth(request: Request) -> JSONResponse | None:
        if _auth_enabled(settings) and not is_authenticated(request):
            return JSONResponse(
                {"detail": "Authentication required"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        return None

    # --- HTML routes ---

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        if _auth_enabled(settings) and is_authenticated(request):
            return RedirectResponse(
                url="/dashboard",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        return templates.TemplateResponse(
            request,
            "login.html",
            {**_template_context(request, "login"), "error": None},
        )

    @app.post("/login")
    async def login(request: Request):
        if not _auth_enabled(settings):
            return RedirectResponse(
                url="/dashboard",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        body = (await request.body()).decode("utf-8")
        form = parse_qs(body)
        username = form.get("username", [""])[0]
        password = form.get("password", [""])[0]

        valid_username = username == settings["auth_username"]
        valid_password = verify_password(
            password,
            settings["auth_password_hash"],
        )
        if valid_username and valid_password:
            request.session["authenticated"] = True
            request.session["username"] = settings["auth_username"]
            return RedirectResponse(
                url="/dashboard",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        return templates.TemplateResponse(
            request,
            "login.html",
            {
                **_template_context(request, "login"),
                "error": "Invalid username or password",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    @app.post("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.get("/", response_class=HTMLResponse)
    async def dashboard_root(request: Request):
        auth_response = _require_html_auth(request)
        if auth_response is not None:
            return auth_response
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            _template_context(request, "dashboard"),
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_page(request: Request):
        auth_response = _require_html_auth(request)
        if auth_response is not None:
            return auth_response
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            _template_context(request, "dashboard"),
        )

    @app.get("/history", response_class=HTMLResponse)
    async def history_page(request: Request):
        auth_response = _require_html_auth(request)
        if auth_response is not None:
            return auth_response
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
        request: Request,
        period: str = Query("weekly", pattern="^(weekly|monthly|yearly)$"),
    ):
        auth_response = _require_api_auth(request)
        if auth_response is not None:
            return auth_response
        return _load_snapshot(period)

    @app.get("/api/history")
    async def api_history(
        request: Request,
        size: str | None = Query(None),
        start: str | None = Query(None, alias="from"),
        end: str | None = Query(None, alias="to"),
        limit: int = Query(200, ge=1, le=1000),
    ):
        auth_response = _require_api_auth(request)
        if auth_response is not None:
            return auth_response
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
    async def api_collect(request: Request):
        auth_response = _require_api_auth(request)
        if auth_response is not None:
            return auth_response

        snapshot = _load_snapshot("weekly")
        current_count = snapshot["today_total"]

        if current_count > 0:
            logger = EggDatabaseLogger(db_path)
            logger.log_eggs_collected(current_count)
            logger.close()

        updated_snapshot = _load_snapshot("weekly")

        hub = _get_hub(app)
        event = hub.build_snapshot_event(
            "eggs_collected",
            updated_snapshot,
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
    async def ws_meta(request: Request):
        auth_response = _require_api_auth(request)
        if auth_response is not None:
            return auth_response
        hub = _get_hub(app)
        return {"active_connections": len(hub.connections)}

    # --- WebSocket ---

    @app.websocket("/ws")
    @app.websocket("/ws/dashboard")
    async def websocket_endpoint(websocket: WebSocket):
        if _auth_enabled(settings) and not is_authenticated(websocket):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        hub = _get_hub(app)
        await hub.connect(websocket)
        try:
            snapshot = _load_snapshot("weekly")
            event = hub.build_snapshot_event("snapshot", snapshot)
            await websocket.send_json(event)
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
