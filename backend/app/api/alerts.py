from fastapi import APIRouter, Header, HTTPException, Query, Request

from app import fuel as fuel_mod
from app.api.schemas import AlertSubscribeIn, AlertUpdateIn
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


@router.get("/confirm")
def confirm(token: str = Query(..., description="Confirmation token from your signup email")):
    confirmed = alerts.confirm_by_token(token)
    if not confirmed:
        raise HTTPException(
            status_code=404,
            detail="Token not found or alert already confirmed.",
        )
    return {"ok": True, "message": "Your alert is now active. We'll email you when the price crosses your threshold."}


@router.post("/dispatch")
def dispatch(x_dispatch_secret: str | None = Header(None)):
    s = get_settings()
    if not s.dispatch_secret or x_dispatch_secret != s.dispatch_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    fired = alerts.dispatch_pending()
    return {"ok": True, "fired": fired}


@router.get("/manage")
def get_manage(token: str = Query(..., description="Unsubscribe token from your alert email")):
    alert = alerts.get_by_token(token)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found or already cancelled.")
    return alert


@router.patch("/manage")
def update_manage(
    payload: AlertUpdateIn,
    token: str = Query(..., description="Unsubscribe token from your alert email"),
):
    try:
        updated = alerts.update_by_token(token, payload.threshold, payload.direction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail="Alert not found or already cancelled.")
    return {"ok": True}


@router.delete("/manage")
def unsubscribe(token: str = Query(..., description="Unsubscribe token from your alert email")):
    success = alerts.unsubscribe_by_token(token)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Alert not found or already unsubscribed.",
        )
    return {"ok": True, "message": "Unsubscribed successfully. You won't receive further emails for this alert."}
