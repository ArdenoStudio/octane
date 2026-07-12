"""Run all scrapers and persist results. Idempotent — safe to run repeatedly.

Invoked by:
  - Manual: `python -m app.scrapers.run`
  - Cron:   GitHub Actions (see .github/workflows/scrape.yml) — 5× daily
"""
from __future__ import annotations

import logging
import os

from app.config import get_settings
from app.db import migrate
from app.db.connection import cursor
from app.scrapers import cpc, fx, lanka_ioc, news, world
from app.services import alerts as alert_service

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Sources whose latest pump / early-signal prices should refresh AI outlook.
_SENTIMENT_SOURCES = ("cpc", "news", "lanka_ioc")


def latest_prices_by_source(source: str) -> dict[str, float]:
    """Most recent price_lkr per fuel for a source."""
    with cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (fuel_type)
                   fuel_type, price_lkr
            FROM fuel_prices
            WHERE source = %s
            ORDER BY fuel_type, recorded_at DESC
            """,
            (source,),
        )
        return {r["fuel_type"]: float(r["price_lkr"]) for r in cur.fetchall()}


def snapshot_sentiment_prices() -> dict[str, dict[str, float]]:
    """Latest CPC / news / LIOC prices used to decide if outlook should refresh."""
    return {src: latest_prices_by_source(src) for src in _SENTIMENT_SOURCES}


def prices_changed(
    before: dict[str, dict[str, float]],
    after: dict[str, dict[str, float]],
    *,
    tolerance_lkr: float = 0.01,
) -> bool:
    """True when any tracked source/fuel latest price moved."""
    for source in _SENTIMENT_SOURCES:
        prev = before.get(source) or {}
        nxt = after.get(source) or {}
        fuels = set(prev) | set(nxt)
        for fuel in fuels:
            a = prev.get(fuel)
            b = nxt.get(fuel)
            if a is None and b is None:
                continue
            if a is None or b is None:
                return True
            if abs(a - b) >= tolerance_lkr:
                return True
    return False


def write_github_output(*, price_changed: bool) -> None:
    """Emit price_changed for GitHub Actions when GITHUB_OUTPUT is set."""
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a", encoding="utf-8") as fh:
        fh.write(f"price_changed={'true' if price_changed else 'false'}\n")
    log.info("GITHUB_OUTPUT price_changed=%s", price_changed)


def _persist_fuel(points: list[cpc.PricePoint]) -> int:
    if not points:
        return 0
    rows = [
        (p.recorded_at, p.fuel_type, p.price_lkr, p.source) for p in points
    ]
    with cursor() as cur:
        cur.executemany(
            """
            INSERT INTO fuel_prices (recorded_at, fuel_type, price_lkr, source, scraped_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (recorded_at, fuel_type, source) DO UPDATE
              SET price_lkr = EXCLUDED.price_lkr,
                  scraped_at = NOW()
            """,
            rows,
        )
    return len(rows)


def _record_scrape_run(
    source: str,
    rows_upserted: int,
    *,
    ok: bool = True,
    detail: str | None = None,
) -> None:
    """Always record that we checked a source, even when prices did not change."""
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO scrape_runs (source, rows_upserted, ok, detail)
            VALUES (%s, %s, %s, %s)
            """,
            (source, rows_upserted, ok, detail),
        )


def _persist_world(points: list[world.WorldPrice]) -> int:
    if not points:
        return 0
    rows = [
        (p.recorded_at, p.country, p.fuel_type, p.price_usd) for p in points
    ]
    with cursor() as cur:
        cur.executemany(
            """
            INSERT INTO world_prices (recorded_at, country, fuel_type, price_usd)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (recorded_at, country, fuel_type) DO UPDATE
              SET price_usd = EXCLUDED.price_usd
            """,
            rows,
        )
    return len(rows)


