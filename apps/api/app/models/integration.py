"""Store integration model for e-commerce platform connections."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.store import Store


class PlatformType(str, enum.Enum):
    """Supported e-commerce platforms."""

    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"
    BIGCOMMERCE = "bigcommerce"
    MAGENTO = "magento"
    CUSTOM = "custom"


class IntegrationStatus(str, enum.Enum):
    """Integration connection status."""

    PENDING = "pending"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class StoreIntegration(Base):
    """Store integration model for connecting to e-commerce platforms.

    Each store has exactly one integration to a platform (Shopify, WooCommerce, etc.).
    Credentials are stored as encrypted JSON to support different platform requirements.
    """

    __tablename__ = "store_integrations"

    # Link to store (1:1 relationship)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Platform information
    platform: Mapped[PlatformType] = mapped_column(
        Enum(PlatformType, name="platform_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    platform_store_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    platform_domain: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Credentials (encrypted JSON)
    # Shopify: {access_token}
    # WooCommerce: {consumer_key, consumer_secret, url}
    # BigCommerce: {store_hash, access_token, client_id}
    credentials: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Status tracking
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(
            IntegrationStatus,
            name="integration_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=IntegrationStatus.PENDING,
        nullable=False,
    )
    status_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Sync tracking
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sync_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    store: Mapped["Store"] = relationship(
        "Store",
        back_populates="integration",
    )

    def __repr__(self) -> str:
        return f"<StoreIntegration {self.platform.value}:{self.platform_domain}>"
