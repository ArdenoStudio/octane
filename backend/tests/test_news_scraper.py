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
    assert outlet_from_host("https://www.onlanka.com/news/sri-lanka-revises-fuel-prices-from-june-30-2026.html") == "onlanka"
    assert outlet_from_host("https://lankanewsweb.net/archives/226278/fuel-prices-reduced/") == "lankanewsweb"
    assert outlet_from_host("https://english.newsfirst.lk/2026/06/30/fuel-prices-reduced/") == "newsfirst"
    assert outlet_from_host("https://www.themorning.lk/articles/BaLVZbOkscOFkRbNhy4P") == "themorning"
    assert outlet_from_host("https://www.ft.lk/business/Govt-revises-fuel-prices/34") == "dailyft"
    assert outlet_from_host(
        "https://www.sundaytimes.lk/260630/news/fuel-prices-reduced-from-tonight-648000.html"
    ) == "sundaytimes"
    assert outlet_from_host("https://srilankamirror.com/news/fuel-prices-reduced") == "srilankamirror"
    assert outlet_from_host("https://example.com") == "unknown"


def test_date_hint_from_url_and_ft_byline():
    from app.scrapers.news import _date_hint_from_url, _parse_article_published_date
    from bs4 import BeautifulSoup

    assert _date_hint_from_url(
        "https://english.newsfirst.lk/2026/06/30/fuel-prices-reduced/"
    ) == date(2026, 6, 30)
    assert _date_hint_from_url(
        "https://www.sundaytimes.lk/260503/news/fuel-prices-hiked-again-640961.html"
    ) == date(2026, 5, 3)
    assert _date_hint_from_url(
        "https://www.sundaytimes.lk/210620/columns/old-hike-446923.html"
    ) == date(2021, 6, 20)

    soup = BeautifulSoup(
        "<html><body>PAPER Tuesday, 6 January 2026 02:46 - - hits</body></html>",
        "lxml",
    )
    assert _parse_article_published_date(
        soup, "https://www.ft.lk/front-page/Ceypetco-revises/44-786572"
    ) == date(2026, 1, 6)


def test_looks_like_cloudflare():
    from app.scrapers.news import _looks_like_cloudflare

    assert _looks_like_cloudflare(403, "forbidden")
    assert _looks_like_cloudflare(200, "<html><title>Just a moment...</title></html>")
    assert not _looks_like_cloudflare(200, "<html><title>Fuel prices reduced</title></html>")


def test_fetch_article_content_falls_back_to_jina_on_403():
    from unittest.mock import MagicMock
    from app.scrapers.news import _fetch_article_content, JINA_READER_PREFIX

    blocked = MagicMock()
    blocked.is_success = False
    blocked.status_code = 403
    blocked.text = "<html><title>Just a moment...</title></html>"
    blocked.url = "https://srilankamirror.com/biz/fuel-prices-slashed-3/"

    jina = MagicMock()
    jina.is_success = True
    jina.status_code = 200
    jina.text = (
        "Title: Fuel prices slashed\n\n"
        "URL Source: https://srilankamirror.com/biz/fuel-prices-slashed-3/\n\n"
        "Markdown Content:\n"
        "The Ceylon Petroleum Corporation (Ceypetco) has announced a revision "
        "of fuel prices, effective from midnight today (June 29).\n"
        "Auto Diesel – Rs. 382 (reduced by Rs. 25)\n"
        "Super Diesel – Rs. 478 (unchanged)\n"
        "Petrol 92 Octane – Rs. 414 (reduced by Rs. 20)\n"
        "Petrol 95 Octane – Rs. 495 (unchanged)\n"
        "Kerosene – Rs. 285 (unchanged)\n"
    )
    jina.raise_for_status = MagicMock()

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, **kwargs):
            if url.startswith(JINA_READER_PREFIX):
                return jina
            return blocked

    with patch("app.scrapers.news.httpx.Client", FakeClient):
        fetched = _fetch_article_content(
            "https://srilankamirror.com/biz/fuel-prices-slashed-3/"
        )
    assert fetched is not None
    final_url, content, mode = fetched
    assert mode == "text"
    assert "Rs. 414" in content
    assert final_url.endswith("fuel-prices-slashed-3/")


