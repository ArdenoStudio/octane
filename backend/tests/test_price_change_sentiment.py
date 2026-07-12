"""Unit tests for scrape → AI outlook change detection."""
from __future__ import annotations

from pathlib import Path

from app.scrapers.run import prices_changed, write_github_output


def test_prices_changed_detects_cpc_move():
    before = {"cpc": {"petrol_92": 414.0}, "news": {}, "lanka_ioc": {}}
    after = {"cpc": {"petrol_92": 434.0}, "news": {}, "lanka_ioc": {}}
    assert prices_changed(before, after) is True


def test_prices_changed_detects_news_early_signal():
    before = {
        "cpc": {"petrol_92": 414.0},
        "news": {},
        "lanka_ioc": {},
    }
    after = {
        "cpc": {"petrol_92": 414.0},
        "news": {"petrol_92": 434.0},
        "lanka_ioc": {},
    }
    assert prices_changed(before, after) is True


def test_prices_changed_ignores_same_prices():
    snap = {
        "cpc": {"petrol_92": 414.0, "auto_diesel": 382.0},
        "news": {"petrol_92": 434.0},
        "lanka_ioc": {},
    }
    assert prices_changed(snap, snap) is False


def test_prices_changed_ignores_sub_cent_noise():
    before = {"cpc": {"petrol_92": 414.0}, "news": {}, "lanka_ioc": {}}
    after = {"cpc": {"petrol_92": 414.005}, "news": {}, "lanka_ioc": {}}
    assert prices_changed(before, after) is False


def test_write_github_output(tmp_path: Path, monkeypatch):
    out = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    write_github_output(price_changed=True)
    write_github_output(price_changed=False)
    text = out.read_text(encoding="utf-8")
    assert "price_changed=true\n" in text
    assert "price_changed=false\n" in text
