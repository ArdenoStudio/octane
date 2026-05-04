"""Tests for the world price scraper's HTML parsing logic."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.scrapers.world import _extract_price, _extract_world_avg_pct, fetch

FIXTURE = Path(__file__).parent / "fixtures" / "world_gasoline.html"


def _soup(html: str):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "lxml")


def test_extract_price_from_fixture():
    soup = _soup(FIXTURE.read_text())
    price = _extract_price(soup)
    assert price == 1.280


def test_extract_price_not_found():
    soup = _soup("<html><body><p>nothing here</p></body></html>")
    assert _extract_price(soup) is None


def test_extract_price_ignores_non_numeric():
    html = "<table><tr><td>Current price</td><td>N/A</td></tr></table>"
    assert _extract_price(_soup(html)) is None


def test_extract_world_avg_pct_from_fixture():
    soup = _soup(FIXTURE.read_text())
    pct = _extract_world_avg_pct(soup)
    assert pct == 123.4


def test_extract_world_avg_pct_not_found():
    soup = _soup("<html><body></body></html>")
    assert _extract_world_avg_pct(soup) is None


def test_fetch_skips_out_of_range_prices():
    """Prices outside 0.10–10.00 USD/L should be discarded."""
    html = "<table><tr><td>Current price</td><td>99.99</td></tr></table>"
    mock_response = MagicMock()
    mock_response.text = html
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get = MagicMock(return_value=mock_response)

    with patch("app.scrapers.world.client", return_value=mock_client):
        results = fetch("gasoline")

    assert results == []


def test_fetch_happy_path():
    """A valid price page should produce one WorldPrice per country."""
    html = FIXTURE.read_text()
    mock_response = MagicMock()
    mock_response.text = html
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get = MagicMock(return_value=mock_response)

    with patch("app.scrapers.world.client", return_value=mock_client):
        results = fetch("gasoline")

    # 6 countries + 1 world average derived from Sri Lanka's page
    assert len(results) == 7
    countries = {r.country for r in results}
    assert "Sri Lanka" in countries
    assert "World" in countries
    assert all(r.fuel_type == "gasoline" for r in results)


def test_fetch_network_error_returns_empty():
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get = MagicMock(side_effect=Exception("network error"))

    with patch("app.scrapers.world.client", return_value=mock_client):
        results = fetch("gasoline")

    assert results == []
