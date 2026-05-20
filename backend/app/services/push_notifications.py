"""Web Push notification service using VAPID protocol."""
from __future__ import annotations

import json
import logging
from typing import TypedDict

from pywebpush import webpush, WebPushException

from app.config import get_settings
from app.db.connection import connect, cursor

log = logging.getLogger(__name__)


class PushSubscription(TypedDict):
    endpoint: str
    keys: dict[str, str]  # p256dh and auth


class PushPayload(TypedDict, total=False):
    title: str
    body: str
    icon: str
    badge: str
    url: str
    tag: str


def save_subscription(alert_id: int, subscription: PushSubscription) -> int:
    """Save a push subscription linked to an alert."""
    endpoint = subscription["endpoint"]
    p256dh = subscription["keys"]["p256dh"]
    auth = subscription["keys"]["auth"]

    with cursor() as cur:
        # Upsert: update if endpoint exists, else insert
        cur.execute(
            """
            INSERT INTO push_subscriptions (alert_id, endpoint, p256dh_key, auth_key)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (endpoint) DO UPDATE SET
                alert_id = EXCLUDED.alert_id,
                p256dh_key = EXCLUDED.p256dh_key,
                auth_key = EXCLUDED.auth_key
            RETURNING id
            """,
            (alert_id, endpoint, p256dh, auth),
        )
        row = cur.fetchone()
        return row["id"] if row else 0


def remove_subscription(endpoint: str) -> bool:
    """Remove a push subscription by endpoint."""
    with cursor() as cur:
        cur.execute(
            "DELETE FROM push_subscriptions WHERE endpoint = %s RETURNING id",
            (endpoint,),
        )
        return cur.fetchone() is not None


def get_subscriptions_for_alert(alert_id: int) -> list[dict]:
    """Get all push subscriptions for an alert."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, endpoint, p256dh_key, auth_key
                FROM push_subscriptions
                WHERE alert_id = %s
                """,
                (alert_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def send_push(subscription: PushSubscription, payload: PushPayload) -> tuple[bool, str | None]:
    """Send a push notification to a subscription."""
    s = get_settings()
    if not s.vapid_private_key or not s.vapid_public_key:
        log.warning("[push] VAPID keys not configured, skipping push")
        return False, "VAPID not configured"

    try:
        webpush(
            subscription_info={
                "endpoint": subscription["endpoint"],
                "keys": subscription["keys"],
            },
            data=json.dumps(payload),
            vapid_private_key=s.vapid_private_key,
            vapid_claims={"sub": s.vapid_subject},
        )
        return True, None
    except WebPushException as e:
        log.error("[push] WebPush failed: %s", e)
        # If subscription is expired/invalid, clean it up
        if e.response and e.response.status_code in (404, 410):
            remove_subscription(subscription["endpoint"])
            return False, "Subscription expired"
        return False, str(e)
    except Exception as e:
        log.exception("[push] Unexpected error sending push")
        return False, str(e)


def send_push_to_alert(
    alert_id: int,
    title: str,
    body: str,
    url: str | None = None,
    tag: str | None = None,
) -> int:
    """Send push notifications to all subscriptions for an alert.
    
    Returns the number of successful sends.
    """
    s = get_settings()
    subscriptions = get_subscriptions_for_alert(alert_id)
    if not subscriptions:
        return 0

    payload: PushPayload = {
        "title": title,
        "body": body,
        "icon": "/octane-o.svg",
        "badge": "/octane-o.svg",
    }
    if url:
        payload["url"] = url
    if tag:
        payload["tag"] = tag

    sent = 0
    for sub in subscriptions:
        subscription: PushSubscription = {
            "endpoint": sub["endpoint"],
            "keys": {
                "p256dh": sub["p256dh_key"],
                "auth": sub["auth_key"],
            },
        }
        ok, _ = send_push(subscription, payload)
        if ok:
            # Update last_used_at
            with cursor() as cur:
                cur.execute(
                    "UPDATE push_subscriptions SET last_used_at = NOW() WHERE id = %s",
                    (sub["id"],),
                )
            sent += 1
    return sent


def send_test_push(subscription: PushSubscription) -> tuple[bool, str | None]:
    """Send a test push notification."""
    payload: PushPayload = {
        "title": "Octane Test",
        "body": "Push notifications are working!",
        "icon": "/octane-o.svg",
        "tag": "test",
    }
    return send_push(subscription, payload)


def get_vapid_public_key() -> str | None:
    """Get the VAPID public key for client-side subscription."""
    s = get_settings()
    return s.vapid_public_key if s.vapid_public_key else None
