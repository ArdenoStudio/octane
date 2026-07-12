"""Tests for the CPC price scraper's HTML parsing logic."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.scrapers.cpc import (
    _parse_table,
    _parse_date,
    _parse_price,
    parse_latest_html,
)
from app import fuel as fuel_mod

FIXTURE = Path(__file__).parent / "fixtures" / "cpc_prices.html"
HOMEPAGE_FIXTURE = Path(__file__).parent / "fixtures" / "cpc_homepage.html"


def test_parse_table_returns_correct_row_count():
    html = FIXTURE.read_text()
    points = _parse_table(html)
    # 3 date rows × 5 fuels = 15 price points
    assert len(points) == 15


def test_parse_table_fuel_types_are_valid():
    html = FIXTURE.read_text()
    points = _parse_table(html)
    for p in points:
        assert p.fuel_type in fuel_mod.ALL_FUELS, f"unexpected fuel: {p.fuel_type}"


def test_parse_table_prices_in_range():
    html = FIXTURE.read_text()
    points = _parse_table(html)
    for p in points:
        assert 50 <= p.price_lkr <= 2000, f"price out of range: {p.price_lkr}"


def test_parse_table_dates_parsed():
    html = FIXTURE.read_text()
    points = _parse_table(html)
    dates = {p.recorded_at.isoformat() for p in points}
    assert "2024-01-15" in dates
    assert "2023-06-12" in dates
    assert "2022-11-01" in dates


def test_parse_table_source_is_cpc():
    html = FIXTURE.read_text()
    points = _parse_table(html)
    assert all(p.source == "cpc" for p in points)


def test_parse_table_known_price():
    html = FIXTURE.read_text()
    points = _parse_table(html)
    jan15_92 = next(
        (p for p in points if p.recorded_at.isoformat() == "2024-01-15" and p.fuel_type == fuel_mod.PETROL_92),
        None,
    )
    assert jan15_92 is not None
    assert jan15_92.price_lkr == 317.0


def test_parse_table_empty_html():
    assert _parse_table("<html><body></body></html>") == []


def test_parse_table_no_date_column():
    html = "<table><tr><th>Petrol 92</th></tr><tr><td>317</td></tr></table>"
    assert _parse_table(html) == []


def test_parse_date_formats():
    from datetime import date
    assert _parse_date("2024-01-15") == date(2024, 1, 15)
    assert _parse_date("15/01/2024") == date(2024, 1, 15)
    assert _parse_date("15-01-2024") == date(2024, 1, 15)
    assert _parse_date("15 January 2024") == date(2024, 1, 15)
    assert _parse_date("not-a-date") is None


def test_parse_price_basic():
    assert _parse_price("317.00") == 317.0
    assert _parse_price("LKR 317.00") == 317.0
    assert _parse_price("317,00") == 317.0  # comma stripped


def test_parse_price_invalid():
    assert _parse_price("N/A") is None
    assert _parse_price("") is None


def test_parse_latest_html_from_homepage_widget():
    html = HOMEPAGE_FIXTURE.read_text()
    as_of = date(2026, 7, 9)
    points = parse_latest_html(html, as_of=as_of)
    by_fuel = {p.fuel_type: p.price_lkr for p in points}
    assert by_fuel[fuel_mod.PETROL_92] == 311.0
    assert by_fuel[fuel_mod.PETROL_95] == 345.0
    assert by_fuel[fuel_mod.AUTO_DIESEL] == 291.0
    assert by_fuel[fuel_mod.SUPER_DIESEL] == 311.0
    assert by_fuel[fuel_mod.KEROSENE] == 185.0
    assert all(p.recorded_at == as_of for p in points)


def test_parse_latest_html_text_fallback():
    html = """
    <html><body>
      Petrol 92 Octane 317.00 Petrol 95 Octane 355.00
      Auto Diesel 293.00 Super Diesel 313.00 Kerosene 190.00
    </body></html>
    """
    points = parse_latest_html(html, as_of=date(2026, 7, 9))
    fuels = {p.fuel_type for p in points}
    assert fuel_mod.PETROL_92 in fuels
    assert fuel_mod.AUTO_DIESEL in fuels
    assert len(points) >= 3
