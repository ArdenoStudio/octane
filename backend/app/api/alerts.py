from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

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


@router.get("/manage")
def get_manage(token: str = Query(..., description="Unsubscribe token from your alert email")):
    alert = alerts.get_by_token(token)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found or already cancelled.")
    return alert


@router.delete("/manage")
def unsubscribe(token: str = Query(..., description="Unsubscribe token from your alert email")):
    success = alerts.unsubscribe_by_token(token)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Alert not found or already unsubscribed.",
        )
    return {"ok": True, "message": "Unsubscribed successfully. You won't receive further emails for this alert."}
