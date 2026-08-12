"""Unit tests for password-reset token issuance and consumption."""

import asyncio
import hashlib
from collections.abc import Coroutine
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest

from app.auth.password_reset import (
    PasswordResetConfig,
    PasswordResetService,
)
from app.auth.passwords import PasswordHasher
from app.auth.transactional_store import AuthStore, AuthUserRecord
from app.email.senders import EmailSender
from app.errors import InvalidInputError, StoreError


ResultT = TypeVar("ResultT")
NOW = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
RAW_TOKEN = "opaque-password-reset-token"
TOKEN_HASH = hashlib.sha256(RAW_TOKEN.encode("utf-8")).hexdigest()


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _user(**overrides: object) -> AuthUserRecord:
    values: dict[str, object] = {
        "user_id": 7,
        "email": "user@example.com",
        "password_hash": "existing-password-hash",
        "name": "Ada",
        "avatar_url": None,
        "auth_provider": "password",
        "google_subject": None,
        "email_verified_at": NOW,
        "disabled_at": None,
    }
    values.update(overrides)
    return AuthUserRecord(**values)  # type: ignore[arg-type]


class FakeAuthStore:
    def __init__(self) -> None:
        self.user: AuthUserRecord | None = _user()
        self.calls: list[tuple[str, object]] = []
        self.reset_error: StoreError | None = None

    async def get_user_by_email(
        self,
        email: str,
    ) -> AuthUserRecord | None:
        self.calls.append(("get_user_by_email", email))
        return self.user

    async def create_password_reset_token(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
        requested_at: datetime,
    ) -> None:
        self.calls.append(
            (
                "create_password_reset_token",
                {
                    "user_id": user_id,
                    "token_hash": token_hash,
                    "expires_at": expires_at,
                    "requested_at": requested_at,
                },
            )
        )

    async def reset_password_with_token(
        self,
        *,
        token_hash: str,
        password_hash: str,
        consumed_at: datetime,
    ) -> None:
        self.calls.append(
            (
                "reset_password_with_token",
                {
                    "token_hash": token_hash,
                    "password_hash": password_hash,
                    "consumed_at": consumed_at,
                },
            )
        )

        if self.reset_error is not None:
            raise self.reset_error


class FakePasswordHasher:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.error: Exception | None = None

    def hash(self, password: str) -> str:
        self.calls.append(password)

        if self.error is not None:
            raise self.error

        return "new-argon2-password-hash"


class FakeEmailSender:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    def send_template_html(
        self,
        *,
        subject: str,
        to: str,
        text_content: str,
        html_path: Path,
        template_values: dict[str, str],
    ) -> None:
        self.messages.append(
            {
                "subject": subject,
                "to": to,
                "text_content": text_content,
                "html_path": html_path,
                "template_values": template_values,
            }
        )


class ServiceHarness:
    def __init__(self) -> None:
        self.store = FakeAuthStore()
        self.password_hasher = FakePasswordHasher()
        self.email_sender = FakeEmailSender()
        self.service = PasswordResetService(
            auth_store=cast(AuthStore, self.store),
            password_hasher=cast(PasswordHasher, self.password_hasher),
            email_sender=cast(EmailSender, self.email_sender),
            config=PasswordResetConfig(
                public_web_url="https://app.example.com/",
                token_ttl_seconds=30 * 60,
            ),
            clock=lambda: NOW,
            token_generator=lambda: RAW_TOKEN,
        )


@pytest.mark.parametrize("token_ttl_seconds", [0, -1, True, 1.5])
def test_config_rejects_invalid_token_ttl(token_ttl_seconds: object) -> None:
    """Reject reset links without a positive integer lifetime."""

    with pytest.raises(ValueError):
        PasswordResetConfig(
            public_web_url="https://app.example.com",
            token_ttl_seconds=token_ttl_seconds,  # type: ignore[arg-type]
        )


