"""Unit tests for price freshness helpers that do not need a live DB."""
from __future__ import annotations

from datetime import datetime, timezone

from app.services import prices as price_service


def test_iso_ts_formats_naive_as_utc():
    dt = datetime(2026, 7, 9, 6, 30, 0)
    assert price_service._iso_ts(dt) == "2026-07-09T06:30:00Z"


def test_iso_ts_preserves_timezone():
    dt = datetime(2026, 7, 9, 12, 0, 0, tzinfo=timezone.utc)
    assert price_service._iso_ts(dt) == "2026-07-09T12:00:00Z"


def test_iso_ts_none():
    assert price_service._iso_ts(None) is None
