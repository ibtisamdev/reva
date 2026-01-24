"""Organization model representing Shopify stores."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.knowledge import KnowledgeArticle
    from app.models.product import Product
    from app.models.user import User


class Organization(Base):
    """Organization model representing a Shopify store."""

    __tablename__ = "organizations"

    # Shopify integration
    shopify_domain: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    shopify_access_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # Encrypted

    # Store information
    shop_name: Mapped[str] = mapped_column(String(255), nullable=False)
    shop_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Plan and billing
    plan: Mapped[str] = mapped_column(
        String(50),
        default="free",
        nullable=False,
    )

    # Flexible settings storage
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    knowledge_articles: Mapped[list["KnowledgeArticle"]] = relationship(
        "KnowledgeArticle",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization {self.shop_name} ({self.shopify_domain})>"
