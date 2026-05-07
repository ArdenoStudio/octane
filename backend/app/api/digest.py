"""Weekly digest subscription endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr

from app.config import get_settings
from app.email_disposable import is_disposable_email
from app.rate_limits import limiter
from app.services import digest as digest_svc

router = APIRouter(prefix="/v1/digest", tags=["digest"])

_DIGEST_SUBSCRIBE_LIMIT = get_settings().rate_limit_writes


class DigestSubscribeIn(BaseModel):
    email: EmailStr


@router.post("/subscribe")
@limiter.limit(_DIGEST_SUBSCRIBE_LIMIT)
def subscribe(request: Request, payload: DigestSubscribeIn):
    if is_disposable_email(str(payload.email)):
        raise HTTPException(
            status_code=400,
            detail="Please use a permanent email address, not a disposable inbox.",
        )
    result = digest_svc.subscribe(str(payload.email))
    return {"ok": True, "id": result["id"]}


@router.delete("/unsubscribe")
def unsubscribe(token: str = Query(..., description="Unsubscribe token from digest email")):
    success = digest_svc.unsubscribe_by_token(token)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found or already unsubscribed.",
        )
    return {"ok": True, "message": "Unsubscribed from weekly digest."}
