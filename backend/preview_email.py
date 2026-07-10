"""Open a live preview of the alert email in your browser. Run: python preview_email.py"""
import ast, os, re, webbrowser, tempfile

# Pull _EMAIL_HTML out of alerts.py without importing the module (avoids DB deps)
src = open(os.path.join(os.path.dirname(__file__), "app/services/alerts.py"), encoding="utf-8").read()
match = re.search(r'_EMAIL_HTML = (""".*?""")', src, re.DOTALL)
template = ast.literal_eval(match.group(1))

def _sample_chart(threshold=400):
    vals = [330, 340, 355, 355, 380, 398, 410]
    W, H, PAD = 580, 72, 10
    raw_lo = min(min(vals), threshold)
    raw_hi = max(max(vals), threshold)
    pad_amt = (raw_hi - raw_lo) * 0.18 or 15
    lo, hi = raw_lo - pad_amt, raw_hi + pad_amt
    span = hi - lo
    n = len(vals)

    def px(i): return PAD + i * (W - 2 * PAD) / (n - 1)
    def py(v): return PAD + (1 - (v - lo) / span) * (H - 2 * PAD)

    pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(vals))
    lx, ly = f"{px(n-1):.1f}", f"{py(vals[-1]):.1f}"
    fill = (
        f"M{px(0):.1f},{py(vals[0]):.1f} "
        + " ".join(f"L{px(i):.1f},{py(v):.1f}" for i, v in enumerate(vals))
        + f" L{px(n-1):.1f},{H} L{px(0):.1f},{H} Z"
    )
    ty = py(threshold)
    return (
        f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'style="display:block;width:100%;" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><linearGradient id="oct-g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#f59e0b" stop-opacity="0.22"/>'
        f'<stop offset="100%" stop-color="#f59e0b" stop-opacity="0"/>'
        f'</linearGradient></defs>'
        f'<line x1="{PAD}" y1="{ty:.1f}" x2="{W-PAD}" y2="{ty:.1f}" '
        f'stroke="#c4b99a" stroke-width="1" stroke-dasharray="4 3"/>'
        f'<text x="{W-PAD-3}" y="{ty-4:.1f}" font-size="8.5" fill="#c4b99a" '
        f'text-anchor="end" font-family="-apple-system,BlinkMacSystemFont,sans-serif">LKR {threshold}</text>'
        f'<path d="{fill}" fill="url(#oct-g)"/>'
        f'<polyline points="{pts}" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{lx}" cy="{ly}" r="4.5" fill="#ffffff" stroke="#f59e0b" stroke-width="2"/>'
        f'</svg>'
    )

delta_badge = '<span style="display:inline-block;font-size:11px;font-weight:700;color:#dc2626;background:#fef2f2;padding:3px 8px;border-radius:6px;letter-spacing:-0.01em;">&#9650;&nbsp;+12</span>'

html = template.format(
    fuel_name="Petrol 92",
    price=410,
    direction="above",
    direction_cap="Above",
    threshold=400,
    recorded_at="3 May 2026",
    manage_url="https://octane-smoky.vercel.app/manage?token=preview-token",
    chart_html=_sample_chart(threshold=400),
    delta_badge=delta_badge,
)

with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
    f.write(html)
    path = f.name

print(f"Preview: {path}")
webbrowser.open(f"file:///{path}")
