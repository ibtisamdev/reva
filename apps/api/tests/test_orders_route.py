"""Tests for order verification API endpoints.

Covers POST /api/v1/orders/verify endpoint: success, validation, auth, errors.
"""

import uuid
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.store import Store
from app.schemas.order import OrderStatusResponse, OrderVerificationResponse


class TestVerifyOrderEndpoint:
    """Tests for POST /api/v1/orders/verify."""

    @pytest.mark.asyncio
    async def test_success_returns_verified_order(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        mock_decrypt_token: MagicMock,
    ) -> None:
        """Successful verification returns 200 with verified=True."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        mock_verification = OrderVerificationResponse(
            verified=True,
            order=OrderStatusResponse(
                order_number="#1001",
                order_id=123,
                email="customer@example.com",
                financial_status="paid",
                fulfillment_status=None,
                created_at="2024-01-01T00:00:00Z",
                total_price="79.98",
                currency="USD",
                line_items=[],
                fulfillments=[],
                status_message="Your order is confirmed.",
            ),
            message="Order verified successfully.",
        )

        with patch("app.api.v1.orders.OrderService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service_cls.return_value = mock_service
            mock_service.verify_and_lookup.return_value = mock_verification

            response = await unauthed_client.post(
                "/api/v1/orders/verify",
                params={"store_id": str(store.id)},
                json={"order_number": "#1001", "email": "customer@example.com"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is True
        assert data["order"]["order_number"] == "#1001"

    @pytest.mark.asyncio
    async def test_email_mismatch_returns_not_verified(
        self,
        unauthed_client: AsyncClient,
        store: Store,
    ) -> None:
        """Email mismatch returns 200 with verified=False (not an HTTP error)."""
        mock_verification = OrderVerificationResponse(
            verified=False,
            message="The email address does not match our records for this order.",
        )

        with patch("app.api.v1.orders.OrderService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service_cls.return_value = mock_service
            mock_service.verify_and_lookup.return_value = mock_verification

            response = await unauthed_client.post(
                "/api/v1/orders/verify",
                params={"store_id": str(store.id)},
                json={"order_number": "#1001", "email": "wrong@example.com"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is False
        assert "does not match" in data["message"]

    @pytest.mark.asyncio
    async def test_order_not_found(
        self,
        unauthed_client: AsyncClient,
        store: Store,
    ) -> None:
        """Non-existent order returns 200 with verified=False."""
        mock_verification = OrderVerificationResponse(
            verified=False,
            message="Order not found. Please check the order number and try again.",
        )

        with patch("app.api.v1.orders.OrderService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service_cls.return_value = mock_service
            mock_service.verify_and_lookup.return_value = mock_verification

            response = await unauthed_client.post(
                "/api/v1/orders/verify",
                params={"store_id": str(store.id)},
                json={"order_number": "#9999", "email": "test@test.com"},
            )

        assert response.status_code == 200
        assert response.json()["verified"] is False

    @pytest.mark.asyncio
    async def test_invalid_store_returns_404(
        self,
        unauthed_client: AsyncClient,
    ) -> None:
        """Non-existent store_id returns 404."""
        response = await unauthed_client.post(
            "/api/v1/orders/verify",
            params={"store_id": str(uuid.uuid4())},
            json={"order_number": "#1001", "email": "test@test.com"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_missing_fields_returns_422(
        self,
        unauthed_client: AsyncClient,
        store: Store,
    ) -> None:
        """Missing required fields returns 422 validation error."""
        response = await unauthed_client.post(
            "/api/v1/orders/verify",
            params={"store_id": str(store.id)},
            json={"order_number": "#1001"},  # Missing 'email'
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_no_integration_returns_not_available(
        self,
        unauthed_client: AsyncClient,
        store: Store,
    ) -> None:
        """Store without integration returns unavailable message."""
        mock_verification = OrderVerificationResponse(
            verified=False,
            message="Order lookup is not available for this store.",
        )

        with patch("app.api.v1.orders.OrderService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service_cls.return_value = mock_service
            mock_service.verify_and_lookup.return_value = mock_verification

            response = await unauthed_client.post(
                "/api/v1/orders/verify",
                params={"store_id": str(store.id)},
                json={"order_number": "#1001", "email": "test@test.com"},
            )

        assert response.status_code == 200
        assert "not available" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_inactive_store_returns_404(
        self,
        unauthed_client: AsyncClient,
        store_factory: Callable[..., Any],
    ) -> None:
        """Inactive store returns 404."""
        inactive_store = await store_factory(name="Inactive", is_active=False)

        response = await unauthed_client.post(
            "/api/v1/orders/verify",
            params={"store_id": str(inactive_store.id)},
            json={"order_number": "#1001", "email": "test@test.com"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_missing_store_id_returns_422(
        self,
        unauthed_client: AsyncClient,
    ) -> None:
        """Missing store_id query parameter returns 422."""
        response = await unauthed_client.post(
            "/api/v1/orders/verify",
            json={"order_number": "#1001", "email": "test@test.com"},
        )

        assert response.status_code == 422
