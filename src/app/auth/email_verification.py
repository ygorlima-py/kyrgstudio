from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from app.email.senders import EmailSender
from app.auth.transactional_store import AuthStore, AuthUserRecord
from app.errors import InvalidInputError, InvalidTokenError

@dataclass(frozen=True)
class EmailVerificationConfig:
    """Configuration required to create email verification links."""
    
    public_web_url: str
    token_ttl_seconds: int = 24 * 60 * 60
    
class EmailVerificationService:
    """Create and consume one-time email verification links."""
    
    def __init__(
        self,
        *,
        auth_store: AuthStore,
        email_sender: EmailSender,
        config: EmailVerificationConfig,
    ) -> None:
        
        self.auth_store = auth_store
        self.email_sender = email_sender
        self.config = config
    
    async def send_verification_email(
        self,
        *,
        user_id: int,
        email: str,
    ) -> None:
        
        """Create a fresh verification token and send it to the user."""

        normalized_email = _normalize_email(email)
        raw_token = _generate_raw_token()
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(
            seconds=self.config.token_ttl_seconds
        )

        await self.auth_store.revoke_pending_email_verification_tokens_for_user(user_id)
        await self.auth_store.create_email_verification_token(
            user_id=user_id,
            email=normalized_email,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        
        verification_url = _build_verification_url(
            public_web_url=self.config.public_web_url,
            raw_token=raw_token,
        )

        self.email_sender.send_text(
            subject="Confirm your Kyrg Studio email",
            to=normalized_email,
            content=_verification_email_text(verification_url),
        )
    
    async def verify_email_token(self, raw_token: str) -> AuthUserRecord:
        """Validate a raw token from the email link and verify the user."""

        token_hash = _hash_token(_required_token(raw_token))
        verification_token = await self.auth_store.get_email_verification_token_by_hash(
            token_hash
        )
        
        if verification_token is None:
            raise InvalidTokenError(
                technical_message="Email verification token was not found.",
                details={"reason": "not_found"},
            )

        if verification_token.used_at is not None:
            raise InvalidTokenError(
                technical_message="Email verification token was already used.",
                details={"reason": "used"},
            )

        if verification_token.expires_at <= datetime.now(UTC):
            raise InvalidTokenError(
                technical_message="Email verification token expired.",
                details={"reason": "expired"},
            )

        await self.auth_store.mark_email_verification_token_used(
            verification_token.token_id
        )
        
        return await self.auth_store.mark_user_email_verified(
            verification_token.user_id
        )
    
def _generate_raw_token() -> str:
    """Generate a URL-safe token with enough entropy for email verification."""

    return secrets.token_urlsafe(32)


def _hash_token(raw_token: str) -> str:
    """Return a deterministic hash used for database lookup."""

    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

def _build_verification_url(
    *,
    public_web_url: str,
    raw_token: str,
) -> str:
    """Build the backend URL that consumes the raw verification token."""

    base_url = public_web_url.rstrip("/")
    query_string = urlencode({"token": raw_token})

    return f"{base_url}/v1/auth/verify-email?{query_string}"

def _required_token(raw_token: str) -> str:
    token = raw_token.strip()

    if not token:
        raise InvalidInputError(
            technical_message="Email verification token is required.",
            details={"field": "token"},
        )

    return token

def _normalize_email(email: str) -> str:
    normalized_email = email.strip().lower()

    if not normalized_email or "@" not in normalized_email:
        raise InvalidInputError(
            technical_message="A valid email is required.",
            details={"field": "email"},
        )

    return normalized_email

def _verification_email_text(verification_url: str) -> str:
    return (
        "Confirm your Kyrg Studio email by opening this link:\n\n"
        f"{verification_url}\n\n"
        "If you did not create an account, ignore this email."
    )
