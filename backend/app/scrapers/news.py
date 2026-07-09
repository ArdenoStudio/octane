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
# without triggering their Cloudflare WAF. Prefer en-US locale — en-LK
# redirects and sometimes returns thinner results from Actions runners.
FEEDS = [
    "https://news.google.com/rss/search?q=%22fuel+prices%22+OR+%22fuel+price%22+%22Sri+Lanka%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=ceypetco+OR+%22petrol+92%22+%22Sri+Lanka%22+price&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22fuel+prices%22+(revised+OR+reduced+OR+increased+OR+hike+OR+cut)+%22Sri+Lanka%22&hl=en-US&gl=US&ceid=US:en",
    "https://economynext.com/feed/",
    "https://www.newswire.lk/feed/",
    "https://adaderana.lk/rss.xml",
]

# Revision / change language. Titles are often short ("Fuel prices reduced in
# Sri Lanka") so keep patterns broad, but still require a price-move verb or
# Ceypetco/petrol-92 cue to skip pure analysis pieces.
FUEL_KEYWORDS = re.compile(
    r"fuel\s+prices?\s+(?:revised?|increased?|reduced?|changed?|cut|hike|effective|up|down|adjust|drop(?:ped)?|slash(?:ed)?)|"
    r"(?:revised?|new|updated?|latest)\s+fuel\s+prices?|"
    r"(?:petrol|diesel|kerosene).{0,40}(?:price|rate)s?.{0,20}(?:revised?|increased?|reduced?|up|down|hike|cut|drop)|"
    r"(?:petrol|diesel|kerosene).{0,40}(?:revised?|increased?|reduced?|hike|cut|drop)|"
    r"(?:price|rate)s?\s+(?:of\s+)?(?:petrol|diesel|kerosene).{0,20}(?:revised?|increased?|reduced?|hike|cut)|"
    r"fuel\s+(?:price\s+)?revision|fuel\s+price\s+change|fuel\s+price\s+hike|"
    r"ceypetco\s+(?:price|fuel|revis)|fuel\s+price\s+effective|"
    r"fuel\s+prices?\s+(?:in\s+)?sri\s+lanka|"
    r"(?:breaking|update).{0,20}fuel\s+prices?",
    re.IGNORECASE,
)

# "to Rs. 340" captures the new price (not the old "from Rs. X")
TO_RS_RE = re.compile(r"to\s+Rs\.?\s*(\d{2,4}(?:\.\d{1,2})?)", re.IGNORECASE)
RS_RE = re.compile(r"Rs\.?\s*(\d{2,4}(?:\.\d{1,2})?)", re.IGNORECASE)
PER_LITRE_RE = re.compile(r"(\d{2,4}(?:\.\d{1,2})?)\s*(?:per\s*li(?:tre|ter)|/litre|/liter)", re.IGNORECASE)

