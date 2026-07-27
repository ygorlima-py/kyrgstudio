"""Unit tests for framework-independent authentication use cases."""

import asyncio
from collections.abc import Coroutine
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar, cast

import pytest

from app.auth.google import GoogleTokenVerifier
from app.auth.passwords import PasswordHasher
from app.auth.principal import AccessTokenClaims, GoogleIdentity
from app.auth.service import AuthService
from app.auth.tokens import AccessTokenService, RefreshTokenGenerator
from app.auth.transactional_store import (
    AuthSessionRecord,
    AuthStore,
    AuthUserRecord,
    AuthUserSessionRecord,
    RefreshSessionRotationRecord,
)
from app.errors import (
    AccountDisabledError,
    AccountLinkRequiredError,
    AuthConfigurationError,
    EmailVerificationRequiredError,
    InvalidCredentialsError,
    InvalidInputError,
    InvalidTokenError,
    RefreshTokenInvalidError,
    UserStoreError,
)


ResultT = TypeVar("ResultT")
NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _user(**overrides: object) -> AuthUserRecord:
    values: dict[str, object] = {
        "user_id": 7,
        "email": "user@example.com",
        "password_hash": "stored-password-hash",
        "name": "Ada",
        "avatar_url": None,
        "auth_provider": "password",
        "google_subject": None,
        "email_verified_at": NOW,
        "disabled_at": None,
    }
    values.update(overrides)
    return AuthUserRecord(**values)  # type: ignore[arg-type]


def _session(**overrides: object) -> AuthSessionRecord:
    values: dict[str, object] = {
        "session_id": 13,
        "user_id": 7,
        "token_hash": "refresh-digest",
        "family_id": "family-id",
        "expires_at": NOW + timedelta(hours=1),
        "last_used_at": NOW,
        "revoked_at": None,
        "replaced_by_session_id": None,
        "created_at": NOW,
    }
    values.update(overrides)
    return AuthSessionRecord(**values)  # type: ignore[arg-type]


class FakePasswordHasher:
    """Record password operations while returning configured outcomes."""

    def __init__(self) -> None:
        self.hash_result = "generated-password-hash"
        self.verify_result: tuple[bool, str | None] = (True, None)
        self.hash_calls: list[str] = []
        self.verify_calls: list[tuple[str, str | None]] = []

    def hash(self, password: str) -> str:
        self.hash_calls.append(password)
        return self.hash_result

    def verify(self, password: str, password_hash: str | None) -> bool:
        verified, _ = self.verify_and_update(password, password_hash)
        return verified

    def verify_and_update(
        self,
        password: str,
        password_hash: str | None,
    ) -> tuple[bool, str | None]:
        self.verify_calls.append((password, password_hash))
        return self.verify_result


class FakeAccessTokenService:
    """Issue deterministic access tokens and trusted claims for tests."""

    ttl_seconds = 900

    def __init__(self) -> None:
        self.issue_calls: list[object] = []
        self.decode_calls: list[str] = []
        self.decoded_user_id = 7

    def issue(self, principal: object) -> str:
        self.issue_calls.append(principal)
        return f"access-token-{len(self.issue_calls)}"

    def decode(self, token: str) -> AccessTokenClaims:
        self.decode_calls.append(token)
        return AccessTokenClaims(
            user_id=self.decoded_user_id,
            token_id="access-jti",
            issued_at=NOW,
            not_before=NOW,
            expires_at=NOW + timedelta(seconds=self.ttl_seconds),
        )


class FakeRefreshTokenGenerator:
    """Generate deterministic opaque values and record digest operations."""

    def __init__(self) -> None:
        self.generated_tokens = ["refresh-token"]
        self.generate_calls = 0
        self.digest_calls: list[str] = []
        self.invalid_tokens: set[str] = set()

    def generate(self) -> str:
        token_index = min(
            self.generate_calls,
            len(self.generated_tokens) - 1,
        )
        token = self.generated_tokens[token_index]
        self.generate_calls += 1
        return token

    def digest(self, token: str) -> str:
        self.digest_calls.append(token)
        if token in self.invalid_tokens:
            raise ValueError("invalid refresh token")
        return f"digest:{token}"


