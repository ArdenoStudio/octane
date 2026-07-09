"""Unit tests for early price signal selection (no DB)."""
from __future__ import annotations

from datetime import date, timedelta

from app.services import signals


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


def test_lioc_divergence():
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
    out = signals.early_signals(rows)
    assert len(out) == 1
    assert out[0]["source"] == "lanka_ioc"
    assert out[0]["status"] == "divergence"
    assert out[0]["delta_lkr"] == 4.0
