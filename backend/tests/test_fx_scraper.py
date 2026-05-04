"""Tests for the FX rate scraper."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from app.scrapers.fx import run, MIN_VALID_LKR, MAX_VALID_LKR


def _mock_client(json_data: dict):
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value=json_data)
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get = MagicMock(return_value=mock_response)
    return mock_client


def test_run_returns_fx_rate_on_valid_response():
    payload = {"result": "success", "rates": {"LKR": 299.75}}
    with patch("app.scrapers.fx.client", return_value=_mock_client(payload)):
        result = run()

    assert result is not None
    assert result.base == "USD"
    assert result.target == "LKR"
    assert result.rate == 299.75
    assert result.recorded_at == date.today()


def test_run_rejects_rate_below_min():
    payload = {"rates": {"LKR": MIN_VALID_LKR - 1}}
    with patch("app.scrapers.fx.client", return_value=_mock_client(payload)):
        assert run() is None


def test_run_rejects_rate_above_max():
    payload = {"rates": {"LKR": MAX_VALID_LKR + 1}}
    with patch("app.scrapers.fx.client", return_value=_mock_client(payload)):
        assert run() is None


def test_run_handles_missing_lkr_key():
    payload = {"rates": {"USD": 1.0, "EUR": 0.9}}
    with patch("app.scrapers.fx.client", return_value=_mock_client(payload)):
        assert run() is None


def test_run_handles_network_error():
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get = MagicMock(side_effect=Exception("connection refused"))

    with patch("app.scrapers.fx.client", return_value=mock_client):
        assert run() is None


def test_run_rate_is_rounded_to_4dp():
    payload = {"rates": {"LKR": 299.123456789}}
    with patch("app.scrapers.fx.client", return_value=_mock_client(payload)):
        result = run()
    assert result is not None
    assert result.rate == round(299.123456789, 4)
