"""Unit tests for early price signal selection and official resolver (no DB)."""
from __future__ import annotations

from datetime import date, timedelta

from app.services import prices, signals


def test_news_ahead_of_cpc_is_unconfirmed():
    today = date.today()
    rows = [
        {
            "fuel_type": "petrol_92",
            "source": "cpc",
            "price_lkr": 311.0,
            "recorded_at": (today - timedelta(days=90)).isoformat(),
            "scraped_at": None,
        },
        {
            "fuel_type": "petrol_92",
            "source": "news",
            "price_lkr": 295.0,
            "recorded_at": (today - timedelta(days=1)).isoformat(),
            "scraped_at": None,
        },
    ]
    out = signals.early_signals(rows)
    assert len(out) == 1
    assert out[0]["source"] == "news"
    assert out[0]["status"] == "unconfirmed"
    assert out[0]["delta_lkr"] == -16.0
    assert out[0]["official_source"] == "cpc"


def test_stale_news_ignored():
    today = date.today()
    rows = [
        {
            "fuel_type": "petrol_92",
            "source": "cpc",
            "price_lkr": 311.0,
            "recorded_at": (today - timedelta(days=200)).isoformat(),
            "scraped_at": None,
        },
        {
            "fuel_type": "petrol_92",
            "source": "news",
            "price_lkr": 300.0,
            "recorded_at": (today - timedelta(days=60)).isoformat(),
            "scraped_at": None,
        },
    ]
    assert signals.early_signals(rows) == []


def test_matching_news_same_day_ignored():
    today = date.today()
    rows = [
        {
            "fuel_type": "petrol_92",
            "source": "cpc",
            "price_lkr": 311.0,
            "recorded_at": today.isoformat(),
            "scraped_at": None,
        },
        {
            "fuel_type": "petrol_92",
            "source": "news",
            "price_lkr": 311.0,
            "recorded_at": today.isoformat(),
            "scraped_at": None,
        },
    ]
    assert signals.early_signals(rows) == []


def test_lioc_newer_becomes_official_not_early_signal():
    """Lanka IOC is official — a newer LIOC price wins, it is not 'unconfirmed'."""
    today = date.today()
    rows = [
        {
            "fuel_type": "auto_diesel",
            "source": "cpc",
            "price_lkr": 291.0,
            "recorded_at": (today - timedelta(days=90)).isoformat(),
            "scraped_at": None,
        },
        {
            "fuel_type": "auto_diesel",
            "source": "lanka_ioc",
            "price_lkr": 295.0,
            "recorded_at": today.isoformat(),
            "scraped_at": None,
        },
    ]
    assert signals.early_signals(rows) == []
    official = prices.official_latest(rows)
    assert len(official) == 1
    assert official[0]["source"] == "lanka_ioc"
    assert official[0]["price_lkr"] == 295.0


def test_news_compared_against_winning_lioc():
    today = date.today()
    rows = [
        {
            "fuel_type": "petrol_92",
            "source": "cpc",
            "price_lkr": 400.0,
            "recorded_at": (today - timedelta(days=30)).isoformat(),
            "scraped_at": None,
        },
        {
            "fuel_type": "petrol_92",
            "source": "lanka_ioc",
            "price_lkr": 414.0,
            "recorded_at": (today - timedelta(days=2)).isoformat(),
            "scraped_at": None,
        },
        {
            "fuel_type": "petrol_92",
            "source": "news",
            "price_lkr": 434.0,
            "recorded_at": today.isoformat(),
            "scraped_at": None,
        },
    ]
    out = signals.early_signals(rows)
    assert len(out) == 1
    assert out[0]["official_source"] == "lanka_ioc"
    assert out[0]["official_price_lkr"] == 414.0
    assert out[0]["delta_lkr"] == 20.0


def test_pick_official_prefers_newer_recorded_at():
    older = {
        "fuel_type": "petrol_92",
        "source": "cpc",
        "price_lkr": 400.0,
        "recorded_at": "2026-06-01",
        "scraped_at": "2026-07-12T10:00:00Z",
    }
    newer = {
        "fuel_type": "petrol_92",
        "source": "lanka_ioc",
        "price_lkr": 420.0,
        "recorded_at": "2026-07-11",
        "scraped_at": "2026-07-11T08:00:00Z",
    }
    assert prices.pick_official(older, newer)["source"] == "lanka_ioc"
    assert prices.pick_official(newer, older)["source"] == "lanka_ioc"


def test_pick_official_tie_prefers_cpc_when_scraped_equal():
    cpc = {
        "fuel_type": "petrol_92",
        "source": "cpc",
        "price_lkr": 400.0,
        "recorded_at": "2026-07-01",
        "scraped_at": None,
    }
    ioc = {
        "fuel_type": "petrol_92",
        "source": "lanka_ioc",
        "price_lkr": 405.0,
        "recorded_at": "2026-07-01",
        "scraped_at": None,
    }
    assert prices.pick_official(cpc, ioc)["source"] == "cpc"


def test_pick_official_tie_uses_scraped_at():
    cpc = {
        "fuel_type": "petrol_92",
        "source": "cpc",
        "price_lkr": 400.0,
        "recorded_at": "2026-07-01",
        "scraped_at": "2026-07-01T08:00:00Z",
    }
    ioc = {
        "fuel_type": "petrol_92",
        "source": "lanka_ioc",
        "price_lkr": 405.0,
        "recorded_at": "2026-07-01",
        "scraped_at": "2026-07-01T12:00:00Z",
    }
    assert prices.pick_official(cpc, ioc)["source"] == "lanka_ioc"
