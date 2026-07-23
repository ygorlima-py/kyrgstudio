"""Unit tests for the API liveness endpoint."""

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

import httpx
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import ValidationError

from app.api.routers.health import HealthResponse, health_check, router


ResultT = TypeVar("ResultT")


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _application() -> FastAPI:
    application = FastAPI()
    application.include_router(router)
    return application


def test_health_check_returns_ok() -> None:
    """Return the stable liveness response from the endpoint function."""

    response = _run(health_check())

    assert response == HealthResponse(status="ok")
    assert response.model_dump() == {"status": "ok"}


def test_health_route_is_registered() -> None:
    """Expose one GET route at the public liveness path."""

    health_routes = [
        route
        for route in router.routes
        if isinstance(route, APIRoute) and route.path == "/health"
    ]

    assert len(health_routes) == 1
    assert health_routes[0].methods == {"GET"}
    assert health_routes[0].response_model is HealthResponse
    assert health_routes[0].status_code == 200


def test_health_response_rejects_extra_fields() -> None:
    """Keep the liveness response schema explicit and closed."""

    with pytest.raises(ValidationError):
        HealthResponse(status="ok", database="connected")  # type: ignore[call-arg]


def test_health_route_does_not_require_application_resources() -> None:
    """Answer without settings, database, storage, queue, or auth resources."""

    async def scenario() -> httpx.Response:
        application = _application()
        transport = httpx.ASGITransport(app=application)

        async with httpx.AsyncClient(
            transport=transport,
            base_url="https://api.example.com",
        ) as client:
            return await client.get("/health")

    response = _run(scenario())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
