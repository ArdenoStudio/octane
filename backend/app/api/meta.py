from __future__ import annotations

from fastapi import APIRouter

from app import fuel as fuel_mod

router = APIRouter(prefix="/v1", tags=["meta"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/fuels")
def fuels():
    return {
        "fuels": [
            {"id": fid, "display": fuel_mod.DISPLAY[fid]}
            for fid in fuel_mod.ALL_FUELS
        ]
    }
