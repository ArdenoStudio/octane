"""Tests for news price extraction and consensus selection."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

from app.scrapers.news import (
    _extract_prices,
    _extract_price,
    _parse_effective_date,
    outlet_from_host,
)
from app.scrapers.run_news import prefer_consensus, consensus_summary
from app.scrapers.cpc import PricePoint
from app import fuel as fuel_mod


def test_extract_price_prefers_to_rs():
    assert _extract_price("Petrol 92 reduced to Rs. 295 from Rs. 311") == 295.0


def test_extract_price_skips_by_rs_delta():
    """'by Rs. 20' is a change amount, not the new retail price."""
    assert _extract_price("reduced by Rs. 20") is None
    assert _extract_price("increased by Rs. 24") is None
    # Still pick the new price when both delta and 'to Rs.' appear.
    assert _extract_price("reduced by Rs. 20 to Rs. 414") == 414.0


def test_extract_price_per_litre():
    assert _extract_price("Auto Diesel at 291 per litre") == 291.0


def test_extract_prices_skips_speculative_could_be():
    text = (
        "SJB: Petrol and diesel prices could have been reduced by Rs. 115 each per litre. "
        "Petrol 92 Octane is now priced at Rs. 414 per litre."
    )
    assert (
        _extract_prices(
            text,
            fallback_date=date(2026, 7, 1),
            title="SJB: Petrol and diesel prices could have been reduced",
            article_url="https://island.lk/sjb-petrol-could-have-been-reduced/",
        )
        == []
    )


def test_parse_article_published_date_prefers_byline_over_site_chrome():
    from bs4 import BeautifulSoup
    from app.scrapers.news import _parse_article_published_date

    html = """
    <html><body>
      <div class="header">Thu, 09 Jul 2026 - 08:42 PM</div>
      <h1>Fuel prices reduced</h1>
      <span>Sep 30, 2024</span>
      <p>The CPC has announced a revision...</p>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    assert _parse_article_published_date(soup, "https://adaderana.lk/news/102362") == date(
        2024, 9, 30
    )


def test_extract_prices_from_article_text():
    text = (
        "The Ceylon Petroleum Corporation revised fuel prices effective 8 July 2026. "
        "Petrol 92 Octane will be sold at Rs. 295 per litre. "
        "Petrol 95 Octane to Rs. 325. Auto Diesel to Rs. 275. "
        "Super Diesel to Rs. 305 and Kerosene to Rs. 180."
    )
    points = _extract_prices(
        text,
        fallback_date=date(2026, 7, 8),
        outlet="newswire",
        article_url="https://www.newswire.lk/example/",
    )
    by_fuel = {p.fuel_type: p.price_lkr for p in points}
    assert by_fuel[fuel_mod.PETROL_92] == 295.0
    assert by_fuel[fuel_mod.PETROL_95] == 325.0
    assert by_fuel[fuel_mod.AUTO_DIESEL] == 275.0
    assert all(p.source == "news" for p in points)
    assert all(p.outlet == "newswire" for p in points)
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


def test_outlet_from_host():
    assert outlet_from_host("https://www.newswire.lk/2026/06/29/fuel/") == "newswire"
    assert outlet_from_host("https://adaderana.lk") == "adaderana"
    assert outlet_from_host("https://www.dailymirror.lk/breaking-news/x/1") == "dailymirror"
    assert outlet_from_host("https://island.lk/fuel-prices-increased/") == "island"
    assert outlet_from_host("https://example.com") == "unknown"


def test_prefer_consensus_picks_majority_price():
    points = [
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 295.0, source="news", outlet="newswire"),
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 295.0, source="news", outlet="adaderana"),
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 300.0, source="news", outlet="unknown"),
        PricePoint(date(2026, 7, 8), fuel_mod.AUTO_DIESEL, 275.0, source="news", outlet="island"),
    ]
    selected = prefer_consensus(points)
    by_fuel = {p.fuel_type: p.price_lkr for p in selected}
    assert by_fuel[fuel_mod.PETROL_92] == 295.0
    assert by_fuel[fuel_mod.AUTO_DIESEL] == 275.0


