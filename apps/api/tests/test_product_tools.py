"""Unit tests for product tools factory."""

import json
import uuid
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store
from app.services.recommendation_service import RecommendationService
from app.services.search_service import SearchService
from app.services.tools.product_tools import create_product_tools


@pytest.fixture
def product_tools(
    db_session: AsyncSession,
    store: Store,
    mock_embedding_service: MagicMock,  # noqa: ARG001  # Activates mock
) -> list[Any]:
    """Create product tools bound to test store."""
    search_service = SearchService(db_session)
    recommendation_service = RecommendationService(db_session)
    return create_product_tools(search_service, recommendation_service, store.id)


class TestSearchProductsTool:
    """Tests for the search_products tool."""

    @pytest.mark.asyncio
    async def test_returns_matching_products(
        self,
        product_tools: list[Any],
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding: list[float],
    ) -> None:
        """Returns products that match the search query."""
        await product_factory(
            store_id=store.id,
            title="Blue Running Shoes",
            handle="blue-shoes",
            embedding=mock_embedding,
            variants=[{"title": "Default", "price": "59.99", "inventory_quantity": 5}],
        )

        search_tool = product_tools[0]
        result = await search_tool.ainvoke({"query": "blue shoes"})
        data = json.loads(result)

        assert data["total"] >= 1
        assert data["results"][0]["title"] == "Blue Running Shoes"

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_matches(
        self,
        product_tools: list[Any],
    ) -> None:
        """Returns empty results when no products match."""
        search_tool = product_tools[0]
        result = await search_tool.ainvoke({"query": "nonexistent product xyz"})
        data = json.loads(result)

        assert data["results"] == []


class TestGetProductDetailsTool:
    """Tests for the get_product_details tool."""

    @pytest.mark.asyncio
    async def test_returns_product_details(
        self,
        product_tools: list[Any],
        store: Store,
        product_factory: Callable[..., Any],
    ) -> None:
        """Returns full product details for a valid product ID."""
        product = await product_factory(
            store_id=store.id,
            title="Test Widget",
            handle="test-widget",
            vendor="WidgetCo",
            product_type="Widgets",
            variants=[{"title": "Small", "price": "19.99", "inventory_quantity": 3}],
            images=[{"src": "https://example.com/widget.jpg"}],
        )

        details_tool = product_tools[1]
        result = await details_tool.ainvoke({"product_id": str(product.id)})
        data = json.loads(result)

        assert data["title"] == "Test Widget"
        assert data["vendor"] == "WidgetCo"
        assert len(data["variants"]) == 1
        assert data["variants"][0]["price"] == "19.99"

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_product(
        self,
        product_tools: list[Any],
    ) -> None:
        """Returns error for non-existent product ID."""
        details_tool = product_tools[1]
        result = await details_tool.ainvoke({"product_id": str(uuid.uuid4())})
        data = json.loads(result)

        assert "error" in data


class TestCheckProductAvailabilityTool:
    """Tests for the check_product_availability tool."""

    @pytest.mark.asyncio
    async def test_shows_availability(
        self,
        product_tools: list[Any],
        store: Store,
        product_factory: Callable[..., Any],
    ) -> None:
        """Shows availability status for product variants."""
        product = await product_factory(
            store_id=store.id,
            title="Available Widget",
            handle="available-widget",
            variants=[
                {"title": "Small", "price": "10.00", "inventory_quantity": 5},
                {"title": "Large", "price": "15.00", "inventory_quantity": 0},
            ],
        )

        availability_tool = product_tools[2]
        result = await availability_tool.ainvoke({"product_id": str(product.id)})
        data = json.loads(result)

        assert data["any_available"] is True
        assert len(data["variants"]) == 2

    @pytest.mark.asyncio
    async def test_filters_by_variant_title(
        self,
        product_tools: list[Any],
        store: Store,
        product_factory: Callable[..., Any],
    ) -> None:
        """Filters results to the requested variant."""
        product = await product_factory(
            store_id=store.id,
            title="Multi Variant",
            handle="multi-variant",
            variants=[
                {"title": "Small", "price": "10.00", "inventory_quantity": 5},
                {"title": "Large", "price": "15.00", "inventory_quantity": 0},
            ],
        )

        availability_tool = product_tools[2]
        result = await availability_tool.ainvoke(
            {"product_id": str(product.id), "variant_title": "Small"}
        )
        data = json.loads(result)

        assert len(data["variants"]) == 1
        assert data["variants"][0]["variant"] == "Small"


class TestCompareProductsTool:
    """Tests for the compare_products tool."""

    @pytest.mark.asyncio
    async def test_compares_products(
        self,
        product_tools: list[Any],
        store: Store,
        product_factory: Callable[..., Any],
    ) -> None:
        """Compares multiple products side by side."""
        p1 = await product_factory(
            store_id=store.id,
            title="Widget A",
            handle="widget-a",
            variants=[{"title": "Default", "price": "25.00", "inventory_quantity": 3}],
        )
        p2 = await product_factory(
            store_id=store.id,
            title="Widget B",
            handle="widget-b",
            variants=[{"title": "Default", "price": "35.00", "inventory_quantity": 1}],
        )

        compare_tool = product_tools[5]
        result = await compare_tool.ainvoke({"product_ids": [str(p1.id), str(p2.id)]})
        data = json.loads(result)

        assert data["total"] == 2
        titles = [p["title"] for p in data["products"]]
        assert "Widget A" in titles
        assert "Widget B" in titles
