"""Fuel station API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException

from app.services import stations

router = APIRouter(prefix="/v1/stations", tags=["stations"])


@router.get("")
def list_stations(
    provider: str | None = Query(None, description="Filter by provider (CPC or LIOC)"),
    district: str | None = Query(None, description="Filter by district name"),
    fuel_type: str | None = Query(None, description="Filter by fuel type availability"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all fuel stations with optional filters."""
    return {
        "stations": stations.list_all(
            provider=provider,
            district=district,
            fuel_type=fuel_type,
            limit=limit,
            offset=offset,
        )
    }


@router.get("/nearby")
def find_nearby_stations(
    lat: float = Query(..., description="User latitude"),
    lon: float = Query(..., description="User longitude"),
    radius: float = Query(10, description="Search radius in km", ge=1, le=100),
    provider: str | None = Query(None, description="Filter by provider"),
    fuel_type: str | None = Query(None, description="Filter by fuel type"),
    limit: int = Query(20, ge=1, le=50),
):
    """Find stations near a location, sorted by distance."""
    return {
        "stations": stations.find_nearby(
            lat=lat,
            lon=lon,
            radius_km=radius,
            provider=provider,
            fuel_type=fuel_type,
            limit=limit,
        )
    }


@router.get("/districts")
def list_districts():
    """Get list of all districts with stations."""
    return {"districts": stations.list_districts()}


@router.get("/stats")
def get_stats():
    """Get station statistics."""
    return stations.get_stats()


@router.get("/{station_id}")
def get_station(station_id: int):
    """Get a single station by ID."""
    station = stations.get_by_id(station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station
