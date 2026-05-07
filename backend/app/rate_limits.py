"""Shared SlowAPI limiter singleton (imports config once at load)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

_limiter_settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_limiter_settings.rate_limit],
)
