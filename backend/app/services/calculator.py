"""Trip cost calculator."""
from __future__ import annotations

from app.services import prices


def trip_cost(distance_km: float, efficiency_km_per_l: float, fuel_type: str) -> dict:
    if distance_km <= 0:
        raise ValueError("distance_km must be positive")
    if efficiency_km_per_l <= 0:
        raise ValueError("efficiency_km_per_l must be positive")

    latest = prices.latest_for(fuel_type)
    if not latest:
        raise LookupError(f"no price data for fuel_type={fuel_type}")

    litres_needed = distance_km / efficiency_km_per_l
    cost_lkr = litres_needed * latest["price_lkr"]

    return {
        "fuel_type": fuel_type,
        "distance_km": distance_km,
        "efficiency_km_per_l": efficiency_km_per_l,
        "price_lkr_per_l": latest["price_lkr"],
        "litres_needed": round(litres_needed, 2),
        "cost_lkr": round(cost_lkr, 2),
        "price_recorded_at": latest["recorded_at"],
    }
