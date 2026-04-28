"""World fuel price scraper.

Scrapes globalpetrolprices.com country-specific pages for gasoline + diesel
prices in USD per litre. Fetches Sri Lanka and its regional neighbors, plus
derives the world average from the analytics table on Sri Lanka's page.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup

from app.scrapers.http import client

SOURCE = "globalpetrolprices"

COUNTRY_SLUGS: dict[str, str] = {
    "Sri Lanka": "Sri-Lanka",
    "India":     "India",
    "Pakistan":  "Pakistan",
    "Bangladesh":"Bangladesh",
    "Nepal":     "Nepal",
    "Maldives":  "Maldives",
}

FUEL_SLUGS: dict[str, str] = {
    "gasoline": "gasoline_prices",
    "diesel":   "diesel_prices",
}


@dataclass(frozen=True)
class WorldPrice:
    recorded_at: date
    country: str
    fuel_type: str
    price_usd: float


def _extract_price(soup: BeautifulSoup) -> float | None:
    """Pull USD/Liter current price from the first summary table."""
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for i, row in enumerate(rows):
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) >= 2 and cells[0] == "Current price":
                try:
                    return float(cells[1])
                except ValueError:
                    pass
    return None


def _extract_world_avg_pct(soup: BeautifulSoup) -> float | None:
    """Read 'Percent of world average' from analytics table to derive world avg."""
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) >= 2 and "world average" in cells[0].lower():
                m = re.search(r"(\d+\.?\d*)", cells[1])
                if m:
                    try:
                        return float(m.group(1))
                    except ValueError:
                        pass
    return None


def fetch(fuel_type: str) -> list[WorldPrice]:
    today = date.today()
    slug = FUEL_SLUGS[fuel_type]
    points: list[WorldPrice] = []
    world_avg: float | None = None

    with client() as c:
        for country, country_slug in COUNTRY_SLUGS.items():
            try:
                r = c.get(
                    f"https://www.globalpetrolprices.com/{country_slug}/{slug}/",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"},
                )
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                price = _extract_price(soup)
                if price and 0.1 <= price <= 10:
                    points.append(WorldPrice(today, country, fuel_type, price))
                    if world_avg is None and country == "Sri Lanka":
                        pct = _extract_world_avg_pct(soup)
                        if pct and pct > 0:
                            world_avg = round(price / (pct / 100), 3)
            except Exception:
                pass

    if world_avg:
        points.append(WorldPrice(today, "World", fuel_type, world_avg))

    return points


def run() -> list[WorldPrice]:
    out: list[WorldPrice] = []
    out.extend(fetch("gasoline"))
    out.extend(fetch("diesel"))
    return out
