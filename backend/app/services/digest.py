"""Weekly price digest: subscription management + email dispatch."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.db.connection import connect, cursor
from app.services import prices
from app.services.alerts import _send_html_email

log = logging.getLogger(__name__)

_FUEL_LABELS: dict[str, str] = {
    "petrol_92":    "Petrol 92",
    "petrol_95":    "Petrol 95",
    "auto_diesel":  "Auto Diesel",
    "super_diesel": "Super Diesel",
    "kerosene":     "Kerosene",
}

_FUEL_ORDER = ["petrol_92", "petrol_95", "auto_diesel", "super_diesel", "kerosene"]

# ---------------------------------------------------------------------------
# Subscriber management
# ---------------------------------------------------------------------------

def subscribe(email: str) -> dict:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO digest_subscribers (email)
            VALUES (%s)
            ON CONFLICT (email) DO UPDATE
              SET active = TRUE
            RETURNING id, active
            """,
            (email,),
        )
        row = cur.fetchone()
    return {"id": row["id"], "already_active": row["active"]}


def unsubscribe_by_token(token: str) -> bool:
    with cursor() as cur:
        cur.execute(
            """
            UPDATE digest_subscribers SET active = FALSE
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
                "SELECT id, email, unsubscribe_token FROM digest_subscribers WHERE active = TRUE"
            )
            return [dict(r) for r in cur.fetchall()]


def _mark_sent(subscriber_id: int) -> None:
    with cursor() as cur:
        cur.execute(
            "UPDATE digest_subscribers SET last_sent_at = %s WHERE id = %s",
            (datetime.now(timezone.utc), subscriber_id),
        )


# ---------------------------------------------------------------------------
# Email template
# ---------------------------------------------------------------------------

def _build_price_rows(latest: list[dict]) -> str:
    """Build HTML table rows for each CPC fuel price."""
    by_fuel: dict[str, dict] = {r["fuel_type"]: r for r in latest if r["source"] == "cpc"}

    # Get 7-day change for each fuel
    changes_7d: dict[str, float | None] = {}
    for fuel_id in _FUEL_ORDER:
        pts = prices.history(fuel_id, 14, "cpc")
        if len(pts) >= 2:
            # Find a point ~7 days ago
            current = pts[-1]["price_lkr"] if pts else None
            week_ago = pts[0]["price_lkr"] if pts else None
            if current is not None and week_ago is not None and week_ago != 0:
                changes_7d[fuel_id] = ((current - week_ago) / week_ago) * 100
            else:
                changes_7d[fuel_id] = None
        else:
            changes_7d[fuel_id] = None

    rows_html = ""
    for fuel_id in _FUEL_ORDER:
        p = by_fuel.get(fuel_id)
        if not p:
            continue
        label = _FUEL_LABELS.get(fuel_id, fuel_id)
        price = p["price_lkr"]
        pct = changes_7d.get(fuel_id)
        if pct is None:
            delta_str = '<span style="color:#a1a1aa;">—</span>'
        elif pct > 0.01:
            delta_str = f'<span style="color:#dc2626;font-weight:600;">▲ {pct:+.1f}%</span>'
        elif pct < -0.01:
            delta_str = f'<span style="color:#16a34a;font-weight:600;">▼ {pct:.1f}%</span>'
        else:
            delta_str = '<span style="color:#71717a;">unchanged</span>'

        rows_html += f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid #f4f4f5;font-size:13px;color:#3f3f46;">{label}</td>
          <td style="padding:12px 16px;border-bottom:1px solid #f4f4f5;font-size:15px;font-weight:700;color:#09090b;text-align:right;">LKR&nbsp;{price:.2f}</td>
          <td style="padding:12px 16px;border-bottom:1px solid #f4f4f5;font-size:12px;text-align:right;">{delta_str}</td>
        </tr>"""

    return rows_html


_DIGEST_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;">
  <tr><td align="center" style="padding:40px 16px;">
    <table width="580" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #e4e4e7;border-radius:16px;overflow:hidden;max-width:100%;">

      <!-- Header -->
      <tr>
        <td style="padding:24px 32px 20px;border-bottom:3px solid #f59e0b;">
          <span style="font-size:20px;font-weight:800;letter-spacing:-0.04em;color:#09090b;">Octane</span>
          <span style="font-size:11px;font-weight:500;color:#a1a1aa;margin-left:8px;">Weekly Fuel Price Digest</span>
        </td>
      </tr>

      <!-- Week label -->
      <tr>
        <td style="padding:24px 32px 8px;">
          <p style="margin:0;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#a1a1aa;">Week of {week_of}</p>
          <h1 style="margin:8px 0 0;font-size:22px;font-weight:800;letter-spacing:-0.04em;color:#09090b;">Sri Lanka fuel prices at a glance.</h1>
        </td>
      </tr>

      <!-- Price table -->
      <tr>
        <td style="padding:16px 32px 8px;">
          <table cellpadding="0" cellspacing="0" width="100%" style="border:1px solid #e4e4e7;border-radius:12px;overflow:hidden;">
            <thead>
              <tr style="background:#f9f9f9;">
                <th style="padding:10px 16px;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#a1a1aa;text-align:left;">Fuel</th>
                <th style="padding:10px 16px;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#a1a1aa;text-align:right;">Price (LKR/L)</th>
                <th style="padding:10px 16px;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#a1a1aa;text-align:right;">7-day change</th>
              </tr>
            </thead>
            <tbody>
              {price_rows}
            </tbody>
          </table>
        </td>
      </tr>

      <!-- Note -->
      <tr>
        <td style="padding:12px 32px 24px;">
          <p style="margin:0;font-size:12px;color:#a1a1aa;">Source: Ceylon Petroleum Corporation (CPC). Prices in LKR per litre.</p>
        </td>
      </tr>

      <!-- CTA -->
      <tr>
        <td style="padding:0 32px 32px;">
          <a href="https://octane.lk" style="display:inline-block;background:#f59e0b;color:#09090b;text-decoration:none;font-size:13px;font-weight:700;padding:10px 20px;border-radius:8px;">View live prices &amp; history →</a>
        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td style="padding:18px 32px;background:#f9f9f9;border-top:1px solid #e4e4e7;">
          <p style="margin:0;font-size:11px;color:#a1a1aa;line-height:1.6;">
            You're receiving this weekly digest because you subscribed on
            <a href="https://octane.lk" style="color:#f59e0b;text-decoration:none;">octane.lk</a>.
            &nbsp;·&nbsp;
            <a href="{unsub_url}" style="color:#a1a1aa;text-decoration:underline;">Unsubscribe</a>
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>
"""

_DIGEST_TEXT = """\
Octane Weekly Fuel Price Digest — Week of {week_of}
=====================================================

Sri Lanka CPC Fuel Prices (LKR per litre):

{price_text}

Source: Ceylon Petroleum Corporation

View live prices, history & world comparison:
https://octane.lk

Unsubscribe: {unsub_url}
"""


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def send_weekly_digest() -> int:
    """Compose and send the weekly digest to all active subscribers."""
    from app.config import get_settings
    s = get_settings()

    # Current prices
    latest = prices.latest_all()
    by_fuel = {r["fuel_type"]: r for r in latest if r["source"] == "cpc"}

    if not by_fuel:
        log.warning("digest: no CPC prices found, skipping")
        return 0

    week_of = datetime.now(timezone.utc).strftime("%B %d, %Y")
    price_rows = _build_price_rows(latest)

    # Plain text version
    price_text_lines = []
    for fuel_id in _FUEL_ORDER:
        p = by_fuel.get(fuel_id)
        if p:
            label = _FUEL_LABELS.get(fuel_id, fuel_id)
            price_text_lines.append(f"  {label:<16} LKR {p['price_lkr']:.2f}")
    price_text = "\n".join(price_text_lines)

    subject = f"Octane Weekly: Sri Lanka fuel prices — {week_of}"

    sent = 0
    for sub in list_active():
        unsub_url = f"{s.site_url}/digest/unsubscribe?token={sub['unsubscribe_token']}"
        html_body = _DIGEST_HTML.format(
            week_of=week_of,
            price_rows=price_rows,
            unsub_url=unsub_url,
        )
        text_body = _DIGEST_TEXT.format(
            week_of=week_of,
            price_text=price_text,
            unsub_url=unsub_url,
        )
        ok, err = _send_html_email(sub["email"], subject, html_body, text_body)
        if ok:
            _mark_sent(sub["id"])
            sent += 1
        elif err:
            log.error("digest send failed for %s: %s", sub["email"], err)

    log.info("weekly digest: sent %d / %d", sent, len(list_active()))
    return sent
