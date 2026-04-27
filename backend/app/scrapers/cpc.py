"""Ceylon Petroleum Corporation scraper.

Parses the historical-prices revisions table at ceypetco.gov.lk. The page
layout has shifted over the years — be defensive about column order and
fuel-type labels. Each row in the historical table represents a price
revision; we record one fuel_prices row per fuel per revision date.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from bs4 import BeautifulSoup

from app import fuel as fuel_mod
from app.scrapers.http import client

SOURCE = "cpc"
HISTORICAL_URL = "https://ceypetco.gov.lk/historical-prices/"
LATEST_URL = "https://ceypetco.gov.lk/"

PRICE_RE = re.compile(r"(\d{2,4}(?:\.\d{1,2})?)")
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%d %b %Y")


@dataclass(frozen=True)
class PricePoint:
    recorded_at: date
    fuel_type: str
    price_lkr: float
    source: str = SOURCE


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_price(cell: str) -> float | None:
    match = PRICE_RE.search(cell.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _parse_table(html: str) -> list[PricePoint]:
    soup = BeautifulSoup(html, "lxml")
    points: list[PricePoint] = []
    for table in soup.find_all("table"):
        headers_row = table.find("tr")
        if not headers_row:
            continue
        headers = [c.get_text(strip=True) for c in headers_row.find_all(["th", "td"])]
        if not headers:
            continue
        # Identify fuel columns by header label.
        fuel_cols: dict[int, str] = {}
        date_col = -1
        for i, h in enumerate(headers):
            if not h:
                continue
            low = h.lower()
            if any(k in low for k in ("date", "revision", "effective")):
                date_col = i
                continue
            normalized = fuel_mod.normalize(h)
            if normalized:
                fuel_cols[i] = normalized
        if date_col < 0 or not fuel_cols:
            continue

        for row in table.find_all("tr")[1:]:
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) <= date_col:
                continue
            d = _parse_date(cells[date_col])
            if not d:
                continue
            for idx, fuel in fuel_cols.items():
                if idx >= len(cells):
                    continue
                price = _parse_price(cells[idx])
                if price is None or price <= 0:
                    continue
                points.append(PricePoint(d, fuel, price))
    return points


def fetch_historical() -> list[PricePoint]:
    with client() as c:
        r = c.get(HISTORICAL_URL)
        r.raise_for_status()
        return _parse_table(r.text)


def fetch_latest() -> list[PricePoint]:
    """Best-effort scrape of the homepage's price-strip widget.

    Returns the most recent CPC prices stamped with today's date. The
    historical table is the source of truth; this is just a daily ping
    to detect changes between revisions.
    """
    today = date.today()
    with client() as c:
        r = c.get(LATEST_URL)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    text = soup.get_text(" ", strip=True)
    points: list[PricePoint] = []
    # Look for "<fuel-name> ... <price>" patterns in the rendered text.
    for alias, fuel in fuel_mod.CPC_ALIASES.items():
        pattern = re.compile(
            re.escape(alias) + r"[^\d]{0,40}(\d{2,4}(?:\.\d{1,2})?)",
            re.IGNORECASE,
        )
        m = pattern.search(text)
        if not m:
            continue
        try:
            price = float(m.group(1))
        except ValueError:
            continue
        if 50 <= price <= 2000:  # sanity range for LKR fuel
            points.append(PricePoint(today, fuel, price))
    # De-dup by fuel — first match wins.
    seen: set[str] = set()
    unique: list[PricePoint] = []
    for p in points:
        if p.fuel_type in seen:
            continue
        seen.add(p.fuel_type)
        unique.append(p)
    return unique


def run() -> Iterable[PricePoint]:
    points = list(fetch_historical())
    # Append today's snapshot if missing — helps detect off-cycle revisions.
    today_points = fetch_latest()
    have = {(p.recorded_at, p.fuel_type) for p in points}
    for tp in today_points:
        if (tp.recorded_at, tp.fuel_type) not in have:
            points.append(tp)
    return points