def test_request_password_reset_normalizes_email_and_sends_link() -> None:
    """Persist only the digest and send the raw token only in the email URL."""

    harness = ServiceHarness()

    _run(harness.service.request_password_reset(" USER@Example.com "))

    assert harness.store.calls[0] == (
        "get_user_by_email",
        "user@example.com",
    )
    operation, payload = harness.store.calls[1]
    assert operation == "create_password_reset_token"
    assert isinstance(payload, dict)
    assert payload == {
        "user_id": 7,
        "token_hash": TOKEN_HASH,
        "expires_at": NOW + timedelta(minutes=30),
        "requested_at": NOW,
    }
    assert RAW_TOKEN not in repr(payload)

    assert len(harness.email_sender.messages) == 1
    message = harness.email_sender.messages[0]
    assert message["to"] == "user@example.com"
    assert message["html_path"] == Path(
        "src/app/email/templates/password-reset.en.html"
    ).resolve()
    assert message["template_values"] == {
        "reset_url": (
            "https://app.example.com/reset-password"
            f"#token={RAW_TOKEN}"
        ),
        "expiration_minutes": "30",
    }


@pytest.mark.parametrize(
    "user",
    [
        None,
        _user(disabled_at=NOW),
        _user(auth_provider="google", password_hash=None),
    ],
)
def test_request_password_reset_hides_ineligible_accounts(
    user: AuthUserRecord | None,
) -> None:
    """Return identically without issuing a token for ineligible accounts."""

    harness = ServiceHarness()
    harness.store.user = user

    assert _run(
        harness.service.request_password_reset("user@example.com")
    ) is None
    assert harness.store.calls == [
        ("get_user_by_email", "user@example.com")
    ]
    assert harness.email_sender.messages == []


def test_reset_password_hashes_password_before_transactional_update() -> None:
    """Pass only token and password hashes to the transactional store."""

    harness = ServiceHarness()

    _run(
        harness.service.reset_password(
            raw_token=RAW_TOKEN,
            new_password="new-secret-password",
        )
    )

    assert harness.password_hasher.calls == ["new-secret-password"]
    assert harness.store.calls == [
        (
            "reset_password_with_token",
            {
                "token_hash": TOKEN_HASH,
                "password_hash": "new-argon2-password-hash",
                "consumed_at": NOW,
            },
        )
    ]
    assert RAW_TOKEN not in repr(harness.store.calls)
    assert "new-secret-password" not in repr(harness.store.calls)


def test_reset_password_maps_unavailable_token_to_public_input_error() -> None:
    """Hide whether a reset token was missing, expired, or already used."""

    harness = ServiceHarness()
    harness.store.reset_error = StoreError(
        technical_message="Reset token unavailable.",
        details={"reason": "unavailable"},
    )

    with pytest.raises(InvalidInputError) as error_info:
        _run(
            harness.service.reset_password(
                raw_token=RAW_TOKEN,
                new_password="new-secret-password",
            )
        )

    assert error_info.value.details == {"field": "token"}


def test_reset_password_does_not_hide_infrastructure_errors() -> None:
    """Allow genuine database failures to remain controlled store errors."""

    harness = ServiceHarness()
    harness.store.reset_error = StoreError(
        technical_message="Database unavailable.",
        details={"operation": "consume_password_reset_token"},
    )

    with pytest.raises(StoreError):
        _run(
            harness.service.reset_password(
                raw_token=RAW_TOKEN,
                new_password="new-secret-password",
            )
        )


def test_reset_password_rejects_invalid_new_password() -> None:
    """Expose only the new-password field when Argon2 validation rejects it."""

    harness = ServiceHarness()
    harness.password_hasher.error = ValueError("too short")

    with pytest.raises(InvalidInputError) as error_info:
        _run(
            harness.service.reset_password(
                raw_token=RAW_TOKEN,
                new_password="short",
            )
        )

    assert error_info.value.details == {"field": "new_password"}
    assert harness.store.calls == []
