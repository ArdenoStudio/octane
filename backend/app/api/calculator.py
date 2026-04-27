from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app import fuel as fuel_mod
from app.services import calculator

router = APIRouter(prefix="/v1/calculator", tags=["calculator"])


@router.get("/trip")
def trip(
    distance: float = Query(..., gt=0, description="distance in km"),
    efficiency: float = Query(..., gt=0, description="km per litre"),
    fuel: str = Query(..., description="fuel type id"),
):
    if fuel not in fuel_mod.ALL_FUELS:
        raise HTTPException(status_code=400, detail=f"unknown fuel '{fuel}'")
    try:
        return calculator.trip_cost(distance, efficiency, fuel)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
