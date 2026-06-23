"""Open a live preview of the weekly digest email in your browser. Run: python preview_digest.py"""
import ast, os, re, webbrowser, tempfile

src = open(os.path.join(os.path.dirname(__file__), "app/services/digest.py"), encoding="utf-8").read()
match = re.search(r'_DIGEST_HTML = ("""\\\n.*?""")', src, re.DOTALL)
template = ast.literal_eval(match.group(1))

price_rows = """
<tr>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:13px;color:#6b5e4e;font-family:'Cal Sans',-apple-system,sans-serif;">Petrol 92</td>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:15px;font-weight:700;color:#1a1208;text-align:right;font-family:'Cal Sans',-apple-system,sans-serif;">LKR&nbsp;317.00</td>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:12px;text-align:right;"><span style="color:#c4b99a;">unchanged</span></td>
</tr>
<tr>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:13px;color:#6b5e4e;font-family:'Cal Sans',-apple-system,sans-serif;">Petrol 95</td>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:15px;font-weight:700;color:#1a1208;text-align:right;font-family:'Cal Sans',-apple-system,sans-serif;">LKR&nbsp;377.00</td>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:12px;text-align:right;"><span style="display:inline-block;font-size:11px;font-weight:700;color:#16a34a;background:#f0fdf4;padding:2px 7px;border-radius:5px;">&#9660;&nbsp;-2.5%</span></td>
</tr>
<tr>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:13px;color:#6b5e4e;font-family:'Cal Sans',-apple-system,sans-serif;">Auto Diesel</td>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:15px;font-weight:700;color:#1a1208;text-align:right;font-family:'Cal Sans',-apple-system,sans-serif;">LKR&nbsp;273.00</td>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:12px;text-align:right;"><span style="color:#c4b99a;">unchanged</span></td>
</tr>
<tr>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:13px;color:#6b5e4e;font-family:'Cal Sans',-apple-system,sans-serif;">Super Diesel</td>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:15px;font-weight:700;color:#1a1208;text-align:right;font-family:'Cal Sans',-apple-system,sans-serif;">LKR&nbsp;318.00</td>
  <td style="padding:12px 16px;border-bottom:1px solid #ede8df;font-size:12px;text-align:right;"><span style="display:inline-block;font-size:11px;font-weight:700;color:#dc2626;background:#fef2f2;padding:2px 7px;border-radius:5px;">&#9650;&nbsp;+1.8%</span></td>
</tr>
<tr>
  <td style="padding:12px 16px;font-size:13px;color:#6b5e4e;font-family:'Cal Sans',-apple-system,sans-serif;">Kerosene</td>
  <td style="padding:12px 16px;font-size:15px;font-weight:700;color:#1a1208;text-align:right;font-family:'Cal Sans',-apple-system,sans-serif;">LKR&nbsp;195.00</td>
  <td style="padding:12px 16px;font-size:12px;text-align:right;"><span style="color:#c4b99a;">—</span></td>
</tr>
"""

html = template.format(
    week_of="May 10, 2026",
    price_rows=price_rows,
    unsub_url="https://octane-smoky.vercel.app/digest/unsubscribe?token=preview-token",
    site_url="https://octane-smoky.vercel.app",
)

with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
    f.write(html)
    path = f.name

print(f"Preview: {path}")
webbrowser.open(f"file:///{path}")
