"""Pydantic schemas for knowledge management."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, HttpUrl

from app.models.knowledge import ContentType
from app.schemas.common import BaseSchema

# === Knowledge Chunk Schemas ===


class KnowledgeChunkResponse(BaseSchema):
    """Schema for knowledge chunk in responses."""

    id: UUID
    chunk_index: int
    content: str
    token_count: int | None = None
    has_embedding: bool


# === Knowledge Article Schemas ===


class KnowledgeArticleBase(BaseSchema):
    """Base schema for knowledge article."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    content_type: ContentType = ContentType.FAQ
    source_url: str | None = None


class KnowledgeArticleCreate(KnowledgeArticleBase):
    """Schema for creating a knowledge article."""

    pass


class KnowledgeArticleUpdate(BaseSchema):
    """Schema for updating a knowledge article."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = Field(default=None, min_length=1)
    content_type: ContentType | None = None
    source_url: str | None = None


class KnowledgeArticleResponse(BaseSchema):
    """Schema for knowledge article response."""

    id: UUID
    store_id: UUID
    title: str
    content: str
    content_type: ContentType
    source_url: str | None
    chunks_count: int
    created_at: datetime
    updated_at: datetime


class KnowledgeArticleDetailResponse(KnowledgeArticleResponse):
    """Detailed response with chunks."""

    chunks: list[KnowledgeChunkResponse]


# === Ingestion Schemas ===


class TextIngestionRequest(BaseSchema):
    """Request for text ingestion."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    content_type: ContentType = ContentType.FAQ
    source_url: HttpUrl | None = None


class IngestionResponse(BaseSchema):
    """Response after ingestion."""

    article_id: UUID
    title: str
    chunks_count: int
    status: str  # "completed" or "processing"
    message: str
