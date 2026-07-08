"""Unit tests for app billing store behavior.

These tests validate billing payload rules, idempotency semantics, and
subscription/customer boundaries without opening a real database connection.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, cast

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import app.store.billing as billing
from app.errors import BillingStoreError
from app.store.billing import SQLAlchemyBillingStore
from app.store.models import BillingCustomer, BillingEvent, Subscription


def _run_async(awaitable: Any) -> Any:
    """Run an async store method from a synchronous unit test."""

    return asyncio.run(awaitable)


def _store(session: object | None = None) -> SQLAlchemyBillingStore:
    """Build a billing store around a typed fake session."""

    return SQLAlchemyBillingStore(cast(AsyncSession, session or object()))


def _integrity_error() -> IntegrityError:
    """Return a SQLAlchemy integrity error for savepoint conflict paths."""

    return IntegrityError("statement", "params", Exception("duplicate"))


def _subscription_payload(**overrides: Any) -> dict[str, Any]:
    """Build a valid subscription payload with optional overrides."""

    payload: dict[str, Any] = {
        "user_id": 1,
        "stripe_customer_id": "cus_123",
        "stripe_subscription_id": "sub_123",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def _event_payload(**overrides: Any) -> dict[str, Any]:
    """Build a valid Stripe event payload with optional overrides."""

    payload: dict[str, Any] = {
        "stripe_event_id": "evt_123",
        "event_type": "customer.subscription.updated",
        "payload_json": {"id": "evt_123"},
    }
    payload.update(overrides)
    return payload


class _InsertSession:
    """Session fake for insert paths with optional flush failure."""

    def __init__(self, flush_error: Exception | None = None) -> None:
        self.added: list[object] = []
        self.flush_error = flush_error
        self.flush_called = False

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flush_called = True

        if self.flush_error is not None:
            raise self.flush_error


class _ScalarOneOrNoneResult:
    """SQLAlchemy result fake for scalar lookup queries."""

    def __init__(self, value: object | None = None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class _ExecuteCaptureSession:
    """Session fake that captures the statement passed to execute."""

    def __init__(self) -> None:
        self.statement: object | None = None

    async def execute(self, statement: object) -> _ScalarOneOrNoneResult:
        self.statement = statement
        return _ScalarOneOrNoneResult()


class _ExecuteRaisesSession:
    """Session fake that raises a SQLAlchemy infrastructure error."""

    async def execute(self, statement: object) -> _ScalarOneOrNoneResult:
        raise SQLAlchemyError("database failed")


class _BillingStoreSpy(SQLAlchemyBillingStore):
    """Store spy for controlled billing branch coverage."""

    def __init__(self, session: object | None = None) -> None:
        super().__init__(cast(AsyncSession, session or object()))
        self.customer_by_user: BillingCustomer | None = None
        self.customer_by_stripe_id: BillingCustomer | None = None
        self.subscription_by_subscription_id: Subscription | None = None
        self.subscription_by_customer_id: Subscription | None = None
        self.billing_event_by_event_id: BillingEvent | None = None
        self.customer_by_user_calls: list[int] = []
        self.customer_by_stripe_id_calls: list[str] = []
        self.subscription_by_subscription_id_calls: list[str] = []
        self.subscription_by_customer_id_calls: list[str] = []
        self.billing_event_by_event_id_calls: list[str] = []
        self.updated_customers: list[dict[str, Any]] = []
        self.updated_subscriptions: list[dict[str, Any]] = []

    async def get_billing_customer_by_user_id(
        self,
        user_id: int,
    ) -> BillingCustomer | None:
        self.customer_by_user_calls.append(user_id)
        return self.customer_by_user

    async def get_billing_customer_by_stripe_customer_id(
        self,
        stripe_customer_id: str,
    ) -> BillingCustomer | None:
        self.customer_by_stripe_id_calls.append(stripe_customer_id)
        return self.customer_by_stripe_id

    async def get_subscription_by_stripe_subscription_id(
        self,
        stripe_subscription_id: str,
    ) -> Subscription | None:
        self.subscription_by_subscription_id_calls.append(stripe_subscription_id)
        return self.subscription_by_subscription_id

    async def get_subscription_by_stripe_customer_id(
        self,
        stripe_customer_id: str,
    ) -> Subscription | None:
        self.subscription_by_customer_id_calls.append(stripe_customer_id)
        return self.subscription_by_customer_id

    async def get_billing_event_by_stripe_event_id(
        self,
        stripe_event_id: str,
    ) -> BillingEvent | None:
        self.billing_event_by_event_id_calls.append(stripe_event_id)
        return self.billing_event_by_event_id

    async def _update_billing_customer(
        self,
        *,
        billing_customer_id: int,
        operation: str,
        values: Mapping[str, Any],
    ) -> BillingCustomer:
        self.updated_customers.append(
            {
                "billing_customer_id": billing_customer_id,
                "operation": operation,
                "values": dict(values),
            }
        )
        return BillingCustomer(
            id=billing_customer_id,
            user_id=self.customer_by_user.user_id if self.customer_by_user else 1,
            stripe_customer_id=str(values["stripe_customer_id"]),
        )

    async def _update_subscription(
        self,
        *,
        subscription_id: int,
        operation: str,
        values: Mapping[str, Any],
    ) -> Subscription:
        self.updated_subscriptions.append(
            {
                "subscription_id": subscription_id,
                "operation": operation,
                "values": dict(values),
            }
        )
        return Subscription(id=subscription_id, **dict(values))


@asynccontextmanager
async def _fake_savepoint(session: object) -> AsyncIterator[object]:
    """Savepoint fake that lets insert paths run without SQLAlchemy."""

    yield session


def _compile_query(statement: object) -> str:
    """Compile a SQLAlchemy statement with literals for assertion."""

    compiled = getattr(statement, "compile")
    return str(compiled(compile_kwargs={"literal_binds": True}))


def test_set_stripe_customer_requires_positive_user_id() -> None:
    """set_stripe_customer should reject invalid user identifiers."""

    store = _store()

    for invalid_user_id in (0, -1, True, 1.5, "abc"):
        with pytest.raises(BillingStoreError) as error:
            _run_async(store.set_stripe_customer(invalid_user_id, "cus_123")) #type: ignore

        assert error.value.details["operation"] == "set_stripe_customer"
        assert error.value.details["field"] == "user_id"


def test_set_stripe_customer_requires_customer_prefix() -> None:
    """Stripe customer ids should use the cus_ prefix."""

    store = _store()

    with pytest.raises(BillingStoreError) as error:
        _run_async(store.set_stripe_customer(1, "customer_123"))

    assert error.value.details == {
        "operation": "set_stripe_customer",
        "field": "stripe_customer_id",
        "expected_prefix": "cus_",
    }


def test_set_stripe_customer_updates_existing_customer_for_user() -> None:
    """Existing customer links should be updated for the same user."""

    store = _BillingStoreSpy()
    store.customer_by_user = BillingCustomer(
        id=10,
        user_id=1,
        stripe_customer_id="cus_old",
    )

    customer = cast(
        BillingCustomer,
        _run_async(store.set_stripe_customer(1, "cus_new")),
    )

    assert customer.id == 10
    assert customer.stripe_customer_id == "cus_new"
    assert store.customer_by_user_calls == [1]
    assert store.updated_customers == [
        {
            "billing_customer_id": 10,
            "operation": "set_stripe_customer",
            "values": {"stripe_customer_id": "cus_new"},
        }
    ]


def test_set_stripe_customer_rejects_customer_linked_to_other_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Stripe customer already linked elsewhere should not be reassigned."""

    monkeypatch.setattr(billing, "async_savepoint_scope", _fake_savepoint)
    store = _BillingStoreSpy(_InsertSession(flush_error=_integrity_error()))
    store.customer_by_stripe_id = BillingCustomer(
        id=99,
        user_id=55,
        stripe_customer_id="cus_shared",
    )

    with pytest.raises(BillingStoreError) as error:
        _run_async(store.set_stripe_customer(1, "cus_shared"))

    assert error.value.details == {
        "operation": "set_stripe_customer",
        "user_id": 1,
        "stripe_customer_id": "cus_shared",
        "existing_user_id": 55,
    }


