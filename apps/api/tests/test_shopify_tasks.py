"""Tests for Shopify Celery tasks.

Covers:
- Helper functions (_strip_html, product_to_text, _map_shopify_product)
- _sync_products_full_async (full product sync)
- _generate_product_embeddings_async (embedding generation)
- _sync_single_product_async (single product upsert)

We test the async implementations directly rather than the sync wrappers,
as the wrappers are just thin shells that create event loops.
"""

from datetime import UTC, datetime
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_token
from app.models.integration import IntegrationStatus, PlatformType, StoreIntegration
from app.models.product import Product
from app.models.store import Store
from app.workers.tasks.shopify import (
    _map_shopify_product,
    _strip_html,
    product_to_text,
)


# ---------------------------------------------------------------------------
# Helper Function Tests: _strip_html
# ---------------------------------------------------------------------------


class TestStripHtml:
    """Tests for HTML tag stripping."""

    def test_removes_tags(self) -> None:
        """_strip_html removes HTML tags."""
        html = "<p>Hello <strong>World</strong></p>"
        assert _strip_html(html) == "Hello World"

    def test_handles_none(self) -> None:
        """_strip_html(None) returns empty string."""
        assert _strip_html(None) == ""

    def test_handles_empty_string(self) -> None:
        """_strip_html('') returns empty string."""
        assert _strip_html("") == ""

    def test_preserves_text_content(self) -> None:
        """Plain text is preserved."""
        text = "No HTML here"
        assert _strip_html(text) == "No HTML here"

    def test_removes_nested_tags(self) -> None:
        """Handles nested tags."""
        html = "<div><p>Nested <span>content</span></p></div>"
        assert _strip_html(html) == "Nested content"

    def test_strips_whitespace(self) -> None:
        """Result is stripped of leading/trailing whitespace."""
        html = "  <p>  Text  </p>  "
        result = _strip_html(html)
        assert result == "Text"


# ---------------------------------------------------------------------------
# Helper Function Tests: product_to_text
# ---------------------------------------------------------------------------


class TestProductToText:
    """Tests for product-to-text conversion."""

    def test_basic_product(self) -> None:
        """Includes title and description."""
        product = MagicMock(spec=Product)
        product.title = "Test Product"
        product.description = "<p>A great product</p>"
        product.variants = []
        product.tags = []
        product.vendor = None
        product.product_type = None

        text = product_to_text(product)

        assert "Product: Test Product" in text
        assert "Description: A great product" in text

    def test_with_variants(self) -> None:
        """Includes price from first variant."""
        product = MagicMock(spec=Product)
        product.title = "Product"
        product.description = None
        product.variants = [
            {"title": "Small", "price": "19.99"},
            {"title": "Large", "price": "24.99"},
        ]
        product.tags = []
        product.vendor = None
        product.product_type = None

        text = product_to_text(product)

        assert "Price: $19.99" in text
        assert "Available options: Small, Large" in text

    def test_with_tags(self) -> None:
        """Includes tags."""
        product = MagicMock(spec=Product)
        product.title = "Product"
        product.description = None
        product.variants = []
        product.tags = ["sale", "featured", "new"]
        product.vendor = None
        product.product_type = None

        text = product_to_text(product)

        assert "Tags: sale, featured, new" in text

    def test_with_vendor_and_type(self) -> None:
        """Includes vendor and product type."""
        product = MagicMock(spec=Product)
        product.title = "Product"
        product.description = None
        product.variants = []
        product.tags = []
        product.vendor = "Nike"
        product.product_type = "Shoes"

        text = product_to_text(product)

        assert "Vendor: Nike" in text
        assert "Type: Shoes" in text

    def test_skips_default_title_variants(self) -> None:
        """Doesn't list 'Default Title' as an option."""
        product = MagicMock(spec=Product)
        product.title = "Product"
        product.description = None
        product.variants = [
            {"title": "Default Title", "price": "10.00"},
        ]
        product.tags = []
        product.vendor = None
        product.product_type = None

        text = product_to_text(product)

        assert "Available options" not in text

    def test_handles_empty_variants_list(self) -> None:
        """Handles empty variants list."""
        product = MagicMock(spec=Product)
        product.title = "Product"
        product.description = None
        product.variants = []
        product.tags = []
        product.vendor = None
        product.product_type = None

        text = product_to_text(product)

        assert "Price:" not in text


# ---------------------------------------------------------------------------
# Helper Function Tests: _map_shopify_product
# ---------------------------------------------------------------------------


