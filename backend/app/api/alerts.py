from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app import fuel as fuel_mod
from app.api.schemas import AlertSubscribeIn
from app.services import alerts

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


@router.post("/subscribe")
def subscribe(payload: AlertSubscribeIn):
    if payload.fuel_type not in fuel_mod.ALL_FUELS:
        raise HTTPException(status_code=400, detail=f"unknown fuel '{payload.fuel_type}'")
    alert_id = alerts.subscribe(
        email=str(payload.email),
        fuel_type=payload.fuel_type,
        threshold=payload.threshold,
        direction=payload.direction,
    )
    return {"id": alert_id, "ok": True}