class FakeGoogleTokenVerifier:
    """Return an already-verified identity without external communication."""

    def __init__(self) -> None:
        self.identity = GoogleIdentity(
            subject="google-subject",
            email="google@example.com",
            email_verified=True,
            name="Google User",
            avatar_url="https://example.com/avatar.png",
        )
        self.calls: list[str] = []

    def verify(self, id_token: str) -> GoogleIdentity:
        self.calls.append(id_token)
        return self.identity


class FakeAuthStore:
    """In-memory call recorder matching the AuthStore service boundary."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.user_by_email: AuthUserRecord | None = _user()
        self.user_by_google_subject: AuthUserRecord | None = None
        self.user_by_id: AuthUserRecord | None = _user()
        self.session_by_hash: AuthSessionRecord | None = _session()
        self.created_user = _user()
        self.created_google_user = _user(
            email="google@example.com",
            password_hash=None,
            auth_provider="google",
            google_subject="google-subject",
        )
        self.updated_user = _user(password_hash="updated-password-hash")
        self.create_password_error: UserStoreError | None = None
        self.create_google_error: UserStoreError | None = None
        self.rotation = RefreshSessionRotationRecord(status="not_found")

    async def get_user(self, user_id: int) -> AuthUserRecord | None:
        self.calls.append(("get_user", user_id))
        return self.user_by_id

    async def get_user_by_email(self, email: str) -> AuthUserRecord | None:
        self.calls.append(("get_user_by_email", email))
        return self.user_by_email

    async def get_user_by_google_sub(
        self,
        subject: str,
    ) -> AuthUserRecord | None:
        self.calls.append(("get_user_by_google_sub", subject))
        return self.user_by_google_subject

    async def create_password_user_with_session(
        self,
        **payload: object,
    ) -> AuthUserSessionRecord:
        self.calls.append(("create_password_user_with_session", payload))
        if self.create_password_error is not None:
            raise self.create_password_error
        return AuthUserSessionRecord(
            user=self.created_user,
            session=_session(),
        )

    async def create_google_user_with_session(
        self,
        **payload: object,
    ) -> AuthUserSessionRecord:
        self.calls.append(("create_google_user_with_session", payload))
        if self.create_google_error is not None:
            raise self.create_google_error
        return AuthUserSessionRecord(
            user=self.created_google_user,
            session=_session(),
        )

    async def create_session(self, **payload: object) -> AuthSessionRecord:
        self.calls.append(("create_session", payload))
        return _session(
            user_id=payload["user_id"],
            token_hash=payload["token_hash"],
            family_id=payload["family_id"],
            expires_at=payload["expires_at"],
        )

    async def update_password_hash(
        self,
        user_id: int,
        password_hash: str,
    ) -> AuthUserRecord:
        self.calls.append(
            ("update_password_hash", (user_id, password_hash))
        )
        return self.updated_user

    async def rotate_session_by_token_hash(
        self,
        **payload: object,
    ) -> RefreshSessionRotationRecord:
        self.calls.append(("rotate_session_by_token_hash", payload))
        return self.rotation

    async def get_session_by_token_hash(
        self,
        token_hash: str,
    ) -> AuthSessionRecord | None:
        self.calls.append(("get_session_by_token_hash", token_hash))
        return self.session_by_hash

    async def revoke_session_family(self, family_id: str) -> int:
        self.calls.append(("revoke_session_family", family_id))
        return 1

    async def revoke_user_sessions(self, user_id: int) -> int:
        self.calls.append(("revoke_user_sessions", user_id))
        return 1


class ServiceHarness:
    """Collect all fake dependencies used by one AuthService instance."""

    def __init__(
        self,
        *,
        refresh_ttl_seconds: int = 3600,
        google_authentication_enabled: bool = True,
    ) -> None:
        self.store = FakeAuthStore()
        self.password_hasher = FakePasswordHasher()
        self.access_tokens = FakeAccessTokenService()
        self.refresh_tokens = FakeRefreshTokenGenerator()
        self.google = FakeGoogleTokenVerifier()
        self.service = AuthService(
            auth_store=cast(AuthStore, self.store),
            password_hasher=cast(PasswordHasher, self.password_hasher),
            access_token_service=cast(
                AccessTokenService,
                self.access_tokens,
            ),
            refresh_token_generator=cast(
                RefreshTokenGenerator,
                self.refresh_tokens,
            ),
            google_token_verifier=(
                cast(GoogleTokenVerifier, self.google)
                if google_authentication_enabled
                else None
            ),
            refresh_token_ttl_seconds=refresh_ttl_seconds,
            clock=lambda: NOW,
        )


@pytest.fixture
def harness() -> ServiceHarness:
    return ServiceHarness()


@pytest.mark.parametrize("refresh_ttl_seconds", [0, 900, 899])
def test_constructor_rejects_refresh_ttl_not_greater_than_access_ttl(
    refresh_ttl_seconds: int,
) -> None:
    """Require refresh credentials to outlive access credentials."""

    with pytest.raises(AuthConfigurationError):
        ServiceHarness(refresh_ttl_seconds=refresh_ttl_seconds)


def test_register_normalizes_input_and_never_sends_plain_password_to_store(
    harness: ServiceHarness,
) -> None:
    """Normalize registration data and persist only the generated hash."""

    _run(
        harness.service.register_with_password(
            email="  USER@Example.COM ",
            password="plain-password",
            name="  Ada  ",
        )
    )

    _, payload = harness.store.calls[0]
    assert isinstance(payload, dict)
    assert payload["email"] == "user@example.com"
    assert payload["name"] == "Ada"
    assert payload["password_hash"] == "generated-password-hash"
    assert "plain-password" not in payload.values()
    assert harness.password_hasher.hash_calls == ["plain-password"]


def test_register_creates_user_and_refresh_session_atomically(
    harness: ServiceHarness,
) -> None:
    """Delegate user and initial-session creation to one atomic store call."""

    result = _run(
        harness.service.register_with_password(
            email="user@example.com",
            password="plain-password",
        )
    )

    operation, payload = harness.store.calls[0]
    assert operation == "create_password_user_with_session"
    assert isinstance(payload, dict)
    assert payload["token_hash"] == "digest:refresh-token"
    assert payload["session_expires_at"] == NOW + timedelta(hours=1)
    assert result.principal.user_id == harness.store.created_user.user_id
    assert result.tokens.refresh_token == "refresh-token"


def test_register_maps_email_conflict_to_invalid_input(
    harness: ServiceHarness,
) -> None:
    """Translate a unique-email conflict into a stable registration error."""

    harness.store.create_password_error = UserStoreError(
        technical_message="email conflict",
        details={"conflict_fields": ["email"]},
    )

    with pytest.raises(InvalidInputError) as captured:
        _run(
            harness.service.register_with_password(
                email="user@example.com",
                password="plain-password",
            )
        )

    assert captured.value.details == {
        "field": "email",
        "code": "already_exists",
    }


def test_password_login_uses_dummy_verification_for_unknown_email(
    harness: ServiceHarness,
) -> None:
    """Always invoke password verification when the account does not exist."""

    harness.store.user_by_email = None
    harness.password_hasher.verify_result = (False, None)

    with pytest.raises(InvalidCredentialsError):
        _run(
            harness.service.login_with_password(
                email="missing@example.com",
                password="candidate",
            )
        )

    assert harness.password_hasher.verify_calls == [("candidate", None)]


def test_password_login_returns_same_error_for_unknown_email_and_wrong_password() -> None:
    """Prevent callers from distinguishing unknown accounts from bad passwords."""

    unknown = ServiceHarness()
    unknown.store.user_by_email = None
    unknown.password_hasher.verify_result = (False, None)
    incorrect = ServiceHarness()
    incorrect.password_hasher.verify_result = (False, None)

    with pytest.raises(InvalidCredentialsError) as unknown_error:
        _run(
            unknown.service.login_with_password(
                email="missing@example.com",
                password="candidate",
            )
        )
    with pytest.raises(InvalidCredentialsError) as incorrect_error:
        _run(
            incorrect.service.login_with_password(
                email="user@example.com",
                password="candidate",
            )
        )

    assert unknown_error.value.code == incorrect_error.value.code
    assert (
        unknown_error.value.technical_message
        == incorrect_error.value.technical_message
    )


def test_password_login_updates_outdated_password_hash(
    harness: ServiceHarness,
) -> None:
    """Persist an upgraded hash after successful legacy verification."""

    harness.password_hasher.verify_result = (True, "updated-password-hash")

    result = _run(
        harness.service.login_with_password(
            email="user@example.com",
            password="candidate",
        )
    )

    assert (
        "update_password_hash",
        (7, "updated-password-hash"),
    ) in harness.store.calls
    assert result.principal.user_id == 7


def test_password_login_rejects_disabled_account(
    harness: ServiceHarness,
) -> None:
    """Reject valid credentials belonging to a disabled account."""

    harness.store.user_by_email = _user(disabled_at=NOW)

    with pytest.raises(AccountDisabledError):
        _run(
            harness.service.login_with_password(
                email="user@example.com",
                password="candidate",
            )
        )

    assert not any(call[0] == "create_session" for call in harness.store.calls)


def test_password_login_creates_refresh_session(
    harness: ServiceHarness,
) -> None:
    """Create a durable refresh session after password authentication."""

    result = _run(
        harness.service.login_with_password(
            email="user@example.com",
            password="candidate",
        )
    )

    create_call = next(
        call for call in harness.store.calls if call[0] == "create_session"
    )
    payload = create_call[1]
    assert isinstance(payload, dict)
    assert payload["user_id"] == 7
    assert payload["token_hash"] == "digest:refresh-token"
    assert result.tokens.refresh_token == "refresh-token"


def test_google_login_uses_verified_google_identity(
    harness: ServiceHarness,
) -> None:
    """Use only the identity returned by the configured Google verifier."""

    harness.store.user_by_email = None

    result = _run(harness.service.login_with_google("signed-id-token"))

    assert harness.google.calls == ["signed-id-token"]
    _, payload = harness.store.calls[-1]
    assert isinstance(payload, dict)
    assert payload["google_subject"] == "google-subject"
    assert result.principal.email == "google@example.com"


def test_google_login_rejects_unconfigured_google_authentication() -> None:
    """Keep password authentication available when Google is not configured."""

    harness = ServiceHarness(google_authentication_enabled=False)

    with pytest.raises(
        AuthConfigurationError,
        match="Google authentication is not configured",
    ):
        _run(harness.service.login_with_google("signed-id-token"))

    assert harness.google.calls == []
    assert harness.store.calls == []


def test_google_login_reuses_account_found_by_google_subject(
    harness: ServiceHarness,
) -> None:
    """Create only a new session for an already-linked Google account."""

    harness.store.user_by_google_subject = _user(
        email="google@example.com",
        password_hash=None,
        auth_provider="google",
        google_subject="google-subject",
    )

    result = _run(harness.service.login_with_google("signed-id-token"))

    assert result.principal.auth_provider == "google"
    assert any(call[0] == "create_session" for call in harness.store.calls)
    assert not any(
        call[0] == "create_google_user_with_session"
        for call in harness.store.calls
    )


def test_google_login_creates_user_and_session_atomically(
    harness: ServiceHarness,
) -> None:
    """Create a new Google user and initial session through one store call."""

    harness.store.user_by_email = None

    _run(harness.service.login_with_google("signed-id-token"))

    operations = [call[0] for call in harness.store.calls]
    assert operations == [
        "get_user_by_google_sub",
        "get_user_by_email",
        "create_google_user_with_session",
    ]


def test_google_login_rejects_unverified_email(
    harness: ServiceHarness,
) -> None:
    """Require Google's verified-email claim before account access."""

    harness.google.identity = GoogleIdentity(
        subject="google-subject",
        email="google@example.com",
        email_verified=False,
    )

    with pytest.raises(EmailVerificationRequiredError):
        _run(harness.service.login_with_google("signed-id-token"))

    assert harness.store.calls == []


