"""Password-reset use cases independent from HTTP and FastAPI.

The service creates opaque, single-use reset links and coordinates secure
password replacement. Raw tokens and plain passwords are never persisted or
included in logs, exceptions, or returned records.
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from app.auth.passwords import PasswordHasher
from app.auth.transactional_store import AuthStore
from app.email.senders import EmailSender
from app.errors import InvalidInputError, StoreError


DEFAULT_PASSWORD_RESET_TOKEN_TTL_SECONDS = 30 * 60
PASSWORD_RESET_TOKEN_BYTES = 32
PASSWORD_RESET_PATH = "/reset-password"


@dataclass(frozen=True, slots=True, kw_only=True)
class PasswordResetConfig:
    """Validated configuration required to issue password-reset links."""

    public_web_url: str
    token_ttl_seconds: int = DEFAULT_PASSWORD_RESET_TOKEN_TTL_SECONDS

    def __post_init__(self) -> None:
        normalized_public_web_url = self.public_web_url.strip().rstrip("/")

        if not normalized_public_web_url:
            raise ValueError("public_web_url is required.")

        if (
            isinstance(self.token_ttl_seconds, bool)
            or not isinstance(self.token_ttl_seconds, int)
            or self.token_ttl_seconds <= 0
        ):
            raise ValueError("token_ttl_seconds must be a positive integer.")

        object.__setattr__(
            self,
            "public_web_url",
            normalized_public_web_url,
        )


class PasswordResetService:
    """Issue password-reset links and securely replace local passwords."""

    __slots__ = (
        "_clock",
        "_token_generator",
        "auth_store",
        "config",
        "email_sender",
        "password_hasher",
    )

    def __init__(
        self,
        *,
        auth_store: AuthStore,
        password_hasher: PasswordHasher,
        email_sender: EmailSender,
        config: PasswordResetConfig,
        clock: Callable[[], datetime] | None = None,
        token_generator: Callable[[], str] | None = None,
    ) -> None:
        """Create the service from application-owned dependencies."""

        self.auth_store = auth_store
        self.password_hasher = password_hasher
        self.email_sender = email_sender
        self.config = config
        self._clock = clock if clock is not None else _utc_now
        self._token_generator = (
            token_generator
            if token_generator is not None
            else _generate_raw_token
        )

    async def request_password_reset(self, email: str) -> None:
        """Send a reset link without revealing whether an account exists.

        Missing, disabled, and non-password accounts deliberately produce the
        same successful return as an eligible account. API clients can
        therefore display one neutral response for every request.
        """

        normalized_email = _normalize_email(email)
        user = await self.auth_store.get_user_by_email(normalized_email)

        if (
            user is None
            or user.disabled
            or user.auth_provider != "password"
            or user.password_hash is None
        ):
            return

        requested_at = _utc_datetime(
            self._clock(),
            field_name="clock",
        )
        raw_token = _required_generated_token(self._token_generator())
        token_hash = _hash_token(raw_token)
        expires_at = requested_at + timedelta(
            seconds=self.config.token_ttl_seconds
        )

        await self.auth_store.create_password_reset_token(
            user_id=user.user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            requested_at=requested_at,
        )

        reset_url = _build_password_reset_url(
            public_web_url=self.config.public_web_url,
            raw_token=raw_token,
        )
        expiration_minutes = max(
            1,
            self.config.token_ttl_seconds // 60,
        )

        self.email_sender.send_template_html(
            subject="Reset your Kyrg Studio password",
            to=user.email,
            text_content=_password_reset_email_text(
                reset_url,
                expiration_minutes=expiration_minutes,
            ),
            html_path=_password_reset_template_path(),
            template_values={
                "reset_url": reset_url,
                "expiration_minutes": str(expiration_minutes),
            },
        )

    async def reset_password(
        self,
        *,
        raw_token: str,
        new_password: str,
    ) -> None:
        """Consume one token and replace the password atomically.

        Argon2id hashing runs before the database transaction begins. The
        transactional store then consumes the token, saves the resulting hash,
        and revokes all existing refresh sessions as one indivisible write.
        """

        token_hash = _hash_token(_required_token(raw_token))
        password_hash = _hash_new_password(
            self.password_hasher,
            new_password,
        )
        consumed_at = _utc_datetime(
            self._clock(),
            field_name="clock",
        )

        try:
            await self.auth_store.reset_password_with_token(
                token_hash=token_hash,
                password_hash=password_hash,
                consumed_at=consumed_at,
            )
        except StoreError as error:
            if error.details.get("reason") != "unavailable":
                raise

            raise InvalidInputError(
                technical_message="Password-reset token could not be accepted.",
                details={"field": "token"},
            ) from error


def _generate_raw_token() -> str:
    """Generate a cryptographically secure URL-safe opaque token."""

    return secrets.token_urlsafe(PASSWORD_RESET_TOKEN_BYTES)


def _hash_token(raw_token: str) -> str:
    """Return the deterministic SHA-256 digest used for database lookup."""

    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _build_password_reset_url(
    *,
    public_web_url: str,
    raw_token: str,
) -> str:
    """Build a frontend URL without exposing the token to access logs.

    URL fragments are handled by the browser and are not sent to Nginx or the
    application server. The frontend later submits the token in the reset
    request body.
    """

    fragment = urlencode({"token": raw_token})
    return f"{public_web_url}{PASSWORD_RESET_PATH}#{fragment}"


def _required_token(raw_token: object) -> str:
    if not isinstance(raw_token, str) or raw_token.strip() == "":
        raise InvalidInputError(
            technical_message="Password-reset token is required.",
            details={"field": "token"},
        )

    return raw_token.strip()


def _required_generated_token(raw_token: object) -> str:
    if not isinstance(raw_token, str) or raw_token.strip() == "":
        raise ValueError("token_generator must return a non-empty string.")

    return raw_token.strip()


def _normalize_email(email: object) -> str:
    if not isinstance(email, str):
        raise InvalidInputError(
            technical_message="A valid email is required.",
            details={"field": "email"},
        )

    normalized_email = email.strip().lower()

    if (
        not normalized_email
        or "@" not in normalized_email
        or len(normalized_email) > 320
    ):
        raise InvalidInputError(
            technical_message="A valid email is required.",
            details={"field": "email"},
        )

    return normalized_email


def _hash_new_password(
    password_hasher: PasswordHasher,
    new_password: str,
) -> str:
    try:
        return password_hasher.hash(new_password)
    except (TypeError, ValueError) as error:
        raise InvalidInputError(
            technical_message="New password is invalid.",
            details={"field": "new_password"},
        ) from error


def _utc_datetime(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must return a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone data.")

    return value.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _password_reset_template_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "email"
        / "templates"
        / "password-reset.en.html"
    )


def _password_reset_email_text(
    reset_url: str,
    *,
    expiration_minutes: int,
) -> str:
    return (
        "Use this link to reset your Kyrg Studio password:\n\n"
        f"{reset_url}\n\n"
        f"This link expires in {expiration_minutes} minutes and can only be "
        "used once. If you did not request a password reset, ignore this "
        "email."
    )


__all__ = [
    "PasswordResetConfig",
    "PasswordResetService",
]
