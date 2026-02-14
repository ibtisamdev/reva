"""Tests for chat API endpoints.

Covers:
- POST /api/v1/chat/messages (send message, get AI response)
- Conversation creation and continuation
- Input validation
- Error handling
"""

import uuid
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.store import Store


class TestSendMessage:
    """Tests for POST /api/v1/chat/messages endpoint."""

    @pytest.mark.asyncio
    async def test_creates_conversation_and_returns_response(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """First message creates a new conversation and returns AI response."""
        response = await unauthed_client.post(
            "/api/v1/chat/messages",
            params={"store_id": str(store.id)},
            json={"message": "What is your return policy?"},
        )

        assert response.status_code == 201
        data = response.json()

        assert "conversation_id" in data
        assert "message_id" in data
        assert "response" in data
        assert data["response"] == "This is a mock AI response for testing."
        assert "sources" in data
        assert isinstance(data["sources"], list)
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_continues_existing_conversation(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        conversation_factory: Callable[..., Any],
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Message with conversation_id continues existing conversation."""
        existing_conv = await conversation_factory(store_id=store.id)

        response = await unauthed_client.post(
            "/api/v1/chat/messages",
            params={"store_id": str(store.id)},
            json={
                "message": "Follow-up question about shipping",
                "conversation_id": str(existing_conv.id),
            },
        )

        assert response.status_code == 201
        assert response.json()["conversation_id"] == str(existing_conv.id)

    @pytest.mark.asyncio
    async def test_with_session_id(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Session ID is preserved for widget tracking."""
        response = await unauthed_client.post(
            "/api/v1/chat/messages",
            params={"store_id": str(store.id)},
            json={
                "message": "Hello from the widget",
                "session_id": "widget-session-abc123",
            },
        )

        assert response.status_code == 201
        # Session ID is used internally; verify conversation was created
        assert response.json()["conversation_id"] is not None

    @pytest.mark.asyncio
    async def test_with_context_data(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Context data (page URL, etc.) is accepted."""
        response = await unauthed_client.post(
            "/api/v1/chat/messages",
            params={"store_id": str(store.id)},
            json={
                "message": "Tell me about this product",
                "context": {
                    "page_url": "/products/widget-pro",
                    "product_id": "12345",
                },
            },
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_invalid_store_returns_404(
        self,
        unauthed_client: AsyncClient,
    ) -> None:
        """Non-existent store_id returns 404."""
        response = await unauthed_client.post(
            "/api/v1/chat/messages",
            params={"store_id": str(uuid.uuid4())},
            json={"message": "Hello"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_inactive_store_returns_404(
        self,
        unauthed_client: AsyncClient,
        store_factory: Callable[..., Any],
    ) -> None:
        """Inactive store returns 404."""
        inactive_store = await store_factory(name="Inactive Store", is_active=False)

        response = await unauthed_client.post(
            "/api/v1/chat/messages",
            params={"store_id": str(inactive_store.id)},
            json={"message": "Hello"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_message_returns_422(
        self,
        unauthed_client: AsyncClient,
        store: Store,
    ) -> None:
        """Empty message fails Pydantic validation."""
        response = await unauthed_client.post(
            "/api/v1/chat/messages",
            params={"store_id": str(store.id)},
            json={"message": ""},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_message_too_long_returns_422(
        self,
        unauthed_client: AsyncClient,
        store: Store,
    ) -> None:
        """Message exceeding 4000 characters fails validation."""
        response = await unauthed_client.post(
            "/api/v1/chat/messages",
            params={"store_id": str(store.id)},
            json={"message": "x" * 4001},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_nonexistent_conversation_id_creates_new(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Non-existent conversation_id creates a new conversation (doesn't 404)."""
        fake_conv_id = str(uuid.uuid4())

        response = await unauthed_client.post(
            "/api/v1/chat/messages",
            params={"store_id": str(store.id)},
            json={
                "message": "Hello",
                "conversation_id": fake_conv_id,
            },
        )

        assert response.status_code == 201
        # Should create new conversation, not use the fake ID
        assert response.json()["conversation_id"] != fake_conv_id

    @pytest.mark.asyncio
    async def test_includes_sources_from_knowledge_base(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        mock_openai_chat: MagicMock,
        mock_embedding: list[float],
    ) -> None:
        """Response includes sources when knowledge chunks match."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Return Policy",
            source_url="/pages/returns",
        )
        await knowledge_chunk_factory(
            article_id=article.id,
            content="You may return items within 30 days of purchase.",
            embedding=mock_embedding,
        )

        with patch("app.services.retrieval_service.get_embedding_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.generate_embedding = AsyncMock(return_value=mock_embedding)
            mock_get.return_value = mock_svc

            response = await unauthed_client.post(
                "/api/v1/chat/messages",
                params={"store_id": str(store.id)},
                json={"message": "What is your return policy?"},
            )

        assert response.status_code == 201
        sources = response.json()["sources"]
        assert len(sources) >= 1
        assert sources[0]["title"] == "Return Policy"

    @pytest.mark.asyncio
    async def test_openai_failure_returns_503(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        mock_embedding_service: MagicMock,
    ) -> None:
        """OpenAI API failure returns 503 Service Unavailable."""
        with patch("app.services.graph.nodes.ChatOpenAI") as mock_class:
            mock_llm = MagicMock()
            mock_class.return_value = mock_llm
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("OpenAI API is down"))
            mock_llm.bind_tools = MagicMock(return_value=mock_llm)

            response = await unauthed_client.post(
                "/api/v1/chat/messages",
                params={"store_id": str(store.id)},
                json={"message": "Hello"},
            )

        assert response.status_code == 503
        assert "temporarily unavailable" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_missing_store_id_returns_422(
        self,
        unauthed_client: AsyncClient,
    ) -> None:
        """Missing store_id query parameter returns 422."""
        response = await unauthed_client.post(
            "/api/v1/chat/messages",
            json={"message": "Hello"},
        )

        assert response.status_code == 422
