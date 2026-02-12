"""WISMO analytics endpoints for the dashboard."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db, get_store_for_user
from app.schemas.analytics import DailyCount, OrderInquiryResponse, WismoSummary
from app.schemas.common import PaginatedResponse
from app.services.analytics_service import WismoAnalyticsService

router = APIRouter()


@router.get("/wismo/summary", response_model=WismoSummary)
async def wismo_summary(
    user: CurrentUser,
    store_id: UUID = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> WismoSummary:
    """Get WISMO summary statistics. Requires authentication."""
    await get_store_for_user(store_id, user, db)
    service = WismoAnalyticsService(db)
    return await service.get_summary(store_id, days)


@router.get("/wismo/trend", response_model=list[DailyCount])
async def wismo_trend(
    user: CurrentUser,
    store_id: UUID = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> list[DailyCount]:
    """Get daily WISMO inquiry counts for trend chart. Requires authentication."""
    await get_store_for_user(store_id, user, db)
    service = WismoAnalyticsService(db)
    return await service.get_daily_trend(store_id, days)


@router.get("/wismo/inquiries", response_model=PaginatedResponse[OrderInquiryResponse])
async def wismo_inquiries(
    user: CurrentUser,
    store_id: UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[OrderInquiryResponse]:
    """Get paginated WISMO inquiries. Requires authentication."""
    await get_store_for_user(store_id, user, db)
    service = WismoAnalyticsService(db)
    items, total = await service.get_recent_inquiries(store_id, page, page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
