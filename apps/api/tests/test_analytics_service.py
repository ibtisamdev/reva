"""Unit tests for WismoAnalyticsService.

Tests summary statistics, daily trend aggregation, and paginated inquiry listing.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_inquiry import InquiryResolution, InquiryType
from app.models.store import Store
from app.services.analytics_service import WismoAnalyticsService


class TestGetSummary:
    """Tests for WismoAnalyticsService.get_summary()."""

    @pytest.mark.asyncio
    async def test_returns_summary_with_data(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Returns correct summary statistics when inquiries exist."""
        # 3 inquiries: 2 resolved, 1 unresolved
        await order_inquiry_factory(store_id=store.id, resolution=InquiryResolution.ANSWERED)
        await order_inquiry_factory(
            store_id=store.id, resolution=InquiryResolution.TRACKING_PROVIDED
        )
        await order_inquiry_factory(store_id=store.id, resolution=None)

        service = WismoAnalyticsService(db_session)
        summary = await service.get_summary(store.id, days=30)

        assert summary.total_inquiries == 3
        assert summary.resolution_rate == round(2 / 3, 3)
        assert summary.period_days == 30
        assert summary.avg_per_day == round(3 / 30, 2)

    @pytest.mark.asyncio
    async def test_returns_zeros_when_empty(
        self,
        db_session: AsyncSession,
        store: Store,
    ) -> None:
        """Returns zeroed summary when no inquiries exist."""
        service = WismoAnalyticsService(db_session)
        summary = await service.get_summary(store.id, days=30)

        assert summary.total_inquiries == 0
        assert summary.resolution_rate == 0.0
        assert summary.avg_per_day == 0.0
        assert summary.period_days == 30

    @pytest.mark.asyncio
    async def test_respects_store_scope(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Only counts inquiries for the specified store."""
        await order_inquiry_factory(store_id=store.id, resolution=InquiryResolution.ANSWERED)
        await order_inquiry_factory(store_id=store.id, resolution=InquiryResolution.ANSWERED)
        await order_inquiry_factory(store_id=other_store.id, resolution=InquiryResolution.ANSWERED)

        service = WismoAnalyticsService(db_session)
        summary = await service.get_summary(store.id, days=30)

        assert summary.total_inquiries == 2

    @pytest.mark.asyncio
    async def test_custom_days_parameter(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Custom days parameter affects avg_per_day and period_days."""
        await order_inquiry_factory(store_id=store.id)

        service = WismoAnalyticsService(db_session)
        summary = await service.get_summary(store.id, days=7)

        assert summary.period_days == 7
        assert summary.avg_per_day == round(1 / 7, 2)

    @pytest.mark.asyncio
    async def test_resolution_rate_calculation(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Resolution rate is correctly calculated as resolved/total."""
        # All resolved
        for _ in range(5):
            await order_inquiry_factory(store_id=store.id, resolution=InquiryResolution.ANSWERED)
        # 5 unresolved
        for _ in range(5):
            await order_inquiry_factory(store_id=store.id, resolution=None)

        service = WismoAnalyticsService(db_session)
        summary = await service.get_summary(store.id, days=30)

        assert summary.total_inquiries == 10
        assert summary.resolution_rate == 0.5

    @pytest.mark.asyncio
    async def test_only_successful_resolutions_count_as_resolved(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Only ANSWERED and TRACKING_PROVIDED count as resolved."""
        await order_inquiry_factory(store_id=store.id, resolution=InquiryResolution.ANSWERED)
        await order_inquiry_factory(
            store_id=store.id, resolution=InquiryResolution.TRACKING_PROVIDED
        )
        await order_inquiry_factory(
            store_id=store.id, resolution=InquiryResolution.VERIFICATION_FAILED
        )
        await order_inquiry_factory(store_id=store.id, resolution=InquiryResolution.ESCALATED)
        await order_inquiry_factory(store_id=store.id, resolution=InquiryResolution.UNRESOLVED)

        service = WismoAnalyticsService(db_session)
        summary = await service.get_summary(store.id, days=30)

        assert summary.total_inquiries == 5
        assert summary.resolution_rate == round(2 / 5, 3)


class TestGetDailyTrend:
    """Tests for WismoAnalyticsService.get_daily_trend()."""

    @pytest.mark.asyncio
    async def test_returns_daily_counts(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Returns daily counts with date strings."""
        await order_inquiry_factory(store_id=store.id)
        await order_inquiry_factory(store_id=store.id)

        service = WismoAnalyticsService(db_session)
        trend = await service.get_daily_trend(store.id, days=30)

        assert len(trend) >= 1
        # All inquiries created today should be in one bucket
        total_count = sum(d.count for d in trend)
        assert total_count == 2

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_data(
        self,
        db_session: AsyncSession,
        store: Store,
    ) -> None:
        """Returns empty list when no inquiries exist."""
        service = WismoAnalyticsService(db_session)
        trend = await service.get_daily_trend(store.id, days=30)

        assert trend == []

    @pytest.mark.asyncio
    async def test_respects_store_scope(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Only includes inquiries for the specified store."""
        await order_inquiry_factory(store_id=store.id)
        await order_inquiry_factory(store_id=other_store.id)

        service = WismoAnalyticsService(db_session)
        trend = await service.get_daily_trend(store.id, days=30)

        total_count = sum(d.count for d in trend)
        assert total_count == 1

    @pytest.mark.asyncio
    async def test_dates_are_sorted(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Results are sorted by date ascending."""
        await order_inquiry_factory(store_id=store.id)

        service = WismoAnalyticsService(db_session)
        trend = await service.get_daily_trend(store.id, days=30)

        if len(trend) > 1:
            dates = [d.date for d in trend]
            assert dates == sorted(dates)

    @pytest.mark.asyncio
    async def test_date_format_is_yyyy_mm_dd(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Dates are formatted as YYYY-MM-DD strings."""
        await order_inquiry_factory(store_id=store.id)

        service = WismoAnalyticsService(db_session)
        trend = await service.get_daily_trend(store.id, days=30)

        assert len(trend) >= 1
        # Validate date format
        date_str = trend[0].date
        datetime.strptime(date_str, "%Y-%m-%d")


class TestGetRecentInquiries:
    """Tests for WismoAnalyticsService.get_recent_inquiries()."""

    @pytest.mark.asyncio
    async def test_returns_paginated_results(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Returns items and total count."""
        for i in range(3):
            await order_inquiry_factory(
                store_id=store.id,
                order_number=f"#100{i}",
            )

        service = WismoAnalyticsService(db_session)
        items, total = await service.get_recent_inquiries(store.id, page=1, page_size=20)

        assert total == 3
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_page_2_offset(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Page 2 with page_size=2 returns remaining items."""
        for i in range(5):
            await order_inquiry_factory(store_id=store.id, order_number=f"#100{i}")

        service = WismoAnalyticsService(db_session)
        items, total = await service.get_recent_inquiries(store.id, page=2, page_size=2)

        assert total == 5
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_data(
        self,
        db_session: AsyncSession,
        store: Store,
    ) -> None:
        """Returns empty list and zero total when no inquiries exist."""
        service = WismoAnalyticsService(db_session)
        items, total = await service.get_recent_inquiries(store.id)

        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_respects_store_scope(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Only returns inquiries for the specified store."""
        await order_inquiry_factory(store_id=store.id)
        await order_inquiry_factory(store_id=store.id)
        await order_inquiry_factory(store_id=other_store.id)

        service = WismoAnalyticsService(db_session)
        items, total = await service.get_recent_inquiries(store.id)

        assert total == 2
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_ordered_by_created_at_desc(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Results are ordered newest first."""
        await order_inquiry_factory(store_id=store.id, order_number="#1001")
        await order_inquiry_factory(store_id=store.id, order_number="#1002")

        service = WismoAnalyticsService(db_session)
        items, _ = await service.get_recent_inquiries(store.id)

        # Most recently created should be first
        assert len(items) == 2
        assert items[0].created_at >= items[1].created_at

    @pytest.mark.asyncio
    async def test_field_mapping(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Fields are correctly mapped from model to response."""
        await order_inquiry_factory(
            store_id=store.id,
            customer_email="test@example.com",
            order_number="#1001",
            inquiry_type=InquiryType.TRACKING,
            order_status="paid",
            fulfillment_status="fulfilled",
            resolution=InquiryResolution.TRACKING_PROVIDED,
        )

        service = WismoAnalyticsService(db_session)
        items, _ = await service.get_recent_inquiries(store.id)

        assert len(items) == 1
        item = items[0]
        assert item.customer_email == "test@example.com"
        assert item.order_number == "#1001"
        assert item.inquiry_type == "tracking"
        assert item.order_status == "paid"
        assert item.fulfillment_status == "fulfilled"
        assert item.resolution == "tracking_provided"

    @pytest.mark.asyncio
    async def test_null_resolution_mapped(
        self,
        db_session: AsyncSession,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Null resolution is mapped as None in response."""
        await order_inquiry_factory(
            store_id=store.id,
            resolution=None,
        )

        service = WismoAnalyticsService(db_session)
        items, _ = await service.get_recent_inquiries(store.id)

        assert len(items) == 1
        assert items[0].resolution is None
