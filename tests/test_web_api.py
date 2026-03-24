"""Tests for web API: repository-backed dashboard, history, and collection."""

import sqlite3
from datetime import date
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from egg_counter.auth import hash_password, verify_password
from egg_counter.config import load_settings
from egg_counter.db import EggDatabaseLogger
from egg_counter.repository import EggRepository


def _initialize_db(db_path: str) -> None:
    """Initialize database schema using EggDatabaseLogger."""
    logger = EggDatabaseLogger(db_path)
    logger.close()


def _insert_egg(
    conn: sqlite3.Connection,
    detected_date: str,
    size: str,
    timestamp: str | None = None,
    track_id: int = 1,
) -> None:
    """Insert a test egg event."""
    ts = timestamp or f"{detected_date}T12:00:00+00:00"
    conn.execute(
        """
        INSERT INTO egg_events (
            timestamp, detected_date, track_id, size, confidence,
            bbox_x1, bbox_y1, bbox_x2, bbox_y2,
            size_method, raw_measurement_mm, frame_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ts, detected_date, track_id, size, 0.9, 0.0, 0.0, 0.0, 0.0,
         "bbox_ratio", 50.0, 1),
    )


def _insert_collection(
    conn: sqlite3.Connection,
    collected_date: str,
    count: int,
    timestamp: str | None = None,
) -> None:
    """Insert a test collection event."""
    ts = timestamp or f"{collected_date}T14:00:00+00:00"
    conn.execute(
        """
        INSERT INTO collection_events (timestamp, collected_date, count)
        VALUES (?, ?, ?)
        """,
        (ts, collected_date, count),
    )


class TestDashboardSnapshot:
    """Tests for EggRepository.get_dashboard_snapshot."""

    def test_dashboard_snapshot(self, tmp_db_path):
        """Snapshot returns today's totals, all-time stats, and production series."""
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            _insert_egg(conn, "2026-03-20", "large")
            _insert_egg(conn, "2026-03-20", "medium")
            _insert_egg(conn, "2026-03-20", "large")
            _insert_egg(conn, "2026-03-21", "jumbo")
            _insert_egg(conn, "2026-03-23", "large",
                        timestamp="2026-03-23T10:00:00+00:00")
            _insert_egg(conn, "2026-03-23", "small",
                        timestamp="2026-03-23T11:00:00+00:00")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            snap = repo.get_dashboard_snapshot(date(2026, 3, 23), "weekly")
        finally:
            repo.close()

        assert snap["date"] == "2026-03-23"
        assert snap["today_total"] == 2
        assert snap["today_by_size"]["large"] == 1
        assert snap["today_by_size"]["small"] == 1
        assert snap["all_time_total"] == 6
        assert snap["period"] == "weekly"
        assert "best_day" in snap
        assert "top_size" in snap
        assert "production_series" in snap
        assert "size_breakdown" in snap

    def test_dashboard_snapshot_excludes_pre_collection_eggs(self, tmp_db_path):
        """After a same-day collection, only post-collection eggs appear."""
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            # Pre-collection eggs
            _insert_egg(conn, "2026-03-23", "large",
                        timestamp="2026-03-23T08:00:00+00:00")
            _insert_egg(conn, "2026-03-23", "medium",
                        timestamp="2026-03-23T09:00:00+00:00")
            # Collection at 10:00
            _insert_collection(conn, "2026-03-23", 2,
                               timestamp="2026-03-23T10:00:00+00:00")
            # Post-collection egg
            _insert_egg(conn, "2026-03-23", "jumbo",
                        timestamp="2026-03-23T11:00:00+00:00")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            snap = repo.get_dashboard_snapshot(date(2026, 3, 23), "weekly")
        finally:
            repo.close()

        assert snap["today_total"] == 1
        assert snap["today_by_size"] == {"jumbo": 1}


class TestHistoryRecords:
    """Tests for EggRepository.get_history_records."""

    def test_history_records_default_newest_first(self, tmp_db_path):
        """History records return newest first by default."""
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            _insert_egg(conn, "2026-03-18", "large",
                        timestamp="2026-03-18T12:00:00+00:00")
            _insert_egg(conn, "2026-03-20", "medium",
                        timestamp="2026-03-20T12:00:00+00:00")
            _insert_egg(conn, "2026-03-19", "small",
                        timestamp="2026-03-19T12:00:00+00:00")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            records = repo.get_history_records()
        finally:
            repo.close()

        assert len(records) == 3
        # Newest first
        assert records[0]["detected_date"] == "2026-03-20"
        assert records[1]["detected_date"] == "2026-03-19"
        assert records[2]["detected_date"] == "2026-03-18"

    def test_history_records_filters_by_size_and_date_range(self, tmp_db_path):
        """History records can be filtered by size and date range."""
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            _insert_egg(conn, "2026-03-18", "large")
            _insert_egg(conn, "2026-03-19", "medium")
            _insert_egg(conn, "2026-03-19", "large")
            _insert_egg(conn, "2026-03-20", "large")
            _insert_egg(conn, "2026-03-21", "large")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            records = repo.get_history_records(
                start=date(2026, 3, 19),
                end=date(2026, 3, 20),
                size="large",
            )
        finally:
            repo.close()

        assert len(records) == 2
        for r in records:
            assert r["size"] == "large"


class TestAggregates:
    """Tests for best_day and top_size roll-ups."""

    def test_best_day_and_top_size_roll_up(self, tmp_db_path):
        """Best day and top size compute correctly from all data."""
        _initialize_db(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            _insert_egg(conn, "2026-03-18", "large")
            _insert_egg(conn, "2026-03-18", "large")
            _insert_egg(conn, "2026-03-18", "large")
            _insert_egg(conn, "2026-03-19", "medium")
            _insert_egg(conn, "2026-03-20", "medium")
            conn.commit()
        finally:
            conn.close()

        repo = EggRepository(tmp_db_path)
        try:
            best = repo.get_best_day()
            top = repo.get_top_size()
        finally:
            repo.close()

        assert best["date"] == "2026-03-18"
        assert best["total"] == 3
        assert top["size"] == "large"
        assert top["total"] == 3


def test_verify_password_accepts_matching_scrypt_hash():
    """Matching password validates against scrypt hash format."""
    stored_hash = hash_password("farm-secret", "pepper-salt")

    assert verify_password("farm-secret", stored_hash) is True


def test_verify_password_rejects_wrong_password():
    """Wrong password fails verification."""
    stored_hash = hash_password("farm-secret", "pepper-salt")

    assert verify_password("wrong-secret", stored_hash) is False


def test_load_settings_overrides_auth_from_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    """Environment auth values override YAML defaults."""
    config_path = Path("tests/_auth_settings.yaml")
    monkeypatch.setenv("EGG_COUNTER_AUTH_USERNAME", "keeper")
    monkeypatch.setenv(
        "EGG_COUNTER_AUTH_PASSWORD_HASH",
        "scrypt$salty$deadbeef",
    )
    monkeypatch.setenv("EGG_COUNTER_SESSION_SECRET", "super-secret")
    monkeypatch.setenv("EGG_COUNTER_SESSION_MAX_AGE", "86400")
    config_path.write_text(
        "\n".join(
            [
                'dashboard_title: "EggSentry"',
                "auth_enabled: true",
                'auth_cookie_name: "egg_counter_session"',
                "session_max_age: 1209600",
            ]
        ),
        encoding="utf-8",
    )

    try:
        settings = load_settings(str(config_path))
    finally:
        config_path.unlink(missing_ok=True)

    assert settings["auth_username"] == "keeper"
    assert settings["auth_password_hash"] == "scrypt$salty$deadbeef"
    assert settings["session_secret"] == "super-secret"
    assert settings["session_max_age"] == 86400


# --- FastAPI route tests ---


@pytest.fixture
def _seeded_app(tmp_db_path):
    """Create a FastAPI app with seeded test data."""
    _initialize_db(tmp_db_path)
    conn = sqlite3.connect(tmp_db_path)
    try:
        _insert_egg(conn, "2026-03-23", "large",
                    timestamp="2026-03-23T10:00:00+00:00")
        _insert_egg(conn, "2026-03-23", "medium",
                    timestamp="2026-03-23T11:00:00+00:00")
        _insert_egg(conn, "2026-03-20", "jumbo")
        conn.commit()
    finally:
        conn.close()

    settings = {
        "db_path": tmp_db_path,
        "web_host": "127.0.0.1",
        "web_port": 8000,
        "dashboard_title": "EggSentry",
        "collection_mode": "manual",
        "auth_enabled": True,
        "auth_username": "keeper",
        "auth_password_hash": hash_password("farm-secret", "pepper-salt"),
        "auth_cookie_name": "egg_counter_session",
        "session_secret": "super-secret-session-key",
        "session_max_age": 1209600,
    }
    zone_config = {
        "x1": 100, "y1": 100, "x2": 500, "y2": 400,
        "nest_box_width_mm": 300.0,
    }
    from egg_counter.web.server import create_app
    return create_app(settings, zone_config)


async def _login(client: AsyncClient) -> None:
    """Authenticate a test client against the login route."""
    response = await client.post(
        "/login",
        content="username=keeper&password=farm-secret",
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert response.status_code == 303


@pytest.mark.asyncio
async def test_dashboard_api_returns_snapshot(tmp_db_path, _seeded_app):
    """GET /api/dashboard returns a dashboard snapshot."""
    transport = ASGITransport(app=_seeded_app)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
    ) as client:
        await _login(client)
        resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "today_total" in data
    assert "production_series" in data


@pytest.mark.asyncio
async def test_history_api_applies_filters(tmp_db_path, _seeded_app):
    """GET /api/history with size filter returns matching records."""
    transport = ASGITransport(app=_seeded_app)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
    ) as client:
        await _login(client)
        resp = await client.get("/api/history?size=large")
    assert resp.status_code == 200
    data = resp.json()
    for rec in data:
        assert rec["size"] == "large"


@pytest.mark.asyncio
async def test_collect_api_persists_collection_and_returns_updated_snapshot(
    tmp_db_path, _seeded_app
):
    """POST /api/collect persists a collection and returns updated snapshot."""
    transport = ASGITransport(app=_seeded_app)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
    ) as client:
        await _login(client)
        resp = await client.post("/api/collect")
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "collected_count" in data
    assert "snapshot" in data
    # After collection, today's running count should be 0
    assert data["snapshot"]["today_total"] == 0


