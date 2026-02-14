"""Chat service orchestrating RAG and LLM for responses."""

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
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Channel, Conversation, ConversationStatus
from app.models.message import Message, MessageRole
from app.models.order_inquiry import InquiryResolution, InquiryType, OrderInquiry
from app.models.store import Store
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.citation_service import CitationService
from app.services.retrieval_service import RetrievalService, RetrievedChunk, RetrievedProduct

logger = logging.getLogger(__name__)

# Constants
CHAT_MODEL = "gpt-4o"
MAX_CONVERSATION_HISTORY = 10  # Last N messages to include
MAX_RESPONSE_TOKENS = 800
MAX_TOOL_ITERATIONS = 3


class ChatService:
    """Service for chat functionality with RAG and optional tool calling."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = ChatOpenAI(
            model=CHAT_MODEL,
            api_key=settings.openai_api_key,
            temperature=0.7,
            max_tokens=MAX_RESPONSE_TOKENS,
        )
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
        4. Optionally creates order tools (if store has read_orders scope)
        5. Generates an AI response (with agentic loop if tools available)
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
        # Wrapped in try/except so chat continues with empty context if embedding fails
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
        tools = None
        if redis_client:
            try:
                from app.services.order_service import OrderService
                from app.services.order_tools import create_order_tools

                order_service = OrderService(self.db, redis_client)
                tools = create_order_tools(order_service, store.id)
            except Exception:
                logger.exception("Failed to create order tools for store %s", store.id)

        # Generate AI response
        try:
            (
                response_content,
                tokens_used,
                tool_calls_record,
                tool_results_record,
            ) = await self._generate_response(
                store_name=store.name,
                user_message=request.message,
                context_chunks=chunks,
                conversation_history=history,
                product_context=products,
                tools=tools,
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
        user_message: str,
        context_chunks: list[RetrievedChunk],
        conversation_history: list[Message],
        product_context: list[RetrievedProduct] | None = None,
        tools: list[Any] | None = None,
    ) -> tuple[str, int, list[dict[str, Any]] | None, list[dict[str, Any]] | None]:
        """Generate AI response using LangChain with optional tool calling.

        Returns:
            Tuple of (content, tokens_used, tool_calls_record, tool_results_record)
        """
        system_prompt = self._build_system_prompt(
            store_name, context_chunks, product_context or [], has_order_tools=bool(tools)
        )
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]

        # Build conversation history using LangChain message types
        for msg in conversation_history:
            if msg.role == MessageRole.USER:
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                if msg.tool_calls:
                    # Reconstruct AIMessage with tool_calls for context
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
                    # Add corresponding ToolMessages
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

        llm = self.llm.bind_tools(tools) if tools else self.llm
        all_tool_calls: list[dict[str, Any]] = []
        all_tool_results: list[dict[str, Any]] = []

        # Agentic loop (max iterations to prevent runaway)
        for _ in range(MAX_TOOL_ITERATIONS):
            response: AIMessage = await llm.ainvoke(messages)  # type: ignore[assignment,unused-ignore]

            if not response.tool_calls:
                # Final text response
                tokens = (
                    response.usage_metadata.get("total_tokens", 0) if response.usage_metadata else 0
                )
                content = response.content if isinstance(response.content, str) else ""
                return (
                    content,
                    tokens,
                    all_tool_calls or None,
                    all_tool_results or None,
                )

            # Process tool calls
            messages.append(response)
            for tc in response.tool_calls:
                all_tool_calls.append({"id": tc["id"], "name": tc["name"], "args": tc["args"]})

                # Find and execute the matching tool
                tool_fn = next((t for t in tools if t.name == tc["name"]), None) if tools else None
                try:
                    if tool_fn:
                        result = await tool_fn.ainvoke(tc["args"])
                    else:
                        result = f"Unknown tool: {tc['name']}"
                except Exception as e:
                    logger.exception("Tool execution error: %s", tc["name"])
                    result = f"Error: {e}"

                all_tool_results.append({"tool_call_id": tc["id"], "result": str(result)})
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        # Max iterations exceeded — get final text response
        return (
            "I'm having trouble processing your request. Please try again.",
            0,
            all_tool_calls or None,
            all_tool_results or None,
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

    def _build_system_prompt(
        self,
        store_name: str,
        context_chunks: list[RetrievedChunk],
        product_context: list[RetrievedProduct] | None = None,
        has_order_tools: bool = False,
    ) -> str:
        """Build the system prompt with context and optional order instructions."""
        context_text = self.citation_service.format_context_for_prompt(context_chunks)

        product_text = ""
        if product_context:
            product_parts = []
            for i, p in enumerate(product_context, 1):
                desc = (p.description or "")[:200]
                price_str = f" - Price: ${p.price}" if p.price else ""
                product_parts.append(f"[P{i}] {p.title}{price_str}\n{desc}")
            product_text = "\n\n".join(product_parts)

        order_instructions = ""
        if has_order_tools:
            order_instructions = """

ORDER STATUS INSTRUCTIONS:
1. When a customer asks about their order status, you MUST ask for BOTH their order number AND email address before using the verification tool
2. NEVER reveal order details without successful verification
3. After verification, use the lookup_order_status tool for follow-up questions about the same order
4. When sharing tracking info, always include the tracking number and carrier name
5. Use get_tracking_details when the customer asks specifically about tracking, shipping, or delivery
6. If verification fails, suggest the customer double-check their order number and email"""

        return f"""You are a helpful customer support agent for {store_name}.

Your role is to assist customers with their questions about products, orders, shipping, returns, and other store policies.

INSTRUCTIONS:
1. Use the provided context to answer questions accurately
2. Be friendly, professional, and concise
3. If the context doesn't contain enough information to answer, say so honestly
4. Do NOT make up information - only use what's in the context
5. If you reference information from the context, mention which source it came from
6. Keep responses focused and avoid unnecessary verbosity
{order_instructions}

CONTEXT FROM KNOWLEDGE BASE:
{context_text}

PRODUCT INFORMATION:
{product_text or "No matching products found."}

Remember: Only answer based on the context provided. If you're unsure, ask for clarification or direct the customer to contact support."""
