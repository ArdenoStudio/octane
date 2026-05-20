"""CPC and LIOC fuel station data scraper.

This module provides functions to scrape station location data from
official CPC and LIOC websites and convert addresses to coordinates.
"""
from __future__ import annotations

import logging
import re
from typing import TypedDict
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from app.config import get_settings
from app.db.connection import cursor

log = logging.getLogger(__name__)


class StationData(TypedDict, total=False):
    name: str
    provider: str
    address: str
    city: str
    district: str
    latitude: float | None
    longitude: float | None
    phone: str | None
    operating_hours: str | None


# Sri Lanka districts for fuzzy matching
SRI_LANKA_DISTRICTS = [
    "Colombo", "Gampaha", "Kalutara", "Kandy", "Matale", "Nuwara Eliya",
    "Galle", "Matara", "Hambantota", "Jaffna", "Kilinochchi", "Mannar",
    "Mullaitivu", "Vavuniya", "Trincomalee", "Batticaloa", "Ampara",
    "Kurunegala", "Puttalam", "Anuradhapura", "Polonnaruwa", "Badulla",
    "Monaragala", "Ratnapura", "Kegalle",
]


def _get_geocoder() -> Nominatim:
    """Get a geocoder instance with proper user agent."""
    s = get_settings()
    return Nominatim(user_agent=s.scraper_user_agent, timeout=10)


def _geocode_address(address: str, city: str | None = None) -> tuple[float | None, float | None]:
    """Geocode an address to coordinates using Nominatim."""
    geocoder = _get_geocoder()
    
    # Build search query with Sri Lanka context
    query = address
    if city:
        query = f"{address}, {city}"
    query = f"{query}, Sri Lanka"
    
    try:
        location = geocoder.geocode(query, addressdetails=True)
        if location:
            return location.latitude, location.longitude
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        log.warning("Geocoding failed for %s: %s", address, e)
    
    return None, None


def _extract_district(address: str) -> str | None:
    """Try to extract district name from address string."""
    address_lower = address.lower()
    for district in SRI_LANKA_DISTRICTS:
        if district.lower() in address_lower:
            return district
    return None


def _extract_city(address: str) -> str | None:
    """Try to extract city from address (usually first part before comma)."""
    parts = address.split(",")
    if parts:
        return parts[0].strip()
    return None


def scrape_cpc_stations() -> list[StationData]:
    """Scrape CPC fuel station data.
    
    Note: This is a placeholder implementation. The actual scraping logic
    would depend on the structure of CPC's website. Currently returns
    sample data for major cities.
    """
    # CPC doesn't have a public API or easily scrapable station list
    # This returns curated sample data for major Sri Lankan cities
    sample_stations: list[StationData] = [
        {"name": "CPC Colombo Fort", "provider": "CPC", "address": "York Street, Colombo 01", "city": "Colombo", "district": "Colombo", "latitude": 6.9355, "longitude": 79.8449},
        {"name": "CPC Borella", "provider": "CPC", "address": "Borella Junction, Colombo 08", "city": "Colombo", "district": "Colombo", "latitude": 6.9147, "longitude": 79.8773},
        {"name": "CPC Bambalapitiya", "provider": "CPC", "address": "Galle Road, Bambalapitiya", "city": "Colombo", "district": "Colombo", "latitude": 6.8939, "longitude": 79.8567},
        {"name": "CPC Rajagiriya", "provider": "CPC", "address": "Parliament Road, Rajagiriya", "city": "Rajagiriya", "district": "Colombo", "latitude": 6.9062, "longitude": 79.8943},
        {"name": "CPC Nugegoda", "provider": "CPC", "address": "High Level Road, Nugegoda", "city": "Nugegoda", "district": "Colombo", "latitude": 6.8722, "longitude": 79.8892},
        {"name": "CPC Kandy City", "provider": "CPC", "address": "Peradeniya Road, Kandy", "city": "Kandy", "district": "Kandy", "latitude": 7.2906, "longitude": 80.6337},
        {"name": "CPC Galle", "provider": "CPC", "address": "Matara Road, Galle", "city": "Galle", "district": "Galle", "latitude": 6.0535, "longitude": 80.2210},
        {"name": "CPC Negombo", "provider": "CPC", "address": "Colombo Road, Negombo", "city": "Negombo", "district": "Gampaha", "latitude": 7.2094, "longitude": 79.8358},
        {"name": "CPC Kurunegala", "provider": "CPC", "address": "Colombo Road, Kurunegala", "city": "Kurunegala", "district": "Kurunegala", "latitude": 7.4863, "longitude": 80.3623},
        {"name": "CPC Jaffna", "provider": "CPC", "address": "Hospital Road, Jaffna", "city": "Jaffna", "district": "Jaffna", "latitude": 9.6615, "longitude": 80.0255},
        {"name": "CPC Matara", "provider": "CPC", "address": "Anagarika Dharmapala Mawatha, Matara", "city": "Matara", "district": "Matara", "latitude": 5.9549, "longitude": 80.5550},
        {"name": "CPC Anuradhapura", "provider": "CPC", "address": "Maithripala Senanayake Mawatha, Anuradhapura", "city": "Anuradhapura", "district": "Anuradhapura", "latitude": 8.3114, "longitude": 80.4037},
    ]
    return sample_stations


