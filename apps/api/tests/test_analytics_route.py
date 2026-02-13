"""Tests for WISMO analytics API endpoints.

Covers GET /api/v1/analytics/wismo/summary, /trend, and /inquiries.
"""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient

from app.models.order_inquiry import InquiryResolution
from app.models.store import Store


class TestWismoSummaryEndpoint:
    """Tests for GET /api/v1/analytics/wismo/summary."""

    @pytest.mark.asyncio
    async def test_returns_summary_data(
        self,
        client: AsyncClient,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Returns summary statistics for the store."""
        await order_inquiry_factory(store_id=store.id, resolution=InquiryResolution.ANSWERED)
        await order_inquiry_factory(store_id=store.id, resolution=None)

        response = await client.get(
            "/api/v1/analytics/wismo/summary",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_inquiries"] == 2
        assert data["resolution_rate"] == 0.5
        assert data["period_days"] == 30
        assert "avg_per_day" in data

    @pytest.mark.asyncio
    async def test_requires_authentication(
        self,
        unauthed_client: AsyncClient,
        store: Store,
    ) -> None:
        """Unauthenticated request returns 401."""
        response = await unauthed_client.get(
            "/api/v1/analytics/wismo/summary",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_store_id(
        self,
        client: AsyncClient,
    ) -> None:
        """Missing store_id returns 422."""
        response = await client.get("/api/v1/analytics/wismo/summary")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_nonexistent_store_returns_404(
        self,
        client: AsyncClient,
    ) -> None:
        """Non-existent store_id returns 404."""
        response = await client.get(
            "/api/v1/analytics/wismo/summary",
            params={"store_id": str(uuid.uuid4())},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_custom_days_parameter(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Custom days parameter is respected."""
        response = await client.get(
            "/api/v1/analytics/wismo/summary",
            params={"store_id": str(store.id), "days": "7"},
        )

        assert response.status_code == 200
        assert response.json()["period_days"] == 7

    @pytest.mark.asyncio
    async def test_days_validation(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Days parameter must be 1-365."""
        response = await client.get(
            "/api/v1/analytics/wismo/summary",
            params={"store_id": str(store.id), "days": "0"},
        )

        assert response.status_code == 422


class TestWismoTrendEndpoint:
    """Tests for GET /api/v1/analytics/wismo/trend."""

    @pytest.mark.asyncio
    async def test_returns_trend_data(
        self,
        client: AsyncClient,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Returns daily trend counts."""
        await order_inquiry_factory(store_id=store.id)

        response = await client.get(
            "/api/v1/analytics/wismo/trend",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "date" in data[0]
        assert "count" in data[0]

    @pytest.mark.asyncio
    async def test_requires_authentication(
        self,
        unauthed_client: AsyncClient,
        store: Store,
    ) -> None:
        """Unauthenticated request returns 401."""
        response = await unauthed_client.get(
            "/api/v1/analytics/wismo/trend",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_data(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Returns empty list when no inquiries exist."""
        response = await client.get(
            "/api/v1/analytics/wismo/trend",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        assert response.json() == []


class TestWismoInquiriesEndpoint:
    """Tests for GET /api/v1/analytics/wismo/inquiries."""

    @pytest.mark.asyncio
    async def test_returns_paginated_inquiries(
        self,
        client: AsyncClient,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Returns paginated inquiry list."""
        await order_inquiry_factory(store_id=store.id, order_number="#1001")
        await order_inquiry_factory(store_id=store.id, order_number="#1002")

        response = await client.get(
            "/api/v1/analytics/wismo/inquiries",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert "pages" in data

    @pytest.mark.asyncio
    async def test_requires_authentication(
        self,
        unauthed_client: AsyncClient,
        store: Store,
    ) -> None:
        """Unauthenticated request returns 401."""
        response = await unauthed_client.get(
            "/api/v1/analytics/wismo/inquiries",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_pagination_params(
        self,
        client: AsyncClient,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Pagination parameters are respected."""
        for i in range(5):
            await order_inquiry_factory(store_id=store.id, order_number=f"#100{i}")

        response = await client.get(
            "/api/v1/analytics/wismo/inquiries",
            params={
                "store_id": str(store.id),
                "page": "2",
                "page_size": "2",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["page"] == 2
        assert data["page_size"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_page_count_calculation(
        self,
        client: AsyncClient,
        store: Store,
        order_inquiry_factory: Callable[..., Any],
    ) -> None:
        """Pages count is correctly calculated."""
        for i in range(5):
            await order_inquiry_factory(store_id=store.id, order_number=f"#100{i}")

        response = await client.get(
            "/api/v1/analytics/wismo/inquiries",
            params={
                "store_id": str(store.id),
                "page_size": "2",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pages"] == 3  # ceil(5/2)

    @pytest.mark.asyncio
    async def test_empty_results(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Returns empty paginated response when no inquiries exist."""
        response = await client.get(
            "/api/v1/analytics/wismo/inquiries",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["pages"] == 1
