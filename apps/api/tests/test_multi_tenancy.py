"""Tests for multi-tenancy isolation.

Verifies that a user in org A cannot access org B's resources across
all major API endpoints: stores, products, knowledge, conversations,
and settings.

Uses:
- ``client`` (authenticated as TEST_ORG_ID)
- ``unauthed_client`` (no auth override — real auth runs)
- ``store`` (belongs to TEST_ORG_ID)
- ``other_store`` (belongs to OTHER_ORG_ID)
"""

from typing import Any

from httpx import AsyncClient

from app.models.store import Store

# ---------------------------------------------------------------------------
# Store CRUD isolation
# ---------------------------------------------------------------------------


class TestStoreTenancy:
    """Verify store CRUD is scoped to the authenticated user's org."""

    async def test_list_stores_only_returns_own_org(
        self, client: AsyncClient, store: Store, other_store: Store
    ) -> None:
        """GET /stores only returns stores for the authed user's org."""
        response = await client.get("/api/v1/stores")
        assert response.status_code == 200

        store_ids = [s["id"] for s in response.json()["items"]]
        assert str(store.id) in store_ids
        assert str(other_store.id) not in store_ids

    async def test_get_own_store(self, client: AsyncClient, store: Store) -> None:
        """Can access a store belonging to own org."""
        response = await client.get(f"/api/v1/stores/{store.id}")
        assert response.status_code == 200
        assert response.json()["id"] == str(store.id)

    async def test_get_other_org_store_returns_404(
        self, client: AsyncClient, other_store: Store
    ) -> None:
        """Cannot access a store belonging to another org — returns 404, not 403."""
        response = await client.get(f"/api/v1/stores/{other_store.id}")
        assert response.status_code == 404

    async def test_update_other_org_store_returns_404(
        self, client: AsyncClient, other_store: Store
    ) -> None:
        """Cannot update another org's store."""
        response = await client.patch(f"/api/v1/stores/{other_store.id}", json={"name": "Hacked"})
        assert response.status_code == 404

    async def test_delete_other_org_store_returns_404(
        self, client: AsyncClient, other_store: Store
    ) -> None:
        """Cannot soft-delete another org's store."""
        response = await client.delete(f"/api/v1/stores/{other_store.id}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Products isolation
# ---------------------------------------------------------------------------


class TestProductTenancy:
    """Verify product listing is scoped to the user's org."""

    async def test_list_products_own_store(
        self, client: AsyncClient, store: Store, product_factory: Any
    ) -> None:
        """Can list products for own store."""
        await product_factory(store_id=store.id, title="My Product")
        response = await client.get("/api/v1/products/", params={"store_id": str(store.id)})
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    async def test_list_products_other_org_store_returns_404(
        self, client: AsyncClient, other_store: Store
    ) -> None:
        """Cannot list products for another org's store."""
        response = await client.get("/api/v1/products/", params={"store_id": str(other_store.id)})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Knowledge isolation
# ---------------------------------------------------------------------------


class TestKnowledgeTenancy:
    """Verify knowledge endpoints are scoped to the user's org."""

    async def test_list_knowledge_own_store(self, client: AsyncClient, store: Store) -> None:
        """Can list knowledge for own store."""
        response = await client.get("/api/v1/knowledge", params={"store_id": str(store.id)})
        assert response.status_code == 200

    async def test_list_knowledge_other_org_store_returns_404(
        self, client: AsyncClient, other_store: Store
    ) -> None:
        """Cannot list knowledge for another org's store."""
        response = await client.get("/api/v1/knowledge", params={"store_id": str(other_store.id)})
        assert response.status_code == 404

    async def test_ingest_knowledge_other_org_store_returns_404(
        self, client: AsyncClient, other_store: Store
    ) -> None:
        """Cannot ingest knowledge into another org's store."""
        response = await client.post(
            "/api/v1/knowledge",
            params={"store_id": str(other_store.id)},
            json={
                "title": "Injected Article",
                "content": "This should not be allowed.",
                "content_type": "faq",
            },
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Conversation isolation (after Fix 2)
# ---------------------------------------------------------------------------


class TestConversationTenancy:
    """Verify conversation endpoints enforce auth and org scoping."""

    async def test_list_conversations_unauthenticated_no_session_returns_401(
        self, unauthed_client: AsyncClient, store: Store
    ) -> None:
        """Unauthenticated request without session_id → 401 (Fix 2 regression)."""
        response = await unauthed_client.get(
            "/api/v1/chat/conversations", params={"store_id": str(store.id)}
        )
        assert response.status_code == 401

    async def test_list_conversations_unauthenticated_with_session(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        conversation_factory: Any,
    ) -> None:
        """Widget access: unauthenticated + session_id → only that session's conversations."""
        my_session = "widget-session-abc"
        other_session = "widget-session-xyz"

        await conversation_factory(store_id=store.id, session_id=my_session)
        await conversation_factory(store_id=store.id, session_id=other_session)

        response = await unauthed_client.get(
            "/api/v1/chat/conversations",
            params={"store_id": str(store.id), "session_id": my_session},
        )
        assert response.status_code == 200
        items = response.json()["items"]
        # Should only see conversations for my_session
        for item in items:
            assert item["session_id"] == my_session

    async def test_list_conversations_authenticated_sees_all(
        self, client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Dashboard (authenticated) can list all conversations for own store."""
        await conversation_factory(store_id=store.id, session_id="s1")
        await conversation_factory(store_id=store.id, session_id="s2")

        response = await client.get(
            "/api/v1/chat/conversations", params={"store_id": str(store.id)}
        )
        assert response.status_code == 200
        assert response.json()["total"] >= 2

    async def test_list_conversations_authenticated_other_org_returns_404(
        self, client: AsyncClient, other_store: Store
    ) -> None:
        """Authenticated user cannot list conversations for another org's store."""
        response = await client.get(
            "/api/v1/chat/conversations", params={"store_id": str(other_store.id)}
        )
        assert response.status_code == 404

    async def test_get_conversation_unauthenticated_no_session_returns_401(
        self, unauthed_client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """GET conversation without auth and without session_id → 401."""
        conv = await conversation_factory(store_id=store.id)
        response = await unauthed_client.get(
            f"/api/v1/chat/conversations/{conv.id}",
            params={"store_id": str(store.id)},
        )
        assert response.status_code == 401

    async def test_get_conversation_unauthenticated_with_correct_session(
        self, unauthed_client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Widget can access a conversation using the correct session_id."""
        conv = await conversation_factory(store_id=store.id, session_id="my-session")
        response = await unauthed_client.get(
            f"/api/v1/chat/conversations/{conv.id}",
            params={"store_id": str(store.id), "session_id": "my-session"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(conv.id)

    async def test_get_conversation_unauthenticated_with_wrong_session(
        self, unauthed_client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Widget cannot access a conversation belonging to a different session."""
        conv = await conversation_factory(store_id=store.id, session_id="session-A")
        response = await unauthed_client.get(
            f"/api/v1/chat/conversations/{conv.id}",
            params={"store_id": str(store.id), "session_id": "session-B"},
        )
        assert response.status_code == 404

    async def test_update_conversation_status_requires_auth(
        self, unauthed_client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """PATCH conversation status without auth → 401 (Fix 2 regression)."""
        conv = await conversation_factory(store_id=store.id)
        response = await unauthed_client.patch(
            f"/api/v1/chat/conversations/{conv.id}/status",
            params={"store_id": str(store.id)},
            json={"status": "resolved"},
        )
        assert response.status_code == 401

    async def test_update_conversation_status_other_org_returns_404(
        self, client: AsyncClient, other_store: Store, conversation_factory: Any
    ) -> None:
        """Cannot update conversation status for another org's store."""
        conv = await conversation_factory(store_id=other_store.id)
        response = await client.patch(
            f"/api/v1/chat/conversations/{conv.id}/status",
            params={"store_id": str(other_store.id)},
            json={"status": "resolved"},
        )
        assert response.status_code == 404

    async def test_update_conversation_status_own_store(
        self, client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Authenticated user can update conversation status for own store."""
        conv = await conversation_factory(store_id=store.id)
        response = await client.patch(
            f"/api/v1/chat/conversations/{conv.id}/status",
            params={"store_id": str(store.id)},
            json={"status": "resolved"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "resolved"


# ---------------------------------------------------------------------------
# Settings isolation (after Fix 1)
# ---------------------------------------------------------------------------


class TestSettingsTenancy:
    """Verify settings update is scoped but read is public."""

    async def test_get_settings_public_for_any_store(
        self, client: AsyncClient, other_store: Store
    ) -> None:
        """GET settings is public — even another org's store is readable."""
        response = await client.get(
            "/api/v1/stores/settings", params={"store_id": str(other_store.id)}
        )
        assert response.status_code == 200

    async def test_update_settings_other_org_returns_404(
        self, client: AsyncClient, other_store: Store
    ) -> None:
        """Cannot update settings for another org's store."""
        response = await client.patch(
            "/api/v1/stores/settings",
            params={"store_id": str(other_store.id)},
            json={"widget": {"primary_color": "#000000"}},
        )
        assert response.status_code == 404

    async def test_update_settings_unauthenticated_returns_401(
        self, unauthed_client: AsyncClient, store: Store
    ) -> None:
        """Unauthenticated settings update → 401 (Fix 1 regression)."""
        response = await unauthed_client.patch(
            "/api/v1/stores/settings",
            params={"store_id": str(store.id)},
            json={"widget": {"primary_color": "#000000"}},
        )
        assert response.status_code == 401
