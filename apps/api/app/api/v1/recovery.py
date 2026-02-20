"""Recovery management API endpoints."""

import logging
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentUser, get_db, get_store_for_user
from app.models.abandoned_checkout import AbandonedCheckout
from app.models.email_unsubscribe import EmailUnsubscribe
from app.models.recovery_sequence import RecoverySequence, SequenceStatus
from app.schemas.common import PaginatedResponse
from app.schemas.recovery import (
    AbandonedCheckoutResponse,
    RecoveryCheckResponse,
    RecoveryDailyCount,
    RecoveryItem,
    RecoverySequenceResponse,
    RecoverySettings,
    RecoverySummary,
)
from app.services.recovery_analytics_service import RecoveryAnalyticsService
from app.services.recovery_service import RecoveryService

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Authenticated endpoints ---


@router.get("/sequences", response_model=PaginatedResponse[RecoverySequenceResponse])
async def list_sequences(
    user: CurrentUser,
    store_id: UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RecoverySequenceResponse]:
    """Get paginated list of recovery sequences."""
    await get_store_for_user(store_id, user, db)
    service = RecoveryService(db)
    items, total = await service.get_sequences(store_id, page, page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/sequences/{sequence_id}", response_model=RecoverySequenceResponse)
async def get_sequence(
    sequence_id: UUID,
    user: CurrentUser,
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RecoverySequenceResponse:
    """Get a single recovery sequence by ID."""
    store = await get_store_for_user(store_id, user, db)

    stmt = select(RecoverySequence).where(
        RecoverySequence.id == sequence_id,
        RecoverySequence.store_id == store_id,
    )
    seq = (await db.execute(stmt)).scalar_one_or_none()
    if not seq:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sequence not found")

    timing = (
        (store.settings or {})
        .get("recovery", {})
        .get("sequence_timing_minutes", [120, 1440, 2880, 4320])
    )

    return RecoverySequenceResponse(
        id=seq.id,
        abandoned_checkout_id=seq.abandoned_checkout_id,
        customer_email=seq.customer_email,
        sequence_type=seq.sequence_type,
        status=seq.status.value,
        current_step_index=seq.current_step_index,
        steps_completed=seq.steps_completed or [],
        total_steps=len(timing),
        next_step_at=seq.next_step_at,
        started_at=seq.started_at,
        completed_at=seq.completed_at,
        created_at=seq.created_at,
    )


@router.post("/sequences/{sequence_id}/stop")
async def stop_sequence(
    sequence_id: UUID,
    user: CurrentUser,
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Manually stop a recovery sequence."""
    await get_store_for_user(store_id, user, db)

    service = RecoveryService(db)
    stopped = await service.stop_sequence(sequence_id, store_id, "manual_stop")
    if not stopped:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Active sequence not found")

    return {"status": "stopped"}


@router.get("/checkouts", response_model=PaginatedResponse[AbandonedCheckoutResponse])
async def list_checkouts(
    user: CurrentUser,
    store_id: UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AbandonedCheckoutResponse]:
    """Get paginated list of abandoned checkouts."""
    await get_store_for_user(store_id, user, db)
    service = RecoveryService(db)
    items, total = await service.get_checkouts(store_id, page, page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/analytics/summary", response_model=RecoverySummary)
async def recovery_summary(
    user: CurrentUser,
    store_id: UUID = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> RecoverySummary:
    """Get recovery analytics summary."""
    await get_store_for_user(store_id, user, db)
    service = RecoveryAnalyticsService(db)
    return await service.get_summary(store_id, days)


@router.get("/analytics/trend", response_model=list[RecoveryDailyCount])
async def recovery_trend(
    user: CurrentUser,
    store_id: UUID = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> list[RecoveryDailyCount]:
    """Get daily recovery trend data."""
    await get_store_for_user(store_id, user, db)
    service = RecoveryAnalyticsService(db)
    return await service.get_daily_trend(store_id, days)


@router.get("/settings", response_model=RecoverySettings)
async def get_recovery_settings(
    user: CurrentUser,
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RecoverySettings:
    """Get store recovery settings."""
    store = await get_store_for_user(store_id, user, db)
    recovery_config = (store.settings or {}).get("recovery", {})
    return RecoverySettings(**recovery_config)


@router.patch("/settings", response_model=RecoverySettings)
async def update_recovery_settings(
    data: RecoverySettings,
    user: CurrentUser,
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RecoverySettings:
    """Update store recovery settings."""
    await get_store_for_user(store_id, user, db)
    service = RecoveryService(db)
    return await service.update_settings(store_id, data)


# --- Public endpoints ---


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Handle email unsubscribe via signed token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        store_id = UUID(payload["store_id"])
        email = payload["email"]
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return HTMLResponse(
            "<html><body><h1>Invalid Link</h1>"
            "<p>This unsubscribe link is invalid or has expired.</p></body></html>",
            status_code=400,
        )

    # Create unsubscribe record (idempotent via unique constraint)
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = (
        pg_insert(EmailUnsubscribe)
        .values(
            store_id=store_id,
            email=email,
        )
        .on_conflict_do_nothing(
            constraint="uq_email_unsubscribes_store_email",
        )
    )
    await db.execute(stmt)

    # Stop all active sequences
    service = RecoveryService(db)
    await service.stop_sequences_for_email(store_id, email, "unsubscribed")

    await db.commit()

    return HTMLResponse(
        "<html><body style='font-family: sans-serif; text-align: center; padding: 60px;'>"
        "<h1>Unsubscribed</h1>"
        "<p>You've been unsubscribed from cart recovery emails. "
        "You won't receive any more recovery emails from this store.</p>"
        "</body></html>"
    )


@router.get("/check", response_model=RecoveryCheckResponse)
async def check_recovery(
    store_id: UUID = Query(...),
    session_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RecoveryCheckResponse:
    """Check if the current widget session has an active recovery.

    Maps session_id -> conversations -> customer_email -> active recovery sequences.
    """
    from app.models.conversation import Conversation

    # Find conversations with this session_id that have a customer email
    conv_stmt = (
        select(Conversation.customer_email)
        .where(
            Conversation.store_id == store_id,
            Conversation.session_id == session_id,
            Conversation.customer_email.isnot(None),
        )
        .distinct()
    )
    conv_result = await db.execute(conv_stmt)
    emails = [row[0] for row in conv_result.all() if row[0]]

    if not emails:
        return RecoveryCheckResponse()

    # Find active recovery sequences for these emails
    seq_stmt = (
        select(RecoverySequence)
        .where(
            RecoverySequence.store_id == store_id,
            RecoverySequence.customer_email.in_(emails),
            RecoverySequence.status == SequenceStatus.ACTIVE,
        )
        .order_by(RecoverySequence.created_at.desc())
        .limit(1)
    )
    seq = (await db.execute(seq_stmt)).scalar_one_or_none()
    if not seq:
        return RecoveryCheckResponse()

    # Load the abandoned checkout for cart items
    checkout = (
        await db.execute(
            select(AbandonedCheckout).where(AbandonedCheckout.id == seq.abandoned_checkout_id)
        )
    ).scalar_one_or_none()

    if not checkout:
        return RecoveryCheckResponse()

    items = [
        RecoveryItem(
            title=item.get("title", "Item"),
            price=str(item.get("price", "0.00")),
            image_url=item.get("image_url"),
            quantity=item.get("quantity", 1),
        )
        for item in (checkout.line_items or [])[:5]
    ]

    return RecoveryCheckResponse(
        has_recovery=True,
        items=items,
        checkout_url=checkout.checkout_url,
        total_price=str(checkout.total_price),
        sequence_id=seq.id,
    )
