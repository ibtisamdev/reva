"""Tests for the products API endpoint.

Covers:
- GET /api/v1/products/ (list products with pagination)
- Response shape validation
- Ordering, pagination boundary cases, validation

Auth enforcement is covered in test_auth.py.
Multi-tenancy isolation is covered in test_multi_tenancy.py.
"""

from typing import Any

from httpx import AsyncClient

from app.models.store import Store

# ---------------------------------------------------------------------------
# GET /api/v1/products/ (list)
# ---------------------------------------------------------------------------


class TestListProducts:
    """Tests for listing synced products."""

    async def test_list_products_empty_store(self, client: AsyncClient, store: Store) -> None:
        """Store with no products returns empty list."""
        response = await client.get("/api/v1/products/", params={"store_id": str(store.id)})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["pages"] == 0

    async def test_list_products_returns_products(
        self, client: AsyncClient, store: Store, product_factory: Any
    ) -> None:
        """Returns products with correct response shape."""
        await product_factory(store_id=store.id, title="Widget A")
        await product_factory(store_id=store.id, title="Widget B")
        await product_factory(store_id=store.id, title="Widget C")

        response = await client.get("/api/v1/products/", params={"store_id": str(store.id)})
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

        # Verify response shape of first item
        item = data["items"][0]
        expected_keys = {
            "id",
            "platform_product_id",
            "title",
            "description",
            "handle",
            "vendor",
            "product_type",
            "status",
            "tags",
            "variants",
            "images",
            "synced_at",
            "created_at",
        }
        assert expected_keys.issubset(item.keys())

    async def test_list_products_pagination_first_page(
        self, client: AsyncClient, store: Store, product_factory: Any
    ) -> None:
        """First page returns correct subset and total."""
        for i in range(5):
            await product_factory(store_id=store.id, title=f"Product {i:02d}")

        response = await client.get(
            "/api/v1/products/",
            params={"store_id": str(store.id), "page": 1, "page_size": 2},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["pages"] == 3

    async def test_list_products_pagination_last_page(
        self, client: AsyncClient, store: Store, product_factory: Any
    ) -> None:
        """Last page returns the remainder."""
        for i in range(5):
            await product_factory(store_id=store.id, title=f"Product {i:02d}")

        response = await client.get(
            "/api/v1/products/",
            params={"store_id": str(store.id), "page": 3, "page_size": 2},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 1

    async def test_list_products_ordered_by_title(
        self, client: AsyncClient, store: Store, product_factory: Any
    ) -> None:
        """Products are returned ordered by title (alphabetical)."""
        await product_factory(store_id=store.id, title="Charlie")
        await product_factory(store_id=store.id, title="Alpha")
        await product_factory(store_id=store.id, title="Bravo")

        response = await client.get("/api/v1/products/", params={"store_id": str(store.id)})
        assert response.status_code == 200

        titles = [item["title"] for item in response.json()["items"]]
        assert titles == ["Alpha", "Bravo", "Charlie"]

    async def test_list_products_requires_auth(
        self, unauthed_client: AsyncClient, store: Store
    ) -> None:
        """Unauthenticated requests are rejected."""
        response = await unauthed_client.get(
            "/api/v1/products/", params={"store_id": str(store.id)}
        )
        assert response.status_code == 401

    async def test_list_products_invalid_page_returns_422(
        self, client: AsyncClient, store: Store
    ) -> None:
        """page must be >= 1."""
        response = await client.get(
            "/api/v1/products/",
            params={"store_id": str(store.id), "page": 0},
        )
        assert response.status_code == 422

    async def test_list_products_page_size_over_limit_returns_422(
        self, client: AsyncClient, store: Store
    ) -> None:
        """page_size must be <= 100."""
        response = await client.get(
            "/api/v1/products/",
            params={"store_id": str(store.id), "page_size": 101},
        )
        assert response.status_code == 422
