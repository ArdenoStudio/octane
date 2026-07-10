"""Daily market context — sentiment, FX, and world comparison snapshot.

Gives the homepage something that updates even when CPC retail is flat.
"""
from __future__ import annotations

from datetime import date

from app import fuel as fuel_mod
from app.db.connection import connect
from app.services import comparison, sentiment as sentiment_svc


def _latest_fx() -> dict | None:
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT rate, recorded_at
                    FROM fx_rates
                    WHERE base = 'USD' AND target = 'LKR'
                    ORDER BY recorded_at DESC
                    LIMIT 1
                    """
                )
                r = cur.fetchone()
    except Exception:
        return None
    if not r:
        return None
    return {
        "usd_lkr": float(r["rate"]),
        "recorded_at": r["recorded_at"].isoformat(),
    }


def snapshot(fuel_type: str = fuel_mod.PETROL_95) -> dict:
    """Aggregate daily-updating signals for the homepage strip."""
    if fuel_type not in fuel_mod.ALL_FUELS:
        fuel_type = fuel_mod.PETROL_95

    sent = sentiment_svc.load()
    sentiment_payload = None
    if sent is not None:
        sentiment_payload = {
            "direction": sent.direction,
            "confidence": sent.confidence,
            "magnitude_lkr": sent.magnitude_lkr,
            "summary": sent.summary,
            "generated_at": sent.generated_at,
            "headlines_analyzed": sent.headlines_analyzed,
            "signals": sent.signals[:3],
        }

    fx = _latest_fx()
    world = None
    try:
        cmp = comparison.world_comparison(fuel_type)
        world = {
            "fuel_type": cmp["fuel_type"],
            "sri_lanka_usd": cmp["sri_lanka"]["price_usd"],
            "world_average_usd": cmp["world_average_usd"],
            "delta_vs_world_pct": cmp["delta_vs_world_pct"],
            "fx_rate_used": cmp["fx_rate_used"],
        }
    except Exception:
        world = None

    return {
        "as_of": date.today().isoformat(),
        "fuel_type": fuel_type,
        "sentiment": sentiment_payload,
        "fx": fx,
        "world": world,
    }
