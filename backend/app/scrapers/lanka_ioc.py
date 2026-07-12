"""Lanka IOC scraper.

``lankaiocoil.lk`` no longer resolves (DNS NXDOMAIN across public resolvers).
The current corporate site ``lankaioc.com`` does not publish retail pump
prices. We therefore:

1. Best-effort fetch of any still-live official URL (in case DNS / content
   comes back).
2. Fall back to LIOC-specific news articles (Newswire, Newsfirst, OnLanka,
   LNW, Google News) and reuse the news scraper's price extraction, tagged
   ``source="lanka_ioc"``.

For each fuel, the newest extracted revision wins so partial updates
(e.g. diesel-only hikes) merge cleanly with earlier full tables.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from app import fuel as fuel_mod
from app.scrapers import news as news_mod
from app.scrapers.cpc import PricePoint
from app.scrapers.http import client, get_text

log = logging.getLogger(__name__)

SOURCE = "lanka_ioc"

# Legacy domain (dead DNS) + current corporate site (no pump prices today).
OFFICIAL_URLS = (
    "https://lankaiocoil.lk/",
    "https://www.lankaiocoil.lk/",
    "https://www.lankaioc.com/",
    "https://lankaioc.com/",
)

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_BROWSER_HEADERS = {
    "User-Agent": _BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}

LIOC_MENTION_RE = re.compile(
    r"\b(?:lanka\s*ioc|lioc|lanka\s*indian\s*oil)\b",
    re.IGNORECASE,
)
FUEL_PRICE_TITLE_RE = re.compile(
    r"(?:fuel|petrol|diesel|kerosene).{0,40}(?:price|prices|hike|revis|increase|reduce|cut)"
    r"|(?:price|prices).{0,40}(?:fuel|petrol|diesel|kerosene)"
    r"|(?:petrol|diesel|kerosene)\s+\d{2,4}",
    re.IGNORECASE,
)

# Publisher search pages that reliably list LIOC revision stories.
SEARCH_PAGES = (
    "https://www.newswire.lk/?s=Lanka+IOC+fuel",
    "https://www.newswire.lk/?s=Lanka+IOC",
    "https://www.onlanka.com/?s=Lanka+IOC+fuel+prices",
    "https://lankanewsweb.net/?s=Lanka+IOC+fuel",
)

GOOGLE_FEEDS = (
    "https://news.google.com/rss/search?q=%22Lanka+IOC%22+(fuel+OR+petrol+OR+diesel)"
    "+(price+OR+prices+OR+hike+OR+revises+OR+increases)&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=LIOC+(petrol+OR+diesel)+(price+OR+prices)"
    "+%22Sri+Lanka%22&hl=en-US&gl=US&ceid=US:en",
)

ARTICLE_LINK_RE = re.compile(
    r"https?://(?:www\.)?(?:"
    r"newswire\.lk/\d{4}/\d{2}/\d{2}/[a-z0-9\-]+/?"
    r"|onlanka\.com/news/[a-z0-9\-]+\.html"
    r"|lankanewsweb\.net/archives/\d+/[a-z0-9\-]+/?"
    r"|newsfirst\.lk/\d{4}/\d{2}/\d{2}/[a-z0-9\-]+/?"
    r"|adaderana\.lk/(?:news\.php\?nid=\d+|news/[A-Za-z0-9]+(?:/[A-Za-z0-9\-]+)?)"
    r"|dailymirror\.lk/[A-Za-z0-9\-]+/[A-Za-z0-9\-]+/\d+"
    r")",
    re.IGNORECASE,
)
URL_DATE_RE = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")
# Drop ancient search hits before we even fetch them.
MIN_ARTICLE_YEAR = 2025

# Quiet periods between LIOC revisions can exceed a month — keep enough
# history to recover the last full/partial table.
NEWS_LOOKBACK_DAYS = 180
# Stop once we have a full fuel set from news (avoids thrashing Google WAF).
EARLY_EXIT_FUELS = 5

# Hard anchors for recent LIOC revision stories. Discovery still runs; these
# ensure we keep working when Newsfirst/Brave rate-limit archives.
SEED_ARTICLES: tuple[tuple[str, str], ...] = (
    (
        "https://www.dailymirror.lk/breaking-news/LIOC-and-Sinopec-raise-fuel-prices-following-CPC-revision/108-341596",
        "LIOC and Sinopec raise fuel prices following CPC revision",
    ),
    (
        "https://www.newswire.lk/2026/05/03/lanka-ioc-raises-petrol-92-and-auto-diesel-prices-other-types-unchanged/",
        "Lanka IOC raises petrol 92 and auto diesel prices; other types unchanged",
    ),
    (
        "https://www.newswire.lk/2026/04/08/lanka-ioc-increases-diesel-prices-cpc-unchanged/",
        "Lanka IOC increases diesel prices; CPC unchanged",
    ),
    (
        "https://www.newswire.lk/2026/03/22/lanka-ioc-revises-fuel-prices-rs-382-588-range/",
        "Lanka IOC revises fuel prices: Rs. 382–588 range",
    ),
)

def _retag(points: list[PricePoint]) -> list[PricePoint]:
    return [
        PricePoint(
            p.recorded_at,
            p.fuel_type,
            p.price_lkr,
            SOURCE,
            outlet=p.outlet,
            article_url=p.article_url,
        )
        for p in points
    ]


def _url_date(url: str) -> date | None:
    m = URL_DATE_RE.search(url)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _is_recent_enough_url(url: str) -> bool:
    """Filter obviously ancient publisher URLs before fetching."""
    d = _url_date(url)
    if d is not None:
        return d >= date.today() - timedelta(days=NEWS_LOOKBACK_DAYS)
    # LNW archive IDs / Ada cuid paths — allow; stale check happens after fetch.
    year_m = re.search(r"/(\d{4})/", url)
    if year_m:
        return int(year_m.group(1)) >= MIN_ARTICLE_YEAR
    return True


def _parse_official_html(html: str) -> list[PricePoint]:
    """Legacy homepage regex scrape — used if an official URL recovers."""
    today = date.today()
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    points: list[PricePoint] = []
    for alias, fuel in fuel_mod.CPC_ALIASES.items():
        pattern = re.compile(
            re.escape(alias) + r"[^\d]{0,40}(\d{2,4}(?:\.\d{1,2})?)",
            re.IGNORECASE,
        )
        m = pattern.search(text)
        if not m:
            continue
        try:
            price = float(m.group(1))
        except ValueError:
            continue
        if 50 <= price <= 2000:
            points.append(PricePoint(today, fuel, price, source=SOURCE))
    seen: set[str] = set()
    unique: list[PricePoint] = []
    for p in points:
        if p.fuel_type in seen:
            continue
        seen.add(p.fuel_type)
        unique.append(p)
    return unique


def fetch_from_official() -> list[PricePoint]:
    """Try official LIOC URLs. Returns [] when DNS/site has no prices."""
    for url in OFFICIAL_URLS:
        try:
            html = get_text(
                url,
                timeout=20.0,
                headers=_BROWSER_HEADERS,
                tls_fallback=True,
            )
        except Exception as exc:  # noqa: BLE001
            log.info("official LIOC fetch failed %s: %s", url, exc)
            continue
        points = _parse_official_html(html)
        if len(points) >= 2:
            log.info("LIOC official site returned %d fuels from %s", len(points), url)
            return points
        log.info("official LIOC page had no pump prices: %s", url)
    return []


def _article_urls_from_html(html: str, base_host: str | None = None) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("/") and base_host:
            href = base_host.rstrip("/") + href
        if not ARTICLE_LINK_RE.search(href):
            continue
        if not _is_recent_enough_url(href):
            continue
        title = a.get_text(" ", strip=True)
        if not title or len(title) < 12:
            continue
        if not LIOC_MENTION_RE.search(title + " " + href):
            continue
        if not FUEL_PRICE_TITLE_RE.search(title):
            continue
        out.append((href.split("#")[0].rstrip("/"), title))
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for href, title in out:
        key = href.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        unique.append((href, title))
    return unique


def _article_urls_from_search_page(url: str) -> list[tuple[str, str]]:
    """Return (article_url, link_text) pairs from a publisher search page."""
    try:
        with client(timeout=20.0, headers=_BROWSER_HEADERS) as c:
            r = c.get(url)
            r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        log.warning("LIOC search page failed %s: %s", url, exc)
        return []

    host = None
    if "newsfirst.lk" in url:
        host = "https://www.newsfirst.lk"
    elif "newswire.lk" in url:
        host = "https://www.newswire.lk"
    elif "onlanka.com" in url:
        host = "https://www.onlanka.com"
    elif "lankanewsweb.net" in url:
        host = "https://lankanewsweb.net"
    return _article_urls_from_html(r.text, host)


def _google_feed_items() -> list[tuple[str, datetime | None, str, str | None]]:
    """Return (url, pub_date, title, source_url) for LIOC Google News hits."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=NEWS_LOOKBACK_DAYS)
    items: list[tuple[str, datetime | None, str, str | None]] = []
    for feed_url in GOOGLE_FEEDS:
        try:
            with client(timeout=20.0, headers=_BROWSER_HEADERS) as c:
                r = c.get(feed_url)
                r.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            log.warning("LIOC google feed failed %s: %s", feed_url, exc)
            continue
        soup = BeautifulSoup(r.text, "xml")
        for item in soup.find_all("item"):
            title = item.find("title").get_text(strip=True) if item.find("title") else ""
            if not LIOC_MENTION_RE.search(title):
                continue
            if not FUEL_PRICE_TITLE_RE.search(title):
                continue
            link = item.find("link").get_text(strip=True) if item.find("link") else ""
            if not link:
                continue
            pub_tag = item.find("pubDate")
            pub_date = None
            if pub_tag and pub_tag.get_text(strip=True):
                try:
                    pub_date = parsedate_to_datetime(pub_tag.get_text(strip=True))
                except Exception:  # noqa: BLE001
                    pub_date = None
            if pub_date and pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            if pub_date and pub_date < cutoff:
                continue
            source_tag = item.find("source")
            source_url = (
                source_tag.get("url") if source_tag and source_tag.has_attr("url") else None
            )
            items.append((link, pub_date, title, source_url))
    return items


