"""Chat service orchestrating LangGraph sales agent for responses."""

import contextlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Channel, Conversation, ConversationStatus
from app.models.message import Message, MessageRole
from app.models.order_inquiry import InquiryResolution, InquiryType, OrderInquiry
from app.models.store import Store
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.citation_service import CitationService
from app.services.graph.workflow import create_sales_graph
from app.services.retrieval_service import RetrievalService, RetrievedChunk, RetrievedProduct

logger = logging.getLogger(__name__)

# Constants
CHAT_MODEL = "gpt-4o"
MAX_CONVERSATION_HISTORY = 10  # Last N messages to include
MAX_RESPONSE_TOKENS = 800


class ChatService:
    """Service for chat functionality with LangGraph-based routing and tool calling."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.retrieval_service = RetrievalService(db)
        self.citation_service = CitationService()

    async def process_message(
        self,
        store: Store,
        request: ChatRequest,
        session_id: str | None = None,
        redis_client: aioredis.Redis | None = None,
    ) -> ChatResponse:
        """Process a chat message and generate a response.

        This is the main entry point for chat. It:
        1. Gets or creates a conversation
        2. Saves the user message
        3. Retrieves relevant context via RAG
        4. Creates tools (order + product)
        5. Runs LangGraph workflow (classify → route → respond)
        6. Saves and returns the response

        Args:
            store: The store context
            request: Chat request with message and optional conversation_id
            session_id: Session ID for anonymous users (from widget)
            redis_client: Redis client for order caching (enables order tools)

        Returns:
            Chat response with AI message and sources
        """
        # Get or create conversation
        conversation = await self._get_or_create_conversation(
            store_id=store.id,
            conversation_id=request.conversation_id,
            session_id=session_id or str(uuid.uuid4()),
            context=request.context,
        )

        # Get conversation history BEFORE saving the new message
        history = await self._get_conversation_history(
            conversation_id=conversation.id,
            limit=MAX_CONVERSATION_HISTORY,
        )

        # Save user message
        await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message,
        )

        # Retrieve relevant context (knowledge + products)
        try:
            chunks = await self.retrieval_service.retrieve_context(
                query=request.message,
                store_id=store.id,
                top_k=5,
                threshold=0.5,
            )
        except Exception:
            logger.exception("Failed to retrieve context for store %s", store.id)
            chunks = []

        try:
            products = await self.retrieval_service.retrieve_products(
                query=request.message,
                store_id=store.id,
                top_k=3,
                threshold=0.5,
            )
        except Exception:
            logger.exception("Failed to retrieve products for store %s", store.id)
            products = []

        # Create order tools when redis is available
        order_tools = None
        if redis_client:
            try:
                from app.services.order_service import OrderService
                from app.services.order_tools import create_order_tools

                order_service = OrderService(self.db, redis_client)
                order_tools = create_order_tools(order_service, store.id)
            except Exception:
                logger.exception("Failed to create order tools for store %s", store.id)

        # Create product tools
        product_tools = None
        try:
            from app.services.recommendation_service import RecommendationService
            from app.services.search_service import SearchService
            from app.services.tools.product_tools import create_product_tools

            search_service = SearchService(self.db)
            recommendation_service = RecommendationService(self.db)
            product_tools = create_product_tools(search_service, recommendation_service, store.id)
        except Exception:
            logger.exception("Failed to create product tools for store %s", store.id)

        # Generate AI response via LangGraph
        try:
            (
                response_content,
                tokens_used,
                tool_calls_record,
                tool_results_record,
            ) = await self._generate_response(
                store_name=store.name,
                store_id=store.id,
                user_message=request.message,
                context_chunks=chunks,
                conversation_history=history,
                product_context=products,
                order_tools=order_tools,
                product_tools=product_tools,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to generate AI response: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service is temporarily unavailable. Please try again.",
            ) from e

        # Record order inquiry if verification tool was used
        if tool_calls_record:
            await self._maybe_record_order_inquiry(
                store_id=store.id,
                conversation_id=conversation.id,
                tool_calls=tool_calls_record,
                tool_results=tool_results_record,
            )

        # Create sources from chunks
        sources = self.citation_service.create_sources_from_chunks(chunks)

        # Save assistant message
        assistant_message = await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_content,
            sources=[s.model_dump(mode="json") for s in sources],
            tokens_used=tokens_used,
            tool_calls=tool_calls_record,
            tool_results=tool_results_record,
        )

        await self.db.commit()

        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            response=response_content,
            sources=sources,
            created_at=assistant_message.created_at,
        )

    async def _get_or_create_conversation(
        self,
        store_id: UUID,
        conversation_id: UUID | None,
        session_id: str,
        context: dict[str, Any] | None = None,
    ) -> Conversation:
        """Get existing conversation or create a new one."""
        if conversation_id:
            query = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.store_id == store_id,
            )
            result = await self.db.execute(query)
            conversation = result.scalar_one_or_none()

            if conversation:
                return conversation

        conversation = Conversation(
            store_id=store_id,
            session_id=session_id,
            channel=Channel.WIDGET,
            status=ConversationStatus.ACTIVE,
            extra_data=context or {},
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def _save_message(
        self,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        sources: list[dict[str, Any]] | None = None,
        tokens_used: int | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> Message:
        """Save a message to the database."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources,
            tokens_used=tokens_used,
            tool_calls=tool_calls,
            tool_results=tool_results,
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def _get_conversation_history(
        self,
        conversation_id: UUID,
        limit: int = 10,
    ) -> list[Message]:
        """Get recent messages from conversation in chronological order."""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        return list(reversed(messages))

    async def _generate_response(
        self,
        store_name: str,
        store_id: UUID,
        user_message: str,
        context_chunks: list[RetrievedChunk],
        conversation_history: list[Message],
        product_context: list[RetrievedProduct] | None = None,
        order_tools: list[Any] | None = None,
        product_tools: list[Any] | None = None,
    ) -> tuple[str, int, list[dict[str, Any]] | None, list[dict[str, Any]] | None]:
        """Generate AI response using LangGraph workflow.

        The graph classifies the user's intent, routes to the appropriate node
        (search, recommend, support, general, clarify), and generates a response
        using the relevant tools and context.

        Returns:
            Tuple of (content, tokens_used, tool_calls_record, tool_results_record)
        """
        # Build context strings for prompts
        context_text = self.citation_service.format_context_for_prompt(context_chunks)

        product_text = ""
        if product_context:
            product_parts = []
            for i, p in enumerate(product_context, 1):
                desc = (p.description or "")[:200]
                price_str = f" - Price: ${p.price}" if p.price else ""
                product_parts.append(f"[P{i}] {p.title}{price_str}\n{desc}")
            product_text = "\n\n".join(product_parts)

        context_section = ""
        if context_text or product_text:
            context_section = f"""
CONTEXT FROM KNOWLEDGE BASE:
{context_text or "No knowledge base context available."}

PRODUCT INFORMATION:
{product_text or "No matching products found."}"""

        # Build the LangGraph workflow
        graph = create_sales_graph(
            product_tools=product_tools,
            order_tools=order_tools,
            context_text=context_text,
            product_text=product_text,
            context_section=context_section,
        )

        # Build conversation history as LangChain messages
        messages: list[BaseMessage] = []
        for msg in conversation_history:
            if msg.role == MessageRole.USER:
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                if msg.tool_calls:
                    messages.append(
                        AIMessage(
                            content=msg.content or "",
                            tool_calls=[
                                {
                                    "id": tc["id"],
                                    "name": tc["name"],
                                    "args": tc["args"],
                                }
                                for tc in msg.tool_calls
                            ],
                        )
                    )
                    if msg.tool_results:
                        for tr in msg.tool_results:
                            messages.append(
                                ToolMessage(
                                    content=tr["result"],
                                    tool_call_id=tr["tool_call_id"],
                                )
                            )
                else:
                    messages.append(AIMessage(content=msg.content))

        messages.append(HumanMessage(content=user_message))

        # Build initial state
        initial_state = {
            "messages": messages,
            "intent": "",
            "confidence": 0.0,
            "store_id": str(store_id),
            "store_name": store_name,
            "tools_used": [],
            "has_order_tools": bool(order_tools),
            "has_product_tools": bool(product_tools),
            "tool_calls_record": [],
            "tool_results_record": [],
        }

        # Run the graph
        final_state = await graph.ainvoke(initial_state)

        # Extract response from the last AI message
        response_content = ""
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, AIMessage):
                response_content = msg.content if isinstance(msg.content, str) else ""
                break

        # Extract tool records from final state
        tool_calls_record = final_state.get("tool_calls_record") or None
        tool_results_record = final_state.get("tool_results_record") or None

        # We don't get token counts from the graph (multiple LLM calls)
        tokens_used = 0

        return (
            response_content,
            tokens_used,
            tool_calls_record if tool_calls_record else None,
            tool_results_record if tool_results_record else None,
        )

    async def _maybe_record_order_inquiry(
        self,
        store_id: UUID,
        conversation_id: UUID,
        tool_calls: list[dict[str, Any]],
        tool_results: list[dict[str, Any]] | None,
    ) -> None:
        """Record an OrderInquiry if a verification tool was called successfully."""
        for tc in tool_calls:
            if tc["name"] != "verify_customer_and_lookup_order":
                continue

            # Find the corresponding result
            result_data: dict[str, Any] = {}
            if tool_results:
                for tr in tool_results:
                    if tr["tool_call_id"] == tc["id"]:
                        with contextlib.suppress(json.JSONDecodeError, TypeError):
                            result_data = json.loads(tr["result"])
                        break

            verified = result_data.get("verified", False)
            order_data = result_data.get("order") or {}

            inquiry = OrderInquiry(
                store_id=store_id,
                conversation_id=conversation_id,
                customer_email=tc["args"].get("email"),
                order_number=tc["args"].get("order_number"),
                inquiry_type=InquiryType.ORDER_STATUS,
                order_status=order_data.get("financial_status") if verified else None,
                fulfillment_status=order_data.get("fulfillment_status") if verified else None,
                resolution=(
                    InquiryResolution.ANSWERED
                    if verified
                    else InquiryResolution.VERIFICATION_FAILED
                ),
                resolved_at=datetime.now(UTC),
                extra_data={},
            )
            self.db.add(inquiry)
