"""Recovery analytics service using SQL aggregation."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.models.abandoned_checkout import AbandonedCheckout, CheckoutStatus
from app.models.recovery_event import RecoveryEvent
from app.models.recovery_sequence import RecoverySequence, SequenceStatus
from app.schemas.recovery import RecoveryDailyCount, RecoverySummary

logger = logging.getLogger(__name__)


class RecoveryAnalyticsService:
    """Analytics service for cart recovery data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(self, store_id: UUID, days: int = 30) -> RecoverySummary:
        """Get recovery summary statistics for the given time period."""
        since = datetime.now(UTC) - timedelta(days=days)

        # Abandoned checkouts stats
        checkout_stmt = select(
            func.count().label("total_abandoned"),
            func.count(
                case(
                    (AbandonedCheckout.status == CheckoutStatus.RECOVERED, 1),
                    (AbandonedCheckout.status == CheckoutStatus.COMPLETED, 1),
                    else_=None,
                )
            ).label("total_recovered"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            AbandonedCheckout.status.in_(
                                [CheckoutStatus.RECOVERED, CheckoutStatus.COMPLETED]
                            ),
                            AbandonedCheckout.total_price,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("recovered_revenue"),
        ).where(
            AbandonedCheckout.store_id == store_id,
            AbandonedCheckout.status != CheckoutStatus.ACTIVE,
            AbandonedCheckout.created_at >= since,
        )

        checkout_result = await self.db.execute(checkout_stmt)
        checkout_row = checkout_result.one()

        total_abandoned = checkout_row.total_abandoned or 0
        total_recovered = checkout_row.total_recovered or 0
        recovered_revenue = float(checkout_row.recovered_revenue or 0)

        recovery_rate = total_recovered / total_abandoned if total_abandoned > 0 else 0.0

        # Count emails sent
        email_stmt = select(func.count()).where(
            RecoveryEvent.store_id == store_id,
            RecoveryEvent.event_type == "email_sent",
            RecoveryEvent.created_at >= since,
        )
        emails_sent = (await self.db.execute(email_stmt)).scalar() or 0

        # Count active sequences
        active_stmt = select(func.count()).where(
            RecoverySequence.store_id == store_id,
            RecoverySequence.status == SequenceStatus.ACTIVE,
        )
        active_sequences = (await self.db.execute(active_stmt)).scalar() or 0

        return RecoverySummary(
            total_abandoned=total_abandoned,
            total_recovered=total_recovered,
            recovery_rate=round(recovery_rate, 3),
            recovered_revenue=round(recovered_revenue, 2),
            emails_sent=emails_sent,
            active_sequences=active_sequences,
            period_days=days,
        )

    async def get_daily_trend(self, store_id: UUID, days: int = 30) -> list[RecoveryDailyCount]:
        """Get daily abandoned vs recovered counts for trend chart."""
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(
                cast(AbandonedCheckout.created_at, Date).label("day"),
                func.count().label("abandoned"),
                func.count(
                    case(
                        (
                            AbandonedCheckout.status.in_(
                                [CheckoutStatus.RECOVERED, CheckoutStatus.COMPLETED]
                            ),
                            1,
                        ),
                        else_=None,
                    )
                ).label("recovered"),
            )
            .where(
                AbandonedCheckout.store_id == store_id,
                AbandonedCheckout.status != CheckoutStatus.ACTIVE,
                AbandonedCheckout.created_at >= since,
            )
            .group_by("day")
            .order_by("day")
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            RecoveryDailyCount(date=str(row.day), abandoned=row.abandoned, recovered=row.recovered)
            for row in rows
        ]
