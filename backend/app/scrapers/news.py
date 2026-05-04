"""News outlet scraper — catches price announcements before CPC site updates.

Polls RSS feeds from major Sri Lankan news sites, filters for fuel-price
articles published in the last 48 hours, then extracts price data from
the article body. Results are tagged source="news" and complement CPC/LIOC
entries without conflicting (unique constraint is on recorded_at+fuel_type+source).
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

from bs4 import BeautifulSoup

from app.scrapers.cpc import PricePoint
from app.scrapers.http import client

log = logging.getLogger(__name__)

SOURCE = "news"

# Sri Lankan news outlets with reliable RSS feeds
FEEDS = [
    "https://www.adaderana.lk/rss.php",
    "https://economynext.com/feed/",
    "https://www.dailymirror.lk/rss/",
    "http://www.colombopage.com/rss.xml",
]

FUEL_KEYWORDS = re.compile(
    r"fuel\s+price|petrol\s+price|diesel\s+price|fuel\s+revision|"
    r"fuel\s+hike|fuel\s+cut|fuel\s+reduc|price\s+revision|"
    r"petroleum\s+price|fuel\s+increas|litre\s+price|fuel\s+rates?",
    re.IGNORECASE,
)

# "to Rs. 340" captures the new price (not the old "from Rs. X")
TO_RS_RE = re.compile(r"to\s+Rs\.?\s*(\d{2,4}(?:\.\d{1,2})?)", re.IGNORECASE)
RS_RE = re.compile(r"Rs\.?\s*(\d{2,4}(?:\.\d{1,2})?)", re.IGNORECASE)
PER_LITRE_RE = re.compile(r"(\d{2,4}(?:\.\d{1,2})?)\s*(?:per\s*li(?:tre|ter)|/litre|/liter)", re.IGNORECASE)

FUEL_NAME_RE: dict[str, re.Pattern[str]] = {
    "petrol_92": re.compile(r"\b(?:92|petrol\s*92|LP\s*92|octane\s*92)\b", re.IGNORECASE),
    "petrol_95": re.compile(r"\b(?:95|petrol\s*95|LP\s*95|super\s*petrol)\b", re.IGNORECASE),
    "auto_diesel": re.compile(r"\bauto\s*diesel\b", re.IGNORECASE),
    "super_diesel": re.compile(r"\bsuper\s*diesel\b", re.IGNORECASE),
    "kerosene": re.compile(r"\bkerosene\b", re.IGNORECASE),
}

DATE_FORMATS = ("%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")
EFFECTIVE_DATE_RE = re.compile(
    r"(?:effective|with\s+effect|w\.e\.f\.?|from)\s+(?:from\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})",
    re.IGNORECASE,
)


def _parse_rss_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _parse_effective_date(text: str) -> date | None:
    for m in EFFECTIVE_DATE_RE.finditer(text):
        raw = re.sub(r"\b(st|nd|rd|th)\b", "", m.group(1)).strip()
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return None


def _extract_price(segment: str) -> float | None:
    """Extract price from a text segment, preferring 'to Rs. X' over bare 'Rs. X'."""
    for pattern in (TO_RS_RE, PER_LITRE_RE, RS_RE):
        m = pattern.search(segment)
        if m:
            try:
                price = float(m.group(1))
                if 50 <= price <= 2000:
                    return price
            except (ValueError, IndexError):
                continue
    return None


def _extract_prices(text: str, fallback_date: date) -> list[PricePoint]:
    effective_date = _parse_effective_date(text) or fallback_date

    # Split on sentence/line boundaries for contextual matching
    segments = re.split(r"[.\n;|]", text)

    points: list[PricePoint] = []
    for fuel_type, fuel_re in FUEL_NAME_RE.items():
        for i, seg in enumerate(segments):
            if not fuel_re.search(seg):
                continue
            # Also look one segment ahead (price sometimes on next line/cell)
            combined = seg + " " + (segments[i + 1] if i + 1 < len(segments) else "")
            price = _extract_price(combined)
            if price is not None:
                points.append(PricePoint(effective_date, fuel_type, price, SOURCE))
                break  # first match per fuel type

    # De-dup by fuel type
    seen: set[str] = set()
    return [p for p in points if not (p.fuel_type in seen or seen.add(p.fuel_type))]  # type: ignore[func-returns-value]


def _poll_feed(feed_url: str, max_age_hours: int = 48) -> list[tuple[str, datetime | None]]:
    """Return (url, pub_date) for recent fuel-related articles in one RSS feed."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    results: list[tuple[str, datetime | None]] = []
    try:
        with client(timeout=15.0) as c:
            r = c.get(feed_url)
            r.raise_for_status()
    except Exception as exc:
        log.warning("rss fetch failed %s: %s", feed_url, exc)
        return results

    soup = BeautifulSoup(r.text, "xml")
    for item in soup.find_all("item"):
        title_tag = item.find("title")
        desc_tag = item.find("description")
        link_tag = item.find("link")
        pub_tag = item.find("pubDate") or item.find("published")

        combined = " ".join(
            t.get_text(strip=True) for t in (title_tag, desc_tag) if t
        )
        if not FUEL_KEYWORDS.search(combined):
            continue

        pub_date = _parse_rss_date(pub_tag.get_text(strip=True) if pub_tag else None)
        if pub_date and pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        if pub_date and pub_date < cutoff:
            continue

        url = link_tag.get_text(strip=True) if link_tag else None
        if not url:
            guid = item.find("guid")
            url = guid.get_text(strip=True) if guid else None
        if url and url.startswith("http"):
            results.append((url, pub_date))

    return results


def _scrape_article(url: str, pub_date: datetime | None) -> list[PricePoint]:
    fallback_date = pub_date.date() if pub_date else date.today()
    try:
        with client(timeout=20.0) as c:
            r = c.get(url)
            r.raise_for_status()
    except Exception as exc:
        log.warning("article fetch failed %s: %s", url, exc)
        return []

    soup = BeautifulSoup(r.text, "lxml")
    body = (
        soup.find("article")
        or soup.find(class_=re.compile(r"article|story|content|post-body", re.IGNORECASE))
        or soup.find("main")
        or soup.body
    )
    if not body:
        return []

    text = body.get_text(" ", strip=True)
    return _extract_prices(text, fallback_date)


def run() -> Iterable[PricePoint]:
    """Scrape all configured news feeds and return deduplicated price points."""
    all_points: list[PricePoint] = []
    seen_urls: set[str] = set()

    for feed_url in FEEDS:
        articles = _poll_feed(feed_url)
        log.info("news feed %s → %d fuel articles", feed_url, len(articles))
        for url, pub_date in articles:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            points = _scrape_article(url, pub_date)
            if points:
                log.info("news article %s → %d prices", url, len(points))
            all_points.extend(points)

    # Final de-dup across outlets by (date, fuel_type) — CPC is authoritative;
    # news fills gaps for today if CPC hasn't updated yet.
    seen: set[tuple[date, str]] = set()
    unique: list[PricePoint] = []
    for p in all_points:
        key = (p.recorded_at, p.fuel_type)
        if key not in seen:
            seen.add(key)
            unique.append(p)

    log.info("news scraper total: %d price points", len(unique))
    return unique
