"""Tests for news price extraction and consensus selection."""
from __future__ import annotations

from datetime import date

from app.scrapers.news import _extract_prices, _extract_price, _parse_effective_date
from app.scrapers.run_news import prefer_consensus, consensus_summary
from app.scrapers.cpc import PricePoint
from app import fuel as fuel_mod


def test_extract_price_prefers_to_rs():
    assert _extract_price("Petrol 92 reduced to Rs. 295 from Rs. 311") == 295.0


def test_extract_price_per_litre():
    assert _extract_price("Auto Diesel at 291 per litre") == 291.0


def test_extract_prices_from_article_text():
    text = (
        "The Ceylon Petroleum Corporation revised fuel prices effective 8 July 2026. "
        "Petrol 92 Octane will be sold at Rs. 295 per litre. "
        "Petrol 95 Octane to Rs. 325. Auto Diesel to Rs. 275. "
        "Super Diesel to Rs. 305 and Kerosene to Rs. 180."
    )
    points = _extract_prices(text, fallback_date=date(2026, 7, 8))
    by_fuel = {p.fuel_type: p.price_lkr for p in points}
    assert by_fuel[fuel_mod.PETROL_92] == 295.0
    assert by_fuel[fuel_mod.PETROL_95] == 325.0
    assert by_fuel[fuel_mod.AUTO_DIESEL] == 275.0
    assert all(p.source == "news" for p in points)
    assert all(p.recorded_at == date(2026, 7, 8) for p in points)


def test_extract_prices_handles_rs_dot_and_octane_wording():
    """Real Newswire wording — 'Rs.' must not break sentence splitting."""
    text = (
        "The Ceylon Petroleum Corporation (CPC) has announced a reduction in the prices of "
        "Petrol Octane 92 and Auto Diesel with effect from midnight today (29). Accordingly, "
        "the price of a litre of Petrol Octane 92 has been reduced by Rs. 20 to Rs. 414, while "
        "the price of Auto Diesel has been cut by Rs. 25 to Rs. 382."
    )
    points = _extract_prices(text, fallback_date=date(2026, 6, 29))
    by_fuel = {p.fuel_type: p.price_lkr for p in points}
    assert by_fuel[fuel_mod.PETROL_92] == 414.0
    assert by_fuel[fuel_mod.AUTO_DIESEL] == 382.0


def test_parse_effective_date():
    assert _parse_effective_date("effective from 8 July 2026") == date(2026, 7, 8)
    assert _parse_effective_date("with effect from 01/07/2026") == date(2026, 7, 1)


def test_prefer_consensus_picks_majority_price():
    points = [
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 295.0, source="news"),
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 295.0, source="news"),
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 300.0, source="news"),
        PricePoint(date(2026, 7, 8), fuel_mod.AUTO_DIESEL, 275.0, source="news"),
    ]
    selected = prefer_consensus(points)
    by_fuel = {p.fuel_type: p.price_lkr for p in selected}
    assert by_fuel[fuel_mod.PETROL_92] == 295.0
    assert by_fuel[fuel_mod.AUTO_DIESEL] == 275.0


def test_consensus_summary_flags_agreement():
    points = [
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 295.0, source="news"),
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 295.5, source="news"),
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_95, 325.0, source="news"),
    ]
    summary = consensus_summary(points)
    assert summary[fuel_mod.PETROL_92]["consensus"] is True
    assert summary[fuel_mod.PETROL_92]["agreeing_hits"] == 2
    assert summary[fuel_mod.PETROL_95]["consensus"] is False


def test_resolve_via_publisher_search_newswire():
    from app.scrapers.news import _resolve_via_publisher_search

    url = _resolve_via_publisher_search(
        "Fuel prices reduced in Sri Lanka - Newswire",
        "https://www.newswire.lk",
    )
    assert url is not None
    assert "newswire.lk" in url
    assert "/2026/" in url or "/fuel-prices-reduced" in url
