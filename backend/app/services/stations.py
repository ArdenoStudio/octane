"""Fuel station service — query and manage station data."""
from __future__ import annotations

import math
from typing import TypedDict

from app.db.connection import connect


class StationOut(TypedDict):
    id: int
    name: str
    provider: str
    address: str | None
    city: str | None
    district: str | None
    latitude: float | None
    longitude: float | None
    phone: str | None
    operating_hours: str | None
    has_petrol_92: bool
    has_petrol_95: bool
    has_diesel: bool
    has_super_diesel: bool
    distance_km: float | None


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in km."""
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def _row_to_station(row: dict, user_lat: float | None = None, user_lon: float | None = None) -> StationOut:
    """Convert a database row to StationOut with optional distance calculation."""
    distance = None
    if user_lat is not None and user_lon is not None and row["latitude"] and row["longitude"]:
        distance = round(_haversine(user_lat, user_lon, float(row["latitude"]), float(row["longitude"])), 2)
    
    return {
        "id": row["id"],
        "name": row["name"],
        "provider": row["provider"],
        "address": row["address"],
        "city": row["city"],
        "district": row["district"],
        "latitude": float(row["latitude"]) if row["latitude"] else None,
        "longitude": float(row["longitude"]) if row["longitude"] else None,
        "phone": row["phone"],
        "operating_hours": row["operating_hours"],
        "has_petrol_92": row["has_petrol_92"],
        "has_petrol_95": row["has_petrol_95"],
        "has_diesel": row["has_diesel"],
        "has_super_diesel": row["has_super_diesel"],
        "distance_km": distance,
    }


def list_all(
    provider: str | None = None,
    district: str | None = None,
    fuel_type: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[StationOut]:
    """List all stations with optional filters."""
    conditions = []
    params: list = []
    
    if provider:
        conditions.append("provider = %s")
        params.append(provider.upper())
    
    if district:
        conditions.append("district ILIKE %s")
        params.append(f"%{district}%")
    
    if fuel_type:
        fuel_map = {
            "petrol_92": "has_petrol_92",
            "petrol_95": "has_petrol_95",
            "auto_diesel": "has_diesel",
            "super_diesel": "has_super_diesel",
        }
        col = fuel_map.get(fuel_type)
        if col:
            conditions.append(f"{col} = TRUE")
    
    where = " AND ".join(conditions) if conditions else "TRUE"
    params.extend([limit, offset])
    
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, name, provider, address, city, district,
                       latitude, longitude, phone, operating_hours,
                       has_petrol_92, has_petrol_95, has_diesel, has_super_diesel
                FROM fuel_stations
                WHERE {where}
                ORDER BY provider, district, name
                LIMIT %s OFFSET %s
                """,
                params,
            )
            return [_row_to_station(dict(r)) for r in cur.fetchall()]


def find_nearby(
    lat: float,
    lon: float,
    radius_km: float = 10,
    provider: str | None = None,
    fuel_type: str | None = None,
    limit: int = 50,
) -> list[StationOut]:
    """Find stations within a radius of a given location, sorted by distance."""
    # Get all stations with coordinates and filter in Python for accuracy
    conditions = ["latitude IS NOT NULL", "longitude IS NOT NULL"]
    params: list = []
    
    if provider:
        conditions.append("provider = %s")
        params.append(provider.upper())
    
    if fuel_type:
        fuel_map = {
            "petrol_92": "has_petrol_92",
            "petrol_95": "has_petrol_95",
            "auto_diesel": "has_diesel",
            "super_diesel": "has_super_diesel",
        }
        col = fuel_map.get(fuel_type)
        if col:
            conditions.append(f"{col} = TRUE")
    
    where = " AND ".join(conditions)
    
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, name, provider, address, city, district,
                       latitude, longitude, phone, operating_hours,
                       has_petrol_92, has_petrol_95, has_diesel, has_super_diesel
                FROM fuel_stations
                WHERE {where}
                """,
                params,
            )
            rows = [dict(r) for r in cur.fetchall()]
    
    # Calculate distances and filter
    stations_with_distance = []
    for row in rows:
        station = _row_to_station(row, lat, lon)
        if station["distance_km"] is not None and station["distance_km"] <= radius_km:
            stations_with_distance.append(station)
    
    # Sort by distance and limit
    stations_with_distance.sort(key=lambda s: s["distance_km"] or float("inf"))
    return stations_with_distance[:limit]


def get_by_id(station_id: int) -> StationOut | None:
    """Get a single station by ID."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, provider, address, city, district,
                       latitude, longitude, phone, operating_hours,
                       has_petrol_92, has_petrol_95, has_diesel, has_super_diesel
                FROM fuel_stations
                WHERE id = %s
                """,
                (station_id,),
            )
            row = cur.fetchone()
            if row:
                return _row_to_station(dict(row))
    return None


def list_districts() -> list[str]:
    """Get a list of all districts with stations."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT district FROM fuel_stations
                WHERE district IS NOT NULL
                ORDER BY district
                """
            )
            return [r["district"] for r in cur.fetchall()]


def get_stats() -> dict:
    """Get station statistics."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE provider = 'CPC') as cpc_count,
                    COUNT(*) FILTER (WHERE provider = 'LIOC') as lioc_count,
                    COUNT(DISTINCT district) as district_count
                FROM fuel_stations
                """
            )
            row = cur.fetchone()
            return {
                "total": row["total"],
                "cpc_count": row["cpc_count"],
                "lioc_count": row["lioc_count"],
                "district_count": row["district_count"],
            }
