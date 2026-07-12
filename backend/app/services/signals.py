"""Early price signals — news ahead of the winning official (CPC or LIOC).

CPC and Lanka IOC are both treated as official retail sources. The more
recently revised one wins per fuel. News remains an unconfirmed early signal
relative to that winner — LIOC is never an \"unconfirmed\" signal anymore.
"""
from __future__ import annotations

from datetime import date, timedelta

from app import fuel as fuel_mod
from app.services import prices

# How long a news-reported price stays "early" after its effective date.
NEWS_SIGNAL_WINDOW_DAYS = 14


def _row_by_source(rows: list[dict], fuel_type: str, source: str) -> dict | None:
    for r in rows:
        if r["fuel_type"] == fuel_type and r["source"] == source:
            return r
    return None


def early_signals(rows: list[dict] | None = None) -> list[dict]:
    """Return unconfirmed news prices relative to the winning official source.

    Each item:
      fuel_type, source (\"news\"), price_lkr, recorded_at,
      official_source, official_price_lkr, official_recorded_at,
      cpc_price_lkr, cpc_recorded_at (aliases of official_* for older clients),
      delta_lkr, status
    """
    all_rows = rows if rows is not None else prices.latest_all()
    today = date.today()
    cutoff = today - timedelta(days=NEWS_SIGNAL_WINDOW_DAYS)
    out: list[dict] = []

    for fuel in fuel_mod.ALL_FUELS:
        official = prices.pick_official(
            _row_by_source(all_rows, fuel, "cpc"),
            _row_by_source(all_rows, fuel, "lanka_ioc"),
        )
        if not official:
            continue

        official_price = float(official["price_lkr"])
        official_date = date.fromisoformat(str(official["recorded_at"])[:10])
        official_source = official["source"]
        official_recorded_at = official["recorded_at"]

        news = _row_by_source(all_rows, fuel, "news")
        if not news:
            continue

        news_date = date.fromisoformat(str(news["recorded_at"])[:10])
        news_price = float(news["price_lkr"])
        newer_or_same = news_date >= official_date
        differs = abs(news_price - official_price) >= 0.01
        recent = news_date >= cutoff
        # Ahead of the winning official, or same-day report with a different figure.
        if recent and newer_or_same and (news_date > official_date or differs):
            out.append(
                {
                    "fuel_type": fuel,
                    "source": "news",
                    "price_lkr": news_price,
                    "recorded_at": news["recorded_at"],
                    "scraped_at": news.get("scraped_at"),
                    "official_source": official_source,
                    "official_price_lkr": official_price,
                    "official_recorded_at": official_recorded_at,
                    # Back-compat aliases used by chart media extensions.
                    "cpc_price_lkr": official_price,
                    "cpc_recorded_at": official_recorded_at,
                    "delta_lkr": round(news_price - official_price, 2),
                    "status": "unconfirmed",
                }
            )

    fuel_rank = {f: i for i, f in enumerate(fuel_mod.ALL_FUELS)}
    out.sort(key=lambda s: fuel_rank.get(s["fuel_type"], 99))
    return out