FUEL_NAME_RE: dict[str, re.Pattern[str]] = {
    "petrol_92": re.compile(
        r"\b(?:petrol\s*(?:octane\s*)?92|LP\s*92|octane\s*92|92\s*octane)\b",
        re.IGNORECASE,
    ),
    "petrol_95": re.compile(
        r"\b(?:petrol\s*(?:octane\s*)?95|LP\s*95|octane\s*95|95\s*octane|super\s*petrol)\b",
        re.IGNORECASE,
    ),
    "auto_diesel": re.compile(r"\b(?:auto\s*diesel|lanka\s*auto\s*diesel)\b", re.IGNORECASE),
    "super_diesel": re.compile(r"\b(?:super\s*diesel|lanka\s*super\s*diesel)\b", re.IGNORECASE),
    "kerosene": re.compile(r"\b(?:kerosene|lanka\s*kerosene)\b", re.IGNORECASE),
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


def _split_segments(text: str) -> list[str]:
    """Split article text without breaking 'Rs. 414' or decimal prices."""
    # Protect currency abbreviations and decimals, then split on sentence ends.
    protected = re.sub(r"\bRs\.", "Rs‹DOT›", text, flags=re.IGNORECASE)
    protected = re.sub(r"(\d)\.(\d)", r"\1‹DOT›\2", protected)
    parts = re.split(r"[.\n;|]+", protected)
    return [p.replace("‹DOT›", ".").strip() for p in parts if p.strip()]


def _price_near_fuel(segment: str, fuel_re: re.Pattern[str]) -> float | None:
    """Extract the price associated with a fuel mention inside one segment.

    Tries every fuel mention in the segment (not just the first), preferring
    a 'to Rs. X' / 'per litre' match in a short window after the name so
    multi-fuel sentences don't bleed prices across fuels.
    """
    for m in fuel_re.finditer(segment):
        after = segment[m.end() : m.end() + 120]
        price = _extract_price(after)
        if price is not None:
            return price
        before = segment[max(0, m.start() - 60) : m.start()]
        price = _extract_price(before)
        if price is not None:
            return price
    return None


def _extract_prices(text: str, fallback_date: date) -> list[PricePoint]:
    effective_date = _parse_effective_date(text) or fallback_date
    segments = _split_segments(text)

    points: list[PricePoint] = []
    for fuel_type, fuel_re in FUEL_NAME_RE.items():
        found: float | None = None
        for i, seg in enumerate(segments):
            if not fuel_re.search(seg):
                continue
            # Prefer price in the same segment; then same+next (not +2 — that
            # bleeds into the next fuel's sentence).
            for window in (seg, " ".join(segments[i : i + 2])):
                found = _price_near_fuel(window, fuel_re)
                if found is not None:
                    break
            if found is not None:
                points.append(PricePoint(effective_date, fuel_type, found, SOURCE))
                break

    # De-dup by fuel type
    seen: set[str] = set()
    return [p for p in points if not (p.fuel_type in seen or seen.add(p.fuel_type))]  # type: ignore[func-returns-value]


# Keep news hits aligned with the UI early-signal window (14 days).
DEFAULT_MAX_AGE_HOURS = 24 * 14


def _poll_feed(
    feed_url: str,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
) -> list[tuple[str, datetime | None, str, str | None]]:
    """Return (url, pub_date, summary_text, source_url) for recent fuel articles.

    Default window is 14 days — matches early-signal usefulness and tolerates
    Google News pubDates that are rounded or delayed.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    results: list[tuple[str, datetime | None, str, str | None]] = []
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
        source_tag = item.find("source")

        title_text = title_tag.get_text(strip=True) if title_tag else ""
        desc_text = desc_tag.get_text(strip=True) if desc_tag else ""
        # Google News descriptions are HTML-escaped — strip tags for text
        desc_clean = BeautifulSoup(desc_text, "lxml").get_text(" ", strip=True)
        summary = f"{title_text} {desc_clean}".strip()
        source_url = source_tag.get("url") if source_tag and source_tag.has_attr("url") else None

        if not FUEL_KEYWORDS.search(summary):
            continue

        pub_date = _parse_rss_date(pub_tag.get_text(strip=True) if pub_tag else None)
        if pub_date and pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        if pub_date and pub_date < cutoff:
            continue

        # Prefer a direct publisher http(s) URL. Keep the Google News article
        # URL as a fallback — _scrape_article() resolves the publisher page.
        # IMPORTANT: Google <guid> values are opaque CBMi tokens (not URLs).
        link_url = link_tag.get_text(strip=True) if link_tag else None
        guid = item.find("guid")
        guid_text = guid.get_text(strip=True) if guid else None
        guid_url = guid_text if guid_text and guid_text.startswith("http") else None

        publisher_url = _resolve_via_publisher_search(title_text, source_url)
        if not publisher_url:
            raw_item = str(item)
            candidates = re.findall(r'https?://[^\s<>"\']+', raw_item)
            for cand in candidates:
                cand = cand.rstrip("/.,;)")
                if "google.com" in cand or "gstatic.com" in cand:
                    continue
                # Skip bare homepages (no article path) — they have no prices.
                path = re.sub(r"^https?://[^/]+", "", cand).strip("/")
                if not path:
                    continue
                publisher_url = cand
                break

        url = publisher_url or guid_url or link_url
        if url and url.startswith("http"):
            results.append((url, pub_date, summary, source_url))

    return results


def _decode_google_news_url(url: str) -> str | None:
    """Best-effort decode of a Google News /articles/… token.

    Newer tokens (AU_yq…) no longer embed a plain URL. We still try the
    legacy two-level base64/protobuf shape, then fall back to scanning the
    decoded bytes for any http(s) URL.
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

    # Legacy shape: protobuf field4 length-delimited inner token.
    if len(outer) >= 5 and outer[2] == 0x22:
        inner_len = outer[3]
        if len(outer) >= 4 + inner_len:
            inner_token = outer[4 : 4 + inner_len].decode("ascii", errors="ignore")
            pad2 = (4 - len(inner_token) % 4) % 4
            try:
                inner = base64.urlsafe_b64decode(inner_token + "=" * pad2)
                hit = re.search(rb"https?://[^\x00\x01-\x1f\x7f ]+", inner)
                if hit:
                    candidate = hit.group(0).decode("utf-8", errors="ignore").rstrip("/.,;)")
                    if "google.com" not in candidate:
                        return candidate
            except Exception:
                pass

    # Fallback: any URL bytes hiding in the outer payload.
    hit = re.search(rb"https?://[^\x00\x01-\x1f\x7f ]+", outer)
    if hit:
        candidate = hit.group(0).decode("utf-8", errors="ignore").rstrip("/.,;)")
        if "google.com" not in candidate:
            return candidate
    return None


def _strip_outlet_suffix(title: str) -> str:
    """Remove trailing ' - Outlet Name' from Google News titles."""
    return re.sub(r"\s+[-–|]\s+[^-–|]{2,40}$", "", title).strip()


def _resolve_via_publisher_search(title: str, source_url: str | None) -> str | None:
    """Find the article URL by searching the publisher site.

    Google News article tokens no longer embed publisher URLs. For known SL
    outlets we can recover the real page via their on-site search.
    """
    if not source_url or not title:
        return None
    host = re.sub(r"^https?://(www\.)?", "", source_url).strip("/").lower()
    query = _strip_outlet_suffix(title)
    if not query:
        return None

    search_url: str | None = None
    link_re: re.Pattern[str] | None = None
    if "newswire.lk" in host:
        search_url = "https://www.newswire.lk/?s=" + query.replace(" ", "+")
        link_re = re.compile(
            r"https://www\.newswire\.lk/\d{4}/\d{2}/\d{2}/[a-z0-9\-]+/?",
            re.IGNORECASE,
        )
    elif "economynext.com" in host:
        search_url = "https://economynext.com/?s=" + query.replace(" ", "+")
        link_re = re.compile(r"https://economynext\.com/[a-z0-9\-]+-\d+/", re.IGNORECASE)
    elif "dailymirror.lk" in host:
        search_url = "https://www.dailymirror.lk/search/" + query.replace(" ", "-")
        link_re = re.compile(
            r"https://www\.dailymirror\.lk/[A-Za-z0-9\-]+/\d+",
            re.IGNORECASE,
        )
    else:
        return None

    try:
        with httpx.Client(headers={"User-Agent": _BROWSER_UA}, timeout=15.0, follow_redirects=True) as c:
            r = c.get(search_url)
            r.raise_for_status()
    except Exception as exc:
        log.warning("publisher search failed %s: %s", search_url, exc)
        return None

    links = link_re.findall(r.text)
    if not links:
        return None
    # Prefer the newest-looking / first unique hit.
    seen: set[str] = set()
    unique = [u for u in links if not (u.rstrip("/") in seen or seen.add(u.rstrip("/")))]
    return unique[0]


def _resolve_publisher_url(
    google_url: str,
    html: str,
    *,
    title: str | None = None,
    source_url: str | None = None,
) -> str | None:
    """Find the publisher URL for a Google News item."""
    via_search = _resolve_via_publisher_search(title or "", source_url)
    if via_search:
        return via_search

    decoded = _decode_google_news_url(google_url)
    if decoded:
        return decoded

    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            continue
        if "google.com" in href or "gstatic.com" in href:
            continue
        if any(k in href.lower() for k in ("fuel", "petrol", "diesel", "ceypetco", "news")):
            return href
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and "google.com" not in href and "gstatic.com" not in href:
            return href
    return None


def _scrape_article(
    url: str,
    pub_date: datetime | None,
    *,
    title: str | None = None,
    source_url: str | None = None,
) -> list[PricePoint]:
    fallback_date = pub_date.date() if pub_date else date.today()
    try:
        with httpx.Client(headers={"User-Agent": _BROWSER_UA}, timeout=20.0, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
    except Exception as exc:
        log.warning("article fetch failed %s: %s", url, exc)
        return []

    # If we're still on Google's servers, resolve the publisher URL.
    if "news.google.com" in str(r.url):
        actual_url = _resolve_publisher_url(
            url, r.text, title=title, source_url=source_url
        )
        if actual_url:
            log.info("google news url resolved to %s", actual_url)
            try:
                with httpx.Client(headers={"User-Agent": _BROWSER_UA}, timeout=20.0, follow_redirects=True) as c:
                    r2 = c.get(actual_url)
                    r2.raise_for_status()
                    r = r2
            except Exception as exc:
                log.warning("publisher article fetch failed %s: %s", actual_url, exc)
        else:
            log.info("could not resolve publisher URL — mining Google preview for %s", url)

    soup = BeautifulSoup(r.text, "lxml")

    # Prefer article body containers; fall back to full page text.
    body = (
        soup.find("article")
        or soup.find(class_=re.compile(r"article-body|post-content|entry-content|story-content|td-post-content", re.IGNORECASE))
        or soup.find(class_=re.compile(r"article|story|content|post-body", re.IGNORECASE))
        or soup.find("main")
        or soup.body
    )
    if not body:
        return []

    text = body.get_text(" ", strip=True)
    points = _extract_prices(text, fallback_date)
    if points:
        return points
    # Last resort: whole-page text (some WP themes bury the body).
    return _extract_prices(soup.get_text(" ", strip=True), fallback_date)


def run(max_age_hours: int = DEFAULT_MAX_AGE_HOURS) -> Iterable[PricePoint]:
    """Scrape all configured news feeds and return deduplicated price points."""
    all_points: list[PricePoint] = []
    seen_urls: set[str] = set()

    for feed_url in FEEDS:
        articles = _poll_feed(feed_url, max_age_hours=max_age_hours)
        log.info("news feed %s → %d fuel articles", feed_url, len(articles))
        for url, pub_date, summary, source_url in articles:
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
                points = _scrape_article(
                    url, pub_date, title=summary, source_url=source_url
                )
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
