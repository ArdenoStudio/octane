"""Shared HTTP helpers for scrapers."""
from __future__ import annotations

import logging

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)


def client(
    timeout: float = 30.0,
    *,
    verify: bool = True,
    headers: dict[str, str] | None = None,
) -> httpx.Client:
    merged = {"User-Agent": get_settings().scraper_user_agent}
    if headers:
        merged.update(headers)
    return httpx.Client(
        headers=merged,
        timeout=timeout,
        follow_redirects=True,
        verify=verify,
    )


def _is_tls_verify_error(exc: BaseException) -> bool:
    """True when the failure is an expired / untrusted server certificate."""
    msg = str(exc).upper()
    return any(
        token in msg
        for token in (
            "CERTIFICATE_VERIFY_FAILED",
            "CERTIFICATE HAS EXPIRED",
            "SSL: CERTIFICATE",
            "CERTIFICATE_VERIFY",
        )
    )


def get_text(
    url: str,
    *,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
    tls_fallback: bool = False,
) -> str:
    """GET a URL and return response text.

    When ``tls_fallback`` is True and the first attempt fails TLS verification
    (e.g. an expired government-site certificate), retry once with
    ``verify=False`` so scrapers keep working until the operator renews the cert.
    """
    with client(timeout=timeout, headers=headers) as c:
        try:
            r = c.get(url)
            r.raise_for_status()
            return r.text
        except (httpx.ConnectError, httpx.TransportError) as e:
            if not tls_fallback or not _is_tls_verify_error(e):
                raise
            log.warning(
                "TLS verification failed for %s (%s); retrying without verification",
                url,
                e,
            )

    with client(timeout=timeout, headers=headers, verify=False) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text
