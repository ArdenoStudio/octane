"""News outlet scraper — catches price announcements before CPC site updates.

Polls RSS feeds from major Sri Lankan news sites (and Google News discovery),
filters for fuel-price articles, then extracts price data from the article
body. Results are tagged source="news" and keep per-outlet provenance so
run_news can select by multi-outlet consensus rather than blindly taking the
newest headline.
"""
from __future__ import annotations

import base64
import logging
import re
import time
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import quote, unquote

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
# Direct publisher feeds fill gaps when Google ranking is noisy.
FEEDS = [
    "https://news.google.com/rss/search?q=%22fuel+prices%22+OR+%22fuel+price%22+%22Sri+Lanka%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=ceypetco+OR+%22petrol+92%22+%22Sri+Lanka%22+price&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22fuel+prices%22+(revised+OR+reduced+OR+increased+OR+hike+OR+cut)+%22Sri+Lanka%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:adaderana.lk+(fuel+OR+petrol+OR+diesel)+(price+OR+prices)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:dailymirror.lk+(fuel+OR+petrol)+(price+OR+prices+OR+ceypetco+OR+CPC)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:island.lk+(fuel+OR+petrol)+(price+OR+prices+OR+ceypetco)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:onlanka.com+(fuel+OR+petrol)+(price+OR+prices+OR+ceypetco)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:lankanewsweb.net+(fuel+OR+petrol+OR+ceypetco)+(price+OR+prices)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:newsfirst.lk+(fuel+OR+petrol+OR+ceypetco)+(price+OR+prices+OR+reduced+OR+revised)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:english.newsfirst.lk+(fuel+OR+petrol+OR+CPC)+(price+OR+prices+OR+reduced+OR+revised)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:themorning.lk+(fuel+OR+petrol)+(price+OR+prices+OR+ceypetco+OR+revised)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:ft.lk+(fuel+OR+petrol)+(price+OR+prices+OR+ceypetco+OR+revised)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:sundaytimes.lk+(fuel+OR+petrol)+(price+OR+prices+OR+reduced+OR+revised)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:srilankamirror.com+(fuel+OR+petrol)+(price+OR+prices+OR+reduced+OR+revised)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site:economynext.com+(fuel+OR+petrol+OR+ceypetco)+(price+OR+prices)&hl=en-US&gl=US&ceid=US:en",
    "https://economynext.com/feed/",
    "https://www.newswire.lk/feed/",
    # Ada Derana /rss.xml returns 500 from many IPs — rely on Google News + Brave.
    "https://island.lk/feed/",
    "https://www.onlanka.com/feed",
    "https://lankanewsweb.net/feed",
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
    r"(?:breaking|update).{0,20}fuel\s+prices?|"
    r"cpc\s+announces\s+fuel|"
    r"price\s+of\s+auto\s+diesel\s+(?:reduced|increased|revised)|"
    r"revises?\s+fuel\s+prices?|"
    r"fuel\s+prices?\s+(?:slashed|cut)|"
    r"ceypetco\s+announces\s+(?:latest\s+)?revision",
    re.IGNORECASE,
)

# "to Rs. 340" / "fixed at Rs. 382" capture the new price (not "from Rs. X" / "by Rs. X")
TO_RS_RE = re.compile(
    r"(?:to|fixed\s+at|set\s+at|now\s+(?:at|priced\s+at))\s+Rs\.?\s*(\d{2,4}(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
RS_RE = re.compile(r"Rs\.?\s*(\d{2,4}(?:\.\d{1,2})?)", re.IGNORECASE)
# Delta / old-price prefixes — skip these bare Rs. matches.
RS_SKIP_PREFIX_RE = re.compile(r"\b(?:by|from|of)\s+$", re.IGNORECASE)
PER_LITRE_RE = re.compile(r"(\d{2,4}(?:\.\d{1,2})?)\s*(?:per\s*li(?:tre|ter)|/litre|/liter)", re.IGNORECASE)
# Speculative / opposition "could be reduced by Rs. X" — not an official revision.
SPECULATIVE_RE = re.compile(
    r"\b(?:could|would|should|may|might)\s+(?:have\s+been\s+)?(?:be\s+)?(?:reduced|increased|cut|hiked)\b",
    re.IGNORECASE,
)
ARTICLE_DATE_META = (
    "article:published_time",
    "og:article:published_time",
    "publishdate",
    "pubdate",
    "date",
    "dc.date",
    "dc.date.issued",
)
ARTICLE_DATE_VISIBLE = re.compile(
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}"
    r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)
# Ada Derana / Mirror bylines often look like "Sep 30, 2024 09:44 PM".
ARTICLE_BYLINE_DATE = re.compile(
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})"
    r"(?:\s+\d{1,2}:\d{2}\s*(?:AM|PM))?",
    re.IGNORECASE,
)

