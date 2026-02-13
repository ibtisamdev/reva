"""Unit tests for OrderService.

Tests order verification, status lookup, Shopify client creation,
order status building, and human-readable status messages.
"""

import json
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationStatus
from app.models.store import Store
from app.services.order_service import OrderService


class TestOrderServiceVerifyAndLookup:
    """Tests for OrderService.verify_and_lookup()."""

    @pytest.mark.asyncio
    async def test_happy_path_returns_verified_order(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
        sample_shopify_order: dict[str, Any],
        sample_fulfillments: list[dict[str, Any]],
    ) -> None:
        """Successful verification returns verified=True with order data."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_order_by_number.return_value = sample_shopify_order
            mock_client.get_order_fulfillments.return_value = sample_fulfillments

            service = OrderService(db_session, fake_redis)
            result = await service.verify_and_lookup(
                store.id, "#1001", "customer@example.com"
            )

        assert result.verified is True
        assert result.order is not None
        assert result.order.order_number == "#1001"
        assert result.order.email == "customer@example.com"
        assert result.message == "Order verified successfully."

    @pytest.mark.asyncio
    async def test_email_mismatch_returns_not_verified(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
        sample_shopify_order: dict[str, Any],
    ) -> None:
        """Wrong email returns verified=False with descriptive message."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_order_by_number.return_value = sample_shopify_order

            service = OrderService(db_session, fake_redis)
            result = await service.verify_and_lookup(
                store.id, "#1001", "wrong@example.com"
            )

        assert result.verified is False
        assert result.order is None
        assert "does not match" in result.message

    @pytest.mark.asyncio
    async def test_order_not_found_returns_not_verified(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
    ) -> None:
        """Non-existent order returns verified=False."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_order_by_number.return_value = None

            service = OrderService(db_session, fake_redis)
            result = await service.verify_and_lookup(
                store.id, "#9999", "customer@example.com"
            )

        assert result.verified is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_no_integration_returns_unavailable(
        self,
        db_session: AsyncSession,
        store: Store,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Store without Shopify integration returns unavailable message."""
        service = OrderService(db_session, fake_redis)
        result = await service.verify_and_lookup(
            store.id, "#1001", "customer@example.com"
        )

        assert result.verified is False
        assert "not available" in result.message.lower()

    @pytest.mark.asyncio
    async def test_redis_cache_hit_skips_shopify_api(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
        sample_shopify_order: dict[str, Any],
        sample_fulfillments: list[dict[str, Any]],
    ) -> None:
        """Cached order data is used instead of calling Shopify API."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        # Pre-populate Redis cache
        cache_key = f"order:{store.id}:1001"
        await fake_redis.set(cache_key, json.dumps(sample_shopify_order))

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_order_fulfillments.return_value = sample_fulfillments

            service = OrderService(db_session, fake_redis)
            result = await service.verify_and_lookup(
                store.id, "#1001", "customer@example.com"
            )

        # Should NOT have called get_order_by_number (cache hit)
        mock_client.get_order_by_number.assert_not_called()
        assert result.verified is True

    @pytest.mark.asyncio
    async def test_sets_redis_cache_on_shopify_fetch(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
        sample_shopify_order: dict[str, Any],
        sample_fulfillments: list[dict[str, Any]],
    ) -> None:
        """Order data is cached in Redis after Shopify fetch."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_order_by_number.return_value = sample_shopify_order
            mock_client.get_order_fulfillments.return_value = sample_fulfillments

            service = OrderService(db_session, fake_redis)
            await service.verify_and_lookup(
                store.id, "#1001", "customer@example.com"
            )

        # Verify Redis cache was set
        cache_key = f"order:{store.id}:1001"
        cached = await fake_redis.get(cache_key)
        assert cached is not None
        cached_data = json.loads(cached)
        assert cached_data["id"] == sample_shopify_order["id"]

    @pytest.mark.asyncio
    async def test_case_insensitive_email_match(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
        sample_shopify_order: dict[str, Any],
        sample_fulfillments: list[dict[str, Any]],
    ) -> None:
        """Email verification is case-insensitive."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_order_by_number.return_value = sample_shopify_order
            mock_client.get_order_fulfillments.return_value = sample_fulfillments

            service = OrderService(db_session, fake_redis)
            result = await service.verify_and_lookup(
                store.id, "#1001", "CUSTOMER@EXAMPLE.COM"
            )

        assert result.verified is True

    @pytest.mark.asyncio
    async def test_hash_prefix_stripped_for_cache_key(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
        sample_shopify_order: dict[str, Any],
        sample_fulfillments: list[dict[str, Any]],
    ) -> None:
        """Order number '#1001' and '1001' use the same cache key."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        # Pre-populate cache with key stripped of '#'
        cache_key = f"order:{store.id}:1001"
        await fake_redis.set(cache_key, json.dumps(sample_shopify_order))

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_order_fulfillments.return_value = sample_fulfillments

            service = OrderService(db_session, fake_redis)
            # Use '#1001' — should still hit cache for '1001'
            result = await service.verify_and_lookup(
                store.id, "#1001", "customer@example.com"
            )

        mock_client.get_order_by_number.assert_not_called()
        assert result.verified is True

    @pytest.mark.asyncio
    async def test_multi_tenancy_different_stores_different_cache(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
        sample_shopify_order: dict[str, Any],
    ) -> None:
        """Cache keys are scoped by store_id — different stores don't share cache."""
        # Cache order for store 1
        cache_key_store1 = f"order:{store.id}:1001"
        await fake_redis.set(cache_key_store1, json.dumps(sample_shopify_order))

        # Store 2 should NOT have cached data
        cache_key_store2 = f"order:{other_store.id}:1001"
        cached = await fake_redis.get(cache_key_store2)
        assert cached is None


