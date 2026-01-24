"""Knowledge base models for FAQs, policies, and documents."""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.store import Store


class ContentType(str, enum.Enum):
    """Types of knowledge content."""

    FAQ = "faq"
    POLICY = "policy"
    GUIDE = "guide"
    PAGE = "page"


class KnowledgeArticle(Base):
    """Knowledge article model for FAQs, policies, etc.

    Knowledge articles are scoped to a store and used for RAG-based responses.
    Each article can be split into chunks for better retrieval.
    """

    __tablename__ = "knowledge_articles"

    # Store relationship (replaces organization_id)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Article content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="content_type"),
        default=ContentType.FAQ,
        nullable=False,
    )

    # Source tracking (for synced content)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Flexible extra data storage
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    store: Mapped["Store"] = relationship(
        "Store",
        back_populates="knowledge_articles",
    )
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="KnowledgeChunk.chunk_index",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeArticle {self.title} ({self.content_type.value})>"


class KnowledgeChunk(Base):
    """Chunked content for RAG retrieval with embeddings."""

    __tablename__ = "knowledge_chunks"

    # Article relationship
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Chunk content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Vector embedding for semantic search
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
    )

    # Chunk extra data
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    article: Mapped["KnowledgeArticle"] = relationship(
        "KnowledgeArticle",
        back_populates="chunks",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeChunk {self.article_id}:{self.chunk_index}>"
