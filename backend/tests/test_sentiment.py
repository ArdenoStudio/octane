"""Tests for AI sentiment loader freshness fallback."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import app.services.sentiment as sentiment


def test_parse_rejects_placeholder(tmp_path: Path, monkeypatch):
    sentiment._cache_time = 0
    sentiment._cache_value = None
    data_file = tmp_path / "ai_sentiment.json"
    data_file.write_text(json.dumps({"confidence": 0, "direction": "up"}), encoding="utf-8")
    monkeypatch.setattr(sentiment, "_DATA_FILE", data_file)
    monkeypatch.setattr(sentiment, "_load_remote", lambda: None)
    assert sentiment.load() is None


def test_load_uses_remote_when_local_is_stale(tmp_path: Path, monkeypatch):
    sentiment._cache_time = 0
    sentiment._cache_value = None
    data_file = tmp_path / "ai_sentiment.json"
    old = {
        "direction": "up",
        "confidence": 0.8,
        "magnitude_lkr": 25,
        "summary": "old",
        "generated_at": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
        "headlines_analyzed": 10,
        "signals": ["old"],
    }
    data_file.write_text(json.dumps(old), encoding="utf-8")
    monkeypatch.setattr(sentiment, "_DATA_FILE", data_file)

    fresh = sentiment.SentimentData(
        direction="down",
        confidence=0.8,
        magnitude_lkr=-30,
        summary="fresh",
        generated_at=datetime.now(timezone.utc).isoformat(),
        headlines_analyzed=30,
        signals=["new"],
    )
    monkeypatch.setattr(sentiment, "_load_remote", lambda: fresh)

    out = sentiment.load()
    assert out is not None
    assert out.direction == "down"
    assert out.magnitude_lkr == -30
