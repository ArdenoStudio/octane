"""Fetch live USD/LKR exchange rate from Open Exchange Rates (free, no auth)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from app.scrapers.http import client

log = logging.getLogger(__name__)

API_URL = "https://open.er-api.com/v6/latest/USD"
MIN_VALID_LKR = 100.0
MAX_VALID_LKR = 1000.0


@dataclass(frozen=True)
class FxRate:
    recorded_at: date
    base: str
    target: str
    rate: float


def run() -> FxRate | None:
    try:
        with client() as c:
            r = c.get(API_URL)
            r.raise_for_status()
            data = r.json()
        lkr = data.get("rates", {}).get("LKR")
        if lkr and MIN_VALID_LKR < float(lkr) < MAX_VALID_LKR:
            return FxRate(date.today(), "USD", "LKR", round(float(lkr), 4))
        log.warning("fx scraper: LKR rate out of expected range: %s", lkr)
    except Exception:
        log.exception("fx scraper failed")
    return None
