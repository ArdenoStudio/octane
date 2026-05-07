from fastapi import APIRouter, HTTPException, Query, Request

from app import fuel as fuel_mod
from app.api.schemas import AlertSubscribeIn
from app.config import get_settings
from app.email_disposable import is_disposable_email
from app.rate_limits import limiter
from app.services import alerts

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])

_ALERT_SUBSCRIBE_LIMIT = get_settings().rate_limit_writes


@router.post("/subscribe")
@limiter.limit(_ALERT_SUBSCRIBE_LIMIT)
def subscribe(request: Request, payload: AlertSubscribeIn):
    if is_disposable_email(str(payload.email)):
        raise HTTPException(
            status_code=400,
            detail="Please use a permanent email address, not a disposable inbox.",
        )
    if payload.fuel_type not in fuel_mod.ALL_FUELS:
        raise HTTPException(status_code=400, detail=f"unknown fuel '{payload.fuel_type}'")
    alert_id = alerts.subscribe(
        email=str(payload.email),
        fuel_type=payload.fuel_type,
        threshold=payload.threshold,
        direction=payload.direction,
        telegram_chat_id=payload.telegram_chat_id,
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
