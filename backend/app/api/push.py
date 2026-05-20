"""Push notification subscription API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.rate_limits import limiter
from app.services import push_notifications

router = APIRouter(prefix="/v1/push", tags=["push"])


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class SubscribeRequest(BaseModel):
    alert_id: int
    endpoint: str
    keys: PushKeys


class UnsubscribeRequest(BaseModel):
    endpoint: str


class TestPushRequest(BaseModel):
    endpoint: str
    keys: PushKeys


@router.get("/vapid-key")
def get_vapid_key():
    """Get the VAPID public key for client-side push subscription."""
    key = push_notifications.get_vapid_public_key()
    if not key:
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    return {"public_key": key}


@router.post("/subscribe")
@limiter.limit("10/minute")
def subscribe_push(req: SubscribeRequest, request: Request):
    """Subscribe to push notifications for an alert."""
    subscription = {
        "endpoint": req.endpoint,
        "keys": {"p256dh": req.keys.p256dh, "auth": req.keys.auth},
    }
    sub_id = push_notifications.save_subscription(req.alert_id, subscription)
    return {"ok": True, "id": sub_id}


@router.delete("/unsubscribe")
def unsubscribe_push(req: UnsubscribeRequest):
    """Unsubscribe from push notifications."""
    removed = push_notifications.remove_subscription(req.endpoint)
    return {"ok": removed}


@router.post("/test")
@limiter.limit("5/minute")
def test_push(req: TestPushRequest, request: Request):
    """Send a test push notification."""
    subscription = {
        "endpoint": req.endpoint,
        "keys": {"p256dh": req.keys.p256dh, "auth": req.keys.auth},
    }
    ok, error = push_notifications.send_test_push(subscription)
    if not ok:
        raise HTTPException(status_code=500, detail=error or "Failed to send push")
    return {"ok": True, "message": "Test notification sent"}