def test_upsert_subscription_requires_customer_prefix() -> None:
    """Subscription payloads should require Stripe customer ids."""

    store = _store()

    with pytest.raises(BillingStoreError) as error:
        _run_async(
            store.upsert_subscription(
                _subscription_payload(stripe_customer_id="customer_123")
            )
        )

    assert error.value.details == {
        "operation": "upsert_subscription",
        "field": "stripe_customer_id",
        "expected_prefix": "cus_",
    }


def test_upsert_subscription_requires_subscription_prefix() -> None:
    """Subscription payloads should require Stripe subscription ids."""

    store = _store()

    with pytest.raises(BillingStoreError) as error:
        _run_async(
            store.upsert_subscription(
                _subscription_payload(stripe_subscription_id="subscription_123")
            )
        )

    assert error.value.details == {
        "operation": "upsert_subscription",
        "field": "stripe_subscription_id",
        "expected_prefix": "sub_",
    }


def test_upsert_subscription_uses_subscription_id_as_identity() -> None:
    """Existing subscriptions should be resolved by subscription id."""

    store = _BillingStoreSpy()
    store.subscription_by_subscription_id = Subscription(
        id=20,
        user_id=1,
        stripe_customer_id="cus_existing",
        stripe_subscription_id="sub_123",
        status="active",
    )

    subscription = cast(
        Subscription,
        _run_async(
            store.upsert_subscription(
                _subscription_payload(
                    stripe_customer_id="cus_new",
                    stripe_subscription_id="sub_123",
                    status="trialing",
                )
            )
        ),
    )

    assert subscription.id == 20
    assert subscription.stripe_customer_id == "cus_new"
    assert subscription.status == "trialing"
    assert store.subscription_by_subscription_id_calls == ["sub_123"]
    assert store.subscription_by_customer_id_calls == []


