"""Embeddable widget — returns a self-contained HTML page suitable for iframe."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app import fuel as fuel_mod
from app.services import prices

router = APIRouter(prefix="/v1/embed", tags=["embed"])


_TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Octane — Live Sri Lanka Fuel Prices</title>
<style>
  :root {{
    --bg: {bg};
    --fg: {fg};
    --muted: {muted};
    --accent: {accent};
    --border: {border};
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; height: 100%; }}
  body {{
    background: var(--bg); color: var(--fg);
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    padding: 16px; line-height: 1.4;
  }}
  .wrap {{ display: flex; flex-direction: column; gap: 8px; height: 100%; }}
  .head {{ display: flex; justify-content: space-between; align-items: baseline; }}
  .label {{ font-size: 12px; letter-spacing: .08em; color: var(--muted); text-transform: uppercase; }}
  .price {{ font-size: 40px; font-weight: 700; color: var(--accent); letter-spacing: -0.02em; }}
  .meta {{ font-size: 12px; color: var(--muted); }}
  .row {{ display: flex; justify-content: space-between; gap: 8px; padding-top: 8px; border-top: 1px solid var(--border); margin-top: auto; }}
  a {{ color: var(--accent); text-decoration: none; font-weight: 600; }}
</style>
</head><body>
<div class="wrap">
  <div class="head">
    <div class="label">{display}</div>
    <div class="meta">CPC</div>
  </div>
  <div class="price">LKR {price}</div>
  <div class="meta">As of {recorded_at}</div>
  <div class="row">
    <span class="meta">Live Sri Lanka fuel prices</span>
    <a href="https://octane.lk" target="_blank" rel="noopener">octane.lk →</a>
  </div>
</div>
</body></html>"""


def _theme(name: str) -> dict:
    if name == "dark":
        return {
            "bg": "#0b0d10",
            "fg": "#f4f4f5",
            "muted": "#9ca3af",
            "accent": "#fbbf24",
            "border": "#1f2937",
        }
    return {
        "bg": "#ffffff",
        "fg": "#0a0a0a",
        "muted": "#6b7280",
        "accent": "#b45309",
        "border": "#e5e7eb",
    }


@router.get("/widget", response_class=HTMLResponse)
def widget(
    fuel: str = Query("petrol_92"),
    theme: str = Query("light", pattern="^(light|dark)$"),
):
    if fuel not in fuel_mod.ALL_FUELS:
        raise HTTPException(status_code=400, detail=f"unknown fuel '{fuel}'")
    latest = prices.latest_for(fuel)
    if not latest:
        raise HTTPException(status_code=404, detail="no data")
    html = _TEMPLATE.format(
        display=fuel_mod.DISPLAY[fuel],
        price=f"{latest['price_lkr']:.2f}",
        recorded_at=latest["recorded_at"],
        **_theme(theme),
    )
    return HTMLResponse(html, headers={"X-Frame-Options": "ALLOWALL"})