def test_google_login_requires_explicit_link_for_matching_local_email(
    harness: ServiceHarness,
) -> None:
    """Never link a Google identity by email coincidence alone."""

    harness.store.user_by_email = _user(email="google@example.com")

    with pytest.raises(AccountLinkRequiredError):
        _run(harness.service.login_with_google("signed-id-token"))

    assert not any(
        call[0] == "create_google_user_with_session"
        for call in harness.store.calls
    )


def test_google_login_rejects_disabled_account(
    harness: ServiceHarness,
) -> None:
    """Reject a verified Google identity linked to a disabled user."""

    harness.store.user_by_google_subject = _user(
        auth_provider="google",
        google_subject="google-subject",
        disabled_at=NOW,
    )

    with pytest.raises(AccountDisabledError):
        _run(harness.service.login_with_google("signed-id-token"))

    assert not any(call[0] == "create_session" for call in harness.store.calls)


def test_refresh_rotates_token_and_issues_new_token_pair(
    harness: ServiceHarness,
) -> None:
    """Rotate a valid refresh token and return newly issued credentials."""

    replacement_session = _session(
        session_id=14,
        token_hash="digest:refresh-token",
    )
    harness.store.rotation = RefreshSessionRotationRecord(
        status="rotated",
        user=_user(),
        current_session=_session(),
        replacement_session=replacement_session,
    )

    result = _run(harness.service.refresh("current-refresh-token"))

    operation, payload = harness.store.calls[0]
    assert operation == "rotate_session_by_token_hash"
    assert isinstance(payload, dict)
    assert payload["current_token_hash"] == "digest:current-refresh-token"
    assert payload["replacement_token_hash"] == "digest:refresh-token"
    assert result.tokens.refresh_token == "refresh-token"


