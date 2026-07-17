"""Request-level middleware shared by all HTTP API routes."""

from __future__ import annotations

import re
import uuid

from fastapi import FastAPI
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


REQUEST_ID_HEADER = "X-Request-ID"

_REQUEST_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
)


class RequestIdMiddleware:
    """Attach one safe correlation identifier to each HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_headers = Headers(scope=scope)
        request_id = _resolve_request_id(
            request_headers.get(REQUEST_ID_HEADER)
        )
        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers[REQUEST_ID_HEADER] = request_id

            await send(message)

        await self.app(scope, receive, send_with_request_id)


def install_request_id_middleware(app: FastAPI) -> None:
    """Install request correlation before the application starts."""

    app.add_middleware(RequestIdMiddleware)


def _resolve_request_id(value: str | None) -> str:
    if value is not None:
        candidate = value.strip()

        if _REQUEST_ID_PATTERN.fullmatch(candidate):
            return candidate

    return uuid.uuid4().hex


__all__ = [
    "REQUEST_ID_HEADER",
    "RequestIdMiddleware",
    "install_request_id_middleware",
]
