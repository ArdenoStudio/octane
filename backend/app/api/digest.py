"""Weekly digest subscription endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr

from app.services import digest as digest_svc

router = APIRouter(prefix="/v1/digest", tags=["digest"])


class DigestSubscribeIn(BaseModel):
    email: EmailStr


@router.post("/subscribe")
def subscribe(payload: DigestSubscribeIn):
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
