"""Password hashing contracts and Argon2id implementation.

This module owns password hashing and verification only. It has no knowledge of
users, databases, HTTP requests, JWTs, or OAuth providers. Plain passwords and
encoded hashes are never logged or included in exceptions raised by this file.
"""

from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from typing import TypeGuard

from argon2.low_level import Type
from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError
from pwdlib.hashers.argon2 import Argon2Hasher


DEFAULT_MIN_PASSWORD_LENGTH = 12
DEFAULT_MAX_PASSWORD_LENGTH = 128
DEFAULT_ARGON2_TIME_COST = 3
DEFAULT_ARGON2_MEMORY_COST = 65_536
DEFAULT_ARGON2_PARALLELISM = 4
DEFAULT_ARGON2_HASH_LENGTH = 32
DEFAULT_ARGON2_SALT_LENGTH = 16
MAX_ENCODED_HASH_LENGTH = 512


class PasswordHasher(ABC):
    """Contract for password hashing and verification services."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Return a new encoded hash for a password accepted at registration."""

        ...

    @abstractmethod
    def verify(
        self,
        password: str,
        password_hash: str | None,
    ) -> bool:
        """Return whether a candidate matches, without exposing failure cause."""

        ...

    @abstractmethod
    def verify_and_update(
        self,
        password: str,
        password_hash: str | None,
    ) -> tuple[bool, str | None]:
        """Verify a password and return a replacement hash when required."""

        ...


class Argon2PasswordHasher(PasswordHasher):
    """Hash and verify passwords using explicitly configured Argon2id.

    Registration enforces both minimum and maximum password lengths. Login
    accepts legacy passwords below the current minimum so users can still
    authenticate and migrate their hash, but always enforces the maximum input
    length. Missing and malformed stored hashes are verified against an
    instance-local dummy hash to reduce account-enumeration timing differences.

    The class is intended to be created once during application startup and
    reused. Constructing it generates one dummy Argon2id hash and therefore has
    the expected cost of one password-hashing operation.
    """

    __slots__ = (
        "_dummy_hash",
        "_dummy_password",
        "_password_hash",
        "max_password_length",
        "min_password_length",
    )

    def __init__(
        self,
        *,
        min_password_length: int = DEFAULT_MIN_PASSWORD_LENGTH,
        max_password_length: int = DEFAULT_MAX_PASSWORD_LENGTH,
        time_cost: int = DEFAULT_ARGON2_TIME_COST,
        memory_cost: int = DEFAULT_ARGON2_MEMORY_COST,
        parallelism: int = DEFAULT_ARGON2_PARALLELISM,
        hash_length: int = DEFAULT_ARGON2_HASH_LENGTH,
        salt_length: int = DEFAULT_ARGON2_SALT_LENGTH,
    ) -> None:
        self.min_password_length = _positive_integer(
            min_password_length,
            field_name="min_password_length",
        )
        self.max_password_length = _positive_integer(
            max_password_length,
            field_name="max_password_length",
        )

        if self.max_password_length < self.min_password_length:
            raise ValueError(
                "max_password_length must be greater than or equal to "
                "min_password_length."
            )

        argon2_hasher = Argon2Hasher(
            time_cost=_positive_integer(time_cost, field_name="time_cost"),
            memory_cost=_positive_integer(
                memory_cost,
                field_name="memory_cost",
            ),
            parallelism=_positive_integer(
                parallelism,
                field_name="parallelism",
            ),
            hash_len=_positive_integer(
                hash_length,
                field_name="hash_length",
            ),
            salt_len=_positive_integer(
                salt_length,
                field_name="salt_length",
            ),
            type=Type.ID,
        )
        self._password_hash = PasswordHash((argon2_hasher,))

        # The random value is unrelated to any user and remains process-local.
        self._dummy_password = secrets.token_urlsafe(32)
        self._dummy_hash = self._password_hash.hash(self._dummy_password)

    def hash(self, password: str) -> str:
        """Return a salted Argon2id hash suitable for ``User.password_hash``.

        Password text is never trimmed or Unicode-normalized because those
        operations would silently change the user's credential.
        """

        validated_password = self._password_for_hashing(password)
        return self._password_hash.hash(validated_password)

    def verify(
        self,
        password: str,
        password_hash: str | None,
    ) -> bool:
        """Verify a candidate while hiding missing or malformed hash details."""

        candidate = self._password_for_verification(password)

        if candidate is None or not _is_encoded_hash_candidate(password_hash):
            self._consume_dummy_verification()
            return False

        try:
            return self._password_hash.verify(candidate, password_hash)
        except (PwdlibError, TypeError, ValueError):
            self._consume_dummy_verification()
            return False

    def verify_and_update(
        self,
        password: str,
        password_hash: str | None,
    ) -> tuple[bool, str | None]:
        """Verify and optionally rehash with the current Argon2id parameters.

        ``updated_hash`` is returned only when verification succeeds and
        ``pwdlib`` detects that the stored parameters are outdated.
        """

        candidate = self._password_for_verification(password)

        if candidate is None or not _is_encoded_hash_candidate(password_hash):
            self._consume_dummy_verification()
            return False, None

        try:
            verified, updated_hash = self._password_hash.verify_and_update(
                candidate,
                password_hash,
            )
        except (PwdlibError, TypeError, ValueError):
            self._consume_dummy_verification()
            return False, None

        if not verified:
            return False, None

        return True, updated_hash

    def _password_for_hashing(self, password: object) -> str:
        if not isinstance(password, str):
            raise TypeError("password must be a string.")

        password_length = len(password)

        if password_length < self.min_password_length:
            raise ValueError(
                "password is shorter than the configured minimum length."
            )

        if password_length > self.max_password_length:
            raise ValueError(
                "password exceeds the configured maximum length."
            )

        return password

    def _password_for_verification(self, password: object) -> str | None:
        if not isinstance(password, str):
            return None

        if not password or len(password) > self.max_password_length:
            return None

        return password

    def _consume_dummy_verification(self) -> None:
        """Perform one Argon2 verification unrelated to a real account."""

        self._password_hash.verify(
            self._dummy_password,
            self._dummy_hash,
        )


def _positive_integer(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")

    return value


def _is_encoded_hash_candidate(value: object) -> TypeGuard[str]:
    return (
        isinstance(value, str)
        and value == value.strip()
        and 0 < len(value) <= MAX_ENCODED_HASH_LENGTH
    )


__all__ = [
    "Argon2PasswordHasher",
    "PasswordHasher",
]
