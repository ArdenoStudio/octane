from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app import fuel as fuel_mod
from app.services import comparison

router = APIRouter(prefix="/v1/comparison", tags=["comparison"])


@router.get("/world")
def world(fuel: str = Query("petrol_95")):
    if fuel not in fuel_mod.ALL_FUELS:
        raise HTTPException(status_code=400, detail=f"unknown fuel '{fuel}'")
    return comparison.world_comparison(fuel)
