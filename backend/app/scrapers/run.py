"""Run all scrapers and persist results. Idempotent — safe to run repeatedly.

Invoked by:
  - Manual: `python -m app.scrapers.run`
  - Cron:   Railway daily 8am
  - HTTP:   POST /v1/internal/run-scrapers (with token)
"""
from __future__ import annotations

import logging

from app.db import migrate
from app.db.connection import cursor
from app.scrapers import cpc, lanka_ioc, world
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
            INSERT INTO fuel_prices (recorded_at, fuel_type, price_lkr, source)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (recorded_at, fuel_type, source) DO UPDATE
              SET price_lkr = EXCLUDED.price_lkr
            """,
            rows,
        )
    return len(rows)


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


def run_all() -> dict[str, int]:
    migrate.run()
    summary: dict[str, int] = {}

    try:
        cpc_points = list(cpc.run())
        summary["cpc"] = _persist_fuel(cpc_points)
    except Exception as e:  # noqa: BLE001
        log.exception("cpc scraper failed: %s", e)
        summary["cpc"] = 0

    try:
        ioc_points = list(lanka_ioc.run())
        summary["lanka_ioc"] = _persist_fuel(ioc_points)
    except Exception as e:  # noqa: BLE001
        log.exception("lanka_ioc scraper failed: %s", e)
        summary["lanka_ioc"] = 0

    try:
        world_points = world.run()
        summary["world"] = _persist_world(world_points)
    except Exception as e:  # noqa: BLE001
        log.exception("world scraper failed: %s", e)
        summary["world"] = 0

    try:
        summary["alerts_fired"] = alert_service.dispatch_pending()
    except Exception as e:  # noqa: BLE001
        log.exception("alert dispatch failed: %s", e)
        summary["alerts_fired"] = 0

    log.info("scraper run complete: %s", summary)
    return summary


if __name__ == "__main__":
    run_all()
