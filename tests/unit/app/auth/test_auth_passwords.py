"""Unit tests for Argon2id password hashing and verification."""

from collections.abc import Iterator

import pytest

from app.auth.passwords import Argon2PasswordHasher


@pytest.fixture
def password_hasher() -> Iterator[Argon2PasswordHasher]:
    """Provide a real Argon2id hasher with test-safe resource parameters."""

    yield _build_hasher()


def _build_hasher(
    *,
    min_password_length: int = 4,
    max_password_length: int = 32,
    time_cost: int = 1,
    memory_cost: int = 8,
    parallelism: int = 1,
    hash_length: int = 16,
    salt_length: int = 8,
) -> Argon2PasswordHasher:
    return Argon2PasswordHasher(
        min_password_length=min_password_length,
        max_password_length=max_password_length,
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
        hash_length=hash_length,
        salt_length=salt_length,
    )


def test_hash_produces_argon2id_encoded_hash(
    password_hasher: Argon2PasswordHasher,
) -> None:
    """Generate a salted hash using the required Argon2id variant."""

    password_hash = password_hasher.hash("safe-password")

    assert password_hash.startswith("$argon2id$")
    assert "safe-password" not in password_hash


@pytest.mark.parametrize("password", ["abcd", "x" * 32])
def test_hash_accepts_password_at_configured_boundaries(
    password_hasher: Argon2PasswordHasher,
    password: str,
) -> None:
    """Accept registration passwords exactly at both configured limits."""

    password_hash = password_hasher.hash(password)

    assert password_hasher.verify(password, password_hash) is True


@pytest.mark.parametrize("password", ["abc", "x" * 33])
def test_hash_rejects_password_outside_configured_boundaries(
    password_hasher: Argon2PasswordHasher,
    password: str,
) -> None:
    """Reject registration passwords outside configured length limits."""

    with pytest.raises(ValueError):
        password_hasher.hash(password)


def test_verify_accepts_correct_password(
    password_hasher: Argon2PasswordHasher,
) -> None:
    """Accept a candidate matching its stored encoded hash."""

    password_hash = password_hasher.hash("safe-password")

    assert password_hasher.verify("safe-password", password_hash) is True


def test_verify_rejects_incorrect_password(
    password_hasher: Argon2PasswordHasher,
) -> None:
    """Reject an incorrect candidate without raising an authentication detail."""

    password_hash = password_hasher.hash("safe-password")

    assert password_hasher.verify("wrong-password", password_hash) is False


@pytest.mark.parametrize(
    "password_hash",
    [None, "", "   ", "not-an-argon2-hash", "x" * 513],
)
def test_verify_rejects_missing_or_malformed_hash(
    password_hasher: Argon2PasswordHasher,
    password_hash: str | None,
) -> None:
    """Treat absent and malformed database values as failed verification."""

    assert password_hasher.verify("safe-password", password_hash) is False


@pytest.mark.parametrize("password_hash", [None, "malformed-hash"])
def test_verify_uses_dummy_hash_for_missing_or_malformed_hash(
    monkeypatch: pytest.MonkeyPatch,
    password_hasher: Argon2PasswordHasher,
    password_hash: str | None,
) -> None:
    """Consume dummy verification work when no usable account hash exists."""

    dummy_calls: list[None] = []

    def record_dummy_verification(self: Argon2PasswordHasher) -> None:
        dummy_calls.append(None)

    monkeypatch.setattr(
        Argon2PasswordHasher,
        "_consume_dummy_verification",
        record_dummy_verification,
    )

    verified = password_hasher.verify("safe-password", password_hash)

    assert verified is False
    assert dummy_calls == [None]


def test_verify_accepts_legacy_password_below_registration_minimum() -> None:
    """Allow existing short credentials to authenticate during migration."""

    legacy_hasher = _build_hasher(min_password_length=1)
    current_hasher = _build_hasher(min_password_length=12)
    legacy_hash = legacy_hasher.hash("short")

    assert current_hasher.verify("short", legacy_hash) is True


def test_verify_and_update_returns_replacement_hash_when_parameters_change() -> None:
    """Rehash a valid password when its stored Argon2 parameters are outdated."""

    legacy_hasher = _build_hasher(hash_length=12)
    current_hasher = _build_hasher(hash_length=16)
    legacy_hash = legacy_hasher.hash("safe-password")

    verified, updated_hash = current_hasher.verify_and_update(
        "safe-password",
        legacy_hash,
    )

    assert verified is True
    assert updated_hash is not None
    assert updated_hash != legacy_hash
    assert current_hasher.verify("safe-password", updated_hash) is True


def test_verify_and_update_returns_none_when_hash_is_current(
    password_hasher: Argon2PasswordHasher,
) -> None:
    """Avoid unnecessary writes when the stored hash uses current parameters."""

    current_hash = password_hasher.hash("safe-password")

    verified, updated_hash = password_hasher.verify_and_update(
        "safe-password",
        current_hash,
    )

    assert verified is True
    assert updated_hash is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"min_password_length": 0},
        {"max_password_length": 0},
        {"min_password_length": 10, "max_password_length": 9},
        {"time_cost": 0},
        {"memory_cost": 0},
        {"parallelism": 0},
        {"hash_length": 0},
        {"salt_length": 0},
    ],
)
def test_constructor_rejects_invalid_argon2_configuration(
    overrides: dict[str, int],
) -> None:
    """Fail startup when password or Argon2 parameters are unsafe or invalid."""

    configuration = {
        "min_password_length": 4,
        "max_password_length": 32,
        "time_cost": 1,
        "memory_cost": 8,
        "parallelism": 1,
        "hash_length": 16,
        "salt_length": 8,
    }
    configuration.update(overrides)

    with pytest.raises(ValueError):
        Argon2PasswordHasher(**configuration)
