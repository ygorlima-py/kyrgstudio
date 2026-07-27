"""Application lifecycle management for the HTTP API.

The API owns long-lived infrastructure required to submit jobs. It never owns
workflow execution: jobs are delegated to Celery and executed by a separate
worker process.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI

from app.auth.google import GoogleTokenVerifier
from app.auth.passwords import Argon2PasswordHasher
from app.auth.service import AuthService
from app.auth.tokens import AccessTokenService, RefreshTokenGenerator
from app.auth.transactional_store import AuthStore
from app.errors import AuthConfigurationError
from app.queue.base import QueueBase
from app.queue.celery import CeleryQueue, CeleryTask
from app.settings import AppSettings, load_settings
from app.storage.factory import create_storage
from app.store.database import (
    SessionFactory,
    create_async_engine_from_settings,
    create_async_session_factory,
    dispose_async_engine,
)


@asynccontextmanager
async def api_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and release API-scoped infrastructure.

    Sessions remain request-scoped and are created later from the stored
    ``SessionFactory``. No job is submitted and no workflow is executed while
    the API starts or stops.
    """

    settings = _resolve_application_settings(app)
    engine = create_async_engine_from_settings(settings)

    try:
        session_factory = create_async_session_factory(engine)
        storage = create_storage(settings)
        queue = _create_pipeline_queue()
        auth_service = _create_auth_service(
            settings=settings,
            session_factory=session_factory,
        )

        app.state.settings = settings
        app.state.session_factory = session_factory
        app.state.storage = storage
        app.state.queue = queue
        app.state.auth_service = auth_service

        yield
    finally:
        await dispose_async_engine(engine)


def _resolve_application_settings(app: FastAPI) -> AppSettings:
    """Reuse settings supplied by application composition when available.

    ``create_app`` is expected to resolve settings before the lifespan starts
    because application construction also needs them for CORS. The fallback
    keeps the standalone lifespan usable until that composition module is
    implemented, while still rejecting an invalid object already stored in
    application state.
    """

    configured_settings = getattr(app.state, "settings", None)

    if configured_settings is None:
        return load_settings()

    if not isinstance(configured_settings, AppSettings):
        raise AuthConfigurationError(
            technical_message=(
                "Application settings in API state have an invalid type."
            ),
        )

    return configured_settings


def _create_auth_service(
    *,
    settings: AppSettings,
    session_factory: SessionFactory,
) -> AuthService:
    """Compose the reusable authentication service for the API process.

    The store retains only the session factory, not an open database session.
    Password hashing, token codecs, and Google verification are initialized
    once and safely reused by all requests handled by this process.
    """

    try:
        jwt_signing_secret = settings.require_auth_jwt_secret()
    except ValueError as error:
        raise AuthConfigurationError(
            technical_message="Authentication JWT configuration is invalid.",
        ) from error

    auth_store = AuthStore(session_factory)
    password_hasher = Argon2PasswordHasher()
    access_token_service = AccessTokenService(
        secret=jwt_signing_secret,
        issuer=settings.auth_issuer,
        audience=settings.auth_audience,
        algorithm=settings.auth_jwt_algorithm,
        ttl_seconds=settings.auth_access_token_ttl_seconds,
        allowed_clock_skew_seconds=(
            settings.auth_allowed_clock_skew_seconds
        ),
    )
    refresh_token_generator = RefreshTokenGenerator()
    google_token_verifier = (
        GoogleTokenVerifier(
            client_ids=settings.google_client_ids,
            allowed_clock_skew_seconds=(
                settings.auth_allowed_clock_skew_seconds
            ),
        )
        if settings.google_client_ids
        else None
    )

    return AuthService(
        auth_store=auth_store,
        password_hasher=password_hasher,
        access_token_service=access_token_service,
        refresh_token_generator=refresh_token_generator,
        google_token_verifier=google_token_verifier,
        refresh_token_ttl_seconds=(
            settings.auth_refresh_token_ttl_seconds
        ),
    )


def _create_pipeline_queue() -> QueueBase:
    """Create the queue adapter without executing workflow code."""

    # Importing the Celery task registers its message entry point only. The
    # task body and all workflows run later in a Celery worker process.
    from app.worker.tasks import run_pipeline_job

    return CeleryQueue(cast(CeleryTask, run_pipeline_job))


__all__ = ["api_lifespan"]
