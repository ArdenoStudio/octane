"""Alert subscriptions + dispatch."""
from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from app.config import get_settings
from app.db.connection import connect, cursor
from app.services import prices

log = logging.getLogger(__name__)


def subscribe(email: str, fuel_type: str, threshold: float, direction: str) -> int:
    if direction not in ("above", "below"):
        raise ValueError("direction must be 'above' or 'below'")
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts (email, fuel_type, threshold, direction)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (email, fuel_type, threshold, direction),
        )
        return cur.fetchone()["id"]


def get_by_token(token: str) -> dict | None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, fuel_type, threshold, direction, active, created_at
                FROM alerts WHERE unsubscribe_token = %s
                """,
                (token,),
            )
            r = cur.fetchone()
    if not r:
        return None
    row = dict(r)
    row["created_at"] = row["created_at"].isoformat()
    row["threshold"] = float(row["threshold"])
    return row


def unsubscribe_by_token(token: str) -> bool:
    with cursor() as cur:
        cur.execute(
            """
            UPDATE alerts SET active = FALSE
            WHERE unsubscribe_token = %s AND active = TRUE
            RETURNING id
            """,
            (token,),
        )
        return cur.fetchone() is not None


def list_active() -> list[dict]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, fuel_type, threshold, direction,
                       last_fired_at, unsubscribe_token
                FROM alerts WHERE active = TRUE
                """
            )
            return [dict(r) for r in cur.fetchall()]


def _send_email(to_email: str, subject: str, body: str) -> bool:
    s = get_settings()
    if not s.smtp_host or not s.smtp_user:
        log.info("[alert] would send to %s: %s", to_email, subject)
        return False
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = s.alert_from_email
    msg["To"] = to_email
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(s.smtp_user, s.smtp_pass)
            smtp.send_message(msg)
        return True
    except Exception:  # noqa: BLE001
        log.exception("smtp send failed")
        return False


def dispatch_pending() -> int:
    """Find alerts whose threshold is currently met and notify subscribers."""
    s = get_settings()
    fired = 0
    for alert in list_active():
        latest = prices.latest_for(alert["fuel_type"])
        if not latest:
            continue
        price = latest["price_lkr"]
        threshold = float(alert["threshold"])
        triggered = (
            (alert["direction"] == "above" and price >= threshold)
            or (alert["direction"] == "below" and price <= threshold)
        )
        if not triggered:
            continue
        manage_url = f"{s.site_url}/manage?token={alert['unsubscribe_token']}"
        subject = f"Octane alert: {alert['fuel_type']} @ LKR {price}"
        body = (
            f"Your Octane alert triggered.\n\n"
            f"Fuel:      {alert['fuel_type']}\n"
            f"Price now: LKR {price}\n"
            f"Threshold: {alert['direction']} LKR {threshold}\n"
            f"Recorded:  {latest['recorded_at']}\n\n"
            f"Manage or unsubscribe this alert:\n"
            f"{manage_url}\n\n"
            f"— Octane (octane.lk)"
        )
        if _send_email(alert["email"], subject, body):
            with cursor() as cur:
                cur.execute(
                    "UPDATE alerts SET last_fired_at = %s WHERE id = %s",
                    (datetime.now(timezone.utc), alert["id"]),
                )
            fired += 1
    return fired
