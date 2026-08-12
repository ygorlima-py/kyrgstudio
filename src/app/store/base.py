"""Persistence contracts for application-level stores.

The store layer owns structured product data such as jobs, users, billing
customers, subscriptions, and webhook events. It does not store binary files,
execute workflows, enqueue jobs, or manage request transactions.

Concrete implementations are expected to receive an active database session
from the application boundary. Commit and rollback remain the responsibility of
the caller so multiple store operations can be composed in one transaction.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from datetime import datetime
from app.store.models import EmailVerificationToken
from app.store.models import PasswordResetToken

@dataclass(frozen=True, slots=True)
class JobListPage:
    """One bounded page of jobs returned by a store query.

    ``has_more`` is calculated by the persistence implementation without
    loading the user's complete job history into memory.
    """

    items: tuple[Any, ...]
    has_more: bool


class JobStoreBase(ABC):
    """Contract for persisted pipeline job state.

    A job represents one user-requested processing run. Implementations must
    protect lifecycle transitions so workers cannot move jobs out of order or
    finalize the same job concurrently.
    """

    @abstractmethod
    async def create_job(self, payload: dict[str, Any]) -> Any:
        """Create a new pending job from normalized pipeline input.

        Args:
            payload: Job creation data. Expected keys include ``user_id``,
                ``pipeline_type``, optional ``run_id``, and ``input_json``.

        Returns:
            The created job record, or an existing idempotent job when the
            implementation supports ``run_id`` reuse.
        """

        ...

    @abstractmethod
    async def mark_uploaded(self, job_id: int, payload: dict[str, Any]) -> Any:
        """Attach input file references and move a job to uploaded.

        Args:
            job_id: Internal job identifier.
            payload: Storage reference payload. Expected keys include
                ``storage_backend``, ``input_file_key``, and ``input_file_uri``.

        Returns:
            The updated job record.
        """

        ...

    @abstractmethod
    async def mark_running(self, job_id: int, step: str) -> Any:
        """Move an uploaded job to running.

        Args:
            job_id: Internal job identifier.
            step: Current worker step to expose for progress and debugging.

        Returns:
            The updated job record.
        """

        ...

    @abstractmethod
    async def mark_step_completed(
        self,
        job_id: int,
        step: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        """Record progress for a completed worker step.

        Args:
            job_id: Internal job identifier.
            step: Completed step name.
            payload: Optional structured metadata about the completed step.

        Returns:
            The updated job record.
        """

        ...

    @abstractmethod
    async def mark_completed(self, job_id: int, output: dict[str, Any]) -> Any:
        """Persist final output and move a running job to completed.

        Args:
            job_id: Internal job identifier.
            output: JSON-serializable final result, including token usage and
                execution time when available.

        Returns:
            The updated job record.
        """

        ...

    @abstractmethod
    async def mark_failed(self, job_id: int, error: dict[str, Any]) -> Any:
        """Persist a controlled failure payload and move the job to failed.

        Args:
            job_id: Internal job identifier.
            error: JSON-serializable error payload with stable code, step, and
                details for product/API consumers.

        Returns:
            The updated job record.
        """

        ...

    @abstractmethod
    async def get_job(self, job_id: int) -> Any:
        """Return a job by id, or ``None`` when it does not exist."""

        ...

    @abstractmethod
    async def get_job_by_run_id(self, run_id: str) -> Any:
        """Return a job by idempotency key, or ``None`` when absent."""

        ...

    @abstractmethod
    async def list_user_jobs(
        self,
        user_id: int,
        *,
        job_id: int | None = None,
        status: str | None = None,
        pipeline_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> JobListPage:
        """Return a filtered page of jobs owned by one user.

        Args:
            user_id: Owner user id.
            job_id: Optional exact internal job identifier.
            status: Optional lifecycle status filter.
            pipeline_type: Optional pipeline type filter.
            limit: Maximum number of jobs to return.
            offset: Number of jobs to skip.

        Returns:
            Jobs in stable newest-first order and whether another page exists.
        """

        ...
        

class UserStoreBase(ABC):
    """Contract for user persistence.

    This interface is intentionally small. Authentication flows can create and
    resolve users without coupling API code to SQLAlchemy models or database
    statements.
    """

    @abstractmethod
    async def create_user(self, payload: dict[str, Any]) -> Any:
        """Create a user from validated authentication/profile data."""

        ...

    @abstractmethod
    async def get_user(self, user_id: int) -> Any:
        """Return a user by internal id, or ``None`` when absent."""

        ...

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Any:
        """Return a user by normalized email, or ``None`` when absent."""

        ...

    @abstractmethod
    async def get_user_by_google_sub(self, google_sub: str) -> Any:
        """Return a user by Google subject id, or ``None`` when absent."""

        ...

    @abstractmethod
    async def mark_email_verified(self, user_id: int) -> Any:
        """Mark a user's email address as verified."""

        ...
        