def test_prefer_consensus_prefers_multi_outlet_over_newer_singleton():
    """Two outlets at 414 beat one newer outlet at 420."""
    points = [
        PricePoint(
            date(2026, 6, 29),
            fuel_mod.PETROL_92,
            414.0,
            source="news",
            outlet="newswire",
            article_url="https://www.newswire.lk/a/",
        ),
        PricePoint(
            date(2026, 6, 29),
            fuel_mod.PETROL_92,
            414.0,
            source="news",
            outlet="adaderana",
            article_url="https://www.adaderana.lk/news/1",
        ),
        PricePoint(
            date(2026, 7, 1),
            fuel_mod.PETROL_92,
            420.0,
            source="news",
            outlet="unknown",
            article_url="https://example.com/wrong",
        ),
    ]
    selected = prefer_consensus(points)
    assert len(selected) == 1
    assert selected[0].price_lkr == 414.0
    assert selected[0].outlet in {"newswire", "adaderana"}


def test_prefer_consensus_counts_distinct_outlets_not_duplicate_articles():
    """Three hits from the same outlet do not count as consensus."""
    points = [
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 295.0, source="news", outlet="newswire", article_url="a"),
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 295.0, source="news", outlet="newswire", article_url="b"),
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 295.0, source="news", outlet="newswire", article_url="c"),
    ]
    summary = consensus_summary(points)
    assert summary[fuel_mod.PETROL_92]["consensus"] is False
    assert summary[fuel_mod.PETROL_92]["agreeing_outlets"] == 1


def test_consensus_summary_flags_agreement():
    points = [
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 295.0, source="news", outlet="newswire"),
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_92, 295.5, source="news", outlet="island"),
        PricePoint(date(2026, 7, 8), fuel_mod.PETROL_95, 325.0, source="news", outlet="adaderana"),
    ]
    summary = consensus_summary(points)
    assert summary[fuel_mod.PETROL_92]["consensus"] is True
    assert summary[fuel_mod.PETROL_92]["agreeing_outlets"] == 2
    assert set(summary[fuel_mod.PETROL_92]["outlets"]) == {"newswire", "island"}
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


def test_resolve_via_publisher_search_island():
    from app.scrapers.news import _resolve_via_publisher_search

    url = _resolve_via_publisher_search(
        "Fuel prices increased - The island.lk",
        "http://island.lk",
    )
    assert url is not None
    assert "island.lk" in url
    assert "fuel" in url.lower()


def test_resolve_via_ddg_picks_best_slug_match():
    """Unit-test DDG ranking without depending on live search availability."""
    from app.scrapers import news as news_mod

    fake = [
        "https://www.adaderana.lk/news/1/unrelated-sports",
        "https://www.adaderana.lk/news/120058/fuel-prices-increased",
        "https://example.com/other",
    ]
    with patch.object(news_mod, "_ddg_search_urls", return_value=fake):
        url = news_mod._resolve_via_publisher_search(
            "Fuel prices increased - Ada Derana",
            "https://adaderana.lk",
        )
    assert url == "https://www.adaderana.lk/news/120058/fuel-prices-increased"


def test_resolve_via_ddg_dailymirror_pattern():
    from app.scrapers import news as news_mod

    fake = [
        "https://www.dailymirror.lk/breaking-news/Fuel-prices-increased/108-334878",
    ]
    with patch.object(news_mod, "_ddg_search_urls", return_value=fake):
        # Force the on-site search path to fail so DDG fallback runs.
        with patch("httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value.get.side_effect = Exception(
                "403"
            )
            url = news_mod._resolve_via_publisher_search(
                "Fuel prices increased - Daily Mirror",
                "https://www.dailymirror.lk",
            )
    assert url is not None
    assert "dailymirror.lk" in url