def scrape_lioc_stations() -> list[StationData]:
    """Scrape LIOC (Lanka IOC) fuel station data.
    
    Note: This is a placeholder implementation. The actual scraping logic
    would depend on the structure of LIOC's website. Currently returns
    sample data for major cities.
    """
    # LIOC (Lanka Indian Oil Corporation) sample stations
    sample_stations: list[StationData] = [
        {"name": "LIOC Kollupitiya", "provider": "LIOC", "address": "Galle Road, Kollupitiya", "city": "Colombo", "district": "Colombo", "latitude": 6.9122, "longitude": 79.8498},
        {"name": "LIOC Wellawatte", "provider": "LIOC", "address": "Galle Road, Wellawatte", "city": "Colombo", "district": "Colombo", "latitude": 6.8742, "longitude": 79.8612},
        {"name": "LIOC Maharagama", "provider": "LIOC", "address": "High Level Road, Maharagama", "city": "Maharagama", "district": "Colombo", "latitude": 6.8471, "longitude": 79.9259},
        {"name": "LIOC Moratuwa", "provider": "LIOC", "address": "Galle Road, Moratuwa", "city": "Moratuwa", "district": "Colombo", "latitude": 6.7742, "longitude": 79.8822},
        {"name": "LIOC Kadawatha", "provider": "LIOC", "address": "Kandy Road, Kadawatha", "city": "Kadawatha", "district": "Gampaha", "latitude": 6.9865, "longitude": 79.9528},
        {"name": "LIOC Panadura", "provider": "LIOC", "address": "Galle Road, Panadura", "city": "Panadura", "district": "Kalutara", "latitude": 6.7142, "longitude": 79.9042},
        {"name": "LIOC Ratnapura", "provider": "LIOC", "address": "Main Street, Ratnapura", "city": "Ratnapura", "district": "Ratnapura", "latitude": 6.6828, "longitude": 80.3992},
        {"name": "LIOC Trincomalee", "provider": "LIOC", "address": "Main Street, Trincomalee", "city": "Trincomalee", "district": "Trincomalee", "latitude": 8.5874, "longitude": 81.2152},
        {"name": "LIOC Batticaloa", "provider": "LIOC", "address": "Main Street, Batticaloa", "city": "Batticaloa", "district": "Batticaloa", "latitude": 7.7310, "longitude": 81.6924},
        {"name": "LIOC Badulla", "provider": "LIOC", "address": "Main Street, Badulla", "city": "Badulla", "district": "Badulla", "latitude": 6.9934, "longitude": 81.0550},
    ]
    return sample_stations


def save_stations(stations: list[StationData]) -> int:
    """Save stations to database, updating existing ones by name+provider."""
    saved = 0
    for station in stations:
        try:
            with cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO fuel_stations (
                        name, provider, address, city, district,
                        latitude, longitude, phone, operating_hours,
                        updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (name, provider) DO UPDATE SET
                        address = EXCLUDED.address,
                        city = EXCLUDED.city,
                        district = EXCLUDED.district,
                        latitude = COALESCE(EXCLUDED.latitude, fuel_stations.latitude),
                        longitude = COALESCE(EXCLUDED.longitude, fuel_stations.longitude),
                        phone = EXCLUDED.phone,
                        operating_hours = EXCLUDED.operating_hours,
                        updated_at = NOW()
                    """,
                    (
                        station["name"],
                        station["provider"],
                        station.get("address"),
                        station.get("city"),
                        station.get("district"),
                        station.get("latitude"),
                        station.get("longitude"),
                        station.get("phone"),
                        station.get("operating_hours"),
                    ),
                )
                saved += 1
        except Exception as e:
            log.error("Failed to save station %s: %s", station.get("name"), e)
    return saved


def refresh_all_stations() -> dict:
    """Scrape and save all stations from both providers."""
    cpc = scrape_cpc_stations()
    lioc = scrape_lioc_stations()
    
    cpc_saved = save_stations(cpc)
    lioc_saved = save_stations(lioc)
    
    return {
        "cpc_scraped": len(cpc),
        "cpc_saved": cpc_saved,
        "lioc_scraped": len(lioc),
        "lioc_saved": lioc_saved,
    }
