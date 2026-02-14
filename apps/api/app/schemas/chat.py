"""Pydantic schemas for chat functionality."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.conversation import Channel, ConversationStatus
from app.models.message import MessageRole
from app.schemas.common import BaseSchema

# === Source/Citation Schemas ===


class SourceReference(BaseSchema):
    """A source citation from RAG."""

    title: str
    url: str | None = None
    snippet: str
    chunk_id: UUID | None = None


# === Product Card Schemas ===


class ProductCard(BaseSchema):
    """A product card extracted from tool results for widget display."""

    product_id: str
    title: str
    price: str | None = None
    image_url: str | None = None
    in_stock: bool = True
    product_url: str | None = None


# === Message Schemas ===


class MessageCreate(BaseSchema):
    """Schema for creating a chat message."""

    message: str = Field(..., min_length=1, max_length=4000)
    context: dict[str, Any] | None = None  # page_url, product_id, etc.


class MessageResponse(BaseSchema):
    """Schema for a message in response."""

    id: UUID
    role: MessageRole
    content: str
    sources: list[SourceReference] | None = None
    products: list[ProductCard] | None = None
    tokens_used: int | None = None
    created_at: datetime


# === Conversation Schemas ===


class ConversationResponse(BaseSchema):
    """Schema for conversation response."""

    id: UUID
    store_id: UUID
    session_id: str
    channel: Channel
    status: ConversationStatus
    customer_email: str | None
    customer_name: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    """Conversation with messages."""

    messages: list[MessageResponse]


# === Chat API Schemas ===


class ChatRequest(BaseSchema):
    """Request for sending a chat message."""

    conversation_id: UUID | None = None  # None = new conversation
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None  # For widget tracking
    context: dict[str, Any] | None = None  # page_url, product_id, etc.


class ChatResponse(BaseSchema):
    """Response from chat endpoint."""

    conversation_id: UUID
    message_id: UUID
    response: str
    sources: list[SourceReference]
    products: list[ProductCard] = Field(default_factory=list)
    created_at: datetime
