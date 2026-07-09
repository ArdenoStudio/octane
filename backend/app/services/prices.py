"""Price queries — read from fuel_prices."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.db.connection import connect


def _iso_ts(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def last_verified_at(source: str = "cpc") -> str | None:
    """Most recent successful scrape check for a source."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT checked_at
                FROM scrape_runs
                WHERE source = %s AND ok = TRUE
                ORDER BY checked_at DESC
                LIMIT 1
                """,
                (source,),
            )
            r = cur.fetchone()
            if r and r["checked_at"]:
                return _iso_ts(r["checked_at"])

            # Fallback for DBs that have not run the new scraper yet.
            cur.execute(
                """
                SELECT MAX(scraped_at) AS latest
                FROM fuel_prices
                WHERE source = %s AND scraped_at IS NOT NULL
                """,
                (source,),
            )
            r2 = cur.fetchone()
            return _iso_ts(r2["latest"]) if r2 and r2["latest"] else None


def latest_all() -> list[dict]:
    """Most recent price per (fuel_type, source)."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (fuel_type, source)
                       fuel_type, source, price_lkr, recorded_at, scraped_at
                FROM fuel_prices
                ORDER BY fuel_type, source, recorded_at DESC
                """
            )
            return [
                {
                    "fuel_type": r["fuel_type"],
                    "source": r["source"],
                    "price_lkr": float(r["price_lkr"]),
                    "recorded_at": r["recorded_at"].isoformat(),
                    "scraped_at": _iso_ts(r["scraped_at"]),
                }
                for r in cur.fetchall()
            ]


def latest_for(fuel_type: str, source: str = "cpc") -> dict | None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT fuel_type, source, price_lkr, recorded_at, scraped_at
                FROM fuel_prices
                WHERE fuel_type = %s AND source = %s
                ORDER BY recorded_at DESC
                LIMIT 1
                """,
                (fuel_type, source),
            )
            r = cur.fetchone()
    if not r:
        return None
    return {
        "fuel_type": r["fuel_type"],
        "source": r["source"],
        "price_lkr": float(r["price_lkr"]),
        "recorded_at": r["recorded_at"].isoformat(),
        "scraped_at": _iso_ts(r["scraped_at"]),
    }


def history(fuel_type: str, days: int, source: str = "cpc") -> list[dict]:
    cutoff = date.today() - timedelta(days=days)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT recorded_at, price_lkr
                FROM fuel_prices
                WHERE fuel_type = %s AND source = %s AND recorded_at >= %s
                ORDER BY recorded_at ASC
                """,
                (fuel_type, source, cutoff),
            )
            return [
                {
                    "recorded_at": r["recorded_at"].isoformat(),
                    "price_lkr": float(r["price_lkr"]),
                }
                for r in cur.fetchall()
            ]


def changes(source: str = "cpc", limit: int = 200) -> list[dict]:
    """Revision events with delta vs prior price, per fuel."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH ranked AS (
                  SELECT
                    fuel_type,
                    recorded_at,
                    price_lkr,
                    LAG(price_lkr) OVER (PARTITION BY fuel_type ORDER BY recorded_at)
                      AS prev_price
                  FROM fuel_prices
                  WHERE source = %s
                )
                SELECT fuel_type, recorded_at, price_lkr, prev_price
                FROM ranked
                WHERE prev_price IS NULL OR price_lkr <> prev_price
                ORDER BY recorded_at DESC
                LIMIT %s
                """,
                (source, limit),
            )
            rows = cur.fetchall()
    out: list[dict] = []
    for r in rows:
        prev = float(r["prev_price"]) if r["prev_price"] is not None else None
        cur_p = float(r["price_lkr"])
        delta = (cur_p - prev) if prev is not None else None
        pct = (delta / prev * 100) if prev not in (None, 0) else None
        out.append(
            {
                "fuel_type": r["fuel_type"],
                "recorded_at": r["recorded_at"].isoformat(),
                "price_lkr": cur_p,
                "previous_lkr": prev,
                "delta_lkr": delta,
                "delta_pct": pct,
            }
        )
    return out
