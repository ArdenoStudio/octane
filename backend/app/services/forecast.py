"""Simple linear-regression price forecast.

Uses pure-Python math (no scipy/numpy) so it adds zero dependencies.
The regression is fitted on recent price history and projected forward.

Strategy
--------
Because CPC prices are step functions (constant until a revision), we
fit the regression on *revision events only* rather than daily fills —
the slope reflects the genuine rate of change between official revisions.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.db.connection import connect


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _linreg(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Return (slope, intercept, r_squared).

    Raises ValueError if fewer than 2 distinct points are provided.
    """
    n = len(xs)
    if n < 2:
        raise ValueError("need at least 2 points for regression")

    sx = sum(xs)
    sy = sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sxx = sum(x * x for x in xs)
    syy = sum(y * y for y in ys)

    denom = n * sxx - sx * sx
    if denom == 0:
        raise ValueError("all x values identical — cannot fit a line")

    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n

    # Pearson r²
    ss_tot = syy - sy * sy / n
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot != 0 else 0.0

    return slope, intercept, max(0.0, min(1.0, r2))


def _fetch_revisions(fuel_type: str, source: str, days: int) -> list[tuple[date, float]]:
    """Return (date, price_lkr) for each distinct price revision in the window."""
    cutoff = date.today() - timedelta(days=days)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH ranked AS (
                  SELECT recorded_at, price_lkr,
                         LAG(price_lkr) OVER (ORDER BY recorded_at) AS prev_price
                  FROM fuel_prices
                  WHERE fuel_type = %s AND source = %s AND recorded_at >= %s
                )
                SELECT recorded_at, price_lkr
                FROM ranked
                WHERE prev_price IS NULL OR price_lkr <> prev_price
                ORDER BY recorded_at ASC
                """,
                (fuel_type, source, cutoff),
            )
            return [(r["recorded_at"], float(r["price_lkr"])) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def forecast(
    fuel_type: str,
    source: str = "cpc",
    history_days: int = 365,
    horizon_days: int = 90,
) -> dict:
    """Fit a linear trend on recent revision history and project forward.

    Returns::

        {
          "fuel_type": str,
          "source": str,
          "r_squared": float,          # 0-1 confidence
          "slope_lkr_per_day": float,  # how fast price is moving
          "regression_points": [       # fitted line over history window
              {"date": "YYYY-MM-DD", "price_lkr": float}, ...
          ],
          "forecast_points": [         # projected prices beyond today
              {"date": "YYYY-MM-DD", "price_lkr": float}, ...
          ],
        }
    """
    revisions = _fetch_revisions(fuel_type, source, history_days)
    if len(revisions) < 2:
        return {
            "fuel_type": fuel_type,
            "source": source,
            "r_squared": None,
            "slope_lkr_per_day": None,
            "regression_points": [],
            "forecast_points": [],
            "error": "Not enough revision history to compute a trend.",
        }

    # Use the ordinal (days-since-epoch) of each revision date as x
    epoch = revisions[0][0].toordinal()
    xs = [float(d.toordinal() - epoch) for d, _ in revisions]
    ys = [price for _, price in revisions]

    slope, intercept, r2 = _linreg(xs, ys)

    today = date.today()

    # Regression line over the history window (one point per revision date +
    # today's end-of-window point for visual continuity)
    reg_dates = sorted({d for d, _ in revisions} | {today})
    regression_points = [
        {
            "date": d.isoformat(),
            "price_lkr": round(slope * (d.toordinal() - epoch) + intercept, 2),
        }
        for d in reg_dates
    ]

    # Forecast: daily points for the next horizon_days
    forecast_points = []
    for i in range(1, horizon_days + 1):
        fd = today + timedelta(days=i)
        projected = slope * (fd.toordinal() - epoch) + intercept
        forecast_points.append({
            "date": fd.isoformat(),
            "price_lkr": round(projected, 2),
        })

    return {
        "fuel_type": fuel_type,
        "source": source,
        "r_squared": round(r2, 4),
        "slope_lkr_per_day": round(slope, 4),
        "regression_points": regression_points,
        "forecast_points": forecast_points,
    }
