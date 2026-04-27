"""World fuel price scraper.

Scrapes globalpetrolprices.com for gasoline + diesel prices per country
in USD per litre. Only stores the world average + Sri Lanka and its
regional neighbors (India, Pakistan, Bangladesh, Nepal, Maldives) to
keep the comparison row tight.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup

from app.scrapers.http import client

SOURCE = "globalpetrolprices"
GASOLINE_URL = "https://www.globalpetrolprices.com/gasoline_prices/"
DIESEL_URL = "https://www.globalpetrolprices.com/diesel_prices/"

NEIGHBORS = {
    "Sri Lanka",
    "India",
    "Pakistan",
    "Bangladesh",
    "Nepal",
    "Maldives",
    "World",
}

PRICE_RE = re.compile(r"(\d+\.\d{2,3})")


@dataclass(frozen=True)
class WorldPrice:
    recorded_at: date
    country: str
    fuel_type: str  # 'gasoline' | 'diesel'
    price_usd: float


def _parse(html: str, fuel_type: str) -> list[WorldPrice]:
    soup = BeautifulSoup(html, "lxml")
    today = date.today()
    points: list[WorldPrice] = []
    # The site renders a long table of countries. Each row: country + price USD/L.
    for row in soup.select("table tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        country = cells[0]
        if country not in NEIGHBORS:
            continue
        for cell in cells[1:]:
            m = PRICE_RE.search(cell)
            if m:
                try:
                    price = float(m.group(1))
                except ValueError:
                    continue
                if 0.1 <= price <= 10:
                    points.append(WorldPrice(today, country, fuel_type, price))
                    break
    # Fallback: try to find the world-average sentence in the body text.
    if not any(p.country == "World" for p in points):
        text = soup.get_text(" ", strip=True)
        m = re.search(r"world average [^.]*?(\d+\.\d{2,3})", text, re.IGNORECASE)
        if m:
            try:
                price = float(m.group(1))
                points.append(WorldPrice(today, "World", fuel_type, price))
            except ValueError:
                pass
    return points


def fetch() -> list[WorldPrice]:
    out: list[WorldPrice] = []
    with client() as c:
        r = c.get(GASOLINE_URL)
        r.raise_for_status()
        out.extend(_parse(r.text, "gasoline"))
        r = c.get(DIESEL_URL)
        r.raise_for_status()
        out.extend(_parse(r.text, "diesel"))
    return out


def run() -> list[WorldPrice]:
    return fetch()