def _slugify(title: str) -> str:
    clean = news_mod._strip_outlet_suffix(title).lower()
    clean = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    return clean


def _guess_newsfirst_url(title: str, pub: date) -> str | None:
    slug = _slugify(title)
    if not slug:
        return None
    return f"https://www.newsfirst.lk/{pub:%Y/%m/%d}/{slug}"


def _discover_article_targets() -> list[tuple[str, datetime | None, str, str | None]]:
    """Collect (url, pub_date, title, source_url) candidates, newest first."""
    targets: list[tuple[str, datetime | None, str, str | None]] = []
    seen: set[str] = set()
    seed_urls = {href.rstrip("/") for href, _ in SEED_ARTICLES}
    seed_rank = {href.rstrip("/"): i for i, (href, _) in enumerate(SEED_ARTICLES)}

    def _add(url: str, pub: datetime | None, title: str, source: str | None) -> None:
        key = url.rstrip("/")
        if key in seen:
            return
        if url.startswith("http") and "news.google.com" not in url and not _is_recent_enough_url(url):
            return
        seen.add(key)
        targets.append((url, pub, title, source))

    # Seeded anchors first — survive publisher WAF / search outages.
    for href, title in SEED_ARTICLES:
        _add(href, None, title, href)

    google_items = _google_feed_items()

    # Direct publisher search hits.
    for page in SEARCH_PAGES:
        for href, title in _article_urls_from_search_page(page):
            _add(href, None, title, href)

    # Guess Newsfirst article URLs from Google titles + pubDates.
    for _url, pub, title, source in google_items:
        if not pub:
            continue
        if source and "newsfirst.lk" not in source:
            if not re.search(r"news\s*first|news\s*1st", title, re.I):
                continue
        guessed = _guess_newsfirst_url(title, pub.date())
        if guessed:
            _add(guessed, pub, title, guessed)

    for url, pub, title, source in google_items:
        _add(url, pub, title, source)

    def _sort_key(item: tuple[str, datetime | None, str, str | None]) -> tuple:
        url, pub, _title, _src = item
        key = url.rstrip("/")
        is_seed = 0 if key in seed_urls else 1
        is_google = 1 if "news.google.com" in url else 0
        is_newsfirst = 1 if "newsfirst.lk" in url else 0
        d = _url_date(url) or (pub.date() if pub else date.min)
        return (
            is_seed,
            seed_rank.get(key, 999) if is_seed == 0 else 0,
            is_google,
            is_newsfirst,
            -d.toordinal(),
        )

    targets.sort(key=_sort_key)
    return targets