class TestOrderServiceGetOrderStatus:
    """Tests for OrderService.get_order_status()."""

    @pytest.mark.asyncio
    async def test_returns_order_status(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
        sample_shopify_order: dict[str, Any],
        sample_fulfillments: list[dict[str, Any]],
    ) -> None:
        """Returns order status without email verification."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_order_by_number.return_value = sample_shopify_order
            mock_client.get_order_fulfillments.return_value = sample_fulfillments

            service = OrderService(db_session, fake_redis)
            result = await service.get_order_status(store.id, "#1001")

        assert result is not None
        assert result.order_number == "#1001"
        assert result.financial_status == "paid"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
    ) -> None:
        """Returns None when order doesn't exist."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_order_by_number.return_value = None

            service = OrderService(db_session, fake_redis)
            result = await service.get_order_status(store.id, "#9999")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_integration(
        self,
        db_session: AsyncSession,
        store: Store,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Returns None when store has no Shopify integration."""
        service = OrderService(db_session, fake_redis)
        result = await service.get_order_status(store.id, "#1001")
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_cache_when_available(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
        sample_shopify_order: dict[str, Any],
        sample_fulfillments: list[dict[str, Any]],
    ) -> None:
        """Uses cached order data from Redis."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        # Pre-populate cache
        cache_key = f"order:{store.id}:1001"
        await fake_redis.set(cache_key, json.dumps(sample_shopify_order))

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_order_fulfillments.return_value = sample_fulfillments

            service = OrderService(db_session, fake_redis)
            result = await service.get_order_status(store.id, "#1001")

        mock_client.get_order_by_number.assert_not_called()
        assert result is not None

    @pytest.mark.asyncio
    async def test_caches_order_on_fetch(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
        sample_shopify_order: dict[str, Any],
        sample_fulfillments: list[dict[str, Any]],
    ) -> None:
        """Order data is cached in Redis after fetch."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_order_by_number.return_value = sample_shopify_order
            mock_client.get_order_fulfillments.return_value = sample_fulfillments

            service = OrderService(db_session, fake_redis)
            await service.get_order_status(store.id, "#1001")

        cached = await fake_redis.get(f"order:{store.id}:1001")
        assert cached is not None


class TestOrderServiceGetShopifyClient:
    """Tests for OrderService._get_shopify_client()."""

    @pytest.mark.asyncio
    async def test_returns_client_for_active_integration(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
        mock_decrypt_token: MagicMock,
    ) -> None:
        """Returns ShopifyClient when active integration exists."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "encrypted_token"},
        )

        with patch("app.services.order_service.ShopifyClient") as mock_client_cls:
            service = OrderService(db_session, fake_redis)
            result = await service._get_shopify_client(store.id)

        assert result is not None
        mock_client_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_integration(
        self,
        db_session: AsyncSession,
        store: Store,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Returns None when no integration exists."""
        service = OrderService(db_session, fake_redis)
        result = await service._get_shopify_client(store.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_inactive_integration(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Returns None when integration is not active."""
        await integration_factory(
            store_id=store.id,
            status=IntegrationStatus.DISCONNECTED,
            credentials={"access_token": "encrypted_token"},
        )

        service = OrderService(db_session, fake_redis)
        result = await service._get_shopify_client(store.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_decrypt_failure(
        self,
        db_session: AsyncSession,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Returns None when token decryption fails."""
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": "bad_encrypted_token"},
        )

        with patch(
            "app.services.order_service.decrypt_token",
            side_effect=Exception("Decryption failed"),
        ):
            service = OrderService(db_session, fake_redis)
            result = await service._get_shopify_client(store.id)

        assert result is None


class TestOrderServiceBuildOrderStatus:
    """Tests for OrderService._build_order_status()."""

    def test_complete_data(
        self,
        sample_shopify_order: dict[str, Any],
        sample_fulfillments: list[dict[str, Any]],
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Parses complete order data into OrderStatusResponse."""
        service = OrderService(MagicMock(), fake_redis)
        result = service._build_order_status(sample_shopify_order, sample_fulfillments)

        assert result.order_number == "#1001"
        assert result.order_id == 5551234567890
        assert result.email == "customer@example.com"
        assert result.financial_status == "paid"
        assert result.total_price == "79.98"
        assert result.currency == "USD"
        assert result.customer_name == "Jane Doe"
        assert result.shipping_city == "New York"
        assert result.shipping_province == "NY"
        assert len(result.line_items) == 1
        assert result.line_items[0].title == "Widget Pro"
        assert result.line_items[0].quantity == 2
        assert len(result.fulfillments) == 1
        assert result.fulfillments[0].tracking_number == "1Z999AA10123456784"

    def test_no_fulfillments(
        self,
        sample_shopify_order: dict[str, Any],
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Handles order with no fulfillments."""
        service = OrderService(MagicMock(), fake_redis)
        result = service._build_order_status(sample_shopify_order, [])

        assert result.fulfillments == []
        assert result.fulfillment_status is None

    def test_partial_data_no_shipping_address(
        self,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Handles order without shipping address."""
        order_data = {
            "id": 123,
            "name": "#1002",
            "email": "test@test.com",
            "financial_status": "paid",
            "fulfillment_status": None,
            "created_at": "2024-01-01T00:00:00Z",
            "total_price": "10.00",
            "currency": "USD",
            "line_items": [],
            "shipping_address": None,
            "customer": None,
            "cancelled_at": None,
        }

        service = OrderService(MagicMock(), fake_redis)
        result = service._build_order_status(order_data, [])

        assert result.shipping_city is None
        assert result.shipping_province is None
        assert result.customer_name is None

    def test_customer_first_name_only(
        self,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Customer with only first name."""
        order_data = {
            "id": 123,
            "name": "#1003",
            "email": "test@test.com",
            "financial_status": "paid",
            "fulfillment_status": None,
            "created_at": "2024-01-01T00:00:00Z",
            "total_price": "10.00",
            "currency": "USD",
            "line_items": [],
            "customer": {"first_name": "Jane", "last_name": ""},
        }

        service = OrderService(MagicMock(), fake_redis)
        result = service._build_order_status(order_data, [])

        assert result.customer_name == "Jane"

    def test_customer_last_name_only(
        self,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Customer with only last name."""
        order_data = {
            "id": 123,
            "name": "#1004",
            "email": "test@test.com",
            "financial_status": "paid",
            "fulfillment_status": None,
            "created_at": "2024-01-01T00:00:00Z",
            "total_price": "10.00",
            "currency": "USD",
            "line_items": [],
            "customer": {"first_name": "", "last_name": "Doe"},
        }

        service = OrderService(MagicMock(), fake_redis)
        result = service._build_order_status(order_data, [])

        assert result.customer_name == "Doe"

    def test_no_customer_data(
        self,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Customer with no name fields."""
        order_data = {
            "id": 123,
            "name": "#1005",
            "email": "test@test.com",
            "financial_status": "paid",
            "fulfillment_status": None,
            "created_at": "2024-01-01T00:00:00Z",
            "total_price": "10.00",
            "currency": "USD",
            "line_items": [],
            "customer": {"first_name": "", "last_name": ""},
        }

        service = OrderService(MagicMock(), fake_redis)
        result = service._build_order_status(order_data, [])

        assert result.customer_name is None


class TestOrderServiceGetStatusMessage:
    """Tests for OrderService._get_status_message()."""

    def _get_msg(self, order_data: dict[str, Any], fulfillments: list[dict[str, Any]] | None = None) -> str:
        service = OrderService(MagicMock(), MagicMock())
        return service._get_status_message(order_data, fulfillments or [])

    def test_cancelled_order(self) -> None:
        assert "cancelled" in self._get_msg(
            {"financial_status": "paid", "fulfillment_status": None, "cancelled_at": "2024-01-01"}
        ).lower()

    def test_refunded_order(self) -> None:
        assert "fully refunded" in self._get_msg(
            {"financial_status": "refunded", "fulfillment_status": None, "cancelled_at": None}
        ).lower()

    def test_partially_refunded_order(self) -> None:
        assert "partially refunded" in self._get_msg(
            {"financial_status": "partially_refunded", "fulfillment_status": None, "cancelled_at": None}
        ).lower()

    def test_paid_unfulfilled(self) -> None:
        msg = self._get_msg(
            {"financial_status": "paid", "fulfillment_status": None, "cancelled_at": None}
        )
        assert "confirmed" in msg.lower()
        assert "prepared" in msg.lower() or "shipment" in msg.lower()

    def test_pending_payment(self) -> None:
        msg = self._get_msg(
            {"financial_status": "pending", "fulfillment_status": None, "cancelled_at": None}
        )
        assert "awaiting payment" in msg.lower()

    def test_authorized_payment(self) -> None:
        msg = self._get_msg(
            {"financial_status": "authorized", "fulfillment_status": None, "cancelled_at": None}
        )
        assert "authorized" in msg.lower()

    def test_unknown_financial_unfulfilled(self) -> None:
        msg = self._get_msg(
            {"financial_status": "voided", "fulfillment_status": None, "cancelled_at": None}
        )
        assert "processed" in msg.lower()

    def test_partial_fulfillment(self) -> None:
        msg = self._get_msg(
            {"financial_status": "paid", "fulfillment_status": "partial", "cancelled_at": None},
            [{"tracking_number": "123"}],
        )
        assert "partially shipped" in msg.lower()
        assert "1 shipment" in msg.lower()

    def test_partial_fulfillment_multiple_shipments(self) -> None:
        msg = self._get_msg(
            {"financial_status": "paid", "fulfillment_status": "partial", "cancelled_at": None},
            [{"tracking_number": "123"}, {"tracking_number": "456"}],
        )
        assert "2 shipments" in msg.lower()

    def test_fulfilled_with_tracking(self) -> None:
        msg = self._get_msg(
            {"financial_status": "paid", "fulfillment_status": "fulfilled", "cancelled_at": None},
            [{"tracking_number": "1Z999", "tracking_company": "UPS"}],
        )
        assert "shipped" in msg.lower()
        assert "UPS" in msg
        assert "1Z999" in msg

    def test_fulfilled_without_tracking(self) -> None:
        msg = self._get_msg(
            {"financial_status": "paid", "fulfillment_status": "fulfilled", "cancelled_at": None},
            [{"tracking_number": None, "tracking_company": None}],
        )
        assert "shipped" in msg.lower()

    def test_fulfilled_no_fulfillment_records(self) -> None:
        msg = self._get_msg(
            {"financial_status": "paid", "fulfillment_status": "fulfilled", "cancelled_at": None},
            [],
        )
        assert "shipped" in msg.lower()

    def test_default_status(self) -> None:
        msg = self._get_msg(
            {"financial_status": "paid", "fulfillment_status": "restocked", "cancelled_at": None},
        )
        assert "processed" in msg.lower()
