"""AbandonedCheckout model for tracking Shopify checkout abandonment."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.store import Store


class CheckoutStatus(str, enum.Enum):
    """Status of an abandoned checkout."""

    ACTIVE = "active"
    ABANDONED = "abandoned"
    RECOVERED = "recovered"
    COMPLETED = "completed"


class AbandonedCheckout(Base):
    """Tracks Shopify checkouts for abandonment detection and recovery.

    Created/updated via checkout webhooks. When a checkout goes stale
    (no updates within the threshold), it's marked as abandoned and
    a recovery sequence is triggered.
    """

    __tablename__ = "abandoned_checkouts"
    __table_args__ = (
        UniqueConstraint(
            "store_id", "shopify_checkout_id", name="uq_abandoned_checkouts_store_checkout"
        ),
    )

    # Store relationship (multi-tenancy)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Shopify checkout identifiers
    shopify_checkout_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    shopify_checkout_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Customer info
    customer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    customer_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Cart details
    total_price: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )
    line_items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    checkout_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    # Status tracking
    status: Mapped[CheckoutStatus] = mapped_column(
        Enum(
            CheckoutStatus,
            name="checkout_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=CheckoutStatus.ACTIVE,
        nullable=False,
    )
    abandonment_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    recovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_order_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Extensible data
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    store: Mapped["Store"] = relationship("Store")

    def __repr__(self) -> str:
        return f"<AbandonedCheckout {self.shopify_checkout_id} ({self.status.value})>"
