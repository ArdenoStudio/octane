"""Open a live preview of the alert email in your browser. Run: python preview_email.py"""
import ast, os, re, webbrowser, tempfile

# Pull _EMAIL_HTML out of alerts.py without importing the module (avoids DB deps)
src = open(os.path.join(os.path.dirname(__file__), "app/services/alerts.py"), encoding="utf-8").read()
match = re.search(r'_EMAIL_HTML = (""".*?""")', src, re.DOTALL)
template = ast.literal_eval(match.group(1))

html = template.format(
    fuel_name="Petrol 92",
    price=410,
    direction="above",
    direction_cap="Above",
    threshold=400,
    recorded_at="2026-05-03",
    manage_url="https://octane-smoky.vercel.app/manage?token=preview-token",
)

with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
    f.write(html)
    path = f.name

print(f"Preview: {path}")
webbrowser.open(f"file:///{path}")
