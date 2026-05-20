"""Simple linear-regression price forecast, optionally blended with AI sentiment.

Uses pure-Python math (no scipy/numpy) so it adds zero dependencies.
The regression is fitted on recent price history and projected forward.

Strategy
--------
Because CPC prices are step functions (constant until a revision), we
fit the regression on *revision events only* rather than daily fills —
the slope reflects the genuine rate of change between official revisions.

AI overlay
----------
When a sentiment snapshot is available (backend/data/ai_sentiment.json),
a second projection line is generated using the AI's predicted revision
magnitude. Both lines are returned; the frontend renders them separately.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.db.connection import connect
from app.services import sentiment as sentiment_svc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _linreg(xs: list[float], ys: list[float]) -> tuple[float, float, float, float]:
    """Return (slope, intercept, r_squared, std_error).

    Raises ValueError if fewer than 2 distinct points are provided.
    The std_error is the standard error of the residuals, used for confidence intervals.
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

    # Standard error of residuals (for confidence intervals)
    mse = ss_res / max(n - 2, 1)
    std_error = mse ** 0.5

    return slope, intercept, max(0.0, min(1.0, r2)), std_error


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
          "r_squared": float,           # 0-1 confidence
          "slope_lkr_per_day": float,   # how fast price is moving
          "regression_points": [...],   # fitted line over history window
          "forecast_points": [...],     # linear projection beyond today with confidence bands
          "ai_forecast_points": [...],  # AI-adjusted projection (may be [])
          "sentiment": {...} | null,    # current AI sentiment snapshot
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
            "ai_forecast_points": [],
            "sentiment": None,
            "error": "Not enough revision history to compute a trend.",
        }

    # Use the ordinal (days-since-epoch) of each revision date as x
    epoch = revisions[0][0].toordinal()
    xs = [float(d.toordinal() - epoch) for d, _ in revisions]
    ys = [price for _, price in revisions]
    n = len(xs)

    slope, intercept, r2, std_error = _linreg(xs, ys)

    # Calculate prediction interval multipliers
    # Using approximate t-values for 80% and 95% confidence
    # t(0.90, df) ≈ 1.3 for 80%, t(0.975, df) ≈ 2.0 for 95%
    t_80 = 1.28
    t_95 = 1.96

    # Mean of x for leverage calculation
    x_mean = sum(xs) / n
    ss_x = sum((x - x_mean) ** 2 for x in xs)

    today = date.today()
    today_x = float(today.toordinal() - epoch)

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

    # Linear forecast: daily points for the next horizon_days with confidence intervals
    forecast_points = []
    for i in range(1, horizon_days + 1):
        fd = today + timedelta(days=i)
        x_pred = float(fd.toordinal() - epoch)
        projected = slope * x_pred + intercept

        # Prediction interval width increases with distance from mean
        # SE_pred = std_error * sqrt(1 + 1/n + (x - x_mean)^2 / ss_x)
        leverage = 1 + 1/n + (x_pred - x_mean) ** 2 / max(ss_x, 1)
        se_pred = std_error * (leverage ** 0.5)

        conf_80 = t_80 * se_pred
        conf_95 = t_95 * se_pred

        forecast_points.append({
            "date": fd.isoformat(),
            "price_lkr": round(projected, 2),
            "conf_80_lower": round(projected - conf_80, 2),
            "conf_80_upper": round(projected + conf_80, 2),
            "conf_95_lower": round(projected - conf_95, 2),
            "conf_95_upper": round(projected + conf_95, 2),
        })

    # AI-adjusted forecast (uses sentiment magnitude if available)
    ai_forecast_points: list[dict] = []
    sentiment_out: dict | None = None

    sent = sentiment_svc.load()
    if sent is not None:
        sentiment_out = {
            "direction": sent.direction,
            "confidence": sent.confidence,
            "magnitude_lkr": sent.magnitude_lkr,
            "summary": sent.summary,
            "generated_at": sent.generated_at,
            "headlines_analyzed": sent.headlines_analyzed,
            "signals": sent.signals,
        }

        # AI slope: assume the predicted revision happens within 30 days,
        # then prices flatten at that new level.
        # We use the regression value at today as the base so the frontend's
        # existing offset-anchoring logic keeps the line connected correctly.
        today_reg_price = slope * today_x + intercept
        revision_horizon = 30  # days until expected revision
        ai_daily_slope = sent.magnitude_lkr / revision_horizon

        for i in range(1, horizon_days + 1):
            fd = today + timedelta(days=i)
            delta = ai_daily_slope * min(i, revision_horizon)
            ai_projected = today_reg_price + delta
            ai_forecast_points.append({
                "date": fd.isoformat(),
                "price_lkr": round(ai_projected, 2),
            })

    return {
        "fuel_type": fuel_type,
        "source": source,
        "r_squared": round(r2, 4),
        "slope_lkr_per_day": round(slope, 4),
        "regression_points": regression_points,
        "forecast_points": forecast_points,
        "ai_forecast_points": ai_forecast_points,
        "sentiment": sentiment_out,
    }
