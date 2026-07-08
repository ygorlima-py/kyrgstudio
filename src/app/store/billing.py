"""Billing persistence for the application store.

This module persists Stripe subscription state and webhook events. It does not
verify Stripe signatures, execute webhook business logic, or commit database
transactions. Callers must pass an active ``AsyncSession`` and control
commit/rollback outside this class.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import BillingStoreError
from app.store.base import BillingStoreBase
from app.store.database import async_savepoint_scope
from app.store.models import BillingCustomer, BillingEvent, Subscription


ACTIVE_SUBSCRIPTION_STATUSES = frozenset({"active", "trialing"})
CANCELED_SUBSCRIPTION_STATUS = "canceled"


@dataclass(frozen=True)
class BillingEventRecordResult:
    """Result of recording a Stripe event idempotently.

    ``should_process`` is true only when this process inserted the event. Stripe
    retries that hit an existing ``stripe_event_id`` must not execute webhook
    side effects again.
    """

    event: BillingEvent
    should_process: bool
    created: bool


class SQLAlchemyBillingStore(BillingStoreBase):
    """SQLAlchemy implementation of billing persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def set_stripe_customer(
        self,
        user_id: int,
        stripe_customer_id: str,
    ) -> BillingCustomer:
        """Create or update the Stripe customer linked to a user."""

        operation = "set_stripe_customer"
        normalized_user_id = _normalize_int(
            user_id,
            "user_id",
            operation=operation,
        )
        normalized_customer_id = _required_value(
            stripe_customer_id,
            "stripe_customer_id",
            operation=operation,
            prefix="cus_",
        )

        existing_customer = await self.get_billing_customer_by_user_id(
            normalized_user_id
        )

        if existing_customer is not None:
            return await self._update_billing_customer(
                billing_customer_id=existing_customer.id,
                operation=operation,
                values={"stripe_customer_id": normalized_customer_id},
            )

        billing_customer = BillingCustomer(
            user_id=normalized_user_id,
            stripe_customer_id=normalized_customer_id,
        )

        try:
            async with async_savepoint_scope(self.session):
                self.session.add(billing_customer)
                await self.session.flush()
        except IntegrityError as error:
            customer_by_user = await self.get_billing_customer_by_user_id(
                normalized_user_id
            )

            if customer_by_user is not None:
                return await self._update_billing_customer(
                    billing_customer_id=customer_by_user.id,
                    operation=operation,
                    values={"stripe_customer_id": normalized_customer_id},
                )

            customer_by_stripe_id = (
                await self.get_billing_customer_by_stripe_customer_id(
                    normalized_customer_id
                )
            )

            if customer_by_stripe_id is not None:
                raise BillingStoreError(
                    technical_message=(
                        "Stripe customer is already linked to another user."
                    ),
                    details={
                        "operation": operation,
                        "user_id": normalized_user_id,
                        "stripe_customer_id": normalized_customer_id,
                        "existing_user_id": customer_by_stripe_id.user_id,
                    },
                )

            raise _billing_store_error(
                operation,
                "Billing customer conflict occurred, but the existing row was not found.",
                details={
                    "user_id": normalized_user_id,
                    "stripe_customer_id": normalized_customer_id,
                },
                error=error,
            )
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to set Stripe customer.",
                details={
                    "user_id": normalized_user_id,
                    "stripe_customer_id": normalized_customer_id,
                },
                error=error,
            )

        return billing_customer

    async def upsert_subscription(self, payload: dict[str, Any]) -> Subscription:
        """Create or update a subscription from normalized Stripe data."""

        operation = "upsert_subscription"
        user_id = _required_int(payload, "user_id", operation=operation)
        stripe_customer_id = _required_str(
            payload,
            "stripe_customer_id",
            operation=operation,
            prefix="cus_",
        )
        stripe_subscription_id = _required_str(
            payload,
            "stripe_subscription_id",
            operation=operation,
            prefix="sub_",
        )
        status = _required_str(payload, "status", operation=operation)

        values = {
            "user_id": user_id,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
            "stripe_price_id": _optional_str(payload.get("stripe_price_id")),
            "status": status,
            "plan": _optional_str(payload.get("plan")),
            "current_period_start": _optional_datetime(
                payload.get("current_period_start"),
                field="current_period_start",
                operation=operation,
            ),
            "current_period_end": _optional_datetime(
                payload.get("current_period_end"),
                field="current_period_end",
                operation=operation,
            ),
            "cancel_at_period_end": _optional_bool(
                payload.get("cancel_at_period_end"),
                default=False,
                field="cancel_at_period_end",
                operation=operation,
            ),
        }

        existing_subscription = await self.get_subscription_by_stripe_subscription_id(
            stripe_subscription_id
        )

        if existing_subscription is not None:
            return await self._update_subscription(
                subscription_id=existing_subscription.id,
                operation=operation,
                values=values,
            )

        subscription = Subscription(**values)

        try:
            async with async_savepoint_scope(self.session):
                self.session.add(subscription)
                await self.session.flush()
        except IntegrityError as error:
            conflicted_subscription = await self.get_subscription_by_stripe_subscription_id(
                stripe_subscription_id
            )

            if conflicted_subscription is not None:
                return await self._update_subscription(
                    subscription_id=conflicted_subscription.id,
                    operation=operation,
                    values=values,
                )

            customer_subscription = await self.get_subscription_by_stripe_customer_id(
                stripe_customer_id
            )

            if customer_subscription is not None:
                raise BillingStoreError(
                    technical_message=(
                        "Stripe customer already has a different subscription."
                    ),
                    details={
                        "operation": operation,
                        "stripe_customer_id": stripe_customer_id,
                        "existing_stripe_subscription_id": (
                            customer_subscription.stripe_subscription_id
                        ),
                        "incoming_stripe_subscription_id": stripe_subscription_id,
                    },
                )

            raise _billing_store_error(
                operation,
                "Subscription conflict occurred, but the existing row was not found.",
                details={
                    "stripe_customer_id": stripe_customer_id,
                    "stripe_subscription_id": stripe_subscription_id,
                },
                error=error,
            )
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to upsert subscription.",
                details={
                    "user_id": user_id,
                    "stripe_customer_id": stripe_customer_id,
                    "stripe_subscription_id": stripe_subscription_id,
                },
                error=error,
            )

        return subscription

    async def record_billing_event(
        self,
        payload: dict[str, Any],
    ) -> BillingEventRecordResult:
        """Record a Stripe webhook event idempotently.

        If Stripe retries the same event, the existing row is returned instead
        of creating a duplicate or surfacing a raw unique-constraint error.
        """

        operation = "record_billing_event"
        stripe_event_id = _required_str(
            payload,
            "stripe_event_id",
            operation=operation,
            prefix="evt_",
        )
        event_type = _required_str(payload, "event_type", operation=operation)
        payload_json = _required_mapping(payload, "payload_json", operation=operation)
        processed_at = _optional_datetime(
            payload.get("processed_at"),
            field="processed_at",
            operation=operation,
        )

        event = BillingEvent(
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            payload_json=dict(payload_json),
            processed_at=processed_at,
        )

        try:
            async with async_savepoint_scope(self.session):
                self.session.add(event)
                await self.session.flush()
        except IntegrityError as error:
            existing_event = await self.get_billing_event_by_stripe_event_id(
                stripe_event_id
            )

            if existing_event is not None:
                return BillingEventRecordResult(
                    event=existing_event,
                    should_process=False,
                    created=False,
                )

            raise _billing_store_error(
                operation,
                "Billing event conflict occurred, but the existing row was not found.",
                details={"stripe_event_id": stripe_event_id},
                error=error,
            )
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to record billing event.",
                details={"stripe_event_id": stripe_event_id},
                error=error,
            )

        return BillingEventRecordResult(
            event=event,
            should_process=True,
            created=True,
        )

    async def get_subscription_by_user_id(self, user_id: int) -> Subscription | None:
        """Return the latest subscription for a user, or ``None`` when absent."""

        operation = "get_subscription_by_user_id"

        try:
            result = await self.session.execute(
                select(Subscription)
                .where(Subscription.user_id == user_id)
                .order_by(Subscription.created_at.desc(), Subscription.id.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to get subscription by user id.",
                details={"user_id": user_id},
                error=error,
            )

    async def get_active_subscription(self, user_id: int) -> Subscription | None:
        """Return the latest active or trialing subscription for a user."""

        operation = "get_active_subscription"

        try:
            result = await self.session.execute(
                select(Subscription)
                .where(
                    Subscription.user_id == user_id,
                    Subscription.status.in_(ACTIVE_SUBSCRIPTION_STATUSES),
                )
                .order_by(Subscription.created_at.desc(), Subscription.id.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to get active subscription.",
                details={"user_id": user_id},
                error=error,
            )

    async def get_billing_customer_by_user_id(
        self,
        user_id: int,
    ) -> BillingCustomer | None:
        """Return the Stripe customer linked to a user, if any."""

        operation = "get_billing_customer_by_user_id"
        normalized_user_id = _normalize_int(
            user_id,
            "user_id",
            operation=operation,
        )

        try:
            result = await self.session.execute(
                select(BillingCustomer).where(
                    BillingCustomer.user_id == normalized_user_id
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to get billing customer by user id.",
                details={"user_id": normalized_user_id},
                error=error,
            )

    async def get_billing_customer_by_stripe_customer_id(
        self,
        stripe_customer_id: str,
    ) -> BillingCustomer | None:
        """Return the user/customer link for a Stripe customer id."""

        operation = "get_billing_customer_by_stripe_customer_id"
        normalized_customer_id = _required_value(
            stripe_customer_id,
            "stripe_customer_id",
            operation=operation,
            prefix="cus_",
        )

        try:
            result = await self.session.execute(
                select(BillingCustomer).where(
                    BillingCustomer.stripe_customer_id == normalized_customer_id
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to get billing customer by Stripe customer id.",
                details={"stripe_customer_id": normalized_customer_id},
                error=error,
            )

    async def get_subscription_by_stripe_subscription_id(
        self,
        stripe_subscription_id: str,
    ) -> Subscription | None:
        """Return a subscription by Stripe subscription id."""

        operation = "get_subscription_by_stripe_subscription_id"
        normalized_subscription_id = _required_value(
            stripe_subscription_id,
            "stripe_subscription_id",
            operation=operation,
            prefix="sub_",
        )

        try:
            result = await self.session.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == normalized_subscription_id
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to get subscription by Stripe subscription id.",
                details={"stripe_subscription_id": normalized_subscription_id},
                error=error,
            )

    async def get_subscription_by_stripe_customer_id(
        self,
        stripe_customer_id: str,
    ) -> Subscription | None:
        """Return a subscription by Stripe customer id."""

        operation = "get_subscription_by_stripe_customer_id"
        normalized_customer_id = _required_value(
            stripe_customer_id,
            "stripe_customer_id",
            operation=operation,
            prefix="cus_",
        )

        try:
            result = await self.session.execute(
                select(Subscription).where(
                    Subscription.stripe_customer_id == normalized_customer_id
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to get subscription by Stripe customer id.",
                details={"stripe_customer_id": normalized_customer_id},
                error=error,
            )

    async def get_billing_event_by_stripe_event_id(
        self,
        stripe_event_id: str,
    ) -> BillingEvent | None:
        """Return a billing event by Stripe event id."""

        operation = "get_billing_event_by_stripe_event_id"
        normalized_event_id = _required_value(
            stripe_event_id,
            "stripe_event_id",
            operation=operation,
            prefix="evt_",
        )

        try:
            result = await self.session.execute(
                select(BillingEvent).where(
                    BillingEvent.stripe_event_id == normalized_event_id
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to get billing event by Stripe event id.",
                details={"stripe_event_id": normalized_event_id},
                error=error,
            )

    async def mark_billing_event_processed(
        self,
        stripe_event_id: str,
    ) -> BillingEvent:
        """Mark a recorded billing event as processed."""

        operation = "mark_billing_event_processed"
        normalized_event_id = _required_value(
            stripe_event_id,
            "stripe_event_id",
            operation=operation,
            prefix="evt_",
        )

        try:
            result = await self.session.execute(
                update(BillingEvent)
                .where(BillingEvent.stripe_event_id == normalized_event_id)
                .values(processed_at=func.now())
                .returning(BillingEvent.id)
            )
            event_id = result.scalar_one_or_none()

            if event_id is None:
                raise BillingStoreError(
                    technical_message="Billing event was not found for processing.",
                    details={
                        "operation": operation,
                        "stripe_event_id": normalized_event_id,
                    },
                )

            event = await self.session.get(BillingEvent, event_id)

            if event is None:
                raise BillingStoreError(
                    technical_message="Processed billing event was not found.",
                    details={"operation": operation, "event_id": event_id},
                )

            return event
        except BillingStoreError:
            raise
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to mark billing event as processed.",
                details={"stripe_event_id": normalized_event_id},
                error=error,
            )

    async def mark_subscription_canceled(
        self,
        stripe_subscription_id: str,
        *,
        cancel_at_period_end: bool = False,
    ) -> Subscription:
        """Mark a Stripe subscription as canceled locally."""

        operation = "mark_subscription_canceled"
        normalized_subscription_id = _required_value(
            stripe_subscription_id,
            "stripe_subscription_id",
            operation=operation,
            prefix="sub_",
        )

        try:
            result = await self.session.execute(
                update(Subscription)
                .where(Subscription.stripe_subscription_id == normalized_subscription_id)
                .values(
                    status=CANCELED_SUBSCRIPTION_STATUS,
                    cancel_at_period_end=cancel_at_period_end,
                    updated_at=func.now(),
                )
                .returning(Subscription.id)
            )
            subscription_id = result.scalar_one_or_none()

            if subscription_id is None:
                raise BillingStoreError(
                    technical_message="Subscription was not found for cancellation.",
                    details={
                        "operation": operation,
                        "stripe_subscription_id": normalized_subscription_id,
                    },
                )

            subscription = await self.session.get(Subscription, subscription_id)

            if subscription is None:
                raise BillingStoreError(
                    technical_message="Canceled subscription was not found.",
                    details={"operation": operation, "subscription_id": subscription_id},
                )

            return subscription
        except BillingStoreError:
            raise
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to mark subscription as canceled.",
                details={"stripe_subscription_id": normalized_subscription_id},
                error=error,
            )

    async def _update_subscription(
        self,
        *,
        subscription_id: int,
        operation: str,
        values: Mapping[str, Any],
    ) -> Subscription:
        """Update a subscription and return the updated row."""

        update_values = dict(values)
        update_values["updated_at"] = func.now()

        try:
            result = await self.session.execute(
                update(Subscription)
                .where(Subscription.id == subscription_id)
                .values(**update_values)
                .returning(Subscription.id)
            )
            updated_subscription_id = result.scalar_one_or_none()

            if updated_subscription_id is None:
                raise BillingStoreError(
                    technical_message="Subscription was not found for update.",
                    details={
                        "operation": operation,
                        "subscription_id": subscription_id,
                    },
                )

            subscription = await self.session.get(
                Subscription,
                updated_subscription_id,
            )

            if subscription is None:
                raise BillingStoreError(
                    technical_message="Updated subscription was not found.",
                    details={
                        "operation": operation,
                        "subscription_id": updated_subscription_id,
                    },
                )

            return subscription
        except BillingStoreError:
            raise
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to update subscription.",
                details={"subscription_id": subscription_id},
                error=error,
            )

    async def _update_billing_customer(
        self,
        *,
        billing_customer_id: int,
        operation: str,
        values: Mapping[str, Any],
    ) -> BillingCustomer:
        """Update a billing customer row and return it."""

        update_values = dict(values)
        update_values["updated_at"] = func.now()

        try:
            result = await self.session.execute(
                update(BillingCustomer)
                .where(BillingCustomer.id == billing_customer_id)
                .values(**update_values)
                .returning(BillingCustomer.id)
            )
            updated_billing_customer_id = result.scalar_one_or_none()

            if updated_billing_customer_id is None:
                raise BillingStoreError(
                    technical_message="Billing customer was not found for update.",
                    details={
                        "operation": operation,
                        "billing_customer_id": billing_customer_id,
                    },
                )

            billing_customer = await self.session.get(
                BillingCustomer,
                updated_billing_customer_id,
            )

            if billing_customer is None:
                raise BillingStoreError(
                    technical_message="Updated billing customer was not found.",
                    details={
                        "operation": operation,
                        "billing_customer_id": updated_billing_customer_id,
                    },
                )

            return billing_customer
        except BillingStoreError:
            raise
        except SQLAlchemyError as error:
            raise _billing_store_error(
                operation,
                "Failed to update billing customer.",
                details={"billing_customer_id": billing_customer_id},
                error=error,
            )


BillingStore = SQLAlchemyBillingStore


def _required_str(
    payload: Mapping[str, Any],
    field: str,
    *,
    operation: str,
    prefix: str | None = None,
) -> str:
    value = payload.get(field)
    return _required_value(value, field, operation=operation, prefix=prefix)


def _required_int(
    payload: Mapping[str, Any],
    field: str,
    *,
    operation: str,
) -> int:
    value = payload.get(field)
    return _normalize_int(value, field, operation=operation)


def _normalize_int(value: Any, field: str, *, operation: str) -> int:
    if isinstance(value, bool):
        raise BillingStoreError(
            technical_message=f"Required billing field must be an integer: {field}",
            details={"operation": operation, "field": field, "value": value},
        )

    if isinstance(value, int):
        parsed_value = value
    elif isinstance(value, str) and value.strip().isdigit():
        parsed_value = int(value.strip())
    else:
        raise BillingStoreError(
            technical_message=f"Required billing field must be an integer: {field}",
            details={"operation": operation, "field": field, "value": value},
        )

    if parsed_value <= 0:
        raise BillingStoreError(
            technical_message=f"Required billing field must be positive: {field}",
            details={"operation": operation, "field": field, "value": value},
        )

    return parsed_value


def _required_mapping(
    payload: Mapping[str, Any],
    field: str,
    *,
    operation: str,
) -> Mapping[str, Any]:
    value = payload.get(field)

    if not isinstance(value, Mapping):
        raise BillingStoreError(
            technical_message=f"Required billing field must be an object: {field}",
            details={"operation": operation, "field": field},
        )

    return value


def _required_value(
    value: Any,
    field: str,
    *,
    operation: str,
    prefix: str | None = None,
) -> str:
    if value is None:
        raise BillingStoreError(
            technical_message=f"Required billing field is missing: {field}",
            details={"operation": operation, "field": field},
        )

    if not isinstance(value, str):
        raise BillingStoreError(
            technical_message=f"Required billing field must be a string: {field}",
            details={
                "operation": operation,
                "field": field,
                "value_type": type(value).__name__,
            },
        )

    normalized = str(value).strip()

    if normalized == "":
        raise BillingStoreError(
            technical_message=f"Required billing field is empty: {field}",
            details={"operation": operation, "field": field},
        )

    if prefix is not None and not normalized.startswith(prefix):
        raise BillingStoreError(
            technical_message=(
                f"Required billing field has invalid Stripe prefix: {field}"
            ),
            details={
                "operation": operation,
                "field": field,
                "expected_prefix": prefix,
            },
        )

    return normalized


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()
    return normalized or None


def _optional_bool(
    value: Any,
    *,
    default: bool,
    field: str,
    operation: str,
) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise BillingStoreError(
        technical_message=f"Billing field must be a boolean: {field}",
        details={"operation": operation, "field": field, "value": value},
    )


def _optional_datetime(
    value: Any,
    *,
    field: str,
    operation: str,
) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value

    raise BillingStoreError(
        technical_message=f"Billing field must be a datetime: {field}",
        details={"operation": operation, "field": field, "value_type": type(value).__name__},
    )


def _billing_store_error(
    operation: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    error: Exception | None = None,
) -> BillingStoreError:
    error_details = {"operation": operation}
    error_details.update(details or {})

    if error is not None:
        error_details["error_type"] = error.__class__.__name__

    return BillingStoreError(
        technical_message=message,
        details=error_details,
    )


__all__ = [
    "ACTIVE_SUBSCRIPTION_STATUSES",
    "BillingEventRecordResult",
    "BillingStore",
    "CANCELED_SUBSCRIPTION_STATUS",
    "SQLAlchemyBillingStore",
]
