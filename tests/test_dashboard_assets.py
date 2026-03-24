"""Asset and template assertions for the Phase 03 dashboard UI."""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "src" / "egg_counter" / "web" / "templates"
STATIC = ROOT / "src" / "egg_counter" / "web" / "static"


@pytest.fixture
def dashboard_html() -> str:
    return (TEMPLATES / "dashboard.html").read_text(encoding="utf-8")


@pytest.fixture
def history_html() -> str:
    return (TEMPLATES / "history.html").read_text(encoding="utf-8")


@pytest.fixture
def styles_css() -> str:
    return (STATIC / "styles.css").read_text(encoding="utf-8")


@pytest.fixture
def dashboard_js() -> str:
    return (STATIC / "dashboard.js").read_text(encoding="utf-8")


@pytest.fixture
def history_js() -> str:
    return (STATIC / "history.js").read_text(encoding="utf-8")


def test_dashboard_template_contains_locked_sections(dashboard_html: str) -> None:
    for marker in (
        "Dashboard",
        "History",
        "Modify Camera",
        "Logout",
        "Collected",
        "Daily Egg Production",
        "Egg Size Distribution",
    ):
        assert marker in dashboard_html


def test_dashboard_template_contains_required_hooks(dashboard_html: str) -> None:
    for hook in (
        'id="today-total"',
        'id="size-small"',
        'id="size-medium"',
        'id="size-large"',
        'id="size-jumbo"',
        'id="collect-button"',
        'id="period-weekly"',
        'id="period-monthly"',
        'id="period-yearly"',
        'id="production-chart"',
        'id="size-chart"',
        'id="live-toast"',
    ):
        assert hook in dashboard_html


def test_dashboard_js_uses_contracts_and_live_behaviors(dashboard_js: str) -> None:
    for marker in (
        "/api/dashboard/snapshot",
        "/api/dashboard/collect",
        "/ws/dashboard",
        "1 new egg added",
        "window.confirm",
    ):
        assert marker in dashboard_js


def test_styles_include_no_overflow_and_mobile_stack_guardrails(styles_css: str) -> None:
    for marker in (
        "overflow-x: hidden",
        "grid-template-columns: repeat(3, minmax(0, 1fr));",
        "@media (max-width: 719px)",
        "grid-template-columns: minmax(0, 1fr);",
    ):
        assert marker in styles_css
