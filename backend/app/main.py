from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, calculator, comparison, embed, meta, prices
from app.config import get_settings

app = FastAPI(
    title="Octane API",
    description="Live Sri Lanka fuel price intelligence — by Ardeno Studio.",
    version="1.0.0",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
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


@app.get("/")
def root():
    return {
        "name": "Octane API",
        "docs": "/docs",
        "site": "https://octane.lk",
    }
