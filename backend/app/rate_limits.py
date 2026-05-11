"""Shared SlowAPI limiter singleton (imports config once at load)."""

from fastapi import Request
from slowapi import Limiter

from app.config import get_settings


def _get_client_ip(request: Request) -> str:
    # Fly.io sets Fly-Client-IP to the real client IP before the request
    # reaches the app — it cannot be spoofed by the client.
    fly_ip = request.headers.get("Fly-Client-IP")
    if fly_ip:
        return fly_ip
    # Fall back to the leftmost value in X-Forwarded-For (standard proxy header).
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


_limiter_settings = get_settings()

limiter = Limiter(
    key_func=_get_client_ip,
    default_limits=[_limiter_settings.rate_limit],
)
