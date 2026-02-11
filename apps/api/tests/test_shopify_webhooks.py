"""Tests for Shopify webhook HMAC verification and webhook routes.

Covers:
- Webhook HMAC verification (verify_webhook)
- POST /api/v1/webhooks/shopify/products-create
- POST /api/v1/webhooks/shopify/products-update
- POST /api/v1/webhooks/shopify/products-delete
- Helper function _get_store_id_from_shop
"""

import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.shopify.webhooks import verify_webhook
from app.models.integration import IntegrationStatus, PlatformType
from app.models.product import Product
from app.models.store import Store
from tests.conftest import SHOPIFY_TEST_CLIENT_SECRET, SHOPIFY_TEST_SHOP

# ---------------------------------------------------------------------------
# Unit Tests: verify_webhook
# ---------------------------------------------------------------------------


class TestVerifyWebhook:
    """Unit tests for Shopify webhook HMAC verification."""

    def _compute_signature(self, body: bytes, secret: str) -> str:
        """Compute the expected webhook signature."""
        return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()

    def test_valid_signature(self) -> None:
        """verify_webhook returns True for correctly signed body."""
        body = b'{"id": 123, "title": "Test Product"}'
        signature = self._compute_signature(body, SHOPIFY_TEST_CLIENT_SECRET)

        assert verify_webhook(body, signature, SHOPIFY_TEST_CLIENT_SECRET) is True

    def test_invalid_signature(self) -> None:
        """verify_webhook returns False for wrong signature."""
        body = b'{"id": 123}'

        assert verify_webhook(body, "invalid-signature", SHOPIFY_TEST_CLIENT_SECRET) is False

    def test_tampered_body(self) -> None:
        """verify_webhook returns False if body is modified after signing."""
        original_body = b'{"id": 123}'
        signature = self._compute_signature(original_body, SHOPIFY_TEST_CLIENT_SECRET)

        tampered_body = b'{"id": 456}'

        assert verify_webhook(tampered_body, signature, SHOPIFY_TEST_CLIENT_SECRET) is False

    def test_empty_body(self) -> None:
        """verify_webhook handles empty body correctly."""
        body = b""
        signature = self._compute_signature(body, SHOPIFY_TEST_CLIENT_SECRET)

        assert verify_webhook(body, signature, SHOPIFY_TEST_CLIENT_SECRET) is True

    def test_wrong_secret(self) -> None:
        """verify_webhook returns False with wrong secret."""
        body = b'{"id": 123}'
        signature = self._compute_signature(body, SHOPIFY_TEST_CLIENT_SECRET)

        assert verify_webhook(body, signature, "wrong-secret") is False

    def test_unicode_body(self) -> None:
        """verify_webhook handles unicode content in body."""
        body = '{"title": "日本語テスト"}'.encode()
        signature = self._compute_signature(body, SHOPIFY_TEST_CLIENT_SECRET)

        assert verify_webhook(body, signature, SHOPIFY_TEST_CLIENT_SECRET) is True

    def test_large_body(self) -> None:
        """verify_webhook handles large payloads."""
        body = b'{"data": "' + b"x" * 100000 + b'"}'
        signature = self._compute_signature(body, SHOPIFY_TEST_CLIENT_SECRET)

        assert verify_webhook(body, signature, SHOPIFY_TEST_CLIENT_SECRET) is True


# ---------------------------------------------------------------------------
# Route Tests: POST /api/v1/webhooks/shopify/products-create
# ---------------------------------------------------------------------------


