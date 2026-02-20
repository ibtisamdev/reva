"""Celery tasks for cart recovery: webhook processing and abandonment detection."""

import asyncio
import contextlib
import logging
import re
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import async_session_maker, engine
from app.models.abandoned_checkout import AbandonedCheckout, CheckoutStatus
from app.models.store import Store
from app.workers.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


def _run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine in a fresh event loop, disposing DB connections after.

    Each Celery prefork worker creates a new event loop per task. asyncpg connections
    are bound to the loop that created them — if pooled connections from a previous
    (closed) loop are reused, RuntimeError("Event loop is closed") is raised.

    Disposing the engine after each task clears stale pooled connections so the next
    task gets fresh ones.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.run_until_complete(engine.dispose())
        loop.close()


# ---------------------------------------------------------------------------
# Checkout webhook processing
# ---------------------------------------------------------------------------


@celery_app.task(  # type: ignore[untyped-decorator]
    name="tasks.recovery.process_checkout_webhook",
    base=BaseTask,
    bind=True,
)
def process_checkout_webhook(
    self: BaseTask,  # noqa: ARG001
    store_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Upsert an AbandonedCheckout from a Shopify checkout webhook."""
    return _run_async(_process_checkout_webhook_async(UUID(store_id), event_type, payload))


async def _process_checkout_webhook_async(
    store_id: UUID, event_type: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Async implementation of checkout webhook processing."""
    checkout_id = str(payload.get("id", ""))
    if not checkout_id:
        return {"status": "ignored", "reason": "no checkout id"}

    # Extract customer email from nested structures
    email = payload.get("email")
    if not email:
        customer = payload.get("customer") or {}
        email = customer.get("email")

    # Extract customer name
    customer_name = None
    if payload.get("billing_address"):
        addr = payload["billing_address"]
        parts = [addr.get("first_name", ""), addr.get("last_name", "")]
        customer_name = " ".join(p for p in parts if p).strip() or None
    if not customer_name and payload.get("customer"):
        cust = payload["customer"]
        parts = [cust.get("first_name", ""), cust.get("last_name", "")]
        customer_name = " ".join(p for p in parts if p).strip() or None

    # Extract line items
    line_items = []
    for item in payload.get("line_items", []):
        line_items.append(
            {
                "title": item.get("title", ""),
                "quantity": item.get("quantity", 1),
                "price": str(item.get("price", "0.00")),
                "variant_title": item.get("variant_title"),
                "image_url": (item.get("image") or {}).get("src")
                if isinstance(item.get("image"), dict)
                else None,
            }
        )

    total_price = payload.get("total_price", "0.00")
    currency = payload.get("currency", "USD")
    checkout_url = payload.get("abandoned_checkout_url") or payload.get("checkout_url")
    token = payload.get("token")

    values: dict[str, Any] = {
        "store_id": store_id,
        "shopify_checkout_id": checkout_id,
        "shopify_checkout_token": token,
        "customer_email": email,
        "customer_name": customer_name,
        "total_price": total_price,
        "currency": currency,
        "line_items": line_items,
        "checkout_url": checkout_url,
        "status": CheckoutStatus.ACTIVE.value,
    }

    async with async_session_maker() as session:
        stmt = pg_insert(AbandonedCheckout).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_abandoned_checkouts_store_checkout",
            set_={
                "customer_email": stmt.excluded.customer_email,
                "customer_name": stmt.excluded.customer_name,
                "total_price": stmt.excluded.total_price,
                "currency": stmt.excluded.currency,
                "line_items": stmt.excluded.line_items,
                "checkout_url": stmt.excluded.checkout_url,
                "shopify_checkout_token": stmt.excluded.shopify_checkout_token,
                "updated_at": datetime.now(UTC),
            },
        )
        await session.execute(stmt)
        await session.commit()

    logger.info(
        "Processed checkout webhook: store=%s checkout=%s event=%s",
        store_id,
        checkout_id,
        event_type,
    )
    return {"status": "processed", "checkout_id": checkout_id, "event_type": event_type}