@pytest.mark.parametrize(
    "status",
    ["not_found", "expired", "reused", "user_not_found"],
)
def test_refresh_rejects_non_rotated_session_statuses(
    harness: ServiceHarness,
    status: str,
) -> None:
    """Return one public refresh error for every failed rotation outcome."""

    harness.store.rotation = RefreshSessionRotationRecord(
        status=status,  # type: ignore[arg-type]
    )

    with pytest.raises(RefreshTokenInvalidError):
        _run(harness.service.refresh("current-refresh-token"))


def test_refresh_revokes_sessions_for_disabled_account(
    harness: ServiceHarness,
) -> None:
    """Revoke all sessions if the account is disabled during rotation."""

    harness.store.rotation = RefreshSessionRotationRecord(
        status="rotated",
        user=_user(disabled_at=NOW),
        current_session=_session(),
        replacement_session=_session(session_id=14),
    )

    with pytest.raises(AccountDisabledError):
        _run(harness.service.refresh("current-refresh-token"))

    assert ("revoke_user_sessions", 7) in harness.store.calls


def test_logout_revokes_refresh_session_family(
    harness: ServiceHarness,
) -> None:
    """Invalidate the entire refresh family on explicit logout."""

    _run(harness.service.logout("current-refresh-token"))

    assert harness.store.calls == [
        ("get_session_by_token_hash", "digest:current-refresh-token"),
        ("revoke_session_family", "family-id"),
    ]


