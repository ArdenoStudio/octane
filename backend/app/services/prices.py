"""Price queries — read from fuel_prices."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app import fuel as fuel_mod
from app.db.connection import connect

# CPC and Lanka IOC both set administered retail prices in Sri Lanka.
OFFICIAL_SOURCES = ("cpc", "lanka_ioc")


def _iso_ts(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_date(value: str | date) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value)[:10])


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        raw = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def pick_official(cpc: dict | None, ioc: dict | None) -> dict | None:
    """Choose the more recently revised official price between CPC and LIOC.

    Primary key: recorded_at (revision / effective date).
    Tie-break: scraped_at, then prefer CPC as the stable default.
    """
    if not cpc and not ioc:
        return None
    if not cpc:
        return dict(ioc)  # type: ignore[arg-type]
    if not ioc:
        return dict(cpc)

    cpc_d = _parse_date(cpc["recorded_at"])
    ioc_d = _parse_date(ioc["recorded_at"])
    if ioc_d > cpc_d:
        return dict(ioc)
    if cpc_d > ioc_d:
        return dict(cpc)

    cpc_s = _parse_ts(cpc.get("scraped_at"))
    ioc_s = _parse_ts(ioc.get("scraped_at"))
    if ioc_s and (cpc_s is None or ioc_s > cpc_s):
        return dict(ioc)
    return dict(cpc)


def _row_by_source(rows: list[dict], fuel_type: str, source: str) -> dict | None:
    for r in rows:
        if r["fuel_type"] == fuel_type and r["source"] == source:
            return r
    return None


def official_latest(rows: list[dict] | None = None) -> list[dict]:
    """Latest official price per fuel — CPC vs Lanka IOC, most recent wins."""
    all_rows = rows if rows is not None else latest_all()
    out: list[dict] = []
    for fuel in fuel_mod.ALL_FUELS:
        picked = pick_official(
            _row_by_source(all_rows, fuel, "cpc"),
            _row_by_source(all_rows, fuel, "lanka_ioc"),
        )
        if picked:
            out.append(picked)
    return out


def last_verified_at(source: str = "cpc") -> str | None:
    """Most recent successful scrape check for a source.

    Pass source=\"official\" for the fresher of CPC and Lanka IOC checks.
    """
    if source == "official":
        stamps = [last_verified_at(s) for s in OFFICIAL_SOURCES]
        present = [s for s in stamps if s]
        return max(present) if present else None

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


def latest_for(fuel_type: str, source: str = "official") -> dict | None:
    """Latest price for a fuel.

    Default source=\"official\" picks the more recent of CPC and Lanka IOC.
    Pass \"cpc\", \"lanka_ioc\", or \"news\" for a specific stream.
    """
    if source == "official":
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (source)
                           fuel_type, source, price_lkr, recorded_at, scraped_at
                    FROM fuel_prices
                    WHERE fuel_type = %s AND source = ANY(%s)
                    ORDER BY source, recorded_at DESC
                    """,
                    (fuel_type, list(OFFICIAL_SOURCES)),
                )
                rows = [
                    {
                        "fuel_type": r["fuel_type"],
                        "source": r["source"],
                        "price_lkr": float(r["price_lkr"]),
                        "recorded_at": r["recorded_at"].isoformat(),
                        "scraped_at": _iso_ts(r["scraped_at"]),
                    }
                    for r in cur.fetchall()
                ]
        cpc = next((r for r in rows if r["source"] == "cpc"), None)
        ioc = next((r for r in rows if r["source"] == "lanka_ioc"), None)
        return pick_official(cpc, ioc)

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
