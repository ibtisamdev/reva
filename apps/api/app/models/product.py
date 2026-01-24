"""Product model for synced e-commerce products."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.store import Store


class Product(Base):
    """Product model synced from e-commerce platforms.

    Products are scoped to a store and synced from the connected platform.
    The platform_product_id is the external ID from the platform (Shopify, WooCommerce, etc.).
    """

    __tablename__ = "products"

    # Store relationship (replaces organization_id)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Platform product identifier (external ID from Shopify/WooCommerce/etc.)
    platform_product_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Product data
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
    )

    # Arrays and JSON fields
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
    )
    variants: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    images: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    # Vector embedding for semantic search (1536 dimensions for OpenAI embeddings)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
    )

    # Sync tracking
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    store: Mapped["Store"] = relationship(
        "Store",
        back_populates="products",
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_products_store_platform_id",
            "store_id",
            "platform_product_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<Product {self.title} ({self.platform_product_id})>"