class AuthSessionStoreBase(ABC):
    """Contract for persisted refresh-token sessions.

    Implementations store token digests only. Authentication policy, token
    generation, expiry decisions, and transaction ownership remain outside
    this persistence contract.
    """

    @abstractmethod
    async def create_session(self, payload: dict[str, Any]) -> Any:
        """Create a refresh session from normalized digest metadata."""

        ...

    @abstractmethod
    async def get_session(self, session_id: int) -> Any:
        """Return a refresh session by internal id, or ``None`` when absent."""

        ...

    @abstractmethod
    async def get_session_by_token_hash(
        self,
        token_hash: str,
        *,
        lock_for_update: bool = False,
    ) -> Any:
        """Return a session by token digest, optionally locking its row."""

        ...

    @abstractmethod
    async def rotate_session(
        self,
        session_id: int,
        replacement: dict[str, Any],
    ) -> Any:
        """Revoke one session and create its replacement atomically."""

        ...

    @abstractmethod
    async def revoke_session(self, session_id: int) -> Any:
        """Revoke one refresh session idempotently."""

        ...

    @abstractmethod
    async def revoke_user_sessions(self, user_id: int) -> int:
        """Revoke every active refresh session owned by one user."""

        ...

    @abstractmethod
    async def revoke_family(self, family_id: str) -> int:
        """Revoke every active session in one refresh-token family."""

        ...


class BillingStoreBase(ABC):
    """Contract for billing customer, subscription, and webhook persistence.

    The billing store keeps Stripe state synchronized with local users. It does
    not call Stripe APIs directly; webhook handlers or billing services pass
    already-validated Stripe identifiers and payloads.
    """

    @abstractmethod
    async def set_stripe_customer(
        self,
        user_id: int,
        stripe_customer_id: str,
    ) -> Any:
        """Create or update the Stripe customer linked to a user."""

        ...

    @abstractmethod
    async def upsert_subscription(self, payload: dict[str, Any]) -> Any:
        """Create or update a Stripe subscription snapshot."""

        ...

    @abstractmethod
    async def record_billing_event(self, payload: dict[str, Any]) -> Any:
        """Persist a Stripe webhook event idempotently."""

        ...

    @abstractmethod
    async def get_subscription_by_user_id(self, user_id: int) -> Any:
        """Return the active subscription for a user, or ``None`` when absent."""

        ...

class EmailVerificationStoreBase(ABC):
    """Persistence contract for one-time email verification tokens."""

    @abstractmethod
    async def create_token(
        self,
        *,
        user_id: int,
        email: str,
        token_hash: str,
        expires_at: datetime,
    ) -> EmailVerificationToken:
        ...

    @abstractmethod
    async def get_token_by_hash(
        self,
        token_hash: str,
    ) -> EmailVerificationToken | None:
        ...

    @abstractmethod
    async def mark_token_used(
        self,
        token_id: int,
    ) -> EmailVerificationToken:
        ...

    @abstractmethod
    async def revoke_pending_tokens_for_user(
        self,
        user_id: int,
    ) -> int:
        ...

class PasswordResetStoreBase(ABC):
    """Persistence contract for single-use password-reset tokens."""

    @abstractmethod
    async def create_token(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        """Persist a password-reset token hash for one user."""

        ...

    @abstractmethod
    async def get_token_by_hash(
        self,
        *,
        token_hash: str,
    ) -> PasswordResetToken | None:
        """Return a password-reset token by hash, when it exists."""

        ...

    @abstractmethod
    async def consume_token(
        self,
        *,
        token_hash: str,
        consumed_at: datetime,
    ) -> PasswordResetToken:
        """Atomically consume a valid, unused password-reset token."""

        ...

    @abstractmethod
    async def revoke_pending_tokens_for_user(
        self,
        *,
        user_id: int,
        revoked_at: datetime,
    ) -> int:
        """Invalidate every unused password-reset token for one user."""

        ...

    @abstractmethod
    async def delete_expired_tokens(
        self,
        *,
        before: datetime,
    ) -> int:
        """Delete tokens that expired on or before the supplied timestamp."""

        ...
