"""Tests for TLS-tolerant HTTP helper and LIOC news fallback scraper."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.scrapers import lanka_ioc
from app.scrapers.cpc import PricePoint
from app.scrapers.http import _is_tls_verify_error, get_text


def test_is_tls_verify_error_detects_expired_cert():
    err = httpx.ConnectError(
        "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
        "certificate has expired (_ssl.c:1000)"
    )
    assert _is_tls_verify_error(err)
    assert not _is_tls_verify_error(httpx.ConnectError("[Errno -2] Name or service not known"))


def test_get_text_retries_without_verify_on_expired_cert():
    calls: list[bool] = []

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def __init__(self, *args, verify: bool = True, **kwargs):
            self.verify = verify

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, url: str):
            calls.append(self.verify)
            if self.verify:
                raise httpx.ConnectError(
                    "[SSL: CERTIFICATE_VERIFY_FAILED] certificate has expired"
                )
            return FakeResponse("<html>ok</html>")

    with patch("app.scrapers.http.client", FakeClient):
        text = get_text("https://ceypetco.gov.lk/", tls_fallback=True)

    assert text == "<html>ok</html>"
    assert calls == [True, False]


def test_get_text_does_not_fallback_on_dns_failure():
    class FakeClient:
        def __init__(self, *args, verify: bool = True, **kwargs):
            self.verify = verify

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, url: str):
            raise httpx.ConnectError("[Errno -2] Name or service not known")

    with patch("app.scrapers.http.client", FakeClient):
        with pytest.raises(httpx.ConnectError):
            get_text("https://lankaiocoil.lk/", tls_fallback=True)


def test_parse_official_html_extracts_fuels():
    html = """
    <html><body>
      Petrol 92 Octane 434.00 Petrol 95 Octane 495.00
      Auto Diesel 407.00 Super Diesel 478.00 Kerosene 285.00
    </body></html>
    """
    points = lanka_ioc._parse_official_html(html)
    by_fuel = {p.fuel_type: p.price_lkr for p in points}
    assert by_fuel["petrol_92"] == 434.0
    assert by_fuel["auto_diesel"] == 407.0
    assert all(p.source == "lanka_ioc" for p in points)


def test_merge_newest_per_fuel_prefers_later_revision():
    points = [
        PricePoint(date(2026, 3, 22), "petrol_92", 398.0, "lanka_ioc"),
        PricePoint(date(2026, 3, 22), "petrol_95", 487.0, "lanka_ioc"),
        PricePoint(date(2026, 3, 22), "super_diesel", 572.0, "lanka_ioc"),
        PricePoint(date(2026, 5, 31), "petrol_92", 434.0, "lanka_ioc"),
        PricePoint(date(2026, 5, 31), "auto_diesel", 407.0, "lanka_ioc"),
        PricePoint(date(2026, 4, 8), "super_diesel", 600.0, "lanka_ioc"),
    ]
    merged = lanka_ioc._merge_newest_per_fuel(points)
    by_fuel = {p.fuel_type: p.price_lkr for p in merged}
    assert by_fuel["petrol_92"] == 434.0
    assert by_fuel["petrol_95"] == 487.0  # carried from March
    assert by_fuel["auto_diesel"] == 407.0
    assert by_fuel["super_diesel"] == 600.0  # April beats March


def test_fetch_latest_uses_news_when_official_empty():
    news_points = [
        PricePoint(date(2026, 5, 31), "petrol_92", 434.0, "lanka_ioc"),
        PricePoint(date(2026, 5, 31), "auto_diesel", 407.0, "lanka_ioc"),
    ]
    with (
        patch.object(lanka_ioc, "fetch_from_official", return_value=[]),
        patch.object(lanka_ioc, "fetch_from_news", return_value=news_points),
    ):
        out = lanka_ioc.fetch_latest()
    assert out == news_points


def test_fetch_latest_prefers_rich_official_snapshot():
    official = [
        PricePoint(date(2026, 7, 12), "petrol_92", 434.0, "lanka_ioc"),
        PricePoint(date(2026, 7, 12), "petrol_95", 495.0, "lanka_ioc"),
        PricePoint(date(2026, 7, 12), "auto_diesel", 407.0, "lanka_ioc"),
    ]
    with (
        patch.object(lanka_ioc, "fetch_from_official", return_value=official),
        patch.object(lanka_ioc, "fetch_from_news") as news_mock,
    ):
        out = lanka_ioc.fetch_latest()
    assert out == official
    news_mock.assert_not_called()
