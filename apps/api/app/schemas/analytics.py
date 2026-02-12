"""Analytics Pydantic schemas for WISMO dashboard."""

from datetime import datetime
from uuid import UUID

from app.schemas.common import BaseSchema


class WismoSummary(BaseSchema):
    """Summary statistics for WISMO analytics."""

    total_inquiries: int
    resolution_rate: float  # 0.0 - 1.0
    avg_per_day: float
    period_days: int


class DailyCount(BaseSchema):
    """Single day count for trend data."""

    date: str  # YYYY-MM-DD
    count: int


class OrderInquiryResponse(BaseSchema):
    """Single order inquiry for the inquiries table."""

    id: UUID
    customer_email: str | None
    order_number: str | None
    inquiry_type: str
    order_status: str | None
    fulfillment_status: str | None
    resolution: str | None
    created_at: datetime
    resolved_at: datetime | None
