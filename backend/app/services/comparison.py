"""Sri Lanka vs world comparison."""
from __future__ import annotations

from app import fuel as fuel_mod
from app.db.connection import connect
from app.services import prices

# Static USD/LKR fallback used only when no recent record is available.
# In production, override via daily FX scrape — for now, conservative default.
USD_LKR_FALLBACK = 305.0

# Map our fuel ids to globalpetrolprices categories (gasoline / diesel).
FUEL_TO_WORLD = {
    fuel_mod.PETROL_92: "gasoline",
    fuel_mod.PETROL_95: "gasoline",
    fuel_mod.AUTO_DIESEL: "diesel",
    fuel_mod.SUPER_DIESEL: "diesel",
    fuel_mod.KEROSENE: "diesel",
}


def _world_latest(fuel_category: str) -> list[dict]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (country)
                       country, price_usd, recorded_at
                FROM world_prices
                WHERE fuel_type = %s
                ORDER BY country, recorded_at DESC
                """,
                (fuel_category,),
            )
            return [
                {
                    "country": r["country"],
                    "price_usd": float(r["price_usd"]),
                    "recorded_at": r["recorded_at"].isoformat(),
                }
                for r in cur.fetchall()
            ]


def world_comparison(fuel_type: str) -> dict:
    category = FUEL_TO_WORLD.get(fuel_type, "gasoline")
    sl_price = prices.latest_for(fuel_type)
    world_rows = _world_latest(category)
    world_avg = next((r for r in world_rows if r["country"] == "World"), None)

    sl_price_lkr = sl_price["price_lkr"] if sl_price else None
    sl_price_usd = (sl_price_lkr / USD_LKR_FALLBACK) if sl_price_lkr else None

    delta_pct = None
    if sl_price_usd and world_avg:
        delta_pct = (sl_price_usd - world_avg["price_usd"]) / world_avg["price_usd"] * 100

    return {
        "fuel_type": fuel_type,
        "fuel_category": category,
        "sri_lanka": {
            "price_lkr": sl_price_lkr,
            "price_usd": round(sl_price_usd, 3) if sl_price_usd else None,
            "recorded_at": sl_price["recorded_at"] if sl_price else None,
        },
        "world_average_usd": world_avg["price_usd"] if world_avg else None,
        "delta_vs_world_pct": round(delta_pct, 1) if delta_pct is not None else None,
        "neighbors": [r for r in world_rows if r["country"] not in ("World", "Sri Lanka")],
        "fx_rate_used": USD_LKR_FALLBACK,
    }
