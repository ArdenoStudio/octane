"""Open a live preview of the alert email in your browser. Run: python preview_email.py"""
import ast, os, re, webbrowser, tempfile

src = open(os.path.join(os.path.dirname(__file__), "app/services/alerts.py"), encoding="utf-8").read()
match = re.search(r'_EMAIL_HTML = ("""\\\n.*?""")', src, re.DOTALL)
template = ast.literal_eval(match.group(1))

delta_badge = '<span style="display:inline-block;font-size:11px;font-weight:700;color:#dc2626;background:#fef2f2;padding:3px 8px;border-radius:6px;letter-spacing:-0.01em;">&#9650;&nbsp;+12</span>'

html = template.format(
    fuel_name="Petrol 92",
    price=410,
    direction="above",
    direction_cap="Above",
    threshold=400,
    recorded_at="3 May 2026",
    manage_url="https://octane-smoky.vercel.app/manage?token=preview-token",
    chart_html="",
    delta_badge=delta_badge,
)

with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
    f.write(html)
    path = f.name

print(f"Preview: {path}")
webbrowser.open(f"file:///{path}")