class TestMapShopifyProduct:
    """Tests for Shopify product JSON mapping."""

    def test_maps_all_fields(self, sample_shopify_product: dict[str, Any]) -> None:
        """Maps all fields correctly."""
        store_id = UUID("12345678-1234-1234-1234-123456789012")

        result = _map_shopify_product(store_id, sample_shopify_product)

        assert result["store_id"] == store_id
        assert result["platform_product_id"] == "1234567890"
        assert result["title"] == "Test Product"
        assert result["description"] == "<p>A great product</p>"
        assert result["handle"] == "test-product"
        assert result["vendor"] == "Test Vendor"
        assert result["product_type"] == "Widget"
        assert result["status"] == "active"
        assert result["tags"] == ["sale", "featured"]
        assert len(result["variants"]) == 1
        assert len(result["images"]) == 1
        assert "synced_at" in result

    def test_handles_missing_fields(self) -> None:
        """Defaults for missing optional fields."""
        store_id = UUID("12345678-1234-1234-1234-123456789012")
        minimal_product = {
            "id": 123,
            "title": "Minimal",
            "handle": "minimal",
        }

        result = _map_shopify_product(store_id, minimal_product)

        assert result["platform_product_id"] == "123"
        assert result["title"] == "Minimal"
        assert result["description"] is None
        assert result["vendor"] is None
        assert result["product_type"] is None
        assert result["status"] == "active"
        assert result["tags"] == []
        assert result["variants"] == []
        assert result["images"] == []

    def test_parses_comma_separated_tags(self) -> None:
        """Parses comma-separated tags string."""
        store_id = UUID("12345678-1234-1234-1234-123456789012")
        product = {
            "id": 123,
            "title": "Product",
            "handle": "product",
            "tags": "  tag1  ,  tag2  ,  tag3  ",
        }

        result = _map_shopify_product(store_id, product)

        assert result["tags"] == ["tag1", "tag2", "tag3"]

    def test_handles_tags_as_list(self) -> None:
        """Handles tags already as list."""
        store_id = UUID("12345678-1234-1234-1234-123456789012")
        product = {
            "id": 123,
            "title": "Product",
            "handle": "product",
            "tags": ["tag1", "tag2"],
        }

        result = _map_shopify_product(store_id, product)

        assert result["tags"] == ["tag1", "tag2"]

    def test_handles_empty_tags_string(self) -> None:
        """Handles empty tags string."""
        store_id = UUID("12345678-1234-1234-1234-123456789012")
        product = {
            "id": 123,
            "title": "Product",
            "handle": "product",
            "tags": "",
        }

        result = _map_shopify_product(store_id, product)

        assert result["tags"] == []


# ---------------------------------------------------------------------------
# Task Tests: _sync_products_full_async
# ---------------------------------------------------------------------------


