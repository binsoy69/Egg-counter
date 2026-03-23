"""Pydantic response and event models shared by routes and tests."""

from __future__ import annotations

from pydantic import BaseModel


class SizeBreakdown(BaseModel):
    """Egg counts by size classification."""

    small: int = 0
    medium: int = 0
    large: int = 0
    jumbo: int = 0


class BestDay(BaseModel):
    """Best single-day egg production record."""

    date: str | None = None
    total: int = 0


class TopSize(BaseModel):
    """Most common size classification."""

    size: str | None = None
    total: int = 0


class ProductionPoint(BaseModel):
    """Single data point in a production time series."""

    date: str
    total: int


class DashboardSnapshot(BaseModel):
    """Complete dashboard state for a given day and period."""

    date: str
    today_total: int
    today_by_size: dict[str, int]
    all_time_total: int
    best_day: BestDay
    top_size: TopSize
    period: str
    production_series: list[ProductionPoint]
    size_breakdown: SizeBreakdown


class HistoryRecord(BaseModel):
    """Individual egg detection event from the history log."""

    id: int
    timestamp: str
    detected_date: str
    track_id: int
    size: str
    confidence: float


class CollectionResponse(BaseModel):
    """Response from the collection endpoint."""

    message: str
    collected_count: int
    snapshot: dict
