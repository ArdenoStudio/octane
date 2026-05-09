"""Alert subscriptions + dispatch."""
from __future__ import annotations

import logging
import smtplib
import urllib.request
import urllib.parse
import json as _json
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings
from app.db.connection import connect, cursor
from app.services import prices

log = logging.getLogger(__name__)

MAX_SEND_ATTEMPTS = 5

# ---------------------------------------------------------------------------
# Human-readable fuel labels
# ---------------------------------------------------------------------------
_FUEL_LABELS: dict[str, str] = {
    "petrol_92":   "Petrol 92",
    "petrol_95":   "Petrol 95",
    "auto_diesel": "Auto Diesel",
    "super_diesel": "Super Diesel",
    "kerosene":    "Kerosene",
}


# ---------------------------------------------------------------------------
# Subscription management
# ---------------------------------------------------------------------------

def subscribe(
    email: str,
    fuel_type: str,
    threshold: float,
    direction: str,
    telegram_chat_id: str | None = None,
) -> int:
    if direction not in ("above", "below"):
        raise ValueError("direction must be 'above' or 'below'")
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts (email, fuel_type, threshold, direction, telegram_chat_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (email, fuel_type, threshold, direction, telegram_chat_id or None),
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
                       last_fired_at, unsubscribe_token,
                       send_attempts, last_send_error, telegram_chat_id
                FROM alerts WHERE active = TRUE
                """
            )
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Email (HTML)
# ---------------------------------------------------------------------------

_EMAIL_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0c0c0d;font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0c0c0d;">
  <tr><td align="center" style="padding:40px 16px;">
    <table width="560" cellpadding="0" cellspacing="0" style="max-width:100%;">

      <!-- Header -->
      <tr>
        <td style="padding:0 0 24px;">
          <span style="font-size:18px;font-weight:800;letter-spacing:-0.04em;color:#ffffff;">Octane</span>
        </td>
      </tr>

      <!-- Card -->
      <tr>
        <td style="background:#18181b;border:1px solid #27272a;border-radius:16px;overflow:hidden;">
          <table width="100%" cellpadding="0" cellspacing="0">

            <!-- Amber accent bar -->
            <tr>
              <td style="background:#f59e0b;height:3px;font-size:0;line-height:0;">&nbsp;</td>
            </tr>

            <!-- Body -->
            <tr>
              <td style="padding:32px 32px 28px;">

                <!-- Badge -->
                <table cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                  <tr>
                    <td style="background:#292524;border:1px solid #44403c;border-radius:6px;padding:4px 10px;">
                      <span style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#f59e0b;">&#9679;&nbsp; Price alert triggered</span>
                    </td>
                  </tr>
                </table>

                <!-- Headline -->
                <p style="margin:0 0 6px;font-size:13px;font-weight:500;color:#71717a;">{fuel_name}</p>
                <p style="margin:0 0 28px;font-size:42px;font-weight:800;letter-spacing:-0.04em;color:#ffffff;line-height:1;">LKR&nbsp;{price}</p>

                <!-- Divider -->
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                  <tr><td style="background:#27272a;height:1px;font-size:0;line-height:0;"></td></tr>
                </table>

                <!-- Stats row -->
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
                  <tr>
                    <td width="50%" style="vertical-align:top;">
                      <p style="margin:0 0 4px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:#52525b;">Your threshold</p>
                      <p style="margin:0;font-size:15px;font-weight:700;color:#a1a1aa;">{direction_cap} LKR&nbsp;{threshold}</p>
                    </td>
                    <td width="50%" style="vertical-align:top;">
                      <p style="margin:0 0 4px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:#52525b;">Recorded on</p>
                      <p style="margin:0;font-size:15px;font-weight:700;color:#a1a1aa;">{recorded_at}</p>
                    </td>
                  </tr>
                </table>

                <!-- CTA -->
                <a href="{manage_url}"
                   style="display:inline-block;background:#f59e0b;color:#0c0c0d;text-decoration:none;font-size:13px;font-weight:700;padding:11px 22px;border-radius:8px;letter-spacing:-0.01em;">
                  Manage this alert &rarr;
                </a>

              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="padding:16px 32px;background:#111113;border-top:1px solid #27272a;">
                <p style="margin:0;font-size:11px;color:#52525b;line-height:1.6;">
                  You set up this alert on
                  <a href="https://octane-smoky.vercel.app" style="color:#71717a;text-decoration:none;">Octane</a>.
                  &nbsp;&middot;&nbsp;
                  <a href="{manage_url}" style="color:#71717a;text-decoration:underline;">Unsubscribe</a>
                </p>
              </td>
            </tr>

          </table>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>
"""

_EMAIL_TEXT = """\
Octane price alert triggered
=============================

{fuel_name} is now LKR {price}.

Your threshold: {direction} LKR {threshold}
Recorded: {recorded_at}

Manage or unsubscribe:
{manage_url}

— Octane (octane.lk)
"""


def _send_email(to_email: str, subject: str, body: str) -> tuple[bool, str | None]:
    """Send a plain-text email. Returns (sent, error_or_None).

    Returns (False, None) when SMTP is not configured — not treated as a failure.
    """
    s = get_settings()
    if not s.smtp_host or not s.smtp_user:
        log.info("[alert] would send to %s: %s", to_email, subject)
        return False, None
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = s.alert_from_email
    msg["To"] = to_email
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(s.smtp_user, s.smtp_pass)
            smtp.send_message(msg)
        return True, None
    except Exception as exc:  # noqa: BLE001
        log.exception("smtp send failed")
        return False, str(exc)[:500]


def _send_html_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> tuple[bool, str | None]:
    """Send a multipart HTML+text email."""
    s = get_settings()
    if not s.smtp_host or not s.smtp_user:
        log.info("[alert] would send to %s: %s", to_email, subject)
        return False, None
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = s.alert_from_email
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(s.smtp_user, s.smtp_pass)
            smtp.send_message(msg)
        return True, None
    except Exception as exc:  # noqa: BLE001
        log.exception("smtp send failed")
        return False, str(exc)[:500]


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def _send_telegram(chat_id: str, text: str) -> tuple[bool, str | None]:
    """Send a message via Telegram Bot API. Returns (sent, error_or_None)."""
    s = get_settings()
    if not s.telegram_bot_token:
        log.info("[alert] telegram not configured, skipping chat_id=%s", chat_id)
        return False, None
    url = f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage"
    payload = _json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = _json.loads(resp.read())
        if not result.get("ok"):
            err = result.get("description", "unknown error")
            log.error("telegram send failed for chat_id=%s: %s", chat_id, err)
            return False, err
        return True, None
    except Exception as exc:  # noqa: BLE001
        log.exception("telegram send failed for chat_id=%s", chat_id)
        return False, str(exc)[:500]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def dispatch_pending() -> int:
    """Find alerts whose threshold is currently met and notify subscribers."""
    s = get_settings()
    fired = 0
    for alert in list_active():
        if (alert.get("send_attempts") or 0) >= MAX_SEND_ATTEMPTS:
            log.warning(
                "alert %s skipped after %d failed attempts (last error: %s)",
                alert["id"],
                alert["send_attempts"],
                alert.get("last_send_error"),
            )
            continue

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

        fuel_name = _FUEL_LABELS.get(alert["fuel_type"], alert["fuel_type"])
        manage_url = f"{s.site_url}/manage?token={alert['unsubscribe_token']}"
        recorded_at = latest["recorded_at"]
        price_fmt = int(price) if price == int(price) else price
        threshold_fmt = int(threshold) if threshold == int(threshold) else threshold

        # ── Email ────────────────────────────────────────────────────────────
        subject = f"Octane alert: {fuel_name} is now LKR {price_fmt}"
        html_body = _EMAIL_HTML.format(
            fuel_name=fuel_name,
            price=price_fmt,
            direction=alert["direction"],
            direction_cap=alert["direction"].capitalize(),
            threshold=threshold_fmt,
            recorded_at=recorded_at,
            manage_url=manage_url,
        )
        text_body = _EMAIL_TEXT.format(
            fuel_name=fuel_name,
            price=price_fmt,
            direction=alert["direction"],
            threshold=threshold_fmt,
            recorded_at=recorded_at,
            manage_url=manage_url,
        )
        email_sent, email_err = _send_html_email(
            alert["email"], subject, html_body, text_body
        )

        # ── Telegram ─────────────────────────────────────────────────────────
        tg_sent = False
        tg_err: str | None = None
        chat_id = alert.get("telegram_chat_id")
        if chat_id:
            tg_text = (
                f"🔔 <b>Octane Price Alert</b>\n\n"
                f"<b>{fuel_name}</b> is now <b>LKR {price}</b>\n"
                f"Your threshold: {alert['direction']} LKR {threshold}\n"
                f"Recorded: {recorded_at}\n\n"
                f'<a href="{manage_url}">Manage this alert</a>'
            )
            tg_sent, tg_err = _send_telegram(chat_id, tg_text)

        # ── Mark fired / track failures ───────────────────────────────────────
        delivery_ok = email_sent or tg_sent
        error = email_err or tg_err
        if delivery_ok:
            with cursor() as cur:
                cur.execute(
                    """
                    UPDATE alerts
                    SET last_fired_at = %s, send_attempts = 0, last_send_error = NULL
                    WHERE id = %s
                    """,
                    (datetime.now(timezone.utc), alert["id"]),
                )
            fired += 1
        elif error:
            with cursor() as cur:
                cur.execute(
                    """
                    UPDATE alerts
                    SET send_attempts = send_attempts + 1, last_send_error = %s
                    WHERE id = %s
                    """,
                    (error, alert["id"]),
                )
    return fired
