"""Chat API endpoints for the widget."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import DBSession, OptionalUser, get_store_by_id
from app.models.conversation import Conversation, ConversationStatus
from app.models.store import Store
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    MessageResponse,
    SourceReference,
)
from app.services.chat_service import ChatService

router = APIRouter()


# === Endpoints ===


@router.post(
    "/messages",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a chat message",
    description="""
    Send a message and get an AI response.

    This endpoint is used by the chat widget. It doesn't require
    authentication - anonymous users can chat.

    The store_id must be provided as a query parameter.
    Optionally provide conversation_id to continue an existing conversation.

    The AI response uses RAG (Retrieval-Augmented Generation) to find
    relevant information from the store's knowledge base.
    """,
)
async def send_message(
    request: ChatRequest,
    db: DBSession,
    store: Store = Depends(get_store_by_id),
    _user: OptionalUser = None,  # Reserved for future use (e.g., linking to customer)
) -> ChatResponse:
    """Send a message and get an AI response.

    TODO: Add streaming support in Phase 2 via SSE endpoint.
    """
    service = ChatService(db)

    # Use session_id from request or None (service will generate one)
    session_id = request.session_id

    response = await service.process_message(
        store=store,
        request=request,
        session_id=session_id,
    )

    return response


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get a conversation",
)
async def get_conversation(
    conversation_id: UUID,
    db: DBSession,
    store: Store = Depends(get_store_by_id),
) -> ConversationDetailResponse:
    """Get a conversation with all its messages.

    Used to load conversation history in the widget.
    """
    query = (
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.store_id == store.id,
        )
        .options(selectinload(Conversation.messages))
    )

    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    messages = [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            sources=[SourceReference(**s) for s in m.sources] if m.sources else None,
            tokens_used=m.tokens_used,
            created_at=m.created_at,
        )
        for m in conversation.messages
    ]

    return ConversationDetailResponse(
        id=conversation.id,
        store_id=conversation.store_id,
        session_id=conversation.session_id,
        channel=conversation.channel,
        status=conversation.status,
        customer_email=conversation.customer_email,
        customer_name=conversation.customer_name,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


@router.get(
    "/conversations",
    response_model=list[ConversationDetailResponse],
    summary="List conversations by session",
)
async def list_conversations_by_session(
    db: DBSession,
    session_id: str = Query(..., description="Session ID from widget"),
    store: Store = Depends(get_store_by_id),
) -> list[ConversationDetailResponse]:
    """List conversations for a session.

    Used by the widget to restore previous conversations for a returning user.
    """
    query = (
        select(Conversation)
        .where(
            Conversation.store_id == store.id,
            Conversation.session_id == session_id,
        )
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.created_at.desc())
        .limit(10)
    )

    result = await db.execute(query)
    conversations = result.scalars().all()

    return [
        ConversationDetailResponse(
            id=c.id,
            store_id=c.store_id,
            session_id=c.session_id,
            channel=c.channel,
            status=c.status,
            customer_email=c.customer_email,
            customer_name=c.customer_name,
            created_at=c.created_at,
            updated_at=c.updated_at,
            messages=[
                MessageResponse(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    sources=[SourceReference(**s) for s in m.sources] if m.sources else None,
                    tokens_used=m.tokens_used,
                    created_at=m.created_at,
                )
                for m in c.messages
            ],
        )
        for c in conversations
    ]


# === Status Update Schema ===


class ConversationStatusUpdate(BaseModel):
    """Schema for updating conversation status."""

    status: ConversationStatus


@router.patch(
    "/conversations/{conversation_id}/status",
    response_model=ConversationDetailResponse,
    summary="Update conversation status",
    description="Update the status of a conversation (active, resolved, escalated).",
)
async def update_conversation_status(
    conversation_id: UUID,
    data: ConversationStatusUpdate,
    db: DBSession,
    store: Store = Depends(get_store_by_id),
) -> ConversationDetailResponse:
    """Update conversation status.

    Used by dashboard to mark conversations as resolved or escalated.
    """
    query = (
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.store_id == store.id,
        )
        .options(selectinload(Conversation.messages))
    )

    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    conversation.status = data.status
    await db.commit()
    await db.refresh(conversation)

    return ConversationDetailResponse(
        id=conversation.id,
        store_id=conversation.store_id,
        session_id=conversation.session_id,
        channel=conversation.channel,
        status=conversation.status,
        customer_email=conversation.customer_email,
        customer_name=conversation.customer_name,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                sources=[SourceReference(**s) for s in m.sources] if m.sources else None,
                tokens_used=m.tokens_used,
                created_at=m.created_at,
            )
            for m in conversation.messages
        ],
    )
