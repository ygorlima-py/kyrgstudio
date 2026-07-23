"""Unit tests for request correlation middleware."""

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any, TypeVar, cast
from uuid import UUID

import pytest
from fastapi import FastAPI
from starlette.datastructures import Headers
from starlette.types import Message, Receive, Scope, Send

import app.api.middleware as middleware_module
from app.api.middleware import (
    REQUEST_ID_HEADER,
    RequestIdMiddleware,
    install_request_id_middleware,
)


ResultT = TypeVar("ResultT")
GENERATED_REQUEST_ID = "12345678123456781234567812345678"


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


@dataclass(frozen=True)
class MiddlewareExecution:
    """Captured state and response messages from one middleware invocation."""

    downstream_request_id: str
    messages: list[Message]

    @property
    def response_headers(self) -> Headers:
        start_message = next(
            message
            for message in self.messages
            if message["type"] == "http.response.start"
        )
        return Headers(raw=start_message["headers"])


def _scope(request_id: str | None = None) -> Scope:
    headers: list[tuple[bytes, bytes]] = []

    if request_id is not None:
        headers.append(
            (
                REQUEST_ID_HEADER.lower().encode("ascii"),
                request_id.encode("latin-1"),
            )
        )

    return cast(
        Scope,
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/health",
            "raw_path": b"/health",
            "query_string": b"",
            "root_path": "",
            "headers": headers,
            "client": ("127.0.0.1", 50000),
            "server": ("api.example.com", 443),
            "state": {},
        },
    )


def _execute_middleware(request_id: str | None = None) -> MiddlewareExecution:
    messages: list[Message] = []
    downstream_request_ids: list[str] = []

    async def downstream(
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        del receive
        downstream_request_ids.append(scope["state"]["request_id"])
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"x-existing-header", b"existing-value")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"ok",
                "more_body": False,
            }
        )

    async def receive() -> Message:
        return {
            "type": "http.request",
            "body": b"",
            "more_body": False,
        }

    async def send(message: Message) -> None:
        messages.append(message)

    middleware = RequestIdMiddleware(downstream)
    _run(middleware(_scope(request_id), receive, send))

    return MiddlewareExecution(
        downstream_request_id=downstream_request_ids[0],
        messages=messages,
    )


@pytest.fixture(autouse=True)
def deterministic_generated_request_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace random UUID generation with one valid deterministic value."""

    monkeypatch.setattr(
        middleware_module.uuid,
        "uuid4",
        lambda: UUID(GENERATED_REQUEST_ID),
    )


def test_request_id_middleware_preserves_valid_request_id() -> None:
    """Preserve a client correlation id that satisfies the safe format."""

    execution = _execute_middleware("client-request_123:attempt-2")

    assert execution.downstream_request_id == "client-request_123:attempt-2"
    assert execution.response_headers[REQUEST_ID_HEADER] == (
        "client-request_123:attempt-2"
    )


def test_request_id_middleware_generates_missing_request_id() -> None:
    """Generate a correlation id when the request has no header."""

    execution = _execute_middleware()

    assert execution.downstream_request_id == GENERATED_REQUEST_ID
    assert execution.response_headers[REQUEST_ID_HEADER] == (
        GENERATED_REQUEST_ID
    )


@pytest.mark.parametrize(
    "invalid_request_id",
    ["contains spaces", "@invalid", "-starts-with-symbol", ""],
)
def test_request_id_middleware_replaces_invalid_request_id(
    invalid_request_id: str,
) -> None:
    """Replace malformed client identifiers instead of propagating them."""

    execution = _execute_middleware(invalid_request_id)

    assert execution.downstream_request_id == GENERATED_REQUEST_ID
    assert execution.response_headers[REQUEST_ID_HEADER] == (
        GENERATED_REQUEST_ID
    )


def test_request_id_is_available_in_request_state() -> None:
    """Expose the resolved id to downstream logs and exception handlers."""

    execution = _execute_middleware("request-visible-in-state")

    assert execution.downstream_request_id == "request-visible-in-state"


def test_request_id_is_returned_in_response_header() -> None:
    """Add the same resolved identifier to the response start message."""

    execution = _execute_middleware("response-correlation-id")

    assert execution.response_headers[REQUEST_ID_HEADER] == (
        "response-correlation-id"
    )
    assert execution.response_headers["x-existing-header"] == "existing-value"


@pytest.mark.parametrize(
    "request_id",
    [
        "request\ninjected-header",
        "request\rvalue",
        "request\tvalue",
        "request\x00value",
    ],
)
def test_request_id_rejects_control_characters(request_id: str) -> None:
    """Prevent control characters from reaching logs or response headers."""

    execution = _execute_middleware(request_id)

    assert execution.downstream_request_id == GENERATED_REQUEST_ID
    assert execution.response_headers[REQUEST_ID_HEADER] == (
        GENERATED_REQUEST_ID
    )


def test_request_id_rejects_oversized_values() -> None:
    """Replace identifiers longer than the 128-character contract."""

    execution = _execute_middleware("a" * 129)

    assert execution.downstream_request_id == GENERATED_REQUEST_ID
    assert execution.response_headers[REQUEST_ID_HEADER] == (
        GENERATED_REQUEST_ID
    )


def test_install_request_id_middleware_registers_middleware() -> None:
    """Register the request-id middleware through the public installer."""

    application = FastAPI()

    install_request_id_middleware(application)

    assert len(application.user_middleware) == 1
    assert application.user_middleware[0].cls is RequestIdMiddleware
