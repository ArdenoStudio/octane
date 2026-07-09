"""Run all scrapers and persist results. Idempotent — safe to run repeatedly.

Invoked by:
  - Manual: `python -m app.scrapers.run`
  - Cron:   GitHub Actions (see .github/workflows/scrape.yml) — 5× daily
"""
from __future__ import annotations

import logging

from app.config import get_settings
from app.db import migrate
from app.db.connection import cursor
from app.scrapers import cpc, fx, lanka_ioc, news, world
from app.services import alerts as alert_service

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


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
        news_points = list(news.run())
        summary["news"] = _persist_fuel(news_points)
        _record_scrape_run(
            "news",
            summary["news"],
            ok=True,
            detail=None if summary["news"] else "0 rows (no matching headlines)",
        )
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

    log.info("scraper run complete: %s", summary)
    return summary


if __name__ == "__main__":
    run_all()
