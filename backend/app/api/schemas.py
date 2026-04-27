from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class AlertSubscribeIn(BaseModel):
    email: EmailStr
    fuel_type: str = Field(..., description="e.g. 'petrol_92'")
    threshold: float = Field(..., gt=0)
    direction: str = Field(..., pattern="^(above|below)$")


class AlertOut(BaseModel):
    id: int
    email: str
    fuel_type: str
    threshold: float
    direction: str