FUEL_NAME_RE: dict[str, re.Pattern[str]] = {
    "petrol_92": re.compile(
        r"\b(?:petrol\s*(?:octane\s*)?92|LP\s*92|octane\s*92(?:\s*petrol)?|92\s*octane)\b",
        re.IGNORECASE,
    ),
    "petrol_95": re.compile(
        r"\b(?:petrol\s*(?:octane\s*)?95|LP\s*95|octane\s*95(?:\s*petrol)?|95\s*octane|super\s*petrol)\b",
        re.IGNORECASE,
    ),
    "auto_diesel": re.compile(
        r"\b(?:auto\s*diesel|lanka\s*auto\s*diesel|white\s*diesel|LAD)\b",
        re.IGNORECASE,
    ),
    "super_diesel": re.compile(
        r"\b(?:super\s*diesel|lanka\s*super\s*diesel|LSD)\b",
        re.IGNORECASE,
    ),
    "kerosene": re.compile(r"\b(?:kerosene|lanka\s*kerosene)\b", re.IGNORECASE),
}

DATE_FORMATS = ("%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")
EFFECTIVE_DATE_RE = re.compile(
    r"(?:effective|with\s+effect|w\.e\.f\.?|from)\s+(?:from\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})",
    re.IGNORECASE,
)

# Canonical outlet ids used for trust-weighted consensus in run_news.
OUTLET_HOSTS: list[tuple[str, str]] = [
    ("newswire.lk", "newswire"),
    ("adaderana.lk", "adaderana"),
    ("dailymirror.lk", "dailymirror"),
    ("economynext.com", "economynext"),
    ("onlanka.com", "onlanka"),
    ("lankanewsweb.net", "lankanewsweb"),
    ("newsfirst.lk", "newsfirst"),
    ("themorning.lk", "themorning"),
    ("ft.lk", "dailyft"),
    ("sundaytimes.lk", "sundaytimes"),
    ("island.lk", "island"),
    ("srilankamirror.com", "srilankamirror"),
]


def outlet_from_host(url_or_host: str | None) -> str:
    """Map a publisher URL/host to a short outlet id."""
    if not url_or_host:
        return "unknown"
    host = re.sub(r"^https?://(www\.)?", "", url_or_host).strip("/").lower()
    host = host.split("/")[0]
    for needle, outlet in OUTLET_HOSTS:
        if needle in host:
            return outlet
    return "unknown"


def _date_hint_from_url(url: str | None) -> date | None:
    """Pull a publish date from URL paths when outlets embed one.

    NewsFirst / Newswire: /YYYY/MM/DD/slug
    Sunday Times: /YYMMDD/section/slug.html
    Prefer these over page chrome dates (FT/Ada often show "today").
    """
    if not url:
        return None
    m = re.search(r"/(20\d{2})/(\d{2})/(\d{2})/", url)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"sundaytimes\.lk/(\d{2})(\d{2})(\d{2})/", url, re.IGNORECASE)
    if m:
        yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(2000 + yy, mm, dd)
        except ValueError:
            return None
    return None


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
    for pattern in (TO_RS_RE, PER_LITRE_RE):
        m = pattern.search(segment)
        if m:
            try:
                price = float(m.group(1))
                if 50 <= price <= 2000:
                    return price
            except (ValueError, IndexError):
                continue
    # Bare Rs. — skip deltas ("by Rs. 20") and old prices ("from Rs. 311").
    for m in RS_RE.finditer(segment):
        prefix = segment[max(0, m.start() - 8) : m.start()]
        if RS_SKIP_PREFIX_RE.search(prefix):
            continue
        try:
            price = float(m.group(1))
            if 50 <= price <= 2000:
                return price
        except (ValueError, IndexError):
            continue
    return None


