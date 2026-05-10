"""AI sentiment snapshot loader.

Reads the latest Groq-generated sentiment analysis from backend/data/ai_sentiment.json,
which is committed daily by the sentiment GitHub Actions workflow.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_DATA_FILE = Path(__file__).parent.parent.parent / "data" / "ai_sentiment.json"
_CACHE_TTL = 3600  # re-read file at most once per hour

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


def load() -> Optional[SentimentData]:
    """Return the latest AI sentiment snapshot, or None if unavailable."""
    global _cache_time, _cache_value
    now = time.monotonic()
    if now - _cache_time < _CACHE_TTL:
        return _cache_value

    result: Optional[SentimentData] = None
    if _DATA_FILE.exists():
        try:
            data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
            # Only return real data — skip the zero-confidence placeholder
            if data.get("confidence", 0.0) > 0.0:
                result = SentimentData(
                    direction=data.get("direction", "stable"),
                    confidence=float(data.get("confidence", 0.5)),
                    magnitude_lkr=float(data.get("magnitude_lkr", 0.0)),
                    summary=data.get("summary", ""),
                    generated_at=data.get("generated_at", ""),
                    headlines_analyzed=int(data.get("headlines_analyzed", 0)),
                    signals=data.get("signals", []),
                )
        except Exception:
            pass

    _cache_time = now
    _cache_value = result
    return result
