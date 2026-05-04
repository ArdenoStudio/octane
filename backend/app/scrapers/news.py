"""News outlet scraper — catches price announcements before CPC site updates.

Polls RSS feeds from major Sri Lankan news sites, filters for fuel-price
articles published in the last 48 hours, then extracts price data from
the article body. Results are tagged source="news" and complement CPC/LIOC
entries without conflicting (unique constraint is on recorded_at+fuel_type+source).
"""
from __future__ import annotations

import base64
import logging
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

from bs4 import BeautifulSoup

import httpx

from app.scrapers.cpc import PricePoint

log = logging.getLogger(__name__)

SOURCE = "news"

# Browser UA so news sites don't 403 the OctaneBot agent
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Google News RSS aggregates SL outlets (Ada Derana, Daily Mirror, etc.)
# without triggering their Cloudflare WAF. Two queries: one for revisions,
# one for ceypetco announcements specifically.
FEEDS = [
    "https://news.google.com/rss/search?q=Sri+Lanka+fuel+price+revised&hl=en-LK&gl=LK&ceid=LK:en",
    "https://news.google.com/rss/search?q=ceypetco+fuel+price&hl=en-LK&gl=LK&ceid=LK:en",
    "https://economynext.com/feed/",
    "http://www.colombopage.com/rss.xml",
]

# Require revision/change language to skip explainer/analysis pieces.
# Google News titles are short so also accept "fuel prices" alone as a match
# when coming from a ceypetco-specific query.
FUEL_KEYWORDS = re.compile(
    r"fuel\s+prices?\s+(?:revised?|increased?|reduced?|changed?|cut|hike|effective|up|down|adjust)|"
    r"(?:revised?|new|updated?)\s+fuel\s+prices?|"
    r"petrol\s+(?:price|rate)s?\s+(?:revised?|increased?|reduced?|up|down|hike|cut)|"
    r"diesel\s+(?:price|rate)s?\s+(?:revised?|increased?|reduced?|up|down|hike|cut)|"
    r"fuel\s+(?:price\s+)?revision|fuel\s+price\s+change|"
    r"ceypetco\s+(?:price|fuel)|fuel\s+price\s+effective|"
    r"fuel\s+prices?\s+in\s+sri\s+lanka",
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


def _poll_feed(feed_url: str, max_age_hours: int = 72) -> list[tuple[str, datetime | None, str]]:
    """Return (url, pub_date, summary_text) for recent fuel-related articles."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    results: list[tuple[str, datetime | None, str]] = []
    try:
        with httpx.Client(headers={"User-Agent": _BROWSER_UA}, timeout=15.0, follow_redirects=True) as c:
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

        title_text = title_tag.get_text(strip=True) if title_tag else ""
        desc_text = desc_tag.get_text(strip=True) if desc_tag else ""
        # Google News descriptions are HTML-escaped — strip tags for text
        desc_clean = BeautifulSoup(desc_text, "lxml").get_text(" ", strip=True)
        summary = f"{title_text} {desc_clean}".strip()

        if not FUEL_KEYWORDS.search(summary):
            continue

        pub_date = _parse_rss_date(pub_tag.get_text(strip=True) if pub_tag else None)
        if pub_date and pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        if pub_date and pub_date < cutoff:
            continue

        # 1) Try <link> text (works for non-Google RSS feeds)
        url = link_tag.get_text(strip=True) if link_tag else None
        # 2) Try <guid> (often the Google CBMi URL)
        if not url or "google.com" in url:
            guid = item.find("guid")
            guid_url = guid.get_text(strip=True) if guid else None
            if guid_url and "google.com" not in guid_url:
                url = guid_url
        # 3) Try <source url="..."> attribute (direct source domain isn't enough but log it)
        # 4) Scan the raw item for any non-Google http URL (e.g. in href attributes)
        if not url or "google.com" in url:
            raw_item = str(item)
            candidates = re.findall(r'https?://[^\s<>"\']+', raw_item)
            real = next((u for u in candidates if "google.com" not in u), None)
            if real:
                url = real.rstrip("/.,;)")
        if url and url.startswith("http"):
            results.append((url, pub_date, summary))

    return results


def _decode_google_news_url(url: str) -> str | None:
    """Decode a Google News CBMi token to recover the original article URL.

    The token is a two-level encoding:
      outer = base64url(protobuf{ field1: int, field4: inner_token_bytes })
      inner = base64url(structure containing the article URL)
    """
    m = re.search(r"/articles/([A-Za-z0-9_-]+)", url)
    if not m:
        return None
    token = m.group(1)
    pad = (4 - len(token) % 4) % 4
    try:
        outer = base64.urlsafe_b64decode(token + "=" * pad)
    except Exception:
        return None

    # Protobuf header is typically 4 bytes:
    # [field1 varint tag][varint value][field4 len-delim tag][field4 length]
    # followed by the ASCII inner token.
    if len(outer) < 5 or outer[2] != 0x22:
        return None
    inner_len = outer[3]
    if len(outer) < 4 + inner_len:
        return None
    inner_token = outer[4 : 4 + inner_len].decode("ascii", errors="ignore")

    pad2 = (4 - len(inner_token) % 4) % 4
    try:
        inner = base64.urlsafe_b64decode(inner_token + "=" * pad2)
    except Exception:
        return None

    hit = re.search(rb"https?://[^\x00\x01-\x1f\x7f ]+", inner)
    if not hit:
        return None
    candidate = hit.group(0).decode("utf-8", errors="ignore").rstrip("/.,;)")
    return candidate if "google.com" not in candidate else None


def _scrape_article(url: str, pub_date: datetime | None) -> list[PricePoint]:
    fallback_date = pub_date.date() if pub_date else date.today()
    try:
        with httpx.Client(headers={"User-Agent": _BROWSER_UA}, timeout=20.0, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
    except Exception as exc:
        log.warning("article fetch failed %s: %s", url, exc)
        return []

    # If we're still on Google's servers, decode the actual article URL
    if "news.google.com" in str(r.url):
        actual_url = _decode_google_news_url(url)
        if not actual_url:
            log.warning("could not decode google news url: %s", url)
            return []
        log.info("google news url decoded to %s", actual_url)
        try:
            with httpx.Client(headers={"User-Agent": _BROWSER_UA}, timeout=20.0, follow_redirects=True) as c:
                r = c.get(actual_url)
                r.raise_for_status()
        except Exception as exc:
            log.warning("article fetch failed %s: %s", actual_url, exc)
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
        for url, pub_date, summary in articles:
            if url in seen_urls:
                continue
            seen_urls.add(url)

            fallback_date = pub_date.date() if pub_date else date.today()

            # Try extracting prices from the RSS summary first (cheaper, no fetch needed)
            points = _extract_prices(summary, fallback_date)
            if points:
                log.info("news summary hit %s → %d prices", url, len(points))
            else:
                # Fall back to fetching the full article
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