def _scrape_lioc_article(
    url: str,
    pub_date: datetime | None,
    title: str,
    source_url: str | None,
) -> list[PricePoint]:
    points = news_mod._scrape_article(
        url,
        pub_date,
        title=title,
        source_url=source_url,
        max_age_hours=NEWS_LOOKBACK_DAYS * 24,
    )
    if not points:
        return []
    cutoff = date.today() - timedelta(days=NEWS_LOOKBACK_DAYS)
    points = [p for p in points if p.recorded_at >= cutoff]
    return _retag(points)


def _merge_newest_per_fuel(points: list[PricePoint]) -> list[PricePoint]:
    best: dict[str, PricePoint] = {}
    for p in points:
        prev = best.get(p.fuel_type)
        if prev is None or p.recorded_at > prev.recorded_at:
            best[p.fuel_type] = p
            continue
        if p.recorded_at == prev.recorded_at and p.article_url and not prev.article_url:
            best[p.fuel_type] = p
    return [best[f] for f in fuel_mod.ALL_FUELS if f in best]


def fetch_from_news() -> list[PricePoint]:
    """Scrape LIOC retail prices from recent news revisions."""
    collected: list[PricePoint] = []
    targets = _discover_article_targets()
    log.info("LIOC news discovery found %d candidate articles", len(targets))
    for url, pub, title, source in targets:
        try:
            pts = _scrape_lioc_article(url, pub, title, source)
        except Exception as exc:  # noqa: BLE001
            log.warning("LIOC article scrape failed %s: %s", url, exc)
            continue
        if pts:
            log.info(
                "LIOC article %s -> %s",
                url,
                {p.fuel_type: p.price_lkr for p in pts},
            )
            collected.extend(pts)
            merged = _merge_newest_per_fuel(collected)
            if len(merged) >= EARLY_EXIT_FUELS:
                log.info("LIOC early exit with %d fuels from %s", len(merged), url)
                return merged

    return _merge_newest_per_fuel(collected)


def fetch_latest() -> list[PricePoint]:
    official = fetch_from_official()
    if len(official) >= 3:
        return official
    news_points = fetch_from_news()
    if news_points:
        return news_points
    # Prefer a partial official parse over nothing.
    return official


def run() -> list[PricePoint]:
    return fetch_latest()
