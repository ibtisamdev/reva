"""Unit tests for ChatService.

Tests the service layer independently of HTTP routing.
All OpenAI calls are mocked.
"""

import uuid
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Channel, Conversation, ConversationStatus
from app.models.message import Message, MessageRole
from app.models.store import Store
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.services.retrieval_service import RetrievedChunk, RetrievedProduct


class TestChatServiceProcessMessage:
    """Tests for ChatService.process_message() orchestration."""

    @pytest.mark.asyncio
    async def test_creates_conversation_and_messages(
        self,
        db_session: AsyncSession,
        store: Store,
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """process_message creates conversation, user message, and assistant message."""
        service = ChatService(db_session)
        request = ChatRequest(message="Hello, what are your hours?")

        response = await service.process_message(store, request)

        # Verify response structure
        assert response.conversation_id is not None
        assert response.message_id is not None
        assert response.response == "This is a mock AI response for testing."
        assert response.sources is not None
        assert response.created_at is not None

        # Verify conversation created in DB
        conv = await db_session.get(Conversation, response.conversation_id)
        assert conv is not None
        assert conv.store_id == store.id
        assert conv.status == ConversationStatus.ACTIVE

        # Verify 2 messages created (user + assistant)
        result = await db_session.execute(
            select(Message)
            .where(Message.conversation_id == response.conversation_id)
            .order_by(Message.created_at)
        )
        messages = list(result.scalars().all())
        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER
        assert messages[0].content == "Hello, what are your hours?"
        assert messages[1].role == MessageRole.ASSISTANT
        assert messages[1].content == "This is a mock AI response for testing."

    @pytest.mark.asyncio
    async def test_continues_existing_conversation(
        self,
        db_session: AsyncSession,
        store: Store,
        conversation_factory: Callable[..., Any],
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Providing conversation_id reuses existing conversation."""
        existing_conv = await conversation_factory(store_id=store.id)

        service = ChatService(db_session)
        request = ChatRequest(
            message="Follow up question",
            conversation_id=existing_conv.id,
        )

        response = await service.process_message(store, request)

        assert response.conversation_id == existing_conv.id

    @pytest.mark.asyncio
    async def test_stores_tokens_used(
        self,
        db_session: AsyncSession,
        store: Store,
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Token usage from OpenAI is stored in the assistant message."""
        service = ChatService(db_session)
        request = ChatRequest(message="Hello")

        response = await service.process_message(store, request)

        msg = await db_session.get(Message, response.message_id)
        assert msg is not None
        assert msg.tokens_used == 150  # From mock_openai_response fixture

    @pytest.mark.asyncio
    async def test_stores_sources_in_message(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        mock_openai_chat: MagicMock,
        mock_embedding: list[float],
    ) -> None:
        """Sources from RAG are stored in the assistant message."""
        # Create knowledge article with embedded chunk
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Store Hours",
            source_url="/pages/hours",
        )
        await knowledge_chunk_factory(
            article_id=article.id,
            content="We are open 9am to 5pm Monday through Friday.",
            embedding=mock_embedding,
        )

        # Mock embedding service to return same vector (ensures match)
        with patch("app.services.retrieval_service.get_embedding_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.generate_embedding = AsyncMock(return_value=mock_embedding)
            mock_get.return_value = mock_svc

            service = ChatService(db_session)
            request = ChatRequest(message="What are your hours?")
            response = await service.process_message(store, request)

        # Verify sources returned
        assert len(response.sources) >= 1
        assert response.sources[0].title == "Store Hours"

        # Verify sources stored in message
        msg = await db_session.get(Message, response.message_id)
        assert msg is not None
        assert msg.sources is not None
        assert len(msg.sources) >= 1

    @pytest.mark.asyncio
    async def test_duplicate_messages_in_history_not_skipped(
        self,
        db_session: AsyncSession,
        store: Store,
        conversation_factory: Callable[..., Any],
        message_factory: Callable[..., Any],
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Repeated messages in history are all included (regression test for dedup bug)."""
        conv = await conversation_factory(store_id=store.id)

        # User said "Hello" before, got a response
        await message_factory(conversation_id=conv.id, role=MessageRole.USER, content="Hello")
        await message_factory(
            conversation_id=conv.id, role=MessageRole.ASSISTANT, content="Hi there!"
        )

        # User says "Hello" again
        service = ChatService(db_session)
        request = ChatRequest(message="Hello", conversation_id=conv.id)

        # Track what gets passed to _generate_response
        original_generate = service._generate_response
        captured_history: list[Message] = []

        async def capture_generate(
            *args: Any, **kwargs: Any
        ) -> tuple[str, int, list[dict[str, Any]] | None, list[dict[str, Any]] | None]:
            captured_history.extend(kwargs.get("conversation_history", []))
            return await original_generate(*args, **kwargs)

        with patch.object(service, "_generate_response", side_effect=capture_generate):
            await service.process_message(store, request)

        # The first "Hello" should be in history
        hello_messages = [m for m in captured_history if m.content == "Hello"]
        assert len(hello_messages) == 1  # The previous "Hello", not the current one

    @pytest.mark.asyncio
    async def test_openai_failure_returns_503(
        self,
        db_session: AsyncSession,
        store: Store,
        mock_embedding_service: MagicMock,
    ) -> None:
        """OpenAI API failure raises HTTPException with 503."""
        from fastapi import HTTPException

        with patch("app.services.chat_service.ChatOpenAI") as mock_class:
            mock_llm = MagicMock()
            mock_class.return_value = mock_llm
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("OpenAI API error"))
            mock_llm.bind_tools = MagicMock(return_value=mock_llm)

            service = ChatService(db_session)
            request = ChatRequest(message="Hello")

            with pytest.raises(HTTPException) as exc_info:
                await service.process_message(store, request)

            assert exc_info.value.status_code == 503
            assert "temporarily unavailable" in exc_info.value.detail.lower()


class TestChatServiceGetOrCreateConversation:
    """Tests for ChatService._get_or_create_conversation()."""

    @pytest.mark.asyncio
    async def test_creates_new_when_no_id_provided(
        self,
        db_session: AsyncSession,
        store: Store,
    ) -> None:
        """Creates new conversation when conversation_id is None."""
        service = ChatService(db_session)

        conv = await service._get_or_create_conversation(
            store_id=store.id,
            conversation_id=None,
            session_id="test-session-123",
        )

        assert conv.id is not None
        assert conv.store_id == store.id
        assert conv.session_id == "test-session-123"
        assert conv.status == ConversationStatus.ACTIVE
        assert conv.channel == Channel.WIDGET

    @pytest.mark.asyncio
    async def test_returns_existing_when_found(
        self,
        db_session: AsyncSession,
        store: Store,
        conversation_factory: Callable[..., Any],
    ) -> None:
        """Returns existing conversation when ID matches and belongs to store."""
        existing = await conversation_factory(store_id=store.id, session_id="original")

        service = ChatService(db_session)
        conv = await service._get_or_create_conversation(
            store_id=store.id,
            conversation_id=existing.id,
            session_id="different-session",  # Should be ignored
        )

        assert conv.id == existing.id
        assert conv.session_id == "original"  # Original session preserved

    @pytest.mark.asyncio
    async def test_creates_new_when_id_not_found(
        self,
        db_session: AsyncSession,
        store: Store,
    ) -> None:
        """Creates new conversation when provided ID doesn't exist."""
        service = ChatService(db_session)
        fake_id = uuid.uuid4()

        conv = await service._get_or_create_conversation(
            store_id=store.id,
            conversation_id=fake_id,
            session_id="test-session",
        )

        # Should create new, not fail
        assert conv.id is not None
        assert conv.id != fake_id

    @pytest.mark.asyncio
    async def test_creates_new_when_id_belongs_to_other_store(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        conversation_factory: Callable[..., Any],
    ) -> None:
        """Creates new conversation when ID belongs to a different store."""
        other_conv = await conversation_factory(store_id=other_store.id)

        service = ChatService(db_session)
        conv = await service._get_or_create_conversation(
            store_id=store.id,  # Our store, not other_store
            conversation_id=other_conv.id,
            session_id="test-session",
        )

        # Should create new, not use other store's conversation
        assert conv.id != other_conv.id
        assert conv.store_id == store.id


class TestChatServiceGetConversationHistory:
    """Tests for ChatService._get_conversation_history()."""

    @pytest.mark.asyncio
    async def test_returns_chronological_order(
        self,
        db_session: AsyncSession,
        store: Store,
        conversation_factory: Callable[..., Any],
        message_factory: Callable[..., Any],
    ) -> None:
        """Messages are returned in chronological order (oldest first)."""
        conv = await conversation_factory(store_id=store.id)

        await message_factory(conversation_id=conv.id, content="First")
        await message_factory(conversation_id=conv.id, content="Second")
        await message_factory(conversation_id=conv.id, content="Third")

        service = ChatService(db_session)
        history = await service._get_conversation_history(conv.id, limit=10)

        assert len(history) == 3
        assert history[0].content == "First"
        assert history[1].content == "Second"
        assert history[2].content == "Third"

    @pytest.mark.asyncio
    async def test_respects_limit(
        self,
        db_session: AsyncSession,
        store: Store,
        conversation_factory: Callable[..., Any],
        message_factory: Callable[..., Any],
    ) -> None:
        """Returns at most `limit` most recent messages."""
        conv = await conversation_factory(store_id=store.id)

        for i in range(15):
            await message_factory(conversation_id=conv.id, content=f"Message {i}")

        service = ChatService(db_session)
        history = await service._get_conversation_history(conv.id, limit=10)

        assert len(history) == 10
        # Should be the 10 most recent (5-14), in chronological order
        assert history[0].content == "Message 5"
        assert history[-1].content == "Message 14"


class TestChatServiceBuildSystemPrompt:
    """Tests for ChatService._build_system_prompt()."""

    def test_includes_store_name(self) -> None:
        """System prompt includes the store name."""
        service = ChatService(MagicMock())  # DB not needed for this method

        prompt = service._build_system_prompt("Acme Store", [], [])

        assert "Acme Store" in prompt

    def test_includes_knowledge_context(self) -> None:
        """System prompt includes formatted context from chunks."""
        service = ChatService(MagicMock())
        chunks = [
            RetrievedChunk(
                chunk_id=uuid.uuid4(),
                article_id=uuid.uuid4(),
                content="Returns are accepted within 30 days of purchase.",
                chunk_index=0,
                similarity=0.92,
                article_title="Return Policy",
                article_url="/pages/returns",
            )
        ]

        prompt = service._build_system_prompt("Test Store", chunks, [])

        assert "Return Policy" in prompt
        assert "Returns are accepted within 30 days" in prompt

    def test_includes_product_context(self) -> None:
        """System prompt includes product information with prices."""
        service = ChatService(MagicMock())
        products = [
            RetrievedProduct(
                product_id=uuid.uuid4(),
                title="Widget Pro",
                description="A professional-grade widget for experts.",
                price="99.99",
                similarity=0.85,
            )
        ]

        prompt = service._build_system_prompt("Test Store", [], products)

        assert "Widget Pro" in prompt
        assert "99.99" in prompt
        assert "professional-grade" in prompt

    def test_handles_empty_context(self) -> None:
        """System prompt handles empty context gracefully."""
        service = ChatService(MagicMock())

        prompt = service._build_system_prompt("Test Store", [], [])

        assert "Test Store" in prompt
        # Citation service returns "No relevant context found." for empty chunks
        assert "No relevant context found" in prompt or "No matching products" in prompt

    def test_includes_order_instructions_when_tools_available(self) -> None:
        """System prompt includes order instructions when has_order_tools=True."""
        service = ChatService(MagicMock())

        prompt = service._build_system_prompt("Test Store", [], [], has_order_tools=True)

        assert "ORDER STATUS INSTRUCTIONS" in prompt
        assert "verification" in prompt.lower()

    def test_excludes_order_instructions_when_no_tools(self) -> None:
        """System prompt omits order instructions when has_order_tools=False."""
        service = ChatService(MagicMock())

        prompt = service._build_system_prompt("Test Store", [], [], has_order_tools=False)

        assert "ORDER STATUS INSTRUCTIONS" not in prompt


class TestChatServiceOrderToolIntegration:
    """Tests for order tool creation within ChatService.process_message()."""

    @pytest.mark.asyncio
    async def test_tools_created_when_redis_provided(
        self,
        db_session: AsyncSession,
        store: Store,
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
        fake_redis: Any,
    ) -> None:
        """Order tools are created when redis_client is provided."""
        service = ChatService(db_session)
        request = ChatRequest(message="Where is my order #1001?")

        with patch("app.services.order_service.OrderService") as mock_os_cls, patch(
            "app.services.order_tools.create_order_tools"
        ) as mock_cot:
            mock_cot.return_value = [MagicMock(name="tool1")]

            await service.process_message(store, request, redis_client=fake_redis)

            mock_os_cls.assert_called_once_with(db_session, fake_redis)
            mock_cot.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_tools_without_redis(
        self,
        db_session: AsyncSession,
        store: Store,
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Order tools are NOT created when redis_client is None."""
        service = ChatService(db_session)
        request = ChatRequest(message="What are your hours?")

        with patch("app.services.order_tools.create_order_tools") as mock_cot:
            await service.process_message(store, request, redis_client=None)

            mock_cot.assert_not_called()

    @pytest.mark.asyncio
    async def test_tool_creation_failure_handled_gracefully(
        self,
        db_session: AsyncSession,
        store: Store,
        mock_openai_chat: MagicMock,
        mock_embedding_service: MagicMock,
        fake_redis: Any,
    ) -> None:
        """Tool creation failure is logged but doesn't crash the request."""
        service = ChatService(db_session)
        request = ChatRequest(message="Hello")

        with patch(
            "app.services.order_tools.create_order_tools",
            side_effect=Exception("Tool creation failed"),
        ):
            # Should not raise — falls back to no tools
            response = await service.process_message(store, request, redis_client=fake_redis)

        assert response.response == "This is a mock AI response for testing."


class TestChatServiceMaybeRecordOrderInquiry:
    """Tests for ChatService._maybe_record_order_inquiry()."""

    @pytest.mark.asyncio
    async def test_records_on_successful_verification(
        self,
        db_session: AsyncSession,
        store: Store,
        conversation_factory: Callable[..., Any],
    ) -> None:
        """Records OrderInquiry when verification succeeds."""
        conv = await conversation_factory(store_id=store.id)

        service = ChatService(db_session)
        await service._maybe_record_order_inquiry(
            store_id=store.id,
            conversation_id=conv.id,
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "verify_customer_and_lookup_order",
                    "args": {"order_number": "#1001", "email": "test@example.com"},
                }
            ],
            tool_results=[
                {
                    "tool_call_id": "call_1",
                    "result": '{"verified": true, "order": {"financial_status": "paid", "fulfillment_status": "fulfilled"}, "message": "verified"}',
                }
            ],
        )
        await db_session.flush()

        from sqlalchemy import select

        from app.models.order_inquiry import InquiryResolution, OrderInquiry

        result = await db_session.execute(
            select(OrderInquiry).where(OrderInquiry.store_id == store.id)
        )
        inquiry = result.scalar_one_or_none()

        assert inquiry is not None
        assert inquiry.order_number == "#1001"
        assert inquiry.customer_email == "test@example.com"
        assert inquiry.resolution == InquiryResolution.ANSWERED
        assert inquiry.order_status == "paid"
        assert inquiry.fulfillment_status == "fulfilled"

    @pytest.mark.asyncio
    async def test_records_verification_failure(
        self,
        db_session: AsyncSession,
        store: Store,
        conversation_factory: Callable[..., Any],
    ) -> None:
        """Records OrderInquiry when verification fails."""
        conv = await conversation_factory(store_id=store.id)

        service = ChatService(db_session)
        await service._maybe_record_order_inquiry(
            store_id=store.id,
            conversation_id=conv.id,
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "verify_customer_and_lookup_order",
                    "args": {"order_number": "#1001", "email": "wrong@example.com"},
                }
            ],
            tool_results=[
                {
                    "tool_call_id": "call_1",
                    "result": '{"verified": false, "message": "Email mismatch"}',
                }
            ],
        )
        await db_session.flush()

        from sqlalchemy import select

        from app.models.order_inquiry import InquiryResolution, OrderInquiry

        result = await db_session.execute(
            select(OrderInquiry).where(OrderInquiry.store_id == store.id)
        )
        inquiry = result.scalar_one_or_none()

        assert inquiry is not None
        assert inquiry.resolution == InquiryResolution.VERIFICATION_FAILED
        assert inquiry.order_status is None

    @pytest.mark.asyncio
    async def test_skips_non_verification_tools(
        self,
        db_session: AsyncSession,
        store: Store,
        conversation_factory: Callable[..., Any],
    ) -> None:
        """Does not record inquiry for non-verification tool calls."""
        conv = await conversation_factory(store_id=store.id)

        service = ChatService(db_session)
        await service._maybe_record_order_inquiry(
            store_id=store.id,
            conversation_id=conv.id,
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "lookup_order_status",
                    "args": {"order_number": "#1001"},
                }
            ],
            tool_results=[
                {
                    "tool_call_id": "call_1",
                    "result": '{"order_number": "#1001"}',
                }
            ],
        )
        await db_session.flush()

        from sqlalchemy import func, select

        from app.models.order_inquiry import OrderInquiry

        count = (
            await db_session.execute(
                select(func.count()).select_from(OrderInquiry).where(OrderInquiry.store_id == store.id)
            )
        ).scalar()
        assert count == 0

    @pytest.mark.asyncio
    async def test_handles_malformed_json_result(
        self,
        db_session: AsyncSession,
        store: Store,
        conversation_factory: Callable[..., Any],
    ) -> None:
        """Handles malformed JSON in tool results gracefully."""
        conv = await conversation_factory(store_id=store.id)

        service = ChatService(db_session)
        # Should not raise — just creates inquiry with empty result_data
        await service._maybe_record_order_inquiry(
            store_id=store.id,
            conversation_id=conv.id,
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "verify_customer_and_lookup_order",
                    "args": {"order_number": "#1001", "email": "test@test.com"},
                }
            ],
            tool_results=[
                {
                    "tool_call_id": "call_1",
                    "result": "not valid json {{{",
                }
            ],
        )
        await db_session.flush()

        from sqlalchemy import select

        from app.models.order_inquiry import OrderInquiry

        result = await db_session.execute(
            select(OrderInquiry).where(OrderInquiry.store_id == store.id)
        )
        inquiry = result.scalar_one_or_none()
        assert inquiry is not None
        # verified defaults to False when JSON parsing fails
        assert inquiry.order_status is None

    @pytest.mark.asyncio
    async def test_correct_email_and_order_extraction(
        self,
        db_session: AsyncSession,
        store: Store,
        conversation_factory: Callable[..., Any],
    ) -> None:
        """Extracts email and order_number from tool call args."""
        conv = await conversation_factory(store_id=store.id)

        service = ChatService(db_session)
        await service._maybe_record_order_inquiry(
            store_id=store.id,
            conversation_id=conv.id,
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "verify_customer_and_lookup_order",
                    "args": {"order_number": "#2002", "email": "specific@email.com"},
                }
            ],
            tool_results=[
                {
                    "tool_call_id": "call_1",
                    "result": '{"verified": true, "order": {}, "message": "ok"}',
                }
            ],
        )
        await db_session.flush()

        from sqlalchemy import select

        from app.models.order_inquiry import OrderInquiry

        result = await db_session.execute(
            select(OrderInquiry).where(OrderInquiry.store_id == store.id)
        )
        inquiry = result.scalar_one_or_none()

        assert inquiry is not None
        assert inquiry.customer_email == "specific@email.com"
        assert inquiry.order_number == "#2002"

    @pytest.mark.asyncio
    async def test_handles_none_tool_results(
        self,
        db_session: AsyncSession,
        store: Store,
        conversation_factory: Callable[..., Any],
    ) -> None:
        """Handles None tool_results gracefully."""
        conv = await conversation_factory(store_id=store.id)

        service = ChatService(db_session)
        await service._maybe_record_order_inquiry(
            store_id=store.id,
            conversation_id=conv.id,
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "verify_customer_and_lookup_order",
                    "args": {"order_number": "#1001", "email": "test@test.com"},
                }
            ],
            tool_results=None,
        )
        await db_session.flush()

        from sqlalchemy import select

        from app.models.order_inquiry import OrderInquiry

        result = await db_session.execute(
            select(OrderInquiry).where(OrderInquiry.store_id == store.id)
        )
        inquiry = result.scalar_one_or_none()
        assert inquiry is not None