def test_upsert_subscription_rejects_customer_conflict_with_different_subscription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A customer conflict should not overwrite a different subscription."""

    monkeypatch.setattr(billing, "async_savepoint_scope", _fake_savepoint)
    store = _BillingStoreSpy(_InsertSession(flush_error=_integrity_error()))
    store.subscription_by_customer_id = Subscription(
        id=30,
        user_id=1,
        stripe_customer_id="cus_123",
        stripe_subscription_id="sub_existing",
        status="active",
    )

    with pytest.raises(BillingStoreError) as error:
        _run_async(
            store.upsert_subscription(
                _subscription_payload(
                    stripe_customer_id="cus_123",
                    stripe_subscription_id="sub_incoming",
                )
            )
        )

    assert error.value.details == {
        "operation": "upsert_subscription",
        "stripe_customer_id": "cus_123",
        "existing_stripe_subscription_id": "sub_existing",
        "incoming_stripe_subscription_id": "sub_incoming",
    }


def test_record_billing_event_requires_event_prefix() -> None:
    """Stripe event ids should use the evt_ prefix."""

    store = _store()

    with pytest.raises(BillingStoreError) as error:
        _run_async(
            store.record_billing_event(
                _event_payload(stripe_event_id="event_123")
            )
        )

    assert error.value.details == {
        "operation": "record_billing_event",
        "field": "stripe_event_id",
        "expected_prefix": "evt_",
    }


def test_record_billing_event_returns_should_process_true_for_new_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A newly inserted event should be processed exactly once."""

    monkeypatch.setattr(billing, "async_savepoint_scope", _fake_savepoint)
    session = _InsertSession()
    store = _store(session)

    result = _run_async(store.record_billing_event(_event_payload()))

    assert isinstance(result, billing.BillingEventRecordResult)
    assert result.created is True
    assert result.should_process is True
    assert result.event.stripe_event_id == "evt_123"
    assert session.added == [result.event]
    assert session.flush_called is True


def test_record_billing_event_returns_should_process_false_for_duplicate_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A duplicate Stripe event should return the existing event without work."""

    monkeypatch.setattr(billing, "async_savepoint_scope", _fake_savepoint)
    existing_event = BillingEvent(
        id=40,
        stripe_event_id="evt_123",
        event_type="customer.subscription.updated",
        payload_json={"id": "evt_123"},
    )
    store = _BillingStoreSpy(_InsertSession(flush_error=_integrity_error()))
    store.billing_event_by_event_id = existing_event

    result = _run_async(store.record_billing_event(_event_payload()))

    assert isinstance(result, billing.BillingEventRecordResult)
    assert result.event is existing_event
    assert result.created is False
    assert result.should_process is False
    assert store.billing_event_by_event_id_calls == ["evt_123"]


def test_mark_billing_event_processed_requires_event_prefix() -> None:
    """mark_billing_event_processed should validate Stripe event ids."""

    store = _store()

    with pytest.raises(BillingStoreError) as error:
        _run_async(store.mark_billing_event_processed("event_123"))

    assert error.value.details == {
        "operation": "mark_billing_event_processed",
        "field": "stripe_event_id",
        "expected_prefix": "evt_",
    }


def test_mark_subscription_canceled_requires_subscription_prefix() -> None:
    """mark_subscription_canceled should validate Stripe subscription ids."""

    store = _store()

    with pytest.raises(BillingStoreError) as error:
        _run_async(store.mark_subscription_canceled("subscription_123"))

    assert error.value.details == {
        "operation": "mark_subscription_canceled",
        "field": "stripe_subscription_id",
        "expected_prefix": "sub_",
    }


def test_get_active_subscription_uses_active_and_trialing_statuses() -> None:
    """Active subscription lookup should include active and trialing only."""

    session = _ExecuteCaptureSession()
    store = _store(session)

    result = _run_async(store.get_active_subscription(1))

    assert result is None
    assert billing.ACTIVE_SUBSCRIPTION_STATUSES == frozenset(
        {"active", "trialing"}
    )
    assert session.statement is not None
    compiled_query = _compile_query(session.statement)
    assert "'active'" in compiled_query
    assert "'trialing'" in compiled_query


def test_sqlalchemy_errors_are_wrapped_as_billing_store_error() -> None:
    """SQLAlchemy infrastructure errors should become controlled store errors."""

    store = _store(_ExecuteRaisesSession())

    with pytest.raises(BillingStoreError) as error:
        _run_async(store.get_subscription_by_user_id(1))

    assert error.value.details == {
        "operation": "get_subscription_by_user_id",
        "user_id": 1,
        "error_type": "SQLAlchemyError",
    }
