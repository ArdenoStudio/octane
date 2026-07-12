"""Ceylon Petroleum Corporation scraper.

Parses the historical-prices revisions table at ceypetco.gov.lk. The page
layout has shifted over the years — be defensive about column order and
fuel-type labels. Each row in the historical table represents a price
revision; we record one fuel_prices row per fuel per revision date.

Homepage snapshots are stamped with today's date so off-cycle revisions are
detected before the historical table catches up.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from bs4 import BeautifulSoup, Tag

from app import fuel as fuel_mod
from app.scrapers.http import get_text

SOURCE = "cpc"
HISTORICAL_URL = "https://ceypetco.gov.lk/historical-prices/"
LATEST_URL = "https://ceypetco.gov.lk/"

PRICE_RE = re.compile(r"(\d{2,4}(?:\.\d{1,2})?)")
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %B %Y", "%d %b %Y")

# Prefer longer aliases first so "Petrol 92 Octane" wins over bare "92".
_ALIAS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            re.escape(alias) + r"[^\d]{0,60}(\d{2,4}(?:\.\d{1,2})?)",
            re.IGNORECASE,
        ),
        fuel,
    )
    for alias, fuel in sorted(
        fuel_mod.CPC_ALIASES.items(), key=lambda item: -len(item[0])
    )
]


@dataclass(frozen=True)
class PricePoint:
    recorded_at: date
    fuel_type: str
    price_lkr: float
    source: str = SOURCE
    # Optional provenance for news consensus (ignored by CPC/LIOC persist).
    outlet: str | None = None
    article_url: str | None = None


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_price(cell: str) -> float | None:
    s = cell.strip()
    # European-style decimal comma when no period is present (e.g. "317,00").
    if "." not in s and s.count(",") == 1:
        s = re.sub(r"(\d+)\,(\d{1,2})", r"\1.\2", s)
    match = PRICE_RE.search(s.replace(",", ""))
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


def _price_in_range(price: float) -> bool:
    return 50 <= price <= 2000


def _dedupe_by_fuel(points: list[PricePoint]) -> list[PricePoint]:
    seen: set[str] = set()
    unique: list[PricePoint] = []
    for p in points:
        if p.fuel_type in seen:
            continue
        seen.add(p.fuel_type)
        unique.append(p)
    return unique


def _extract_from_text(text: str, as_of: date) -> list[PricePoint]:
    points: list[PricePoint] = []
    for pattern, fuel in _ALIAS_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        try:
            price = float(m.group(1))
        except ValueError:
            continue
        if _price_in_range(price):
            points.append(PricePoint(as_of, fuel, price))
    return _dedupe_by_fuel(points)


def _extract_from_dom(soup: BeautifulSoup, as_of: date) -> list[PricePoint]:
    """Prefer structured widgets/cards over whole-page regex when possible."""
    points: list[PricePoint] = []
    selectors = (
        "[class*='price']",
        "[class*='fuel']",
        "[class*='product']",
        "[class*='petrol']",
        "[class*='diesel']",
        "article",
        "li",
    )
    seen_nodes: set[int] = set()
    for selector in selectors:
        for node in soup.select(selector):
            node_id = id(node)
            if node_id in seen_nodes:
                continue
            seen_nodes.add(node_id)
            if not isinstance(node, Tag):
                continue
            text = node.get_text(" ", strip=True)
            if not text or len(text) > 280:
                continue
            # Prefer alias+price patterns so currency codes (LKR) don't steal matches.
            extracted = _extract_from_text(text, as_of)
            if extracted:
                points.extend(extracted)
                continue
            fuel = fuel_mod.normalize(text)
            if not fuel:
                continue
            price = _parse_price(text)
            if price is None or not _price_in_range(price):
                continue
            points.append(PricePoint(as_of, fuel, price))
    return _dedupe_by_fuel(points)


def parse_latest_html(html: str, as_of: date | None = None) -> list[PricePoint]:
    """Parse homepage / widget HTML into today's price snapshot."""
    today = as_of or date.today()
    soup = BeautifulSoup(html, "lxml")
    points = _extract_from_dom(soup, today)
    if len(points) >= 3:
        return points
    # Fall back to full-page text patterns (covers older layouts).
    text_points = _extract_from_text(soup.get_text(" ", strip=True), today)
    by_fuel = {p.fuel_type: p for p in points}
    for p in text_points:
        by_fuel.setdefault(p.fuel_type, p)
    return list(by_fuel.values())


def _fetch_html(url: str) -> str:
    # ceypetco.gov.lk has periodically served an expired TLS cert; fall back
    # to insecure verify so the pipeline keeps collecting official prices.
    return get_text(url, tls_fallback=True)


def fetch_historical() -> list[PricePoint]:
    return _parse_table(_fetch_html(HISTORICAL_URL))


def fetch_latest() -> list[PricePoint]:
    """Best-effort scrape of the homepage's price-strip widget.

    Returns the most recent CPC prices stamped with today's date. The
    historical table is the source of truth; this is just a daily ping
    to detect changes between revisions.
    """
    return parse_latest_html(_fetch_html(LATEST_URL))


def run() -> Iterable[PricePoint]:
    points = list(fetch_historical())
    # Append today's snapshot if missing — helps detect off-cycle revisions.
    today_points = fetch_latest()
    have = {(p.recorded_at, p.fuel_type) for p in points}
    for tp in today_points:
        if (tp.recorded_at, tp.fuel_type) not in have:
            points.append(tp)
    return points