def _persist_fx(rate: fx.FxRate) -> int:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO fx_rates (recorded_at, base, target, rate)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (recorded_at, base, target) DO UPDATE
              SET rate = EXCLUDED.rate
            """,
            (rate.recorded_at, rate.base, rate.target, rate.rate),
        )
    return 1


def _notify_admin(subject: str, body: str) -> None:
    """Send an operational alert to the admin email if configured."""
    s = get_settings()
    if not s.admin_email:
        return
    from app.services.alerts import _send_email
    _send_email(s.admin_email, subject, body)


def run_all() -> dict[str, int]:
    migrate.run()
    summary: dict[str, int] = {}
    before = snapshot_sentiment_prices()

    try:
        cpc_points = list(cpc.run())
        summary["cpc"] = _persist_fuel(cpc_points)
        if summary["cpc"] == 0:
            log.error("cpc scraper returned 0 rows — site layout may have changed")
            _record_scrape_run("cpc", 0, ok=False, detail="0 rows returned")
            _notify_admin(
                "Octane: CPC scraper returned 0 rows",
                "The CPC scraper ran but found no price data.\n\n"
                "The site layout may have changed. Check manually:\n"
                "https://ceypetco.gov.lk/historical-prices/\n\n"
                "— Octane health monitor",
            )
        else:
            _record_scrape_run("cpc", summary["cpc"])
    except Exception as e:  # noqa: BLE001
        log.exception("cpc scraper failed: %s", e)
        summary["cpc"] = 0
        try:
            _record_scrape_run("cpc", 0, ok=False, detail=str(e)[:500])
        except Exception:  # noqa: BLE001
            log.exception("failed to record cpc scrape_run")

    try:
        ioc_points = list(lanka_ioc.run())
        summary["lanka_ioc"] = _persist_fuel(ioc_points)
        if summary["lanka_ioc"] == 0:
            log.warning("lanka_ioc scraper returned 0 rows")
            _record_scrape_run("lanka_ioc", 0, ok=False, detail="0 rows returned")
        else:
            _record_scrape_run("lanka_ioc", summary["lanka_ioc"])
    except Exception as e:  # noqa: BLE001
        log.exception("lanka_ioc scraper failed: %s", e)
        summary["lanka_ioc"] = 0
        try:
            _record_scrape_run("lanka_ioc", 0, ok=False, detail=str(e)[:500])
        except Exception:  # noqa: BLE001
            log.exception("failed to record lanka_ioc scrape_run")

    try:
        # Ingest broadly, then persist one consensus row per fuel (same as
        # the hourly news job) so multi-outlet hits don't thrash the table.
        from app.scrapers.run_news import prefer_consensus, consensus_summary

        raw_news = list(news.run())
        news_points = prefer_consensus(raw_news)
        summary["news"] = _persist_fuel(news_points)
        fuels = consensus_summary(raw_news)
        consensus_fuels = [f for f, s in fuels.items() if s["consensus"]]
        detail = (
            f"raw={len(raw_news)} selected={len(news_points)} "
            f"consensus_fuels={consensus_fuels or 'none'}"
            if news_points
            else "0 rows (no matching headlines)"
        )
        _record_scrape_run("news", summary["news"], ok=True, detail=detail)
    except Exception as e:  # noqa: BLE001
        log.exception("news scraper failed: %s", e)
        summary["news"] = 0
        try:
            _record_scrape_run("news", 0, ok=False, detail=str(e)[:500])
        except Exception:  # noqa: BLE001
            log.exception("failed to record news scrape_run")

    try:
        world_points = world.run()
        summary["world"] = _persist_world(world_points)
    except Exception as e:  # noqa: BLE001
        log.exception("world scraper failed: %s", e)
        summary["world"] = 0

    try:
        fx_rate = fx.run()
        if fx_rate:
            summary["fx"] = _persist_fx(fx_rate)
            log.info("fx rate: 1 USD = %s LKR", fx_rate.rate)
        else:
            summary["fx"] = 0
            log.warning("fx scraper returned no rate")
    except Exception as e:  # noqa: BLE001
        log.exception("fx scraper failed: %s", e)
        summary["fx"] = 0

    try:
        summary["alerts_fired"] = alert_service.dispatch_pending()
    except Exception as e:  # noqa: BLE001
        log.exception("alert dispatch failed: %s", e)
        summary["alerts_fired"] = 0

    after = snapshot_sentiment_prices()
    changed = prices_changed(before, after)
    summary["price_changed"] = 1 if changed else 0
    write_github_output(price_changed=changed)
    if changed:
        log.info("price change detected — AI revision outlook should refresh")

    log.info("scraper run complete: %s", summary)
    return summary


if __name__ == "__main__":
    run_all()
