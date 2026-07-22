"""Integration tests for authentication use cases and SQL persistence."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.auth.principal import GoogleIdentity
from app.errors import (
    AccountLinkRequiredError,
    InvalidInputError,
    RefreshTokenInvalidError,
    UserStoreError,
)
from app.store.models import AuthSession, User
from auth_helpers import AuthIntegrationContext, run_async


PASSWORD = "correct-horse-battery-staple"


def test_password_registration_persists_user_and_hashed_refresh_session(
    auth_context: AuthIntegrationContext,
) -> None:
    """Persist a password user while storing only credential hashes."""

    async def scenario() -> None:
        result = await auth_context.service.register_with_password(
            email="  USER@Example.COM ",
            password=PASSWORD,
            name="  Ada Lovelace  ",
        )

        async with auth_context.session_factory() as session:
            user = (
                await session.execute(
                    select(User).where(User.email == "user@example.com")
                )
            ).scalar_one()
            auth_session = (
                await session.execute(
                    select(AuthSession).where(AuthSession.user_id == user.id)
                )
            ).scalar_one()

        assert result.principal.user_id == user.id
        assert result.principal.email == "user@example.com"
        assert result.principal.name == "Ada Lovelace"
        assert user.password_hash is not None
        assert PASSWORD not in user.password_hash
        assert auth_context.password_hasher.verify(
            PASSWORD,
            user.password_hash,
        )
        assert auth_session.token_hash == auth_context.refresh_tokens.digest(
            result.tokens.refresh_token
        )
        assert auth_session.token_hash != result.tokens.refresh_token

    run_async(scenario())


def test_duplicate_registration_returns_controlled_input_error(
    auth_context: AuthIntegrationContext,
) -> None:
    """Translate a real unique-email violation without duplicating users."""

    async def scenario() -> None:
        await auth_context.service.register_with_password(
            email="user@example.com",
            password=PASSWORD,
        )

        with pytest.raises(InvalidInputError) as captured:
            await auth_context.service.register_with_password(
                email="USER@example.com",
                password=PASSWORD,
            )

        async with auth_context.session_factory() as session:
            user_count = await session.scalar(select(func.count(User.id)))

        assert captured.value.details["code"] == "already_exists"
        assert user_count == 1

    run_async(scenario())


def test_password_login_creates_session_and_authenticates_access_token(
    auth_context: AuthIntegrationContext,
) -> None:
    """Connect password verification, session persistence, and JWT identity."""

    async def scenario() -> None:
        registered = await auth_context.service.register_with_password(
            email="user@example.com",
            password=PASSWORD,
            name="Ada",
        )
        logged_in = await auth_context.service.login_with_password(
            email="USER@EXAMPLE.COM",
            password=PASSWORD,
        )
        principal = await auth_context.service.authenticate_access_token(
            logged_in.tokens.access_token
        )

        async with auth_context.session_factory() as session:
            session_count = await session.scalar(
                select(func.count(AuthSession.id)).where(
                    AuthSession.user_id == registered.principal.user_id
                )
            )

        assert principal == logged_in.principal
        assert principal.user_id == registered.principal.user_id
        assert session_count == 2

    run_async(scenario())


def test_refresh_rotation_persists_replacement_and_detects_reuse(
    auth_context: AuthIntegrationContext,
) -> None:
    """Rotate refresh state and revoke the family when an old token is reused."""

    async def scenario() -> None:
        registered = await auth_context.service.register_with_password(
            email="user@example.com",
            password=PASSWORD,
        )
        original_refresh_token = registered.tokens.refresh_token
        refreshed = await auth_context.service.refresh(original_refresh_token)

        assert refreshed.tokens.refresh_token != original_refresh_token

        with pytest.raises(RefreshTokenInvalidError):
            await auth_context.service.refresh(original_refresh_token)

        async with auth_context.session_factory() as session:
            persisted_sessions = list(
                (
                    await session.scalars(
                        select(AuthSession).order_by(AuthSession.id)
                    )
                ).all()
            )

        assert len(persisted_sessions) == 2
        assert persisted_sessions[0].replaced_by_session_id == (
            persisted_sessions[1].id
        )
        assert all(
            auth_session.revoked_at is not None
            for auth_session in persisted_sessions
        )

    run_async(scenario())


def test_logout_revokes_persisted_refresh_family(
    auth_context: AuthIntegrationContext,
) -> None:
    """Persist logout revocation for the refresh session family."""

    async def scenario() -> None:
        registered = await auth_context.service.register_with_password(
            email="user@example.com",
            password=PASSWORD,
        )

        await auth_context.service.logout(registered.tokens.refresh_token)

        async with auth_context.session_factory() as session:
            auth_session = (
                await session.execute(select(AuthSession))
            ).scalar_one()

        assert auth_session.revoked_at is not None

    run_async(scenario())


def test_google_login_persists_verified_identity_and_session(
    auth_context: AuthIntegrationContext,
) -> None:
    """Persist only identity data returned by the verified Google boundary."""

    async def scenario() -> None:
        result = await auth_context.service.login_with_google(
            "verified-google-id-token"
        )

        async with auth_context.session_factory() as session:
            user = (
                await session.execute(
                    select(User).where(
                        User.google_sub == "google-integration-subject"
                    )
                )
            ).scalar_one()
            session_count = await session.scalar(
                select(func.count(AuthSession.id)).where(
                    AuthSession.user_id == user.id
                )
            )

        assert auth_context.google_verifier.received_tokens == [
            "verified-google-id-token"
        ]
        assert result.principal.user_id == user.id
        assert user.auth_provider == "google"
        assert user.password_hash is None
        assert user.email_verified_at is not None
        assert session_count == 1

    run_async(scenario())


def test_google_login_does_not_implicitly_link_matching_password_email(
    auth_context: AuthIntegrationContext,
) -> None:
    """Require explicit account linking when Google matches a local email."""

    async def scenario() -> None:
        await auth_context.service.register_with_password(
            email="google@example.com",
            password=PASSWORD,
        )
        auth_context.google_verifier.identity = GoogleIdentity(
            subject="new-google-subject",
            email="google@example.com",
            email_verified=True,
        )

        with pytest.raises(AccountLinkRequiredError):
            await auth_context.service.login_with_google(
                "verified-google-id-token"
            )

        async with auth_context.session_factory() as session:
            users = list((await session.scalars(select(User))).all())

        assert len(users) == 1
        assert users[0].auth_provider == "password"
        assert users[0].google_sub is None

    run_async(scenario())


def test_user_creation_rolls_back_when_initial_session_insert_fails(
    auth_context: AuthIntegrationContext,
) -> None:
    """Rollback the user row when its atomic session insert violates uniqueness."""

    async def scenario() -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await auth_context.store.create_password_user_with_session(
            email="first@example.com",
            password_hash="first-password-hash",
            name=None,
            token_hash="shared-token-hash",
            family_id="first-family",
            session_expires_at=expires_at,
        )

        with pytest.raises(UserStoreError):
            await auth_context.store.create_password_user_with_session(
                email="rolled-back@example.com",
                password_hash="second-password-hash",
                name=None,
                token_hash="shared-token-hash",
                family_id="second-family",
                session_expires_at=expires_at,
            )

        persisted_user = await auth_context.store.get_user_by_email(
            "rolled-back@example.com"
        )
        async with auth_context.session_factory() as session:
            user_count = await session.scalar(select(func.count(User.id)))
            session_count = await session.scalar(
                select(func.count(AuthSession.id))
            )

        assert persisted_user is None
        assert user_count == 1
        assert session_count == 1

    run_async(scenario())
