"""Chat service orchestrating RAG and LLM for responses."""

import logging
import uuid
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Channel, Conversation, ConversationStatus
from app.models.message import Message, MessageRole
from app.models.store import Store
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.citation_service import CitationService
from app.services.retrieval_service import RetrievalService, RetrievedChunk, RetrievedProduct

logger = logging.getLogger(__name__)

# Constants
CHAT_MODEL = "gpt-4o"
MAX_CONVERSATION_HISTORY = 10  # Last N messages to include
MAX_RESPONSE_TOKENS = 500


class ChatService:
    """Service for chat functionality with RAG."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key)
        self.retrieval_service = RetrievalService(db)
        self.citation_service = CitationService()

    async def process_message(
        self,
        store: Store,
        request: ChatRequest,
        session_id: str | None = None,
    ) -> ChatResponse:
        """Process a chat message and generate a response.

        This is the main entry point for chat. It:
        1. Gets or creates a conversation
        2. Saves the user message
        3. Retrieves relevant context via RAG
        4. Generates an AI response
        5. Saves and returns the response

        Args:
            store: The store context
            request: Chat request with message and optional conversation_id
            session_id: Session ID for anonymous users (from widget)

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
        # This ensures the current message isn't in history, avoiding dedup issues
        # where repeated messages (e.g., "Hello" twice) would be incorrectly skipped
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
        chunks = await self.retrieval_service.retrieve_context(
            query=request.message,
            store_id=store.id,
            top_k=5,
            threshold=0.5,
        )

        products = await self.retrieval_service.retrieve_products(
            query=request.message,
            store_id=store.id,
            top_k=3,
            threshold=0.5,
        )

        # Generate AI response
        # TODO: Add streaming support in Phase 2
        try:
            response_content, tokens_used = await self._generate_response(
                store_name=store.name,
                user_message=request.message,
                context_chunks=chunks,
                conversation_history=history,
                product_context=products,
            )
        except HTTPException:
            raise  # Re-raise HTTP exceptions as-is
        except Exception as e:
            logger.exception("Failed to generate AI response: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service is temporarily unavailable. Please try again.",
            ) from e

        # Create sources from chunks
        sources = self.citation_service.create_sources_from_chunks(chunks)

        # Save assistant message
        assistant_message = await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_content,
            sources=[s.model_dump(mode="json") for s in sources],
            tokens_used=tokens_used,
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
        """Get existing conversation or create a new one.

        Args:
            store_id: The store ID
            conversation_id: Optional existing conversation ID
            session_id: Session ID for tracking
            context: Optional context data (page_url, etc.)

        Returns:
            The conversation (existing or new)
        """
        if conversation_id:
            # Try to get existing conversation (scoped to store)
            query = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.store_id == store_id,
            )
            result = await self.db.execute(query)
            conversation = result.scalar_one_or_none()

            if conversation:
                return conversation

        # Create new conversation
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
    ) -> Message:
        """Save a message to the database.

        Args:
            conversation_id: The conversation ID
            role: Message role (user, assistant, system)
            content: Message content
            sources: Optional source citations
            tokens_used: Optional token count

        Returns:
            The created message
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources,
            tokens_used=tokens_used,
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def _get_conversation_history(
        self,
        conversation_id: UUID,
        limit: int = 10,
    ) -> list[Message]:
        """Get recent messages from conversation.

        Args:
            conversation_id: The conversation ID
            limit: Maximum number of messages to return

        Returns:
            List of messages in chronological order
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        # Reverse to get chronological order
        return list(reversed(messages))

    async def _generate_response(
        self,
        store_name: str,
        user_message: str,
        context_chunks: list[RetrievedChunk],
        conversation_history: list[Message],
        product_context: list[RetrievedProduct] | None = None,
    ) -> tuple[str, int]:
        """Generate AI response using OpenAI.

        Args:
            store_name: Name of the store for personalization
            user_message: The current user message
            context_chunks: Retrieved context from RAG
            conversation_history: Previous messages in conversation

        Returns:
            Tuple of (response_content, tokens_used)
        """
        # Build system prompt
        system_prompt = self._build_system_prompt(store_name, context_chunks, product_context or [])

        # Build messages for API
        messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        # Note: History is fetched BEFORE the current message is saved, so we don't
        # need to filter out the current message here
        for msg in conversation_history:
            if msg.role == MessageRole.USER:
                messages.append(ChatCompletionUserMessageParam(role="user", content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                messages.append(
                    ChatCompletionAssistantMessageParam(role="assistant", content=msg.content)
                )

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Call OpenAI API
        # TODO: Add streaming support in Phase 2
        response = await self.openai.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=MAX_RESPONSE_TOKENS,
            temperature=0.7,
        )

        content = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0

        return content, tokens_used

    def _build_system_prompt(
        self,
        store_name: str,
        context_chunks: list[RetrievedChunk],
        product_context: list[RetrievedProduct] | None = None,
    ) -> str:
        """Build the system prompt with context.

        Args:
            store_name: Name of the store
            context_chunks: Retrieved context chunks
            product_context: Retrieved product matches

        Returns:
            Complete system prompt string
        """
        context_text = self.citation_service.format_context_for_prompt(context_chunks)

        product_text = ""
        if product_context:
            product_parts = []
            for i, p in enumerate(product_context, 1):
                desc = (p.description or "")[:200]
                price_str = f" - Price: ${p.price}" if p.price else ""
                product_parts.append(f"[P{i}] {p.title}{price_str}\n{desc}")
            product_text = "\n\n".join(product_parts)

        return f"""You are a helpful customer support agent for {store_name}.

Your role is to assist customers with their questions about products, orders, shipping, returns, and other store policies.

INSTRUCTIONS:
1. Use the provided context to answer questions accurately
2. Be friendly, professional, and concise
3. If the context doesn't contain enough information to answer, say so honestly
4. Do NOT make up information - only use what's in the context
5. If you reference information from the context, mention which source it came from
6. Keep responses focused and avoid unnecessary verbosity

CONTEXT FROM KNOWLEDGE BASE:
{context_text}

PRODUCT INFORMATION:
{product_text or "No matching products found."}

Remember: Only answer based on the context provided. If you're unsure, ask for clarification or direct the customer to contact support."""
