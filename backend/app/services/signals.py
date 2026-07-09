"""Early price signals — news / LIOC ahead of or diverging from CPC.

CPC remains the official retail source. These helpers surface *reported*
prices so the UI can show unconfirmed changes without replacing CPC.
"""
from __future__ import annotations

from datetime import date, timedelta

from app import fuel as fuel_mod
from app.services import prices

# How long a news-reported price stays "early" after its effective date.
NEWS_SIGNAL_WINDOW_DAYS = 14
# Minimum LIOC vs CPC gap (LKR) before we call it a divergence.
LIOC_DIVERGENCE_LKR = 1.0


def _row_by_source(rows: list[dict], fuel_type: str, source: str) -> dict | None:
    for r in rows:
        if r["fuel_type"] == fuel_type and r["source"] == source:
            return r
    return None


def early_signals(rows: list[dict] | None = None) -> list[dict]:
    """Return unconfirmed / divergent prices relative to CPC.

    Each item:
      fuel_type, source ("news"|"lanka_ioc"), price_lkr, recorded_at,
      cpc_price_lkr, cpc_recorded_at, delta_lkr, status
    """
    all_rows = rows if rows is not None else prices.latest_all()
    today = date.today()
    cutoff = today - timedelta(days=NEWS_SIGNAL_WINDOW_DAYS)
    out: list[dict] = []

    for fuel in fuel_mod.ALL_FUELS:
        cpc = _row_by_source(all_rows, fuel, "cpc")
        if not cpc:
            continue
        cpc_price = float(cpc["price_lkr"])
        cpc_date = date.fromisoformat(cpc["recorded_at"])

        news = _row_by_source(all_rows, fuel, "news")
        if news:
            news_date = date.fromisoformat(news["recorded_at"])
            news_price = float(news["price_lkr"])
            newer_or_same = news_date >= cpc_date
            differs = abs(news_price - cpc_price) >= 0.01
            recent = news_date >= cutoff
            # Ahead of CPC, or same-day report with a different figure.
            if recent and newer_or_same and (news_date > cpc_date or differs):
                out.append(
                    {
                        "fuel_type": fuel,
                        "source": "news",
                        "price_lkr": news_price,
                        "recorded_at": news["recorded_at"],
                        "scraped_at": news.get("scraped_at"),
                        "cpc_price_lkr": cpc_price,
                        "cpc_recorded_at": cpc["recorded_at"],
                        "delta_lkr": round(news_price - cpc_price, 2),
                        "status": "unconfirmed",
                    }
                )

        ioc = _row_by_source(all_rows, fuel, "lanka_ioc")
        if ioc:
            ioc_price = float(ioc["price_lkr"])
            if abs(ioc_price - cpc_price) >= LIOC_DIVERGENCE_LKR:
                out.append(
                    {
                        "fuel_type": fuel,
                        "source": "lanka_ioc",
                        "price_lkr": ioc_price,
                        "recorded_at": ioc["recorded_at"],
                        "scraped_at": ioc.get("scraped_at"),
                        "cpc_price_lkr": cpc_price,
                        "cpc_recorded_at": cpc["recorded_at"],
                        "delta_lkr": round(ioc_price - cpc_price, 2),
                        "status": "divergence",
                    }
                )

    # Prefer news signals first, then LIOC; stable fuel order.
    source_rank = {"news": 0, "lanka_ioc": 1}
    fuel_rank = {f: i for i, f in enumerate(fuel_mod.ALL_FUELS)}
    out.sort(key=lambda s: (source_rank.get(s["source"], 9), fuel_rank.get(s["fuel_type"], 99)))
    return out
