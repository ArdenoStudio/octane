from __future__ import annotations

import csv
import io
import json
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app import fuel as fuel_mod
from app.services import prices
from app.services import forecast as forecast_svc
from app.services import sentiment as sentiment_svc
from app.services import signals as signals_svc

router = APIRouter(prefix="/v1/prices", tags=["prices"])


@router.get("/latest")
def latest():
    rows = prices.latest_all()
    return {
        "prices": rows,
        # When Octane last successfully checked CPC — independent of revision age.
        "last_verified_at": prices.last_verified_at("cpc"),
        # News / LIOC figures ahead of or diverging from official CPC.
        "early_signals": signals_svc.early_signals(rows),
    }


@router.get("/history")
def history(
    fuel: str = Query(..., description="fuel type id, e.g. 'petrol_92'"),
    days: int = Query(730, ge=1, le=36500),
    source: str = Query("cpc"),
):
    if fuel not in fuel_mod.ALL_FUELS:
        raise HTTPException(status_code=400, detail=f"unknown fuel '{fuel}'")
    return {
        "fuel_type": fuel,
        "source": source,
        "days": days,
        "points": prices.history(fuel, days, source),
    }


@router.get("/changes")
def changes(source: str = Query("cpc"), limit: int = Query(200, ge=1, le=5000)):
    return {"source": source, "changes": prices.changes(source, limit)}


@router.get(
    "/history.csv",
    response_class=StreamingResponse,
    summary="Download price history as CSV",
    responses={200: {"content": {"text/csv": {}}}},
)
def history_csv(
    fuel: List[str] = Query(
        default=list(fuel_mod.ALL_FUELS),
        description="One or more fuel type ids. Defaults to all fuels.",
    ),
    days: int = Query(3650, ge=1, le=36500, description="Number of days of history to include."),
    source: str = Query("cpc"),
):
    requested = [f for f in fuel if f in fuel_mod.ALL_FUELS]
    if not requested:
        raise HTTPException(status_code=400, detail="No valid fuel types specified.")

    cutoff = date.today() - timedelta(days=days)
    rows: list[dict] = []
    for f in requested:
        for point in prices.history(f, days, source):
            rows.append({"recorded_at": point["recorded_at"], "fuel_type": f, "source": source, "price_lkr": point["price_lkr"]})

    rows.sort(key=lambda r: (r["recorded_at"], r["fuel_type"]))

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["recorded_at", "fuel_type", "source", "price_lkr"])
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)

    filename = f"octane-fuel-prices-{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/history.json",
    response_class=StreamingResponse,
    summary="Download price history as JSON",
    responses={200: {"content": {"application/json": {}}}},
)
def history_json(
    fuel: List[str] = Query(
        default=list(fuel_mod.ALL_FUELS),
        description="One or more fuel type ids. Defaults to all fuels.",
    ),
    days: int = Query(3650, ge=1, le=36500, description="Number of days of history to include."),
    source: str = Query("cpc"),
):
    requested = [f for f in fuel if f in fuel_mod.ALL_FUELS]
    if not requested:
        raise HTTPException(status_code=400, detail="No valid fuel types specified.")

    rows: list[dict] = []
    for f in requested:
        for point in prices.history(f, days, source):
            rows.append({
                "recorded_at": point["recorded_at"],
                "fuel_type": f,
                "source": source,
                "price_lkr": point["price_lkr"],
            })

    rows.sort(key=lambda r: (r["recorded_at"], r["fuel_type"]))

    payload = {
        "generated_at": date.today().isoformat(),
        "source": source,
        "fuels": requested,
        "days": days,
        "data": rows,
    }

    filename = f"octane-fuel-prices-{date.today().isoformat()}.json"
    return StreamingResponse(
        iter([json.dumps(payload, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/forecast", summary="Linear-regression price trend + AI-adjusted forecast")
def forecast(
    fuel: str = Query(..., description="Fuel type id, e.g. 'petrol_92'"),
    source: str = Query("cpc"),
    history_days: int = Query(365, ge=30, le=3650, description="Days of history to fit regression on"),
    horizon_days: int = Query(90, ge=7, le=365, description="Days ahead to forecast"),
):
    if fuel not in fuel_mod.ALL_FUELS:
        raise HTTPException(status_code=400, detail=f"unknown fuel '{fuel}'")
    return forecast_svc.forecast(fuel, source, history_days, horizon_days)


@router.get("/sentiment", summary="Latest AI news sentiment for fuel price direction")
def sentiment():
    sent = sentiment_svc.load()
    if sent is None:
        return {"available": False, "sentiment": None}
    return {
        "available": True,
        "sentiment": {
            "direction": sent.direction,
            "confidence": sent.confidence,
            "magnitude_lkr": sent.magnitude_lkr,
            "summary": sent.summary,
            "generated_at": sent.generated_at,
            "headlines_analyzed": sent.headlines_analyzed,
            "signals": sent.signals,
        },
    }
