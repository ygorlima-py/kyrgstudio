"""Liveness endpoint for the HTTP API process."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response returned when the API process is alive."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check API liveness",
)
async def health_check() -> HealthResponse:
    """Confirm that the API process can receive and answer HTTP requests."""

    return HealthResponse()


__all__ = [
    "HealthResponse",
    "router",
]
