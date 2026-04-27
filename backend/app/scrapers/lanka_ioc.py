"""Lanka IOC scraper. Pulls today's posted prices from lankaiocoil.lk."""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from app import fuel as fuel_mod
from app.scrapers.cpc import PricePoint
from app.scrapers.http import client

SOURCE = "lanka_ioc"
URL = "https://lankaiocoil.lk/"

PRICE_RE = re.compile(r"(\d{2,4}(?:\.\d{1,2})?)")


def fetch_latest() -> list[PricePoint]:
    today = date.today()
    with client() as c:
        r = c.get(URL)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    text = soup.get_text(" ", strip=True)

    points: list[PricePoint] = []
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
        if 50 <= price <= 2000:
            points.append(PricePoint(today, fuel, price, source=SOURCE))
    seen: set[str] = set()
    unique: list[PricePoint] = []
    for p in points:
        if p.fuel_type in seen:
            continue
        seen.add(p.fuel_type)
        unique.append(p)
    return unique


def run() -> list[PricePoint]:
    return fetch_latest()