class TestSyncProductsFullAsync:
    """Tests for the full product sync async implementation."""

    async def test_no_integration_returns_skipped(
        self,
        store: Store,
        db_session: AsyncSession,
    ) -> None:
        """Returns {"status": "skipped"} if no active integration."""
        from app.workers.tasks.shopify import _sync_products_full_async

        # Patch the session maker to use our test session
        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            result = await _sync_products_full_async(store.id)

        assert result["status"] == "skipped"
        assert "no active integration" in result["reason"]

    async def test_disconnected_integration_returns_skipped(
        self,
        store: Store,
        integration_factory: Callable[..., Any],
        db_session: AsyncSession,
    ) -> None:
        """Returns {"status": "skipped"} if integration is disconnected."""
        from app.workers.tasks.shopify import _sync_products_full_async

        await integration_factory(
            store_id=store.id,
            status=IntegrationStatus.DISCONNECTED,
        )

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            result = await _sync_products_full_async(store.id)

        assert result["status"] == "skipped"

    async def test_fetches_and_upserts_products(
        self,
        store: Store,
        integration_factory: Callable[..., Any],
        sample_shopify_products: list[dict[str, Any]],
        db_session: AsyncSession,
        mock_embedding_service_for_tasks: MagicMock,
    ) -> None:
        """Fetches products from Shopify and upserts to DB."""
        from app.workers.tasks.shopify import _sync_products_full_async

        encrypted_token = encrypt_token("shpat_test_token")
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": encrypted_token},
            status=IntegrationStatus.ACTIVE,
        )

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with patch("app.workers.tasks.shopify.ShopifyClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_all_products = AsyncMock(return_value=sample_shopify_products)
                mock_client_class.return_value = mock_client

                with patch("app.workers.tasks.shopify.generate_product_embeddings") as mock_embed:
                    result = await _sync_products_full_async(store.id)

        assert result["status"] == "completed"
        assert result["products_synced"] == 3

        # Verify products were created in DB
        stmt = select(Product).where(Product.store_id == store.id)
        products_result = await db_session.execute(stmt)
        products = list(products_result.scalars().all())
        assert len(products) == 3

    async def test_triggers_embedding_task(
        self,
        store: Store,
        integration_factory: Callable[..., Any],
        db_session: AsyncSession,
    ) -> None:
        """Calls generate_product_embeddings.delay() after sync."""
        from app.workers.tasks.shopify import _sync_products_full_async

        encrypted_token = encrypt_token("shpat_test_token")
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": encrypted_token},
            status=IntegrationStatus.ACTIVE,
        )

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with patch("app.workers.tasks.shopify.ShopifyClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_all_products = AsyncMock(return_value=[])
                mock_client_class.return_value = mock_client

                with patch("app.workers.tasks.shopify.generate_product_embeddings") as mock_embed:
                    await _sync_products_full_async(store.id)

                    mock_embed.delay.assert_called_once_with(str(store.id))

    async def test_updates_last_synced_at(
        self,
        store: Store,
        integration_factory: Callable[..., Any],
        db_session: AsyncSession,
    ) -> None:
        """Updates integration.last_synced_at on success."""
        from app.workers.tasks.shopify import _sync_products_full_async

        encrypted_token = encrypt_token("shpat_test_token")
        integration = await integration_factory(
            store_id=store.id,
            credentials={"access_token": encrypted_token},
            status=IntegrationStatus.ACTIVE,
        )

        before_sync = datetime.now(UTC)

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with patch("app.workers.tasks.shopify.ShopifyClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_all_products = AsyncMock(return_value=[])
                mock_client_class.return_value = mock_client

                with patch("app.workers.tasks.shopify.generate_product_embeddings"):
                    await _sync_products_full_async(store.id)

        await db_session.refresh(integration)
        assert integration.last_synced_at is not None
        assert integration.last_synced_at >= before_sync

    async def test_handles_error_and_stores_sync_error(
        self,
        store: Store,
        integration_factory: Callable[..., Any],
        db_session: AsyncSession,
    ) -> None:
        """Stores sync_error on exception, then re-raises."""
        from app.workers.tasks.shopify import _sync_products_full_async

        encrypted_token = encrypt_token("shpat_test_token")
        integration = await integration_factory(
            store_id=store.id,
            credentials={"access_token": encrypted_token},
            status=IntegrationStatus.ACTIVE,
        )

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with patch("app.workers.tasks.shopify.ShopifyClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_all_products = AsyncMock(side_effect=Exception("Shopify API error"))
                mock_client_class.return_value = mock_client

                with pytest.raises(Exception, match="Shopify API error"):
                    await _sync_products_full_async(store.id)

        await db_session.refresh(integration)
        assert integration.sync_error is not None
        assert "Shopify API error" in integration.sync_error

    async def test_upserts_existing_products(
        self,
        store: Store,
        integration_factory: Callable[..., Any],
        product_factory: Callable[..., Any],
        db_session: AsyncSession,
    ) -> None:
        """Updates existing products instead of creating duplicates."""
        from app.workers.tasks.shopify import _sync_products_full_async

        encrypted_token = encrypt_token("shpat_test_token")
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": encrypted_token},
            status=IntegrationStatus.ACTIVE,
        )

        # Create existing product
        existing = await product_factory(
            store_id=store.id,
            platform_product_id="1001",
            title="Old Title",
        )

        updated_product = {
            "id": 1001,
            "title": "New Title",
            "body_html": "Updated description",
            "handle": "updated-handle",
            "status": "active",
        }

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with patch("app.workers.tasks.shopify.ShopifyClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_all_products = AsyncMock(return_value=[updated_product])
                mock_client_class.return_value = mock_client

                with patch("app.workers.tasks.shopify.generate_product_embeddings"):
                    await _sync_products_full_async(store.id)

        await db_session.refresh(existing)
        assert existing.title == "New Title"

        # Verify no duplicate was created
        stmt = select(Product).where(Product.store_id == store.id)
        result = await db_session.execute(stmt)
        products = list(result.scalars().all())
        assert len(products) == 1


# ---------------------------------------------------------------------------
# Task Tests: _generate_product_embeddings_async
# ---------------------------------------------------------------------------


class TestGenerateProductEmbeddingsAsync:
    """Tests for the product embedding generation async implementation."""

    async def test_empty_store(
        self,
        store: Store,
        db_session: AsyncSession,
    ) -> None:
        """Returns products_embedded: 0 if no products."""
        from app.workers.tasks.shopify import _generate_product_embeddings_async

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with patch("app.workers.tasks.shopify.get_embedding_service"):
                result = await _generate_product_embeddings_async(store.id)

        assert result["status"] == "completed"
        assert result["products_embedded"] == 0

    async def test_generates_for_all_products(
        self,
        store: Store,
        product_factory: Callable[..., Any],
        db_session: AsyncSession,
        mock_embedding: list[float],
    ) -> None:
        """Generates embeddings for all products."""
        from app.workers.tasks.shopify import _generate_product_embeddings_async

        # Create products without embeddings
        await product_factory(store_id=store.id, title="Product 1")
        await product_factory(store_id=store.id, title="Product 2")
        await product_factory(store_id=store.id, title="Product 3")

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with patch("app.workers.tasks.shopify.get_embedding_service") as mock_get:
                mock_service = MagicMock()
                mock_service.generate_embeddings_batch = AsyncMock(
                    return_value=[mock_embedding, mock_embedding, mock_embedding]
                )
                mock_get.return_value = mock_service

                result = await _generate_product_embeddings_async(store.id)

        assert result["status"] == "completed"
        assert result["products_embedded"] == 3

    async def test_saves_embeddings_to_db(
        self,
        store: Store,
        product_factory: Callable[..., Any],
        db_session: AsyncSession,
        mock_embedding: list[float],
    ) -> None:
        """Embeddings are saved to Product.embedding."""
        from app.workers.tasks.shopify import _generate_product_embeddings_async

        product = await product_factory(store_id=store.id, title="Product")
        assert product.embedding is None

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with patch("app.workers.tasks.shopify.get_embedding_service") as mock_get:
                mock_service = MagicMock()
                mock_service.generate_embeddings_batch = AsyncMock(return_value=[mock_embedding])
                mock_get.return_value = mock_service

                await _generate_product_embeddings_async(store.id)

        await db_session.refresh(product)
        assert product.embedding is not None
        assert len(product.embedding) == 1536


# ---------------------------------------------------------------------------
# Task Tests: _sync_single_product_async
# ---------------------------------------------------------------------------


class TestSyncSingleProductAsync:
    """Tests for the single product sync async implementation."""

    async def test_creates_new_product(
        self,
        store: Store,
        sample_shopify_product: dict[str, Any],
        db_session: AsyncSession,
        mock_embedding: list[float],
    ) -> None:
        """Creates product if not exists."""
        from app.workers.tasks.shopify import _sync_single_product_async

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with patch("app.workers.tasks.shopify.get_embedding_service") as mock_get:
                mock_service = MagicMock()
                mock_service.generate_embedding = AsyncMock(return_value=mock_embedding)
                mock_get.return_value = mock_service

                result = await _sync_single_product_async(store.id, sample_shopify_product)

        assert result["status"] == "completed"
        assert result["product_id"] == str(sample_shopify_product["id"])

        # Verify product was created
        stmt = select(Product).where(
            Product.store_id == store.id,
            Product.platform_product_id == str(sample_shopify_product["id"]),
        )
        db_result = await db_session.execute(stmt)
        product = db_result.scalar_one()
        assert product.title == "Test Product"

    async def test_updates_existing_product(
        self,
        store: Store,
        product_factory: Callable[..., Any],
        db_session: AsyncSession,
        mock_embedding: list[float],
    ) -> None:
        """Updates product if exists."""
        from app.workers.tasks.shopify import _sync_single_product_async

        existing = await product_factory(
            store_id=store.id,
            platform_product_id="12345",
            title="Old Title",
        )

        updated_data = {
            "id": 12345,
            "title": "Updated Title",
            "body_html": "<p>New description</p>",
            "handle": "updated",
            "status": "active",
        }

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with patch("app.workers.tasks.shopify.get_embedding_service") as mock_get:
                mock_service = MagicMock()
                mock_service.generate_embedding = AsyncMock(return_value=mock_embedding)
                mock_get.return_value = mock_service

                await _sync_single_product_async(store.id, updated_data)

        await db_session.refresh(existing)
        assert existing.title == "Updated Title"

    async def test_generates_embedding(
        self,
        store: Store,
        sample_shopify_product: dict[str, Any],
        db_session: AsyncSession,
        mock_embedding: list[float],
    ) -> None:
        """Generates and saves embedding for the product."""
        from app.workers.tasks.shopify import _sync_single_product_async

        with patch("app.workers.tasks.shopify.async_session_maker") as mock_session:
            mock_session.return_value.__aenter__.return_value = db_session

            with patch("app.workers.tasks.shopify.get_embedding_service") as mock_get:
                mock_service = MagicMock()
                mock_service.generate_embedding = AsyncMock(return_value=mock_embedding)
                mock_get.return_value = mock_service

                await _sync_single_product_async(store.id, sample_shopify_product)

                # Verify embedding service was called
                mock_service.generate_embedding.assert_called_once()

        # Verify embedding was saved
        stmt = select(Product).where(
            Product.store_id == store.id,
            Product.platform_product_id == str(sample_shopify_product["id"]),
        )
        result = await db_session.execute(stmt)
        product = result.scalar_one()
        assert product.embedding is not None