# ---------------------------------------------------------------------------
# Order completed — marks checkout as completed, stops recovery
# ---------------------------------------------------------------------------


@celery_app.task(  # type: ignore[untyped-decorator]
    name="tasks.recovery.process_order_completed",
    base=BaseTask,
    bind=True,
)
def process_order_completed(
    self: BaseTask,  # noqa: ARG001
    store_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Mark matching abandoned checkouts as completed when an order is placed."""
    return _run_async(_process_order_completed_async(UUID(store_id), payload))


async def _process_order_completed_async(store_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    """Async implementation of order completed processing."""
    email = payload.get("email") or (payload.get("customer") or {}).get("email")
    order_id = str(payload.get("id", ""))
    checkout_token = payload.get("checkout_token")

    if not email and not checkout_token:
        return {"status": "ignored", "reason": "no email or checkout token"}

    async with async_session_maker() as session:
        # Find matching abandoned checkouts by checkout_token or email
        conditions = [
            AbandonedCheckout.store_id == store_id,
            AbandonedCheckout.status.in_([CheckoutStatus.ACTIVE, CheckoutStatus.ABANDONED]),
        ]

        if checkout_token:
            # Prefer matching by checkout token (most accurate)
            stmt = select(AbandonedCheckout).where(
                *conditions, AbandonedCheckout.shopify_checkout_token == checkout_token
            )
        else:
            # Fall back to email matching
            stmt = select(AbandonedCheckout).where(
                *conditions, AbandonedCheckout.customer_email == email
            )

        result = await session.execute(stmt)
        checkouts = list(result.scalars().all())

        if not checkouts:
            return {"status": "no_match", "order_id": order_id}

        now = datetime.now(UTC)
        for checkout in checkouts:
            checkout.status = CheckoutStatus.COMPLETED
            checkout.completed_order_id = order_id
            checkout.recovered_at = now if checkout.abandonment_detected_at else None

        await session.commit()

        logger.info(
            "Order completed: store=%s order=%s matched=%d checkouts",
            store_id,
            order_id,
            len(checkouts),
        )

    # Stop any active recovery sequences for this email
    if email:
        with contextlib.suppress(Exception):
            stop_sequences_for_email.delay(str(store_id), email, "order_completed")

    return {"status": "completed", "order_id": order_id, "checkouts_updated": len(checkouts)}


# ---------------------------------------------------------------------------
# Periodic abandonment detection (Celery Beat)
# ---------------------------------------------------------------------------


@celery_app.task(  # type: ignore[untyped-decorator]
    name="tasks.recovery.check_abandoned_checkouts",
    base=BaseTask,
    bind=True,
)
def check_abandoned_checkouts(self: BaseTask) -> dict[str, Any]:  # noqa: ARG001
    """Periodic task: detect abandoned checkouts and trigger recovery sequences."""
    return _run_async(_check_abandoned_checkouts_async())


async def _check_abandoned_checkouts_async() -> dict[str, Any]:
    """Async implementation of abandonment detection."""
    total_detected = 0

    async with async_session_maker() as session:
        # Find stores with recovery enabled
        stmt = select(Store).where(Store.is_active == True)  # noqa: E712
        result = await session.execute(stmt)
        stores = list(result.scalars().all())

        for store in stores:
            recovery_settings = (store.settings or {}).get("recovery", {})
            if not recovery_settings.get("enabled", False):
                continue

            threshold_minutes = recovery_settings.get("abandonment_threshold_minutes", 60)
            min_cart_value = recovery_settings.get("min_cart_value", 0)
            exclude_patterns = recovery_settings.get("exclude_email_patterns", [])

            cutoff = datetime.now(UTC) - timedelta(minutes=threshold_minutes)

            # Find stale active checkouts
            checkout_stmt = select(AbandonedCheckout).where(
                AbandonedCheckout.store_id == store.id,
                AbandonedCheckout.status == CheckoutStatus.ACTIVE,
                AbandonedCheckout.updated_at < cutoff,
                AbandonedCheckout.customer_email.isnot(None),
                AbandonedCheckout.total_price >= min_cart_value,
            )
            checkout_result = await session.execute(checkout_stmt)
            stale_checkouts = list(checkout_result.scalars().all())

            for checkout in stale_checkouts:
                # Check email exclusion patterns
                if checkout.customer_email and _email_matches_patterns(
                    checkout.customer_email, exclude_patterns
                ):
                    continue

                checkout.status = CheckoutStatus.ABANDONED
                checkout.abandonment_detected_at = datetime.now(UTC)
                total_detected += 1

                # Trigger recovery sequence
                with contextlib.suppress(Exception):
                    start_recovery_sequence.delay(
                        str(store.id),
                        str(checkout.id),
                        checkout.customer_email,
                    )

        await session.commit()

    logger.info("Abandonment check complete: %d new abandonments detected", total_detected)
    return {"status": "completed", "detected": total_detected}


def _email_matches_patterns(email: str, patterns: list[str]) -> bool:
    """Check if an email matches any of the exclusion patterns."""
    for pattern in patterns:
        try:
            if re.search(pattern, email, re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


# ---------------------------------------------------------------------------
# Recovery sequence tasks
# ---------------------------------------------------------------------------


@celery_app.task(  # type: ignore[untyped-decorator]
    name="tasks.recovery.start_recovery_sequence",
    base=BaseTask,
    bind=True,
)
def start_recovery_sequence(
    self: BaseTask,  # noqa: ARG001
    store_id: str,
    checkout_id: str,
    customer_email: str,
) -> dict[str, Any]:
    """Start a recovery email sequence for an abandoned checkout."""
    return _run_async(
        _start_recovery_sequence_async(UUID(store_id), UUID(checkout_id), customer_email)
    )


async def _start_recovery_sequence_async(
    store_id: UUID, checkout_id: UUID, customer_email: str
) -> dict[str, Any]:
    """Async implementation of starting a recovery sequence."""
    from app.services.recovery_service import RecoveryService

    async with async_session_maker() as session:
        service = RecoveryService(session)
        sequence = await service.start_sequence(store_id, checkout_id, customer_email)

        if sequence:
            return {
                "status": "started",
                "sequence_id": str(sequence.id),
                "type": sequence.sequence_type,
            }
        return {"status": "skipped", "email": customer_email}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="tasks.recovery.execute_sequence_step",
    base=BaseTask,
    bind=True,
    max_retries=2,
)
def execute_sequence_step(
    self: BaseTask,  # noqa: ARG001
    sequence_id: str,
    store_id: str,
) -> dict[str, Any]:
    """Execute the current step of a recovery sequence."""
    return _run_async(_execute_sequence_step_async(UUID(sequence_id), UUID(store_id)))


async def _execute_sequence_step_async(sequence_id: UUID, store_id: UUID) -> dict[str, Any]:
    """Async implementation of executing a sequence step."""
    from app.services.recovery_service import RecoveryService

    async with async_session_maker() as session:
        service = RecoveryService(session)
        return await service.execute_step(sequence_id, store_id)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="tasks.recovery.stop_sequences_for_email",
    base=BaseTask,
    bind=True,
)
def stop_sequences_for_email(
    self: BaseTask,  # noqa: ARG001
    store_id: str,
    email: str,
    reason: str,
) -> dict[str, Any]:
    """Stop all active recovery sequences for an email."""
    return _run_async(_stop_sequences_for_email_async(UUID(store_id), email, reason))


async def _stop_sequences_for_email_async(
    store_id: UUID, email: str, reason: str
) -> dict[str, Any]:
    """Async implementation of stopping sequences for an email."""
    from app.services.recovery_service import RecoveryService

    async with async_session_maker() as session:
        service = RecoveryService(session)
        count = await service.stop_sequences_for_email(store_id, email, reason)
        return {"status": "stopped", "sequences_stopped": count, "reason": reason}
