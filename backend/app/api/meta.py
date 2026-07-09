from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter

from app import fuel as fuel_mod
from app.db.connection import connect
from app.services import prices as price_service

router = APIRouter(prefix="/v1", tags=["meta"])


def _data_freshness() -> dict:
    """Check scrape verification freshness (not CPC revision age).

    CPC may leave retail prices unchanged for weeks. Health should reflect
    whether Octane is still successfully checking the source.
    """
    last_verified = price_service.last_verified_at("cpc")
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
    latest_revision = r["latest"] if r else None

    if not last_verified and not latest_revision:
        return {
            "latest_recorded_at": None,
            "last_verified_at": None,
            "stale": True,
            "stale_hours": None,
        }

    stale_hours: float | None = None
    stale = True
    if last_verified:
        verified_dt = datetime.fromisoformat(last_verified.replace("Z", "+00:00"))
        stale_hours = (datetime.now(timezone.utc) - verified_dt).total_seconds() / 3600
        # Scrapers run ~every 4 hours; allow one missed window before degraded.
        stale = stale_hours > 12
    elif latest_revision:
        # Pre-migration fallback: revision date only.
        delta_hours = (date.today() - latest_revision).total_seconds() / 3600
        stale_hours = round(delta_hours, 1)
        stale = delta_hours > 48

    return {
        "latest_recorded_at": latest_revision.isoformat() if latest_revision else None,
        "last_verified_at": last_verified,
        "stale": stale,
        "stale_hours": round(stale_hours, 1) if stale_hours is not None else None,
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