def _coerce_date(raw: str) -> date | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    cleaned = raw.replace(",", "")
    for fmt in (
        "%Y-%m-%d",
        "%b %d %Y",
        "%B %d %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(cleaned[:26], fmt).date()
        except ValueError:
            continue
    return None


def _parse_article_published_date(soup: BeautifulSoup, url: str) -> date | None:
    """Best-effort article publish date from meta tags, <time>, URL, or byline.

    Avoids site-chrome dates (e.g. Ada Derana header "Thu, 09 Jul 2026") by
    preferring meta/URL/byline-with-time over the first date in page text.
    """
    for prop in ARTICLE_DATE_META:
        tag = soup.find("meta", attrs={"property": prop}) or soup.find(
            "meta", attrs={"name": prop}
        )
        if tag and tag.get("content"):
            parsed = _coerce_date(tag["content"])
            if parsed:
                return parsed

    # JSON-LD NewsArticle — Daily Mirror embeds datePublished here (body may
    # contain control chars that break json.loads, so regex-extract).
    for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = script.string or script.get_text() or ""
        m = re.search(
            r'"datePublished"\s*:\s*"([^"]+)"',
            raw,
        )
        if m:
            parsed = _coerce_date(m.group(1))
            if parsed:
                return parsed

    for t in soup.find_all("time"):
        raw = t.get("datetime") or t.get_text(strip=True)
        parsed = _coerce_date(raw) if raw else None
        if parsed:
            return parsed

    # Path-embedded dates (NewsFirst / Newswire /YYYY/MM/DD/, Sunday Times /YYMMDD/)
    url_hint = _date_hint_from_url(url)
    if url_hint is not None:
        return url_hint

    # Newswire / WP style path: /2026/06/29/slug/ (also covered by url_hint)
    m = re.search(r"/((?:19|20)\d{2})/(\d{2})/(\d{2})/", url)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # Short byline spans (Ada: <span>Sep 30, 2024</span>) beat full-page text.
    # Daily Mirror: <a>30 June 2026 07:23 am</a>
    # Skip weekday-prefixed chrome like "Thu, 09 Jul 2026 - 08:42 PM".
    for span in soup.find_all(["span", "p", "div", "h2", "h3", "a"]):
        raw = span.get_text(" ", strip=True)
        if not raw or len(raw) > 40:
            continue
        if re.match(
            r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b",
            raw,
            re.IGNORECASE,
        ):
            continue
        # Ada-style: "Sep 30, 2024" (optionally with clock)
        m = ARTICLE_BYLINE_DATE.fullmatch(raw)
        if m:
            parsed = _coerce_date(m.group(1))
            if parsed:
                return parsed
        # Mirror-style: "30 June 2026 07:23 am" — require the clock so bare
        # "09 Jul 2026" site chrome does not win.
        m = re.fullmatch(
            r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})"
            r"\s+\d{1,2}:\d{2}\s*(?:am|pm)",
            raw,
            re.IGNORECASE,
        )
        if m:
            parsed = _coerce_date(m.group(1))
            if parsed:
                return parsed

    # Bylines with an AM/PM clock in page text (Ada Month-first form).
    text = soup.get_text(" ", strip=True)
    for m in ARTICLE_BYLINE_DATE.finditer(text[:4000]):
        if re.search(r"\d{1,2}:\d{2}\s*(?:AM|PM)", m.group(0), re.IGNORECASE):
            parsed = _coerce_date(m.group(1))
            if parsed:
                return parsed
    m = re.search(
        r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})"
        r"\s+\d{1,2}:\d{2}\s*(?:am|pm)\b",
        text[:4000],
        re.IGNORECASE,
    )
    if m:
        parsed = _coerce_date(m.group(1))
        if parsed:
            return parsed

    # Daily FT print desk: "Tuesday, 6 January 2026 02:46" (24h, no am/pm).
    m = re.search(
        r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+)?"
        r"(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})"
        r"\s+\d{1,2}:\d{2}\b",
        text[:4000],
        re.IGNORECASE,
    )
    if m:
        parsed = _coerce_date(m.group(1))
        if parsed:
            return parsed

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
        # LNW-style sentences put the new price ~140 chars after the fuel name
        # ("…reduction of Rs. 25… now fixed at Rs. 382").
        after = segment[m.end() : m.end() + 180]
        # Stop before the next *other* fuel type so "Petrol 92 … 414, while
        # Auto Diesel … 382" does not assign 414 to diesel.
        cut = len(after)
        for other_re in FUEL_NAME_RE.values():
            if other_re is fuel_re:
                continue
            om = other_re.search(after)
            if om:
                cut = min(cut, om.start())
        after = after[:cut]
        price = _extract_price(after)
        if price is not None:
            return price
        before = segment[max(0, m.start() - 60) : m.start()]
        price = _extract_price(before)
        if price is not None:
            return price
    return None


def _is_speculative_piece(title: str | None, url: str | None, text: str = "") -> bool:
    """True for opposition/analysis 'could have been reduced' stories."""
    head = " ".join(filter(None, [title or "", url or "", text[:280]]))
    if not SPECULATIVE_RE.search(head):
        return False
    # Official revision headlines still win even if body quotes speculation.
    if re.search(
        r"\b(?:announces?|announced|revised?|with\s+effect|effective\s+from|"
        r"fuel\s+prices?\s+(?:reduced|increased|revised))\b",
        title or "",
        re.IGNORECASE,
    ):
        return False
    return True


