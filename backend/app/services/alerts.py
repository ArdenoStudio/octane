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
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;">
  <tr><td align="center" style="padding:48px 16px 56px;">
    <table width="580" cellpadding="0" cellspacing="0" style="max-width:100%;">

      <!-- Logo -->
      <tr>
        <td align="center" style="padding-bottom:28px;">
          <img src="https://octane-smoky.vercel.app/octane-logo-nav.svg"
               width="96" height="36" alt="Octane"
               style="display:block;border:0;outline:none;">
        </td>
      </tr>

      <!-- Card -->
      <tr>
        <td style="background:#ffffff;border-radius:20px;overflow:hidden;
                   box-shadow:0 2px 4px rgba(80,60,20,0.06),0 16px 56px rgba(80,60,20,0.12);">
          <table width="100%" cellpadding="0" cellspacing="0">

            <!-- Amber bar -->
            <tr><td style="background:#f59e0b;height:4px;font-size:0;line-height:0;">&nbsp;</td></tr>

            <!-- Hero -->
            <tr>
              <td style="padding:36px 40px 24px;">

                <!-- Eyebrow -->
                <p style="margin:0 0 22px;font-size:10px;font-weight:600;letter-spacing:0.16em;
                           text-transform:uppercase;color:#c4b99a;text-align:center;">Price alert triggered</p>

                <!-- Fuel + delta -->
                <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:10px;">
                  <tr>
                    <td style="vertical-align:middle;">
                      <p style="margin:0;font-size:14px;font-weight:500;color:#8c7d66;letter-spacing:-0.01em;">{fuel_name}</p>
                    </td>
                    <td align="right" style="vertical-align:middle;">{delta_badge}</td>
                  </tr>
                </table>

                <!-- Price -->
                <p style="margin:0 0 28px;font-size:76px;font-weight:800;
                           color:#1a1208;line-height:0.9;font-variant-numeric:tabular-nums;">
                  <span style="font-size:28px;font-weight:700;color:#c4b99a;
                               vertical-align:middle;margin-right:6px;">LKR</span>{price}</p>

              </td>
            </tr>

            <!-- Chart — full bleed -->
            <tr>
              <td style="padding:0;line-height:0;font-size:0;background:#fffcf5;">{chart_html}</td>
            </tr>

            <!-- Warm divider -->
            <tr><td style="background:#ede8df;height:1px;font-size:0;line-height:0;"></td></tr>

            <!-- Details -->
            <tr>
              <td style="padding:26px 40px 28px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td width="50%" style="vertical-align:top;">
                      <p style="margin:0 0 5px;font-size:10px;font-weight:600;letter-spacing:0.14em;
                                 text-transform:uppercase;color:#c4b99a;">Your threshold</p>
                      <p style="margin:0;font-size:15px;font-weight:600;color:#2d2319;letter-spacing:-0.02em;">{direction_cap} LKR&nbsp;{threshold}</p>
                    </td>
                    <td width="50%" style="vertical-align:top;">
                      <p style="margin:0 0 5px;font-size:10px;font-weight:600;letter-spacing:0.14em;
                                 text-transform:uppercase;color:#c4b99a;">Recorded on</p>
                      <p style="margin:0;font-size:15px;font-weight:600;color:#2d2319;letter-spacing:-0.02em;">{recorded_at}</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- CTA -->
            <tr>
              <td style="padding:0 40px 38px;">
                <a href="{manage_url}"
                   style="display:inline-block;background:#f59e0b;color:#1a0f00;text-decoration:none;
                          font-size:13px;font-weight:700;padding:13px 28px;border-radius:10px;
                          letter-spacing:0.01em;">
                  Manage this alert &rarr;
                </a>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="padding:16px 40px;background:#faf7f2;border-top:1px solid #ede8df;">
                <p style="margin:0;font-size:11px;color:#c4b99a;line-height:1.7;">
                  You set up this alert on
                  <a href="https://octane-smoky.vercel.app" style="color:#f59e0b;text-decoration:none;font-weight:600;">Octane</a>.
                  &nbsp;&middot;&nbsp;
                  <a href="{manage_url}" style="color:#c4b99a;text-decoration:underline;">Unsubscribe</a>
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
# Mini chart
# ---------------------------------------------------------------------------