def test_fetch_article_content_falls_back_to_jina_on_429():
    from unittest.mock import MagicMock
    from app.scrapers.news import _fetch_article_content, JINA_READER_PREFIX

    limited = MagicMock()
    limited.is_success = False
    limited.status_code = 429
    limited.text = "Too Many Requests"
    limited.url = "https://www.newsfirst.lk/2026/06/30/fuel-prices-reduced/"

    jina = MagicMock()
    jina.is_success = True
    jina.status_code = 200
    jina.text = (
        "Title: Fuel Prices Reduced From Midnight Yesterday\n\n"
        "URL Source: https://www.newsfirst.lk/2026/06/30/fuel-prices-reduced/\n\n"
        "Markdown Content:\n"
        "COLOMBO (News 1st): The Ceylon Petroleum Corporation (CPC) has announced "
        "a reduction in fuel prices effective from midnight yesterday. "
        "Accordingly, the price of Octane 92 petrol has been reduced by Rs. 20 "
        "per litre, bringing the new price down to Rs. 414. "
        "The price of Lanka Auto Diesel has also been reduced by Rs. 25 per litre, "
        "with the new price set at Rs. 382 per litre.\n"
    )
    jina.raise_for_status = MagicMock()

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, **kwargs):
            if url.startswith(JINA_READER_PREFIX):
                return jina
            return limited

    with patch("app.scrapers.news.httpx.Client", FakeClient):
        fetched = _fetch_article_content(
            "https://www.newsfirst.lk/2026/06/30/fuel-prices-reduced/"
        )
    assert fetched is not None
    assert fetched[2] == "text"
    assert "414" in fetched[1]


def test_sanitize_drops_petrol_95_equal_to_super_diesel():
    """Mirror June wire typo: P95 listed as Rs. 478 (= Super Diesel)."""
    text = (
        "Auto Diesel – Rs. 382 (reduced by Rs. 25) "
        "Super Diesel – Rs. 478 (unchanged) "
        "Petrol 92 Octane – Rs. 414 (reduced by Rs. 20) "
        "Petrol 95 Octane – Rs. 478 (unchanged) "
        "Kerosene – Rs. 285 (unchanged)"
    )
    points = _extract_prices(
        text,
        fallback_date=date(2026, 6, 29),
        outlet="srilankamirror",
    )
    by_fuel = {p.fuel_type: p.price_lkr for p in points}
    assert by_fuel[fuel_mod.PETROL_92] == 414.0
    assert by_fuel[fuel_mod.AUTO_DIESEL] == 382.0
    assert by_fuel[fuel_mod.SUPER_DIESEL] == 478.0
    assert by_fuel[fuel_mod.KEROSENE] == 285.0
    assert fuel_mod.PETROL_95 not in by_fuel


def test_guess_slmirror_urls_and_resolve():
    from app.scrapers.news import _guess_slmirror_urls, _resolve_via_publisher_search

    guesses = _guess_slmirror_urls("Fuel prices slashed - Sri Lanka Mirror")
    assert "https://srilankamirror.com/biz/fuel-prices-slashed/" in guesses
    assert "https://srilankamirror.com/biz/fuel-prices-slashed-3/" in guesses

    # Live: slug guess should find the June 29 wire via Jina when search is mocked empty.
    with patch("app.scrapers.news._resolve_via_web_search", return_value=None):
        url = _resolve_via_publisher_search(
            "Fuel prices slashed - Sri Lanka Mirror",
            "https://srilankamirror.com/",
        )
    assert url is not None
    assert "fuel-prices-slashed" in url
    assert "srilankamirror.com" in url


def test_scrape_article_uses_jina_text_mode():
    from datetime import datetime, timezone
    from app.scrapers.news import _scrape_article

    jina_md = (
        "Title: Fuel prices slashed\n\n"
        "The Ceylon Petroleum Corporation announced a revision.\n"
        "Petrol 92 Octane – Rs. 414\n"
        "Auto Diesel – Rs. 382\n"
        "Super Diesel – Rs. 478\n"
        "Petrol 95 Octane – Rs. 495\n"
        "Kerosene – Rs. 285\n"
    )
    with patch(
        "app.scrapers.news._fetch_article_content",
        return_value=(
            "https://srilankamirror.com/biz/fuel-prices-slashed-3/",
            jina_md,
            "text",
        ),
    ):
        points = _scrape_article(
            "https://srilankamirror.com/biz/fuel-prices-slashed-3/",
            datetime(2026, 6, 29, tzinfo=timezone.utc),
            title="Fuel prices slashed",
            source_url="https://srilankamirror.com/",
        )
    by_fuel = {p.fuel_type: p.price_lkr for p in points}
    assert by_fuel[fuel_mod.PETROL_92] == 414.0
    assert by_fuel[fuel_mod.PETROL_95] == 495.0
    assert by_fuel[fuel_mod.AUTO_DIESEL] == 382.0
    assert points[0].outlet == "srilankamirror"


def test_extract_prices_lnw_fixed_at_and_octane_petrol_wording():
    """LNW wording: 'Octane 92 petrol' + 'fixed at Rs. 382' after a long clause."""
    text = (
        "Under the latest revision, the price of Octane 92 petrol has been lowered by Rs. 20 "
        "per litre, bringing its new retail price to Rs. 414. Lanka Auto Diesel (white diesel) "
        "has received an even larger reduction of Rs. 25 per litre, with the revised selling "
        "price now fixed at Rs. 382. The CEYPETCO confirmed that there will be no changes to "
        "the prices of Octane 95 petrol, Super Diesel or Kerosene."
    )
    points = _extract_prices(text, fallback_date=date(2026, 6, 30), outlet="lankanewsweb")
    by_fuel = {p.fuel_type: p.price_lkr for p in points}
    assert by_fuel[fuel_mod.PETROL_92] == 414.0
    assert by_fuel[fuel_mod.AUTO_DIESEL] == 382.0


