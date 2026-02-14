"""Unit tests for SearchService hybrid search."""

import uuid
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.store import Store
from app.schemas.search import ProductFilters
from app.services.search_service import SearchService


class TestHybridSearch:
    """Tests for SearchService.hybrid_search()."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_products(
        self,
        db_session: AsyncSession,
        store: Store,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Returns empty list when no products exist."""
        service = SearchService(db_session)
        results = await service.hybrid_search("red shoes", store.id)
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_matching_products_by_vector(
        self,
        db_session: AsyncSession,
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding: list[float],
        mock_embedding_service: MagicMock,
    ) -> None:
        """Returns products matching by vector similarity."""
        await product_factory(
            store_id=store.id,
            title="Red Running Shoes",
            description="Comfortable red running shoes for everyday use",
            handle="red-running-shoes",
            embedding=mock_embedding,
            variants=[{"title": "Size 10", "price": "49.99", "inventory_quantity": 5}],
        )

        service = SearchService(db_session)
        results = await service.hybrid_search("red shoes", store.id)

        assert len(results) >= 1
        assert results[0].title == "Red Running Shoes"
        assert results[0].price == "49.99"

    @pytest.mark.asyncio
    async def test_respects_store_isolation(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        product_factory: Callable[..., Any],
        mock_embedding: list[float],
        mock_embedding_service: MagicMock,
    ) -> None:
        """Products from other stores are never returned."""
        await product_factory(
            store_id=other_store.id,
            title="Other Store Product",
            handle="other-product",
            embedding=mock_embedding,
            variants=[{"title": "Default", "price": "29.99", "inventory_quantity": 10}],
        )

        service = SearchService(db_session)
        results = await service.hybrid_search("product", store.id)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_excludes_inactive_products(
        self,
        db_session: AsyncSession,
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding: list[float],
        mock_embedding_service: MagicMock,
    ) -> None:
        """Inactive (draft/archived) products are excluded."""
        await product_factory(
            store_id=store.id,
            title="Draft Product",
            handle="draft-product",
            status="draft",
            embedding=mock_embedding,
            variants=[{"title": "Default", "price": "19.99", "inventory_quantity": 5}],
        )

        service = SearchService(db_session)
        results = await service.hybrid_search("product", store.id)

        assert len(results) == 0


class TestApplyFilters:
    """Tests for SearchService._apply_filters()."""

    @pytest.mark.asyncio
    async def test_price_max_filter(
        self,
        db_session: AsyncSession,
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding: list[float],
        mock_embedding_service: MagicMock,
    ) -> None:
        """Price max filter excludes expensive products."""
        await product_factory(
            store_id=store.id,
            title="Cheap Shoes",
            handle="cheap-shoes",
            embedding=mock_embedding,
            variants=[{"title": "Default", "price": "29.99", "inventory_quantity": 5}],
        )
        await product_factory(
            store_id=store.id,
            title="Expensive Shoes",
            handle="expensive-shoes",
            embedding=mock_embedding,
            variants=[{"title": "Default", "price": "199.99", "inventory_quantity": 5}],
        )

        service = SearchService(db_session)
        filters = ProductFilters(price_max=50.0, in_stock_only=False)
        results = await service.hybrid_search("shoes", store.id, filters=filters)

        titles = [r.title for r in results]
        assert "Cheap Shoes" in titles
        assert "Expensive Shoes" not in titles


class TestProductToSearchResult:
    """Tests for SearchService._product_to_search_result()."""

    def test_extracts_price_from_first_variant(self) -> None:
        """Extracts price from the first variant."""
        product = MagicMock(spec=Product)
        product.id = uuid.uuid4()
        product.title = "Test Product"
        product.description = "A test product"
        product.vendor = "Test Vendor"
        product.product_type = "Widget"
        product.tags = ["sale"]
        product.handle = "test-product"
        product.variants = [
            {"title": "Small", "price": "19.99", "inventory_quantity": 5},
            {"title": "Large", "price": "24.99", "inventory_quantity": 0},
        ]
        product.images = [{"src": "https://example.com/image.jpg"}]

        result = SearchService._product_to_search_result(product, 0.85)

        assert result.price == "19.99"
        assert result.in_stock is True
        assert result.image_url == "https://example.com/image.jpg"
        assert result.score == 0.85

    def test_handles_empty_variants(self) -> None:
        """Handles products with no variants."""
        product = MagicMock(spec=Product)
        product.id = uuid.uuid4()
        product.title = "No Variants"
        product.description = None
        product.vendor = None
        product.product_type = None
        product.tags = []
        product.handle = "no-variants"
        product.variants = []
        product.images = []

        result = SearchService._product_to_search_result(product, 0.5)

        assert result.price is None
        assert result.in_stock is False
        assert result.image_url is None


class TestRRF:
    """Tests for Reciprocal Rank Fusion."""

    def test_combines_results_from_two_lists(self) -> None:
        """RRF merges and reranks results from two lists."""
        from app.schemas.search import ProductSearchResult

        vector_results = [
            ProductSearchResult(
                product_id="1",
                title="Product A",
                score=0.9,
            ),
            ProductSearchResult(
                product_id="2",
                title="Product B",
                score=0.8,
            ),
        ]
        fulltext_results = [
            ProductSearchResult(
                product_id="2",
                title="Product B",
                score=0.95,
            ),
            ProductSearchResult(
                product_id="3",
                title="Product C",
                score=0.7,
            ),
        ]

        service = SearchService(MagicMock())
        combined = service._reciprocal_rank_fusion(vector_results, fulltext_results)

        # Product B appears in both lists → should rank highest
        assert combined[0].product_id == "2"
        assert len(combined) == 3

    def test_handles_empty_lists(self) -> None:
        """Handles empty result lists gracefully."""
        service = SearchService(MagicMock())
        combined = service._reciprocal_rank_fusion([], [])
        assert combined == []
