from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter

from app import fuel as fuel_mod
from app.db.connection import connect

router = APIRouter(prefix="/v1", tags=["meta"])


def _data_freshness() -> dict:
    """Check how recent our CPC price data is."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT MAX(recorded_at) AS latest
                FROM fuel_prices
                WHERE source = 'cpc'
                """
            )
            r = cur.fetchone()
    latest = r["latest"] if r else None
    if not latest:
        return {"latest_recorded_at": None, "stale": True, "stale_hours": None}
    today = date.today()
    delta_hours = (today - latest).total_seconds() / 3600
    return {
        "latest_recorded_at": latest.isoformat(),
        "stale": delta_hours > 48,
        "stale_hours": round(delta_hours, 1),
    }


@router.get("/health")
def health():
    freshness = _data_freshness()
    return {
        "status": "degraded" if freshness["stale"] else "ok",
        "data": freshness,
    }


@router.get("/fuels")
def fuels():
    return {
        "fuels": [
            {"id": fid, "display": fuel_mod.DISPLAY[fid]}
            for fid in fuel_mod.ALL_FUELS
        ]
    }