def test_extract_prices_onlanka_table_wording():
    text = (
        "The Ceylon Petroleum Corporation (CEYPETCO) has announced the updated fuel prices "
        "as follows: The price of Petrol 92 Octane has been reduced by Rs. 20, bringing the "
        "new price to Rs. 414. The price of Auto Diesel has been reduced by Rs. 25, bringing "
        "the new price to Rs. 382. Petrol 95 Octane Unchanged Rs. 495. Super Diesel Unchanged "
        "Rs. 478. Kerosene Unchanged Rs. 285."
    )
    points = _extract_prices(text, fallback_date=date(2026, 6, 29), outlet="onlanka")
    by_fuel = {p.fuel_type: p.price_lkr for p in points}
    assert by_fuel[fuel_mod.PETROL_92] == 414.0
    assert by_fuel[fuel_mod.AUTO_DIESEL] == 382.0
    assert by_fuel[fuel_mod.PETROL_95] == 495.0


def test_extract_price_fixed_at_rs():
    assert _extract_price("revised selling price now fixed at Rs. 382") == 382.0
    assert _extract_price("new price set at Rs. 414") == 414.0


def test_resolve_via_publisher_search_onlanka():
    from app.scrapers.news import _resolve_via_publisher_search

    url = _resolve_via_publisher_search(
        "Sri Lanka revises fuel prices from June 30, 2026 - ONLANKA",
        "https://www.onlanka.com",
    )
    assert url is not None
    assert "onlanka.com" in url
    assert "fuel-prices" in url.lower() or "june-30" in url.lower()


def test_resolve_via_publisher_search_lankanewsweb():
    from app.scrapers.news import _resolve_via_publisher_search

    url = _resolve_via_publisher_search(
        "Fuel Prices Reduced as CEYPETCO Announces Latest Revision - LNW",
        "https://lankanewsweb.net",
    )
    assert url is not None
    assert "lankanewsweb.net" in url
    assert "fuel-prices" in url.lower() or "226278" in url


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
    """Island on-site search is flaky (500s) — unit-test ranking, not live HTML."""
    from app.scrapers import news as news_mod

    html = """
    <html><body>
      <a href="http://island.lk/archives/">Archives</a>
      <a href="http://island.lk/fuel-prices-increased/">Fuel prices increased</a>
      <a href="http://island.lk/unrelated-cricket-match/">Cricket</a>
    </body></html>
    """

    class _Resp:
        text = html
        def raise_for_status(self):
            return None

    with patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = _Resp()
        url = news_mod._resolve_via_publisher_search(
            "Fuel prices increased - The island.lk",
            "http://island.lk",
        )
    assert url is not None
    assert "island.lk" in url
    assert "fuel" in url.lower()


def test_resolve_via_web_search_picks_best_slug_match():
    """Unit-test web-search ranking without depending on live search availability."""
    from app.scrapers import news as news_mod

    fake = [
        "https://www.adaderana.lk/news/1/unrelated-sports",
        "https://www.adaderana.lk/news/120058/fuel-prices-increased",
        "https://example.com/other",
    ]
    with patch.object(news_mod, "_web_search_urls", return_value=fake):
        url = news_mod._resolve_via_publisher_search(
            "Fuel prices increased - Ada Derana",
            "https://adaderana.lk",
        )
    assert url == "https://www.adaderana.lk/news/120058/fuel-prices-increased"


def test_resolve_via_web_search_adaderana_cuid_via_page_title():
    """Ada cuid URLs have no slug — match by fetching page <title>."""
    from app.scrapers import news as news_mod

    fake = ["https://adaderana.lk/news/cmqzfsf47000a356pblxalol4"]
    with patch.object(news_mod, "_web_search_urls", return_value=fake):
        with patch.object(news_mod, "_page_title_matches", return_value=True):
            url = news_mod._resolve_via_publisher_search(
                "Auto Diesel, Petrol 92 Octane prices reduced - Ada Derana",
                "https://adaderana.lk",
            )
    assert url == "https://adaderana.lk/news/cmqzfsf47000a356pblxalol4"


def test_resolve_via_web_search_dailymirror_pattern():
    from app.scrapers import news as news_mod

    fake = [
        "https://www.dailymirror.lk/breaking-news/Fuel-prices-increased/108-334878",
    ]
    with patch.object(news_mod, "_web_search_urls", return_value=fake):
        # Force the on-site search path to fail so web-search fallback runs.
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
