from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app import fuel as fuel_mod
from app.services import prices

router = APIRouter(prefix="/v1/prices", tags=["prices"])


@router.get("/latest")
def latest():
    rows = prices.latest_all()
    return {"prices": rows}


@router.get("/history")
def history(
    fuel: str = Query(..., description="fuel type id, e.g. 'petrol_92'"),
    days: int = Query(730, ge=1, le=3650),
    source: str = Query("cpc"),
):
    if fuel not in fuel_mod.ALL_FUELS:
        raise HTTPException(status_code=400, detail=f"unknown fuel '{fuel}'")
    return {
        "fuel_type": fuel,
        "source": source,
        "days": days,
        "points": prices.history(fuel, days, source),
    }


@router.get("/changes")
def changes(source: str = Query("cpc"), limit: int = Query(200, ge=1, le=1000)):
    return {"source": source, "changes": prices.changes(source, limit)}
