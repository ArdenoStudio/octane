"""AI sentiment snapshot loader.

Reads the latest Groq-generated sentiment analysis from backend/data/ai_sentiment.json,
which is committed daily by the sentiment GitHub Actions workflow.

If the on-disk copy is stale (common when Fly image deploys fail), fall back to
the same JSON on GitHub raw so /v1/prices/sentiment stays current.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_DATA_FILE = Path(__file__).parent.parent.parent / "data" / "ai_sentiment.json"
_RAW_URL = (
    "https://raw.githubusercontent.com/ArdenoStudio/octane/master/"
    "backend/data/ai_sentiment.json"
)
_CACHE_TTL = 3600  # re-read at most once per hour
_STALE_HOURS = 36

_cache_time: float = 0.0
_cache_value: Optional["SentimentData"] = None


@dataclass
class SentimentData:
    direction: str          # "up" | "down" | "stable"
    confidence: float       # 0.0 – 1.0
    magnitude_lkr: float    # estimated revision size in LKR (positive = up)
    summary: str
    generated_at: str
    headlines_analyzed: int
    signals: list[str] = field(default_factory=list)


def _parse(data: dict) -> Optional[SentimentData]:
    # Only return real data — skip the zero-confidence placeholder
    if float(data.get("confidence", 0.0) or 0.0) <= 0.0:
        return None
    return SentimentData(
        direction=data.get("direction", "stable"),
        confidence=float(data.get("confidence", 0.5)),
        magnitude_lkr=float(data.get("magnitude_lkr", 0.0)),
        summary=data.get("summary", ""),
        generated_at=data.get("generated_at", ""),
        headlines_analyzed=int(data.get("headlines_analyzed", 0)),
        signals=list(data.get("signals", [])),
    )


def _is_stale(sent: SentimentData | None) -> bool:
    if not sent or not sent.generated_at:
        return True
    try:
        raw = sent.generated_at.replace("Z", "+00:00")
        generated = datetime.fromisoformat(raw)
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - generated).total_seconds() / 3600
        return age_h > _STALE_HOURS
    except ValueError:
        return True


def _load_file() -> Optional[SentimentData]:
    if not _DATA_FILE.exists():
        return None
    try:
        data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        return _parse(data)
    except Exception:
        return None


def _load_remote() -> Optional[SentimentData]:
    try:
        with urllib.request.urlopen(_RAW_URL, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return _parse(data)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        log.info("remote sentiment fetch failed: %s", exc)
        return None


def load() -> Optional[SentimentData]:
    """Return the latest AI sentiment snapshot, or None if unavailable."""
    global _cache_time, _cache_value
    now = time.monotonic()
    # Treat never-populated cache as a miss even when _cache_time was reset to 0.
    if _cache_value is not None and now - _cache_time < _CACHE_TTL:
        return _cache_value

    local = _load_file()
    result = local
    if _is_stale(local):
        remote = _load_remote()
        if remote is not None:
            if local is None or _is_stale(local):
                # Prefer whichever generated_at is newer.
                if local is None:
                    result = remote
                else:
                    try:
                        local_t = datetime.fromisoformat(
                            local.generated_at.replace("Z", "+00:00")
                        )
                        remote_t = datetime.fromisoformat(
                            remote.generated_at.replace("Z", "+00:00")
                        )
                        result = remote if remote_t >= local_t else local
                    except ValueError:
                        result = remote

    _cache_time = now
    _cache_value = result
    return result
