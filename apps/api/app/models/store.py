"""Store model for multi-tenant store management."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.integration import StoreIntegration
    from app.models.knowledge import KnowledgeArticle
    from app.models.product import Product


class Store(Base):
    """Store model representing a single e-commerce store.

    Each organization (from Better Auth) can have multiple stores.
    Each store has one integration (Shopify, WooCommerce, etc.).
    All products, knowledge articles, and conversations are scoped to a store.
    """

    __tablename__ = "stores"

    # Link to Better Auth's organization
    organization_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Store information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Plan and billing (per store)
    plan: Mapped[str] = mapped_column(
        String(50),
        default="free",
        nullable=False,
    )

    # Store status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Flexible settings storage (widget config, AI settings, etc.)
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    integration: Mapped["StoreIntegration | None"] = relationship(
        "StoreIntegration",
        back_populates="store",
        uselist=False,
        cascade="all, delete-orphan",
    )
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="store",
        cascade="all, delete-orphan",
    )
    knowledge_articles: Mapped[list["KnowledgeArticle"]] = relationship(
        "KnowledgeArticle",
        back_populates="store",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="store",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Store {self.name} ({self.plan})>"
