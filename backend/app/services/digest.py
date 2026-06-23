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
            delta_str = '<span style="color:#c4b99a;">—</span>'
        elif pct > 0.01:
            delta_str = f'<span style="display:inline-block;font-size:11px;font-weight:700;color:#dc2626;background:#fef2f2;padding:2px 7px;border-radius:5px;">&#9650;&nbsp;{pct:+.1f}%</span>'
        elif pct < -0.01:
            delta_str = f'<span style="display:inline-block;font-size:11px;font-weight:700;color:#16a34a;background:#f0fdf4;padding:2px 7px;border-radius:5px;">&#9660;&nbsp;{pct:.1f}%</span>'
        else:
            delta_str = '<span style="color:#c4b99a;">unchanged</span>'

        rows_html += f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:13px;color:#6b5e4e;font-family:'Cal Sans',-apple-system,sans-serif;">{label}</td>
          <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:15px;font-weight:700;color:#1a1208;text-align:right;font-family:'Cal Sans',-apple-system,sans-serif;">LKR&nbsp;{price:.2f}</td>
          <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:12px;text-align:right;font-family:'Cal Sans',-apple-system,sans-serif;">{delta_str}</td>
        </tr>"""

    return rows_html


_DIGEST_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <style>@import url('https://fonts.cdnfonts.com/css/cal-sans');</style>
</head>
<body style="margin:0;padding:0;background:#ffffff;font-family:'Cal Sans',-apple-system,BlinkMacSystemFont,'Helvetica Neue',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;">
  <tr><td align="center" style="padding:48px 16px 56px;">
    <table width="580" cellpadding="0" cellspacing="0" style="max-width:100%;">

      <!-- Logo -->
      <tr>
        <td align="center" style="padding-bottom:28px;">
          <img src="{site_url}/octane-logo-nav.svg"
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

            <!-- Week label -->
            <tr>
              <td style="padding:36px 40px 20px;">
                <p style="margin:0 0 8px;font-size:10px;font-weight:600;letter-spacing:0.16em;text-transform:uppercase;color:#c4b99a;font-family:'Cal Sans',-apple-system,sans-serif;">Week of {week_of}</p>
                <h1 style="margin:0;font-size:24px;font-weight:800;letter-spacing:-0.03em;color:#1a1208;line-height:1.2;font-family:'Cal Sans',-apple-system,sans-serif;">Sri Lanka fuel prices at a glance.</h1>
              </td>
            </tr>

            <!-- Price table -->
            <tr>
              <td style="padding:0 40px 8px;">
                <table cellpadding="0" cellspacing="0" width="100%" style="border:1px solid #ede8df;border-radius:12px;overflow:hidden;">
                  <thead>
                    <tr style="background:#faf7f2;">
                      <th style="padding:10px 16px;font-size:10px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:#c4b99a;text-align:left;font-family:'Cal Sans',-apple-system,sans-serif;">Fuel</th>
                      <th style="padding:10px 16px;font-size:10px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:#c4b99a;text-align:right;font-family:'Cal Sans',-apple-system,sans-serif;">Price (LKR/L)</th>
                      <th style="padding:10px 16px;font-size:10px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:#c4b99a;text-align:right;font-family:'Cal Sans',-apple-system,sans-serif;">7-day change</th>
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
              <td style="padding:14px 40px 28px;">
                <p style="margin:0;font-size:11px;color:#c4b99a;font-family:'Cal Sans',-apple-system,sans-serif;">Source: Ceylon Petroleum Corporation (CPC). Prices in LKR per litre.</p>
              </td>
            </tr>

            <!-- CTA -->
            <tr>
              <td style="padding:0 40px 38px;">
                <a href="{site_url}"
                   style="display:inline-block;background:#f59e0b;color:#1a0f00;text-decoration:none;
                          font-size:13px;font-weight:700;padding:13px 28px;border-radius:10px;
                          letter-spacing:0.01em;font-family:'Cal Sans',-apple-system,sans-serif;">
                  View live prices &amp; history &rarr;
                </a>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="padding:16px 40px;background:#faf7f2;border-top:1px solid #ede8df;">
                <p style="margin:0;font-size:11px;color:#c4b99a;line-height:1.7;font-family:'Cal Sans',-apple-system,sans-serif;">
                  You're receiving this because you subscribed on
                  <a href="{site_url}" style="color:#f59e0b;text-decoration:none;font-weight:600;">Octane</a>.
                  &nbsp;&middot;&nbsp;
                  <a href="{unsub_url}" style="color:#c4b99a;text-decoration:underline;">Unsubscribe</a>
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

_DIGEST_TEXT = """\
Octane Weekly Fuel Price Digest — Week of {week_of}
=====================================================

Sri Lanka CPC Fuel Prices (LKR per litre):

{price_text}

Source: Ceylon Petroleum Corporation

View live prices, history & world comparison:
{site_url}

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
            site_url=s.site_url.rstrip("/"),
        )
        text_body = _DIGEST_TEXT.format(
            week_of=week_of,
            price_text=price_text,
            unsub_url=unsub_url,
            site_url=s.site_url.rstrip("/"),
        )
        ok, err = _send_html_email(sub["email"], subject, html_body, text_body)
        if ok:
            _mark_sent(sub["id"])
            sent += 1
        elif err:
            log.error("digest send failed for %s: %s", sub["email"], err)

    log.info("weekly digest: sent %d / %d", sent, len(list_active()))
    return sent