def _extract_prices(
    text: str,
    fallback_date: date,
    *,
    outlet: str | None = None,
    article_url: str | None = None,
    title: str | None = None,
) -> list[PricePoint]:
    if _is_speculative_piece(title, article_url, text):
        return []

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
                points.append(
                    PricePoint(
                        effective_date,
                        fuel_type,
                        found,
                        SOURCE,
                        outlet=outlet,
                        article_url=article_url,
                    )
                )
                break

    # De-dup by fuel type within one article
    seen: set[str] = set()
    return [p for p in points if not (p.fuel_type in seen or seen.add(p.fuel_type))]  # type: ignore[func-returns-value]


# Keep news hits aligned with the UI early-signal window (14 days).
DEFAULT_MAX_AGE_HOURS = 24 * 14


def _poll_feed(
    feed_url: str,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
) -> list[tuple[str, datetime | None, str, str, str | None]]:
    """Return (url, pub_date, title, summary_text, source_url) for recent fuel articles.

    Default window is 14 days — matches early-signal usefulness and tolerates
    Google News pubDates that are rounded or delayed. Title is kept separate
    from the summary so publisher search queries stay clean.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    results: list[tuple[str, datetime | None, str, str, str | None]] = []
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

        # Infer source_url from resolved publisher when Google omitted <source>.
        if not source_url and publisher_url:
            source_url = publisher_url

        url = publisher_url or guid_url or link_url
        if url and url.startswith("http"):
            results.append((url, pub_date, title_text, summary, source_url))

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


def _title_tokens(title: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", title.lower()) if t not in {"the", "and", "for", "from"}}


def _score_url_against_title(url: str, title: str) -> int:
    """Rough relevance: shared tokens between title and URL slug/path."""
    tokens = _title_tokens(title)
    if not tokens:
        return 0
    path = re.sub(r"^https?://[^/]+", "", url).lower()
    return sum(1 for t in tokens if t in path)


def _brave_search_urls(query: str) -> list[str]:
    """Brave Search HTML — reliable from datacenter IPs when DDG returns 202."""
    try:
        with httpx.Client(
            headers={"User-Agent": _BROWSER_UA},
            timeout=15.0,
            follow_redirects=True,
        ) as c:
            r = c.get("https://search.brave.com/search", params={"q": query})
            r.raise_for_status()
            html = r.text
    except Exception as exc:
        log.warning("brave search failed %s: %s", query, exc)
        return []

    urls: list[str] = []
    for a in BeautifulSoup(html, "lxml").find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and "brave.com" not in href and "brave." not in href:
            urls.append(href.split("#")[0].rstrip("/"))
    seen: set[str] = set()
    return [u for u in urls if not (u in seen or seen.add(u))]


def _ddg_search_urls(query: str) -> list[str]:
    """HTML DuckDuckGo search — secondary fallback (often 202-challenged)."""
    html = ""
    for attempt in range(2):
        try:
            with httpx.Client(
                headers={"User-Agent": _BROWSER_UA},
                timeout=15.0,
                follow_redirects=True,
            ) as c:
                r = c.get("https://html.duckduckgo.com/html/", params={"q": query})
                # 202 Accepted is a soft challenge — retry once.
                if r.status_code == 202 and attempt == 0:
                    continue
                r.raise_for_status()
                html = r.text
                break
        except Exception as exc:
            log.warning("ddg search failed %s: %s", query, exc)
            return []

    urls: list[str] = []
    for a in BeautifulSoup(html, "lxml").find_all("a", href=True):
        href = a["href"]
        m = re.search(r"uddg=([^&]+)", href)
        if m:
            href = unquote(m.group(1))
        if href.startswith("http") and "duckduckgo.com" not in href:
            urls.append(href.rstrip("/"))
    # Preserve order, unique
    seen: set[str] = set()
    return [u for u in urls if not (u in seen or seen.add(u))]


def _web_search_urls(query: str) -> list[str]:
    """Prefer Brave; fall back to DuckDuckGo if Brave is empty."""
    urls = _brave_search_urls(query)
    if urls:
        return urls
    return _ddg_search_urls(query)


def _page_title_matches(url: str, title: str) -> bool:
    """Fetch a candidate page and check its <title> overlaps the headline."""
    want = _title_tokens(title)
    if not want:
        return False
    try:
        with httpx.Client(
            headers={"User-Agent": _BROWSER_UA},
            timeout=12.0,
            follow_redirects=True,
        ) as c:
            r = c.get(url)
            r.raise_for_status()
    except Exception:
        return False
    soup = BeautifulSoup(r.text, "lxml")
    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
    have = _title_tokens(page_title)
    # Require majority of distinctive title tokens (ignore tiny overlap).
    overlap = len(want & have)
    return overlap >= max(2, min(4, len(want) // 2))


def _resolve_via_web_search(title: str, host: str, link_re: re.Pattern[str]) -> str | None:
    """Recover a publisher article URL via Brave/DDG site-search."""
    clean = _strip_outlet_suffix(title)
    # Exact-title query first (best for Ada cuid URLs with no slug tokens).
    queries = [
        f'site:{host} "{clean}"',
        f"site:{host} {clean}",
    ]
    seen_urls: set[str] = set()
    candidates: list[str] = []
    for query in queries:
        for u in _web_search_urls(query):
            if u in seen_urls or not link_re.search(u):
                continue
            seen_urls.add(u)
            candidates.append(u)
        if candidates:
            break

    if not candidates:
        return None

    scored = [(_score_url_against_title(u, clean), u) for u in candidates]
    scored.sort(key=lambda item: item[0], reverse=True)

    # Slug match is enough when the URL contains title words.
    if scored[0][0] >= 2:
        return scored[0][1]

    # Ada cuid paths (/news/cm…) have no slug — verify by page title.
    for _score, u in scored[:5]:
        if _page_title_matches(u, clean):
            return u
    return scored[0][1] if scored[0][0] > 0 else None


# Back-compat alias used by older tests / call sites.
def _resolve_via_ddg(title: str, host: str, link_re: re.Pattern[str]) -> str | None:
    return _resolve_via_web_search(title, host, link_re)


def _resolve_island_search(title: str) -> str | None:
    query = _strip_outlet_suffix(title)
    if not query:
        return None
    search_url = "https://island.lk/?s=" + quote(query)
    try:
        with httpx.Client(headers={"User-Agent": _BROWSER_UA}, timeout=15.0, follow_redirects=True) as c:
            r = c.get(search_url)
            r.raise_for_status()
    except Exception as exc:
        log.warning("island search failed %s: %s", search_url, exc)
        return None

    link_re = re.compile(r"https?://(?:www\.)?island\.lk/[a-z0-9\-]+/?", re.IGNORECASE)
    scored: list[tuple[int, str]] = []
    for m in link_re.finditer(r.text):
        u = m.group(0).rstrip("/")
        # Skip non-article paths
        slug = u.rsplit("/", 1)[-1]
        if slug in {"archives", "feed", "category", "tag", "author", "page"}:
            continue
        scored.append((_score_url_against_title(u, query), u))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    # Require at least one shared token so unrelated homepage links don't win.
    if scored[0][0] <= 0:
        return None
    return scored[0][1]


def _resolve_via_publisher_search(title: str, source_url: str | None) -> str | None:
    """Find the article URL by searching the publisher site.

    Google News article tokens no longer embed publisher URLs. For known SL
    outlets we recover the real page via on-site search, or DuckDuckGo
    site-search when the publisher WAF blocks crawlers (Ada / Daily Mirror).
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
        # On-site search often 403s from datacenter IPs — try it, then Brave.
        search_url = "https://www.dailymirror.lk/search/" + query.replace(" ", "-")
        link_re = re.compile(
            r"https://www\.dailymirror\.lk/[A-Za-z0-9\-]+/[A-Za-z0-9\-]+/\d+",
            re.IGNORECASE,
        )
    elif "island.lk" in host:
        return _resolve_island_search(title)
    elif "onlanka.com" in host:
        search_url = "https://www.onlanka.com/?s=" + query.replace(" ", "+")
        link_re = re.compile(
            r"https://www\.onlanka\.com/news/[a-z0-9\-]+\.html",
            re.IGNORECASE,
        )
    elif "lankanewsweb.net" in host:
        search_url = "https://lankanewsweb.net/?s=" + query.replace(" ", "+")
        link_re = re.compile(
            r"https://lankanewsweb\.net/archives/\d+/[a-z0-9\-]+/?",
            re.IGNORECASE,
        )
    elif "adaderana.lk" in host:
        # Ada on-site search returns 410. Newer articles use cuid paths
        # (/news/cm…) as well as classic /news/<nid>/slug.
        return _resolve_via_web_search(
            title,
            "adaderana.lk",
            re.compile(
                r"https?://(?:www\.)?adaderana\.lk/"
                r"(?:news\.php\?nid=\d+|news/[A-Za-z0-9]+(?:/[A-Za-z0-9\-]+)?)",
                re.IGNORECASE,
            ),
        )
    elif "newsfirst.lk" in host:
        # NewsFirst English uses /YYYY/MM/DD/slug; on-site search is weak so
        # go straight to Brave/DDG site-search.
        return _resolve_via_web_search(
            title,
            "newsfirst.lk",
            re.compile(
                r"https?://(?:english\.|www\.)?newsfirst\.lk/"
                r"\d{4}/\d{2}/\d{2}/[A-Za-z0-9\-]+/?",
                re.IGNORECASE,
            ),
        )
    elif "themorning.lk" in host:
        # The Morning uses opaque /articles/<cuid> paths; on-site ?s= is a no-op.
        return _resolve_via_web_search(
            title,
            "themorning.lk",
            re.compile(
                r"https?://(?:www\.)?themorning\.lk/articles/[A-Za-z0-9]+/?",
                re.IGNORECASE,
            ),
        )
    elif "ft.lk" in host:
        return _resolve_via_web_search(
            title,
            "ft.lk",
            re.compile(
                r"https?://(?:www\.)?ft\.lk/[A-Za-z0-9\-]+/[A-Za-z0-9\-]+/\d+(?:-\d+)?",
                re.IGNORECASE,
            ),
        )
    elif "sundaytimes.lk" in host:
        return _resolve_via_web_search(
            title,
            "sundaytimes.lk",
            re.compile(
                r"https?://(?:www\.)?sundaytimes\.lk/\d+/"
                r"[a-z0-9\-]+/[a-z0-9\-]+\.html",
                re.IGNORECASE,
            ),
        )
    elif "srilankamirror.com" in host:
        # Cloudflare often blocks direct fetch; Brave still indexes article URLs.
        return _resolve_via_web_search(
            title,
            "srilankamirror.com",
            re.compile(
                r"https?://(?:www\.)?srilankamirror\.com/"
                r"(?:news|biz|business|news-features)/[A-Za-z0-9\-]+/?",
                re.IGNORECASE,
            ),
        )
    else:
        return None

    assert search_url is not None and link_re is not None
    mirror_fallback = (
        "dailymirror.lk" in host,
        re.compile(
            r"https://www\.dailymirror\.lk/[A-Za-z0-9\-]+/[A-Za-z0-9\-]+/\d+",
            re.IGNORECASE,
        ),
    )
    try:
        with httpx.Client(headers={"User-Agent": _BROWSER_UA}, timeout=15.0, follow_redirects=True) as c:
            r = c.get(search_url)
            r.raise_for_status()
    except Exception as exc:
        log.warning("publisher search failed %s: %s", search_url, exc)
        if mirror_fallback[0]:
            return _resolve_via_web_search(title, "dailymirror.lk", mirror_fallback[1])
        return None

    links = link_re.findall(r.text)
    if not links:
        if mirror_fallback[0]:
            return _resolve_via_web_search(title, "dailymirror.lk", mirror_fallback[1])
        return None
    # Prefer the URL whose slug best matches the title.
    scored = [(_score_url_against_title(u, query), u) for u in links]
    scored.sort(key=lambda item: item[0], reverse=True)
    seen: set[str] = set()
    for _score, u in scored:
        key = u.rstrip("/")
        if key not in seen:
            seen.add(key)
            return u
    return None


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
    outlet = outlet_from_host(source_url or url)
    try:
        with httpx.Client(headers={"User-Agent": _BROWSER_UA}, timeout=20.0, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
    except Exception as exc:
        log.warning("article fetch failed %s: %s", url, exc)
        return []

    article_url = str(r.url)
    # If we're still on Google's servers, resolve the publisher URL.
    if "news.google.com" in article_url:
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
                    article_url = str(r2.url)
                    outlet = outlet_from_host(article_url)
            except Exception as exc:
                log.warning("publisher article fetch failed %s: %s", actual_url, exc)
        else:
            log.info("could not resolve publisher URL — mining Google preview for %s", url)

    if outlet == "unknown":
        outlet = outlet_from_host(article_url)

    soup = BeautifulSoup(r.text, "lxml")

    published = _parse_article_published_date(soup, article_url)
    url_hint = _date_hint_from_url(article_url)
    if url_hint is not None:
        # URL path dates beat site-chrome "today" stamps.
        published = url_hint
    if published is not None:
        # Prefer the real article date over Google News pubDate (often wrong
        # for re-indexed older stories).
        fallback_date = published
        age_days = (date.today() - published).days
        if age_days > (DEFAULT_MAX_AGE_HOURS // 24) + 1:
            log.info(
                "skipping stale article %s published %s (%d days old)",
                article_url,
                published,
                age_days,
            )
            return []

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

    if _is_speculative_piece(title, article_url):
        log.info("skipping speculative article %s", article_url)
        return []

    text = body.get_text(" ", strip=True)
    points = _extract_prices(
        text,
        fallback_date,
        outlet=outlet,
        article_url=article_url,
        title=title,
    )
    if points:
        return points
    # Last resort: whole-page text (some WP themes bury the body).
    return _extract_prices(
        soup.get_text(" ", strip=True),
        fallback_date,
        outlet=outlet,
        article_url=article_url,
        title=title,
    )


# Outlets Google News often under-indexes for the latest CPC revision.
# Brave site-search fills the gap (Daily Mirror especially).
BRAVE_DISCOVERY: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "dailymirror.lk",
        'site:dailymirror.lk (fuel OR petrol OR diesel) (prices OR price) '
        "(reduced OR increased OR revised OR revision)",
        re.compile(
            r"https://www\.dailymirror\.lk/[A-Za-z0-9\-]+/[A-Za-z0-9\-]+/\d+",
            re.IGNORECASE,
        ),
    ),
    (
        "onlanka.com",
        'site:onlanka.com ("fuel prices" OR "revises fuel") '
        "(reduced OR revised OR revision OR cut)",
        re.compile(
            r"https://www\.onlanka\.com/news/[a-z0-9\-]+\.html",
            re.IGNORECASE,
        ),
    ),
    (
        "lankanewsweb.net",
        'site:lankanewsweb.net (fuel OR petrol OR ceypetco) '
        "(prices OR price OR revision) (reduced OR revised OR increased)",
        re.compile(
            r"https://lankanewsweb\.net/archives/\d+/[a-z0-9\-]+/?",
            re.IGNORECASE,
        ),
    ),
    (
        "newsfirst.lk",
        'site:newsfirst.lk (fuel OR petrol OR CPC OR ceypetco) '
        "(prices OR price) (reduced OR increased OR revised OR revision)",
        re.compile(
            r"https?://(?:english\.|www\.)?newsfirst\.lk/"
            r"\d{4}/\d{2}/\d{2}/[A-Za-z0-9\-]+/?",
            re.IGNORECASE,
        ),
    ),
    (
        "adaderana.lk",
        'site:adaderana.lk (fuel OR petrol OR diesel) (prices OR price) '
        "(reduced OR increased OR revised)",
        re.compile(
            r"https?://(?:www\.)?adaderana\.lk/"
            r"(?:news\.php\?nid=\d+|news/[A-Za-z0-9]+(?:/[A-Za-z0-9\-]+)?)",
            re.IGNORECASE,
        ),
    ),
    (
        "economynext.com",
        'site:economynext.com (fuel OR petrol OR ceypetco) (price OR prices) '
        "(reduced OR increased OR revised)",
        re.compile(r"https://economynext\.com/[a-z0-9\-]+-\d+/", re.IGNORECASE),
    ),
    (
        "themorning.lk",
        'site:themorning.lk (fuel OR petrol OR ceypetco) (prices OR price) '
        "(reduced OR increased OR revised OR revision OR hike)",
        re.compile(
            r"https?://(?:www\.)?themorning\.lk/articles/[A-Za-z0-9]+/?",
            re.IGNORECASE,
        ),
    ),
    (
        "ft.lk",
        # Year token biases Brave away from evergreen 2022–2024 revision wires.
        'site:ft.lk (fuel OR petrol OR ceypetco) (prices OR price) '
        "(reduced OR increased OR revised OR revision) 2026",
        re.compile(
            r"https?://(?:www\.)?ft\.lk/[A-Za-z0-9\-]+/[A-Za-z0-9\-]+/\d+(?:-\d+)?",
            re.IGNORECASE,
        ),
    ),
    (
        "sundaytimes.lk",
        'site:sundaytimes.lk (fuel OR petrol) (prices OR price) '
        "(reduced OR increased OR revised OR revision) 2026",
        re.compile(
            r"https?://(?:www\.)?sundaytimes\.lk/\d+/"
            r"[a-z0-9\-]+/[a-z0-9\-]+\.html",
            re.IGNORECASE,
        ),
    ),
    (
        "srilankamirror.com",
        'site:srilankamirror.com (fuel OR petrol) (prices OR price) '
        "(reduced OR increased OR revised OR revision OR slashed)",
        re.compile(
            r"https?://(?:www\.)?srilankamirror\.com/"
            r"(?:news|biz|business|news-features)/[A-Za-z0-9\-]+/?",
            re.IGNORECASE,
        ),
    ),
    (
        "newswire.lk",
        'site:newswire.lk (fuel OR petrol OR ceypetco) (prices OR price) '
        "(reduced OR increased OR revised OR revision)",
        re.compile(
            r"https://www\.newswire\.lk/\d{4}/\d{2}/\d{2}/[a-z0-9\-]+/?",
            re.IGNORECASE,
        ),
    ),
    (
        "island.lk",
        'site:island.lk (fuel OR petrol OR ceypetco) (prices OR price) '
        "(reduced OR increased OR revised)",
        re.compile(
            r"https://island\.lk/[a-z0-9\-]+/?",
            re.IGNORECASE,
        ),
    ),
]


