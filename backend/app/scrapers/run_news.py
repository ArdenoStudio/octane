"""News-only scraper entrypoint — faster cadence than the full pipeline.

Invoked by:
  - Manual: `python -m app.scrapers.run_news`
  - Cron:   GitHub Actions hourly (see .github/workflows/scrape-news.yml)
  - Dry run (no DB): `python -m app.scrapers.run_news --dry-run`

Purpose: catch media-reported CPC revisions hours before the official site
updates. Results are stored as source='news' and surfaced as unconfirmed
early signals — they never replace official CPC prices.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import defaultdict

from app.scrapers import news
from app.scrapers.cpc import PricePoint

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Prefer a news price when at least this many distinct articles agree
# (same fuel + price within TOLERANCE_LKR). Single-outlet hits are kept
# but flagged in the scrape_run detail for observability.
CONSENSUS_MIN = 2
TOLERANCE_LKR = 1.0


def _cluster_by_price(hits: list[PricePoint]) -> list[list[PricePoint]]:
    """Cluster hits whose prices are within TOLERANCE_LKR of the cluster mean."""
    if not hits:
        return []
    ordered = sorted(hits, key=lambda p: p.price_lkr)
    clusters: list[list[PricePoint]] = [[ordered[0]]]
    for p in ordered[1:]:
        cluster = clusters[-1]
        mean = sum(h.price_lkr for h in cluster) / len(cluster)
        if abs(p.price_lkr - mean) <= TOLERANCE_LKR:
            cluster.append(p)
        else:
            clusters.append([p])
    return clusters


def consensus_summary(points: list[PricePoint]) -> dict[str, dict]:
    """Group raw news hits by fuel and report agreement counts."""
    by_fuel: dict[str, list[PricePoint]] = defaultdict(list)
    for p in points:
        by_fuel[p.fuel_type].append(p)

    summary: dict[str, dict] = {}
    for fuel, hits in by_fuel.items():
        clusters = _cluster_by_price(hits)
        best_hits = max(
            clusters,
            key=lambda group: (len(group), max(h.recorded_at for h in group)),
        )
        summary[fuel] = {
            "price_lkr": best_hits[0].price_lkr,
            "recorded_at": max(h.recorded_at for h in best_hits).isoformat(),
            "article_hits": len(hits),
            "agreeing_hits": len(best_hits),
            "consensus": len(best_hits) >= CONSENSUS_MIN,
        }
    return summary


def prefer_consensus(points: list[PricePoint]) -> list[PricePoint]:
    """Keep one row per fuel — prefer the price with the most agreeing hits.

    Does not drop single-outlet reports (revision day often starts with one
    wire story). Consensus is recorded in logs / scrape_run detail instead.
    """
    by_fuel: dict[str, list[PricePoint]] = defaultdict(list)
    for p in points:
        by_fuel[p.fuel_type].append(p)

    chosen: list[PricePoint] = []
    for _fuel, hits in by_fuel.items():
        clusters = _cluster_by_price(hits)
        best = max(
            clusters,
            key=lambda group: (len(group), max(h.recorded_at for h in group)),
        )
        best_sorted = sorted(best, key=lambda p: p.recorded_at, reverse=True)
        chosen.append(best_sorted[0])
    return chosen


def run_news(
    *,
    dry_run: bool = False,
    persist: bool = True,
    max_age_hours: int | None = None,
) -> dict:
    """Scrape news feeds and optionally persist to Postgres."""
    raw = list(
        news.run(max_age_hours=max_age_hours)
        if max_age_hours is not None
        else news.run()
    )
    selected = prefer_consensus(raw)
    summary = consensus_summary(raw)

    log.info(
        "news scrape: raw=%d selected=%d fuels=%s",
        len(raw),
        len(selected),
        {f: s["price_lkr"] for f, s in summary.items()},
    )
    for fuel, s in summary.items():
        log.info(
            "  %s → LKR %.2f on %s (hits=%d agreeing=%d consensus=%s)",
            fuel,
            s["price_lkr"],
            s["recorded_at"],
            s["article_hits"],
            s["agreeing_hits"],
            s["consensus"],
        )

    result = {
        "raw": len(raw),
        "selected": len(selected),
        "persisted": 0,
        "fuels": summary,
        "points": [
            {
                "fuel_type": p.fuel_type,
                "price_lkr": p.price_lkr,
                "recorded_at": p.recorded_at.isoformat(),
                "source": p.source,
            }
            for p in selected
        ],
    }

    if dry_run or not persist:
        log.info("dry-run / no-persist — skipping DB write")
        return result

    if not os.environ.get("DATABASE_URL"):
        log.error("DATABASE_URL not set — cannot persist")
        result["error"] = "DATABASE_URL not set"
        return result

    # Import DB helpers only when persisting (keeps dry-run lightweight).
    from app.db import migrate
    from app.scrapers.run import _persist_fuel, _record_scrape_run

    migrate.run()
    persisted = _persist_fuel(selected)
    consensus_fuels = [f for f, s in summary.items() if s["consensus"]]
    detail = (
        f"raw={len(raw)} selected={len(selected)} "
        f"consensus_fuels={consensus_fuels or 'none'}"
    )
    _record_scrape_run(
        "news",
        persisted,
        ok=True,
        detail=detail if selected else "0 rows (no matching headlines)",
    )
    result["persisted"] = persisted
    log.info("news scrape persisted %d rows (%s)", persisted, detail)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Octane news-only fuel price scraper")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and print results without writing to the database",
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=None,
        help="Only consider articles newer than this many hours (default: 14 days)",
    )
    args = parser.parse_args(argv)
    result = run_news(
        dry_run=args.dry_run,
        persist=not args.dry_run,
        max_age_hours=args.max_age_hours,
    )
    if result.get("error"):
        return 1
    # Exit 0 even when 0 rows — quiet days are normal between CPC revisions.
    return 0


if __name__ == "__main__":
    sys.exit(main())
