#!/usr/bin/env python3
"""Fetch Sri Lanka fuel news headlines and run Groq AI sentiment analysis.

Called by .github/workflows/sentiment.yml:
  - daily schedule (02:00 UTC)
  - manual workflow_dispatch
  - scrape / scrape-news when CPC, news, or LIOC latest prices change

Outputs backend/data/ai_sentiment.json which is committed back to master.

Note: the Fly API serves whatever copy was baked into the last successful
image deploy. When Fly deploys are blocked, /v1/prices/sentiment can lag for
months even though this file updates daily — the frontend also reads this
JSON from GitHub raw as a freshness fallback.

Env:
    GROQ_API_KEY                     — required
    SENTIMENT_REASON                 — scheduled | manual | price_change
    SENTIMENT_SKIP_IF_FRESH_MINUTES  — if >0, exit early when existing
                                       ai_sentiment.json is newer than this
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import httpx

try:
    from groq import Groq
except ImportError:
    print("groq not installed. Run: pip install httpx groq", file=sys.stderr)
    sys.exit(1)

OCTANE_API = "https://octane-api.fly.dev"

# Google News RSS queries targeted at Sri Lanka fuel policy signals
NEWS_FEEDS = [
    "https://news.google.com/rss/search?q=sri+lanka+fuel+price+petrol+diesel&hl=en-LK&gl=LK&ceid=LK:en",
    "https://news.google.com/rss/search?q=CPC+LIOC+fuel+price+revision+lanka&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=sri+lanka+petroleum+IMF+subsidy+energy&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=brent+crude+oil+price+week&hl=en&gl=US&ceid=US:en",
]


def fetch_headlines() -> list[str]:
    headlines: list[str] = []
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for url in NEWS_FEEDS:
            try:
                r = client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; OctaneSentimentBot/1.0)"})
                r.raise_for_status()
                root = ElementTree.fromstring(r.content)
                for item in root.findall(".//item"):
                    title = item.findtext("title", "").strip()
                    if len(title) > 15:
                        # Strip trailing " - Source Name" from Google News titles
                        clean = re.sub(r"\s+-\s+[^-]{3,40}$", "", title).strip()
                        headlines.append(clean)
            except Exception as e:
                print(f"  Warning: {url}: {e}", file=sys.stderr)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for h in headlines:
        key = h.lower()
        if key not in seen:
            seen.add(key)
            unique.append(h)

    return unique[:30]


def fetch_current_prices() -> dict[str, float]:
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(f"{OCTANE_API}/v1/prices/latest")
            r.raise_for_status()
            return {p["fuel_type"]: float(p["price_lkr"]) for p in r.json().get("prices", [])}
    except Exception as e:
        print(f"  Warning: could not fetch current prices: {e}", file=sys.stderr)
        return {}


def analyze(headlines: list[str], current_prices: dict[str, float]) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    price_block = "\n".join(
        f"  - {k.replace('_', ' ').title()}: LKR {v:.2f}/L"
        for k, v in current_prices.items()
    ) or "  (unavailable)"

    headline_block = (
        "\n".join(f"  - {h}" for h in headlines)
        if headlines
        else "  (no headlines found)"
    )

    prompt = f"""You are an energy economics analyst specialising in Sri Lanka's administered fuel market.

Context:
- Sri Lanka's fuel prices are set by the government (CPC/LIOC), not by market forces
- Key drivers: Brent/Dubai crude prices, USD/LKR exchange rate, IMF programme conditions, government revenue needs
- Revisions happen roughly monthly; typical size is 5–50 LKR per litre
- A "stable" prediction means no revision is likely in the next 30 days

Current retail prices (LKR per litre):
{price_block}

Recent news headlines (past 48 hours):
{headline_block}

Task: Analyse the headlines and return a JSON object with exactly these fields:
- "direction"      : "up", "down", or "stable"
- "confidence"     : float 0.0–1.0 (how strongly the headlines support your prediction)
- "magnitude_lkr"  : float, estimated size of next revision in LKR/L (positive = increase, negative = decrease, 0 = no revision expected). Use 0 if direction is "stable".
- "summary"        : string, one sentence ≤ 20 words explaining the key signal
- "signals"        : list of up to 3 short strings, each naming a specific headline or macro factor driving this

Respond with ONLY valid JSON. No markdown, no explanation outside the JSON."""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.15,
        max_tokens=400,
    )

    raw = response.choices[0].message.content
    return json.loads(raw)


def main() -> None:
    print("=== Octane AI Sentiment Analysis ===")

    reason = os.environ.get("SENTIMENT_REASON", "scheduled")
    skip_mins = int(os.environ.get("SENTIMENT_SKIP_IF_FRESH_MINUTES") or "0")
    out_path = "backend/data/ai_sentiment.json"
    print(f"  reason={reason}  skip_if_fresh_minutes={skip_mins}")

    if skip_mins > 0 and os.path.exists(out_path):
        try:
            existing = json.loads(Path(out_path).read_text(encoding="utf-8"))
            raw = str(existing.get("generated_at") or "").replace("Z", "+00:00")
            generated = datetime.fromisoformat(raw)
            if generated.tzinfo is None:
                generated = generated.replace(tzinfo=timezone.utc)
            age_min = (datetime.now(timezone.utc) - generated).total_seconds() / 60
            if age_min < skip_mins:
                print(
                    f"  Skipping — existing sentiment is {age_min:.0f} min old "
                    f"(<{skip_mins} min). Use scheduled/manual run to force."
                )
                return
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"  Warning: could not read existing sentiment for skip check: {exc}")

    print("Fetching headlines...")
    headlines = fetch_headlines()
    print(f"  {len(headlines)} unique headlines collected")
    for h in headlines[:5]:
        print(f"  · {h}")

    print("Fetching current prices...")
    current_prices = fetch_current_prices()
    print(f"  Prices: {current_prices}")

    print("Running Groq analysis...")
    result = analyze(headlines, current_prices)
    print(f"  Result: {result}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "headlines_analyzed": len(headlines),
        "headlines_sample": headlines[:5],
        "trigger": reason,
        **result,
    }

    os.makedirs("backend/data", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Written: {out_path}")
    print(f"  direction={result.get('direction')}  confidence={result.get('confidence')}  magnitude={result.get('magnitude_lkr')} LKR")


if __name__ == "__main__":
    main()