def _mini_chart(fuel_type: str, threshold: float) -> tuple[str, float | None]:
    """Return (svg_html, delta_lkr). Uses 12-month history with a threshold line."""
    delta: float | None = None
    vals: list[float] = []

    # Primary: 12-month history, deduplicated by price change
    hist = prices.history(fuel_type, days=365)
    if len(hist) >= 2:
        deduped = [hist[0]]
        for r in hist[1:]:
            if r["price_lkr"] != deduped[-1]["price_lkr"]:
                deduped.append(r)
        if hist[-1]["price_lkr"] != deduped[-1]["price_lkr"]:
            deduped.append(hist[-1])
        if len(deduped) >= 2:
            vals = [r["price_lkr"] for r in deduped[-8:]]
            delta = vals[-1] - vals[-2]

    # Fallback: change events
    if len(vals) < 2:
        all_changes = prices.changes(limit=200)
        fuel_changes = [r for r in all_changes if r["fuel_type"] == fuel_type]
        fuel_changes = list(reversed(fuel_changes))[-8:]
        if len(fuel_changes) < 2:
            return "", None
        vals = [r["price_lkr"] for r in fuel_changes]
        delta = fuel_changes[-1]["delta_lkr"]

    W, H, PAD = 580, 72, 10
    raw_lo = min(min(vals), threshold)
    raw_hi = max(max(vals), threshold)
    pad_amt = (raw_hi - raw_lo) * 0.18 or 15
    lo, hi = raw_lo - pad_amt, raw_hi + pad_amt
    span = hi - lo
    n = len(vals)

    def px(i: int) -> float:
        return PAD + i * (W - 2 * PAD) / (n - 1)

    def py(v: float) -> float:
        return PAD + (1 - (v - lo) / span) * (H - 2 * PAD)

    pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(vals))
    lx, ly = f"{px(n - 1):.1f}", f"{py(vals[-1]):.1f}"
    fill = (
        f"M{px(0):.1f},{py(vals[0]):.1f} "
        + " ".join(f"L{px(i):.1f},{py(v):.1f}" for i, v in enumerate(vals))
        + f" L{px(n - 1):.1f},{H} L{px(0):.1f},{H} Z"
    )
    ty = py(threshold)
    t_label = int(threshold) if threshold == int(threshold) else threshold

    svg = (
        f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'style="display:block;width:100%;" xmlns="http://www.w3.org/2000/svg">'
        f'<defs>'
        f'<linearGradient id="oct-g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#f59e0b" stop-opacity="0.22"/>'
        f'<stop offset="100%" stop-color="#f59e0b" stop-opacity="0"/>'
        f'</linearGradient>'
        f'</defs>'
        # Threshold dashed line
        f'<line x1="{PAD}" y1="{ty:.1f}" x2="{W - PAD}" y2="{ty:.1f}" '
        f'stroke="#c4b99a" stroke-width="1" stroke-dasharray="4 3"/>'
        # Threshold label (right-aligned, above the line)
        f'<text x="{W - PAD - 3}" y="{ty - 4:.1f}" font-size="8.5" fill="#c4b99a" '
        f'text-anchor="end" font-family="-apple-system,BlinkMacSystemFont,sans-serif">'
        f'LKR {t_label}</text>'
        # Gradient fill + line
        f'<path d="{fill}" fill="url(#oct-g)"/>'
        f'<polyline points="{pts}" fill="none" stroke="#f59e0b" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{lx}" cy="{ly}" r="4.5" fill="#fffcf5" stroke="#f59e0b" stroke-width="2"/>'
        f'</svg>'
    )
    return svg, delta


def _delta_badge(delta: float | None) -> str:
    if delta is None:
        return ""
    delta_fmt = int(delta) if delta == int(delta) else delta
    sign = "+" if delta >= 0 else ""
    arrow = "&#9650;" if delta >= 0 else "&#9660;"
    bg = "#fef2f2" if delta >= 0 else "#f0fdf4"
    fg = "#dc2626" if delta >= 0 else "#16a34a"
    return (
        f'<span style="display:inline-block;font-size:11px;font-weight:700;'
        f'color:{fg};background:{bg};padding:3px 8px;border-radius:6px;'
        f'letter-spacing:-0.01em;">{arrow}&nbsp;{sign}{delta_fmt}</span>'
    )


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
        chart_html, delta = _mini_chart(alert["fuel_type"], threshold)
        try:
            from datetime import datetime as _dt
            _d = _dt.strptime(recorded_at, "%Y-%m-%d")
            recorded_at_fmt = f"{_d.day} {_d.strftime('%B %Y')}"
        except Exception:
            recorded_at_fmt = recorded_at

        # ── Email ────────────────────────────────────────────────────────────
        subject = f"Octane alert: {fuel_name} is now LKR {price_fmt}"
        html_body = _EMAIL_HTML.format(
            fuel_name=fuel_name,
            price=price_fmt,
            direction=alert["direction"],
            direction_cap=alert["direction"].capitalize(),
            threshold=threshold_fmt,
            recorded_at=recorded_at_fmt,
            manage_url=manage_url,
            chart_html=chart_html,
            delta_badge=_delta_badge(delta),
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
