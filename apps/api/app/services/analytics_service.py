"""WISMO analytics service using SQL aggregation."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.models.order_inquiry import InquiryResolution, OrderInquiry
from app.schemas.analytics import DailyCount, OrderInquiryResponse, WismoSummary

logger = logging.getLogger(__name__)


class WismoAnalyticsService:
    """Analytics service for WISMO (Where Is My Order) data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(self, store_id: UUID, days: int = 30) -> WismoSummary:
        """Get summary statistics for the given time period."""
        since = datetime.now(UTC) - timedelta(days=days)

        # Total inquiries + resolved count in a single query
        stmt = select(
            func.count().label("total"),
            func.count(
                case(
                    (
                        OrderInquiry.resolution.in_(
                            [InquiryResolution.ANSWERED, InquiryResolution.TRACKING_PROVIDED]
                        ),
                        1,
                    ),
                    else_=None,
                )
            ).label("resolved"),
        ).where(
            OrderInquiry.store_id == store_id,
            OrderInquiry.created_at >= since,
        )

        result = await self.db.execute(stmt)
        row = result.one()
        total = row.total or 0
        resolved = row.resolved or 0

        resolution_rate = resolved / total if total > 0 else 0.0
        avg_per_day = total / days if days > 0 else 0.0

        return WismoSummary(
            total_inquiries=total,
            resolution_rate=round(resolution_rate, 3),
            avg_per_day=round(avg_per_day, 2),
            period_days=days,
        )

    async def get_daily_trend(self, store_id: UUID, days: int = 30) -> list[DailyCount]:
        """Get daily inquiry counts for the trend chart."""
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(
                cast(OrderInquiry.created_at, Date).label("day"),
                func.count().label("count"),
            )
            .where(
                OrderInquiry.store_id == store_id,
                OrderInquiry.created_at >= since,
            )
            .group_by("day")
            .order_by("day")
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [DailyCount(date=str(row.day), count=row.count) for row in rows]

    async def get_recent_inquiries(
        self,
        store_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OrderInquiryResponse], int]:
        """Get paginated recent inquiries."""
        # Count
        count_stmt = (
            select(func.count()).select_from(OrderInquiry).where(OrderInquiry.store_id == store_id)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Fetch page
        stmt = (
            select(OrderInquiry)
            .where(OrderInquiry.store_id == store_id)
            .order_by(OrderInquiry.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        inquiries = result.scalars().all()

        items = [
            OrderInquiryResponse(
                id=inq.id,
                customer_email=inq.customer_email,
                order_number=inq.order_number,
                inquiry_type=inq.inquiry_type.value,
                order_status=inq.order_status,
                fulfillment_status=inq.fulfillment_status,
                resolution=inq.resolution.value if inq.resolution else None,
                created_at=inq.created_at,
                resolved_at=inq.resolved_at,
            )
            for inq in inquiries
        ]

        return items, total
