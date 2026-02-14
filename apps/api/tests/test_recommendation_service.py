"""Unit tests for RecommendationService."""

import uuid
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store
from app.services.recommendation_service import RecommendationService


class TestGetSimilarProducts:
    """Tests for RecommendationService.get_similar_products()."""

    @pytest.mark.asyncio
    async def test_returns_similar_products(
        self,
        db_session: AsyncSession,
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding: list[float],
        mock_embedding_service: MagicMock,
    ) -> None:
        """Returns products with similar embeddings."""
        source = await product_factory(
            store_id=store.id,
            title="Source Product",
            handle="source-product",
            embedding=mock_embedding,
            variants=[{"title": "Default", "price": "50.00", "inventory_quantity": 10}],
        )
        await product_factory(
            store_id=store.id,
            title="Similar Product",
            handle="similar-product",
            embedding=mock_embedding,
            variants=[{"title": "Default", "price": "55.00", "inventory_quantity": 5}],
        )

        service = RecommendationService(db_session)
        results = await service.get_similar_products(source.id, store.id)

        assert len(results) >= 1
        assert results[0].title == "Similar Product"

    @pytest.mark.asyncio
    async def test_excludes_source_product(
        self,
        db_session: AsyncSession,
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding: list[float],
        mock_embedding_service: MagicMock,
    ) -> None:
        """The source product is never included in similar results."""
        source = await product_factory(
            store_id=store.id,
            title="Source Product",
            handle="source-product",
            embedding=mock_embedding,
        )

        service = RecommendationService(db_session)
        results = await service.get_similar_products(source.id, store.id)

        source_ids = [r.product_id for r in results]
        assert str(source.id) not in source_ids

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_embedding(
        self,
        db_session: AsyncSession,
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding_service: MagicMock,
    ) -> None:
        """Returns empty list when source product has no embedding."""
        source = await product_factory(
            store_id=store.id,
            title="No Embedding Product",
            handle="no-embedding",
            embedding=None,
        )

        service = RecommendationService(db_session)
        results = await service.get_similar_products(source.id, store.id)

        assert results == []

    @pytest.mark.asyncio
    async def test_respects_store_boundary(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        product_factory: Callable[..., Any],
        mock_embedding: list[float],
        mock_embedding_service: MagicMock,
    ) -> None:
        """Never returns products from other stores."""
        source = await product_factory(
            store_id=store.id,
            title="Source",
            handle="source",
            embedding=mock_embedding,
        )
        await product_factory(
            store_id=other_store.id,
            title="Other Store Product",
            handle="other-product",
            embedding=mock_embedding,
        )

        service = RecommendationService(db_session)
        results = await service.get_similar_products(source.id, store.id)

        for r in results:
            assert r.title != "Other Store Product"


class TestGetUpsellProducts:
    """Tests for RecommendationService.get_upsell_products()."""

    @pytest.mark.asyncio
    async def test_returns_higher_priced_same_category(
        self,
        db_session: AsyncSession,
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding_service: MagicMock,
    ) -> None:
        """Returns products that are 10-30% more expensive in the same category."""
        source = await product_factory(
            store_id=store.id,
            title="Basic Widget",
            handle="basic-widget",
            product_type="Widgets",
            variants=[{"title": "Default", "price": "100.00", "inventory_quantity": 10}],
        )
        # 15% more expensive, same category = valid upsell
        await product_factory(
            store_id=store.id,
            title="Premium Widget",
            handle="premium-widget",
            product_type="Widgets",
            variants=[{"title": "Default", "price": "115.00", "inventory_quantity": 5}],
        )
        # 50% more expensive = too much for upsell
        await product_factory(
            store_id=store.id,
            title="Luxury Widget",
            handle="luxury-widget",
            product_type="Widgets",
            variants=[{"title": "Default", "price": "150.00", "inventory_quantity": 3}],
        )

        service = RecommendationService(db_session)
        results = await service.get_upsell_products(source.id, store.id)

        titles = [r.title for r in results]
        assert "Premium Widget" in titles
        assert "Luxury Widget" not in titles


class TestGetCrossSellProducts:
    """Tests for RecommendationService.get_cross_sell_products()."""

    @pytest.mark.asyncio
    async def test_returns_products_with_overlapping_tags(
        self,
        db_session: AsyncSession,
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding_service: MagicMock,
    ) -> None:
        """Returns products with overlapping tags but different types."""
        source = await product_factory(
            store_id=store.id,
            title="Running Shoes",
            handle="running-shoes",
            product_type="Shoes",
            tags=["running", "fitness", "outdoor"],
        )
        # Same tags, different type = valid cross-sell
        await product_factory(
            store_id=store.id,
            title="Running Socks",
            handle="running-socks",
            product_type="Accessories",
            tags=["running", "fitness"],
        )

        service = RecommendationService(db_session)
        results = await service.get_cross_sell_products(source.id, store.id)

        assert len(results) >= 1
        assert results[0].title == "Running Socks"


class TestCompareProducts:
    """Tests for RecommendationService.compare_products()."""

    @pytest.mark.asyncio
    async def test_compares_multiple_products(
        self,
        db_session: AsyncSession,
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding_service: MagicMock,
    ) -> None:
        """Returns comparison data for multiple products."""
        p1 = await product_factory(
            store_id=store.id,
            title="Product A",
            handle="product-a",
            variants=[{"title": "Default", "price": "50.00", "inventory_quantity": 5}],
        )
        p2 = await product_factory(
            store_id=store.id,
            title="Product B",
            handle="product-b",
            variants=[{"title": "Default", "price": "75.00", "inventory_quantity": 0}],
        )

        service = RecommendationService(db_session)
        comparison = await service.compare_products([p1.id, p2.id], store.id)

        assert comparison["total"] == 2
        assert len(comparison["products"]) == 2

        titles = [p["title"] for p in comparison["products"]]
        assert "Product A" in titles
        assert "Product B" in titles

    @pytest.mark.asyncio
    async def test_returns_error_for_no_products(
        self,
        db_session: AsyncSession,
        store: Store,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Returns error when no product IDs match."""
        service = RecommendationService(db_session)
        comparison = await service.compare_products([uuid.uuid4(), uuid.uuid4()], store.id)

        assert comparison["products"] == []


class TestExtractPrice:
    """Tests for RecommendationService._extract_price()."""

    def test_extracts_price_from_first_variant(self) -> None:
        product = MagicMock()
        product.variants = [{"price": "29.99"}]
        assert RecommendationService._extract_price(product) == 29.99

    def test_returns_none_for_empty_variants(self) -> None:
        product = MagicMock()
        product.variants = []
        assert RecommendationService._extract_price(product) is None

    def test_returns_none_for_no_variants(self) -> None:
        product = MagicMock()
        product.variants = None
        assert RecommendationService._extract_price(product) is None
