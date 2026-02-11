"""Tests for store CRUD API endpoints.

Covers:
- POST /api/v1/stores (create store)
- GET /api/v1/stores (list stores)
- GET /api/v1/stores/{store_id} (get store)
- PATCH /api/v1/stores/{store_id} (update store)
- DELETE /api/v1/stores/{store_id} (soft delete)

Settings endpoints are tested in test_store_settings.py.
Auth enforcement and multi-tenancy are tested in test_auth.py and test_multi_tenancy.py.
"""

import uuid
from typing import Any

from httpx import AsyncClient

from app.models.store import Store

# ---------------------------------------------------------------------------
# POST /api/v1/stores (create)
# ---------------------------------------------------------------------------


class TestCreateStore:
    """Tests for creating a new store."""

    async def test_create_store_success(self, client: AsyncClient) -> None:
        """Creating a store with name and email returns 201 with full response shape."""
        response = await client.post(
            "/api/v1/stores",
            json={"name": "My Store", "email": "shop@example.com"},
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "My Store"
        assert data["email"] == "shop@example.com"
        assert data["plan"] == "free"
        assert data["is_active"] is True
        assert data["organization_id"] == "test-org-id"
        # UUID fields present
        assert uuid.UUID(data["id"])
        # Timestamps present and non-null
        assert data["created_at"] is not None
        assert data["updated_at"] is not None

    async def test_create_store_name_only(self, client: AsyncClient) -> None:
        """Email is optional — only name is required."""
        response = await client.post(
            "/api/v1/stores",
            json={"name": "Minimal Store"},
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Minimal Store"
        assert data["email"] is None

    async def test_create_store_missing_name_returns_422(self, client: AsyncClient) -> None:
        """Name is required — empty body fails validation."""
        response = await client.post("/api/v1/stores", json={})
        assert response.status_code == 422

    async def test_create_store_empty_name_returns_422(self, client: AsyncClient) -> None:
        """Name with min_length=1 rejects empty strings."""
        response = await client.post("/api/v1/stores", json={"name": ""})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/stores (list)
# ---------------------------------------------------------------------------


class TestListStores:
    """Tests for listing stores."""

    async def test_list_stores_returns_own_stores(
        self, client: AsyncClient, store_factory: Any
    ) -> None:
        """Lists all active stores for the authenticated user's org."""
        s1 = await store_factory(name="Store Alpha")
        s2 = await store_factory(name="Store Beta")

        response = await client.get("/api/v1/stores")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 2
        store_ids = [item["id"] for item in data["items"]]
        assert str(s1.id) in store_ids
        assert str(s2.id) in store_ids

    async def test_list_stores_excludes_inactive(
        self, client: AsyncClient, store_factory: Any
    ) -> None:
        """Soft-deleted (inactive) stores are not returned."""
        active = await store_factory(name="Active Store")
        await store_factory(name="Deleted Store", is_active=False)

        response = await client.get("/api/v1/stores")
        assert response.status_code == 200

        store_ids = [item["id"] for item in response.json()["items"]]
        assert str(active.id) in store_ids
        # Inactive store not in list
        assert response.json()["total"] == 1

    async def test_list_stores_empty_org(self, client: AsyncClient) -> None:
        """Org with no stores returns empty list."""
        response = await client.get("/api/v1/stores")
        assert response.status_code == 200
        assert response.json()["total"] == 0
        assert response.json()["items"] == []

    async def test_list_stores_response_shape(self, client: AsyncClient, store: Store) -> None:
        """Each item has the full StoreResponse shape."""
        _ = store  # Ensure a store exists in the DB
        response = await client.get("/api/v1/stores")
        assert response.status_code == 200

        item = response.json()["items"][0]
        expected_keys = {
            "id",
            "organization_id",
            "name",
            "email",
            "plan",
            "is_active",
            "created_at",
            "updated_at",
        }
        assert expected_keys.issubset(item.keys())


# ---------------------------------------------------------------------------
# GET /api/v1/stores/{store_id} (get)
# ---------------------------------------------------------------------------


class TestGetStore:
    """Tests for getting a single store."""

    async def test_get_store_success(self, client: AsyncClient, store: Store) -> None:
        """Returns the store with full response shape."""
        response = await client.get(f"/api/v1/stores/{store.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(store.id)
        assert data["name"] == store.name
        assert data["organization_id"] == store.organization_id
        assert data["plan"] == "free"
        assert data["is_active"] is True

    async def test_get_nonexistent_store_returns_404(self, client: AsyncClient) -> None:
        """Random UUID returns 404."""
        response = await client.get(f"/api/v1/stores/{uuid.uuid4()}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/v1/stores/{store_id} (update)
# ---------------------------------------------------------------------------


class TestUpdateStore:
    """Tests for updating a store."""

    async def test_update_store_name(self, client: AsyncClient, store: Store) -> None:
        """Updating name returns 200 with the new name."""
        response = await client.patch(
            f"/api/v1/stores/{store.id}",
            json={"name": "Renamed Store"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Renamed Store"
        # Email unchanged
        assert response.json()["email"] == store.email

    async def test_update_store_email(self, client: AsyncClient, store: Store) -> None:
        """Partial update — only email changes."""
        response = await client.patch(
            f"/api/v1/stores/{store.id}",
            json={"email": "new@example.com"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "new@example.com"
        assert response.json()["name"] == store.name

    async def test_update_store_nonexistent_returns_404(self, client: AsyncClient) -> None:
        """Updating a nonexistent store returns 404."""
        response = await client.patch(
            f"/api/v1/stores/{uuid.uuid4()}",
            json={"name": "Ghost"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/stores/{store_id} (soft delete)
# ---------------------------------------------------------------------------


class TestDeleteStore:
    """Tests for soft-deleting a store."""

    async def test_delete_store_returns_204(self, client: AsyncClient, store: Store) -> None:
        """Successful deletion returns 204 No Content."""
        response = await client.delete(f"/api/v1/stores/{store.id}")
        assert response.status_code == 204

    async def test_deleted_store_is_marked_inactive(
        self, client: AsyncClient, store: Store
    ) -> None:
        """After deletion, store is marked is_active=False.

        Note: get_store_for_user does not filter by is_active, so the store
        is still accessible via GET /stores/{id}. But it will be excluded
        from list_stores and get_store_by_id (widget) queries.
        """
        await client.delete(f"/api/v1/stores/{store.id}")

        get_response = await client.get(f"/api/v1/stores/{store.id}")
        assert get_response.status_code == 200
        assert get_response.json()["is_active"] is False

    async def test_deleted_store_excluded_from_list(
        self, client: AsyncClient, store: Store
    ) -> None:
        """After deletion, the store no longer appears in list."""
        await client.delete(f"/api/v1/stores/{store.id}")

        list_response = await client.get("/api/v1/stores")
        store_ids = [item["id"] for item in list_response.json()["items"]]
        assert str(store.id) not in store_ids

    async def test_delete_nonexistent_store_returns_404(self, client: AsyncClient) -> None:
        """Deleting a nonexistent store returns 404."""
        response = await client.delete(f"/api/v1/stores/{uuid.uuid4()}")
        assert response.status_code == 404
