from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api import alerts, calculator, comparison, embed, meta, prices
from app.config import get_settings
from app.db import migrate

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit],
)

app = FastAPI(
    title="Octane API",
    description="Live Sri Lanka fuel price intelligence — by Ardeno Studio.",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(meta.router)
app.include_router(prices.router)
app.include_router(comparison.router)
app.include_router(calculator.router)
app.include_router(alerts.router)
app.include_router(embed.router)


@app.on_event("startup")
def on_startup() -> None:
    """Apply any pending DB migrations when the API starts up."""
    migrate.run()


@app.get("/")
def root():
    return {
        "name": "Octane API",
        "docs": "/docs",
        "site": "https://octane.lk",
    }