def _discover_via_brave(
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
) -> list[tuple[str, datetime | None, str, str, str | None]]:
    """Find recent revision articles via Brave when Google News misses them.

    Returns the same tuple shape as _poll_feed:
    (url, pub_date, title, summary, source_url).
    """
    results: list[tuple[str, datetime | None, str, str, str | None]] = []
    seen: set[str] = set()
    max_age_days = (max_age_hours // 24) + 1
    for host, query, link_re in BRAVE_DISCOVERY:
        urls = _brave_search_urls(query)
        matched = [u for u in urls if link_re.search(u)]
        log.info("brave discovery %s → %d candidate urls", host, len(matched))
        # Pace Brave HTML search — bursty loops trip 429 from Actions / cloud IPs.
        time.sleep(0.8)
        for url in matched[:8]:
            key = url.split("?")[0].rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            url_hint = _date_hint_from_url(url)
            if url_hint is not None and (date.today() - url_hint).days > max_age_days:
                continue
            # Fetch title from the page so keyword / speculative filters work.
            try:
                with httpx.Client(
                    headers={"User-Agent": _BROWSER_UA},
                    timeout=15.0,
                    follow_redirects=True,
                ) as c:
                    r = c.get(url)
                    r.raise_for_status()
            except Exception as exc:
                log.warning("brave discovery fetch failed %s: %s", url, exc)
                continue
            soup = BeautifulSoup(r.text, "lxml")
            title = soup.title.get_text(" ", strip=True) if soup.title else ""
            title = _strip_outlet_suffix(title)
            if not FUEL_KEYWORDS.search(title):
                continue
            if _is_speculative_piece(title, url):
                continue
            published = url_hint or _parse_article_published_date(soup, str(r.url))
            if published is not None:
                age_hours = (date.today() - published).days * 24
                if age_hours > max_age_hours + 24:
                    continue
                pub_dt = datetime(
                    published.year, published.month, published.day, tzinfo=timezone.utc
                )
            else:
                # No reliable date — Brave ranks evergreen wires highly; skip.
                continue
            source_url = f"https://{host}"
            results.append((str(r.url), pub_dt, title, title, source_url))
    return results


def run(max_age_hours: int = DEFAULT_MAX_AGE_HOURS) -> Iterable[PricePoint]:
    """Scrape all configured news feeds and return per-outlet price hits.

    Does NOT collapse outlets early — run_news selects the best price via
    multi-outlet consensus + trust weights. Only de-dupes the same article
    URL reporting the same fuel.
    """
    all_points: list[PricePoint] = []
    seen_urls: set[str] = set()

    article_batches: list[tuple[str, list]] = [
        (feed_url, _poll_feed(feed_url, max_age_hours=max_age_hours))
        for feed_url in FEEDS
    ]
    brave_articles = _discover_via_brave(max_age_hours=max_age_hours)
    article_batches.append(("brave-discovery", brave_articles))

    for feed_label, articles in article_batches:
        log.info("news feed %s → %d fuel articles", feed_label, len(articles))
        for url, pub_date, title, summary, source_url in articles:
            # Normalize Google article URLs so the same story isn't scraped twice.
            url_key = url.split("?")[0].rstrip("/")
            if url_key in seen_urls:
                continue
            seen_urls.add(url_key)

            fallback_date = pub_date.date() if pub_date else date.today()
            outlet = outlet_from_host(source_url or url)
            article_title = title or summary

            if _is_speculative_piece(article_title, url):
                log.info("skipping speculative headline %s", article_title[:80])
                continue

            # Try extracting prices from the RSS summary first (cheaper, no fetch needed)
            points = _extract_prices(
                summary,
                fallback_date,
                outlet=outlet,
                article_url=url,
                title=article_title,
            )
            if points:
                log.info("news summary hit %s (%s) → %d prices", url, outlet, len(points))
            else:
                # Fall back to fetching the full article — pass title (not the
                # full summary) so publisher search queries stay precise.
                points = _scrape_article(
                    url, pub_date, title=article_title, source_url=source_url
                )
                if points:
                    log.info(
                        "news article %s (%s) → %d prices",
                        points[0].article_url or url,
                        points[0].outlet or outlet,
                        len(points),
                    )
            all_points.extend(points)

    # De-dup identical article+fuel rows only (keep distinct outlets).
    seen: set[tuple[str, str, str, float]] = set()
    unique: list[PricePoint] = []
    for p in all_points:
        key = (
            p.outlet or "unknown",
            p.article_url or "",
            p.fuel_type,
            round(p.price_lkr, 2),
        )
        if key not in seen:
            seen.add(key)
            unique.append(p)

    log.info(
        "news scraper total: %d price hits across %d outlets",
        len(unique),
        len({p.outlet or "unknown" for p in unique}),
    )
    return unique
