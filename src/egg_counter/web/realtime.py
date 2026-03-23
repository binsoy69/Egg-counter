"""WebSocket connection manager and broadcast helpers for dashboard clients."""

from __future__ import annotations

import json
from typing import Any

from starlette.websockets import WebSocket


class WebSocketHub:
    """Manages WebSocket connections and broadcasts events to all clients."""

    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the active list."""
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast_json(self, payload: dict) -> None:
        """Send a JSON payload to all connected WebSocket clients.

        Disconnected clients are silently removed.
        """
        dead: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def broadcast_json_sync(self, payload: dict) -> None:
        """Synchronous broadcast for use from non-async contexts (e.g. pipeline callbacks).

        Queues the payload for delivery. For test compatibility with
        Starlette's TestClient, this uses the low-level scope send channel.
        """
        import asyncio

        dead: list[WebSocket] = []
        for ws in self.connections:
            try:
                # Try to schedule in the running event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(ws.send_json(payload))
                else:
                    loop.run_until_complete(ws.send_json(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def build_snapshot_event(
        self,
        event_type: str,
        snapshot: dict,
        toast: str | None = None,
    ) -> dict:
        """Build a structured event payload for WebSocket broadcast.

        Args:
            event_type: Event type string (e.g. 'egg_detected', 'eggs_collected').
            snapshot: Current dashboard snapshot dict.
            toast: Optional toast notification text.

        Returns:
            Event dict with type, snapshot, and optional toast.
        """
        event: dict[str, Any] = {
            "type": event_type,
            "snapshot": snapshot,
        }
        if toast is not None:
            event["toast"] = toast
        return event