class TestProductsCreateWebhook:
    """Tests for the products-create webhook endpoint."""

    async def test_rejects_invalid_hmac(self, unauthed_client: AsyncClient) -> None:
        """Returns 401 for invalid signature."""
        body = b'{"id": 123, "title": "Product"}'

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-create",
            content=body,
            headers={
                "X-Shopify-Hmac-Sha256": "invalid-signature",
                "X-Shopify-Shop-Domain": SHOPIFY_TEST_SHOP,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 401
        assert "Invalid webhook signature" in response.json()["detail"]

    async def test_rejects_missing_hmac(self, unauthed_client: AsyncClient) -> None:
        """Returns 401 if X-Shopify-Hmac-Sha256 header missing."""
        body = b'{"id": 123}'

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-create",
            content=body,
            headers={
                "X-Shopify-Shop-Domain": SHOPIFY_TEST_SHOP,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 401

    async def test_ignores_unknown_shop(
        self,
        unauthed_client: AsyncClient,
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
    ) -> None:
        """Returns {"status": "ignored"} if shop not found."""
        body = b'{"id": 123, "title": "Product"}'
        headers = shopify_webhook_headers(body, "unknown-shop.myshopify.com")

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-create",
            content=body,
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ignored"}

    async def test_dispatches_sync_task(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
        mock_celery_shopify_tasks: dict[str, MagicMock],
    ) -> None:
        """Calls sync_single_product.delay() for valid webhook."""
        await integration_factory(
            store_id=store.id,
            platform_domain=SHOPIFY_TEST_SHOP,
            status=IntegrationStatus.ACTIVE,
        )

        product_data = {"id": 12345, "title": "New Product"}
        body = json.dumps(product_data).encode()
        headers = shopify_webhook_headers(body, SHOPIFY_TEST_SHOP)

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-create",
            content=body,
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json() == {"status": "accepted"}

        mock_celery_shopify_tasks["sync_single_product"].delay.assert_called_once_with(
            str(store.id), product_data
        )

    async def test_returns_accepted(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
        _mock_celery_shopify_tasks: dict[str, MagicMock],
    ) -> None:
        """Returns {"status": "accepted"} on success."""
        await integration_factory(
            store_id=store.id,
            platform_domain=SHOPIFY_TEST_SHOP,
            status=IntegrationStatus.ACTIVE,
        )

        body = b'{"id": 123}'
        headers = shopify_webhook_headers(body, SHOPIFY_TEST_SHOP)

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-create",
            content=body,
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"


# ---------------------------------------------------------------------------
# Route Tests: POST /api/v1/webhooks/shopify/products-update
# ---------------------------------------------------------------------------


class TestProductsUpdateWebhook:
    """Tests for the products-update webhook endpoint."""

    async def test_rejects_invalid_hmac(self, unauthed_client: AsyncClient) -> None:
        """Returns 401 for invalid signature."""
        body = b'{"id": 123}'

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-update",
            content=body,
            headers={
                "X-Shopify-Hmac-Sha256": "bad-sig",
                "X-Shopify-Shop-Domain": SHOPIFY_TEST_SHOP,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 401

    async def test_ignores_unknown_shop(
        self,
        unauthed_client: AsyncClient,
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
    ) -> None:
        """Returns {"status": "ignored"} for unknown shop."""
        body = b'{"id": 123}'
        headers = shopify_webhook_headers(body, "unknown.myshopify.com")

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-update",
            content=body,
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ignored"}

    async def test_dispatches_sync_task(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
        mock_celery_shopify_tasks: dict[str, MagicMock],
    ) -> None:
        """Calls sync_single_product.delay() for valid webhook."""
        await integration_factory(
            store_id=store.id,
            platform_domain=SHOPIFY_TEST_SHOP,
            status=IntegrationStatus.ACTIVE,
        )

        product_data = {"id": 12345, "title": "Updated Product"}
        body = json.dumps(product_data).encode()
        headers = shopify_webhook_headers(body, SHOPIFY_TEST_SHOP)

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-update",
            content=body,
            headers=headers,
        )

        assert response.status_code == 200
        mock_celery_shopify_tasks["sync_single_product"].delay.assert_called_once_with(
            str(store.id), product_data
        )


# ---------------------------------------------------------------------------
# Route Tests: POST /api/v1/webhooks/shopify/products-delete
# ---------------------------------------------------------------------------


class TestProductsDeleteWebhook:
    """Tests for the products-delete webhook endpoint."""

    async def test_rejects_invalid_hmac(self, unauthed_client: AsyncClient) -> None:
        """Returns 401 for invalid signature."""
        body = b'{"id": 123}'

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-delete",
            content=body,
            headers={
                "X-Shopify-Hmac-Sha256": "bad-sig",
                "X-Shopify-Shop-Domain": SHOPIFY_TEST_SHOP,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 401

    async def test_ignores_unknown_shop(
        self,
        unauthed_client: AsyncClient,
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
    ) -> None:
        """Returns {"status": "ignored"} for unknown shop."""
        body = b'{"id": 123}'
        headers = shopify_webhook_headers(body, "unknown.myshopify.com")

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-delete",
            content=body,
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ignored"}

    async def test_deletes_product(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        product_factory: Callable[..., Any],
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
        db_session: AsyncSession,
    ) -> None:
        """Product is deleted from DB."""
        await integration_factory(
            store_id=store.id,
            platform_domain=SHOPIFY_TEST_SHOP,
            status=IntegrationStatus.ACTIVE,
        )

        # Create a product with a specific platform_product_id
        product = await product_factory(
            store_id=store.id,
            platform_product_id="12345",
            title="Product To Delete",
        )

        body = b'{"id": 12345}'
        headers = shopify_webhook_headers(body, SHOPIFY_TEST_SHOP)

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-delete",
            content=body,
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json() == {"status": "deleted"}

        # Verify product was deleted
        stmt = select(Product).where(Product.id == product.id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_handles_nonexistent_product(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
    ) -> None:
        """Returns {"status": "deleted"} even if product doesn't exist."""
        await integration_factory(
            store_id=store.id,
            platform_domain=SHOPIFY_TEST_SHOP,
            status=IntegrationStatus.ACTIVE,
        )

        body = b'{"id": 99999}'  # Non-existent product
        headers = shopify_webhook_headers(body, SHOPIFY_TEST_SHOP)

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-delete",
            content=body,
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json() == {"status": "deleted"}

    async def test_only_deletes_from_correct_store(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        store_factory: Callable[..., Any],
        integration_factory: Callable[..., Any],
        product_factory: Callable[..., Any],
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
        db_session: AsyncSession,
    ) -> None:
        """Webhook only deletes product from the matching store."""
        # Create second store with same product ID
        other_store = await store_factory(name="Other Store", organization_id="other-org")

        await integration_factory(
            store_id=store.id,
            platform_domain=SHOPIFY_TEST_SHOP,
            status=IntegrationStatus.ACTIVE,
        )
        await integration_factory(
            store_id=other_store.id,
            platform_domain="other-shop.myshopify.com",
            status=IntegrationStatus.ACTIVE,
        )

        # Both stores have a product with the same platform_product_id
        await product_factory(
            store_id=store.id,
            platform_product_id="12345",
            title="Store 1 Product",
        )
        other_product = await product_factory(
            store_id=other_store.id,
            platform_product_id="12345",
            title="Store 2 Product",
        )

        body = b'{"id": 12345}'
        headers = shopify_webhook_headers(body, SHOPIFY_TEST_SHOP)

        await unauthed_client.post(
            "/api/v1/webhooks/shopify/products-delete",
            content=body,
            headers=headers,
        )

        # Other store's product should still exist
        stmt = select(Product).where(Product.id == other_product.id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Helper Tests: _get_store_id_from_shop
# ---------------------------------------------------------------------------


class TestGetStoreIdFromShop:
    """Tests for the _get_store_id_from_shop helper function."""

    async def test_finds_active_integration(
        self,
        store: Store,
        integration_factory: Callable[..., Any],
        db_session: AsyncSession,
    ) -> None:
        """Returns store_id for active integration."""
        from app.api.v1.webhooks.shopify import _get_store_id_from_shop

        await integration_factory(
            store_id=store.id,
            platform_domain="my-shop.myshopify.com",
            status=IntegrationStatus.ACTIVE,
        )

        store_id = await _get_store_id_from_shop("my-shop.myshopify.com", db_session)

        assert store_id == store.id

    async def test_returns_none_for_disconnected(
        self,
        store: Store,
        integration_factory: Callable[..., Any],
        db_session: AsyncSession,
    ) -> None:
        """Returns None if integration is disconnected."""
        from app.api.v1.webhooks.shopify import _get_store_id_from_shop

        await integration_factory(
            store_id=store.id,
            platform_domain="my-shop.myshopify.com",
            status=IntegrationStatus.DISCONNECTED,
        )

        store_id = await _get_store_id_from_shop("my-shop.myshopify.com", db_session)

        assert store_id is None

    async def test_returns_none_for_unknown_shop(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Returns None for unknown shop domain."""
        from app.api.v1.webhooks.shopify import _get_store_id_from_shop

        store_id = await _get_store_id_from_shop("unknown.myshopify.com", db_session)

        assert store_id is None

    async def test_returns_none_for_pending_status(
        self,
        store: Store,
        integration_factory: Callable[..., Any],
        db_session: AsyncSession,
    ) -> None:
        """Returns None if integration status is PENDING."""
        from app.api.v1.webhooks.shopify import _get_store_id_from_shop

        await integration_factory(
            store_id=store.id,
            platform_domain="my-shop.myshopify.com",
            status=IntegrationStatus.PENDING,
        )

        store_id = await _get_store_id_from_shop("my-shop.myshopify.com", db_session)

        assert store_id is None

    async def test_returns_none_for_error_status(
        self,
        store: Store,
        integration_factory: Callable[..., Any],
        db_session: AsyncSession,
    ) -> None:
        """Returns None if integration status is ERROR."""
        from app.api.v1.webhooks.shopify import _get_store_id_from_shop

        await integration_factory(
            store_id=store.id,
            platform_domain="my-shop.myshopify.com",
            status=IntegrationStatus.ERROR,
        )

        store_id = await _get_store_id_from_shop("my-shop.myshopify.com", db_session)

        assert store_id is None

    async def test_only_matches_shopify_platform(
        self,
        store: Store,
        integration_factory: Callable[..., Any],
        db_session: AsyncSession,
    ) -> None:
        """Only matches integrations with platform=SHOPIFY."""
        from app.api.v1.webhooks.shopify import _get_store_id_from_shop

        await integration_factory(
            store_id=store.id,
            platform=PlatformType.WOOCOMMERCE,  # Not Shopify
            platform_domain="my-shop.myshopify.com",
            status=IntegrationStatus.ACTIVE,
        )

        store_id = await _get_store_id_from_shop("my-shop.myshopify.com", db_session)

        assert store_id is None