@pytest.mark.parametrize("mode", ["unknown", "invalid"])
def test_logout_is_idempotent_for_unknown_or_invalid_token(
    mode: str,
) -> None:
    """Complete logout without revealing whether a refresh token existed."""

    harness = ServiceHarness()
    if mode == "unknown":
        harness.store.session_by_hash = None
    else:
        harness.refresh_tokens.invalid_tokens.add("invalid-token")

    _run(
        harness.service.logout(
            "invalid-token" if mode == "invalid" else "unknown-token"
        )
    )

    assert not any(
        call[0] == "revoke_session_family" for call in harness.store.calls
    )


def test_authenticate_access_token_returns_active_principal(
    harness: ServiceHarness,
) -> None:
    """Return a detached active principal for a valid access token."""

    principal = _run(
        harness.service.authenticate_access_token("valid-access-token")
    )

    assert principal.user_id == 7
    assert principal.email == "user@example.com"
    assert harness.access_tokens.decode_calls == ["valid-access-token"]
    assert harness.store.calls == [("get_user", 7)]


@pytest.mark.parametrize("user", [None, _user(disabled_at=NOW)])
def test_authenticate_access_token_rejects_missing_or_disabled_user(
    harness: ServiceHarness,
    user: AuthUserRecord | None,
) -> None:
    """Reject valid JWTs whose current account is absent or disabled."""

    harness.store.user_by_id = user
    expected_error = InvalidTokenError if user is None else AccountDisabledError

    with pytest.raises(expected_error):
        _run(harness.service.authenticate_access_token("valid-access-token"))
