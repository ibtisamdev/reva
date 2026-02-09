"""Tests for conversation API endpoints.

Covers:
- GET /api/v1/chat/conversations (list with pagination, filters, search)
- GET /api/v1/chat/conversations/{id} (get single conversation)
- PATCH /api/v1/chat/conversations/{id}/status (update status)

Auth/session scoping and multi-tenancy are tested in test_multi_tenancy.py.
Chat message sending is tested in test_chat_route.py.
"""

import uuid
from typing import Any

from httpx import AsyncClient

from app.models.conversation import ConversationStatus
from app.models.message import MessageRole
from app.models.store import Store

# ---------------------------------------------------------------------------
# GET /api/v1/chat/conversations (list)
# ---------------------------------------------------------------------------


class TestListConversations:
    """Tests for listing conversations (authenticated dashboard access)."""

    async def test_list_conversations_empty(self, client: AsyncClient, store: Store) -> None:
        """Store with no conversations returns empty list."""
        response = await client.get(
            "/api/v1/chat/conversations", params={"store_id": str(store.id)}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1

    async def test_list_conversations_returns_all(
        self, client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Authenticated user sees all conversations for their store."""
        await conversation_factory(store_id=store.id, session_id="s1")
        await conversation_factory(store_id=store.id, session_id="s2")
        await conversation_factory(store_id=store.id, session_id="s3")

        response = await client.get(
            "/api/v1/chat/conversations", params={"store_id": str(store.id)}
        )
        assert response.status_code == 200
        assert response.json()["total"] == 3

    async def test_list_conversations_pagination(
        self, client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Pagination returns correct page size and total."""
        for i in range(5):
            await conversation_factory(store_id=store.id, session_id=f"s{i}")

        response = await client.get(
            "/api/v1/chat/conversations",
            params={"store_id": str(store.id), "page": 1, "page_size": 2},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3

    async def test_list_conversations_filter_by_status(
        self, client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Filter by status returns only matching conversations."""
        await conversation_factory(store_id=store.id, status=ConversationStatus.ACTIVE)
        await conversation_factory(store_id=store.id, status=ConversationStatus.ACTIVE)
        await conversation_factory(store_id=store.id, status=ConversationStatus.RESOLVED)

        response = await client.get(
            "/api/v1/chat/conversations",
            params={"store_id": str(store.id), "status": "resolved"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "resolved"

    async def test_list_conversations_search_by_customer_name(
        self, client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Search matches customer name (case-insensitive)."""
        await conversation_factory(
            store_id=store.id, customer_name="Alice Smith", customer_email="alice@test.com"
        )
        await conversation_factory(
            store_id=store.id, customer_name="Bob Jones", customer_email="bob@test.com"
        )

        response = await client.get(
            "/api/v1/chat/conversations",
            params={"store_id": str(store.id), "search": "alice"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["customer_name"] == "Alice Smith"

    async def test_list_conversations_search_by_customer_email(
        self, client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Search matches customer email."""
        await conversation_factory(
            store_id=store.id, customer_name="Alice", customer_email="alice@acme.com"
        )
        await conversation_factory(
            store_id=store.id, customer_name="Bob", customer_email="bob@other.com"
        )

        response = await client.get(
            "/api/v1/chat/conversations",
            params={"store_id": str(store.id), "search": "acme.com"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["customer_email"] == "alice@acme.com"

    async def test_list_conversations_authenticated_filter_by_session(
        self, client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Authenticated user can optionally filter by session_id."""
        await conversation_factory(store_id=store.id, session_id="session-A")
        await conversation_factory(store_id=store.id, session_id="session-B")

        response = await client.get(
            "/api/v1/chat/conversations",
            params={"store_id": str(store.id), "session_id": "session-A"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["session_id"] == "session-A"

    async def test_list_conversations_includes_messages(
        self, client: AsyncClient, store: Store, conversation_factory: Any, message_factory: Any
    ) -> None:
        """Each conversation item includes its messages array."""
        conv = await conversation_factory(store_id=store.id)
        await message_factory(conversation_id=conv.id, role=MessageRole.USER, content="Hello")
        await message_factory(
            conversation_id=conv.id, role=MessageRole.ASSISTANT, content="Hi there!"
        )

        response = await client.get(
            "/api/v1/chat/conversations", params={"store_id": str(store.id)}
        )
        assert response.status_code == 200

        item = response.json()["items"][0]
        assert len(item["messages"]) == 2
        assert item["messages"][0]["role"] == "user"
        assert item["messages"][1]["role"] == "assistant"


# ---------------------------------------------------------------------------
# GET /api/v1/chat/conversations/{id} (get single)
# ---------------------------------------------------------------------------


class TestGetConversation:
    """Tests for getting a single conversation (authenticated dashboard access)."""

    async def test_get_conversation_success(
        self, client: AsyncClient, store: Store, conversation_factory: Any, message_factory: Any
    ) -> None:
        """Returns full conversation with messages and correct response shape."""
        conv = await conversation_factory(
            store_id=store.id,
            customer_name="Test Customer",
            customer_email="customer@test.com",
        )
        msg = await message_factory(
            conversation_id=conv.id, role=MessageRole.USER, content="I need help"
        )

        response = await client.get(
            f"/api/v1/chat/conversations/{conv.id}",
            params={"store_id": str(store.id)},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(conv.id)
        assert data["store_id"] == str(store.id)
        assert data["customer_name"] == "Test Customer"
        assert data["customer_email"] == "customer@test.com"
        assert data["channel"] == "widget"
        assert data["status"] == "active"
        assert data["session_id"] is not None
        assert data["created_at"] is not None
        assert data["updated_at"] is not None

        # Messages
        assert len(data["messages"]) == 1
        assert data["messages"][0]["id"] == str(msg.id)
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "I need help"
        assert data["messages"][0]["created_at"] is not None

    async def test_get_conversation_with_sources_in_messages(
        self, client: AsyncClient, store: Store, conversation_factory: Any, message_factory: Any
    ) -> None:
        """Messages with source citations are properly serialized."""
        conv = await conversation_factory(store_id=store.id)
        sources = [
            {"title": "FAQ", "url": "https://example.com/faq", "snippet": "Return policy"},
            {"title": "Guide", "url": None, "snippet": "Step 1..."},
        ]
        await message_factory(
            conversation_id=conv.id,
            role=MessageRole.ASSISTANT,
            content="Here is the answer",
            sources=sources,
        )

        response = await client.get(
            f"/api/v1/chat/conversations/{conv.id}",
            params={"store_id": str(store.id)},
        )
        assert response.status_code == 200

        msg_data = response.json()["messages"][0]
        assert len(msg_data["sources"]) == 2
        assert msg_data["sources"][0]["title"] == "FAQ"
        assert msg_data["sources"][0]["url"] == "https://example.com/faq"
        assert msg_data["sources"][1]["url"] is None

    async def test_get_conversation_nonexistent_returns_404(
        self, client: AsyncClient, store: Store
    ) -> None:
        """Random conversation UUID returns 404."""
        response = await client.get(
            f"/api/v1/chat/conversations/{uuid.uuid4()}",
            params={"store_id": str(store.id)},
        )
        assert response.status_code == 404

    async def test_get_conversation_wrong_store_returns_404(
        self,
        client: AsyncClient,
        store: Store,
        other_store: Store,
        conversation_factory: Any,
    ) -> None:
        """Conversation exists but belongs to a different store — returns 404."""
        conv = await conversation_factory(store_id=store.id)

        # Try accessing it via other_store's ID (which the authed user doesn't own,
        # but even if they did, the conversation wouldn't match)
        response = await client.get(
            f"/api/v1/chat/conversations/{conv.id}",
            params={"store_id": str(store.id)},
        )
        # This should work because conv is in store and user owns store
        assert response.status_code == 200

        # But accessing via a different store_id should fail with 404
        # because _verify_store_access checks org ownership and the
        # conversation is scoped to the correct store
        response2 = await client.get(
            f"/api/v1/chat/conversations/{conv.id}",
            params={"store_id": str(other_store.id)},
        )
        assert response2.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/v1/chat/conversations/{id}/status (update)
# ---------------------------------------------------------------------------


class TestUpdateConversationStatus:
    """Tests for updating conversation status (authenticated only)."""

    async def test_update_status_to_resolved(
        self, client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Mark an active conversation as resolved."""
        conv = await conversation_factory(store_id=store.id)

        response = await client.patch(
            f"/api/v1/chat/conversations/{conv.id}/status",
            params={"store_id": str(store.id)},
            json={"status": "resolved"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "resolved"
        assert data["id"] == str(conv.id)

    async def test_update_status_to_escalated(
        self, client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Mark an active conversation as escalated."""
        conv = await conversation_factory(store_id=store.id)

        response = await client.patch(
            f"/api/v1/chat/conversations/{conv.id}/status",
            params={"store_id": str(store.id)},
            json={"status": "escalated"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "escalated"

    async def test_update_status_response_includes_messages(
        self, client: AsyncClient, store: Store, conversation_factory: Any, message_factory: Any
    ) -> None:
        """Status update response includes the conversation's messages."""
        conv = await conversation_factory(store_id=store.id)
        await message_factory(conversation_id=conv.id, content="Help me")

        response = await client.patch(
            f"/api/v1/chat/conversations/{conv.id}/status",
            params={"store_id": str(store.id)},
            json={"status": "resolved"},
        )
        assert response.status_code == 200
        assert len(response.json()["messages"]) == 1

    async def test_update_status_invalid_value_returns_422(
        self, client: AsyncClient, store: Store, conversation_factory: Any
    ) -> None:
        """Invalid status value is rejected by Pydantic."""
        conv = await conversation_factory(store_id=store.id)

        response = await client.patch(
            f"/api/v1/chat/conversations/{conv.id}/status",
            params={"store_id": str(store.id)},
            json={"status": "closed"},
        )
        assert response.status_code == 422

    async def test_update_status_nonexistent_conversation_returns_404(
        self, client: AsyncClient, store: Store
    ) -> None:
        """Random conversation UUID returns 404."""
        response = await client.patch(
            f"/api/v1/chat/conversations/{uuid.uuid4()}/status",
            params={"store_id": str(store.id)},
            json={"status": "resolved"},
        )
        assert response.status_code == 404