@pytest.mark.asyncio
async def test_health_route_returns_ok(tmp_db_path, _seeded_app):
    """GET /health returns status ok."""
    transport = ASGITransport(app=_seeded_app)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_dashboard_redirects_to_login_when_unauthenticated(
    tmp_db_path,
    _seeded_app,
):
    """GET /dashboard redirects to the login page without a session."""
    transport = ASGITransport(app=_seeded_app)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
    ) as client:
        resp = await client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


@pytest.mark.asyncio
async def test_api_dashboard_returns_401_when_unauthenticated(
    tmp_db_path,
    _seeded_app,
):
    """GET /api/dashboard is blocked until a session exists."""
    transport = ASGITransport(app=_seeded_app)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
    ) as client:
        resp = await client.get("/api/dashboard")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Authentication required"


@pytest.mark.asyncio
async def test_login_sets_session_cookie(tmp_db_path, _seeded_app):
    """Successful login sets the configured session cookie."""
    transport = ASGITransport(app=_seeded_app)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
    ) as client:
        resp = await client.post(
            "/login",
            content="username=keeper&password=farm-secret",
            headers={"content-type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"
    assert "egg_counter_session=" in resp.headers["set-cookie"]


@pytest.mark.asyncio
async def test_logout_clears_session(tmp_db_path, _seeded_app):
    """Logout clears the session and returns to the login page."""
    transport = ASGITransport(app=_seeded_app)
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
    ) as client:
        await _login(client)
        resp = await client.post("/logout", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"
    assert "egg_counter_session=null" in resp.headers["set-cookie"]
